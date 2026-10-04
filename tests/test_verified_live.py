"""Live validation of the public verified endpoint.

Requires the same Docker, PostgreSQL, HumanEval cache/network, and configured
LLM credentials as the application's normal runtime.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


pytestmark = pytest.mark.integration


def test_verified_endpoint_on_three_humaneval_tasks():
    client = TestClient(app)
    for task_id in ("HumanEval/0", "HumanEval/1", "HumanEval/2"):
        response = client.post("/verified/run", json={"task_id": task_id})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["session"]["task_id"] == task_id
        assert payload["session"]["status"] in {"succeeded", "exhausted"}
        candidates = [item for item in payload["attempts"] if item["phase"] == "candidate"]
        assert len(candidates) == settings.verification_candidates
        assert sum(item["is_selected"] for item in candidates) == 1
