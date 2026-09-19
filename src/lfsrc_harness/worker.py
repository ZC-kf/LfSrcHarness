"""Celery worker entry point."""

from __future__ import annotations

import os
from pathlib import Path

from .orchestration import Orchestrator, TaskRepository
from .plugins import PluginRegistry
from .policy import PolicyEngine
from .scheduler import create_celery_app, register_orchestrator_task
from .scope import load_scope

ROOT = Path(os.environ.get("LFSRC_ROOT", Path(__file__).parents[2])).resolve()


def build_orchestrator() -> Orchestrator:
    runs = Path(os.environ.get("LFSRC_RUNS_ROOT", ROOT / "runs"))
    scope_path = Path(os.environ.get("LFSRC_SCOPE_PATH", ROOT / "deploy" / "config" / "scope.yaml"))
    registry = PluginRegistry()
    registry.load_entry_points()
    scope = load_scope(scope_path)
    return Orchestrator(
        TaskRepository(Path(os.environ.get("LFSRC_DATABASE", runs / "state.sqlite3"))),
        registry,
        PolicyEngine(scope),
        event_root=runs,
    )


app = create_celery_app()
register_orchestrator_task(app, build_orchestrator)
