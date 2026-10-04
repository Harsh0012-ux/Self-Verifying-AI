import base64, json, logging, tempfile, time
from dataclasses import dataclass
from pathlib import Path
import docker
from docker.errors import ContainerError, ImageNotFound
from app.config import settings

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class SandboxTestEvidence:
    name: str; passed: bool; error: str | None; stdout: str = ""; stderr: str = ""
@dataclass(frozen=True)
class SandboxEvidence:
    passed: bool; timed_out: bool; stdout: str; stderr: str; exit_code: int | None; duration_ms: float; tests: list[SandboxTestEvidence]

class SandboxExecutor:
    def __init__(self, client=None, image: str | None = None, timeout_seconds: int = 5):
        self.client = client or docker.from_env(); self.image = image or settings.sandbox_image; self.timeout_seconds = timeout_seconds
    def run(self, candidate_code: str, tests: list[str]) -> SandboxEvidence:
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "candidate.py"; candidate.write_text(candidate_code, encoding="utf-8")
            env = {"SVA_TESTS_B64": base64.b64encode(json.dumps(tests).encode()).decode()}
            started = time.monotonic()
            try:
                output = self.client.containers.run(self.image, detach=True, network_disabled=True, read_only=True,
                    user="sandbox", cap_drop=["ALL"], security_opt=["no-new-privileges:true"], pids_limit=64,
                    mem_limit="128m", nano_cpus=500_000_000, tmpfs={"/tmp": "rw,noexec,nosuid,size=16m"},
                    volumes={str(candidate): {"bind": "/candidate/candidate.py", "mode": "ro"}}, environment=env)
                try: result = output.wait(timeout=self.timeout_seconds)
                except Exception:
                    output.kill(); return SandboxEvidence(False, True, "", "wall-clock timeout", None, (time.monotonic()-started)*1000, [])
                raw = output.logs(stdout=True, stderr=False).decode(errors="replace"); err = output.logs(stdout=False, stderr=True).decode(errors="replace")
                payload = json.loads(raw.splitlines()[-1]) if raw.strip() else {"results": []}
                evidence = [SandboxTestEvidence(**x) for x in payload["results"]]
                if not evidence:
                    logger.warning("Sandbox produced no test evidence; treating candidate as failed")
                passed = bool(evidence) and all(x.passed for x in evidence) and result["StatusCode"] == 0
                return SandboxEvidence(passed, False, raw, err, result["StatusCode"], (time.monotonic()-started)*1000, evidence)
            except ImageNotFound as e: raise RuntimeError(f"Sandbox image missing: build {self.image}") from e
            finally:
                try: output.remove(force=True)
                except UnboundLocalError: pass
