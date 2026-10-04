from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.database import SessionLocal
from app.dataset import HumanEvalLoader
from app.interactive_pipeline import InteractivePipeline
from app.llm import OpenAIClient
from app.pipeline import BaselinePipeline
from app.sandbox import SandboxExecutor
from app.verified_pipeline import VerifiedPipeline

app = FastAPI(title="Experimental Self-Verifying AI")


class BaselineRequest(BaseModel):
    task_id: str


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
        return {"run_id": run.id, "task_id": run.task_id, "hidden_passed": run.hidden_passed,
                "duration_ms": run.duration_ms, "token_usage": run.token_usage}
    except KeyError:
        raise HTTPException(404, "Unknown task id")
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))


@app.post("/verified/run")
def verified_run(request: BaselineRequest):
    try:
        session = VerifiedPipeline(OpenAIClient(), SandboxExecutor(), SessionLocal, HumanEvalLoader()).run(request.task_id)
        return {"session": {"id": session.id, "task_id": session.task_id, "status": session.status.value,
                            "created_at": session.created_at, "completed_at": session.completed_at},
                "attempts": [_attempt_payload(attempt) for attempt in session.attempts]}
    except KeyError:
        raise HTTPException(404, "Unknown task id")
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(503, str(exc))


@app.get("/tasks/humaneval")
def humaneval_tasks():
    """List task ids from the existing HumanEval cache/loader, never a hardcoded list."""
    try:
        return list(HumanEvalLoader().problems())
    except OSError as exc:
        raise HTTPException(503, f"HumanEval tasks are unavailable: {exc}")


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
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(503, str(exc))


SHARED_STYLES = '''<style>
:root {
  --bg: #f8fafc;
  --bg-gradient: radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.05) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.04) 0px, transparent 50%);
  --card: #ffffff;
  --text: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;
  --border-focus: #6366f1;
  --pre: #0f172a;
  --pre-text: #f8fafc;
  --input: #ffffff;
  --accent: #4f46e5;
  --accent-hover: #4338ca;
  --accent-text: #ffffff;
  --accent-subtle: rgba(79, 70, 229, 0.08);
  --success: #059669;
  --success-bg: #ecfdf5;
  --success-border: #10b981;
  --failure: #dc2626;
  --failure-bg: #fef2f2;
  --failure-border: #ef4444;
  --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px 0 rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
  --skeleton-base: #e2e8f0;
  --skeleton-highlight: #f8fafc;
}
:root[data-theme="dark"] {
  --bg: #0b0f17;
  --bg-gradient: radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
  --card: #131b28;
  --text: #f1f5f9;
  --muted: #94a3b8;
  --border: #242f44;
  --border-focus: #818cf8;
  --pre: #070a10;
  --pre-text: #e2e8f0;
  --input: #0f1520;
  --accent: #6366f1;
  --accent-hover: #818cf8;
  --accent-text: #ffffff;
  --accent-subtle: rgba(99, 102, 241, 0.16);
  --success: #34d399;
  --success-bg: #062b1a;
  --success-border: #10b981;
  --failure: #f87171;
  --failure-bg: #2b0f13;
  --failure-border: #ef4444;
  --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 8px -1px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 10px 20px -3px rgba(0, 0, 0, 0.6);
  --skeleton-base: #1c2638;
  --skeleton-highlight: #2b3952;
}
* { box-sizing: border-box; }
body {
  max-width: 1180px;
  margin: 1.5rem auto;
  padding: 0 1.25rem;
  font: 16px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6;
  color: var(--text);
  background: var(--bg);
  background-image: var(--bg-gradient);
  background-attachment: fixed;
  transition: background-color 0.25s ease, color 0.25s ease;
}
a { color: inherit; text-decoration: none; }
h1, h2, h3, p { margin-top: 0; }
h1 { font-size: 2.25rem; font-weight: 800; letter-spacing: -0.025em; line-height: 1.2; margin-bottom: 0.5rem; }
h2 { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.3; }
h3 { font-size: 1.1rem; font-weight: 600; line-height: 1.4; }
main { padding: 2rem 0 3.5rem; }
.subtitle, .muted { color: var(--muted); font-size: 1.05rem; margin-bottom: 1.5rem; }

.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
  transition: border-color 0.25s ease;
}
.site-brand {
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  letter-spacing: -0.02em;
  transition: color 0.2s ease;
}
.site-brand:hover { color: var(--accent); }
.site-brand-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  background: var(--accent-subtle);
  color: var(--accent);
  border: 1px solid var(--border);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.site-nav {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}
.site-nav a, .theme-toggle, button {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.55rem 0.95rem;
  font: inherit;
  font-size: 0.925rem;
  font-weight: 500;
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: var(--shadow-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
}
.site-nav a:hover, .theme-toggle:hover, button:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}
.site-nav a:active, .theme-toggle:active, button:active:not(:disabled) { transform: translateY(0); }
.site-nav a[aria-current="page"] {
  background: var(--accent);
  color: var(--accent-text);
  border-color: var(--accent);
  box-shadow: 0 2px 4px rgba(79, 70, 229, 0.25);
}
.site-nav a[aria-current="page"]:hover { background: var(--accent-hover); color: var(--accent-text); }

button.primary {
  margin-top: 1rem;
  background: var(--accent);
  color: var(--accent-text);
  border-color: var(--accent);
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);
}
button.primary:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
  color: var(--accent-text);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
}
button:disabled { opacity: 0.55; cursor: not-allowed; transform: none !important; box-shadow: none !important; }

label {
  display: block;
  font-weight: 600;
  font-size: 0.95rem;
  margin-top: 1.25rem;
  color: var(--text);
}
textarea, select {
  display: block;
  width: 100%;
  margin-top: 0.45rem;
  padding: 0.8rem 1rem;
  font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--text);
  background: var(--input);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
textarea:focus, select:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--accent-subtle);
}
textarea { min-height: 7rem; resize: vertical; }

.result {
  margin: 1.25rem 0;
  padding: 1.25rem 1.5rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
  animation: bannerFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  transition: all 0.25s ease;
}
@keyframes bannerFadeIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}
.result h2 { margin-bottom: 0.5rem; font-size: 1.25rem; display: flex; align-items: center; gap: 0.5rem; }
.success {
  background: var(--success-bg);
  border-color: var(--success-border);
  border-left: 5px solid var(--success);
}
.failure {
  background: var(--failure-bg);
  border-color: var(--failure-border);
  border-left: 5px solid var(--failure);
}
.error {
  border-left: 5px solid var(--failure);
  color: var(--failure);
  font-weight: 500;
  padding: 1rem 1.25rem;
  background: var(--failure-bg);
  border-radius: 8px;
  margin: 1rem 0;
}
.oracle { font-weight: 500; color: var(--muted); }

pre {
  max-height: 420px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 1rem 1.25rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--pre);
  color: var(--pre-text);
  font: 13px/1.55 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.code-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}
.button-row, .landing-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 1rem;
}

.candidate-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
  margin: 1.25rem 0;
}
@keyframes cardReveal {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
.candidate-card {
  margin: 0;
  min-width: 0;
  padding: 1.25rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease;
  animation: cardReveal 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.candidate-card:hover {
  transform: translateY(-3px);
  border-color: var(--accent);
  box-shadow: var(--shadow-md);
}
.candidate-grid > .candidate-card:nth-child(1) { animation-delay: 0.05s; }
.candidate-grid > .candidate-card:nth-child(2) { animation-delay: 0.18s; }
.candidate-grid > .candidate-card:nth-child(3) { animation-delay: 0.31s; }
.candidate-grid > .candidate-card:nth-child(4) { animation-delay: 0.44s; }
.candidate-card h3 { margin-bottom: 0.4rem; font-size: 1.05rem; }
.candidate-card p { font-size: 0.875rem; color: var(--muted); margin-bottom: 0.75rem; }
.candidate-card pre { font-size: 0.8rem; max-height: 240px; flex: 1; margin: 0.25rem 0; }

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes pulseGlow {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
.skeleton-card {
  margin: 0;
  min-width: 0;
  min-height: 220px;
  padding: 1.25rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.skeleton-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--muted);
  animation: pulseGlow 1.8s infinite ease-in-out;
}
.skeleton-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
}
.skeleton-line {
  height: 0.85rem;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--skeleton-base) 25%, var(--skeleton-highlight) 50%, var(--skeleton-base) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.6s infinite ease-in-out;
}
.skeleton-line.w-75 { width: 75%; }
.skeleton-line.w-50 { width: 50%; }
.skeleton-line.w-30 { width: 30%; }
.skeleton-box {
  flex: 1;
  min-height: 120px;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--skeleton-base) 25%, var(--skeleton-highlight) 50%, var(--skeleton-base) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.6s infinite ease-in-out;
}

.hero-section { padding: 1rem 0 0.5rem; }
.hero-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.35rem 0.8rem;
  border-radius: 9999px;
  background: var(--accent-subtle);
  color: var(--accent);
  border: 1px solid var(--border);
  margin-bottom: 1.25rem;
}
.hero-title {
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.03em;
  margin-bottom: 1rem;
  color: var(--text);
}
.hero-desc {
  font-size: 1.125rem;
  line-height: 1.6;
  color: var(--muted);
  max-width: 50rem;
  margin-bottom: 2.25rem;
}
.landing-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.5rem;
  margin-bottom: 3.5rem;
}
.cta-card {
  display: flex;
  flex-direction: column;
  padding: 1.75rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  text-decoration: none;
  color: var(--text);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.cta-card:hover {
  transform: translateY(-4px);
  border-color: var(--accent);
  box-shadow: var(--shadow-lg);
}
.cta-card.primary-cta {
  border-color: rgba(99, 102, 241, 0.4);
  background: linear-gradient(135deg, var(--card) 60%, var(--accent-subtle) 100%);
}
.cta-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}
.cta-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  background: var(--accent-subtle);
  color: var(--accent);
}
.cta-arrow {
  font-size: 1.25rem;
  color: var(--accent);
  transition: transform 0.2s ease;
}
.cta-card:hover .cta-arrow { transform: translateX(4px); }
.cta-card h3 { font-size: 1.35rem; margin-bottom: 0.5rem; }
.cta-card p { color: var(--muted); font-size: 0.95rem; margin-bottom: 1.25rem; flex: 1; }
.cta-button { font-size: 0.925rem; font-weight: 600; color: var(--accent); }

.features-section {
  padding-top: 1.75rem;
  border-top: 1px solid var(--border);
}
.features-heading { font-size: 1.5rem; margin-bottom: 1.5rem; letter-spacing: -0.02em; }
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
}
.feature-card {
  padding: 1.5rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s ease, border-color 0.2s ease;
}
.feature-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.feature-icon { font-size: 1.75rem; margin-bottom: 0.75rem; }
.feature-card h3 { font-size: 1.1rem; margin-bottom: 0.4rem; }
.feature-card p { font-size: 0.875rem; color: var(--muted); line-height: 1.5; margin: 0; }

@media (max-width: 1024px) {
  .candidate-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .features-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  body { margin: 1rem auto; padding: 0 1rem; }
  .site-header { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 0.75rem; }
  .site-brand { grid-column: 1; }
  .theme-toggle { grid-column: 2; justify-self: end; }
  .site-nav { grid-column: 1 / -1; width: 100%; display: flex; gap: 0.35rem; }
  .site-nav a { flex: 1; text-align: center; padding: 0.5rem 0.25rem; font-size: 0.85rem; }
  .hero-title { font-size: 1.85rem; }
  .candidate-grid, .landing-cards, .features-grid { grid-template-columns: 1fr; }
}
</style>'''

THEME_SCRIPT = '''<script>
(()=>{
  const key = 'theme';
  const saved = localStorage.getItem(key);
  const theme = saved || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const apply = value => {
    document.documentElement.dataset.theme = value;
    const button = document.querySelector('#theme-toggle');
    if (button) {
      button.textContent = value === 'dark' ? '☀️ Light mode' : '🌙 Dark mode';
      button.setAttribute('aria-pressed', String(value === 'dark'));
    }
  };
  apply(theme);
  document.querySelector('#theme-toggle')?.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem(key, next);
    apply(next);
  });
})();
</script>'''


def page_shell(title: str, active: str, content: str, script: str = "") -> str:
    links = [("home", "/", "Home"), ("interactive", "/interactive", "Interactive"),
             ("humaneval", "/humaneval", "HumanEval Demo")]
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if key == active else ""}>{label}</a>'
        for key, href, label in links
    )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>{SHARED_STYLES}</head><body><header class="site-header"><a href="/" class="site-brand">Self-Verifying AI <span class="site-brand-badge">v1.0</span></a><nav class="site-nav" aria-label="Primary">{nav}</nav><button id="theme-toggle" class="theme-toggle" type="button" aria-label="Toggle color theme"></button></header><main>{content}</main>{THEME_SCRIPT}{script}</body></html>'''


@app.get("/", response_class=HTMLResponse)
def home_page():
    return HTMLResponse(page_shell("Self-Verifying AI", "home", '''
<section class="hero-section">
  <div class="hero-badge">Docker Sandbox · Oracle Verification · Automated Repair</div>
  <h1 class="hero-title">Reliable Code Generation with Verifiable Ground Truth</h1>
  <p class="hero-desc">Generate multi-candidate Python solutions, execute them in an isolated Docker sandbox before presenting a result, pool consistent oracles, and transparently surface verification evidence.</p>
  <div class="landing-cards">
    <a href="/interactive" class="cta-card primary-cta">
      <div class="cta-card-header">
        <span class="cta-badge">Interactive Mode</span>
        <span class="cta-arrow">&rarr;</span>
      </div>
      <h3>Interactive Verification Studio</h3>
      <p>Submit free-form coding tasks, test assertions, or existing code. Inspect candidate passes and pooled consistency oracles.</p>
      <span class="cta-button">Launch Studio &rarr;</span>
    </a>
    <a href="/humaneval" class="cta-card">
      <div class="cta-card-header">
        <span class="cta-badge">Benchmark Mode</span>
        <span class="cta-arrow">&rarr;</span>
      </div>
      <h3>HumanEval Benchmark Demo</h3>
      <p>Compare standard single-pass LLM baselines against our verified multi-candidate pipeline on real HumanEval problems.</p>
      <span class="cta-button">Explore Benchmarks &rarr;</span>
    </a>
  </div>
  <div class="features-section">
    <h2 class="features-heading">Architecture & Core Guarantees</h2>
    <div class="features-grid">
      <div class="feature-card">
        <div class="feature-icon">&#128737;&#65039;</div>
        <h3>Docker Sandbox Isolation</h3>
        <p>Every candidate is executed inside an ephemeral Linux container with strict memory, CPU, and network boundaries.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">&#128269;</div>
        <h3>Transparent Oracles</h3>
        <p>Candidate evidence is recorded explicitly. Consistency tests are pooled across candidates and clearly labeled—never masquerading as ground truth.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">&#9889;</div>
        <h3>Automated Iterative Repair</h3>
        <p>Candidates failing tests or raising runtime errors receive targeted feedback for autonomous repair cycles, improving solution correctness.</p>
      </div>
    </div>
  </div>
</section>'''))


@app.get("/interactive", response_class=HTMLResponse)
def interactive_page():
    content = '''<h1>Interactive code verification</h1><p class="subtitle">Candidate code is always executed in the restricted Docker sandbox.</p><label>Question<textarea id="question" required placeholder="Describe the function or bug to solve"></textarea></label><label>Existing code (optional)<textarea id="code" placeholder="Paste existing or partially broken code here"></textarea></label><label>Test assertions, one Python assert per line (optional)<textarea id="tests" placeholder="assert add(2, 3) == 5"></textarea></label><button id="run-interactive" class="primary">Generate and verify</button><div id="interactive-results" aria-live="polite"></div>'''
    script = '''<script>
const interactiveResults=document.querySelector('#interactive-results'),interactiveGo=document.querySelector('#run-interactive');
const escapeHtml=value=>String(value??'').replace(/[&<>]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[char]));
const errorMessage=detail=>Array.isArray(detail)?detail.map(item=>item?.msg||String(item)).join('; '):(typeof detail==='string'?detail:'Request failed.');
const skeletonCards=()=>'<div class="candidate-grid">'+[1,2,3].map(number=>`<article class="skeleton-card" aria-label="Loading candidate ${number}"><div class="skeleton-header"><span class="skeleton-dot"></span>Candidate ${number} executing in sandbox…</div><div class="skeleton-line w-75"></div><div class="skeleton-line w-50"></div><div class="skeleton-box"></div></article>`).join('')+'</div>';
const evidenceFor=(data,attempt)=>attempt.phase==='candidate'?(data.candidate_test_results[attempt.attempt_index]||[]):(attempt.phase==='repair'?(data.repair_test_results[attempt.attempt_index]||[]):[]);
interactiveGo.onclick=async()=>{const question=document.querySelector('#question').value.trim();if(!question){interactiveResults.innerHTML='<p class="error">Enter a question before generating.</p>';document.querySelector('#question').focus();return;}const tests=document.querySelector('#tests').value.split('\\n').filter(value=>value.trim());interactiveGo.disabled=true;interactiveResults.innerHTML='<section class="result"><p>Running sandboxed candidates…</p>'+skeletonCards()+'</section>';try{const response=await fetch('/interactive/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,code:document.querySelector('#code').value||null,tests:tests.length?tests:null})}),raw=await response.text();let data;try{data=JSON.parse(raw);}catch{throw new Error(raw||'Request failed.');}if(!response.ok)throw new Error(errorMessage(data.detail));const working=data.session.status==='succeeded',attempts=data.attempts,candidates=attempts.filter(attempt=>attempt.phase==='candidate'),repairs=attempts.filter(attempt=>attempt.phase==='repair'),selected=attempts.find(attempt=>attempt.is_selected),scores=candidates.map(attempt=>{const evidence=evidenceFor(data,attempt);return{attempt,passed:evidence.filter(test=>test.passed).length,total:evidence.length};}),selectedScore=scores.find(score=>score.attempt===selected),answerScore=scores.reduce((best,current)=>!best||current.passed>best.passed?current:best,null),answer=answerScore?.attempt||selected,oracle=data.session.oracle_kind==='user_supplied'?'Oracle: user-supplied tests.':'Oracle: self-generated consistency tests (no independent ground truth).';let explanation=scores.map(score=>`Candidate ${score.attempt.attempt_index+1} passed ${score.passed} of ${score.total} checks.`).join(' ');if(selectedScore){const ties=scores.filter(score=>score.attempt!==selected&&score.passed===selectedScore.passed);explanation+=` Candidate ${selectedScore.attempt.attempt_index+1} was selected because it passed the most checks (${selectedScore.passed} of ${selectedScore.total}).`;if(ties.length)explanation+=` It was generated before ${ties.map(score=>`Candidate ${score.attempt.attempt_index+1}, which also passed ${score.passed} of ${score.total}`).join(' and ')}; ties keep generation order.`;}if(repairs.length){const finalRepair=repairs.at(-1),evidence=evidenceFor(data,finalRepair);explanation+=` The selected candidate was sent for repair; the final repair passed ${evidence.filter(test=>test.passed).length} of ${evidence.length} checks.`;}const cards=(items,label)=>items.map((attempt,index)=>{const evidence=evidenceFor(data,attempt);const passed=evidence.filter(test=>test.passed).length;return`<article class="candidate-card"><h3>${label} ${label==='Candidate'?attempt.attempt_index+1:index+1}${attempt.is_selected?' — selected':''}</h3><p>${passed}/${evidence.length} tests passed</p><pre>${escapeHtml(attempt.candidate_code)}</pre><pre>${escapeHtml(JSON.stringify(evidence,null,2))}</pre></article>`}).join('');interactiveResults.innerHTML=`<section class="result ${working?'success':'failure'}"><h2>${working?'Working solution found':'No working solution found'}</h2><p class="oracle">${oracle}</p><p>Selected candidate: ${selected?selected.attempt_index+1:'not available'}. Repair triggered: ${repairs.length?'yes':'no'}.</p></section><section class="result"><div class="code-title"><h2>${working?'Final answer — fully verified':'Best attempt — not fully verified'}</h2><button id="copy-code" type="button">Copy to clipboard</button></div><pre>${escapeHtml(answer?.candidate_code)}</pre></section><section class="result"><h2>Why this candidate was selected</h2><p>${escapeHtml(explanation)}</p></section><section class="result"><h2>Pooled oracle tests</h2><pre>${data.session.oracle_tests.map(escapeHtml).join('\\n')}</pre></section><h2>Candidates</h2><div class="candidate-grid">${cards(candidates,'Candidate')}</div>${repairs.length?`<h2>Repair attempts</h2><div class="candidate-grid">${cards(repairs,'Repair')}</div>`:''}`;document.querySelector('#copy-code')?.addEventListener('click',async event=>{try{await navigator.clipboard.writeText(answer?.candidate_code||'');event.currentTarget.textContent='Copied!';setTimeout(()=>event.currentTarget.textContent='Copy to clipboard',1500);}catch{}});}catch(error){interactiveResults.innerHTML=`<p class="error">${escapeHtml(error.message||'Network error: unable to reach the verification service.')}</p>`;}finally{interactiveGo.disabled=false;}};
</script>'''
    return HTMLResponse(page_shell("Interactive Verification", "interactive", content, script))


@app.get("/humaneval", response_class=HTMLResponse)
def humaneval_page():
    content = '''<h1>HumanEval Demo</h1><p class="subtitle">Run one cached HumanEval task through either the baseline or multi-candidate verified pipeline.</p><label>HumanEval task<select id="task-select" disabled><option>Loading tasks…</option></select></label><div class="button-row"><button id="run-baseline" class="primary" disabled>Run baseline</button><button id="run-verified" disabled>Run verified</button></div><div id="humaneval-results" aria-live="polite"></div>'''
    script = '''<script>
const escapeHtml=value=>String(value??'').replace(/[&<>]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[char]));
const errorMessage=detail=>Array.isArray(detail)?detail.map(item=>item?.msg||String(item)).join('; '):(typeof detail==='string'?detail:'Request failed.');
const taskSelect=document.querySelector('#task-select'),baselineButton=document.querySelector('#run-baseline'),verifiedButton=document.querySelector('#run-verified'),humanevalResults=document.querySelector('#humaneval-results');
const humanevalSkeleton=()=>'<div class="candidate-grid">'+[1,2,3].map(number=>`<article class="skeleton-card" aria-label="Loading candidate ${number}"><div class="skeleton-header"><span class="skeleton-dot"></span>Candidate ${number} verifying against tests…</div><div class="skeleton-line w-75"></div><div class="skeleton-line w-50"></div><div class="skeleton-box"></div></article>`).join('')+'</div>';
async function loadTasks(){try{const response=await fetch('/tasks/humaneval'),tasks=await response.json();if(!response.ok||!Array.isArray(tasks)||!tasks.length)throw new Error('No HumanEval tasks are available.');taskSelect.innerHTML=tasks.map(task=>`<option value="${escapeHtml(task)}">${escapeHtml(task)}</option>`).join('');taskSelect.disabled=false;baselineButton.disabled=false;verifiedButton.disabled=false;}catch(error){taskSelect.innerHTML='<option>Tasks unavailable</option>';humanevalResults.innerHTML=`<p class="error">${escapeHtml(error.message||'Unable to load tasks.')}</p>`;}}
async function runHumanEval(mode){const task_id=taskSelect.value;if(!task_id||task_id==='Tasks unavailable')return;baselineButton.disabled=true;verifiedButton.disabled=true;humanevalResults.innerHTML='<section class="result"><p>Running '+escapeHtml(mode)+' pipeline…</p>'+(mode==='verified'?humanevalSkeleton():'')+'</section>';try{const response=await fetch(mode==='baseline'?'/baseline/run':'/verified/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id})}),data=await response.json();if(!response.ok)throw new Error(errorMessage(data.detail));if(mode==='baseline'){humanevalResults.innerHTML=`<section class="result ${data.hidden_passed?'success':'failure'}"><h2>Baseline result: ${data.hidden_passed?'passed':'failed'}</h2><p>Task: ${escapeHtml(data.task_id)}</p><p>Duration: ${data.duration_ms??'not recorded'} ms · Token usage: ${data.token_usage??'not recorded'}</p></section>`;return;}const attempts=data.attempts||[],candidates=attempts.filter(attempt=>attempt.phase==='candidate');humanevalResults.innerHTML=`<section class="result ${data.session.status==='succeeded'?'success':'failure'}"><h2>Verified result: ${escapeHtml(data.session.status)}</h2><p>Task: ${escapeHtml(data.session.task_id)}</p></section><h2>Candidates</h2><div class="candidate-grid">${candidates.map(attempt=>`<article class="candidate-card"><h3>Candidate ${attempt.attempt_index+1}${attempt.is_selected?' — selected':''}</h3><p>Visible tests: ${attempt.passed_visible_tests?'passed':'failed'}<br>Hidden tests: ${attempt.passed_hidden_tests===null?'not run':(attempt.passed_hidden_tests?'passed':'failed')}</p><pre>${escapeHtml(attempt.candidate_code)}</pre></article>`).join('')}</div>${attempts.filter(attempt=>attempt.phase==='repair').length?`<section class="result"><h2>Repairs</h2><p>${attempts.filter(attempt=>attempt.phase==='repair').length} repair attempt(s) were recorded.</p></section>`:''}`;}catch(error){humanevalResults.innerHTML=`<p class="error">${escapeHtml(error.message||'Unable to run the pipeline.')}</p>`;}finally{baselineButton.disabled=false;verifiedButton.disabled=false;}}
baselineButton.onclick=()=>runHumanEval('baseline');verifiedButton.onclick=()=>runHumanEval('verified');loadTasks();
</script>'''
    return HTMLResponse(page_shell("HumanEval Demo", "humaneval", content, script))
