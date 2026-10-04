"""Export evaluation metrics from PostgreSQL to aggregate and per-task CSVs.

Failure Diagnosis Accuracy and Evidence Quality are intentionally out of
scope: the current pipeline has one repair-prompt design and does not store
independent diagnosis or evidence-quality labels.  Reporting a proxy would be
misleading.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

# Allow the documented ``python scripts/compute_metrics.py`` invocation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import AttemptPhase, Run, RunMode, VerificationSession, VerificationStatus


SAFETY_PATTERN = re.compile(r"timeout|timed out|resource|memory|oom|killed|kill condition|pids", re.I)


def safe_rate(records: list[bool]) -> float | None:
    return sum(records) / len(records) if records else None


def is_safety_violation(*values: object) -> bool:
    return bool(SAFETY_PATTERN.search("\n".join(str(value or "") for value in values)))


def summarize(baseline_rows: list[dict], session_rows: list[dict]) -> dict:
    """Calculate metrics from normalized rows; kept pure for deterministic tests."""
    baseline_success = [row["hidden_passed"] for row in baseline_rows]
    verified_success = [row["status"] == "succeeded" for row in session_rows]
    # A session is eval-instrumented only when every generated candidate has a
    # hidden result.  Older production sessions contain only the selected
    # candidate's hidden result and must not bias this measurement.
    eval_sessions = [row for row in session_rows if (
        candidates_in_session := [a for a in row["attempts"] if a["phase"] == "candidate"]
    ) and all(a["hidden"] is not None for a in candidates_in_session)]
    candidates = [attempt for row in eval_sessions for attempt in row["attempts"]
                  if attempt["phase"] == "candidate" and attempt["visible"] is not None]
    tp = sum(a["visible"] and a["hidden"] for a in candidates)
    tn = sum(not a["visible"] and not a["hidden"] for a in candidates)
    fp = sum(a["visible"] and not a["hidden"] for a in candidates)
    fn = sum(not a["visible"] and a["hidden"] for a in candidates)
    initial_failures = []
    repaired_successes = []
    repair_counts = []
    for row in session_rows:
        selected = next((a for a in row["attempts"] if a["phase"] == "candidate" and a["selected"]), None)
        repairs = [a for a in row["attempts"] if a["phase"] == "repair"]
        if selected and selected["hidden"] is False:
            initial_failures.append(row["status"] == "succeeded")
            if row["status"] == "succeeded":
                repaired_successes.append(row)
                repair_counts.append(len(repairs))
    baseline_tokens = [row["tokens"] or 0 for row in baseline_rows]
    baseline_durations = [row["duration"] or 0.0 for row in baseline_rows]
    verified_tokens = [sum(a["tokens"] or 0 for a in row["attempts"]) for row in session_rows]
    verified_durations = [sum(a["duration"] or 0.0 for a in row["attempts"]) for row in session_rows]
    safety = [row["safety"] for row in baseline_rows] + [a["safety"] for row in session_rows for a in row["attempts"]]
    return {
        "baseline_task_success_rate": safe_rate(baseline_success),
        "verified_task_success_rate": safe_rate(verified_success),
        "verification_accuracy": safe_rate([a["visible"] == a["hidden"] for a in candidates]),
        "verification_false_positive_rate": fp / (tp + fp) if tp + fp else None,
        "verification_false_negative_rate": fn / (fn + tp) if fn + tp else None,
        "recovery_success_rate": safe_rate(initial_failures),
        "replanning_efficiency": sum(repair_counts) / len(repair_counts) if repair_counts else None,
        "baseline_avg_tokens": sum(baseline_tokens) / len(baseline_tokens) if baseline_tokens else None,
        "verified_avg_tokens": sum(verified_tokens) / len(verified_tokens) if verified_tokens else None,
        "baseline_avg_duration_ms": sum(baseline_durations) / len(baseline_durations) if baseline_durations else None,
        "verified_avg_duration_ms": sum(verified_durations) / len(verified_durations) if verified_durations else None,
        "safety_violation_rate": safe_rate(safety),
        "candidate_count": len(candidates),
        "recovery_initial_failure_count": len(initial_failures),
    }


def load_rows():
    with SessionLocal() as db:
        runs = db.scalars(select(Run).where(Run.mode == RunMode.baseline).options(selectinload(Run.test_results))).all()
        sessions = db.scalars(select(VerificationSession).options(selectinload(VerificationSession.attempts))).all()
        baseline_rows = [{"task_id": r.task_id, "trial_index": r.trial_index, "hidden_passed": r.hidden_passed,
            "tokens": r.token_usage, "duration": r.duration_ms,
            "safety": any(is_safety_violation(x.stdout, x.stderr, x.error) for x in r.test_results)} for r in runs]
        session_rows = [{"task_id": s.task_id, "trial_index": s.trial_index, "status": s.status.value,
            "attempts": [{"phase": a.phase.value, "visible": a.passed_visible_tests, "hidden": a.passed_hidden_tests,
                "selected": a.is_selected, "tokens": a.token_usage, "duration": a.duration_ms,
                "safety": is_safety_violation(a.stdout, a.stderr, a.error_summary)} for a in s.attempts]} for s in sessions]
    return baseline_rows, session_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=keys)
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation_results"))
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    baseline_rows, session_rows = load_rows()
    per_task = []
    for task_id in sorted({r["task_id"] for r in baseline_rows + session_rows}):
        per_task.append({"task_id": task_id, **summarize(
            [r for r in baseline_rows if r["task_id"] == task_id],
            [r for r in session_rows if r["task_id"] == task_id],
        )})
    aggregate = summarize(baseline_rows, session_rows)
    write_csv(args.output_dir / "per_task_metrics.csv", per_task)
    write_csv(args.output_dir / "aggregate_metrics.csv", [aggregate])
    print(f"Wrote {args.output_dir / 'per_task_metrics.csv'} and {args.output_dir / 'aggregate_metrics.csv'}")
    print("Out of scope: Failure Diagnosis Accuracy and Evidence Quality (no independent labels/design).")


if __name__ == "__main__":
    main()
