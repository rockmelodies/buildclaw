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

    # Knowledge base readiness checks
    knowledge_enabled = config.knowledge.enabled
    knowledge_root = Path(config.knowledge.knowledge_root)
    knowledge_writable = _is_writable_directory(knowledge_root) if knowledge_enabled else True

    # Check for common build tool availability when knowledge system is enabled
    build_tools = {}
    if knowledge_enabled:
        for tool in ("java", "mvn", "gradle", "php", "composer", "ruby", "bundle", "go", "node", "npm", "yarn", "python3", "pip3", "cargo", "dotnet"):
            build_tools[tool] = shutil.which(tool) or ""

    base_ok = bool(git_path) and workspace_exists and workspace_writable and bool(config.repositories)
    knowledge_ok = not knowledge_enabled or knowledge_writable

    return {
        "ok": base_ok and knowledge_ok,
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
            "knowledge_base": {
                "ok": knowledge_ok,
                "enabled": knowledge_enabled,
                "path": str(knowledge_root),
                "writable": knowledge_writable,
                "auto_detect": config.knowledge.auto_detect,
                "auto_learn": config.knowledge.auto_learn,
            },
            "build_tools": {
                "ok": True,
                "available": {k: bool(v) for k, v in build_tools.items()},
            } if knowledge_enabled else {
                "ok": True,
                "note": "knowledge system disabled, build tool check skipped",
            },
        },
    }


def prepare_runtime_directories(config: AppConfig) -> None:
    """Create directories that must exist before deployments can run."""

    workspace_root = Path(config.workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)

    # Ensure knowledge base directories exist when the knowledge system is enabled
    if config.knowledge.enabled:
        knowledge_root = Path(config.knowledge.knowledge_root)
        for subdir in ("recipes", "learnings", "patterns"):
            (knowledge_root / subdir).mkdir(parents=True, exist_ok=True)


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
