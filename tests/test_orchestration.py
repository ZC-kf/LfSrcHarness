from pathlib import Path

import pytest

from lfsrc_harness.orchestration import (
    Budget,
    BudgetExceeded,
    BudgetTracker,
    ConcurrencyLimiter,
    Orchestrator,
    RecoveryPlanner,
    TaskPriority,
    TaskRepository,
    TaskSpec,
    TaskStatus,
)
from lfsrc_harness.plugins import (
    PluginManifest,
    PluginRegistry,
    PluginResult,
    PluginTransport,
    PythonPlugin,
)
from lfsrc_harness.policy import EmergencyStopRegistry, PolicyEngine
from lfsrc_harness.scheduler import create_celery_app
from lfsrc_harness.scope import ScopeConfig


def task(*, plugin: str = "primary", priority: TaskPriority = TaskPriority.P1) -> TaskSpec:
    return TaskSpec(
        target="local-node",
        objective="process fixture",
        plugin=plugin,
        priority=priority,
        budget=Budget(
            token_limit=100, time_seconds=30, cpu_seconds=10, memory_mb=128, network_bytes=1024
        ),
        max_attempts=2,
    )


def policy(stops: EmergencyStopRegistry | None = None) -> PolicyEngine:
    scope = ScopeConfig.model_validate(
        {
            "name": "local",
            "targets": ["local-node"],
            "time_windows": [],
            "rate_limit": {"requests": 20, "per_seconds": 60},
            "prohibited_actions": [],
            "privileges": {},
        }
    )
    return PolicyEngine(scope, stops=stops)


def plugin(name: str, handler) -> PythonPlugin:
    return PythonPlugin(
        PluginManifest(
            name=name,
            version="1",
            capabilities={"fixture"},
            target_types={"local"},
            transport=PluginTransport.PYTHON,
        ),
        handler,
    )


def test_repository_persists_checkpoint_and_resumes(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    repository = TaskRepository(path)
    record = repository.create(task())
    repository.update(record.id, status=TaskStatus.RUNNING, checkpoint={"step": 3})
    repository.close()

    reopened = TaskRepository(path)
    restored = reopened.get(record.id)

    assert restored.status is TaskStatus.RUNNING
    assert restored.checkpoint == {"step": 3}


def test_repository_claims_p0_before_p1(tmp_path: Path) -> None:
    repository = TaskRepository(tmp_path / "state.sqlite3")
    repository.create(task(priority=TaskPriority.P1))
    urgent = repository.create(task(priority=TaskPriority.P0))

    claimed = repository.claim_next()

    assert claimed is not None
    assert claimed.id == urgent.id
    assert claimed.status is TaskStatus.RUNNING


def test_budget_tracker_enforces_token_network_and_time_limits(monkeypatch) -> None:
    current = [100.0]
    tracker = BudgetTracker(
        Budget(token_limit=5, time_seconds=10, cpu_seconds=1, memory_mb=64, network_bytes=20),
        clock=lambda: current[0],
    )
    tracker.consume(tokens=5, network_bytes=20)
    tracker.check()

    tracker.consume(tokens=1)
    with pytest.raises(BudgetExceeded, match="token"):
        tracker.check()

    tracker = BudgetTracker(Budget(time_seconds=1), clock=lambda: current[0])
    current[0] += 2
    with pytest.raises(BudgetExceeded, match="time"):
        tracker.check()


def test_concurrency_limiter_applies_target_tool_and_node_limits() -> None:
    limiter = ConcurrencyLimiter(per_target=1, per_tool=1, per_node=1)

    with limiter.acquire(target="local-node", tool="fixture", node="node-1"):
        assert not limiter.can_acquire(target="local-node", tool="other", node="node-2")
        assert not limiter.can_acquire(target="other", tool="fixture", node="node-2")
        assert not limiter.can_acquire(target="other", tool="other", node="node-1")

    assert limiter.can_acquire(target="local-node", tool="fixture", node="node-1")


def test_orchestrator_recovers_with_alternative_plugin(tmp_path: Path) -> None:
    registry = PluginRegistry()
    registry.register(plugin("primary", lambda _: PluginResult(success=False, output="failed")))
    registry.register(plugin("fallback", lambda _: PluginResult(success=True, output="ok")))
    repository = TaskRepository(tmp_path / "state.sqlite3")
    orchestrator = Orchestrator(
        repository,
        registry,
        policy(),
        event_root=tmp_path / "runs",
        recovery=RecoveryPlanner({"primary": ["fallback"]}),
    )
    created = orchestrator.submit(task())

    finished = orchestrator.run_until_terminal(created.id)

    assert finished.status is TaskStatus.SUCCEEDED
    assert finished.attempts == 2
    assert finished.active_plugin == "fallback"


def test_orchestrator_honors_run_emergency_stop(tmp_path: Path) -> None:
    calls: list[str] = []
    registry = PluginRegistry()
    registry.register(
        plugin("primary", lambda _: calls.append("called") or PluginResult(success=True))
    )
    repository = TaskRepository(tmp_path / "state.sqlite3")
    stops = EmergencyStopRegistry()
    engine = policy(stops)
    orchestrator = Orchestrator(repository, registry, engine, event_root=tmp_path / "runs")
    created = orchestrator.submit(task())
    stops.stop_run(created.id)

    finished = orchestrator.run_until_terminal(created.id)

    assert finished.status is TaskStatus.STOPPED
    assert calls == []


def test_celery_queue_configuration_is_externalized() -> None:
    app = create_celery_app(
        broker_url="redis://queue.invalid/0",
        result_backend="redis://queue.invalid/1",
    )

    assert app.conf.broker_url == "redis://queue.invalid/0"
    assert app.conf.result_backend == "redis://queue.invalid/1"
    assert app.conf.task_serializer == "json"
    assert app.conf.worker_prefetch_multiplier == 1
