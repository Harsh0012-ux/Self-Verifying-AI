import pytest
from app.sandbox import SandboxExecutor

pytestmark = pytest.mark.integration

@pytest.fixture
def executor():
    return SandboxExecutor(timeout_seconds=2)

def test_good_and_bad_candidates(executor):
    test = "assert add(2, 3) == 5"
    assert executor.run("def add(a, b): return a + b", [test]).passed
    bad = executor.run("def add(a, b): return a - b", [test])
    assert not bad.passed and not bad.tests[0].passed

def test_infinite_loop_is_killed(executor):
    evidence = executor.run("while True: pass", ["assert True"])
    assert evidence.timed_out and not evidence.passed

def test_subprocess_attempt_does_not_escape_or_hang(executor):
    evidence = executor.run("import os\nos.system('curl http://example.com')", ["assert True"])
    assert evidence.duration_ms < 3000
    assert evidence.exit_code in (0, None)

def test_zero_test_evidence_is_not_reported_as_passed(caplog):
    class FakeContainer:
        def wait(self, timeout):
            return {"StatusCode": 0}

        def logs(self, stdout, stderr):
            return b'{"results": []}'

        def remove(self, force):
            pass

    class FakeContainers:
        def run(self, *args, **kwargs):
            return FakeContainer()

    class FakeClient:
        containers = FakeContainers()

    evidence = SandboxExecutor(client=FakeClient()).run("def answer(): pass", [])

    assert not evidence.passed
    assert not evidence.tests
    assert "no test evidence" in caplog.text
