
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
    """Translate HumanEval's docstring examples into executable assertions."""
    assertions: list[str] = []

    for example in doctest.DocTestParser().get_examples(task.prompt):
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
            assertions.append(
                f"assert repr(({example.source.strip()})) == {expected!r}"
            )
        else:
            assertions.append(
                f"assert ({example.source.strip()}) == {value!r}"
            )

    return assertions


def visible_score(evidence: SandboxEvidence) -> int:
    """Number of individual visible tests that passed."""
    return sum(test.passed for test in evidence.tests)


def select_best_candidate(evidences: list[SandboxEvidence]) -> int:
    """Pick the highest visible score; max preserves first tie order."""
    if not evidences:
        raise ValueError("At least one candidate is required")

    return max(
        range(len(evidences)),
        key=lambda index: visible_score(evidences[index]),
    )


def _error_summary(evidence: SandboxEvidence) -> str | None:
    errors = [test.error for test in evidence.tests if test.error]

    if evidence.timed_out:
        errors.append("Sandbox wall-clock timeout")

    if evidence.stderr:
        errors.append(evidence.stderr)

    return "\n".join(errors) or None


# Test code and its output are untrusted prompt inputs.
_BUILTIN_EXCEPTION_NAMES = tuple(
    sorted(
        name
        for name, value in vars(builtins).items()
        if isinstance(value, type) and issubclass(value, BaseException)
    )
)


def _repair_evidence_summary(evidence: SandboxEvidence) -> str:
    """Return failure metadata without exposing test source or output."""
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
    def __init__(
        self,
        llm: LLMClient,
        sandbox: SandboxExecutor,
        session_factory,
        loader=None,
        verification_candidates: int | None = None,
        max_repair_attempts: int | None = None,
    ):
        self.llm = llm
        self.sandbox = sandbox
        self.session_factory = session_factory
        self.loader = loader or HumanEvalLoader()

        self.verification_candidates = (
            verification_candidates
            if verification_candidates is not None
            else settings.verification_candidates
        )

        self.max_repair_attempts = (
            max_repair_attempts
            if max_repair_attempts is not None
            else settings.max_repair_attempts
        )

    @staticmethod
    def _generation_prompt(task: Problem) -> str:
        return (
            "Complete only Python code for this HumanEval problem.\n"
            + task.prompt
        )

    @staticmethod
    def _repair_prompt(
        task: Problem,
        failed_code: str,
        evidence: SandboxEvidence,
    ) -> str:
        details = _repair_evidence_summary(evidence)

        return (
            "Return only repaired Python code for this HumanEval problem.\n\n"
            f"Problem:\n{task.prompt}\n\n"
            f"Failed candidate:\n{failed_code}\n\n"
            f"Hidden-test execution evidence:\n{details}"
        )

    @staticmethod
    def _attempt_from_evidence(
        attempt: Attempt,
        evidence: SandboxEvidence,
        *,
        visible: bool,
    ) -> None:
        if visible:
            attempt.passed_visible_tests = evidence.passed
        else:
            attempt.passed_hidden_tests = evidence.passed

        attempt.stdout = evidence.stdout
        attempt.stderr = evidence.stderr
        attempt.error_summary = _error_summary(evidence)
        attempt.duration_ms = evidence.duration_ms

    def run(
        self,
        task_id: str,
        *,
        trial_index: int = 0,
        eval_hidden_candidates: bool = False,
        session_id: int | None = None,
    ) -> VerificationSession:
        """Run one verified session without holding DB connections during external work."""

        if self.verification_candidates < 1:
            raise ValueError("verification_candidates must be at least 1")

        if self.max_repair_attempts < 0:
            raise ValueError("max_repair_attempts cannot be negative")

        task = self.loader.get(task_id)
        tests = visible_assertions(task)

        if not tests:
            raise RuntimeError(
                f"Task {task_id} has no executable visible tests"
            )

        # Create or retrieve the parent session.
        with self.session_factory() as db:
            if session_id is not None:
                verification = db.get(VerificationSession, session_id)

                if verification is None:
                    raise RuntimeError(
                        f"Pre-created session {session_id} not found in database"
                    )

                verification.status = VerificationStatus.running
                verification.current_stage = "initializing"
            else:
                verification = VerificationSession(
                    task_id=task_id,
                    trial_index=trial_index,
                    mode="verified",
                    source="humaneval",
                    status=VerificationStatus.running,
                    current_stage="initializing",
                )
                db.add(verification)
                db.flush()

            verification_id = verification.id
            db.commit()

        def _stage(stage: str) -> None:
            """Persist progress using a short-lived DB session."""
            with self.session_factory() as db:
                verification = db.get(
                    VerificationSession,
                    verification_id,
                )

                if verification is not None:
                    verification.current_stage = stage
                    db.commit()

        def _save_attempt(attempt: Attempt) -> int:
            """Save one attempt and return its database ID."""
            with self.session_factory() as db:
                db.add(attempt)
                db.flush()
                attempt_id = attempt.id
                db.commit()
                return attempt_id

        def _update_attempt(
            attempt_id: int,
            evidence: SandboxEvidence,
            *,
            visible: bool,
        ) -> None:
            """Update an existing attempt using a short-lived DB session."""
            with self.session_factory() as db:
                attempt = db.get(Attempt, attempt_id)

                if attempt is None:
                    raise RuntimeError(
                        f"Attempt {attempt_id} not found in database"
                    )

                self._attempt_from_evidence(
                    attempt,
                    evidence,
                    visible=visible,
                )
                db.commit()

        candidate_ids: list[int] = []
        candidate_codes: list[str] = []
        candidate_evidences: list[SandboxEvidence] = []

        _stage("generating_candidates")

        # Generate and verify candidates without holding DB connections.
        for index in range(self.verification_candidates):
            generation = self.llm.generate(
                self._generation_prompt(task)
            )
            code = extract_python_code(generation.code)

            _stage("running_visible_tests")
            evidence = self.sandbox.run(code, tests)

            attempt = Attempt(
                session_id=verification_id,
                phase=AttemptPhase.candidate,
                attempt_index=index,
                candidate_code=code,
                token_usage=generation.token_usage,
            )

            self._attempt_from_evidence(
                attempt,
                evidence,
                visible=True,
            )

            attempt_id = _save_attempt(attempt)

            candidate_ids.append(attempt_id)
            candidate_codes.append(code)
            candidate_evidences.append(evidence)

        # Select the best candidate using visible-test results.
        _stage("selecting_candidate")

        selected_index = select_best_candidate(candidate_evidences)
        selected_id = candidate_ids[selected_index]
        selected_code = candidate_codes[selected_index]

        with self.session_factory() as db:
            selected = db.get(Attempt, selected_id)

            if selected is None:
                raise RuntimeError(
                    f"Selected attempt {selected_id} not found"
                )

            selected.is_selected = True
            db.commit()

        # Run hidden tests on the selected candidate.
        _stage("running_hidden_tests")

        hidden_evidence = self.sandbox.run(
            selected_code,
            [task.hidden_test],
        )

        _update_attempt(
            selected_id,
            hidden_evidence,
            visible=False,
        )

        if hidden_evidence.passed:
            final_status = VerificationStatus.succeeded
        else:
            final_status = None

            last_code = selected_code
            last_evidence = hidden_evidence

            # Attempt repairs when hidden tests fail.
            for repair_index in range(self.max_repair_attempts):
                _stage("repairing")

                generation = self.llm.generate(
                    self._repair_prompt(
                        task,
                        last_code,
                        last_evidence,
                    )
                )

                repaired_code = extract_python_code(generation.code)

                _stage("running_hidden_tests")

                repair_evidence = self.sandbox.run(
                    repaired_code,
                    [task.hidden_test],
                )

                repair = Attempt(
                    session_id=verification_id,
                    phase=AttemptPhase.repair,
                    attempt_index=repair_index,
                    candidate_code=repaired_code,
                    token_usage=generation.token_usage,
                )

                self._attempt_from_evidence(
                    repair,
                    repair_evidence,
                    visible=False,
                )

                _save_attempt(repair)

                if repair_evidence.passed:
                    final_status = VerificationStatus.succeeded
                    break

                last_code = repaired_code
                last_evidence = repair_evidence

            if final_status is None:
                final_status = VerificationStatus.exhausted

        # Optional measurement-only evaluation of unselected candidates.
        # These results never affect selection or repair decisions.
        if eval_hidden_candidates:
            for index, candidate_code in enumerate(candidate_codes):
                if index == selected_index:
                    continue

                candidate_hidden_evidence = self.sandbox.run(
                    candidate_code,
                    [task.hidden_test],
                )

                _update_attempt(
                    candidate_ids[index],
                    candidate_hidden_evidence,
                    visible=False,
                )

        # Persist the final session state.
        _stage("completing")

        with self.session_factory() as db:
            verification = db.get(
                VerificationSession,
                verification_id,
            )

            if verification is None:
                raise RuntimeError(
                    f"Verification session {verification_id} not found"
                )

            verification.status = final_status
            verification.current_stage = None
            verification.completed_at = datetime.now(UTC)

            db.commit()
            db.refresh(verification)

            # Load attempts before the DB session closes.
            list(verification.attempts)

            return verification
