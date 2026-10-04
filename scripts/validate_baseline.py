"""Run five real baseline attempts after Docker, PostgreSQL, and LLM credentials are configured."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.dataset import HumanEvalLoader
from app.llm import OpenAIClient
from app.pipeline import BaselinePipeline
from app.sandbox import SandboxExecutor


def main():
    loader = HumanEvalLoader()
    pipeline = BaselinePipeline(OpenAIClient(), SandboxExecutor(), SessionLocal, loader)
    for task_id in list(loader.problems())[:5]:
        run = pipeline.run(task_id)
        print({"run_id": run.id, "task_id": task_id, "hidden_passed": run.hidden_passed,
               "duration_ms": run.duration_ms, "token_usage": run.token_usage})


if __name__ == "__main__":
    main()
