import json
import httpx
import pytest
from app.dataset import HumanEvalLoader

def test_loader_splits_prompt_and_canonical_hidden_test(tmp_path):
    record = {"task_id": "HumanEval/0", "entry_point": "add", "prompt": "def add(a,b):\n    \"\"\"\n    >>> add(1, 2)\n    3\n    \"\"\"", "test": "def check(candidate):\n    assert candidate(1, 2) == 3"}
    cache = tmp_path / "data.jsonl"; cache.write_text(json.dumps(record) + "\n")
    problem = HumanEvalLoader(cache, limit=1).get("HumanEval/0")
    assert problem.entry_point == "add"
    assert problem.visible_tests == [">>> add(1, 2)"]
    assert "check(add)" in problem.hidden_test
    assert ">>>" not in problem.hidden_test

def test_loader_raises_when_download_fails(tmp_path, monkeypatch):
    class FailedResponse:
        content = b""

        def raise_for_status(self):
            raise httpx.HTTPError("download interrupted")

    monkeypatch.setattr("app.dataset.httpx.get", lambda *args, **kwargs: FailedResponse())

    with pytest.raises(httpx.HTTPError, match="download interrupted"):
        HumanEvalLoader(tmp_path / "data.jsonl").problems()
