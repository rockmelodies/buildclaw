from __future__ import annotations
"""Runtime environment validation helpers used by readiness checks and tooling."""

import os
import shutil
from pathlib import Path
from typing import Any

from app.config import AppConfig


def collect_runtime_checks(config: AppConfig) -> dict[str, Any]:
    """Collect lightweight readiness signals for the current runtime environment.

    The checks are intentionally local and fast so they are safe to run from
    HTTP readiness probes and CLI doctor commands.
    """

    workspace_root = Path(config.workspace_root)
    git_path = shutil.which("git")
    workspace_exists = workspace_root.exists()
    workspace_writable = _is_writable_directory(workspace_root)

    return {
        "ok": bool(git_path) and workspace_exists and workspace_writable and bool(config.repositories),
        "checks": {
            "git_available": {
                "ok": bool(git_path),
                "path": git_path or "",
            },
            "workspace_root": {
                "ok": workspace_exists and workspace_writable,
                "path": str(workspace_root),
                "exists": workspace_exists,
                "writable": workspace_writable,
            },
            "repositories_configured": {
                "ok": bool(config.repositories),
                "count": len(config.repositories),
            },
            "python_version": {
                "ok": True,
                "value": os.sys.version.split()[0],
            },
        },
    }


def prepare_runtime_directories(config: AppConfig) -> None:
    """Create directories that must exist before deployments can run."""

    workspace_root = Path(config.workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)


def _is_writable_directory(path: Path) -> bool:
    """Return whether a directory exists and supports file creation."""

    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".buildclaw-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError:
        return False
    return True
