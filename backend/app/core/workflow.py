from __future__ import annotations
"""Workflow execution primitives for sequential deployment plans."""

import logging

from app.core.event_bus import AsyncEventBus, Event
from app.core.plugins import PluginRegistry
from app.core.workspace_cleaner import CleanupConfig, WorkspaceCleaner
from app.models import StepContext, WorkflowPlan


EVENT_DEPLOYMENT_TRIGGERED = "deployment.triggered"
EVENT_DEPLOYMENT_STARTED = "deployment.started"
EVENT_DEPLOYMENT_COMPLETED = "deployment.completed"
EVENT_DEPLOYMENT_FAILED = "deployment.failed"
EVENT_STEP_STARTED = "deployment.step.started"
EVENT_STEP_COMPLETED = "deployment.step.completed"
EVENT_CLEANUP_STARTED = "deployment.cleanup.started"
EVENT_CLEANUP_COMPLETED = "deployment.cleanup.completed"


class WorkflowEngine:
    """Execute a normalized deployment plan one step at a time.

    The engine is intentionally conservative in the prototype stage: each step
    is validated immediately before execution and any failure aborts the whole
    deployment. The surrounding event bus emits lifecycle notifications so the
    design can evolve into richer orchestration later.

    When a deployment fails, the engine can optionally clean up workspace
    artifacts to prevent stale state from affecting subsequent builds.
    Cleanup is controlled by the ``cleanup_on_failure`` flag in the workflow
    plan metadata.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        event_bus: AsyncEventBus,
        cleanup_config: CleanupConfig | None = None,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus
        self._cleaner = WorkspaceCleaner(cleanup_config) if cleanup_config else None

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

                # Attempt workspace cleanup on failure
                await self._cleanup_on_failure(context, plan)

                raise

            await self._event_bus.publish(
                Event(
                    type=EVENT_STEP_COMPLETED,
                    payload={"repository_id": plan.repository_id, "branch": plan.branch, "step": step.name},
                )
            )

        await self._event_bus.publish(Event(type=EVENT_DEPLOYMENT_COMPLETED, payload=plan))

    async def _cleanup_on_failure(self, context: StepContext, plan: WorkflowPlan) -> None:
        """Run workspace cleanup after a deployment failure.

        This is a best-effort operation — cleanup failures are logged but
        never mask the original deployment error.
        """
        if not self._cleaner:
            return

        try:
            await self._event_bus.publish(
                Event(
                    type=EVENT_CLEANUP_STARTED,
                    payload={"repository_id": plan.repository_id, "branch": plan.branch},
                )
            )

            result = await self._cleaner.clean_after_failure(
                work_dir=plan.work_dir,
                project_type="",  # Project type unknown at workflow level
                logger=context.logger,
            )

            await self._event_bus.publish(
                Event(
                    type=EVENT_CLEANUP_COMPLETED,
                    payload={
                        "repository_id": plan.repository_id,
                        "branch": plan.branch,
                        "cleanup_result": result,
                    },
                )
            )

            if result.get("cleaned"):
                context.logger.info(
                    "[workflow] post-failure cleanup completed: removed=%s, docker=%s",
                    result.get("artifacts_removed", []),
                    result.get("docker_cleaned", False),
                )
        except Exception:  # noqa: BLE001
            # Cleanup failures must never mask the original deployment error
            context.logger.warning("[workflow] post-failure cleanup encountered an error (ignored)")
