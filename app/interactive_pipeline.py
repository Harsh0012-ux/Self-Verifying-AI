"""Interactive verification built from the verified pipeline's sandbox primitives.

Unlike HumanEval, a self-generated oracle is only a consistency check.  The
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
from app.verified_pipeline import _repair_evidence_summary, select_best_candidate, VerifiedPipeline


logger = logging.getLogger(__name__)


def top_level_function_name(code: str) -> str | None:
    """Return the first top-level function name, or ``None`` when unavailable."""
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
    def __init__(self, llm: LLMClient, sandbox: SandboxExecutor, session_factory,
                 verification_candidates: int, max_repair_attempts: int):
        self.llm, self.sandbox, self.session_factory = llm, sandbox, session_factory
        self.verification_candidates = verification_candidates
        self.max_repair_attempts = max_repair_attempts

    @staticmethod
    def _generation_prompt(question: str, code: str | None,
                           canonical_function_name: str | None = None) -> str:
        prompt = "Return only Python code that solves this user coding request.\n\nRequest:\n" + question
        if canonical_function_name:
            prompt += (
                "\n\nFor cross-candidate compatibility, implement this as a function named exactly "
                f"`{canonical_function_name}`."
            )
        if code:
            prompt += "\n\nExisting code to fix or optimize:\n" + code
        return prompt

    @staticmethod
    def _test_prompt(question: str, candidate_code: str,
                     canonical_function_name: str | None = None) -> str:
        prompt = (
            "Propose a few independent Python test assertions for this coding request. "
            "Return only one executable `assert ...` per line; no prose, Markdown, imports, or setup. "
            "These are consistency checks, not proof of correctness.\n\nRequest:\n"
            + question + "\n\nCandidate code being cross-checked:\n" + candidate_code
        )
        if canonical_function_name:
            prompt += (
                "\n\nEvery assertion must call the canonical function named exactly "
                f"`{canonical_function_name}`."
            )
        return prompt

    @staticmethod
    def _repair_prompt(question: str, failed_code: str, evidence: SandboxEvidence) -> str:
        details = _repair_evidence_summary(evidence)
        return (
            "Return only repaired Python code for this coding request.\n\nRequest:\n"
            f"{question}\n\nFailed candidate:\n{failed_code}\n\n"
            f"Sandbox execution evidence (the test source is intentionally withheld):\n{details}"
        )

    def run(self, question: str, *, code: str | None = None,
            tests: list[str] | None = None) -> InteractiveRun:
        if self.verification_candidates < 1:
            raise ValueError("verification_candidates must be at least 1")
        if self.max_repair_attempts < 0:
            raise ValueError("max_repair_attempts cannot be negative")
        if tests is not None and (not tests or any(not test.strip() for test in tests)):
            raise ValueError("tests must be a non-empty list of non-empty Python assertions")

        first_generation = self.llm.generate(self._generation_prompt(question, code))
        first_candidate_code = extract_python_code(first_generation.code)
        canonical_function_name = top_level_function_name(first_candidate_code)
        canonical_name_note: str | None = None
        if canonical_function_name is None:
            canonical_name_note = (
                "Could not extract a top-level function name from the first candidate; "
                "cross-candidate function-name enforcement was not applied."
            )
            logger.warning(canonical_name_note)

        generations = [first_generation]
        candidate_codes = [first_candidate_code]
        for _ in range(1, self.verification_candidates):
            generation = self.llm.generate(self._generation_prompt(
                question, code, canonical_function_name))
            generations.append(generation)
            candidate_codes.append(extract_python_code(generation.code))
        if tests is None:
            proposals = [self.llm.generate(self._test_prompt(
                question, candidate, canonical_function_name)).code
                         for candidate in candidate_codes]
            oracle_tests = pooled_assertions(proposals)
            oracle_kind = "self_generated"
            if not oracle_tests:
                raise RuntimeError("Candidates did not produce executable self-generated assertions")
        else:
            # Preserve supplied oracle source verbatim; it is never sent in a
            # candidate-generation or repair prompt.
            oracle_tests = list(tests)
            oracle_kind = "user_supplied"

        with self.session_factory() as db:
            verification = VerificationSession(
                task_id="interactive", source="interactive", question=question,
                oracle_kind=oracle_kind, oracle_tests=oracle_tests,
                status=VerificationStatus.running,
            )
            db.add(verification)
            db.flush()

            candidates: list[Attempt] = []
            candidate_evidences: list[SandboxEvidence] = []
            for index, (generation, candidate_code) in enumerate(zip(generations, candidate_codes)):
                evidence = self.sandbox.run(candidate_code, oracle_tests)
                attempt = Attempt(session_id=verification.id, phase=AttemptPhase.candidate,
                    attempt_index=index, candidate_code=candidate_code, token_usage=generation.token_usage)
                VerifiedPipeline._attempt_from_evidence(attempt, evidence, visible=True)
                db.add(attempt)
                candidates.append(attempt)
                candidate_evidences.append(evidence)

            selected_index = select_best_candidate(candidate_evidences)
            selected = candidates[selected_index]
            selected.is_selected = True
            selected_evidence = self.sandbox.run(selected.candidate_code, oracle_tests)
            VerifiedPipeline._attempt_from_evidence(selected, selected_evidence, visible=False)
            repair_evidences: list[SandboxEvidence] = []

            if selected_evidence.passed:
                verification.status = VerificationStatus.succeeded
            else:
                last_code, last_evidence = selected.candidate_code, selected_evidence
                for repair_index in range(self.max_repair_attempts):
                    generation = self.llm.generate(self._repair_prompt(question, last_code, last_evidence))
                    repaired_code = extract_python_code(generation.code)
                    repair_evidence = self.sandbox.run(repaired_code, oracle_tests)
                    repair = Attempt(session_id=verification.id, phase=AttemptPhase.repair,
                        attempt_index=repair_index, candidate_code=repaired_code,
                        token_usage=generation.token_usage)
                    VerifiedPipeline._attempt_from_evidence(repair, repair_evidence, visible=False)
                    db.add(repair)
                    repair_evidences.append(repair_evidence)
                    if repair_evidence.passed:
                        verification.status = VerificationStatus.succeeded
                        break
                    last_code, last_evidence = repaired_code, repair_evidence
                else:
                    verification.status = VerificationStatus.exhausted

            verification.completed_at = datetime.now(UTC)
            db.commit()
            db.refresh(verification)
            list(verification.attempts)
            return InteractiveRun(verification, oracle_tests, candidate_evidences,
                selected_evidence, repair_evidences, canonical_function_name, canonical_name_note)
