"""Celery/Redis queue configuration and orchestration task registration."""

from __future__ import annotations

import os
from collections.abc import Callable

from celery import Celery

from .orchestration import Orchestrator


def create_celery_app(
    *,
    broker_url: str | None = None,
    result_backend: str | None = None,
) -> Celery:
    broker = broker_url or os.environ.get("LFSRC_REDIS_URL", "redis://127.0.0.1:6379/0")
    backend = result_backend or os.environ.get("LFSRC_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
    app = Celery("lfsrc_harness", broker=broker, backend=backend)
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_transport_options={"visibility_timeout": 43200, "priority_steps": list(range(10))},
        task_default_priority=5,
        task_inherit_parent_priority=True,
    )
    return app


def register_orchestrator_task(
    app: Celery,
    orchestrator_factory: Callable[[], Orchestrator],
) -> None:
    @app.task(  # type: ignore[untyped-decorator]
        name="lfsrc.run_task",
        bind=True,
        autoretry_for=(OSError,),
        retry_backoff=True,
        max_retries=3,
    )
    def run_task(_task: object, task_id: str) -> dict[str, object]:
        record = orchestrator_factory().run_until_terminal(task_id)
        return record.model_dump(mode="json")
