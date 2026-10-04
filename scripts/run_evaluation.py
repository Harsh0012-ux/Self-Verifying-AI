"""Run resumable, rate-limited baseline and verified HumanEval evaluations.

Examples:
  python scripts/run_evaluation.py --task-limit 3 --trials 1
  python scripts/run_evaluation.py  # all 25 tasks, three trials each

Existing rows with the same task, pipeline, and trial index are skipped by
default, making an interrupted batch safe to resume.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Allow the documented ``python scripts/run_evaluation.py`` invocation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import RateLimitError
from sqlalchemy import select

from app.database import SessionLocal
from app.dataset import HumanEvalLoader
from app.llm import LLMClient, OpenAIClient
from app.models import Run, RunMode, VerificationSession
from app.pipeline import BaselinePipeline
from app.sandbox import SandboxExecutor
from app.verified_pipeline import VerifiedPipeline


LOG = logging.getLogger("evaluation")


class PacedRetryingLLM(LLMClient):
    """Enforce at most 30 starts/minute and retry provider rate limits."""

    def __init__(self, client: LLMClient, requests_per_minute: int = 30):
        self.client = client
        self.minimum_interval = 60.0 / requests_per_minute
        self.next_request_at = 0.0

    def generate(self, prompt: str):
        delay = self.next_request_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        # Reserve the next slot before the call, including failed calls.
        self.next_request_at = time.monotonic() + self.minimum_interval
        for attempt in range(6):
            try:
                return self.client.generate(prompt)
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                if not isinstance(exc, RateLimitError) and status != 429:
                    raise
                delay = min(60.0, 2.0 ** attempt * self.minimum_interval)
                LOG.warning("Provider rate limited; retrying in %.1fs (attempt %s/6)", delay, attempt + 1)
                time.sleep(delay)
                self.next_request_at = max(self.next_request_at, time.monotonic() + self.minimum_interval)
        raise RuntimeError("LLM stayed rate limited after six retries")


def task_sort_key(task_id: str):
    return int(task_id.rsplit("/", 1)[-1])


def already_done(task_id: str, trial_index: int, pipeline: str) -> bool:
    with SessionLocal() as db:
        if pipeline == "baseline":
            query = select(Run.id).where(
                Run.task_id == task_id, Run.mode == RunMode.baseline,
                Run.trial_index == trial_index,
            )
        else:
            query = select(VerificationSession.id).where(
                VerificationSession.task_id == task_id,
                VerificationSession.trial_index == trial_index,
            )
        return db.scalar(query.limit(1)) is not None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-limit", type=int, default=25)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--requests-per-minute", type=int, default=30)
    parser.add_argument("--no-resume", action="store_true", help="run even if a matching trial already exists")
    args = parser.parse_args()
    if args.task_limit < 1 or args.trials < 1 or not 1 <= args.requests_per_minute <= 30:
        parser.error("task limit/trials must be positive and requests-per-minute must be 1..30")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    task_ids = sorted(HumanEvalLoader().problems(), key=task_sort_key)[:args.task_limit]
    llm = PacedRetryingLLM(OpenAIClient(), args.requests_per_minute)
    sandbox = SandboxExecutor()
    baseline = BaselinePipeline(llm, sandbox, SessionLocal)
    verified = VerifiedPipeline(llm, sandbox, SessionLocal)
    total = len(task_ids) * args.trials * 2
    completed = skipped = 0

    # Pairing the two pipelines by task/trial makes progress logs easy to
    # inspect; the shared limiter accounts for repair calls as well.
    for task_id in task_ids:
        for trial_index in range(args.trials):
            for name, runner in (("baseline", baseline), ("verified", verified)):
                label = f"{name} {task_id} trial={trial_index}"
                if not args.no_resume and already_done(task_id, trial_index, name):
                    skipped += 1
                    LOG.info("SKIP %s (%s/%s)", label, completed + skipped, total)
                    continue
                LOG.info("START %s (%s/%s)", label, completed + skipped + 1, total)
                try:
                    if name == "baseline":
                        result = runner.run(task_id, trial_index=trial_index)
                        detail = f"hidden_passed={result.hidden_passed}"
                    else:
                        result = runner.run(task_id, trial_index=trial_index, eval_hidden_candidates=True)
                        detail = f"status={result.status.value}"
                    completed += 1
                    LOG.info("DONE %s %s", label, detail)
                except Exception:
                    LOG.exception("FAILED %s; rerun this command to resume", label)
                    raise
    LOG.info("Evaluation complete: %s completed, %s skipped, %s total", completed, skipped, total)


if __name__ == "__main__":
    main()
