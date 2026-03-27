from __future__ import annotations
"""Typed configuration objects and YAML loading helpers for the backend."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class ServerConfig:
    """Network binding options for the FastAPI server."""
    address: str = "0.0.0.0"
    port: int = 8080


@dataclass(slots=True)
class GitAuthConfig:
    """Repository authentication settings used by the git pull plugin."""
    ssh_private_key_base64: str = ""
    https_username: str = ""
    https_token: str = ""


@dataclass(slots=True)
class StepConfig:
    """A single deployment step bound to a concrete plugin implementation."""
    name: str
    plugin: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BranchConfig:
    """Branch-specific deployment rules and their step definitions."""
    pattern: str
    worktree: str = ""
    steps: list[StepConfig] = field(default_factory=list)


@dataclass(slots=True)
class RepositoryConfig:
    """Repository-level deployment settings resolved from YAML configuration."""
    id: str
    name: str
    git_url: str
    webhook_secret: str
    auth: GitAuthConfig = field(default_factory=GitAuthConfig)
    branches: list[BranchConfig] = field(default_factory=list)


@dataclass(slots=True)
class AppConfig:
    """Top-level application configuration object."""
    server: ServerConfig = field(default_factory=ServerConfig)
    workspace_root: str = "./workspace"
    repositories: list[RepositoryConfig] = field(default_factory=list)

    def validate(self) -> None:
        """Fail fast on incomplete configuration before the server starts."""
        if not self.workspace_root:
            raise ValueError("workspace_root is required")
        if not self.repositories:
            raise ValueError("at least one repository must be configured")

        seen: set[str] = set()
        for repo in self.repositories:
            if not repo.id:
                raise ValueError("repository.id is required")
            if repo.id in seen:
                raise ValueError(f"repository.id {repo.id!r} is duplicated")
            seen.add(repo.id)
            if not repo.git_url:
                raise ValueError(f"repository {repo.id!r} git_url is required")
            if not repo.webhook_secret:
                raise ValueError(f"repository {repo.id!r} webhook_secret is required")
            if not repo.branches:
                raise ValueError(f"repository {repo.id!r} must define at least one branch rule")
            for branch in repo.branches:
                if not branch.pattern:
                    raise ValueError(f"repository {repo.id!r} has a branch rule without pattern")
                for step in branch.steps:
                    if not step.plugin:
                        raise ValueError(
                            f"repository {repo.id!r} branch {branch.pattern!r} has a step without plugin"
                        )


def load_config() -> AppConfig:
    """Load configuration from YAML and overlay supported environment variables."""
    _load_dotenv_files()
    config_path = Path(os.getenv("BUILDCLAW_CONFIG", "config.yaml"))
    if not config_path.exists():
        raise FileNotFoundError(f"config file {config_path!s} not found")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = AppConfig(
        server=_parse_server(raw.get("server") or {}),
        workspace_root=os.getenv("BUILDCLAW_WORKSPACE", raw.get("workspace_root", "./workspace")),
        repositories=_parse_repositories(raw.get("repositories") or []),
    )
    config.validate()
    return config


def _load_dotenv_files() -> None:
    """Load supported `.env` files into the process environment if unset.

    Precedence is:
    1. existing process environment
    2. file from `BUILDCLAW_ENV_FILE`
    3. local `.env`
    """

    candidate_paths: list[Path] = []
    custom_env_path = os.getenv("BUILDCLAW_ENV_FILE")
    if custom_env_path:
        candidate_paths.append(Path(custom_env_path))
    candidate_paths.append(Path(".env"))

    for path in candidate_paths:
        if not path.exists():
            continue
        _apply_env_file(path)


def _apply_env_file(path: Path) -> None:
    """Parse a minimal dotenv file format without overriding existing env vars."""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _parse_server(raw: dict[str, Any]) -> ServerConfig:
    """Parse server settings while allowing env vars to override YAML values."""
    address = os.getenv("BUILDCLAW_ADDR", raw.get("address", "0.0.0.0"))
    port = int(os.getenv("BUILDCLAW_PORT", raw.get("port", 8080)))
    return ServerConfig(address=address, port=port)


def _parse_repositories(raw_repositories: list[dict[str, Any]]) -> list[RepositoryConfig]:
    """Convert raw repository dictionaries into typed repository objects."""
    repositories: list[RepositoryConfig] = []
    for raw_repo in raw_repositories:
        repositories.append(
            RepositoryConfig(
                id=str(raw_repo.get("id", "")),
                name=str(raw_repo.get("name", "")),
                git_url=str(raw_repo.get("git_url", "")),
                webhook_secret=str(raw_repo.get("webhook_secret", "")),
                auth=_parse_auth(raw_repo.get("auth") or {}),
                branches=_parse_branches(raw_repo.get("branches") or []),
            )
        )
    return repositories


def _parse_auth(raw: dict[str, Any]) -> GitAuthConfig:
    """Parse git authentication fields from a repository config block."""
    return GitAuthConfig(
        ssh_private_key_base64=str(raw.get("ssh_private_key_base64", "")),
        https_username=str(raw.get("https_username", "")),
        https_token=str(raw.get("https_token", "")),
    )


def _parse_branches(raw_branches: list[dict[str, Any]]) -> list[BranchConfig]:
    """Parse per-branch deployment rules and their plugin-backed steps."""
    branches: list[BranchConfig] = []
    for raw_branch in raw_branches:
        steps = [
            StepConfig(
                name=str(raw_step.get("name", raw_step.get("plugin", ""))),
                plugin=str(raw_step.get("plugin", "")),
                config=dict(raw_step.get("config") or {}),
            )
            for raw_step in raw_branch.get("steps") or []
        ]
        branches.append(
            BranchConfig(
                pattern=str(raw_branch.get("pattern", "")),
                worktree=str(raw_branch.get("worktree", "")),
                steps=steps,
            )
        )
    return branches
