"""HumanEval loader. Dataset is MIT licensed: https://github.com/openai/human-eval/blob/master/LICENSE"""
import json
from dataclasses import dataclass
from pathlib import Path
import httpx
from app.config import settings

DATA_URL = "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz"

@dataclass(frozen=True)
class Problem:
    task_id: str; prompt: str; entry_point: str; visible_tests: list[str]; hidden_test: str

def _visible(prompt: str) -> list[str]:
    """Examples remain descriptive prompts; safely executable ones can be added later."""
    return [line.strip() for line in prompt.splitlines() if ">>>" in line]

class HumanEvalLoader:
    def __init__(self, cache_path: Path | None = None, limit: int = 25):
        self.cache_path, self.limit = cache_path or settings.humaneval_cache_path, limit
    def _records(self):
        if not self.cache_path.exists():
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            response = httpx.get(DATA_URL, timeout=30)
            response.raise_for_status()
            data = response.content
            import gzip
            self.cache_path.write_bytes(gzip.decompress(data))
        return [json.loads(x) for x in self.cache_path.read_text(encoding="utf-8").splitlines()]
    def problems(self) -> dict[str, Problem]:
        records = self._records()[:self.limit]
        return {r["task_id"]: Problem(r["task_id"], r["prompt"], r["entry_point"],
                _visible(r["prompt"]), r["test"] + f"\ncheck({r['entry_point']})") for r in records}
    def get(self, task_id: str) -> Problem:
        return self.problems()[task_id]
