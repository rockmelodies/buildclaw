from __future__ import annotations
"""Helpers for running subprocesses while streaming logs into application logs."""

import asyncio
import logging
import shlex
from pathlib import Path
from typing import Mapping


async def run_command(
    command: list[str],
    *,
    logger: logging.Logger,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    display_command: list[str] | None = None,
    timeout: float | None = None,
) -> None:
    """Execute a subprocess, stream combined output, and raise on failure.

    The helper is shared by multiple plugins so command execution semantics stay
    consistent across git operations and deployment commands.
    """
    shown = display_command or command
    logger.info("running command: %s", shlex.join(shown))

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        env=dict(env) if env else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def _drain_process_output() -> int:
        """Read process output incrementally to avoid deadlocks on large logs."""
        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            logger.info(line.decode("utf-8", errors="replace").rstrip())
        return await process.wait()

    try:
        return_code = await asyncio.wait_for(_drain_process_output(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        # A hard kill is used here because deploy commands are typically shell
        # operations and we want a predictable terminal state after timeout.
        process.kill()
        await process.wait()
        raise RuntimeError(f"command timed out after {timeout} seconds: {shlex.join(shown)}") from exc

    if return_code != 0:
        raise RuntimeError(f"command failed with exit code {return_code}: {shlex.join(shown)}")
