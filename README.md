# Experimental Self-Verifying AI

Baseline-only research prototype. `POST /baseline/run` generates one solution, evaluates it only
against hidden HumanEval tests in an isolated Docker container, and stores evidence in PostgreSQL.

## Start

```powershell
docker build -t sva-sandbox:latest -f docker/sandbox.Dockerfile .
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

The first dataset request downloads HumanEval's MIT-licensed JSONL from the upstream repository and
caches it locally. Set `HUMANEVAL_CACHE_PATH` to control that location.

To perform the five-task live validation (requires Docker Desktop, PostgreSQL, and LLM credentials):

```powershell
python scripts/validate_baseline.py
```
