"""Native desktop entry point with an in-process, loopback-only API."""

from __future__ import annotations

import os
import secrets
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from threading import Thread

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import create_app
from .desktop_settings import DesktopSettingsStore, SecretStore
from .scope import ScopeConfig, load_scope


@dataclass
class DesktopRuntime:
    app: FastAPI
    token: str
    data_root: Path


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

    def save_scope(value: ScopeConfig) -> None:
        temporary = scope_path.with_suffix(".json.tmp")
        temporary.write_text(value.model_dump_json(indent=2), encoding="utf-8")
        os.replace(temporary, scope_path)

    token = secrets.token_urlsafe(32)
    app = create_app(
        scope=scope,
        database=data_root / "state.sqlite3",
        runs_root=data_root / "runs",
        report_root=data_root / "reports",
        evidence_root=data_root / "evidence",
        tokens={token: "admin"},
        settings=DesktopSettingsStore(data_root / "settings.json", secrets=secret_store),
        scope_save=save_scope,
    )
    app.mount("/", StaticFiles(directory=web_directory, html=True), name="desktop")
    return DesktopRuntime(app=app, token=token, data_root=data_root)


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
    worker = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    worker.start()
    try:
        import webview

        webview.create_window(
            "LfSrcHarness", f"http://127.0.0.1:{port}/",
            js_api=DesktopBridge(runtime.token), width=1280, height=800, min_size=(960, 640),
        )
        webview.start(gui="edgechromium" if sys.platform == "win32" else None)
    finally:
        server.should_exit = True
        worker.join(timeout=5)
        listener.close()


def _server_config(app: FastAPI, port: int) -> uvicorn.Config:
    # PyInstaller's windowed entry has no stdout/stderr; Uvicorn's default
    # colour formatter calls sys.stdout.isatty() during Config construction.
    return uvicorn.Config(
        app, host="127.0.0.1", port=port, access_log=False, log_config=None,
    )
