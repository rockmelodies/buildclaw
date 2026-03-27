from __future__ import annotations
"""Workflow execution primitives for sequential deployment plans."""

from app.core.event_bus import AsyncEventBus, Event
from app.core.plugins import PluginRegistry
from app.models import StepContext, WorkflowPlan


EVENT_DEPLOYMENT_TRIGGERED = "deployment.triggered"
EVENT_DEPLOYMENT_STARTED = "deployment.started"
EVENT_DEPLOYMENT_COMPLETED = "deployment.completed"
EVENT_DEPLOYMENT_FAILED = "deployment.failed"
EVENT_STEP_STARTED = "deployment.step.started"
EVENT_STEP_COMPLETED = "deployment.step.completed"


class WorkflowEngine:
    """Execute a normalized deployment plan one step at a time.

    The engine is intentionally conservative in the prototype stage: each step
    is validated immediately before execution and any failure aborts the whole
    deployment. The surrounding event bus emits lifecycle notifications so the
    design can evolve into richer orchestration later.
    """

    def __init__(self, registry: PluginRegistry, event_bus: AsyncEventBus) -> None:
        self._registry = registry
        self._event_bus = event_bus

    async def execute(self, plan: WorkflowPlan) -> None:
        """Run all steps in order and publish deployment lifecycle events."""
        await self._event_bus.publish(Event(type=EVENT_DEPLOYMENT_STARTED, payload=plan))

        context = StepContext(
            repository_id=plan.repository_id,
            branch=plan.branch,
            commit_sha=plan.commit_sha,
            work_dir=plan.work_dir,
            logger=plan.logger,
        )

        for step in plan.steps:
            await self._event_bus.publish(
                Event(
                    type=EVENT_STEP_STARTED,
                    payload={"repository_id": plan.repository_id, "branch": plan.branch, "step": step.name},
                )
            )

            plugin = self._registry.get(step.plugin)
            await plugin.validate(step.config)
            try:
                await plugin.execute(context, step.config)
            except Exception:
                # A failed step terminates the deployment so later steps do not
                # run against a partially updated worktree or environment.
                await self._event_bus.publish(
                    Event(
                        type=EVENT_DEPLOYMENT_FAILED,
                        payload={"repository_id": plan.repository_id, "branch": plan.branch, "step": step.name},
                    )
                )
                raise

            await self._event_bus.publish(
                Event(
                    type=EVENT_STEP_COMPLETED,
                    payload={"repository_id": plan.repository_id, "branch": plan.branch, "step": step.name},
                )
            )

        await self._event_bus.publish(Event(type=EVENT_DEPLOYMENT_COMPLETED, payload=plan))
