from __future__ import annotations
"""Repository lookup and branch-to-deployment-rule resolution services."""

from pathlib import Path

from app.config import AppConfig, BranchConfig, RepositoryConfig


class RepositoryCatalog:
    """Expose repository configuration through query-oriented helper methods."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._repositories = {repository.id: repository for repository in config.repositories}

    def get(self, repository_id: str) -> RepositoryConfig:
        """Return the configured repository or raise a descriptive lookup error."""
        try:
            return self._repositories[repository_id]
        except KeyError as exc:
            raise KeyError(f"repository {repository_id!r} not found") from exc

    def resolve_branch(self, repository_id: str, branch: str) -> tuple[RepositoryConfig, BranchConfig, Path]:
        """Resolve the effective branch rule and local worktree path.

        Matching uses the expected priority order for deployment rules:
        exact branch match, then the longest matching prefix wildcard, and
        finally the global catch-all rule.
        """
        repository = self.get(repository_id)
        match = _match_branch(branch, repository.branches)
        if match is None:
            raise ValueError(f"repository {repository_id!r} has no deployment rule for branch {branch!r}")

        worktree = (
            Path(match.worktree)
            if match.worktree
            else Path(self._config.workspace_root) / repository_id / _sanitize_branch(branch)
        )
        return repository, match, worktree


def _match_branch(branch: str, candidates: list[BranchConfig]) -> BranchConfig | None:
    """Select the best branch rule according to deterministic precedence rules."""
    exact: BranchConfig | None = None
    prefix: BranchConfig | None = None
    global_match: BranchConfig | None = None
    longest_prefix = -1

    for candidate in candidates:
        if candidate.pattern == branch:
            exact = candidate
        elif candidate.pattern == "*":
            global_match = global_match or candidate
        elif candidate.pattern.endswith("/*"):
            base = candidate.pattern[:-2]
            if branch.startswith(base + "/") and len(base) > longest_prefix:
                longest_prefix = len(base)
                prefix = candidate

    return exact or prefix or global_match


def _sanitize_branch(branch: str) -> str:
    """Convert a branch name into a filesystem-safe directory fragment."""
    unsafe_characters = {"/": "_", "\\": "_", ":": "_", "*": "_", "?": "_", "\"": "_", "<": "_", ">": "_", "|": "_"}
    sanitized = branch
    for source, target in unsafe_characters.items():
        sanitized = sanitized.replace(source, target)
    return sanitized
