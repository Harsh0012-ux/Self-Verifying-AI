# Claude Project Handoff Prompt

Copy the contents of this document into Claude when you want a complete project analysis and roadmap.

---

## Prompt

You are taking over an existing Python/FastAPI research project called **Self-Verifying AI**.

Your task is to perform a complete technical audit of the repository, reconstruct how the project evolved from its initial state, explain the current architecture and configuration, identify risks and incomplete work, and propose a practical roadmap for the next development stages.

Do not immediately modify files. First inspect the repository and compare the actual implementation with the history described below. Clearly distinguish:

- Facts verified directly from repository files.
- Changes inferred from the development history.
- Risks or assumptions that still need confirmation.
- Recommendations for future work.

Do not reveal, reproduce, or log any real API key. The local `.env` contains a real-looking secret and must be treated as sensitive.

## 1. Project Purpose

The project is an experimental self-verifying AI system.

The current implemented baseline flow is:

1. Receive a HumanEval task ID through a FastAPI endpoint.
2. Load the corresponding HumanEval problem.
3. Ask an LLM to generate Python code.
4. Run the generated code inside an isolated Docker sandbox.
5. Execute a hidden HumanEval test against the generated code.
6. Capture execution evidence.
7. Store the run and test result in PostgreSQL.
8. Return the result through the API.

The intended future system is more advanced:

```text
Generate -> Execute -> Inspect evidence -> Critique failure -> Repair or regenerate -> Re-execute -> Store verification history
```

The repository is still explicitly a baseline-only prototype. A real multi-step self-verification loop has not yet been implemented.

## 2. Repository Structure

Important files include:

### Root configuration and documentation

- `README.md`
- `pyproject.toml`
- `.env`
- `.env.example`
- `.gitignore`
- `alembic.ini`

### Application code

- `app/__init__.py`
- `app/config.py`
- `app/database.py`
- `app/dataset.py`
- `app/llm.py`
- `app/main.py`
- `app/models.py`
- `app/pipeline.py`
- `app/sandbox.py`

### Docker and sandbox code

- `docker/runner.py`
- `docker/sandbox.Dockerfile`

### Database migrations

- `alembic/env.py`
- `alembic/versions/0001_baseline.py`

### Scripts

- `scripts/validate_baseline.py`

### Tests

- `tests/test_dataset.py`
- `tests/test_pipeline.py`
- `tests/test_sandbox.py`

Generated packaging metadata under `self_verifying_ai.egg-info/` is build output rather than primary source code.

## 3. Initial Project State

At the initial stage, the repository already represented a baseline self-verifying-AI experiment with:

- FastAPI.
- SQLAlchemy.
- Alembic migrations.
- PostgreSQL persistence.
- HumanEval loading and caching.
- OpenAI Python SDK integration.
- Docker-based code execution.
- Basic sandbox restrictions.
- A baseline pipeline.
- Unit and integration tests.

The original LLM configuration included:

- `LLM_API_KEY`
- `LLM_MODEL`

There was no configurable LLM base URL.

The original LLM client effectively behaved like:

```python
OpenAI(api_key=api_key or settings.llm_api_key)
```

Therefore, the SDK used OpenAI's default endpoint and could not be redirected to an OpenAI-compatible third-party provider such as Groq.

The original PostgreSQL defaults also did not initially match the Docker command eventually used during development.

## 4. Complete Change History

### A. Added OpenAI-compatible base URL support

`app/config.py` was extended with:

```python
llm_base_url: str | None = None
```

`app/llm.py` now conditionally constructs the OpenAI client:

```python
client_options = {
    "api_key": api_key or settings.llm_api_key
}

if settings.llm_base_url is not None:
    client_options["base_url"] = settings.llm_base_url

self.client = OpenAI(**client_options)
```

The compatibility behavior is:

- Without `LLM_BASE_URL`, the client receives only the API key and uses the SDK default endpoint.
- With `LLM_BASE_URL`, the configured URL is passed as `base_url`.
- The existing Responses API call was deliberately left unchanged:

```python
self.client.responses.create(
    model=self.model,
    input=prompt
)
```

No provider-specific branching was added to the generation logic.

### B. Switched local development from OpenAI to Groq

The local configuration was changed to use Groq's OpenAI-compatible endpoint:

```dotenv
LLM_MODEL=openai/gpt-oss-120b
LLM_BASE_URL=https://api.groq.com/openai/v1
```

The real API key is stored only in the local `.env`. It must never be copied into source code, documentation, commits, or prompts.

The first attempted Groq model was:

```text
llama-3.3-70b-versatile
```

A live request returned a provider error indicating that the model was unavailable for the account. Available models were queried, and the working model selected was:

```text
openai/gpt-oss-120b
```

A live Responses API request then succeeded and returned `OK`.

This verified that the existing OpenAI SDK integration works with the configured Groq endpoint and model.

### C. Cleaned and updated `.env.example`

The example environment file was made into a safe, copy-ready template without a real API key:

```dotenv
LLM_API_KEY=your-groq-api-key-here
LLM_MODEL=openai/gpt-oss-120b
# Optional: set this when using an OpenAI-compatible provider other than OpenAI.
LLM_BASE_URL=https://api.groq.com/openai/v1
DATABASE_URL=postgresql+psycopg://<username>:<password>@localhost:5432/sva
HUMANEVAL_CACHE_PATH=.cache/humaneval.jsonl
```

The previous example had stale or commented-out values, including an old OpenAI model, the retired Groq model, and an actual-looking key. The example must remain placeholder-only.

### D. Aligned PostgreSQL configuration

PostgreSQL is run using:

```powershell
docker run --name sva-postgres `
  -e POSTGRES_PASSWORD=change-this-locally `
  -e POSTGRES_DB=sva `
  -p 5432:5432 `
  -d postgres:16
```

Therefore the correct connection URL is:

```text
postgresql+psycopg://<username>:<password>@localhost:5432/sva
```

This was aligned across:

- `.env`
- `.env.example`
- `app/config.py`
- `alembic.ini`

The previous default used the wrong password and database name:

```text
postgresql+psycopg://<username>:<password>@localhost:5432/self_verifying_ai
```

The corrected application default is:

```python
database_url = "postgresql+psycopg://<username>:<password>@localhost:5432/sva"
```

The PostgreSQL container was running and the application connected successfully to database `sva`.

### E. Validation already performed

The following checks passed during development:

1. The default settings can have `llm_base_url=None`.
2. The LLM client omits `base_url` when it is unset.
3. The LLM client passes `base_url` when it is configured.
4. The Groq endpoint accepted the configured credential.
5. The selected Groq model worked through `client.responses.create(...)`.
6. The PostgreSQL container was running.
7. The application connected to database `sva`.
8. The existing test suite passed:

```text
5 passed
```

The five-task live baseline script should still be treated as an operational smoke test requiring Docker, PostgreSQL, a built sandbox image, network access for the first HumanEval download, and valid LLM credentials.

## 5. Current Configuration

`app/config.py` uses Pydantic Settings and loads `.env`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    database_url: str = (
        "postgresql+psycopg://<username>:<password>@localhost:5432/sva"
    )
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gpt-4.1-mini"
    humaneval_cache_path: Path = Path(".cache/humaneval.jsonl")
    sandbox_image: str = "sva-sandbox:latest"
```

Important configuration precedence:

- Process environment variables override `.env` values.
- `.env` overrides class defaults.
- A stale shell variable can keep an old value active after `.env` is edited.
- This previously happened with the old unavailable LLM model.

The local `.env` contains real local values and must be treated as secret material. The example file must contain only placeholders.

## 6. Current Architecture

### A. FastAPI entry point

`app/main.py` creates a FastAPI application titled `Experimental Self-Verifying AI`.

The current endpoint is:

```text
POST /baseline/run
```

Request body:

```json
{
  "task_id": "HumanEval/0"
}
```

The endpoint constructs an `OpenAIClient`, `SandboxExecutor`, database session factory, `HumanEvalLoader`, and `BaselinePipeline`.

The response includes:

- `run_id`
- `task_id`
- `hidden_passed`
- `duration_ms`
- `token_usage`

Error behavior:

- Unknown task IDs become HTTP 404.
- `RuntimeError` becomes HTTP 503.
- Other errors generally propagate as HTTP 500.

### B. LLM abstraction

`app/llm.py` defines:

- `Generation`
- Abstract `LLMClient`
- Concrete `OpenAIClient`

`Generation` contains generated code and optional token usage.

The client resolves the API key and model from constructor arguments or settings, optionally passes a base URL, calls the Responses API, and returns output text plus token usage.

The prompt currently starts with:

```text
Complete only Python code for this HumanEval problem.
```

followed by the HumanEval function prompt.

### C. HumanEval loader

`app/dataset.py`:

- Downloads HumanEval from the upstream GitHub raw URL.
- Downloads compressed JSONL data.
- Decompresses it.
- Caches uncompressed JSONL locally.
- Parses records into `Problem` objects.
- Defaults to the first 25 records.

Each `Problem` contains:

- `task_id`
- `prompt`
- `entry_point`
- `visible_tests`
- `hidden_test`

Visible examples are extracted from lines containing `>>>`, but are not currently executed by the pipeline.

The hidden test is created from the canonical test and an invocation of the problem entry point.

### D. Baseline pipeline

`app/pipeline.py` performs:

1. Look up a task.
2. Build the generation prompt.
3. Generate candidate code.
4. Run the candidate with one hidden test in Docker.
5. Create a `Run` row.
6. Create `TestResult` rows.
7. Commit the transaction.
8. Return the run.

There is currently no retry, critique, repair, or iterative verification.

### E. Database model

`app/models.py` defines a `Run` model containing:

- `id`
- `task_id`
- `mode`
- `candidate_code`
- `hidden_passed`
- `duration_ms`
- `token_usage`
- `created_at`
- `test_results`

The mode enum contains:

```text
baseline
verified
```

The `verified` value is scaffolded but not used by a verified pipeline.

`TestResult` contains:

- `id`
- `run_id`
- `name`
- `passed`
- `stdout`
- `stderr`
- `error`

The relationship cascades child test results when a run is deleted.

### F. Docker sandbox

`app/sandbox.py` creates containers with:

- Networking disabled.
- Read-only filesystem.
- Non-root `sandbox` user.
- All Linux capabilities dropped.
- `no-new-privileges` enabled.
- PID limit of 64.
- 128 MB memory limit.
- Half a CPU limit.
- Writable but non-executable `/tmp`.
- Candidate code mounted read-only.
- Five-second wall-clock timeout by default.

Candidate code is mounted as:

```text
/candidate/candidate.py
```

Tests are passed through a base64-encoded environment variable named `SVA_TESTS_B64`.

Evidence includes pass/fail state, timeout state, stdout, stderr, exit code, duration, individual results, and error traces.

### G. Docker runner

`docker/runner.py`:

- Decodes test input.
- Loads candidate code.
- Executes candidate code.
- Captures import errors.
- Runs each test.
- Captures stdout and stderr.
- Returns structured JSON logs.

### H. Database migration

The initial Alembic migration creates:

- The PostgreSQL mode enum.
- `runs`.
- `test_results`.
- The foreign key relationship.
- The task ID index.
- Cascade delete behavior.

## 7. Features Currently Implemented

- FastAPI application.
- Baseline endpoint.
- Pydantic environment configuration.
- Optional OpenAI-compatible `base_url`.
- OpenAI SDK Responses API integration.
- Groq-compatible local configuration.
- HumanEval download and caching.
- Candidate generation.
- Docker sandbox execution.
- Basic sandbox restrictions.
- Hidden test evaluation.
- Structured test evidence.
- SQLAlchemy persistence.
- Alembic migration.
- PostgreSQL integration.
- Basic unit and integration tests.
- Five-task baseline validation script.
- Safe `.env.example` template.

## 8. Features Currently Incomplete

### True self-verification

`RunMode.verified` exists, but no workflow performs multiple attempts, critique, repair, re-execution, verification history, confidence scoring, or stopping criteria.

### Visible test execution

Visible tests are extracted but not currently run.

### Result retrieval

There is no endpoint for fetching a run, test-level evidence, generated code, or verification history.

### Asynchronous processing

LLM generation and Docker execution happen synchronously inside the HTTP request.

### Security controls

There is no authentication, authorization, rate limiting, quota system, request-size limit, or protection against unauthorized LLM usage.

### Evaluation framework

The validation script is a small smoke test, not a full experimental evaluation framework.

### Observability

There is limited logging and no structured tracing, metrics, request correlation, or detailed provider diagnostics.

## 9. Known Risks and Technical Debt

Analyze each risk carefully.

### Secret management

- The local `.env` contains a real-looking API key.
- The key must not be committed, logged, or exposed.
- The key should be revoked and rotated if it has been shared.
- `.env` must remain ignored.
- Database credentials are also present in defaults and examples.
- Production should use environment secrets rather than hard-coded credentials.

### LLM client behavior

`OpenAIClient.__init__()` accepts an explicit API key, but `generate()` checks only `settings.llm_api_key`. An injected key can therefore be rejected if the settings key is empty.

Investigate whether validation should use the effective resolved key.

Also investigate whether missing credentials fail during SDK construction before the intended runtime error is reached.

### Provider compatibility

An OpenAI-compatible URL does not guarantee full Responses API compatibility. Validate support for:

- Responses API behavior.
- Model availability.
- Error formats.
- Token usage fields.
- Output text behavior.
- Retry and timeout semantics.

### Dataset loading

Potential issues:

- No `raise_for_status()` after download.
- No checksum validation.
- No corrupted-cache recovery.
- Full cache reparsing on every lookup.
- Raw network failures are not normalized.
- Malformed records are not handled explicitly.

### Sandbox robustness

Potential issues:

- Candidate output is not size-limited.
- A candidate can produce very large logs.
- Only a container-level timeout exists.
- CPU and memory controls depend on Docker and host behavior.
- Broad `wait()` exceptions are treated like timeouts.
- Cleanup can be fragile if container creation fails.
- Empty tests can pass because `all([])` is true.
- Docker API errors are not fully normalized.
- The network test does not conclusively prove isolation.
- Arbitrary generated code remains dangerous even with restrictions.

### API behavior

Potential issues:

- Long-running synchronous work inside HTTP requests.
- No authentication.
- No rate limiting.
- No request cancellation.
- Limited validation.
- No result retrieval or pagination.
- No explicit response schemas.
- No idempotency behavior.
- No concurrency policy.

### Database and migrations

Potential issues:

- Hard-coded database credentials.
- Potential mismatch between timezone-aware Python datetimes and timezone-naive declarations.
- ORM nullability may not fully mirror migration nullability.
- No attempt/session tables for verification iterations.
- Limited query indexes.
- Operational files may not be included in package metadata.

### Testing gaps

Missing tests include:

- FastAPI endpoint behavior.
- LLM configuration behavior.
- Missing-key behavior.
- Base URL behavior.
- Mocked Groq provider behavior.
- PostgreSQL integration.
- Alembic migration execution.
- Docker image build.
- Malformed runner output.
- Empty test behavior.
- Output limits.
- Cleanup after failures.
- Dataset download failure behavior.
- Verified mode.
- Retry and repair logic.
- Security regressions.

## 10. Development Commands

Documented setup:

```powershell
docker build -t sva-sandbox:latest -f docker/sandbox.Dockerfile .
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

PostgreSQL:

```powershell
docker run --name sva-postgres `
  -e POSTGRES_PASSWORD=change-this-locally `
  -e POSTGRES_DB=sva `
  -p 5432:5432 `
  -d postgres:16
```

Baseline validation:

```powershell
python scripts/validate_baseline.py
```

Testing:

```powershell
pytest
pytest -m "not integration"
pytest --cov=app
```

Before trusting the project, verify:

- Python version.
- Docker daemon availability.
- PostgreSQL container status.
- Sandbox image existence.
- Migration state.
- HumanEval cache.
- Active environment variables.
- LLM model availability.

Remember that shell environment variables can override `.env` values.

## 11. Current State

The project is a working baseline prototype, not yet a complete self-verifying AI system.

Working components:

- LLM generation through the OpenAI SDK.
- Groq OpenAI-compatible endpoint.
- Supported Groq model `openai/gpt-oss-120b`.
- Configurable LLM base URL.
- HumanEval loading and caching.
- Docker sandbox execution.
- PostgreSQL storage.
- Alembic migration.
- Baseline API endpoint.
- Existing tests.

Verified runtime facts:

- Groq Responses API request succeeded.
- PostgreSQL container was running.
- Application connected to database `sva`.
- Existing tests passed with `5 passed`.

Current execution model:

```text
HTTP request
  -> load task
  -> generate one candidate
  -> run one hidden test in Docker
  -> store one run and test result
  -> return baseline result
```

Not yet implemented:

```text
critique
repair
multiple attempts
verification history
confidence
verified endpoint
```

The current maturity level is:

> A functional baseline research prototype with provider configuration, sandboxed execution, persistence, and initial tests, but without the actual iterative self-verification algorithm.

## 12. Required Analysis From You

After inspecting the actual repository, produce a detailed report with these sections:

1. Executive summary.
2. Repository map.
3. File-by-file responsibilities.
4. End-to-end request flow.
5. End-to-end data flow.
6. LLM configuration and provider abstraction.
7. Groq migration explanation.
8. PostgreSQL configuration explanation.
9. Docker sandbox security analysis.
10. Database schema and migration analysis.
11. Test and validation analysis.
12. Chronological change history.
13. Current capabilities.
14. Current limitations.
15. Bugs and technical debt ranked by severity.
16. Security review.
17. Reliability review.
18. Performance and scalability review.
19. Experimental validity review.
20. Proposed verified-mode architecture.
21. Database changes needed for verification attempts.
22. API changes needed for verification.
23. Testing strategy.
24. Observability strategy.
25. Prioritized implementation roadmap.
26. Recommended next milestone.
27. Risks and decisions requiring clarification.

For every recommendation:

- Explain the problem it solves.
- Identify the exact files likely to change.
- Explain whether a migration is required.
- Explain how it would be tested.
- Identify compatibility risks.
- Prefer small, incremental changes over a rewrite.

## 13. Recommended Next Milestone

Start with a small, testable milestone called:

> Implement a bounded verified pipeline with attempt persistence.

Proposed behavior:

1. Generate an initial candidate.
2. Execute it in the sandbox.
3. If it passes, mark the verified run successful.
4. If it fails, create a repair prompt containing the original task, candidate code, test output, and error details.
5. Ask the LLM for a repaired candidate.
6. Execute the repaired candidate.
7. Stop after a configurable maximum number of attempts.
8. Store every attempt and its evidence.
9. Return the final result and attempt history.

Before implementing this milestone, design the data model carefully. Decide whether the existing `Run` table should represent:

- One complete verification session.
- One individual attempt.
- A parent session with child attempts.

Do not implement this milestone until the data model, API contract, prompt format, stopping rules, and test strategy are clearly defined.

Preserve the existing OpenAI-compatible provider abstraction and Docker sandbox boundary unless there is a strong technical reason to change them.

---

## End of Prompt
