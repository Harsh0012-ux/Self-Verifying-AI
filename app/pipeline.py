from datetime import UTC, datetime

from app.dataset import HumanEvalLoader
from app.code_extraction import extract_python_code
from app.llm import LLMClient
from app.models import Run, RunMode, TestResult, VerificationSession, VerificationStatus
from app.sandbox import SandboxExecutor


class BaselinePipeline:
    def __init__(self, llm: LLMClient, sandbox: SandboxExecutor, session_factory, loader=None):
        self.llm, self.sandbox, self.session_factory, self.loader = (
            llm, sandbox, session_factory, loader or HumanEvalLoader()
        )

    def run(self, task_id: str, *, trial_index: int = 0,
            session_id: int | None = None) -> Run:
        """Run the baseline pipeline for one HumanEval task.

        When ``session_id`` is provided (async /sessions workflow) the pipeline
        updates the pre-created VerificationSession's stage, status and
        completed_at.  When None (legacy /baseline/run endpoint) behaviour is
        identical to before this change.
        """
        def _stage(db, stage: str) -> None:
            """Write a stage update if we own a parent session."""
            if session_id is None:
                return
            vs = db.get(VerificationSession, session_id)
            if vs is not None:
                vs.current_stage = stage
                db.commit()

        task = self.loader.get(task_id)

        # --- open one DB session for the whole pipeline run ---
        with self.session_factory() as db:
            _stage(db, "initializing")

            _stage(db, "generating_candidates")
            generation = self.llm.generate(
                "Complete only Python code for this HumanEval problem.\n" + task.prompt
            )
            candidate_code = extract_python_code(generation.code)

            _stage(db, "running_hidden_tests")
            evidence = self.sandbox.run(candidate_code, [task.hidden_test])

            _stage(db, "completing")
            run = Run(
                task_id=task_id,
                mode=RunMode.baseline,
                trial_index=trial_index,
                candidate_code=candidate_code,
                hidden_passed=evidence.passed,
                duration_ms=evidence.duration_ms,
                token_usage=generation.token_usage,
                session_id=session_id,
            )
            run.test_results = [
                TestResult(
                    name=x.name, passed=x.passed,
                    stdout=x.stdout, stderr=x.stderr, error=x.error,
                )
                for x in evidence.tests
            ]
            db.add(run)
            db.flush()

            # Update the parent async session to its terminal state.
            if session_id is not None:
                vs = db.get(VerificationSession, session_id)
                if vs is not None:
                    vs.status = (
                        VerificationStatus.succeeded
                        if evidence.passed
                        else VerificationStatus.exhausted
                    )
                    vs.current_stage = None
                    vs.completed_at = datetime.now(UTC)

            db.commit()
            db.refresh(run)
            return run
