# Self-Verifying AI: Mentor Interaction Briefing

## 1. One-Minute Explanation

This project tests whether an AI-generated Python solution can check and improve itself.

The system:

1. Receives a programming problem.
2. Asks an LLM to generate Python code.
3. Runs the code inside a restricted Docker container.
4. Tests the generated code.
5. Records results, errors, execution time, and token usage.
6. In verified mode, generates multiple candidates, selects the strongest one using visible tests, and checks it using hidden tests.
7. If the selected candidate fails, asks the LLM to repair it and tries again within a fixed limit.

The project is currently a working research prototype, not a production system.

## 2. Main Research Idea

The main question is:

> Can execution feedback improve the reliability of LLM-generated programs?

We compare two approaches:

### Baseline

```text
Problem -> Generate one solution -> Run hidden test -> Store result
```

### Verified pipeline

```text
Generate multiple candidates
        -> Run visible tests
        -> Select the best candidate
        -> Run hidden test
        -> Repair if necessary
        -> Re-run
        -> Store complete history
```

The baseline gives us a comparison point. The verified pipeline adds selection, verification, repair, and evidence storage.

## 3. What We Have Achieved

### Baseline pipeline

The baseline pipeline is implemented in `app/pipeline.py`.

It:

1. Loads a HumanEval problem.
2. Builds a prompt for the LLM.
3. Generates one candidate solution.
4. Extracts Python code from the LLM response.
5. Runs the code against a hidden test inside Docker.
6. Saves the result in PostgreSQL.
7. Returns the result through the API.

The endpoint is:

```text
POST /baseline/run
```

Example request:

```json
{
  "task_id": "HumanEval/0"
}
```

### Verified pipeline

The verified workflow is implemented in `app/verified_pipeline.py`.

By default, the system:

- Generates 3 candidates.
- Runs visible tests on all candidates.
- Selects the candidate with the highest visible-test score.
- Runs the selected candidate against the hidden test.
- Allows up to 2 repair attempts if the hidden test fails.
- Stores all candidates, repairs, outputs, errors, timing, and token usage.

The endpoint is:

```text
POST /verified/run
```

### LLM provider support

The application uses the OpenAI Python SDK through an abstraction called `LLMClient`.

Because the client supports an optional OpenAI-compatible base URL, it can work with providers such as Groq without changing the generation logic.

The important configuration concepts are:

```text
LLM_API_KEY=<secret key>
LLM_MODEL=<provider model>
LLM_BASE_URL=<optional OpenAI-compatible endpoint>
```

The actual API key must never be placed in documentation, source code, commits, or presentations.

### HumanEval dataset

`app/dataset.py` downloads and caches the HumanEval dataset.

Each problem contains:

- Task ID
- Problem prompt
- Function entry point
- Visible examples
- Canonical hidden test

The first request downloads the compressed dataset and stores a local JSONL cache.

### Docker sandbox

Generated code is not executed directly on the host machine. It is run inside a Docker container with restrictions including:

- Network disabled
- Read-only filesystem
- Non-root user
- Linux capabilities dropped
- `no-new-privileges` enabled
- Process limit
- Memory limit
- CPU limit
- Temporary filesystem restrictions
- Wall-clock timeout

This reduces risk, although executing arbitrary generated code should still be treated as dangerous.

### Database persistence

SQLAlchemy models store:

- Baseline runs
- Individual test results
- Verification sessions
- Candidate attempts
- Repair attempts
- Pass/fail status
- Standard output and error output
- Execution duration
- Token usage

Alembic migrations create and update the database schema.

### Evaluation framework

The project includes a resumable evaluation runner with:

- Multiple HumanEval tasks
- Multiple trials
- Baseline and verified modes
- Rate limiting
- Provider rate-limit retries
- Resume support after interruption
- CSV metric generation

## 4. What “Creating a Loop First” Means

A normal LLM coding system works like this:

```text
Prompt -> Generate code -> Return code
```

That is risky because the model may produce code that looks correct but fails when executed.

The intended self-verification loop is:

```text
Generate
   -> Execute
   -> Observe evidence
   -> Diagnose or critique failure
   -> Repair or regenerate
   -> Execute again
   -> Stop when successful or attempts are exhausted
```

In simple terms:

> The AI is not trusted after its first answer. It receives evidence about what happened and gets an opportunity to improve.

The loop is bounded so that it cannot run forever or spend unlimited LLM tokens.

The current implementation uses this bounded process:

1. Generate several initial candidates.
2. Test them using visible examples.
3. Select the strongest candidate.
4. Test that candidate using hidden tests.
5. Generate a repair candidate if it fails.
6. Stop after success or the configured repair limit.

## 5. Visible Tests and Hidden Tests

### Visible tests

Visible tests are examples included in the problem prompt, such as:

```python
>>> answer(2)
4
```

The verified pipeline converts these examples into executable assertions. They are used to compare candidate solutions.

### Hidden tests

Hidden tests come from HumanEval's canonical test definition. The LLM does not receive them.

They are used as the final evaluation of the generated solution.

The distinction is important:

- Visible tests help choose a candidate.
- Hidden tests measure whether the candidate generalizes beyond the examples it saw.

## 6. Explanation of the 150 Evaluation Runs

The number 150 refers to evaluation runs, not 150 pytest unit tests.

The configured experiment was:

```text
25 HumanEval tasks
x 3 trials per task
x 2 pipelines
= 150 task-level runs
```

The two pipelines were:

```text
Baseline
Verified
```

Therefore:

```text
25 x 3 = 75 baseline runs
25 x 3 = 75 verified sessions
75 + 75 = 150 total runs
```

The verified pipeline generated 3 candidates per session:

```text
75 verified sessions x 3 candidates = 225 verified candidates
```

That explains why the aggregate metrics report `candidate_count = 225`.

The saved evaluation artifacts are:

- `scripts/run_evaluation.py`
- `scripts/compute_metrics.py`
- `evaluation_results/aggregate_metrics.csv`
- `evaluation_results/per_task_metrics.csv`

The recorded aggregate results include:

```text
Baseline success rate: 92%
Verified success rate: 100%
Verification accuracy: approximately 99.56%
Safety violation rate: 0%
```

The verified pipeline was slower and used more tokens because it generated multiple candidates:

```text
Baseline average duration: approximately 617 ms
Verified average duration: approximately 1,753 ms
```

Important qualification:

> These results are promising, but they come from only the first 25 HumanEval tasks and a limited local experiment. They should not yet be presented as proof of general reliability.

Also, the evaluation recorded no initial failures requiring repair. Therefore, the repair mechanism exists and is tested, but its effectiveness was not strongly demonstrated by the 150-run evaluation.

## 7. File-by-File Explanation

### Root files

#### `README.md`

Basic setup instructions and baseline description. It should be updated because it does not fully describe the newer verified pipeline.

#### `CLAUDE_PROJECT_HANDOFF.md`

Project history, configuration notes, risks, and roadmap. Some sections describe the older baseline-only state and are now outdated.

#### `pyproject.toml`

Defines Python version, dependencies, package configuration, pytest settings, and Ruff settings.

#### `alembic.ini`

Alembic database migration configuration.

### Application files

#### `app/main.py`

Creates the FastAPI application and defines:

- `POST /baseline/run`
- `POST /verified/run`

#### `app/config.py`

Loads settings from `.env`, including:

- Database URL
- LLM API key
- LLM base URL
- LLM model
- Docker image
- Candidate count
- Repair limit

#### `app/llm.py`

Defines the LLM abstraction and OpenAI-compatible client. It sends prompts to the configured model and returns generated code plus token usage.

#### `app/dataset.py`

Downloads, caches, and parses HumanEval problems.

#### `app/code_extraction.py`

Cleans model output, removes Markdown code fences, and extracts usable Python code.

#### `app/pipeline.py`

Implements the one-shot baseline pipeline.

#### `app/verified_pipeline.py`

Implements visible-test generation, candidate scoring, selection, hidden-test evaluation, repair prompts, bounded repair attempts, and attempt history.

#### `app/models.py`

Defines the SQLAlchemy models:

- `Run`
- `TestResult`
- `VerificationSession`
- `Attempt`

#### `app/database.py`

Creates the SQLAlchemy engine and database session factory.

#### `app/sandbox.py`

Controls Docker execution and collects structured test evidence.

### Docker files

#### `docker/sandbox.Dockerfile`

Builds the restricted Python execution image.

#### `docker/runner.py`

Runs inside the container. It loads the candidate, executes tests, captures output and exceptions, and prints structured JSON evidence.

### Database migrations

#### `alembic/versions/0001_baseline.py`

Creates the original `runs` and `test_results` tables.

#### `alembic/versions/0002_verification_sessions.py`

Adds `verification_sessions` and `attempts` for verified-mode history.

#### `alembic/versions/0003_trial_index.py`

Adds `trial_index` so repeated experiments on the same task can be distinguished.

### Scripts

#### `scripts/validate_baseline.py`

Runs five real baseline tasks as a smoke test.

#### `scripts/run_evaluation.py`

Runs repeated baseline and verified experiments with rate limiting, retries, and resume support.

#### `scripts/compute_metrics.py`

Reads stored PostgreSQL results and exports aggregate and per-task CSV metrics.

### Tests

The repository currently collects 18 pytest tests:

- 13 fast unit or mocked tests
- 5 integration-marked tests requiring Docker or live services

Test areas include:

- Dataset loading
- Code extraction
- Baseline persistence
- Candidate selection
- Repair-loop limits
- Sandbox timeout behavior
- Sandbox restrictions
- Empty evidence handling
- Metric calculations
- Live verified endpoint behavior

## 8. Commands to Run the Project

Run these commands from the project root in PowerShell.

### Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### Start PostgreSQL

```powershell
docker run --name sva-postgres `
  -e POSTGRES_PASSWORD=<database-password> `
  -e POSTGRES_DB=sva `
  -p 5432:5432 `
  -d postgres:16
```

If the container already exists:

```powershell
docker start sva-postgres
```

### Build the sandbox image

```powershell
docker build -t sva-sandbox:latest -f docker/sandbox.Dockerfile .
```

### Apply migrations

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### Run the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### Run fast tests

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

### Run all tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### Run five-task baseline validation

```powershell
.\.venv\Scripts\python.exe scripts/validate_baseline.py
```

### Run a small evaluation

```powershell
.\.venv\Scripts\python.exe scripts/run_evaluation.py --task-limit 3 --trials 1
```

### Run the full configured evaluation

```powershell
.\.venv\Scripts\python.exe scripts/run_evaluation.py
```

### Generate metrics

```powershell
.\.venv\Scripts\python.exe scripts/compute_metrics.py
```

## 9. Future Work

### Documentation

Update `README.md` to document:

- `/verified/run`
- Verified pipeline behavior
- Evaluation commands
- Current configuration
- Test counts

### Better critique and repair

Improve the repair system with:

- Structured error diagnosis
- Syntax, logic, timeout, and security failure categories
- Better repair prompts
- Repair effectiveness metrics
- Prompt and model version tracking

### Stronger evaluation

Future experiments should include:

- More HumanEval tasks
- More repeated trials
- Additional benchmarks
- Fixed model settings
- Statistical confidence intervals
- Cost measurements
- Latency measurements
- Additional baseline systems

### Security hardening

Potential improvements include:

- Output-size limits
- More robust Docker cleanup
- Precise exception handling
- Stronger container isolation
- Resource monitoring
- API authentication
- API rate limiting
- Secret rotation
- Removing hard-coded database credentials

### API improvements

The current API performs long-running work synchronously. Future improvements could include:

- Background jobs
- Job IDs
- Status endpoints
- Result retrieval endpoints
- Pagination
- Authentication
- Cancellation
- Idempotency support

### Database improvements

Future database fields could include:

- Prompt version
- Model name
- Temperature
- Provider
- Failure category
- Repair reason
- Test-level results for every attempt
- Experiment configuration
- Evaluation batch ID

### Testing improvements

Additional tests are needed for:

- FastAPI endpoint behavior
- LLM configuration
- Missing API keys
- OpenAI-compatible provider behavior
- PostgreSQL integration
- Alembic migrations
- Docker image building
- Malformed runner output
- Output overflow
- Cleanup failures
- Security regressions
- More repair scenarios

## 10. Suggested Mentor Explanation

> The main research question is whether execution feedback can improve the reliability of LLM-generated programs. We compare a one-shot baseline against a verified workflow that generates multiple candidates, checks them against visible examples, selects the strongest candidate, validates it using hidden tests, and optionally repairs failures. Every execution is isolated in Docker and persisted with evidence so that the experiment is reproducible and measurable.

A truthful maturity statement is:

> The verified loop is implemented, but the project is still a prototype. The current evaluation shows better results for the tested dataset, but it only uses 25 HumanEval tasks and does not strongly exercise the repair path. The next milestone is a larger, more controlled evaluation with better failure diagnosis and stronger security and API controls.

## 11. Important Security Reminder

Do not show or copy the real API key from `.env` during the mentor interaction.

Use placeholders when discussing configuration, and rotate the key if it has ever been exposed.
