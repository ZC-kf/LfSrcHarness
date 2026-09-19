"""Bounded subprocess and Docker execution primitives."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from threading import RLock
from typing import Any

import docker
from docker.errors import DockerException

from .policy import PrivilegeRequest


class RunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CommandSpec:
    argv: list[str]
    timeout_seconds: float = 300
    retries: int = 0
    backoff_seconds: float = 1
    cwd: Path | None = None
    env: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.argv:
            raise ValueError("argv must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.retries < 0 or self.backoff_seconds < 0:
            raise ValueError("retry values must not be negative")


@dataclass(frozen=True, slots=True)
class RunResult:
    status: RunStatus
    exit_code: int | None
    stdout: str
    stderr: str
    attempts: int
    duration_seconds: float


class CircuitOpen(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 3, reset_after_seconds: float = 60) -> None:
        if failure_threshold <= 0 or reset_after_seconds <= 0:
            raise ValueError("circuit-breaker limits must be positive")
        self.failure_threshold = failure_threshold
        self.reset_after_seconds = reset_after_seconds
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = RLock()

    def ensure_closed(self) -> None:
        with self._lock:
            if self._opened_at is None:
                return
            if time.monotonic() - self._opened_at >= self.reset_after_seconds:
                self._failures = 0
                self._opened_at = None
                return
            raise CircuitOpen("runner circuit breaker is open")

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_at = time.monotonic()

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None


class WorkspaceManager:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def create(self, run_id: str, *, preserve: bool = False) -> Iterator[Path]:
        safe_id = "".join(
            character for character in run_id if character.isalnum() or character in "-_"
        )
        if not safe_id:
            raise ValueError("run_id has no safe path characters")
        path = self.root / f"{safe_id}-{time.time_ns()}"
        path.mkdir(parents=False, exist_ok=False)
        try:
            yield path
        finally:
            if not preserve:
                shutil.rmtree(path, ignore_errors=False)


class SubprocessRunner:
    def __init__(
        self,
        *,
        breaker: CircuitBreaker | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.breaker = breaker or CircuitBreaker()
        self.sleeper = sleeper

    def run(self, spec: CommandSpec) -> RunResult:
        self.breaker.ensure_closed()
        started = time.monotonic()
        last_result: RunResult | None = None
        for attempt in range(1, spec.retries + 2):
            last_result = self._run_once(spec, attempt, started)
            if last_result.status is RunStatus.SUCCEEDED:
                self.breaker.record_success()
                return last_result
            if attempt <= spec.retries:
                self.sleeper(spec.backoff_seconds * (2 ** (attempt - 1)))
        self.breaker.record_failure()
        if last_result is None:  # pragma: no cover - the loop always runs once
            raise RuntimeError("runner did not execute")
        return last_result

    def _run_once(self, spec: CommandSpec, attempt: int, started: float) -> RunResult:
        environment = os.environ.copy()
        environment.update(spec.env)
        try:
            completed = subprocess.run(
                spec.argv,
                cwd=spec.cwd,
                env=environment,
                capture_output=True,
                text=True,
                timeout=spec.timeout_seconds,
                check=False,
                shell=False,
            )
            return RunResult(
                status=(RunStatus.SUCCEEDED if completed.returncode == 0 else RunStatus.FAILED),
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                attempts=attempt,
                duration_seconds=time.monotonic() - started,
            )
        except subprocess.TimeoutExpired as exc:
            return RunResult(
                status=RunStatus.TIMED_OUT,
                exit_code=None,
                stdout=_timeout_text(exc.stdout),
                stderr=_timeout_text(exc.stderr),
                attempts=attempt,
                duration_seconds=time.monotonic() - started,
            )


@dataclass(frozen=True, slots=True)
class DockerRunSpec:
    image: str
    command: list[str]
    timeout_seconds: float = 600
    memory_limit: str = "1g"
    nano_cpus: int = 1_000_000_000
    pids_limit: int = 256
    environment: dict[str, str] = field(default_factory=dict)


def build_container_config(
    spec: DockerRunSpec,
    workspace: str | Path,
    privileges: PrivilegeRequest,
) -> dict[str, Any]:
    volumes: dict[str, dict[str, str]] = {
        str(Path(workspace).resolve()): {"bind": "/workspace", "mode": "ro"}
    }
    if privileges.docker_socket:
        volumes["/var/run/docker.sock"] = {
            "bind": "/var/run/docker.sock",
            "mode": "rw",
        }
    return {
        "image": spec.image,
        "command": spec.command,
        "detach": True,
        "read_only": True,
        "network_mode": "host" if privileges.host_network else "none",
        "privileged": privileges.privileged_container,
        "volumes": volumes,
        "mem_limit": spec.memory_limit,
        "nano_cpus": spec.nano_cpus,
        "pids_limit": spec.pids_limit,
        "environment": spec.environment,
        "security_opt": [] if privileges.privileged_container else ["no-new-privileges:true"],
    }


class DockerRunner:
    def __init__(self, client: Any | None = None) -> None:
        self.client = client or docker.from_env()

    def run(
        self,
        spec: DockerRunSpec,
        workspace: str | Path,
        privileges: PrivilegeRequest,
    ) -> RunResult:
        started = time.monotonic()
        container = None
        try:
            container = self.client.containers.run(
                **build_container_config(spec, workspace, privileges)
            )
            response = container.wait(timeout=spec.timeout_seconds)
            code = int(response.get("StatusCode", 1))
            output = container.logs(stdout=True, stderr=False).decode(errors="replace")
            error = container.logs(stdout=False, stderr=True).decode(errors="replace")
            return RunResult(
                status=RunStatus.SUCCEEDED if code == 0 else RunStatus.FAILED,
                exit_code=code,
                stdout=output,
                stderr=error,
                attempts=1,
                duration_seconds=time.monotonic() - started,
            )
        except (DockerException, TimeoutError) as exc:
            return RunResult(
                status=RunStatus.FAILED,
                exit_code=None,
                stdout="",
                stderr=str(exc),
                attempts=1,
                duration_seconds=time.monotonic() - started,
            )
        finally:
            if container is not None:
                container.remove(force=True)


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value
