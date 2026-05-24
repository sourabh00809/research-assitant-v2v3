from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from .config import settings


def run_sandbox(script: str, timeout_seconds: int = 5) -> dict:
    if settings.sandbox_backend == "docker":
        docker_result = run_python_docker_sandbox(script, timeout_seconds)
        if docker_result.get("backend") == "docker":
            return docker_result
    return run_python_sandbox(script, timeout_seconds)


def run_python_docker_sandbox(script: str, timeout_seconds: int = 5) -> dict:
    try:
        import docker  # type: ignore
    except Exception as exc:
        return {"backend": "local", "error": str(exc)}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        script_path = tmp_path / "script.py"
        script_path.write_text(script, encoding="utf-8")
        client = docker.from_env()
        try:
            container = client.containers.run(
                settings.sandbox_image,
                ["python", "/work/script.py"],
                detach=True,
                network_disabled=True,
                mem_limit=f"{settings.sandbox_memory_mb}m",
                cpu_quota=settings.sandbox_cpu_quota,
                volumes={str(tmp_path): {"bind": "/work", "mode": "rw"}},
                working_dir="/work",
            )
            result = container.wait(timeout=timeout_seconds)
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            container.remove(force=True)
            artifacts = [item.name for item in tmp_path.iterdir() if item.name != "script.py"]
            return {
                "backend": "docker",
                "exit_code": int(result.get("StatusCode", 1)),
                "stdout": logs,
                "stderr": "",
                "network_disabled": True,
                "timeout_seconds": timeout_seconds,
                "artifacts": artifacts,
            }
        except Exception as exc:
            try:
                container.remove(force=True)  # type: ignore[name-defined]
            except Exception:
                pass
            return {
                "backend": "docker",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
                "network_disabled": True,
                "timeout_seconds": timeout_seconds,
                "artifacts": [],
            }


def run_python_sandbox(script: str, timeout_seconds: int = 5) -> dict:
    """Local safe fallback for V3 tests. Docker execution should replace this in production."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "script.py"
        guarded_script = "\n".join(
            [
                "import socket",
                "def _ai_scientist_blocked_socket(*args, **kwargs):",
                "    raise OSError('network disabled by AI Scientist sandbox')",
                "socket.socket = _ai_scientist_blocked_socket",
                script,
            ]
        )
        path.write_text(guarded_script, encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=tmp,
            )
            return {
                "backend": "local",
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "network_disabled": True,
                "timeout_seconds": timeout_seconds,
                "artifacts": [],
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "backend": "local",
                "exit_code": -1,
                "stdout": exc.stdout or "",
                "stderr": "Timed out",
                "network_disabled": True,
                "timeout_seconds": timeout_seconds,
                "artifacts": [],
            }
