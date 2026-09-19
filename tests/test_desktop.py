import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import lfsrc_harness.desktop as desktop
from lfsrc_harness.desktop import create_desktop_runtime


class MemorySecrets:
    def get_password(self, service: str, username: str) -> str | None:
        return None

    def set_password(self, service: str, username: str, password: str) -> None:
        pass

    def delete_password(self, service: str, username: str) -> None:
        pass


def test_desktop_runtime_serves_ui_and_api_without_external_services(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    config = resources / "deploy" / "config"
    config.mkdir(parents=True)
    (config / "scope.yaml").write_text(
        "name: local\ntargets: [local-node]\nrate_limit: {requests: 10, per_seconds: 60}\n",
        encoding="utf-8",
    )
    web = resources / "web" / "dist"
    web.mkdir(parents=True)
    (web / "index.html").write_text("<html>Harness desktop</html>", encoding="utf-8")

    runtime = create_desktop_runtime(
        resources=resources, data_root=tmp_path / "data", secret_store=MemorySecrets(),
    )
    api = TestClient(runtime.app)

    assert api.get("/health").json() == {"status": "ok"}
    assert "Harness desktop" in api.get("/").text
    assert api.get("/api/settings/providers", headers={
        "Authorization": f"Bearer {runtime.token}",
    }).json() == []
    assert api.get("/api/settings/providers").status_code == 401
    auth = {"Authorization": f"Bearer {runtime.token}"}
    assert api.put("/api/settings/scope", headers=auth, json={
        "name": "updated", "targets": ["other-node"],
    }).status_code == 200
    restarted = create_desktop_runtime(
        resources=resources, data_root=tmp_path / "data", secret_store=MemorySecrets(),
    )
    assert TestClient(restarted.app).get("/api/targets", headers={
        "Authorization": f"Bearer {restarted.token}",
    }).json()["targets"] == ["other-node"]


def test_windowed_entry_starts_without_console_streams(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI()
    monkeypatch.setattr(desktop, "create_desktop_runtime", lambda: desktop.DesktopRuntime(
        app=app, token="token", data_root=tmp_path,
    ))
    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(
        create_window=lambda *args, **kwargs: None,
        start=lambda **kwargs: None,
    ))
    monkeypatch.setattr(desktop.uvicorn, "Server", lambda config: SimpleNamespace(
        run=lambda **kwargs: None, should_exit=False,
    ))
    monkeypatch.setattr(sys, "argv", ["LfSrcHarness.exe"])
    with monkeypatch.context() as no_console:
        no_console.setattr(sys, "stdout", None)
        no_console.setattr(sys, "stderr", None)
        desktop.main()


def test_self_test_checks_server_configuration_without_console(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def index() -> str:
        return "desktop"

    monkeypatch.setattr(desktop, "create_desktop_runtime", lambda: desktop.DesktopRuntime(
        app=app, token="token", data_root=tmp_path,
    ))
    monkeypatch.setattr(sys, "argv", ["LfSrcHarness.exe", "--self-test"])
    original_config = desktop.uvicorn.Config
    configured = []

    def record_config(*args, **kwargs):
        config = original_config(*args, **kwargs)
        configured.append(config)
        return config

    monkeypatch.setattr(desktop.uvicorn, "Config", record_config)
    with monkeypatch.context() as no_console:
        no_console.setattr(sys, "stdout", None)
        no_console.setattr(sys, "stderr", None)
        desktop.main()
    assert len(configured) == 1
