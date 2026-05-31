from __future__ import annotations
"""FastAPI application entrypoint for the BuildClaw deployment service.

This module wires together configuration loading, dependency construction,
application lifecycle management, and the public HTTP endpoints exposed by the
deployment backend.
"""

import hmac
import json
import logging
from contextlib import asynccontextmanager
from hashlib import sha256
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import load_config
from app.core.build_insights import BuildInsightsEngine
from app.core.build_memory import BuildMemoryManager
from app.core.event_bus import AsyncEventBus
from app.core.plugins import PluginRegistry
from app.core.workflow import WorkflowEngine
from app.models import DeploymentTrigger
from app.plugins.command_deploy import CommandDeployPlugin
from app.plugins.env_learn import EnvLearnPlugin
from app.plugins.git_pull import GitPullPlugin
from app.plugins.smart_build import SmartBuildPlugin
from app.runtime_checks import collect_runtime_checks, prepare_runtime_directories
from app.services.deployments import DeploymentService
from app.services.repositories import RepositoryCatalog


def _configure_logging() -> None:
    """Configure a single process-wide logging format for API and worker logs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create and tear down long-lived services bound to the FastAPI app.

    FastAPI's lifespan hook is used here instead of global module state so the
    application can be tested cleanly and restarted without leaking worker
    tasks.
    """
    _configure_logging()

    config = load_config()
    prepare_runtime_directories(config)
    event_bus = AsyncEventBus()
    registry = PluginRegistry()

    # Initialize the build memory manager (intelligent build system)
    memory_manager: BuildMemoryManager | None = None
    insights_engine: BuildInsightsEngine | None = None

    if config.knowledge.enabled:
        memory_manager = BuildMemoryManager(
            knowledge_root=config.knowledge.knowledge_root,
        )
        memory_manager.initialize()

        insights_engine = BuildInsightsEngine(
            knowledge_base=memory_manager.knowledge_base,
        )

    # Register plugins — core plugins first, then intelligent plugins
    registry.register(GitPullPlugin())
    registry.register(CommandDeployPlugin())

    # Register smart_build and env_learn if knowledge system is enabled
    if memory_manager:
        registry.register(SmartBuildPlugin(memory_manager=memory_manager))
        registry.register(EnvLearnPlugin(memory_manager=memory_manager))

    repositories = RepositoryCatalog(config)
    workflow = WorkflowEngine(registry, event_bus)
    deployments = DeploymentService(repositories, event_bus, workflow, memory_manager)
    await deployments.start()

    app.state.config = config
    app.state.repositories = repositories
    app.state.deployments = deployments
    app.state.memory_manager = memory_manager
    app.state.insights_engine = insights_engine

    try:
        yield
    finally:
        await deployments.stop()


app = FastAPI(title="BuildClaw Backend", version="0.2.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Return a minimal health payload for container and load-balancer probes."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    """Return readiness diagnostics for deployment-capable runtime conditions."""

    checks = collect_runtime_checks(request.app.state.config)
    status_code = 200 if checks["ok"] else 503
    return JSONResponse(status_code=status_code, content=checks)


@app.post("/webhooks/github/{repo_id}")
async def github_webhook(repo_id: str, request: Request) -> JSONResponse:
    """Receive GitHub webhook requests and trigger asynchronous deployments.

    The endpoint intentionally responds quickly after validation. The actual
    deployment work is delegated to the internal event bus and background
    deployment consumer.
    """
    repositories: RepositoryCatalog = request.app.state.repositories
    deployments: DeploymentService = request.app.state.deployments

    try:
        repository = repositories.get(repo_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_github_signature(payload, repository.webhook_secret, signature):
        logging.getLogger("buildclaw.webhook").warning("signature mismatch for repository %s", repo_id)
        raise HTTPException(status_code=401, detail="invalid signature")

    event_name = request.headers.get("X-GitHub-Event", "")
    if event_name == "ping":
        return JSONResponse(status_code=200, content={"status": "pong"})
    if event_name != "push":
        return JSONResponse(status_code=202, content={"status": "ignored", "reason": "unsupported event"})

    event = _parse_push_event(payload)
    branch = event["branch"]
    commit_sha = event["commit_sha"]

    await deployments.trigger_deployment(
        DeploymentTrigger(
            repository_id=repo_id,
            branch=branch,
            commit_sha=commit_sha,
            delivery_id=request.headers.get("X-GitHub-Delivery", ""),
        )
    )

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "repo_id": repo_id, "branch": branch, "commit": commit_sha},
    )


# ---------------------------------------------------------------------------
# Intelligent Build API Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/v1/knowledge/recipes")
async def list_recipes(request: Request) -> JSONResponse:
    """List all available build recipes in the knowledge base."""
    memory_manager: BuildMemoryManager | None = getattr(request.app.state, "memory_manager", None)
    if not memory_manager:
        return JSONResponse(status_code=503, content={"error": "knowledge system is not enabled"})

    recipes = []
    for project_type in memory_manager.knowledge_base.list_recipes():
        recipe = memory_manager.knowledge_base.get_recipe(project_type)
        if recipe:
            recipes.append({
                "project_type": recipe.project_type,
                "language": recipe.language,
                "build_tool": recipe.build_tool,
                "framework": recipe.framework,
                "confidence": recipe.confidence,
                "success_count": recipe.success_count,
                "failure_count": recipe.failure_count,
                "known_issues_count": len(recipe.known_issues),
            })

    return JSONResponse(content={"recipes": recipes, "total": len(recipes)})


@app.get("/api/v1/knowledge/recipes/{project_type}")
async def get_recipe(project_type: str, request: Request) -> JSONResponse:
    """Get detailed information about a specific build recipe."""
    memory_manager: BuildMemoryManager | None = getattr(request.app.state, "memory_manager", None)
    if not memory_manager:
        return JSONResponse(status_code=503, content={"error": "knowledge system is not enabled"})

    recipe = memory_manager.knowledge_base.get_recipe(project_type)
    if not recipe:
        raise HTTPException(status_code=404, detail=f"recipe not found: {project_type}")

    return JSONResponse(content=recipe.to_dict())


@app.get("/api/v1/knowledge/repos")
async def list_repo_learnings(request: Request) -> JSONResponse:
    """List all repository learning records."""
    memory_manager: BuildMemoryManager | None = getattr(request.app.state, "memory_manager", None)
    if not memory_manager:
        return JSONResponse(status_code=503, content={"error": "knowledge system is not enabled"})

    learnings = []
    for repo_id, learning in memory_manager.knowledge_base._repo_learnings.items():
        learnings.append({
            "repository_id": learning.repository_id,
            "project_type": learning.project_type,
            "language": learning.language,
            "framework": learning.framework,
            "total_builds": learning.total_builds,
            "success_rate": learning.success_rate,
            "last_build_status": learning.last_build_status,
        })

    return JSONResponse(content={"repos": learnings, "total": len(learnings)})


@app.get("/api/v1/knowledge/repos/{repo_id}")
async def get_repo_learning(repo_id: str, request: Request) -> JSONResponse:
    """Get detailed learning information for a specific repository."""
    memory_manager: BuildMemoryManager | None = getattr(request.app.state, "memory_manager", None)
    if not memory_manager:
        return JSONResponse(status_code=503, content={"error": "knowledge system is not enabled"})

    learning = memory_manager.knowledge_base.get_repo_learning(repo_id)
    if not learning:
        raise HTTPException(status_code=404, detail=f"repo learning not found: {repo_id}")

    return JSONResponse(content=learning.to_dict())


@app.post("/api/v1/detect/{repo_id}")
async def detect_environment(repo_id: str, request: Request) -> JSONResponse:
    """Detect the project environment for a repository's workspace.

    This endpoint runs environment detection on the repository's local
    workspace and returns the detected project type, language, build tool,
    and framework.
    """
    repositories: RepositoryCatalog = request.app.state.repositories
    memory_manager: BuildMemoryManager | None = getattr(request.app.state, "memory_manager", None)

    if not memory_manager:
        return JSONResponse(status_code=503, content={"error": "knowledge system is not enabled"})

    try:
        repository = repositories.get(repo_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    from pathlib import Path
    config = request.app.state.config
    work_dir = Path(config.workspace_root) / repo_id

    if not work_dir.exists():
        raise HTTPException(status_code=404, detail=f"workspace not found for repo: {repo_id}")

    detected = memory_manager.detector.detect(work_dir)

    return JSONResponse(content={
        "repository_id": repo_id,
        "project_type": detected.project_type.value,
        "language": detected.language,
        "build_tool": detected.build_tool,
        "framework": detected.framework,
        "runtime_version_hint": detected.runtime_version_hint,
        "confidence": detected.confidence,
        "marker_files": detected.marker_files,
        "all_detected": detected.metadata.get("all_detected", []),
    })


@app.post("/api/v1/plan/{repo_id}")
async def generate_build_plan(repo_id: str, request: Request) -> JSONResponse:
    """Generate an intelligent build plan for a repository.

    This endpoint uses the build memory manager to detect the project
    environment, recall knowledge, and produce a complete build plan
    with specific commands for each phase.
    """
    repositories: RepositoryCatalog = request.app.state.repositories
    memory_manager: BuildMemoryManager | None = getattr(request.app.state, "memory_manager", None)

    if not memory_manager:
        return JSONResponse(status_code=503, content={"error": "knowledge system is not enabled"})

    try:
        repository = repositories.get(repo_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    from pathlib import Path
    config = request.app.state.config
    work_dir = Path(config.workspace_root) / repo_id

    if not work_dir.exists():
        raise HTTPException(status_code=404, detail=f"workspace not found for repo: {repo_id}")

    plan = memory_manager.pre_deploy(repo_id, work_dir)

    return JSONResponse(content={
        "repository_id": plan.repository_id,
        "project_type": plan.project_type,
        "language": plan.language,
        "build_tool": plan.build_tool,
        "framework": plan.framework,
        "plan_source": plan.plan_source,
        "confidence": plan.confidence,
        "required_tools": plan.required_tools,
        "environment_variables": plan.environment_variables,
        "install_steps": plan.install_steps,
        "test_steps": plan.test_steps,
        "build_steps": plan.build_steps,
        "deploy_steps": plan.deploy_steps,
        "workarounds": plan.workarounds,
        "workflow_steps": plan.to_workflow_steps(),
    })


@app.get("/api/v1/insights")
async def get_build_insights(request: Request) -> JSONResponse:
    """Get build insights and analytics from the knowledge base."""
    insights_engine: BuildInsightsEngine | None = getattr(request.app.state, "insights_engine", None)

    if not insights_engine:
        return JSONResponse(status_code=503, content={"error": "knowledge system is not enabled"})

    report = insights_engine.generate()

    return JSONResponse(content={
        "generated_at": report.generated_at,
        "total_recipes": report.total_recipes,
        "total_repo_learnings": report.total_repo_learnings,
        "total_builds_tracked": report.total_builds_tracked,
        "overall_success_rate": report.overall_success_rate,
        "recipe_insights": [
            {
                "project_type": r.project_type,
                "language": r.language,
                "build_tool": r.build_tool,
                "success_rate": r.success_rate,
                "confidence": r.confidence,
                "known_issues_count": r.known_issues_count,
            }
            for r in report.recipe_insights
        ],
        "repo_insights": [
            {
                "repository_id": r.repository_id,
                "project_type": r.project_type,
                "health_score": r.health_score,
                "success_rate": r.success_rate,
                "total_builds": r.total_builds,
            }
            for r in report.repo_insights
        ],
        "top_failure_patterns": report.top_failure_patterns[:10],
        "coverage_gaps": report.coverage_gaps,
        "recommendations": report.recommendations,
    })


@app.get("/api/v1/insights/text")
async def get_build_insights_text(request: Request) -> JSONResponse:
    """Get a human-readable text version of build insights."""
    insights_engine: BuildInsightsEngine | None = getattr(request.app.state, "insights_engine", None)

    if not insights_engine:
        return JSONResponse(status_code=503, content={"error": "knowledge system is not enabled"})

    report = insights_engine.generate()
    text = insights_engine.format_report(report)

    return JSONResponse(content={"report": text})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _verify_github_signature(payload: bytes, secret: str, signature: str) -> bool:
    """Verify GitHub's `X-Hub-Signature-256` header using HMAC-SHA256."""
    if not secret or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()
    actual = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, actual)


def _parse_push_event(payload: bytes) -> dict[str, Any]:
    """Extract the branch name and target commit SHA from a push payload."""
    raw = json.loads(payload)
    ref = str(raw.get("ref", ""))
    branch = ref.removeprefix("refs/heads/")
    if not branch:
        raise HTTPException(status_code=400, detail="missing branch ref")
    return {"branch": branch, "commit_sha": str(raw.get("after", ""))}
