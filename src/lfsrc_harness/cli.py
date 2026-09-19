"""LfSrcHarness command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml

from .events import replay_events
from .orchestration import TaskPriority, TaskRepository, TaskSpec, TaskStatus
from .plugins import PluginRegistry
from .reporting import ReportData, ReportRenderer
from .scope import load_scope

app = typer.Typer(help="LfSrcHarness authorized assessment automation")
plugin_app = typer.Typer(help="Inspect installed plugins")
app.add_typer(plugin_app, name="plugin")


@app.command()
def run(
    scope: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    database: Annotated[Path, typer.Option()] = Path("runs/state.sqlite3"),
    target: Annotated[str, typer.Option()] = "local-node",
    objective: Annotated[str, typer.Option()] = "authorized assessment",
    plugin: Annotated[str, typer.Option()] = "agent",
    priority: Annotated[str, typer.Option()] = "P1",
) -> None:
    """Validate scope and queue one task."""
    scope_config = load_scope(scope)
    scope_config.assert_active()
    scope_config.assert_target(target)
    selected_priority = TaskPriority[priority.upper()]
    repository = TaskRepository(database)
    record = repository.create(
        TaskSpec(
            tenant_id=scope_config.tenant_id,
            target=target,
            objective=objective,
            plugin=plugin,
            priority=selected_priority,
        )
    )
    typer.echo(json.dumps(record.model_dump(mode="json"), ensure_ascii=False))


@app.command()
def batch(
    task_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    scope: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    database: Annotated[Path, typer.Option()] = Path("runs/state.sqlite3"),
) -> None:
    """Validate and queue a YAML list of tasks."""
    scope_config = load_scope(scope)
    scope_config.assert_active()
    raw = yaml.safe_load(task_file.read_text(encoding="utf-8"))
    items = raw.get("tasks", raw) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise typer.BadParameter("task file must contain a list or a tasks list")
    repository = TaskRepository(database)
    created = []
    for item in items:
        spec = TaskSpec.model_validate(item)
        scope_config.assert_target(spec.target)
        created.append(repository.create(spec).model_dump(mode="json"))
    typer.echo(json.dumps(created, ensure_ascii=False))


@app.command("report")
def report_command(
    input_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option()] = Path("runs/reports"),
) -> None:
    """Render all report formats from normalized JSON data."""
    report = ReportData.model_validate_json(input_file.read_text(encoding="utf-8"))
    outputs = ReportRenderer().render_all(report, output)
    typer.echo(json.dumps({key: str(value) for key, value in outputs.items()}))


@app.command()
def stop(
    task_id: Annotated[str, typer.Argument()],
    database: Annotated[Path, typer.Option()] = Path("runs/state.sqlite3"),
) -> None:
    """Persistently stop one queued or running task."""
    repository = TaskRepository(database)
    record = repository.update(task_id, status=TaskStatus.STOPPED, error="stopped by operator")
    typer.echo(json.dumps(record.model_dump(mode="json"), ensure_ascii=False))


@app.command()
def replay(event_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)]) -> None:
    """Validate and replay a JSONL event stream."""
    for event in replay_events(event_file):
        typer.echo(event.model_dump_json())


@app.command()
def status(
    task_id: Annotated[str | None, typer.Argument()] = None,
    database: Annotated[Path, typer.Option()] = Path("runs/state.sqlite3"),
) -> None:
    """Show one task or the ordered task list."""
    repository = TaskRepository(database)
    value = repository.get(task_id) if task_id else repository.list()
    payload: object
    if isinstance(value, list):
        payload = [record.model_dump(mode="json") for record in value]
    else:
        payload = value.model_dump(mode="json")
    typer.echo(json.dumps(payload, ensure_ascii=False))


@plugin_app.command("list")
def plugin_list() -> None:
    """List plugins exposed through Python entry points."""
    registry = PluginRegistry()
    registry.load_entry_points()
    typer.echo(
        json.dumps(
            [manifest.model_dump(mode="json") for manifest in registry.list()], ensure_ascii=False
        )
    )


@app.command()
def deploy(
    profile: Annotated[str, typer.Argument()] = "compose",
    root: Annotated[Path, typer.Option()] = Path("deploy"),
) -> None:
    """Resolve a deployment profile created under deploy/."""
    profiles = {
        "compose": root / "docker-compose.yml",
        "ansible": root / "ansible" / "site.yml",
        "vagrant": root / "Vagrantfile",
        "systemd": root / "systemd" / "lfsrc-harness.service",
        "k8s": root / "k8s" / "lfsrc-harness.yaml",
    }
    if profile not in profiles:
        raise typer.BadParameter(f"unknown profile: {profile}")
    typer.echo(str(profiles[profile].resolve()))


if __name__ == "__main__":
    app()
