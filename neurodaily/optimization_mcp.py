"""Read-only local MCP tools for search and optimisation evidence."""
from __future__ import annotations

from . import history
from .optimization import Optimizer, historical_attribution


def make_server(config_path=None, *, store=None):
    from mcp.server.fastmcp import FastMCP

    optimizer = Optimizer(config_path, store)
    server = FastMCP("NeuroDaily search evidence")

    @server.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def search_history(limit: int = 20) -> list[dict]:
        """List recent searches and their outcomes for this server's profile."""
        _, config = optimizer.current()
        runs = history.list_runs(limit=max(1, min(limit, 100)), profile=config.profile)
        keys = ("id", "started_at", "finished_at", "status", "source_counts", "item_count", "has_snapshot")
        return [{key: run.get(key) for key in keys} for run in runs]

    @server.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def search_source_health() -> list[dict]:
        """Read source diagnoses from the latest optimisation or formal search."""
        scope, config = optimizer.current()
        run = optimizer.store.get(scope) or {}
        return run.get("evidence") or historical_attribution(config.profile)[1]

    @server.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def search_rule_attribution() -> list[dict]:
        """List rules and example records matched by the most recent search or trial."""
        scope, config = optimizer.current()
        run = optimizer.store.get(scope) or {}
        return run.get("attributions") or historical_attribution(config.profile)[0]

    @server.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def search_optimization_review(run_id: str | None = None) -> dict:
        """Read verified candidate differences, metrics and evidence from this profile."""
        scope, _ = optimizer.current()
        try:
            run = optimizer.store.get(scope, run_id)
        except LookupError as exc:
            raise ValueError("Optimisation run not found in this profile") from exc
        return optimizer.public_run(run) or {}

    return server
