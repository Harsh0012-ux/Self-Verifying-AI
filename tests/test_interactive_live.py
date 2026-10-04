"""Live endpoint check; requires the configured LLM, PostgreSQL, Docker, and sandbox image."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = pytest.mark.integration


def test_interactive_endpoint_with_a_simple_question():
    response = TestClient(app).post("/interactive/run", json={
        "question": "Write a Python function named add(a, b) that returns their sum.",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["session"]["source"] == "interactive"
    assert payload["session"]["oracle_kind"] == "self_generated"
    assert payload["session"]["oracle_tests"]
    assert len([item for item in payload["attempts"] if item["phase"] == "candidate"]) == 3
