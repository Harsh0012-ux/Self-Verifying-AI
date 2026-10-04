"""Bounded generate, verify, select, and repair workflow."""
import ast
import builtins
import doctest
from datetime import UTC, datetime

from app.code_extraction import extract_python_code
from app.config import settings
from app.dataset import HumanEvalLoader, Problem
from app.llm import LLMClient
from app.models import Attempt, AttemptPhase, VerificationSession, VerificationStatus
from app.sandbox import SandboxEvidence, SandboxExecutor


def visible_assertions(task: Problem) -> list[str]:
    """Translate HumanEval's docstring examples into executable assertions.

    ``Problem.visible_tests`` intentionally retains display-oriented doctest
    lines; the complete prompt retains their expected output, which doctest
    parses reliably without changing the dataset loader.
    """
    assertions: list[str] = []
    for example in doctest.DocTestParser().get_examples(task.prompt):
        # HumanEval docstrings often close immediately after the last example.
        # ``doctest`` includes that delimiter in ``want`` when it is flush-left.
        expected_lines = []
        for line in example.want.splitlines():
            if line.strip().startswith(('"""', "'''")):
                break
            expected_lines.append(line)
        expected = "\n".join(expected_lines).strip()
        if not expected:
            continue
        try:
            value = ast.literal_eval(expected)
        except (SyntaxError, ValueError):
            # Some examples print a non-literal representation.  Comparing its
            # repr still gives the candidate a meaningful visible check.
            assertions.append(f"assert repr(({example.source.strip()})) == {expected!r}")
        else:
            assertions.append(f"assert ({example.source.strip()}) == {value!r}")
    return assertions


def visible_score(evidence: SandboxEvidence) -> int:
    """Number of individual visible tests that passed."""
    return sum(test.passed for test in evidence.tests)


def select_best_candidate(evidences: list[SandboxEvidence]) -> int:
    """Pick the highest visible score; ``max`` preserves first tie order."""
    if not evidences:
        raise ValueError("At least one candidate is required")
    return max(range(len(evidences)), key=lambda index: visible_score(evidences[index]))


def _error_summary(evidence: SandboxEvidence) -> str | None:
    errors = [test.error for test in evidence.tests if test.error]
    if evidence.timed_out:
        errors.append("Sandbox wall-clock timeout")
    if evidence.stderr:
        errors.append(evidence.stderr)
    return "\n".join(errors) or None


# Test code and its output are untrusted prompt inputs: tracebacks can contain
# source lines and exception messages can contain expected values.  Only these
# built-in exception *type names* are safe to carry into a repair prompt.
_BUILTIN_EXCEPTION_NAMES = tuple(sorted(
    name for name, value in vars(builtins).items()
    if isinstance(value, type) and issubclass(value, BaseException)
))


def _repair_evidence_summary(evidence: SandboxEvidence) -> str:
    """Return failure metadata that cannot disclose test-definition source.

    Raw sandbox evidence remains available on ``Attempt`` for diagnostics.
    This intentionally never reads stdout, stderr, test names, or error
    messages into the returned text; they can all contain user/hidden test
    source or values.
    """
    if evidence.timed_out:
        return "Sandbox wall-clock timeout."

    total = len(evidence.tests)
    failed = sum(not test.passed for test in evidence.tests)
    exception_types: list[str] = []
    for test in evidence.tests:
        error = test.error or ""
        for name in _BUILTIN_EXCEPTION_NAMES:
            if name in error and name not in exception_types:
                exception_types.append(name)

    if total:
        summary = f"{failed} of {total} tests failed"
    else:
        summary = "Sandbox execution failed without per-test results"
    if exception_types:
        return f"{summary}; {', '.join(exception_types)} raised."
    if evidence.exit_code not in (None, 0):
        return f"{summary}; sandbox process exited unsuccessfully."
    return f"{summary}."


class VerifiedPipeline:
    def __init__(self, llm: LLMClient, sandbox: SandboxExecutor, session_factory, loader=None,
                 verification_candidates: int | None = None, max_repair_attempts: int | None = None):
        self.llm, self.sandbox, self.session_factory = llm, sandbox, session_factory
        self.loader = loader or HumanEvalLoader()
        self.verification_candidates = verification_candidates if verification_candidates is not None else settings.verification_candidates
        self.max_repair_attempts = max_repair_attempts if max_repair_attempts is not None else settings.max_repair_attempts

    @staticmethod
    def _generation_prompt(task: Problem) -> str:
        return "Complete only Python code for this HumanEval problem.\n" + task.prompt

    @staticmethod
    def _repair_prompt(task: Problem, failed_code: str, evidence: SandboxEvidence) -> str:
        details = _repair_evidence_summary(evidence)
        return (
            "Return only repaired Python code for this HumanEval problem.\n\n"
            f"Problem:\n{task.prompt}\n\nFailed candidate:\n{failed_code}\n\n"
            f"Hidden-test execution evidence:\n{details}"
        )

    @staticmethod
    def _attempt_from_evidence(attempt: Attempt, evidence: SandboxEvidence, *, visible: bool) -> None:
        if visible:
            attempt.passed_visible_tests = evidence.passed
        else:
            attempt.passed_hidden_tests = evidence.passed
        attempt.stdout = evidence.stdout
        attempt.stderr = evidence.stderr
        attempt.error_summary = _error_summary(evidence)
        attempt.duration_ms = evidence.duration_ms

    def run(self, task_id: str, *, trial_index: int = 0,
            eval_hidden_candidates: bool = False) -> VerificationSession:
        """Run one session.

        ``eval_hidden_candidates`` is measurement-only instrumentation.  It
        runs hidden tests for non-selected generated candidates after the
        normal selection/repair path has completed; it never participates in
        selection or repair prompting.
        """
        if self.verification_candidates < 1:
            raise ValueError("verification_candidates must be at least 1")
        if self.max_repair_attempts < 0:
            raise ValueError("max_repair_attempts cannot be negative")
        task = self.loader.get(task_id)
        tests = visible_assertions(task)
        if not tests:
            raise RuntimeError(f"Task {task_id} has no executable visible tests")

        with self.session_factory() as db:
            verification = VerificationSession(task_id=task_id, trial_index=trial_index,
                status=VerificationStatus.running)
            db.add(verification)
            db.flush()

            candidates: list[Attempt] = []
            candidate_evidences: list[SandboxEvidence] = []
            for index in range(self.verification_candidates):
                generation = self.llm.generate(self._generation_prompt(task))
                code = extract_python_code(generation.code)
                evidence = self.sandbox.run(code, tests)
                attempt = Attempt(
                    session_id=verification.id, phase=AttemptPhase.candidate, attempt_index=index,
                    candidate_code=code, token_usage=generation.token_usage,
                )
                self._attempt_from_evidence(attempt, evidence, visible=True)
                db.add(attempt)
                candidates.append(attempt)
                candidate_evidences.append(evidence)

            selected_index = select_best_candidate(candidate_evidences)
            selected = candidates[selected_index]
            selected.is_selected = True
            hidden_evidence = self.sandbox.run(selected.candidate_code, [task.hidden_test])
            self._attempt_from_evidence(selected, hidden_evidence, visible=False)

            if hidden_evidence.passed:
                verification.status = VerificationStatus.succeeded
            else:
                last_code, last_evidence = selected.candidate_code, hidden_evidence
                for repair_index in range(self.max_repair_attempts):
                    generation = self.llm.generate(self._repair_prompt(task, last_code, last_evidence))
                    repaired_code = extract_python_code(generation.code)
                    repair_evidence = self.sandbox.run(repaired_code, [task.hidden_test])
                    repair = Attempt(
                        session_id=verification.id, phase=AttemptPhase.repair, attempt_index=repair_index,
                        candidate_code=repaired_code, token_usage=generation.token_usage,
                    )
                    self._attempt_from_evidence(repair, repair_evidence, visible=False)
                    db.add(repair)
                    if repair_evidence.passed:
                        verification.status = VerificationStatus.succeeded
                        break
                    last_code, last_evidence = repaired_code, repair_evidence
                else:
                    verification.status = VerificationStatus.exhausted

            # Deliberately run this after the ordinary workflow.  In
            # particular, its evidence cannot alter selection, repair inputs,
            # status, or the number of LLM calls made by the real pipeline.
            if eval_hidden_candidates:
                for index, candidate in enumerate(candidates):
                    if index == selected_index:
                        continue
                    candidate_hidden_evidence = self.sandbox.run(
                        candidate.candidate_code, [task.hidden_test]
                    )
                    self._attempt_from_evidence(candidate, candidate_hidden_evidence, visible=False)

            verification.completed_at = datetime.now(UTC)
            db.commit()
            db.refresh(verification)
            # Load the ordered history while the session is active so callers
            # can serialize it after the context manager closes.
            list(verification.attempts)
            return verification
