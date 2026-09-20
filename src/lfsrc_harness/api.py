"""FastAPI service with token authentication and role-based access control."""

import json
import re
import secrets
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Annotated, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .desktop_settings import DesktopSettingsStore, ProviderSettings, ProviderSettingsInput
from .events import IntegrityError, replay_events
from .orchestration import TaskPriority, TaskRepository, TaskSpec, TaskStatus
from .plugins import PluginRegistry
from .policy import ApprovalStore, EmergencyStopRegistry
from .providers import ModelRequest
from .scope import ScopeConfig, ScopeViolation


class Principal(BaseModel):
    token_name: str
    role: Literal["viewer", "operator", "admin"]


class TaskCreate(BaseModel):
    target: str
    objective: str
    plugin: str
    priority: TaskPriority = TaskPriority.P1
    options: dict[str, object] = Field(default_factory=dict)


class EmergencyStopRequest(BaseModel):
    level: Literal["global", "run", "target"]
    identifier: str | None = None
    action: Literal["stop", "resume"] = "stop"


def create_app(
    *,
    scope: ScopeConfig,
    database: str | Path,
    runs_root: str | Path,
    report_root: str | Path,
    evidence_root: str | Path,
    tokens: dict[str, str],
    approvals: ApprovalStore | None = None,
    stops: EmergencyStopRegistry | None = None,
    settings: DesktopSettingsStore | None = None,
    scope_save: Callable[[ScopeConfig], None] | None = None,
    plugins: PluginRegistry | None = None,
) -> FastAPI:
    app = FastAPI(title="LfSrcHarness API", version="0.1.0")
    repository = TaskRepository(database)
    run_directory = Path(runs_root)
    report_directory = Path(report_root)
    evidence_directory = Path(evidence_root)
    approval_store = approvals or ApprovalStore()
    stop_registry = stops or EmergencyStopRegistry()
    bearer = HTTPBearer(auto_error=False)
    role_rank = {"viewer": 0, "operator": 1, "admin": 2}

    def authenticate(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> Principal:
        if credentials is None or credentials.scheme.casefold() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token"
            )
        matched_role = None
        for configured_token, role in tokens.items():
            if secrets.compare_digest(credentials.credentials, configured_token):
                matched_role = role
                break
        if matched_role not in role_rank:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token"
            )
        return Principal(token_name="configured", role=matched_role)  # type: ignore[arg-type]

    def require(minimum: Literal["viewer", "operator", "admin"]) -> Callable[..., Principal]:
        def dependency(principal: Annotated[Principal, Depends(authenticate)]) -> Principal:
            if role_rank[principal.role] < role_rank[minimum]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role"
                )
            return principal

        return dependency

    viewer = require("viewer")
    operator = require("operator")
    admin = require("admin")

    if scope_save is not None:

        @app.get("/api/settings/scope")
        def get_scope(_: Annotated[Principal, Depends(admin)]) -> ScopeConfig:
            return scope

        @app.put("/api/settings/scope")
        def update_scope(
            payload: ScopeConfig,
            _: Annotated[Principal, Depends(admin)],
        ) -> ScopeConfig:
            nonlocal scope
            scope_save(payload)
            scope = payload
            return scope

    if settings is not None:

        @app.get("/api/settings/providers")
        def list_providers(_: Annotated[Principal, Depends(admin)]) -> list[ProviderSettings]:
            return settings.list_providers()

        @app.put("/api/settings/providers/{name}")
        def save_provider(
            name: str,
            payload: ProviderSettingsInput,
            _: Annotated[Principal, Depends(admin)],
        ) -> ProviderSettings:
            if name != payload.name:
                raise HTTPException(status_code=422, detail="provider name mismatch")
            try:
                return settings.save_provider(payload)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        @app.delete("/api/settings/providers/{name}", status_code=204)
        def delete_provider(name: str, _: Annotated[Principal, Depends(admin)]) -> Response:
            try:
                settings.delete_provider(name)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="provider not found") from exc
            return Response(status_code=204)

        @app.post("/api/models/{name}/generate")
        def generate_with_provider(
            name: str,
            payload: ModelRequest,
            _: Annotated[Principal, Depends(admin)],
        ) -> dict[str, object]:
            try:
                provider = settings.create_provider(name)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="provider not found") from exc
            try:
                answer = provider.generate(payload)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise HTTPException(status_code=502, detail="model request failed") from exc
            finally:
                client = getattr(provider, "client", None)
                if isinstance(client, httpx.Client):
                    client.close()
            return {
                "text": answer.text,
                "finish_reason": answer.finish_reason,
                "usage": answer.usage.model_dump(),
            }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/tasks")
    def list_tasks(_: Annotated[Principal, Depends(viewer)]) -> list[dict[str, object]]:
        return [record.model_dump(mode="json") for record in repository.list()]

    @app.get("/api/plugins")
    def list_plugins(_: Annotated[Principal, Depends(viewer)]) -> list[dict[str, object]]:
        return [manifest.model_dump(mode="json") for manifest in plugins.list()] if plugins else []

    @app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
    def create_task(
        payload: TaskCreate,
        _: Annotated[Principal, Depends(operator)],
    ) -> dict[str, object]:
        try:
            scope.assert_active()
            scope.assert_target(payload.target)
        except ScopeViolation as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if plugins is not None:
            try:
                plugins.get(payload.plugin)
            except KeyError as exc:
                raise HTTPException(status_code=422, detail="plugin is not installed") from exc
        record = repository.create(
            TaskSpec(
                tenant_id=scope.tenant_id,
                target=payload.target,
                objective=payload.objective,
                plugin=payload.plugin,
                priority=payload.priority,
                options=dict(payload.options),
            )
        )
        return record.model_dump(mode="json")

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str, _: Annotated[Principal, Depends(viewer)]) -> dict[str, object]:
        return _task_or_404(repository, task_id)

    @app.post("/api/tasks/{task_id}/stop")
    def stop_task(task_id: str, _: Annotated[Principal, Depends(operator)]) -> dict[str, object]:
        stop_registry.stop_run(task_id)
        try:
            record = repository.update(
                task_id, status=TaskStatus.STOPPED, error="stopped by operator"
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="task not found") from exc
        return record.model_dump(mode="json")

    @app.get("/api/targets")
    def list_targets(_: Annotated[Principal, Depends(viewer)]) -> dict[str, object]:
        return {
            "scope": scope.name,
            "targets": scope.targets,
            "rate_limit": scope.rate_limit.model_dump(mode="json"),
        }

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, _: Annotated[Principal, Depends(viewer)]) -> dict[str, object]:
        return _task_or_404(repository, run_id)

    @app.get("/api/runs/{run_id}/events")
    def get_events(
        run_id: str, _: Annotated[Principal, Depends(viewer)]
    ) -> list[dict[str, object]]:
        path = run_directory / run_id / "events.jsonl"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="event stream not found")
        try:
            return [event.model_dump(mode="json") for event in replay_events(path)]
        except IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}/events/stream")
    def stream_events(
        run_id: str,
        _: Annotated[Principal, Depends(viewer)],
    ) -> StreamingResponse:
        path = run_directory / run_id / "events.jsonl"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="event stream not found")

        def generate() -> Iterator[str]:
            for event in replay_events(path):
                data = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                yield f"event: {event.type.value}\ndata: {data}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.get("/api/evidence/{sha256}")
    def get_evidence(sha256: str, _: Annotated[Principal, Depends(viewer)]) -> FileResponse:
        matches = list(evidence_directory.glob(f"*/*/{sha256}.bin"))
        if not matches:
            raise HTTPException(status_code=404, detail="evidence not found")
        return FileResponse(matches[0])

    @app.get("/api/reports/{run_id}")
    def get_reports(run_id: str, _: Annotated[Principal, Depends(viewer)]) -> dict[str, object]:
        directory = _report_directory(run_id)
        return {
            "run_id": run_id,
            "files": sorted(path.name for path in directory.iterdir() if path.is_file()),
        }

    @app.get("/api/reports/{run_id}/files/{filename}")
    def download_report(
        run_id: str, filename: str, _: Annotated[Principal, Depends(viewer)]
    ) -> FileResponse:
        directory = _report_directory(run_id)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", filename):
            raise HTTPException(status_code=404, detail="report not found")
        path = directory / filename
        if not path.is_file() or not path.resolve().is_relative_to(directory.resolve()):
            raise HTTPException(status_code=404, detail="report not found")
        return FileResponse(path, filename=filename)

    def _report_directory(run_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
            raise HTTPException(status_code=404, detail="reports not found")
        for directory in (run_directory / run_id / "reports", report_directory / run_id):
            if directory.is_dir() and directory.resolve().is_relative_to(
                directory.parent.resolve()
            ):
                return directory
        raise HTTPException(status_code=404, detail="reports not found")

    @app.get("/api/approvals")
    def list_approvals(_: Annotated[Principal, Depends(viewer)]) -> list[dict[str, object]]:
        return [record.model_dump(mode="json") for record in approval_store.list()]

    @app.post("/api/approvals/{approval_id}/approve")
    def approve(
        approval_id: str,
        principal: Annotated[Principal, Depends(admin)],
    ) -> dict[str, object]:
        try:
            record = approval_store.approve(approval_id, actor=principal.role)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="approval not found") from exc
        return record.model_dump(mode="json")

    @app.post("/api/approvals/{approval_id}/reject")
    def reject(
        approval_id: str,
        principal: Annotated[Principal, Depends(admin)],
    ) -> dict[str, object]:
        try:
            record = approval_store.reject(approval_id, actor=principal.role)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="approval not found") from exc
        return record.model_dump(mode="json")

    @app.post("/api/emergency-stop", status_code=status.HTTP_204_NO_CONTENT)
    def emergency_stop(
        payload: EmergencyStopRequest,
        _: Annotated[Principal, Depends(operator)],
    ) -> Response:
        _apply_stop(stop_registry, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


def _task_or_404(repository: TaskRepository, task_id: str) -> dict[str, object]:
    try:
        return repository.get(task_id).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc


def _apply_stop(stops: EmergencyStopRegistry, payload: EmergencyStopRequest) -> None:
    method_name = f"{payload.action}_{payload.level}"
    method = getattr(stops, method_name)
    if payload.level == "global":
        method()
        return
    if not payload.identifier:
        raise HTTPException(status_code=422, detail="identifier is required")
    method(payload.identifier)
