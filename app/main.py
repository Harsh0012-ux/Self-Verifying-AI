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


INTERACTIVE_HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Interactive Verification</title>
<style>
:root {
  --bg-color: #f8fafc;
  --text-color: #0f172a;
  --text-muted: #475569;
  --card-bg: #ffffff;
  --card-border: #e2e8f0;
  --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  --border-color: #e2e8f0;

  --input-bg: #ffffff;
  --input-border: #cbd5e1;
  --input-text: #0f172a;
  --input-placeholder: #94a3b8;
  --input-focus-border: #2563eb;
  --focus-ring: rgba(37, 99, 235, 0.2);

  --btn-primary-bg: #0f172a;
  --btn-primary-text: #ffffff;
  --btn-primary-hover-bg: #1e293b;
  --btn-primary-disabled-bg: #94a3b8;
  --btn-primary-disabled-text: #f1f5f9;

  --btn-secondary-bg: #ffffff;
  --btn-secondary-text: #334155;
  --btn-secondary-border: #cbd5e1;
  --btn-secondary-hover-bg: #f1f5f9;

  --success-bg: #ecfdf5;
  --success-border: #10b981;
  --success-text: #064e3b;
  --success-title: #047857;

  --failure-bg: #fef2f2;
  --failure-border: #ef4444;
  --failure-text: #7f1d1d;
  --failure-title: #b91c1c;

  --error-text: #dc2626;

  --pre-bg: #f1f5f9;
  --pre-text: #0f172a;
  --pre-border: #e2e8f0;

  --summary-bg: #f8fafc;
  --summary-hover-bg: #f1f5f9;
}

:root[data-theme="dark"] {
  --bg-color: #0b0f17;
  --text-color: #f1f5f9;
  --text-muted: #94a3b8;
  --card-bg: #131b28;
  --card-border: #242f44;
  --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
  --border-color: #242f44;

  --input-bg: #0f1520;
  --input-border: #2d3b55;
  --input-text: #f8fafc;
  --input-placeholder: #64748b;
  --input-focus-border: #38bdf8;
  --focus-ring: rgba(56, 189, 248, 0.25);

  --btn-primary-bg: #2563eb;
  --btn-primary-text: #ffffff;
  --btn-primary-hover-bg: #1d4ed8;
  --btn-primary-disabled-bg: #1e293b;
  --btn-primary-disabled-text: #475569;

  --btn-secondary-bg: #1a2233;
  --btn-secondary-text: #e2e8f0;
  --btn-secondary-border: #2e3c54;
  --btn-secondary-hover-bg: #242f44;

  --success-bg: #072518;
  --success-border: #22c55e;
  --success-text: #d1fae5;
  --success-title: #4ade80;

  --failure-bg: #2b0f13;
  --failure-border: #f43f5e;
  --failure-text: #ffe4e6;
  --failure-title: #fb7185;

  --error-text: #f87171;

  --pre-bg: #090d14;
  --pre-text: #e2e8f0;
  --pre-border: #1e293b;

  --summary-bg: #161e2e;
  --summary-hover-bg: #1c263a;
}

body {
  font: 16px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1.25rem;
  background-color: var(--bg-color);
  color: var(--text-color);
  line-height: 1.5;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.header-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0;
  color: var(--text-color);
  letter-spacing: -0.02em;
}

.subtitle {
  color: var(--text-muted);
  margin: 0.35rem 0 1rem 0;
  font-size: 0.95rem;
}

label {
  display: block;
  font-weight: 600;
  font-size: 0.9rem;
  margin-top: 1.25rem;
  color: var(--text-color);
}

textarea {
  display: block;
  width: 100%;
  box-sizing: border-box;
  min-height: 7rem;
  margin: 0.4rem 0;
  padding: 0.75rem;
  font: inherit;
  font-size: 0.95rem;
  background-color: var(--input-bg);
  color: var(--input-text);
  border: 1px solid var(--input-border);
  border-radius: 8px;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  resize: vertical;
}

textarea::placeholder {
  color: var(--input-placeholder);
}

textarea:focus {
  outline: none;
  border-color: var(--input-focus-border);
  box-shadow: 0 0 0 3px var(--focus-ring);
}

button {
  font: inherit;
  font-size: 0.95rem;
  font-weight: 500;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
}

#go {
  background-color: var(--btn-primary-bg);
  color: var(--btn-primary-text);
  border: 1px solid transparent;
  margin-top: 0.75rem;
}

#go:hover:not(:disabled) {
  background-color: var(--btn-primary-hover-bg);
}

#go:disabled {
  background-color: var(--btn-primary-disabled-bg);
  color: var(--btn-primary-disabled-text);
  cursor: not-allowed;
  opacity: 0.7;
}

#theme-toggle, #copy-code {
  background-color: var(--btn-secondary-bg);
  color: var(--btn-secondary-text);
  border: 1px solid var(--btn-secondary-border);
}

#theme-toggle:hover, #copy-code:hover {
  background-color: var(--btn-secondary-hover-bg);
}

.code-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.result {
  margin: 1.25rem 0;
  padding: 1.25rem;
  border-radius: 8px;
  background-color: var(--card-bg);
  border: 1px solid var(--card-border);
  box-shadow: var(--card-shadow);
  color: var(--text-color);
}

.result h2 {
  margin-top: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-color);
}

.success {
  background-color: var(--success-bg);
  border-left: 5px solid var(--success-border);
  color: var(--success-text);
}

.success h2 {
  color: var(--success-title);
}

.failure {
  background-color: var(--failure-bg);
  border-left: 5px solid var(--failure-border);
  color: var(--failure-text);
}

.failure h2 {
  color: var(--failure-title);
}

.oracle {
  font-weight: 600;
  margin: 0.4rem 0;
}

.error {
  color: var(--error-text);
  font-weight: 500;
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
  background-color: var(--pre-bg);
  color: var(--pre-text);
  border: 1px solid var(--pre-border);
  border-radius: 6px;
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
  overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}

details {
  margin: 0.85rem 0;
  border: 1px solid var(--card-border);
  border-radius: 8px;
  background-color: var(--card-bg);
  box-shadow: var(--card-shadow);
  overflow: hidden;
}

summary {
  padding: 0.75rem 1rem;
  cursor: pointer;
  font-weight: 500;
  color: var(--text-color);
  background-color: var(--summary-bg);
  transition: background-color 0.15s ease;
}

summary:hover {
  background-color: var(--summary-hover-bg);
}

details[open] summary {
  border-bottom: 1px solid var(--border-color);
}

details pre {
  margin: 0.75rem 1rem;
}
</style>
</head>
<body>
<div class="header-bar">
  <div>
    <h1>Interactive code verification</h1>
    <p class="subtitle">Candidate code is always executed in the restricted Docker sandbox.</p>
  </div>
  <button id="theme-toggle" type="button" aria-label="Toggle color theme">🌙 Dark mode</button>
</div>
<label>Question<textarea id=q required placeholder="Describe the function or bug to solve"></textarea></label>
<label>Existing code (optional)<textarea id=c></textarea></label>
<label>Test assertions, one Python assert per line (optional)<textarea id=t placeholder="assert add(2, 3) == 5"></textarea></label>
<button id=go>Generate and verify</button><div id=r></div>
<script>
(function(){
 const saved=localStorage.getItem('theme');
 const prefersDark=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;
 const theme=saved||(prefersDark?'dark':'light');
 document.documentElement.setAttribute('data-theme',theme);
 const toggle=document.querySelector('#theme-toggle');
 function updateBtn(t){if(toggle){toggle.textContent=t==='dark'?'☀️ Light mode':'🌙 Dark mode';toggle.setAttribute('aria-pressed',t==='dark')}}
 updateBtn(theme);
 if(toggle){
  toggle.onclick=()=>{
   const cur=document.documentElement.getAttribute('data-theme')||'light';
   const next=cur==='dark'?'light':'dark';
   document.documentElement.setAttribute('data-theme',next);
   localStorage.setItem('theme',next);
   updateBtn(next);
  };
 }
})();
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
</script></body></html>'''
