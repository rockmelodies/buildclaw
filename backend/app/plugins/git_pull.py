from __future__ import annotations
"""Git synchronization plugin used as the first step of a deployment."""

import base64
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse, urlunparse

from app.core.process import run_command
from app.models import StepContext


@dataclass(slots=True)
class GitPullConfig:
    """Normalized configuration consumed by the git pull plugin."""
    repository_url: str
    branch: str
    commit_sha: str = ""
    work_dir: str = ""
    ssh_private_key_base64: str = ""
    https_username: str = ""
    https_token: str = ""
    max_retries: int = 3

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "GitPullConfig":
        """Create a typed config object from a generic step config mapping."""
        return cls(
            repository_url=str(raw.get("repository_url", "")),
            branch=str(raw.get("branch", "")),
            commit_sha=str(raw.get("commit_sha", "")),
            work_dir=str(raw.get("work_dir", "")),
            ssh_private_key_base64=str(raw.get("ssh_private_key_base64", "")),
            https_username=str(raw.get("https_username", "")),
            https_token=str(raw.get("https_token", "")),
            max_retries=int(raw.get("max_retries", 3) or 3),
        )


class GitPullPlugin:
    """Clone or update a repository and align it to the requested commit."""

    name = "git_pull"

    async def validate(self, config: dict[str, Any]) -> None:
        """Reject incomplete git pull configurations before execution starts."""
        parsed = GitPullConfig.from_mapping(config)
        if not parsed.repository_url:
            raise ValueError("repository_url is required")
        if not parsed.branch:
            raise ValueError("branch is required")
        if not parsed.work_dir:
            raise ValueError("work_dir is required")

    async def execute(self, context: StepContext, config: dict[str, Any]) -> None:
        """Run the git synchronization flow with bounded retries."""
        parsed = GitPullConfig.from_mapping(config)
        retries = max(parsed.max_retries, 1)
        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            context.logger.info(
                "[git_pull] attempt %s/%s for %s@%s",
                attempt,
                retries,
                _redact_url(parsed.repository_url),
                parsed.branch,
            )
            try:
                await self._run_once(context, parsed)
                context.logger.info("[git_pull] repository ready at %s", parsed.work_dir)
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                context.logger.warning("[git_pull] attempt %s failed: %s", attempt, exc)

        raise RuntimeError(f"git pull failed after {retries} attempts") from last_error

    async def rollback(self, context: StepContext, config: dict[str, Any]) -> None:
        """Signal that explicit git rollback is not yet supported."""
        raise NotImplementedError("git_pull rollback is not implemented")

    async def _run_once(self, context: StepContext, config: GitPullConfig) -> None:
        """Perform a single clone/fetch/checkout attempt."""
        work_dir = Path(config.work_dir)
        work_dir.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        repo_url = config.repository_url
        key_file_path: str | None = None

        try:
            if config.ssh_private_key_base64:
                # The SSH key is materialized only for the lifetime of this
                # command sequence so secrets are not left on disk.
                key_file_path = _write_private_key(config.ssh_private_key_base64)
                env["GIT_SSH_COMMAND"] = (
                    f'ssh -i "{key_file_path}" -o StrictHostKeyChecking=no -o IdentitiesOnly=yes'
                )

            if config.https_token:
                repo_url = _with_https_credentials(
                    config.repository_url,
                    username=config.https_username or "git",
                    token=config.https_token,
                )

            git_dir = work_dir / ".git"
            if not git_dir.exists():
                if work_dir.exists():
                    # If a directory exists but is not a git repository, start
                    # from a clean location to avoid deploying from stale files.
                    shutil.rmtree(work_dir, ignore_errors=True)
                await run_command(
                    ["git", "clone", repo_url, str(work_dir)],
                    logger=context.logger,
                    env=env,
                    display_command=["git", "clone", _redact_url(config.repository_url), str(work_dir)],
                )

            await run_command(["git", "-C", str(work_dir), "fetch", "--all", "--prune"], logger=context.logger, env=env)
            await run_command(
                ["git", "-C", str(work_dir), "checkout", "--force", "-B", config.branch, f"origin/{config.branch}"],
                logger=context.logger,
                env=env,
            )

            if config.commit_sha:
                # Webhook payloads may request a specific commit. We explicitly
                # checkout that SHA so deployment is deterministic.
                await run_command(
                    ["git", "-C", str(work_dir), "checkout", "--force", config.commit_sha],
                    logger=context.logger,
                    env=env,
                )
            else:
                await run_command(
                    ["git", "-C", str(work_dir), "reset", "--hard", f"origin/{config.branch}"],
                    logger=context.logger,
                    env=env,
                )
        finally:
            if key_file_path:
                Path(key_file_path).unlink(missing_ok=True)


def _write_private_key(encoded_key: str) -> str:
    """Decode a base64 SSH key into a temporary file for git to consume."""
    key_bytes = base64.b64decode(encoded_key)
    file_descriptor, file_path = tempfile.mkstemp(prefix="buildclaw-key-", text=True)
    os.close(file_descriptor)
    Path(file_path).write_bytes(key_bytes)
    return file_path


def _with_https_credentials(url: str, *, username: str, token: str) -> str:
    """Embed HTTPS credentials into a clone URL for non-SSH authentication."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return url

    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    auth = f"{quote(username, safe='')}:{quote(token, safe='')}"
    return urlunparse(parsed._replace(netloc=f"{auth}@{host}"))


def _redact_url(url: str) -> str:
    """Remove embedded credentials before a repository URL is logged."""
    parsed = urlparse(url)
    if not parsed.scheme:
        return url
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=host))
