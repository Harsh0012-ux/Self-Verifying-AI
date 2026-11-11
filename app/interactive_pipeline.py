
"""Interactive verification built from the verified pipeline's sandbox primitives.

Unlike HumanEval, a self-generated oracle is only a consistency check. The
caller receives that distinction explicitly through ``oracle_kind``.
"""

import ast
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.code_extraction import extract_python_code
from app.llm import LLMClient
from app.models import Attempt, AttemptPhase, VerificationSession, VerificationStatus
from app.sandbox import SandboxEvidence, SandboxExecutor
from app.verified_pipeline import (
    _repair_evidence_summary,
    select_best_candidate,
    VerifiedPipeline,
)


logger = logging.getLogger(__name__)


def top_level_function_name(code: str) -> str | None:
    """Return the first top-level function name, or None when unavailable."""
    try:
        module = ast.parse(code)
    except SyntaxError:
        return None

    for statement in module.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return statement.name

    return None


def pooled_assertions(proposals: list[str]) -> list[str]:
    """Return the ordered union of executable assertion lines from proposals."""
    pooled: list[str] = []
    seen: set[str] = set()

    for proposal in proposals:
        for raw_line in proposal.splitlines():
            line = raw_line.strip()

            if line.startswith("assert ") and line not in seen:
                pooled.append(line)
                seen.add(line)

    return pooled


@dataclass(frozen=True)
class InteractiveRun:
    session: VerificationSession
    oracle_tests: list[str]
    candidate_evidences: list[SandboxEvidence]
    selected_evidence: SandboxEvidence
    repair_evidences: list[SandboxEvidence]
    canonical_function_name: str | None
    canonical_name_note: str | None


class InteractivePipeline:
    def __init__(
        self,
        llm: LLMClient,
        sandbox: SandboxExecutor,
        session_factory,
        verification_candidates: int,
        max_repair_attempts: int,
    ):
        self.llm = llm
        self.sandbox = sandbox
        self.session_factory = session_factory
        self.verification_candidates = verification_candidates
        self.max_repair_attempts = max_repair_attempts

    @staticmethod
    def _generation_prompt(
        question: str,
        code: str | None,
        canonical_function_name: str | None = None,
    ) -> str:
        prompt = (
            "Return only Python code that solves this user coding request.\n\n"
            "Request:\n" + question
        )

        if canonical_function_name:
            prompt += (
                "\n\nFor cross-candidate compatibility, implement this as a "
                "function named exactly "
                f"`{canonical_function_name}`."
            )

        if code:
            prompt += "\n\nExisting code to fix or optimize:\n" + code

        return prompt

    @staticmethod
    def _test_prompt(
        question: str,
        candidate_code: str,
        canonical_function_name: str | None = None,
    ) -> str:
        prompt = (
            "Propose a few independent Python test assertions for this coding request. "
            "Return only one executable `assert ...` per line; no prose, Markdown, imports, or setup. "
            "These are consistency checks, not proof of correctness.\n\nRequest:\n"
            + question
            + "\n\nCandidate code being cross-checked:\n"
            + candidate_code
        )

        if canonical_function_name:
            prompt += (
                "\n\nEvery assertion must call the canonical function named exactly "
                f"`{canonical_function_name}`."
            )

        return prompt

    @staticmethod
    def _repair_prompt(
        question: str,
        failed_code: str,
        evidence: SandboxEvidence,
    ) -> str:
        details = _repair_evidence_summary(evidence)

        return (
            "Return only repaired Python code for this coding request.\n\n"
            f"Request:\n{question}\n\n"
            f"Failed candidate:\n{failed_code}\n\n"
            "Sandbox execution evidence (the test source is intentionally withheld):\n"
            f"{details}"
        )

    def run(
        self,
        question: str,
        *,
        code: str | None = None,
        tests: list[str] | None = None,
        session_id: int | None = None,
    ) -> InteractiveRun:
        """Run one interactive session without holding DB connections during external work."""

        if self.verification_candidates < 1:
            raise ValueError("verification_candidates must be at least 1")

        if self.max_repair_attempts < 0:
            raise ValueError("max_repair_attempts cannot be negative")

        if tests is not None and (
            not tests or any(not test.strip() for test in tests)
        ):
            raise ValueError(
                "tests must be a non-empty list of non-empty Python assertions"
            )

        # Mark an existing async session as running before external work.
        if session_id is not None:
            with self.session_factory() as db:
                verification = db.get(VerificationSession, session_id)

                if verification is None:
                    raise RuntimeError(
                        f"Pre-created session {session_id} not found in database"
                    )

                verification.status = VerificationStatus.running
                verification.current_stage = "initializing"
                db.commit()

        # All LLM generation happens outside database sessions.
        first_generation = self.llm.generate(
            self._generation_prompt(question, code)
        )

        first_candidate_code = extract_python_code(first_generation.code)
        canonical_function_name = top_level_function_name(
            first_candidate_code
        )

        canonical_name_note: str | None = None

        if canonical_function_name is None:
            canonical_name_note = (
                "Could not extract a top-level function name from the first "
                "candidate; cross-candidate function-name enforcement was "
                "not applied."
            )
            logger.warning(canonical_name_note)

        generations = [first_generation]
        candidate_codes = [first_candidate_code]

        for _ in range(1, self.verification_candidates):
            generation = self.llm.generate(
                self._generation_prompt(
                    question,
                    code,
                    canonical_function_name,
                )
            )

            generations.append(generation)
            candidate_codes.append(
                extract_python_code(generation.code)
            )

        if tests is None:
            proposals = [
                self.llm.generate(
                    self._test_prompt(
                        question,
                        candidate,
                        canonical_function_name,
                    )
                ).code
                for candidate in candidate_codes
            ]

            oracle_tests = pooled_assertions(proposals)
            oracle_kind = "self_generated"

            if not oracle_tests:
                raise RuntimeError(
                    "Candidates did not produce executable self-generated assertions"
                )
        else:
            # Preserve supplied oracle source verbatim.
            oracle_tests = list(tests)
            oracle_kind = "user_supplied"

        # Create the legacy session or update async session metadata.
        with self.session_factory() as db:
            if session_id is not None:
                verification = db.get(
                    VerificationSession,
                    session_id,
                )

                if verification is None:
                    raise RuntimeError(
                        f"Pre-created session {session_id} not found in database"
                    )

                verification.oracle_kind = oracle_kind
                verification.oracle_tests = oracle_tests
                verification.current_stage = "running_visible_tests"
            else:
                verification = VerificationSession(
                    task_id="interactive",
                    source="interactive",
                    question=question,
                    oracle_kind=oracle_kind,
                    oracle_tests=oracle_tests,
                    mode="interactive",
                    status=VerificationStatus.running,
                    current_stage="running_visible_tests",
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
            """Update an attempt using a short-lived DB session."""
            with self.session_factory() as db:
                attempt = db.get(Attempt, attempt_id)

                if attempt is None:
                    raise RuntimeError(
                        f"Attempt {attempt_id} not found in database"
                    )

                VerifiedPipeline._attempt_from_evidence(
                    attempt,
                    evidence,
                    visible=visible,
                )

                db.commit()

        candidate_ids: list[int] = []
        candidate_evidences: list[SandboxEvidence] = []

        # Run visible tests and persist each candidate independently.
        _stage("running_visible_tests")

        for index, (generation, candidate_code) in enumerate(
            zip(generations, candidate_codes)
        ):
            evidence = self.sandbox.run(
                candidate_code,
                oracle_tests,
            )

            attempt = Attempt(
                session_id=verification_id,
                phase=AttemptPhase.candidate,
                attempt_index=index,
                candidate_code=candidate_code,
                token_usage=generation.token_usage,
            )

            VerifiedPipeline._attempt_from_evidence(
                attempt,
                evidence,
                visible=True,
            )

            attempt_id = _save_attempt(attempt)

            candidate_ids.append(attempt_id)
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

        # Interactive hidden tests repeat the same oracle.
        # They are consistency checks, not independent proof.
        _stage("running_hidden_tests")

        selected_evidence = self.sandbox.run(
            selected_code,
            oracle_tests,
        )

        _update_attempt(
            selected_id,
            selected_evidence,
            visible=False,
        )

        repair_evidences: list[SandboxEvidence] = []

        if selected_evidence.passed:
            final_status = VerificationStatus.succeeded
        else:
            final_status = None

            last_code = selected_code
            last_evidence = selected_evidence

            for repair_index in range(self.max_repair_attempts):
                _stage("repairing")

                generation = self.llm.generate(
                    self._repair_prompt(
                        question,
                        last_code,
                        last_evidence,
                    )
                )

                repaired_code = extract_python_code(
                    generation.code
                )

                _stage("running_hidden_tests")

                repair_evidence = self.sandbox.run(
                    repaired_code,
                    oracle_tests,
                )

                repair = Attempt(
                    session_id=verification_id,
                    phase=AttemptPhase.repair,
                    attempt_index=repair_index,
                    candidate_code=repaired_code,
                    token_usage=generation.token_usage,
                )

                VerifiedPipeline._attempt_from_evidence(
                    repair,
                    repair_evidence,
                    visible=False,
                )

                _save_attempt(repair)
                repair_evidences.append(repair_evidence)

                if repair_evidence.passed:
                    final_status = VerificationStatus.succeeded
                    break

                last_code = repaired_code
                last_evidence = repair_evidence

            if final_status is None:
                final_status = VerificationStatus.exhausted

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

            # Load the ordered attempt history before the session closes.
            list(verification.attempts)

            result = InteractiveRun(
                verification,
                oracle_tests,
                candidate_evidences,
                selected_evidence,
                repair_evidences,
                canonical_function_name,
                canonical_name_note,
            )

            return result
