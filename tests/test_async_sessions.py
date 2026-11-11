"""
Tests for the asynchronous /sessions workflow.

All LLM and Docker dependencies are mocked.
PostgreSQL is not required: tests use an in-memory SQLite database via the
existing test helpers.

Tests that cannot run without Docker or a live API are marked @pytest.mark.integration
and are excluded from the CI `pytest -m "not integration"` command.
"""
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from threading import BoundedSemaphore
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    Attempt,
    AttemptPhase,
    Base,
    Run,
    RunMode,
    TestResult,
    VerificationSession,
    VerificationStatus,
)


# ---------------------------------------------------------------------------
# Shared in-memory SQLite fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _restore_main_globals():
    """Restore app.main module-level singletons after every test.

    Prevents two categories of bleed:
    1. SessionLocal patch from one test leaking into the next test's lifespan
       orphan-cleanup, which runs with the module's current SessionLocal.
    2. ThreadPoolExecutor being shut down by one TestClient.__exit__ and then
       silently broken for the next TestClient invocation.
    """
    from concurrent.futures import ThreadPoolExecutor
    import app.main as m
    original_sl = m.SessionLocal
    yield
    m.SessionLocal = original_sl
    # Replace a shut-down executor so the next test gets a fresh one.
    if m._executor._shutdown:
        m._executor = ThreadPoolExecutor(max_workers=m._MAX_WORKERS)
        m._submission_slots = BoundedSemaphore(
            m._MAX_WORKERS + m._MAX_QUEUED
    )

@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def SessionLocal(db_engine):
    return sessionmaker(bind=db_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Minimal sandbox / LLM mocks
# ---------------------------------------------------------------------------

def _make_evidence(passed: bool, tests_count: int = 1):
    """Return a mock SandboxEvidence with predictable structure."""
    ev = MagicMock()
    ev.passed = passed
    ev.stdout = (
        '{"results": [{"name": "test_0", "passed": '
        + str(passed).lower()
        + ', "error": null}], "duration_ms": 50}'
    )
    ev.stderr = ""
    ev.exit_code = 0
    ev.duration_ms = 50.0
    ev.timed_out = False
    test = MagicMock()
    test.passed = passed
    test.name = "test_0"
    test.stdout = ""
    test.stderr = ""
    test.error = None
    ev.tests = [test] * tests_count
    return ev


def _make_generation(code: str = "def f(): pass", tokens: int = 100):
    gen = MagicMock()
    gen.code = code
    gen.token_usage = tokens
    return gen


# ---------------------------------------------------------------------------
# FastAPI test client factory
# ---------------------------------------------------------------------------

def _make_client(SessionLocal):
    """
    Return a TestClient with the app patched to use the in-memory SessionLocal.
    The lifespan handler (orphan cleanup) runs on each client __enter__.
    """
    import app.main as main_module

    # Patch SessionLocal in every module that uses it
    with (
        patch.object(main_module, "SessionLocal", SessionLocal),
        patch("app.pipeline.SessionLocal", SessionLocal, create=True),
        patch("app.verified_pipeline.SessionLocal", SessionLocal, create=True),
        patch("app.interactive_pipeline.SessionLocal", SessionLocal, create=True),
    ):
        # We also need to patch the SessionLocal that _run_pipeline_in_thread
        # closes over via the closure — it re-imports from app.main so the
        # patch above covers it.
        with TestClient(main_module.app, raise_server_exceptions=True) as client:
            yield client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _poll_until_terminal(client, session_id: int, *, timeout: float = 10.0) -> dict:
    """Poll GET /sessions/{id} until the status is not pending or running."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        if data["status"] not in ("pending", "running"):
            return data
        time.sleep(0.05)
    raise TimeoutError(f"Session {session_id} did not reach terminal state within {timeout}s")


# ===========================================================================
# 1. Session creation — HTTP 202, correct initial fields
# ===========================================================================

class TestSessionCreation:
    def test_verified_returns_202(self, SessionLocal):
        loader = MagicMock()
        loader.get.return_value = MagicMock(
            prompt="# problem", hidden_test="assert True"
        )
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "HumanEvalLoader", return_value=loader):
            with TestClient(m.app) as client:
                resp = client.post("/sessions", json={"mode": "verified", "task_id": "HumanEval/0"})
        assert resp.status_code == 202
        body = resp.json()
        assert "id" in body
        assert body["status"] == "pending"

    def test_baseline_returns_202(self, SessionLocal):
        loader = MagicMock()
        loader.get.return_value = MagicMock(prompt="# p", hidden_test="assert True")
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "HumanEvalLoader", return_value=loader), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"):
            with TestClient(m.app) as client:
                resp = client.post("/sessions", json={"mode": "baseline", "task_id": "HumanEval/0"})
        assert resp.status_code == 202
        assert resp.json()["status"] == "pending"

    def test_interactive_returns_202(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader"):
            with TestClient(m.app) as client:
                resp = client.post(
                    "/sessions",
                    json={"mode": "interactive", "question": "Write an add function"},
                )
        assert resp.status_code == 202
        assert resp.json()["status"] == "pending"

    def test_verified_missing_task_id_is_422(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                resp = client.post("/sessions", json={"mode": "verified"})
        assert resp.status_code == 422

    def test_interactive_missing_question_is_422(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                resp = client.post("/sessions", json={"mode": "interactive"})
        assert resp.status_code == 422

    def test_unknown_task_id_returns_404(self, SessionLocal):
        loader = MagicMock()
        loader.get.side_effect = KeyError("HumanEval/999")
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "HumanEvalLoader", return_value=loader):
            with TestClient(m.app) as client:
                resp = client.post(
                    "/sessions", json={"mode": "verified", "task_id": "HumanEval/999"}
                )
        assert resp.status_code == 404

    def test_session_record_created_in_db(self, SessionLocal, db_engine):
        loader = MagicMock()
        loader.get.return_value = MagicMock(prompt="# p", hidden_test="assert True")
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "HumanEvalLoader", return_value=loader), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"):
            with TestClient(m.app) as client:
                resp = client.post(
                    "/sessions", json={"mode": "verified", "task_id": "HumanEval/0"}
                )
        session_id = resp.json()["id"]
        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s is not None
            assert s.mode == "verified"
            assert s.task_id == "HumanEval/0"


# ===========================================================================
# 2. Status transitions
# ===========================================================================

class TestStatusTransitions:

    # Minimal prompt that visible_assertions() can extract an assertion from
    _PROMPT_WITH_DOCTEST = (
        'def answer(x):\n'
        '    """Double x.\n'
        '    >>> answer(2)\n'
        '    4\n'
        '    """\n'
    )

    def _run_verified_in_thread(self, SessionLocal, session_id: int,
                                 task_id: str, passed: bool):
        """
        Directly call _run_pipeline_in_thread with fully mocked dependencies
        so the thread completes synchronously.
        """
        loader = MagicMock()
        loader.get.return_value = MagicMock(
            prompt=self._PROMPT_WITH_DOCTEST,
            hidden_test="assert answer(2) == 4",
        )
        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(passed)
        llm = MagicMock()
        llm.generate.return_value = _make_generation("def answer(x): return x*2")

        import app.main as m
        from app.verified_pipeline import VerifiedPipeline
        real_pipeline = VerifiedPipeline(llm, sandbox, SessionLocal, loader, 1, 0)
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "VerifiedPipeline", return_value=real_pipeline), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader", return_value=loader):
            m._run_pipeline_in_thread(session_id, "verified", task_id,
                                      None, None, None)

    def test_succeeded_transition(self, SessionLocal, db_engine):
        # Create a pending session manually.
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        self._run_verified_in_thread(SessionLocal, session_id, "HumanEval/0", passed=True)

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.status == VerificationStatus.succeeded
            assert s.completed_at is not None
            assert s.error_message is None

    def test_exhausted_transition_when_all_fail(self, SessionLocal):
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        loader = MagicMock()
        loader.get.return_value = MagicMock(
            prompt=self._PROMPT_WITH_DOCTEST,
            hidden_test="assert answer(2) == 4",
        )
        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(False)
        llm = MagicMock()
        llm.generate.return_value = _make_generation("def answer(x): return 0")

        import app.main as m
        from app.verified_pipeline import VerifiedPipeline
        pipeline = VerifiedPipeline(llm, sandbox, SessionLocal, loader, 1, 0)
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "VerifiedPipeline", return_value=pipeline), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader", return_value=loader):
            m._run_pipeline_in_thread(session_id, "verified", "HumanEval/0",
                                       None, None, None)

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.status == VerificationStatus.exhausted
            assert s.completed_at is not None

    def test_failed_transition_on_exception(self, SessionLocal):
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        import app.main as m

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated LLM failure")

        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader"), \
             patch.object(m, "VerifiedPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = _boom
            m._run_pipeline_in_thread(session_id, "verified", "HumanEval/0",
                                       None, None, None)

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.status == VerificationStatus.failed
            assert s.error_message is not None
            assert "RuntimeError" in s.error_message
            assert s.completed_at is not None
            # Must not expose raw exception details beyond type + 200 chars
            assert len(s.error_message) <= 300  # generous bound

    def test_error_message_does_not_contain_api_key(self, SessionLocal):
        """Exception messages must be sanitised — no credentials leak."""
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        import app.main as m

        FAKE_KEY = "sk-secret-api-key-should-not-appear"

        def _boom(*args, **kwargs):
            raise RuntimeError(f"Request failed with key={FAKE_KEY}")

        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader"), \
             patch.object(m, "VerifiedPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = _boom
            m._run_pipeline_in_thread(session_id, "verified", "HumanEval/0",
                                       None, None, None)

            with SessionLocal() as db:
                s = db.get(VerificationSession, session_id)
                assert s.error_message is not None
                assert FAKE_KEY not in s.error_message
                assert "RuntimeError" in s.error_message


# ===========================================================================
# 3. Worker exception / failed session persistence
# ===========================================================================

class TestWorkerExceptions:

    def test_failed_session_persisted_not_lost(self, SessionLocal):
        """When the worker raises, the session must still be in the DB."""
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader"), \
             patch.object(m, "VerifiedPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = Exception("docker gone")
            m._run_pipeline_in_thread(session_id, "verified", "HumanEval/0",
                                       None, None, None)

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s is not None, "Session was lost after worker exception"
            assert s.status == VerificationStatus.failed

    def test_already_succeeded_not_overwritten_by_exception(self, SessionLocal):
        """If pipeline succeeds then raises during cleanup, don't overwrite succeeded."""
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.succeeded,
                completed_at=datetime.now(UTC),
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        import app.main as m
        # Simulate exception AFTER pipeline already set succeeded
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader"), \
             patch.object(m, "VerifiedPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = Exception("late crash")
            # Manually set it succeeded first, then trigger the exception path
            m._run_pipeline_in_thread(session_id, "verified", "HumanEval/0",
                                       None, None, None)

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            # succeeded must not have been downgraded to failed
            assert s.status == VerificationStatus.succeeded


# ===========================================================================
# 4. Session retrieval
# ===========================================================================

class TestSessionRetrieval:

    def _make_session(self, db, **kwargs):
        s = VerificationSession(
            task_id=kwargs.get("task_id", "HumanEval/0"),
            mode=kwargs.get("mode", "verified"),
            source=kwargs.get("source", "humaneval"),
            status=kwargs.get("status", VerificationStatus.pending),
            question=kwargs.get("question"),
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s

    def test_get_session_returns_200(self, SessionLocal):
        with SessionLocal() as db:
            s = self._make_session(db)
            session_id = s.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                resp = client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200

    def test_get_unknown_session_returns_404(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                resp = client.get("/sessions/99999")
        assert resp.status_code == 404

    def test_response_fields_present(self, SessionLocal):
        with SessionLocal() as db:
            s = self._make_session(db, status=VerificationStatus.succeeded,
                                    mode="verified")
            session_id = s.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get(f"/sessions/{session_id}").json()
        for field in ("id", "mode", "task_id", "status", "current_stage",
                      "created_at", "completed_at", "error_message",
                      "attempts", "run", "answer_attempt_id"):
            assert field in body, f"Missing field: {field}"

    def test_response_has_oracle_fields_for_interactive(self, SessionLocal):
        with SessionLocal() as db:
            s = self._make_session(db, mode="interactive", source="interactive",
                                    task_id="interactive",
                                    status=VerificationStatus.succeeded,
                                    question="write add function")
            s.oracle_kind = "user_supplied"
            s.oracle_tests = ["assert add(1,2)==3"]
            db.commit()
            session_id = s.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get(f"/sessions/{session_id}").json()
        assert body["oracle_kind"] == "user_supplied"
        assert body["oracle_tests"] == ["assert add(1,2)==3"]

    def test_attempts_returned_with_evidence(self, SessionLocal):
        with SessionLocal() as db:
            s = self._make_session(db, status=VerificationStatus.succeeded)
            attempt = Attempt(
                session_id=s.id, phase=AttemptPhase.candidate, attempt_index=0,
                candidate_code="def f(): pass",
                passed_visible_tests=True, passed_hidden_tests=True,
                is_selected=True,
                stdout='{"results":[{"name":"t0","passed":true,"error":null}],"duration_ms":40}',
                stderr="",
            )
            db.add(attempt)
            db.commit()
            session_id = s.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get(f"/sessions/{session_id}").json()
        assert len(body["attempts"]) == 1
        ev = body["attempts"][0]["test_evidence"]
        assert isinstance(ev, list)
        assert ev[0]["name"] == "t0"
        assert ev[0]["passed"] is True

    def test_unparseable_stdout_gives_null_evidence(self, SessionLocal):
        with SessionLocal() as db:
            s = self._make_session(db, status=VerificationStatus.succeeded)
            attempt = Attempt(
                session_id=s.id, phase=AttemptPhase.candidate, attempt_index=0,
                candidate_code="def f(): pass",
                passed_visible_tests=True, passed_hidden_tests=True,
                is_selected=True, stdout="not json at all", stderr="",
            )
            db.add(attempt)
            db.commit()
            session_id = s.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get(f"/sessions/{session_id}").json()
        # Must be null, never an invented value
        assert body["attempts"][0]["test_evidence"] is None

    def test_raw_stdout_not_exposed(self, SessionLocal):
        """The raw runner JSON line must not appear in a named 'stdout' field."""
        raw_runner_output = '{"results":[],"duration_ms":10}'
        with SessionLocal() as db:
            s = self._make_session(db)
            attempt = Attempt(
                session_id=s.id, phase=AttemptPhase.candidate, attempt_index=0,
                candidate_code="def f(): pass",
                passed_visible_tests=False, is_selected=False,
                stdout=raw_runner_output, stderr="",
            )
            db.add(attempt)
            db.commit()
            session_id = s.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get(f"/sessions/{session_id}").json()
        attempt_body = body["attempts"][0]
        # attempt_detail must not include a 'stdout' key
        assert "stdout" not in attempt_body, (
            "Raw runner stdout must not be exposed directly in the async API response"
        )

    def test_baseline_run_returned_in_response(self, SessionLocal):
        with SessionLocal() as db:
            s = self._make_session(db, mode="baseline",
                                    status=VerificationStatus.succeeded)
            run = Run(
                task_id="HumanEval/0", mode=RunMode.baseline,
                candidate_code="def f(): pass", hidden_passed=True,
                duration_ms=100.0, token_usage=50, session_id=s.id,
            )
            db.add(run)
            db.commit()
            session_id = s.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get(f"/sessions/{session_id}").json()
        assert body["run"] is not None
        assert body["run"]["hidden_passed"] is True
        assert body["run"]["candidate_code"] == "def f(): pass"

    def test_answer_attempt_id_set_when_succeeded(self, SessionLocal):
        with SessionLocal() as db:
            s = self._make_session(db, status=VerificationStatus.succeeded)
            attempt = Attempt(
                session_id=s.id, phase=AttemptPhase.candidate, attempt_index=0,
                candidate_code="def f(): pass",
                passed_visible_tests=True, passed_hidden_tests=True,
                is_selected=True, stdout="", stderr="",
            )
            db.add(attempt)
            db.commit()
            db.refresh(attempt)
            session_id = s.id
            attempt_id = attempt.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get(f"/sessions/{session_id}").json()
        assert body["answer_attempt_id"] == attempt_id

    def test_answer_attempt_id_null_when_pending(self, SessionLocal):
        with SessionLocal() as db:
            s = self._make_session(db, status=VerificationStatus.pending)
            session_id = s.id
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get(f"/sessions/{session_id}").json()
        assert body["answer_attempt_id"] is None


# ===========================================================================
# 5. Session history / pagination
# ===========================================================================

class TestSessionHistory:

    def _populate(self, SessionLocal, n: int = 5):
        ids = []
        with SessionLocal() as db:
            for i in range(n):
                s = VerificationSession(
                    task_id=f"HumanEval/{i}", mode="verified", source="humaneval",
                    status=VerificationStatus.succeeded,
                )
                db.add(s)
                db.flush()
                ids.append(s.id)
            db.commit()
        return ids

    def test_list_returns_200(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                resp = client.get("/sessions")
        assert resp.status_code == 200

    def test_pagination_fields_present(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get("/sessions").json()
        for field in ("total", "offset", "limit", "sessions"):
            assert field in body

    def test_default_limit_is_20(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get("/sessions").json()
        assert body["limit"] == 20

    def test_offset_pagination(self, SessionLocal):
        self._populate(SessionLocal, 5)
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                page1 = client.get("/sessions?limit=3&offset=0").json()
                page2 = client.get("/sessions?limit=3&offset=3").json()
        ids1 = {s["id"] for s in page1["sessions"]}
        ids2 = {s["id"] for s in page2["sessions"]}
        assert ids1.isdisjoint(ids2), "Pages must not overlap"

    def test_total_count_accurate(self, SessionLocal):
        self._populate(SessionLocal, 4)
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get("/sessions?limit=1").json()
        assert body["total"] >= 4

    def test_filter_by_mode(self, SessionLocal):
        with SessionLocal() as db:
            for mode in ("baseline", "verified", "interactive"):
                db.add(VerificationSession(
                    task_id="HumanEval/0", mode=mode,
                    source="humaneval" if mode != "interactive" else "interactive",
                    status=VerificationStatus.succeeded,
                ))
            db.commit()
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get("/sessions?mode=baseline").json()
        assert all(s["mode"] == "baseline" for s in body["sessions"])

    def test_filter_by_status(self, SessionLocal):
        with SessionLocal() as db:
            for status in (VerificationStatus.succeeded, VerificationStatus.failed):
                db.add(VerificationSession(
                    task_id="HumanEval/0", mode="verified", source="humaneval",
                    status=status,
                ))
            db.commit()
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                body = client.get("/sessions?status=failed").json()
        assert all(s["status"] == "failed" for s in body["sessions"])

    def test_limit_capped_at_100(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app) as client:
                resp = client.get("/sessions?limit=200")
        assert resp.status_code == 422  # FastAPI rejects gt=100


# ===========================================================================
# 6. Progress-stage persistence
# ===========================================================================

class TestProgressStages:

    # Minimal prompt that visible_assertions() can extract an assertion from
    _PROMPT_WITH_DOCTEST = (
        'def answer(x):\n'
        '    """Double x.\n'
        '    >>> answer(2)\n'
        '    4\n'
        '    """\n'
    )

    def test_stage_updated_during_pipeline(self, SessionLocal):
        """Stages must be committed incrementally, not just at the end."""
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        stages_seen = []

        # Wrap SessionLocal to record the current_stage value at each commit.
        original_sf = SessionLocal

        class _TrackingFactory:
            def __call__(self):
                return _TrackingSession(original_sf())

        class _TrackingSession:
            def __init__(self, inner):
                self._inner = inner

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self._inner.__exit__(*args)

            def commit(self):
                s = self._inner.get(VerificationSession, session_id)
                if s and s.current_stage:
                    stages_seen.append(s.current_stage)
                return self._inner.commit()

            def __getattr__(self, name):
                return getattr(self._inner, name)

        tracking_sf = _TrackingFactory()

        loader = MagicMock()
        loader.get.return_value = MagicMock(
            prompt=self._PROMPT_WITH_DOCTEST,
            hidden_test="assert answer(2) == 4",
        )
        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(True)
        llm = MagicMock()
        llm.generate.return_value = _make_generation("def answer(x): return x*2")

        from app.verified_pipeline import VerifiedPipeline
        pipeline = VerifiedPipeline(llm, sandbox, tracking_sf, loader, 1, 0)
        pipeline.run("HumanEval/0", session_id=session_id)

        # At minimum these stages should have been committed
        assert "generating_candidates" in stages_seen or "initializing" in stages_seen

    def test_stage_is_null_on_completion(self, SessionLocal):
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        loader = MagicMock()
        loader.get.return_value = MagicMock(
            prompt=self._PROMPT_WITH_DOCTEST,
            hidden_test="assert answer(2) == 4",
        )
        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(True)
        llm = MagicMock()
        llm.generate.return_value = _make_generation("def answer(x): return x*2")

        from app.verified_pipeline import VerifiedPipeline
        VerifiedPipeline(llm, sandbox, SessionLocal, loader, 1, 0).run(
            "HumanEval/0", session_id=session_id
        )

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.current_stage is None


# ===========================================================================
# 7. Baseline parent-session lifecycle
# ===========================================================================

class TestBaselineSessionLifecycle:

    def test_baseline_pipeline_links_run_to_session(self, SessionLocal):
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="baseline", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        loader = MagicMock()
        loader.get.return_value = MagicMock(
            prompt="# problem", hidden_test="assert True"
        )
        sandbox = MagicMock()
        ev = _make_evidence(True)
        sandbox.run.return_value = ev
        llm = MagicMock()
        llm.generate.return_value = _make_generation("def f(): pass")

        from app.pipeline import BaselinePipeline
        run = BaselinePipeline(llm, sandbox, SessionLocal, loader).run(
            "HumanEval/0", session_id=session_id
        )

        assert run.session_id == session_id

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.status in (
                VerificationStatus.succeeded, VerificationStatus.exhausted
            )
            assert s.completed_at is not None

    def test_baseline_session_succeeded_when_hidden_passes(self, SessionLocal):
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="baseline", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        loader = MagicMock()
        loader.get.return_value = MagicMock(prompt="# p", hidden_test="assert True")
        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(True)
        llm = MagicMock()
        llm.generate.return_value = _make_generation()

        from app.pipeline import BaselinePipeline
        BaselinePipeline(llm, sandbox, SessionLocal, loader).run(
            "HumanEval/0", session_id=session_id
        )

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.status == VerificationStatus.succeeded

    def test_baseline_session_exhausted_when_hidden_fails(self, SessionLocal):
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="HumanEval/0", mode="baseline", source="humaneval",
                status=VerificationStatus.pending,
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        loader = MagicMock()
        loader.get.return_value = MagicMock(prompt="# p", hidden_test="assert False")
        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(False)
        llm = MagicMock()
        llm.generate.return_value = _make_generation()

        from app.pipeline import BaselinePipeline
        BaselinePipeline(llm, sandbox, SessionLocal, loader).run(
            "HumanEval/0", session_id=session_id
        )

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.status == VerificationStatus.exhausted


# ===========================================================================
# 8. Interactive oracle metadata
# ===========================================================================

class TestInteractiveOracle:

    def test_oracle_kind_persisted(self, SessionLocal):
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="interactive", mode="interactive", source="interactive",
                status=VerificationStatus.pending, question="write add",
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(True)
        llm = MagicMock()
        llm.generate.return_value = _make_generation("def add(a,b): return a+b")

        from app.interactive_pipeline import InteractivePipeline
        result = InteractivePipeline(llm, sandbox, SessionLocal, 1, 0).run(
            "write add",
            tests=["assert add(1,2)==3"],
            session_id=session_id,
        )

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.oracle_kind == "user_supplied"
            assert s.oracle_tests == ["assert add(1,2)==3"]

    def test_self_generated_oracle_kind(self, SessionLocal):
        with SessionLocal() as db:
            s = VerificationSession(
                task_id="interactive", mode="interactive", source="interactive",
                status=VerificationStatus.pending, question="write add",
            )
            db.add(s)
            db.commit()
            db.refresh(s)
            session_id = s.id

        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(True)

        # LLM returns a test-proposal that includes an assert line.
        def _gen(prompt, **_):
            g = MagicMock()
            if "assertion" in prompt.lower() or "test" in prompt.lower():
                g.code = "assert add(1,2)==3"
            else:
                g.code = "def add(a,b): return a+b"
            g.token_usage = 50
            return g

        llm = MagicMock()
        llm.generate.side_effect = _gen

        from app.interactive_pipeline import InteractivePipeline
        result = InteractivePipeline(llm, sandbox, SessionLocal, 1, 0).run(
            "write add",
            tests=None,  # trigger self-generation
            session_id=session_id,
        )

        with SessionLocal() as db:
            s = db.get(VerificationSession, session_id)
            assert s.oracle_kind == "self_generated"


# ===========================================================================
# 9. Orphan session recovery
# ===========================================================================

class TestOrphanRecovery:

    def test_orphaned_running_sessions_marked_failed_on_startup(self, SessionLocal):
        # Create sessions in various states before "restarting"
        with SessionLocal() as db:
            orphan1 = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.running,
            )
            orphan2 = VerificationSession(
                task_id="HumanEval/1", mode="verified", source="humaneval",
                status=VerificationStatus.pending,
            )
            safe = VerificationSession(
                task_id="HumanEval/2", mode="verified", source="humaneval",
                status=VerificationStatus.succeeded,
            )
            db.add_all([orphan1, orphan2, safe])
            db.commit()
            ids = (orphan1.id, orphan2.id, safe.id)

        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app):
                # lifespan runs on __enter__
                pass

        with SessionLocal() as db:
            o1 = db.get(VerificationSession, ids[0])
            o2 = db.get(VerificationSession, ids[1])
            s  = db.get(VerificationSession, ids[2])
            assert o1.status == VerificationStatus.failed
            assert o2.status == VerificationStatus.failed
            assert s.status  == VerificationStatus.succeeded  # untouched
            assert "restarted" in (o1.error_message or "").lower()

    def test_orphans_have_completed_at_set(self, SessionLocal):
        with SessionLocal() as db:
            orphan = VerificationSession(
                task_id="HumanEval/0", mode="verified", source="humaneval",
                status=VerificationStatus.running,
            )
            db.add(orphan)
            db.commit()
            db.refresh(orphan)
            orphan_id = orphan.id

        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app):
                pass

        with SessionLocal() as db:
            s = db.get(VerificationSession, orphan_id)
            assert s.completed_at is not None


# ===========================================================================
# 10. Executor submission failure
# ===========================================================================

class TestExecutorFailure:

    def test_submission_failure_marks_session_failed(self, SessionLocal):
        loader = MagicMock()
        loader.get.return_value = MagicMock(prompt="# p", hidden_test="assert True")
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "HumanEvalLoader", return_value=loader), \
             patch.object(m._executor, "submit", side_effect=RuntimeError("executor shut down")):
            with TestClient(m.app) as client:
                resp = client.post(
                    "/sessions", json={"mode": "verified", "task_id": "HumanEval/0"}
                )
        assert resp.status_code == 503

    def test_submission_failure_session_has_failed_status_in_db(self, SessionLocal):
        loader = MagicMock()
        loader.get.return_value = MagicMock(prompt="# p", hidden_test="assert True")
        import app.main as m
        # Capture the session id from the response (even on 503 we return it)
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "HumanEvalLoader", return_value=loader), \
             patch.object(m._executor, "submit", side_effect=RuntimeError("executor shut down")):
            with TestClient(m.app) as client:
                resp = client.post(
                    "/sessions", json={"mode": "verified", "task_id": "HumanEval/0"}
                )
        # The endpoint raises 503, but the session should have been marked failed
        # in the except block before raising.
        # We can verify by looking at the most recent session in the DB.
        with SessionLocal() as db:
            sessions = (
                db.query(VerificationSession)
                .filter(VerificationSession.mode == "verified")
                .all()
            )
            failed = [s for s in sessions if s.status == VerificationStatus.failed]
            assert len(failed) >= 1


# ===========================================================================
# 11. Existing synchronous endpoints remain compatible
# ===========================================================================

class TestBackwardCompatibility:

    _DOCTEST_PROMPT = (
        'def answer(x):\n'
        '    """Double x.\n'
        '    >>> answer(2)\n'
        '    4\n'
        '    """\n'
    )

    def test_baseline_run_still_registered(self, SessionLocal):
        """Route must exist; use raise_server_exceptions=False so LLM errors don't propagate."""
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader"):
            with TestClient(m.app, raise_server_exceptions=False) as client:
                resp = client.post("/baseline/run", json={"task_id": "HumanEval/0"})
        assert resp.status_code != 404

    def test_verified_run_still_registered(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader"):
            with TestClient(m.app, raise_server_exceptions=False) as client:
                resp = client.post("/verified/run", json={"task_id": "HumanEval/0"})
        assert resp.status_code != 404

    def test_interactive_run_still_registered(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"):
            with TestClient(m.app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/interactive/run",
                    json={"question": "write add"},
                )
        assert resp.status_code != 404

    def test_humaneval_tasks_still_registered(self, SessionLocal):
        import app.main as m
        with patch.object(m, "SessionLocal", SessionLocal):
            with TestClient(m.app, raise_server_exceptions=False) as client:
                resp = client.get("/tasks/humaneval")
        assert resp.status_code in (200, 503)

    def test_verified_run_returns_expected_shape(self, SessionLocal):
        """The /verified/run response shape must not have changed."""
        loader = MagicMock()
        loader.get.return_value = MagicMock(
            prompt=self._DOCTEST_PROMPT, hidden_test="assert answer(2) == 4"
        )
        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(True)
        llm = MagicMock()
        llm.generate.return_value = _make_generation("def answer(x): return x*2")

        from app.verified_pipeline import VerifiedPipeline
        from app import main as m

        pipeline = VerifiedPipeline(llm, sandbox, SessionLocal, loader, 1, 0)
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "VerifiedPipeline", return_value=pipeline), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader", return_value=loader):
            with TestClient(m.app) as client:
                resp = client.post("/verified/run", json={"task_id": "HumanEval/0"})

        assert resp.status_code == 200
        body = resp.json()
        assert "session" in body
        assert "attempts" in body
        for key in ("id", "task_id", "status", "created_at", "completed_at"):
            assert key in body["session"]

    def test_interactive_run_returns_oracle_tests(self, SessionLocal):
        sandbox = MagicMock()
        sandbox.run.return_value = _make_evidence(True)
        llm = MagicMock()
        llm.generate.return_value = _make_generation("def add(a,b): return a+b")

        from app.interactive_pipeline import InteractivePipeline
        from app import main as m
        pipeline = InteractivePipeline(llm, sandbox, SessionLocal, 1, 0)
        with patch.object(m, "SessionLocal", SessionLocal), \
             patch.object(m, "InteractivePipeline", return_value=pipeline), \
             patch.object(m, "OpenAIClient"), \
             patch.object(m, "SandboxExecutor"), \
             patch.object(m, "HumanEvalLoader"):
            with TestClient(m.app) as client:
                resp = client.post(
                    "/interactive/run",
                    json={"question": "write add", "tests": ["assert add(1,2)==3"]},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert "oracle_tests" in body["session"]
        assert "candidate_test_results" in body
        assert "selected_test_results" in body
        assert "repair_test_results" in body
