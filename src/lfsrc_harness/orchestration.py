"""Persistent task orchestration, budgets, limits, recovery, and resume."""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .events import EventLedger, EventType
from .plugins import PluginRegistry, PluginRequest
from .policy import ActionRequest, ActionTier, Decision, PolicyEngine


class TaskPriority(IntEnum):
    P0 = 0
    P1 = 1
    P2 = 2


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    STOPPED = "stopped"

    @property
    def terminal(self) -> bool:
        return self in {self.SUCCEEDED, self.FAILED, self.STOPPED}


class Budget(BaseModel):
    token_limit: int | None = Field(default=None, gt=0)
    time_seconds: float | None = Field(default=None, gt=0)
    cpu_seconds: float | None = Field(default=None, gt=0)
    memory_mb: int | None = Field(default=None, gt=0)
    network_bytes: int | None = Field(default=None, gt=0)


class TaskSpec(BaseModel):
    tenant_id: str = "default"
    target: str
    objective: str
    plugin: str
    priority: TaskPriority = TaskPriority.P1
    node: str = "local"
    options: dict[str, Any] = Field(default_factory=dict)
    budget: Budget = Field(default_factory=Budget)
    max_attempts: int = Field(default=3, ge=1, le=20)


class TaskRecord(BaseModel):
    id: str
    spec: TaskSpec
    status: TaskStatus
    attempts: int = 0
    active_plugin: str
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                spec_json TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                attempts INTEGER NOT NULL,
                active_plugin TEXT NOT NULL,
                checkpoint_json TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def create(self, spec: TaskSpec) -> TaskRecord:
        now = datetime.now(UTC)
        record = TaskRecord(
            id=f"task-{uuid4().hex}",
            spec=spec,
            status=TaskStatus.QUEUED,
            active_plugin=spec.plugin,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._connection.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    spec.model_dump_json(),
                    record.status.value,
                    int(spec.priority),
                    0,
                    spec.plugin,
                    "{}",
                    None,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            self._connection.commit()
        return record

    def get(self, task_id: str) -> TaskRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if row is None:
            raise KeyError(task_id)
        return self._from_row(row)

    def list(self, *, status: TaskStatus | None = None) -> list[TaskRecord]:
        query = "SELECT * FROM tasks"
        values: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            values = (status.value,)
        query += " ORDER BY priority ASC, created_at ASC"
        with self._lock:
            rows = self._connection.execute(query, values).fetchall()
        return [self._from_row(row) for row in rows]

    def update(
        self,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        attempts: int | None = None,
        active_plugin: str | None = None,
        checkpoint: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TaskRecord:
        current = self.get(task_id)
        next_status = status or current.status
        next_attempts = current.attempts if attempts is None else attempts
        next_plugin = active_plugin or current.active_plugin
        next_checkpoint = current.checkpoint if checkpoint is None else checkpoint
        next_error = current.error if error is None else error
        updated = datetime.now(UTC)
        with self._lock:
            self._connection.execute(
                """
                UPDATE tasks
                SET status = ?, attempts = ?, active_plugin = ?, checkpoint_json = ?,
                    error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    next_status.value,
                    next_attempts,
                    next_plugin,
                    json.dumps(next_checkpoint, separators=(",", ":")),
                    next_error,
                    updated.isoformat(),
                    task_id,
                ),
            )
            self._connection.commit()
        return self.get(task_id)

    def claim_next(self) -> TaskRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT id FROM tasks WHERE status = ? "
                "ORDER BY priority ASC, created_at ASC LIMIT 1",
                (TaskStatus.QUEUED.value,),
            ).fetchone()
            if row is None:
                return None
            task_id = str(row["id"])
            self._connection.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (TaskStatus.RUNNING.value, datetime.now(UTC).isoformat(), task_id),
            )
            self._connection.commit()
        return self.get(task_id)

    def close(self) -> None:
        self._connection.close()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> TaskRecord:
        spec = TaskSpec.model_validate_json(row["spec_json"])
        return TaskRecord(
            id=row["id"],
            spec=spec,
            status=TaskStatus(row["status"]),
            attempts=row["attempts"],
            active_plugin=row["active_plugin"],
            checkpoint=json.loads(row["checkpoint_json"]),
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class BudgetExceeded(RuntimeError):
    pass


class BudgetTracker:
    def __init__(self, budget: Budget, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.budget = budget
        self.clock = clock
        self.started = clock()
        self.tokens = 0
        self.cpu_seconds = 0.0
        self.memory_mb = 0
        self.network_bytes = 0

    def consume(
        self,
        *,
        tokens: int = 0,
        cpu_seconds: float = 0,
        memory_mb: int = 0,
        network_bytes: int = 0,
    ) -> None:
        self.tokens += tokens
        self.cpu_seconds += cpu_seconds
        self.memory_mb = max(self.memory_mb, memory_mb)
        self.network_bytes += network_bytes

    def check(self) -> None:
        elapsed = self.clock() - self.started
        checks = (
            (self.budget.token_limit, self.tokens, "token budget exceeded"),
            (self.budget.time_seconds, elapsed, "time budget exceeded"),
            (self.budget.cpu_seconds, self.cpu_seconds, "CPU budget exceeded"),
            (self.budget.memory_mb, self.memory_mb, "memory budget exceeded"),
            (self.budget.network_bytes, self.network_bytes, "network budget exceeded"),
        )
        for limit, value, message in checks:
            if limit is not None and value > limit:
                raise BudgetExceeded(message)


class ConcurrencyLimitExceeded(RuntimeError):
    pass


class ConcurrencyLimiter:
    def __init__(self, *, per_target: int = 1, per_tool: int = 2, per_node: int = 4) -> None:
        self.limits = {"target": per_target, "tool": per_tool, "node": per_node}
        if any(value <= 0 for value in self.limits.values()):
            raise ValueError("concurrency limits must be positive")
        self._counts: dict[tuple[str, str], int] = {}
        self._lock = RLock()

    def can_acquire(self, *, target: str, tool: str, node: str) -> bool:
        keys = (("target", target), ("tool", tool), ("node", node))
        with self._lock:
            return all(self._counts.get(key, 0) < self.limits[key[0]] for key in keys)

    @contextmanager
    def acquire(self, *, target: str, tool: str, node: str) -> Iterator[None]:
        keys = (("target", target), ("tool", tool), ("node", node))
        with self._lock:
            if not all(self._counts.get(key, 0) < self.limits[key[0]] for key in keys):
                raise ConcurrencyLimitExceeded("concurrency limit reached")
            for key in keys:
                self._counts[key] = self._counts.get(key, 0) + 1
        try:
            yield
        finally:
            with self._lock:
                for key in keys:
                    self._counts[key] -= 1


class RecoveryPlanner:
    def __init__(self, alternatives: dict[str, list[str]] | None = None) -> None:
        self.alternatives = alternatives or {}

    def next_plugin(self, current: str, tried: set[str]) -> str | None:
        for candidate in self.alternatives.get(current, []):
            if candidate not in tried:
                return candidate
        return None


class Orchestrator:
    def __init__(
        self,
        repository: TaskRepository,
        plugins: PluginRegistry,
        policy: PolicyEngine,
        *,
        event_root: str | Path,
        limiter: ConcurrencyLimiter | None = None,
        recovery: RecoveryPlanner | None = None,
    ) -> None:
        self.repository = repository
        self.plugins = plugins
        self.policy = policy
        self.event_root = Path(event_root)
        self.limiter = limiter or ConcurrencyLimiter()
        self.recovery = recovery or RecoveryPlanner()

    def submit(self, spec: TaskSpec) -> TaskRecord:
        return self.repository.create(spec)

    def run_until_terminal(self, task_id: str) -> TaskRecord:
        record = self.repository.get(task_id)
        ledger_path = self.event_root / task_id / "events.jsonl"
        ledger = EventLedger(ledger_path, run_id=task_id, tenant_id=record.spec.tenant_id)
        if record.attempts == 0:
            ledger.append(EventType.RUN_START, {"task_id": task_id, "target": record.spec.target})

        while not record.status.terminal:
            if record.status is not TaskStatus.RUNNING:
                record = self.repository.update(task_id, status=TaskStatus.RUNNING)

            policy_result = self.policy.evaluate(
                ActionRequest(
                    run_id=task_id,
                    target=record.spec.target,
                    action=record.active_plugin,
                    tier=ActionTier.SCAN,
                )
            )
            if policy_result.decision is Decision.PENDING:
                return self.repository.update(
                    task_id,
                    status=TaskStatus.PENDING_APPROVAL,
                    error=policy_result.reason,
                )
            if policy_result.decision is Decision.DENY:
                status = TaskStatus.STOPPED if "stop" in policy_result.reason else TaskStatus.FAILED
                record = self.repository.update(task_id, status=status, error=policy_result.reason)
                ledger.append(
                    EventType.RUN_END, {"status": status.value, "reason": policy_result.reason}
                )
                return record

            attempt = record.attempts + 1
            tracker = BudgetTracker(record.spec.budget)
            tracker.check()
            plugin = self.plugins.get(record.active_plugin)
            ledger.append(
                EventType.TOOL_CALL,
                {"plugin": record.active_plugin, "attempt": attempt, "target": record.spec.target},
            )
            with self.limiter.acquire(
                target=record.spec.target,
                tool=record.active_plugin,
                node=record.spec.node,
            ):
                result = plugin.run(
                    PluginRequest(
                        run_id=task_id,
                        target=record.spec.target,
                        options=record.spec.options,
                    )
                )
            tracker.consume(
                tokens=int(result.metadata.get("tokens", 0)),
                cpu_seconds=float(result.metadata.get("cpu_seconds", 0)),
                memory_mb=int(result.metadata.get("memory_mb", 0)),
                network_bytes=int(result.metadata.get("network_bytes", 0)),
            )
            try:
                tracker.check()
            except BudgetExceeded as exc:
                result = result.model_copy(update={"success": False, "output": str(exc)})
            ledger.append(
                EventType.TOOL_RESULT,
                {"plugin": record.active_plugin, "attempt": attempt, "success": result.success},
            )
            if result.success:
                record = self.repository.update(
                    task_id,
                    status=TaskStatus.SUCCEEDED,
                    attempts=attempt,
                    checkpoint={"completed": True},
                    error="",
                )
                ledger.append(EventType.RUN_END, {"status": TaskStatus.SUCCEEDED.value})
                return record

            tried = set(record.checkpoint.get("tried", [])) | {record.active_plugin}
            replacement = self.recovery.next_plugin(record.active_plugin, tried)
            if attempt < record.spec.max_attempts and replacement is not None:
                record = self.repository.update(
                    task_id,
                    status=TaskStatus.QUEUED,
                    attempts=attempt,
                    active_plugin=replacement,
                    checkpoint={"tried": sorted(tried), "last_failure": result.output},
                    error=result.output,
                )
                continue

            record = self.repository.update(
                task_id,
                status=TaskStatus.FAILED,
                attempts=attempt,
                checkpoint={"tried": sorted(tried), "last_failure": result.output},
                error=result.output,
            )
            ledger.append(EventType.RUN_END, {"status": TaskStatus.FAILED.value})
            return record
        return record
