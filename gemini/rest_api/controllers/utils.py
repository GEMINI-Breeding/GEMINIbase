"""
Utility endpoints used by the GEMINI-App frontend.

- GET /api/utils/capabilities — advertise optional-dependency availability
  (AgRowStitch, torch/CUDA/MPS, CPU count) so the frontend can warn before
  launching steps that need them.
- GET /api/utils/logs — recent backend log lines from an in-memory ring
  buffer, consumed by the frontend console tab.
- GET /api/utils/health-check — simple boolean liveness probe.
- GET /api/utils/docker-check — docker-daemon availability (so the UI can
  surface setup errors, e.g., "Docker isn't running").

This controller deliberately does not depend on the full stack (db, redis,
minio), so it responds reliably even when those backends are unhealthy.
"""
from __future__ import annotations

import collections
import importlib.util
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, List, Optional

from litestar.controller import Controller
from litestar.di import Provide
from litestar.handlers import get

from gemini.api.user import User
from gemini.rest_api.dependencies import require_superuser

# ────────────────────────────────────────────────────────────────────────────
# In-memory log ring buffer — attached to the root logger at import time so
# every log record emitted while the process lives is captured for the UI.
# ────────────────────────────────────────────────────────────────────────────

_LOG_BUFFER_SIZE = 500
_log_buffer: collections.deque = collections.deque(maxlen=_LOG_BUFFER_SIZE)


class _RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _log_buffer.append(
                {
                    "level": record.levelname,
                    "message": self.format(record),
                    "ts": record.created,
                }
            )
        except Exception:
            self.handleError(record)


_ring_handler = _RingBufferHandler()
_ring_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
# Only attach once — import-safe under uvicorn --reload.
_root_logger = logging.getLogger()
if not any(isinstance(h, _RingBufferHandler) for h in _root_logger.handlers):
    _root_logger.addHandler(_ring_handler)


# ────────────────────────────────────────────────────────────────────────────

def _agrowstitch_status() -> dict:
    """Report whether AgRowStitch is importable in this environment."""
    available = False
    path: Optional[str] = None
    env_path = os.environ.get("AGROWSTITCH_PATH")

    # Candidate locations: AGROWSTITCH_PATH env var, a sibling repo clone, or
    # a vendored copy under the stitch worker (Phase 3 landing zone).
    candidates: List[Path] = []
    if env_path:
        candidates.append(Path(env_path))
    # Sibling-repo checkout next to GEMINIbase (mirrors the old backend's convention).
    candidates.append(Path(__file__).resolve().parents[4] / "AgRowStitch" / "AgRowStitch.py")
    # Phase 3 vendor location (won't exist yet; try anyway).
    candidates.append(Path(__file__).resolve().parents[2] / "workers" / "stitch" / "AgRowStitch.py")

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location("_agrowstitch_check", candidate)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "run"):
                available = True
                path = str(candidate)
                break
        except Exception:
            continue

    return {"available": available, "path": path}


def _torch_status() -> dict:
    """Report torch version and GPU backend availability, gracefully absent."""
    try:
        import torch  # type: ignore
    except ImportError:
        return {"torch_version": None, "cuda_available": False, "mps_available": False}
    return {
        "torch_version": getattr(torch, "__version__", None),
        "cuda_available": bool(getattr(torch.cuda, "is_available", lambda: False)()),
        "mps_available": bool(
            getattr(torch.backends, "mps", None)
            and getattr(torch.backends.mps, "is_available", lambda: False)()
        ),
    }


def _docker_status() -> dict:
    """Check whether a Docker daemon is reachable from inside this process."""
    extra_paths = [
        "/usr/local/bin/docker",
        "/opt/homebrew/bin/docker",
        "/usr/bin/docker",
        os.path.expanduser("~/.docker/bin/docker"),
    ]
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        for p in extra_paths:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                docker_bin = p
                break
    if docker_bin is None:
        return {"available": False, "reason": "not_installed"}

    env = os.environ.copy()
    user_socket = os.path.expanduser("~/.docker/run/docker.sock")
    if os.path.exists(user_socket) and "DOCKER_HOST" not in env:
        env["DOCKER_HOST"] = f"unix://{user_socket}"

    try:
        result = subprocess.run(
            [docker_bin, "info"],
            capture_output=True,
            timeout=10,
            env=env,
        )
        if result.returncode == 0:
            return {"available": True}
        stderr = (result.stderr or b"").decode(errors="replace")
        if "permission denied" in stderr.lower():
            return {"available": False, "reason": "permission_denied"}
        return {"available": False, "reason": stderr[:200]}
    except Exception as e:
        return {"available": False, "reason": str(e)}


# ────────────────────────────────────────────────────────────────────────────

class UtilsController(Controller):

    dependencies = {
        "superuser": Provide(require_superuser, sync_to_thread=True),
    }

    @get(path="/health-check", sync_to_thread=False)
    def health_check(self) -> bool:
        return True

    @get(path="/capabilities", sync_to_thread=True)
    def capabilities(self) -> dict:
        torch = _torch_status()
        return {
            "agrowstitch": _agrowstitch_status(),
            "torch_version": torch["torch_version"],
            "cuda_available": torch["cuda_available"],
            "mps_available": torch["mps_available"],
            "cpu_count": os.cpu_count() or 1,
        }

    @get(path="/logs", sync_to_thread=False)
    def get_logs(
        self,
        superuser: User,
        limit: Optional[int] = None,
        level: Optional[str] = None,
        since: Optional[float] = None,
    ) -> List[dict]:
        # Iterate a snapshot so concurrent writes don't skew the response.
        lines: List[dict] = list(_log_buffer)
        if level:
            wanted = level.upper()
            lines = [l for l in lines if l.get("level") == wanted]
        if since is not None:
            lines = [l for l in lines if float(l.get("ts", 0)) >= since]
        if limit is not None and limit > 0:
            lines = lines[-limit:]
        return lines

    @get(path="/docker-check", sync_to_thread=True)
    def docker_check(self) -> dict:
        return _docker_status()
