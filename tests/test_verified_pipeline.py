from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.dataset import HumanEvalLoader, Problem
from app.llm import Generation, LLMClient
from app.models import Attempt, Base, VerificationSession, VerificationStatus
from app.sandbox import SandboxEvidence, SandboxExecutor, SandboxTestEvidence
from app.verified_pipeline import VerifiedPipeline, select_best_candidate, visible_assertions


class Loader:
    def get(self, task_id):
        return Problem(task_id, '''def answer(x):
    """Double x.
    >>> answer(2)
    4
    """''', "answer", [">>> answer(2)"], "assert answer(2) == 4")


class SequencedLLM(LLMClient):
    def __init__(self, codes): self.codes, self.prompts = iter(codes), []
    def generate(self, prompt):
        self.prompts.append(prompt)
        return Generation(next(self.codes), 11)


class RecordingSandbox:
    def __init__(self, always_fail=False): self.calls, self.always_fail = [], always_fail
    def run(self, code, tests):
        self.calls.append((code, tests))
        hidden = "def check" in tests[0] or "assert answer" in tests[0]
        if hidden:
            passed = "return x * 2" in code and not self.always_fail
        else:
            # Deliberately make the candidate that overfits the lone visible
            # example win selection, so the repair path is exercised.
            passed = "return x + 2" in code and not self.always_fail
        result = SandboxTestEvidence("test_0", passed, None if passed else "AssertionError")
        return SandboxEvidence(passed, False, "ok", "", 0, 3.5, [result])


def evidence(*passed):
    return SandboxEvidence(all(passed), False, "", "", 0, 1, [
        SandboxTestEvidence(str(i), value, None) for i, value in enumerate(passed)
    ])


def test_selection_prefers_most_visible_passes_and_first_tie():
    assert select_best_candidate([evidence(True, False), evidence(True, True), evidence(True, True)]) == 1


def test_verified_pipeline_persists_candidates_and_repairs():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sandbox = RecordingSandbox()
    pipeline = VerifiedPipeline(SequencedLLM([
        "```python\ndef answer(x): return x + 2\n```",
        "def answer(x): return x * 2",
        "def answer(x): return x * 2",
    ]), sandbox, sessionmaker(bind=engine, expire_on_commit=False), Loader(), verification_candidates=2, max_repair_attempts=1)
    result = pipeline.run("HumanEval/test")
    assert result.status == VerificationStatus.succeeded
    assert len(result.attempts) == 3
    assert result.attempts[0].candidate_code.startswith("def answer")
    assert result.attempts[0].is_selected
    assert result.attempts[0].passed_hidden_tests is False
    assert result.attempts[2].passed_visible_tests is None and result.attempts[2].passed_hidden_tests is True
    with sessionmaker(bind=engine)() as db:
        assert db.query(VerificationSession).count() == 1
        assert db.query(Attempt).count() == 3


def test_repair_loop_stops_at_configured_limit():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sandbox = RecordingSandbox(always_fail=True)
    pipeline = VerifiedPipeline(SequencedLLM(["def answer(x): return x"] * 4), sandbox,
        sessionmaker(bind=engine, expire_on_commit=False), Loader(), verification_candidates=1, max_repair_attempts=2)
    result = pipeline.run("HumanEval/test")
    assert result.status == VerificationStatus.exhausted
    assert len(result.attempts) == 3
    assert [item.phase.value for item in result.attempts] == ["candidate", "repair", "repair"]
    assert len(sandbox.calls) == 4  # candidate visible + hidden, then two repairs


def test_eval_mode_logs_non_selected_hidden_results_without_changing_normal_path():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    codes = ["def answer(x): return x + 2", "def answer(x): return x * 2", "def answer(x): return x * 2"]
    normal_sandbox = RecordingSandbox()
    normal = VerifiedPipeline(SequencedLLM(codes), normal_sandbox, factory, Loader(),
        verification_candidates=2, max_repair_attempts=1).run("HumanEval/test", trial_index=7)
    assert normal.trial_index == 7
    assert len(normal_sandbox.calls) == 4
    assert normal.attempts[1].passed_hidden_tests is None

    instrumented_sandbox = RecordingSandbox()
    instrumented = VerifiedPipeline(SequencedLLM(codes), instrumented_sandbox, factory, Loader(),
        verification_candidates=2, max_repair_attempts=1).run(
            "HumanEval/test", trial_index=8, eval_hidden_candidates=True)
    # The normal decision/result history is unchanged; only one observational
    # hidden execution for the non-selected candidate is appended.
    assert instrumented.status == normal.status
    assert [a.phase for a in instrumented.attempts] == [a.phase for a in normal.attempts]
    assert [a.is_selected for a in instrumented.attempts] == [a.is_selected for a in normal.attempts]
    assert len(instrumented_sandbox.calls) == len(normal_sandbox.calls) + 1
    assert instrumented.attempts[1].is_selected is False
    assert instrumented.attempts[1].passed_hidden_tests is True


def test_real_wrong_candidate_fails_real_visible_assertion():
    task = HumanEvalLoader().get("HumanEval/0")
    assertions = visible_assertions(task)
    evidence = SandboxExecutor().run("def has_close_elements(numbers, threshold): return False", assertions)

    assert assertions
    assert not evidence.passed
    assert any(not test.passed for test in evidence.tests)


def test_humaneval_repair_prompt_redacts_hidden_test_source_but_keeps_failure_metadata():
    task = Loader().get("HumanEval/test")
    assertion = "assert add(2, 3) == 5"
    evidence = SandboxEvidence(False, False, assertion, "", 0, 1, [
        SandboxTestEvidence("test_0", False,
            f'Traceback:\\n  File "test_0.py", line 1\\n{assertion}\\nAssertionError: expected 5')
    ])

    prompt = VerifiedPipeline._repair_prompt(task, "def add(a, b): return 0", evidence)

    assert assertion not in prompt
    assert "expected 5" not in prompt
    assert "5" not in prompt
    assert prompt.endswith("1 of 1 tests failed; AssertionError raised.")
    # The established HumanEval prompt structure is otherwise unchanged.
    assert prompt.startswith("Return only repaired Python code for this HumanEval problem.\n\nProblem:\n")
    assert "\n\nFailed candidate:\ndef add(a, b): return 0\n\nHidden-test execution evidence:\n" in prompt
