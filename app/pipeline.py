from app.dataset import HumanEvalLoader
from app.code_extraction import extract_python_code
from app.llm import LLMClient
from app.models import Run, RunMode, TestResult
from app.sandbox import SandboxExecutor

class BaselinePipeline:
    def __init__(self, llm: LLMClient, sandbox: SandboxExecutor, session_factory, loader=None):
        self.llm, self.sandbox, self.session_factory, self.loader = llm, sandbox, session_factory, loader or HumanEvalLoader()
    def run(self, task_id: str, *, trial_index: int = 0) -> Run:
        task = self.loader.get(task_id)
        generation = self.llm.generate("Complete only Python code for this HumanEval problem.\n" + task.prompt)
        candidate_code = extract_python_code(generation.code)
        evidence = self.sandbox.run(candidate_code, [task.hidden_test])
        with self.session_factory() as session:
            run = Run(task_id=task_id, mode=RunMode.baseline, trial_index=trial_index,
                candidate_code=candidate_code, hidden_passed=evidence.passed,
                duration_ms=evidence.duration_ms, token_usage=generation.token_usage)
            run.test_results = [TestResult(name=x.name, passed=x.passed, stdout=x.stdout,
                stderr=x.stderr, error=x.error) for x in evidence.tests]
            session.add(run); session.commit(); session.refresh(run); return run
