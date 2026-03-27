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
from app.core.event_bus import AsyncEventBus
from app.core.plugins import PluginRegistry
from app.core.workflow import WorkflowEngine
from app.models import DeploymentTrigger
from app.plugins.command_deploy import CommandDeployPlugin
from app.plugins.git_pull import GitPullPlugin
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
    registry.register(GitPullPlugin())
    registry.register(CommandDeployPlugin())
    repositories = RepositoryCatalog(config)
    workflow = WorkflowEngine(registry, event_bus)
    deployments = DeploymentService(repositories, event_bus, workflow)
    await deployments.start()

    app.state.config = config
    app.state.repositories = repositories
    app.state.deployments = deployments

    try:
        yield
    finally:
        await deployments.stop()


app = FastAPI(title="BuildClaw Backend", version="0.1.0", lifespan=lifespan)


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
