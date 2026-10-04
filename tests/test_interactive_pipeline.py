import traceback

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.interactive_pipeline import InteractivePipeline, pooled_assertions, top_level_function_name
from app.llm import Generation, LLMClient
from app.models import Base, VerificationStatus
from app.sandbox import SandboxEvidence, SandboxTestEvidence
import app.main as main


class SequencedLLM(LLMClient):
    def __init__(self, replies):
        self.replies, self.prompts = iter(replies), []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return Generation(next(self.replies), 7)


class RecordingSandbox:
    def __init__(self):
        self.calls = []

    def run(self, code, tests):
        self.calls.append((code, tests))
        passed = "good" in code
        results = [SandboxTestEvidence(f"test_{index}", passed, None if passed else "AssertionError")
                   for index, _ in enumerate(tests)]
        return SandboxEvidence(passed, False, "", "", 0, 1, results)


def pipeline(llm, sandbox, verification_candidates=2):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return InteractivePipeline(llm, sandbox, sessionmaker(bind=engine, expire_on_commit=False),
                               verification_candidates, 1)


def test_pooled_assertions_is_an_ordered_union():
    assert pooled_assertions([
        "assert add(1, 2) == 3\nassert add(0, 0) == 0",
        "Here are tests:\nassert add(1, 2) == 3\nassert add(-1, 1) == 0",
    ]) == ["assert add(1, 2) == 3", "assert add(0, 0) == 0", "assert add(-1, 1) == 0"]


def test_first_candidate_function_name_is_enforced_in_later_generation_and_all_test_prompts():
    llm = SequencedLLM([
        "def canonical(value): return value + 1  # good",
        "def another_name(value): return value + 1  # good",
        "def third_name(value): return value + 1  # good",
        "assert canonical(1) == 2",
        "assert canonical(2) == 3",
        "assert canonical(3) == 4",
    ])
    result = pipeline(llm, RecordingSandbox(), verification_candidates=3).run("Increment a number")

    assert top_level_function_name("def canonical(): pass") == "canonical"
    assert result.canonical_function_name == "canonical"
    assert result.canonical_name_note is None
    assert "function named exactly `canonical`" not in llm.prompts[0]
    assert all("function named exactly `canonical`" in prompt for prompt in llm.prompts[1:3])
    assert all("canonical function named exactly `canonical`" in prompt for prompt in llm.prompts[3:])
    assert result.oracle_tests == ["assert canonical(1) == 2", "assert canonical(2) == 3", "assert canonical(3) == 4"]


def test_unparseable_first_candidate_uses_current_prompt_behavior_and_records_note():
    llm = SequencedLLM([
        "def broken(:", "def later(): pass  # good",
        "assert 1 == 1", "assert 2 == 2",
    ])
    result = pipeline(llm, RecordingSandbox()).run("Do something")

    assert top_level_function_name("def broken(:") is None
    assert result.canonical_function_name is None
    assert result.canonical_name_note == (
        "Could not extract a top-level function name from the first candidate; "
        "cross-candidate function-name enforcement was not applied."
    )
    assert all("function named exactly" not in prompt for prompt in llm.prompts)


def test_self_generated_tests_are_pooled_and_shared_across_candidates():
    llm = SequencedLLM([
        "def good(): pass", "def bad(): pass",
        "assert good() is None\nassert 1 == 1", "assert 1 == 1\nassert 2 == 2",
    ])
    sandbox = RecordingSandbox()
    result = pipeline(llm, sandbox).run("Write good()")

    assert result.session.oracle_kind == "self_generated"
    assert result.oracle_tests == ["assert good() is None", "assert 1 == 1", "assert 2 == 2"]
    assert result.session.status == VerificationStatus.succeeded
    # Candidate runs and the selected re-check all receive precisely the same pooled oracle.
    assert all(tests == result.oracle_tests for _, tests in sandbox.calls)


def test_user_tests_are_verbatim_and_no_self_generated_tests_are_requested():
    supplied = ["assert add(2, 3) == 5", "assert add(-1, 1) == 0"]
    llm = SequencedLLM(["def good(): pass", "def bad(): pass"])
    sandbox = RecordingSandbox()
    result = pipeline(llm, sandbox).run("Implement add", tests=supplied)

    assert result.session.oracle_kind == "user_supplied"
    assert result.oracle_tests == supplied
    assert all(tests == supplied for _, tests in sandbox.calls)
    assert len(llm.prompts) == 2
    assert all("assert add(2, 3) == 5" not in prompt for prompt in llm.prompts)


def test_user_oracle_repair_prompt_redacts_assertion_and_expected_value():
    assertion = "assert add(2, 3) == 5"
    evidence = SandboxEvidence(False, False, assertion, "", 0, 1, [
        SandboxTestEvidence("test_0", False,
            f'Traceback:\\n  File "test_0.py", line 1\\n{assertion}\\nAssertionError: expected 5')
    ])

    prompt = InteractivePipeline._repair_prompt("Implement add", "def add(a, b): return 0", evidence)

    assert assertion not in prompt
    assert "expected 5" not in prompt
    assert "5" not in prompt
    assert prompt.endswith("1 of 1 tests failed; AssertionError raised.")


def test_invalid_user_assertion_is_returned_as_recorded_sandbox_failure(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "SessionLocal",
                        sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(main, "OpenAIClient",
                        lambda: SequencedLLM(["def reverse_string(value): return value[::-1]"]))
    monkeypatch.setattr(main.settings, "verification_candidates", 1)
    monkeypatch.setattr(main.settings, "max_repair_attempts", 0)

    class SyntaxReportingSandbox:
        def run(self, code, tests):
            compile(code, "candidate.py", "exec")
            results = []
            for index, test in enumerate(tests):
                try:
                    compile(test, f"test_{index}.py", "exec")
                except SyntaxError:
                    results.append(SandboxTestEvidence(
                        f"test_{index}", False, traceback.format_exc()))
                else:
                    results.append(SandboxTestEvidence(f"test_{index}", True, None))
            passed = bool(results) and all(item.passed for item in results)
            return SandboxEvidence(passed, False, "", "", 0, 1, results)

    monkeypatch.setattr(main, "SandboxExecutor", SyntaxReportingSandbox)
    response = TestClient(main.app).post("/interactive/run", json={
        "question": "Write reverse_string",
        "tests": ["assert reverse_string('abc') === ??? broken syntax"],
    })

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["session"]["status"] == "exhausted"
    assert payload["candidate_test_results"][0][0]["passed"] is False
    assert "SyntaxError" in payload["candidate_test_results"][0][0]["error"]
