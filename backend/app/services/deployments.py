from __future__ import annotations
"""Deployment orchestration service built on top of the event bus and workflow engine."""

import asyncio
import logging

from app.core.event_bus import AsyncEventBus, Event
from app.core.workflow import EVENT_DEPLOYMENT_TRIGGERED, WorkflowEngine
from app.models import DeploymentTrigger, WorkflowPlan, WorkflowStep
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

    async def trigger_deployment(self, trigger: DeploymentTrigger) -> None:
        """Validate a trigger and publish it for asynchronous processing."""
        self._repositories.resolve_branch(trigger.repository_id, trigger.branch)
        await self._event_bus.publish(Event(type=EVENT_DEPLOYMENT_TRIGGERED, payload=trigger))

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

        logger.info("starting deployment for repo=%s branch=%s commit=%s", trigger.repository_id, trigger.branch, trigger.commit_sha)
        try:
            await self._workflow.execute(plan)
        except Exception:  # noqa: BLE001
            logger.exception("deployment failed for repo=%s branch=%s", trigger.repository_id, trigger.branch)
            return

        logger.info("deployment completed for repo=%s branch=%s", trigger.repository_id, trigger.branch)
