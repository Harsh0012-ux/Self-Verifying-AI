"""Report cached HumanEval tasks without executable visible assertions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dataset import HumanEvalLoader
from app.verified_pipeline import visible_assertions


def main() -> None:
    tasks = HumanEvalLoader().problems()
    missing = [task_id for task_id, task in tasks.items() if not visible_assertions(task)]
    print(f"Cached tasks checked: {len(tasks)}")
    print(f"Tasks without doctest-style visible assertions: {len(missing)}")
    for task_id in missing:
        print(task_id)


if __name__ == "__main__":
    main()
