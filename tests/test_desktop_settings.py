from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from lfsrc_harness.api import create_app
from lfsrc_harness.desktop_settings import DesktopSettingsStore, ProviderSettingsInput
from lfsrc_harness.providers import Message, ModelRequest
from lfsrc_harness.scope import ScopeConfig


class MemorySecrets:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[service, username] = password

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


def test_provider_settings_keep_secret_out_of_disk_and_read_api(tmp_path: Path) -> None:
    secrets = MemorySecrets()
    store = DesktopSettingsStore(tmp_path / "settings.json", secrets=secrets)
    saved = store.save_provider(
        ProviderSettingsInput(
            name="deepseek", kind="openai_compatible", base_url="https://api.example.test/v1",
            model="example-model", api_key="super-private-key",
        )
    )

    assert saved.has_api_key is True
    assert "super-private-key" not in (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert "super-private-key" not in saved.model_dump_json()
    assert store.get_api_key("deepseek") == "super-private-key"
    assert store.list_providers()[0].name == "deepseek"


def test_provider_update_preserves_key_and_delete_removes_it(tmp_path: Path) -> None:
    secrets = MemorySecrets()
    store = DesktopSettingsStore(tmp_path / "settings.json", secrets=secrets)
    first = ProviderSettingsInput(
        name="local", kind="openai_compatible", base_url="http://127.0.0.1:8080/v1",
        model="qwen", api_key="local-password",
    )
    store.save_provider(first)
    store.save_provider(first.model_copy(update={"model": "qwen-new", "api_key": None}))

    assert store.get_api_key("local") == "local-password"
    assert store.list_providers()[0].model == "qwen-new"
    store.delete_provider("local")
    assert store.list_providers() == []
    assert store.get_api_key("local") is None


def test_provider_settings_api_is_admin_only_and_redacted(tmp_path: Path) -> None:
    store = DesktopSettingsStore(tmp_path / "settings.json", secrets=MemorySecrets())
    scope = ScopeConfig.model_validate({
        "name": "local", "targets": ["local-node"], "time_windows": [],
        "rate_limit": {"requests": 10, "per_seconds": 60},
        "prohibited_actions": [], "privileges": {},
    })
    app = create_app(
        scope=scope, database=tmp_path / "state.sqlite3", runs_root=tmp_path / "runs",
        report_root=tmp_path / "reports", evidence_root=tmp_path / "evidence",
        tokens={"viewer-token": "viewer", "admin-token": "admin"}, settings=store,
    )
    client = TestClient(app)
    payload = {
        "name": "cloud", "kind": "openai_compatible", "base_url": "https://api.example.test/v1",
        "model": "example-model", "api_key": "api-top-secret",
    }

    assert client.put("/api/settings/providers/cloud", json=payload,
                      headers={"Authorization": "Bearer viewer-token"}).status_code == 403
    response = client.put("/api/settings/providers/cloud", json=payload,
                          headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    assert "api-top-secret" not in response.text
    listed = client.get("/api/settings/providers", headers={"Authorization": "Bearer admin-token"})
    assert listed.status_code == 200
    assert "api-top-secret" not in listed.text
    assert listed.json()[0]["has_api_key"] is True
    assert client.delete("/api/settings/providers/cloud",
                         headers={"Authorization": "Bearer admin-token"}).status_code == 204


def test_settings_reject_name_mismatch(tmp_path: Path) -> None:
    store = DesktopSettingsStore(tmp_path / "settings.json", secrets=MemorySecrets())
    with pytest.raises(ValueError):
        store.save_provider(ProviderSettingsInput(
            name="../escape", kind="ollama", base_url="http://127.0.0.1:11434",
            model="local",
        ))


def test_saved_secret_is_used_by_runtime_provider(tmp_path: Path) -> None:
    store = DesktopSettingsStore(tmp_path / "settings.json", secrets=MemorySecrets())
    store.save_provider(ProviderSettingsInput(
        name="cloud", kind="openai_compatible", base_url="https://api.example.test/v1",
        model="example-model", api_key="runtime-only-secret",
    ))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer runtime-only-secret"
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        })

    provider = store.create_provider(
        "cloud", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = provider.generate(ModelRequest(messages=[Message(role="user", content="hello")]))

    assert result.text == "ok"
    assert "runtime-only-secret" not in provider.config.model_dump_json()


def test_scope_can_be_changed_in_api_and_is_applied_immediately(tmp_path: Path) -> None:
    saved: list[ScopeConfig] = []
    app = create_app(
        scope=ScopeConfig.model_validate({"name": "lab", "targets": ["local-node"]}),
        database=tmp_path / "state.sqlite3", runs_root=tmp_path / "runs",
        report_root=tmp_path / "reports", evidence_root=tmp_path / "evidence",
        tokens={"admin-token": "admin"}, scope_save=saved.append,
    )
    api = TestClient(app)
    auth = {"Authorization": "Bearer admin-token"}
    new_scope = {"name": "lab", "targets": ["another-local-node"],
                 "rate_limit": {"requests": 5, "per_seconds": 60}}

    assert api.put("/api/settings/scope", json=new_scope, headers=auth).status_code == 200
    assert saved[0].targets == ["another-local-node"]
    assert api.get("/api/targets", headers=auth).json()["targets"] == ["another-local-node"]
    task = {"target": "another-local-node", "objective": "fixture", "plugin": "fixture"}
    assert api.post("/api/tasks", json=task, headers=auth).status_code == 201
    assert api.post("/api/tasks", json={**task, "target": "local-node"},
                    headers=auth).status_code == 422


def test_configured_model_can_be_called_through_api(tmp_path: Path) -> None:
    store = DesktopSettingsStore(tmp_path / "settings.json", secrets=MemorySecrets())
    store.save_provider(ProviderSettingsInput(
        name="local", kind="openai_compatible", base_url="http://127.0.0.1:8080/v1",
        model="fixture",
    ))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    original_create = store.create_provider
    store.create_provider = lambda name: original_create(  # type: ignore[method-assign]
        name, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    app = create_app(
        scope=ScopeConfig.model_validate({"name": "local", "targets": ["local-node"]}),
        database=tmp_path / "state.sqlite3", runs_root=tmp_path / "runs",
        report_root=tmp_path / "reports", evidence_root=tmp_path / "evidence",
        tokens={"admin-token": "admin", "viewer-token": "viewer"}, settings=store,
    )
    api = TestClient(app)
    payload = {"messages": [{"role": "user", "content": "say hello"}]}

    assert api.post("/api/models/local/generate", json=payload, headers={
        "Authorization": "Bearer viewer-token",
    }).status_code == 403
    response = api.post("/api/models/local/generate", json=payload, headers={
        "Authorization": "Bearer admin-token",
    })
    assert response.status_code == 200
    assert response.json()["text"] == "hello"
    assert "raw" not in response.json()
