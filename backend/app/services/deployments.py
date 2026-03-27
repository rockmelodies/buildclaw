from __future__ import annotations
"""Deployment orchestration service built on top of the event bus and workflow engine."""

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from uuid import uuid4

from app.core.event_bus import AsyncEventBus, Event
from app.core.workflow import (
    EVENT_DEPLOYMENT_COMPLETED,
    EVENT_DEPLOYMENT_FAILED,
    EVENT_DEPLOYMENT_STARTED,
    EVENT_DEPLOYMENT_TRIGGERED,
    WorkflowEngine,
)
from app.models import DeploymentRecord, DeploymentTrigger, WorkflowPlan, WorkflowStep
from app.services.repositories import RepositoryCatalog


class DeploymentService:
    """Accept deployment triggers and execute them asynchronously.

    Request handlers only publish deployment intents. This service owns the
    long-running consumer loop that translates those intents into concrete
    workflow plans and executes them in background tasks.
    """

    def __init__(self, repositories: RepositoryCatalog, event_bus: AsyncEventBus, workflow: WorkflowEngine) -> None:
        self._repositories = repositories
        self._event_bus = event_bus
        self._workflow = workflow
        self._subscription_id: str | None = None
        self._events: asyncio.Queue[Event] | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._records: dict[str, DeploymentRecord] = {}
        self._history: deque[str] = deque(maxlen=50)
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Subscribe to deployment events and start the background consumer."""
        self._subscription_id, self._events = await self._event_bus.subscribe(maxsize=32)
        self._consumer_task = asyncio.create_task(self._consume_events())

    async def stop(self) -> None:
        """Stop the background consumer and detach from the event bus."""
        if self._consumer_task:
            self._consumer_task.cancel()
            await asyncio.gather(self._consumer_task, return_exceptions=True)
        if self._subscription_id:
            await self._event_bus.unsubscribe(self._subscription_id)

    async def trigger_deployment(self, trigger: DeploymentTrigger) -> str:
        """Validate a trigger and publish it for asynchronous processing."""
        repository, branch_rule, worktree = self._repositories.resolve_branch(trigger.repository_id, trigger.branch)
        record = DeploymentRecord(
            deployment_id=uuid4().hex[:12],
            repository_id=trigger.repository_id,
            branch=trigger.branch,
            commit_sha=trigger.commit_sha,
            delivery_id=trigger.delivery_id,
            status="queued",
            work_dir=str(worktree),
            matched_pattern=branch_rule.pattern,
            steps_total=len(branch_rule.steps) + 1,
        )
        await self._store_record(record)
        await self._event_bus.publish(Event(type=EVENT_DEPLOYMENT_TRIGGERED, payload=trigger))
        return record.deployment_id

    async def _consume_events(self) -> None:
        """Continuously receive deployment events and fork execution tasks."""
        assert self._events is not None
        while True:
            event = await self._events.get()
            if event.type != EVENT_DEPLOYMENT_TRIGGERED:
                continue
            trigger = event.payload
            if not isinstance(trigger, DeploymentTrigger):
                continue
            asyncio.create_task(self._execute(trigger))

    async def _execute(self, trigger: DeploymentTrigger) -> None:
        """Build a workflow plan and execute it for a single trigger."""
        repository, branch_rule, worktree = self._repositories.resolve_branch(trigger.repository_id, trigger.branch)
        logger = logging.getLogger(f"buildclaw.deploy.{trigger.repository_id}.{trigger.branch.replace('/', '_')}")
        record = await self._find_record(trigger)

        # Every deployment starts with a git sync so later steps always operate
        # on the exact repository state requested by the webhook payload.
        steps = [
            WorkflowStep(
                name="git-pull",
                plugin="git_pull",
                config={
                    "repository_url": repository.git_url,
                    "branch": trigger.branch,
                    "commit_sha": trigger.commit_sha,
                    "work_dir": str(worktree),
                    "ssh_private_key_base64": repository.auth.ssh_private_key_base64,
                    "https_username": repository.auth.https_username,
                    "https_token": repository.auth.https_token,
                    "max_retries": 3,
                },
            )
        ]
        steps.extend(
            WorkflowStep(name=step.name or step.plugin, plugin=step.plugin, config=step.config)
            for step in branch_rule.steps
        )

        plan = WorkflowPlan(
            repository_id=trigger.repository_id,
            branch=trigger.branch,
            commit_sha=trigger.commit_sha,
            work_dir=worktree,
            steps=steps,
            logger=logger,
        )

        if record:
            await self._mark_running(record.deployment_id)
        await self._event_bus.publish(Event(type=EVENT_DEPLOYMENT_STARTED, payload={"deployment_id": record.deployment_id if record else ""}))

        logger.info("starting deployment for repo=%s branch=%s commit=%s", trigger.repository_id, trigger.branch, trigger.commit_sha)
        try:
            for index, step in enumerate(plan.steps, start=1):
                if record:
                    await self._mark_step_started(record.deployment_id, step.name)
                plugin = self._workflow._registry.get(step.plugin)
                context = self._workflow.create_step_context(plan)
                await plugin.validate(step.config)
                await plugin.execute(context, step.config)
                if record:
                    await self._mark_step_completed(record.deployment_id, step.name, index)
        except Exception as exc:  # noqa: BLE001
            if record:
                await self._mark_failed(record.deployment_id, str(exc) or "Execution failed")
            await self._event_bus.publish(Event(type=EVENT_DEPLOYMENT_FAILED, payload={"deployment_id": record.deployment_id if record else ""}))
            logger.exception("deployment failed for repo=%s branch=%s", trigger.repository_id, trigger.branch)
            return

        if record:
            await self._mark_succeeded(record.deployment_id)
        await self._event_bus.publish(Event(type=EVENT_DEPLOYMENT_COMPLETED, payload={"deployment_id": record.deployment_id if record else ""}))
        logger.info("deployment completed for repo=%s branch=%s", trigger.repository_id, trigger.branch)

    async def list_recent(self, limit: int = 12) -> list[DeploymentRecord]:
        """Return recent deployment records in reverse chronological order."""

        async with self._lock:
            deployment_ids = list(self._history)[-limit:]
            records = [self._records[deployment_id] for deployment_id in deployment_ids if deployment_id in self._records]
        return list(reversed(records))

    async def get_dashboard_data(self) -> dict[str, object]:
        """Build a dashboard-oriented snapshot for the UI and JSON APIs."""

        recent = await self.list_recent(limit=8)
        queued = sum(1 for record in recent if record.status == "queued")
        running = sum(1 for record in recent if record.status == "running")
        succeeded = sum(1 for record in recent if record.status == "succeeded")
        failed = sum(1 for record in recent if record.status == "failed")

        repositories = []
        for repository in self._repositories.list():
            repositories.append(
                {
                    "id": repository.id,
                    "name": repository.name,
                    "git_url": repository.git_url,
                    "branch_rules": [
                        {
                            "pattern": branch.pattern,
                            "worktree": branch.worktree,
                            "steps": [step.name or step.plugin for step in branch.steps],
                        }
                        for branch in repository.branches
                    ],
                }
            )

        return {
            "summary": {
                "repositories": len(repositories),
                "queued": queued,
                "running": running,
                "succeeded": succeeded,
                "failed": failed,
            },
            "repositories": repositories,
            "deployments": [self._serialize_record(record) for record in recent],
        }

    async def _store_record(self, record: DeploymentRecord) -> None:
        async with self._lock:
            self._records[record.deployment_id] = record
            self._history.append(record.deployment_id)

    async def _find_record(self, trigger: DeploymentTrigger) -> DeploymentRecord | None:
        async with self._lock:
            for deployment_id in reversed(self._history):
                record = self._records.get(deployment_id)
                if (
                    record
                    and record.repository_id == trigger.repository_id
                    and record.branch == trigger.branch
                    and record.commit_sha == trigger.commit_sha
                    and record.delivery_id == trigger.delivery_id
                    and record.status == "queued"
                ):
                    return record
        return None

    async def _mark_running(self, deployment_id: str) -> None:
        async with self._lock:
            record = self._records[deployment_id]
            record.status = "running"
            record.started_at = datetime.now(timezone.utc)

    async def _mark_step_started(self, deployment_id: str, step_name: str) -> None:
        async with self._lock:
            record = self._records[deployment_id]
            record.active_step = step_name
            record.recent_logs.append(f"Starting step: {step_name}")
            record.recent_logs = record.recent_logs[-10:]

    async def _mark_step_completed(self, deployment_id: str, step_name: str, completed_count: int) -> None:
        async with self._lock:
            record = self._records[deployment_id]
            record.active_step = step_name
            record.steps_completed = completed_count
            record.recent_logs.append(f"Completed step: {step_name}")
            record.recent_logs = record.recent_logs[-10:]

    async def _mark_failed(self, deployment_id: str, error: str) -> None:
        async with self._lock:
            record = self._records[deployment_id]
            record.status = "failed"
            record.error = error
            record.finished_at = datetime.now(timezone.utc)
            record.recent_logs.append(error)
            record.recent_logs = record.recent_logs[-10:]

    async def _mark_succeeded(self, deployment_id: str) -> None:
        async with self._lock:
            record = self._records[deployment_id]
            record.status = "succeeded"
            record.finished_at = datetime.now(timezone.utc)
            record.active_step = ""
            record.recent_logs.append("Deployment finished successfully")
            record.recent_logs = record.recent_logs[-10:]

    def _serialize_record(self, record: DeploymentRecord) -> dict[str, object]:
        return {
            "deployment_id": record.deployment_id,
            "repository_id": record.repository_id,
            "branch": record.branch,
            "commit_sha": record.commit_sha,
            "delivery_id": record.delivery_id,
            "status": record.status,
            "created_at": record.created_at.isoformat(),
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "finished_at": record.finished_at.isoformat() if record.finished_at else None,
            "work_dir": record.work_dir,
            "matched_pattern": record.matched_pattern,
            "steps_total": record.steps_total,
            "steps_completed": record.steps_completed,
            "active_step": record.active_step,
            "error": record.error,
            "recent_logs": list(record.recent_logs),
        }
