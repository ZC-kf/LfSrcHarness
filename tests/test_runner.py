import sys
from pathlib import Path

import pytest

from lfsrc_harness.policy import PrivilegeRequest
from lfsrc_harness.runner import (
    CircuitBreaker,
    CircuitOpen,
    CommandSpec,
    DockerRunSpec,
    RunStatus,
    SubprocessRunner,
    WorkspaceManager,
    build_container_config,
)


def test_subprocess_runner_captures_structured_result() -> None:
    result = SubprocessRunner().run(
        CommandSpec(argv=[sys.executable, "-c", "print('ok')"], timeout_seconds=5)
    )

    assert result.status is RunStatus.SUCCEEDED
    assert result.exit_code == 0
    assert result.stdout.strip() == "ok"
    assert result.attempts == 1


def test_subprocess_runner_times_out_without_using_shell() -> None:
    result = SubprocessRunner().run(
        CommandSpec(
            argv=[sys.executable, "-c", "import time; time.sleep(2)"],
            timeout_seconds=0.05,
        )
    )

    assert result.status is RunStatus.TIMED_OUT
    assert result.exit_code is None


def test_runner_retries_with_bounded_attempts(tmp_path: Path) -> None:
    counter = tmp_path / "counter.txt"
    code = (
        "from pathlib import Path; import sys; "
        f"p=Path({str(counter)!r}); n=int(p.read_text())+1 if p.exists() else 1; "
        "p.write_text(str(n)); sys.exit(0 if n == 2 else 3)"
    )
    result = SubprocessRunner(sleeper=lambda _: None).run(
        CommandSpec(
            argv=[sys.executable, "-c", code],
            timeout_seconds=5,
            retries=1,
            backoff_seconds=0,
        )
    )

    assert result.status is RunStatus.SUCCEEDED
    assert result.attempts == 2


def test_workspace_manager_cleans_ephemeral_directory(tmp_path: Path) -> None:
    manager = WorkspaceManager(tmp_path)

    with manager.create("run-1") as workspace:
        workspace_path = workspace
        (workspace / "proof.txt").write_text("proof", encoding="utf-8")
        assert workspace.exists()

    assert not workspace_path.exists()


def test_docker_config_is_restricted_by_default(tmp_path: Path) -> None:
    spec = DockerRunSpec(image="example/tool:1", command=["--version"])

    config = build_container_config(spec, tmp_path, PrivilegeRequest())

    assert config["read_only"] is True
    assert config["network_mode"] == "none"
    assert config["privileged"] is False
    assert config["pids_limit"] == 256
    assert all(mode["mode"] == "ro" for mode in config["volumes"].values())


def test_docker_config_exposes_each_explicit_privilege(tmp_path: Path) -> None:
    privileges = PrivilegeRequest(
        privileged_container=True,
        host_network=True,
        docker_socket=True,
    )

    config = build_container_config(
        DockerRunSpec(image="example/tool:1", command=[]), tmp_path, privileges
    )

    assert config["privileged"] is True
    assert config["network_mode"] == "host"
    assert config["volumes"]["/var/run/docker.sock"]["mode"] == "rw"


def test_circuit_breaker_opens_after_failure_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=2, reset_after_seconds=60)
    breaker.record_failure()
    breaker.record_failure()

    with pytest.raises(CircuitOpen):
        breaker.ensure_closed()

    breaker.record_success()
    breaker.ensure_closed()
