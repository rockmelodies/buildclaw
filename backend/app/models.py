from __future__ import annotations
"""Shared in-memory data structures used across services and plugins."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DeploymentTrigger:
    """Represents a deployment request produced by an incoming webhook event."""
    repository_id: str
    branch: str
    commit_sha: str
    delivery_id: str = ""


@dataclass(slots=True)
class StepContext:
    """Execution context passed to every deployment plugin."""
    repository_id: str
    branch: str
    commit_sha: str
    work_dir: Path
    logger: logging.Logger


@dataclass(slots=True)
class WorkflowStep:
    """A normalized workflow step ready for execution by the workflow engine."""
    name: str
    plugin: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowPlan:
    """A fully materialized deployment plan produced by the service layer."""
    repository_id: str
    branch: str
    commit_sha: str
    work_dir: Path
    steps: list[WorkflowStep]
    logger: logging.Logger
