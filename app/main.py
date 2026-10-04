from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.config import settings
from app.dataset import HumanEvalLoader
from app.llm import OpenAIClient
from app.pipeline import BaselinePipeline
from app.verified_pipeline import VerifiedPipeline
from app.interactive_pipeline import InteractivePipeline
from app.sandbox import SandboxExecutor
app = FastAPI(title="Experimental Self-Verifying AI")
class BaselineRequest(BaseModel): task_id: str
class InteractiveRequest(BaseModel):
    question: str = Field(min_length=1)
    code: str | None = None
    tests: list[str] | None = None


def _attempt_payload(attempt):
    return {"id": attempt.id, "phase": attempt.phase.value, "attempt_index": attempt.attempt_index,
            "candidate_code": attempt.candidate_code, "passed_visible_tests": attempt.passed_visible_tests,
            "passed_hidden_tests": attempt.passed_hidden_tests, "is_selected": attempt.is_selected,
            "stdout": attempt.stdout, "stderr": attempt.stderr, "error_summary": attempt.error_summary,
            "token_usage": attempt.token_usage, "duration_ms": attempt.duration_ms,
            "created_at": attempt.created_at}

@app.post("/baseline/run")
def baseline_run(request: BaselineRequest):
    try:
        run = BaselinePipeline(OpenAIClient(), SandboxExecutor(), SessionLocal, HumanEvalLoader()).run(request.task_id)
        return {"run_id": run.id, "task_id": run.task_id, "hidden_passed": run.hidden_passed, "duration_ms": run.duration_ms, "token_usage": run.token_usage}
    except KeyError: raise HTTPException(404, "Unknown task id")
    except RuntimeError as exc: raise HTTPException(503, str(exc))


@app.post("/verified/run")
def verified_run(request: BaselineRequest):
    try:
        session = VerifiedPipeline(OpenAIClient(), SandboxExecutor(), SessionLocal, HumanEvalLoader()).run(request.task_id)
        return {"session": {"id": session.id, "task_id": session.task_id, "status": session.status.value,
                            "created_at": session.created_at, "completed_at": session.completed_at},
                "attempts": [_attempt_payload(attempt) for attempt in session.attempts]}
    except KeyError: raise HTTPException(404, "Unknown task id")
    except (RuntimeError, ValueError) as exc: raise HTTPException(503, str(exc))


def _evidence_payload(evidence):
    return [{"name": item.name, "passed": item.passed, "error": item.error}
            for item in evidence.tests]


@app.post("/interactive/run")
def interactive_run(request: InteractiveRequest):
    try:
        result = InteractivePipeline(OpenAIClient(), SandboxExecutor(), SessionLocal,
            settings.verification_candidates, settings.max_repair_attempts).run(
                request.question, code=request.code, tests=request.tests)
        session = result.session
        return {"session": {"id": session.id, "source": session.source,
                "status": session.status.value, "question": session.question,
                "oracle_kind": session.oracle_kind, "oracle_tests": result.oracle_tests,
                "canonical_function_name": result.canonical_function_name,
                "canonical_name_note": result.canonical_name_note,
                "created_at": session.created_at, "completed_at": session.completed_at},
                "attempts": [_attempt_payload(attempt) for attempt in session.attempts],
                "candidate_test_results": [_evidence_payload(evidence)
                    for evidence in result.candidate_evidences],
                "selected_test_results": _evidence_payload(result.selected_evidence),
                "repair_test_results": [_evidence_payload(evidence)
                    for evidence in result.repair_evidences]}
    except (RuntimeError, ValueError) as exc: raise HTTPException(503, str(exc))


@app.get("/interactive", response_class=HTMLResponse)
def interactive_page():
    return HTMLResponse(INTERACTIVE_HTML)


INTERACTIVE_HTML = '''<!doctype html><title>Interactive Verification</title>
<style>body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}textarea{width:100%;min-height:7rem;margin:.4rem 0}button{padding:.6rem 1rem}.code-title{display:flex;align-items:center;justify-content:space-between;gap:1rem}pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem;max-height:400px;overflow-y:auto;overflow-x:auto}.result{padding:1rem}.success{background:#e6f6ea}.failure{background:#fde8e7}.oracle{font-weight:600}.error{color:#8a1c1c}</style>
<h1>Interactive code verification</h1><p>Candidate code is always executed in the restricted Docker sandbox.</p>
<label>Question<textarea id=q required placeholder="Describe the function or bug to solve"></textarea></label>
<label>Existing code (optional)<textarea id=c></textarea></label>
<label>Test assertions, one Python assert per line (optional)<textarea id=t placeholder="assert add(2, 3) == 5"></textarea></label>
<button id=go>Generate and verify</button><div id=r></div>
<script>
const r=document.querySelector('#r'),go=document.querySelector('#go'),q=document.querySelector('#q'),c=document.querySelector('#c'),t=document.querySelector('#t');
function errorMessage(detail){if(Array.isArray(detail))return detail.map(item=>item&&item.msg?item.msg:String(item)).join('; ');return typeof detail==='string'?detail:'Request failed.'}
function escapeHtml(v){return String(v).replace(/[&<>]/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[x]))}
go.onclick=async()=>{
 const question=q.value.trim();
 if(!question){r.innerHTML='<p class="error">Enter a question before generating.</p>';q.focus();return}
 const tests=t.value.split('\\n').filter(x=>x.trim()),body={question,code:c.value||null,tests:tests.length?tests:null};
 go.disabled=true;r.textContent='Running sandboxed candidates…';
 try{
  const res=await fetch('/interactive/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const raw=await res.text();let data;
  try{data=JSON.parse(raw)}catch(error){if(!res.ok){r.innerHTML=`<p class="error">Server error: ${escapeHtml(raw||'Request failed.')}</p>`;return}throw error}
  if(!res.ok){r.innerHTML=`<p class="error">${escapeHtml(errorMessage(data.detail))}</p>`;return}
  const independent=data.session.oracle_kind==='user_supplied',working=data.session.status==='succeeded',oracleLabel=independent?'Oracle: user-supplied tests.':'Oracle: self-generated consistency tests (no independent ground truth).',outcome=working?'Working solution found':'No working solution found';
  r.innerHTML=`<section class="result ${working?'success':'failure'}"><h2>${outcome}</h2><p class="oracle">${oracleLabel}</p><p>Selected candidate: ${data.attempts.findIndex(a=>a.is_selected)+1}. Selection: highest number of pooled oracle tests passed; ties keep generation order. Repair triggered: ${data.attempts.some(a=>a.phase==='repair')?'yes':'no'}.</p></section>`;
  function resultsFor(attempt){return (attempt.phase==='candidate'?data.candidate_test_results[attempt.attempt_index]:(attempt.phase==='repair'?data.repair_test_results[attempt.attempt_index]:[]))||[]}
  const scoredAttempts=data.attempts.map(a=>{const results=resultsFor(a);return {attempt:a,passed:results.filter(test=>test.passed).length,total:results.length}});
  const bestScore=scoredAttempts.reduce((best,cur)=>!best||cur.passed>best.passed?cur:best,null);
  const selectedAttempt=data.attempts.find(a=>a.is_selected),repairAttempts=data.attempts.filter(a=>a.phase==='repair'),answerAttempt=bestScore?bestScore.attempt:selectedAttempt;
  const answerResults=bestScore?resultsFor(bestScore.attempt):[],answerPassed=bestScore?bestScore.passed:0;
  r.innerHTML+=`<section class="result"><div class="code-title"><h2>${working?'Final answer — fully verified':'Best attempt — not fully verified'}</h2><button id="copy-code" type="button">Copy to clipboard</button></div><p>Passed ${answerPassed} of ${answerResults.length} checks.</p><pre>${escapeHtml(answerAttempt?answerAttempt.candidate_code:'')}</pre></section>`;
  const candidateScores=data.attempts.filter(a=>a.phase==='candidate').map(attempt=>{const results=(attempt.phase==='candidate'?data.candidate_test_results[attempt.attempt_index]:(attempt.phase==='repair'?data.repair_test_results[attempt.attempt_index]:[]))||[];return {attempt,passed:results.filter(test=>test.passed).length,total:results.length}});
  const selectedScore=candidateScores.find(score=>selectedAttempt&&score.attempt.attempt_index===selectedAttempt.attempt_index);
  let selectionExplanation=candidateScores.map(score=>`Candidate ${score.attempt.attempt_index+1} passed ${score.passed} of ${score.total} checks.`).join(' ');
  if(selectedScore){
   const tiedScores=candidateScores.filter(score=>score.attempt.attempt_index!==selectedScore.attempt.attempt_index&&score.passed===selectedScore.passed),tieText=tiedScores.length?` It was chosen over ${tiedScores.map(score=>`Candidate ${score.attempt.attempt_index+1}, which also passed ${score.passed} of ${score.total}`).join(' and ')}, because Candidate ${selectedScore.attempt.attempt_index+1} was generated first and ties keep generation order.`:'';
   selectionExplanation+=` Candidate ${selectedScore.attempt.attempt_index+1} was selected because it passed the most checks (${selectedScore.passed} of ${selectedScore.total}).${tieText}`;
  }
  if(repairAttempts.length){
   const repairAttempt=repairAttempts[repairAttempts.length-1],repairResults=(repairAttempt.phase==='candidate'?data.candidate_test_results[repairAttempt.attempt_index]:(repairAttempt.phase==='repair'?data.repair_test_results[repairAttempt.attempt_index]:[]))||[],repairPassed=repairResults.filter(test=>test.passed).length;
   selectionExplanation+=` The selected candidate initially failed verification, so it was sent back for repair. The final repair attempt passed ${repairPassed} of ${repairResults.length} checks.`;
  }
  r.innerHTML+=`<section class="result"><h2>Why this candidate was selected</h2><p>${selectionExplanation}</p></section><section class="result"><h2>Pooled oracle tests</h2><pre>${data.session.oracle_tests.map(x=>escapeHtml(x)).join('\\n')}</pre></section>`;
  data.attempts.forEach((a,i)=>{const evidence=a.phase==='candidate'?data.candidate_test_results[a.attempt_index]:(a.phase==='repair'?data.repair_test_results[a.attempt_index]:[]);r.innerHTML+=`<details><summary>Candidate ${i+1} (${a.phase}) ${a.is_selected?'— selected':''}; ${evidence.filter(x=>x.passed).length}/${evidence.length} tests passed</summary><pre>${escapeHtml(a.candidate_code)}</pre><pre>${escapeHtml(JSON.stringify(evidence,null,2))}</pre></details>`})
  const copyButton=document.querySelector('#copy-code');
  if(copyButton&&answerAttempt)copyButton.onclick=async()=>{try{if(!navigator.clipboard||!navigator.clipboard.writeText)return;await navigator.clipboard.writeText(answerAttempt.candidate_code);copyButton.textContent='Copied!';setTimeout(()=>{copyButton.textContent='Copy to clipboard'},1500)}catch(error){}};
 }catch(error){r.innerHTML='<p class="error">Network error: unable to reach the verification service. Please try again.</p>'}finally{go.disabled=false}
};
</script>'''
