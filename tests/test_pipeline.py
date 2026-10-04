from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.dataset import Problem
from app.llm import Generation, LLMClient
from app.models import Base, Run
from app.pipeline import BaselinePipeline
from app.code_extraction import extract_python_code
from app.sandbox import SandboxEvidence, SandboxTestEvidence

class FakeLoader:
    def get(self, task_id):
        return Problem(task_id, "def answer(): pass", "answer", [">>> answer()"], "assert answer() == 42")
class FakeLLM(LLMClient):
    def generate(self, prompt): return Generation("def answer(): return 42", 17)
class FakeSandbox:
    def run(self, code, tests):
        assert len(tests) == 1 and "== 42" in tests[0]
        return SandboxEvidence(True, False, "ok", "", 0, 12.5, [SandboxTestEvidence("hidden", True, None)])

def test_baseline_logs_five_tasks():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    pipeline = BaselinePipeline(FakeLLM(), FakeSandbox(), sessionmaker(bind=engine), FakeLoader())
    runs = [pipeline.run(f"HumanEval/{i}") for i in range(5)]
    with sessionmaker(bind=engine)() as db:
        stored = db.query(Run).all()
        assert len(stored) == 5
        assert all(r.hidden_passed and r.token_usage == 17 and len(r.test_results) == 1 for r in stored)
    assert [r.task_id for r in runs] == [f"HumanEval/{i}" for i in range(5)]


def test_code_extraction_removes_markdown_fences():
    assert extract_python_code("Explanation\n```python\ndef answer(): return 42\n```") == "def answer(): return 42"
    assert extract_python_code("Here is the solution:\ndef answer(): return 42\nThis is the answer.") == "def answer(): return 42"
