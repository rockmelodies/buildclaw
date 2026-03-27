from __future__ import annotations
"""Plugin protocol and registry for deployment executors."""

from typing import Any, Protocol

from app.models import StepContext


class DeployPlugin(Protocol):
    """Contract implemented by every deployment step plugin."""
    name: str

    async def validate(self, config: dict[str, Any]) -> None: ...

    async def execute(self, context: StepContext, config: dict[str, Any]) -> None: ...

    async def rollback(self, context: StepContext, config: dict[str, Any]) -> None: ...


class PluginRegistry:
    """Runtime registry that resolves plugins by their stable names."""

    def __init__(self) -> None:
        self._plugins: dict[str, DeployPlugin] = {}

    def register(self, plugin: DeployPlugin) -> None:
        """Register a plugin instance and protect against duplicate names."""
        if plugin.name in self._plugins:
            raise ValueError(f"plugin {plugin.name!r} already registered")
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> DeployPlugin:
        """Resolve a previously registered plugin by name."""
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise ValueError(f"plugin {name!r} not found") from exc

    def list(self) -> list[str]:
        """Return registered plugin names in deterministic order."""
        return sorted(self._plugins)
