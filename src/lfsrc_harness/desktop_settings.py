"""Desktop provider metadata; credentials are kept in the OS secret store."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field, HttpUrl, SecretStr

from .providers import (
    AnthropicProvider,
    GeminiProvider,
    ModelProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    ProviderConfig,
)

_SERVICE = "LfSrcHarness provider credentials"
_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class SecretStore(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class ProviderSettingsInput(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    kind: Literal["openai_compatible", "anthropic", "gemini", "ollama"]
    base_url: HttpUrl
    model: str = Field(min_length=1, max_length=200)
    api_key: str | None = Field(default=None, min_length=1, repr=False)


class ProviderSettings(BaseModel):
    name: str
    kind: Literal["openai_compatible", "anthropic", "gemini", "ollama"]
    base_url: HttpUrl
    model: str
    has_api_key: bool


class DesktopSettingsStore:
    def __init__(self, path: str | Path, *, secrets: SecretStore | None = None) -> None:
        self.path = Path(path)
        if secrets is None:
            import keyring

            secrets = keyring
        self.secrets = secrets

    def _read(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid desktop settings")
        return data

    def _write(self, data: dict[str, dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def save_provider(self, payload: ProviderSettingsInput) -> ProviderSettings:
        if not _NAME.fullmatch(payload.name):
            raise ValueError("provider name must contain only letters, digits, _ or -")
        data = self._read()
        if payload.api_key is not None:
            self.secrets.set_password(_SERVICE, payload.name, payload.api_key)
        data[payload.name] = {
            "name": payload.name,
            "kind": payload.kind,
            "base_url": str(payload.base_url),
            "model": payload.model,
        }
        self._write(data)
        return self._public(data[payload.name])

    def _public(self, entry: dict[str, str]) -> ProviderSettings:
        return ProviderSettings.model_validate({
            **entry,
            "has_api_key": self.get_api_key(entry["name"]) is not None,
        })

    def list_providers(self) -> list[ProviderSettings]:
        return [self._public(item) for _, item in sorted(self._read().items())]

    def get_api_key(self, name: str) -> str | None:
        return self.secrets.get_password(_SERVICE, name)

    def create_provider(self, name: str, *, client: httpx.Client | None = None) -> ModelProvider:
        data = self._read()
        if name not in data:
            raise KeyError(name)
        entry = data[name]
        key = self.get_api_key(name)
        config = ProviderConfig(
            name=name,
            base_url=entry["base_url"],
            model=entry["model"],
            api_key=SecretStr(key) if key else None,
        )
        kind = entry["kind"]
        if kind == "openai_compatible":
            return OpenAICompatibleProvider(config, client=client)
        if kind == "anthropic":
            return AnthropicProvider(config, client=client)
        if kind == "gemini":
            return GeminiProvider(config, client=client)
        if kind == "ollama":
            return OllamaProvider(config, client=client)
        raise ValueError(f"unsupported provider kind: {kind}")

    def delete_provider(self, name: str) -> None:
        data = self._read()
        if name not in data:
            raise KeyError(name)
        del data[name]
        self._write(data)
        if self.get_api_key(name) is not None:
            self.secrets.delete_password(_SERVICE, name)
