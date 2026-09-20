"""Native desktop entry point with an in-process, loopback-only API."""

from __future__ import annotations

import os
import secrets
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import create_app
from .desktop_settings import DesktopSettingsStore, SecretStore
from .events import EventLedger, EventType
from .orchestration import Orchestrator, TaskRepository, TaskStatus
from .plugins import PluginManifest, PluginRegistry, PluginResult, PluginTransport, PythonPlugin
from .policy import ApprovalStore, EmergencyStopRegistry, PolicyEngine
from .scope import ScopeConfig, load_scope


@dataclass
class DesktopRuntime:
    app: FastAPI
    token: str
    data_root: Path
    local_worker: LocalTaskWorker | None = None


class LocalTaskWorker:
    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator
        self._stop = Event()
        self._thread = Thread(target=self._run, daemon=True, name="lfsrc-local-worker")

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            record = self.orchestrator.repository.claim_next()
            if record is None:
                self._stop.wait(0.1)
                continue
            try:
                self.orchestrator.run_until_terminal(record.id)
            except Exception as exc:
                reason = f"local execution failed: {type(exc).__name__}"
                self.orchestrator.repository.update(
                    record.id, status=TaskStatus.FAILED, error=reason,
                )
                EventLedger(
                    self.orchestrator.event_root / record.id / "events.jsonl",
                    run_id=record.id, tenant_id=record.spec.tenant_id,
                ).append(EventType.RUN_END, {"status": TaskStatus.FAILED.value, "reason": reason})


class DesktopBridge:
    def __init__(self, token: str) -> None:
        self._token = token

    def get_token(self) -> str:
        return self._token


def resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(frozen_root) if frozen_root else Path(__file__).resolve().parents[2]


def user_data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "LfSrcHarness"
    return Path.home() / ".local" / "share" / "LfSrcHarness"


def create_desktop_runtime(
    *,
    resources: Path | None = None,
    data_root: Path | None = None,
    secret_store: SecretStore | None = None,
) -> DesktopRuntime:
    resources = resources or resource_root()
    data_root = data_root or user_data_root()
    web_directory = resources / "web" / "dist"
    if not (web_directory / "index.html").is_file():
        raise FileNotFoundError(f"desktop UI is missing: {web_directory / 'index.html'}")
    data_root.mkdir(parents=True, exist_ok=True)
    scope_path = data_root / "scope.json"
    scope = (
        ScopeConfig.model_validate_json(scope_path.read_text(encoding="utf-8"))
        if scope_path.is_file()
        else load_scope(resources / "deploy" / "config" / "scope.yaml")
    )
    approvals = ApprovalStore()
    stops = EmergencyStopRegistry()
    policy = PolicyEngine(scope, approvals=approvals, stops=stops)
    plugins = PluginRegistry()
    plugins.register(PythonPlugin(
        PluginManifest(
            name="desktop-diagnostics", version="1", capabilities={"local_diagnostics"},
            target_types={"local"}, transport=PluginTransport.PYTHON,
            description="Checks the local task, policy and audit pipeline without target access.",
        ),
        lambda _: PluginResult(success=True, output="Local desktop execution is operational."),
    ))
    runs_root = data_root / "runs"
    local_worker = LocalTaskWorker(Orchestrator(
        TaskRepository(data_root / "state.sqlite3"), plugins, policy, event_root=runs_root,
    ))

    def save_scope(value: ScopeConfig) -> None:
        temporary = scope_path.with_suffix(".json.tmp")
        temporary.write_text(value.model_dump_json(indent=2), encoding="utf-8")
        os.replace(temporary, scope_path)
        policy.scope = value

    token = secrets.token_urlsafe(32)
    app = create_app(
        scope=scope,
        database=data_root / "state.sqlite3",
        runs_root=runs_root,
        report_root=data_root / "reports",
        evidence_root=data_root / "evidence",
        tokens={token: "admin"},
        settings=DesktopSettingsStore(data_root / "settings.json", secrets=secret_store),
        scope_save=save_scope,
        approvals=approvals,
        stops=stops,
        plugins=plugins,
    )
    app.mount("/", StaticFiles(directory=web_directory, html=True), name="desktop")
    return DesktopRuntime(app=app, token=token, data_root=data_root, local_worker=local_worker)


def main() -> None:
    runtime = create_desktop_runtime()
    if "--self-test" in sys.argv:
        from fastapi.testclient import TestClient

        _server_config(runtime.app, 0)
        with TestClient(runtime.app) as client:
            if client.get("/health").status_code != 200:
                raise RuntimeError("desktop API health check failed")
            if client.get("/").status_code != 200:
                raise RuntimeError("desktop UI health check failed")
        return
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(_server_config(runtime.app, port))
    server_thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    if runtime.local_worker is not None:
        runtime.local_worker.start()
    server_thread.start()
    try:
        import webview

        webview.create_window(
            "LfSrcHarness", f"http://127.0.0.1:{port}/",
            js_api=DesktopBridge(runtime.token), width=1280, height=800, min_size=(960, 640),
        )
        webview.start(gui="edgechromium" if sys.platform == "win32" else None)
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)
        if runtime.local_worker is not None:
            runtime.local_worker.stop()
        listener.close()


def _server_config(app: FastAPI, port: int) -> uvicorn.Config:
    # PyInstaller's windowed entry has no stdout/stderr; Uvicorn's default
    # colour formatter calls sys.stdout.isatty() during Config construction.
    return uvicorn.Config(
        app, host="127.0.0.1", port=port, access_log=False, log_config=None,
    )
