import json
from pathlib import Path

from typer.testing import CliRunner

from lfsrc_harness.cli import app
from lfsrc_harness.events import EventLedger, EventType
from lfsrc_harness.orchestration import TaskRepository, TaskStatus

runner = CliRunner()


def write_scope(path: Path) -> None:
    path.write_text(
        """
name: local
targets: [local-node]
time_windows: []
rate_limit: {requests: 10, per_seconds: 60}
prohibited_actions: []
privileges: {}
""".strip(),
        encoding="utf-8",
    )


def test_help_lists_required_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ["run", "batch", "report", "stop", "replay", "status", "plugin", "deploy"]:
        assert command in result.stdout


def test_run_queues_scoped_task_and_status_reads_it(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    scope = tmp_path / "scope.yaml"
    write_scope(scope)

    created = runner.invoke(
        app,
        [
            "run",
            "--scope",
            str(scope),
            "--database",
            str(database),
            "--target",
            "local-node",
            "--objective",
            "fixture",
            "--plugin",
            "fixture",
        ],
    )
    listed = runner.invoke(app, ["status", "--database", str(database)])

    assert created.exit_code == 0
    task_id = json.loads(created.stdout)["id"]
    tasks = json.loads(listed.stdout)
    assert tasks[0]["id"] == task_id
    assert tasks[0]["status"] == "queued"


def test_stop_marks_task_stopped(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    scope = tmp_path / "scope.yaml"
    write_scope(scope)
    created = runner.invoke(
        app,
        [
            "run",
            "--scope",
            str(scope),
            "--database",
            str(database),
            "--target",
            "local-node",
            "--objective",
            "fixture",
            "--plugin",
            "fixture",
        ],
    )
    task_id = json.loads(created.stdout)["id"]

    stopped = runner.invoke(app, ["stop", task_id, "--database", str(database)])

    assert stopped.exit_code == 0
    repository = TaskRepository(database)
    assert repository.get(task_id).status is TaskStatus.STOPPED


def test_replay_outputs_validated_events(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    EventLedger(path, run_id="run-1").append(EventType.RUN_START, {"ok": True})

    result = runner.invoke(app, ["replay", str(path)])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["type"] == "run_start"
