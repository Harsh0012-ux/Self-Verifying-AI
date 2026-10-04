"""Runs inside the deliberately minimal sandbox image; inputs arrive as environment variables."""
import base64
import json
import os
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO


def main():
    tests = json.loads(base64.b64decode(os.environ["SVA_TESTS_B64"]))
    started = time.monotonic()
    namespace = {"__name__": "candidate"}
    try:
        with open("/candidate/candidate.py", encoding="utf-8") as source:
            exec(compile(source.read(), "candidate.py", "exec"), namespace, namespace)
    except BaseException:
        print(json.dumps({"results": [{"name": "candidate_import", "passed": False,
              "error": traceback.format_exc()}], "duration_ms": round((time.monotonic()-started)*1000, 2)}))
        return 0
    results = []
    for index, test in enumerate(tests):
        stdout, stderr = StringIO(), StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exec(compile(test, f"test_{index}.py", "exec"), namespace, namespace)
            results.append({"name": f"test_{index}", "passed": True, "error": None,
                            "stdout": stdout.getvalue(), "stderr": stderr.getvalue()})
        except BaseException:
            results.append({"name": f"test_{index}", "passed": False, "error": traceback.format_exc(),
                            "stdout": stdout.getvalue(), "stderr": stderr.getvalue()})
    print(json.dumps({"results": results, "duration_ms": round((time.monotonic()-started)*1000, 2)}))


if __name__ == "__main__":
    main()
