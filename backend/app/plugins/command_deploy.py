from __future__ import annotations
"""Plugin that executes a configured deployment command inside the worktree."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.process import run_command
from app.models import StepContext


@dataclass(slots=True)
class CommandDeployConfig:
    """Typed command execution settings for the command deployment plugin."""
    command: list[str]
    working_dir: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    timeout_sec: int | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "CommandDeployConfig":
        """Normalize command step configuration into a typed object."""
        command = raw.get("command") or []
        if isinstance(command, str):
            command = [command]
        environment = {str(key): str(value) for key, value in dict(raw.get("environment") or {}).items()}
        timeout_raw = raw.get("timeout_sec")
        timeout_sec = int(timeout_raw) if timeout_raw not in (None, "") else None
        return cls(
            command=[str(part) for part in command],
            working_dir=str(raw.get("working_dir", "")),
            environment=environment,
            timeout_sec=timeout_sec,
        )


class CommandDeployPlugin:
    """Execute an arbitrary command as a deployment step.

    This plugin is intentionally generic and serves as the bridge between the
    deployment workflow and whatever concrete build or release command the
    current project needs to run.
    """

    name = "command_deploy"

    async def validate(self, config: dict[str, Any]) -> None:
        """Ensure the command step contains an executable command list."""
        parsed = CommandDeployConfig.from_mapping(config)
        if not parsed.command:
            raise ValueError("command is required")

    async def execute(self, context: StepContext, config: dict[str, Any]) -> None:
        """Run the configured deployment command in the target worktree."""
        parsed = CommandDeployConfig.from_mapping(config)
        work_dir = context.work_dir
        if parsed.working_dir:
            candidate = Path(parsed.working_dir)
            work_dir = candidate if candidate.is_absolute() else context.work_dir / candidate

        env = os.environ.copy()
        env.update(parsed.environment)

        await run_command(
            parsed.command,
            logger=context.logger,
            cwd=work_dir,
            env=env,
            timeout=float(parsed.timeout_sec) if parsed.timeout_sec else None,
        )

    async def rollback(self, context: StepContext, config: dict[str, Any]) -> None:
        """Signal that command-based rollback is not yet implemented."""
        raise NotImplementedError("command_deploy rollback is not implemented")
