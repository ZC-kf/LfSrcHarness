"""Unified plugin contract and transport adapters."""

from __future__ import annotations

import json
from collections.abc import Callable
from enum import StrEnum
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, Field

from .policy import PrivilegeRequest
from .runner import (
    CommandSpec,
    DockerRunner,
    DockerRunSpec,
    RunStatus,
    SubprocessRunner,
)


class PluginTransport(StrEnum):
    PYTHON = "python"
    SUBPROCESS = "subprocess"
    HTTP = "http"
    GRPC = "grpc"
    DOCKER = "docker"


class PluginManifest(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    version: str = Field(min_length=1)
    capabilities: set[str] = Field(min_length=1)
    target_types: set[str] = Field(default_factory=set)
    transport: PluginTransport
    description: str = ""


class PluginRequest(BaseModel):
    run_id: str
    target: str
    options: dict[str, Any] = Field(default_factory=dict)


class PluginResult(BaseModel):
    success: bool
    output: str = ""
    parsed: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Plugin(Protocol):
    manifest: PluginManifest

    def validate(self, request: PluginRequest) -> None: ...

    def run(self, request: PluginRequest) -> PluginResult: ...

    def parse(self, output: str) -> Any: ...


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        name = plugin.manifest.name
        if name in self._plugins:
            raise ValueError(f"plugin {name!r} is already registered")
        self._plugins[name] = plugin

    def get(self, name: str) -> Plugin:
        return self._plugins[name]

    def list(self) -> list[PluginManifest]:
        return [self._plugins[name].manifest for name in sorted(self._plugins)]

    def load_entry_points(self, group: str = "lfsrc_harness.plugins") -> None:
        for entry_point in metadata.entry_points(group=group):
            loaded = entry_point.load()
            plugin = loaded() if isinstance(loaded, type) else loaded
            self.register(plugin)


class _BasePlugin:
    def __init__(self, manifest: PluginManifest) -> None:
        self.manifest = manifest

    def validate(self, request: PluginRequest) -> None:
        if not request.run_id or not request.target:
            raise ValueError("run_id and target are required")

    def parse(self, output: str) -> Any:
        return output


class PythonPlugin(_BasePlugin):
    def __init__(
        self,
        manifest: PluginManifest,
        handler: Callable[[PluginRequest], PluginResult],
    ) -> None:
        super().__init__(manifest)
        self.handler = handler

    def run(self, request: PluginRequest) -> PluginResult:
        self.validate(request)
        return self.handler(request)


class SubprocessPlugin(_BasePlugin):
    def __init__(
        self,
        manifest: PluginManifest,
        *,
        command_builder: Callable[[PluginRequest], list[str]],
        parser: Callable[[str], Any] | None = None,
        runner: SubprocessRunner | None = None,
    ) -> None:
        super().__init__(manifest)
        self.command_builder = command_builder
        self._parser = parser
        self.runner = runner or SubprocessRunner()

    def parse(self, output: str) -> Any:
        return self._parser(output) if self._parser else output

    def run(self, request: PluginRequest) -> PluginResult:
        self.validate(request)
        timeout = float(request.options.get("timeout_seconds", 300))
        result = self.runner.run(
            CommandSpec(argv=self.command_builder(request), timeout_seconds=timeout)
        )
        parsed = self.parse(result.stdout) if result.status is RunStatus.SUCCEEDED else None
        return PluginResult(
            success=result.status is RunStatus.SUCCEEDED,
            output=result.stdout,
            parsed=parsed,
            metadata={"stderr": result.stderr, "exit_code": result.exit_code},
        )


class HttpPlugin(_BasePlugin):
    def __init__(
        self,
        manifest: PluginManifest,
        *,
        endpoint: str,
        client: httpx.Client | None = None,
    ) -> None:
        super().__init__(manifest)
        self.endpoint = endpoint
        self.client = client or httpx.Client(timeout=30)

    def run(self, request: PluginRequest) -> PluginResult:
        self.validate(request)
        response = self.client.post(self.endpoint, json=request.model_dump(mode="json"))
        response.raise_for_status()
        parsed = response.json()
        return PluginResult(success=True, output=response.text, parsed=parsed)


class GrpcPlugin(_BasePlugin):
    def __init__(
        self,
        manifest: PluginManifest,
        *,
        channel: Any,
        method: str,
        timeout_seconds: float = 30,
    ) -> None:
        super().__init__(manifest)
        self.channel = channel
        self.method = method
        self.timeout_seconds = timeout_seconds

    def run(self, request: PluginRequest) -> PluginResult:
        self.validate(request)
        invoke = self.channel.unary_unary(self.method)
        payload = json.dumps(request.model_dump(mode="json"), separators=(",", ":")).encode()
        response = invoke(payload, timeout=self.timeout_seconds)
        output = response.decode("utf-8")
        return PluginResult(success=True, output=output, parsed=json.loads(output))


class DockerPlugin(_BasePlugin):
    def __init__(
        self,
        manifest: PluginManifest,
        *,
        spec_builder: Callable[[PluginRequest], DockerRunSpec],
        workspace: str | Path,
        runner: DockerRunner | None = None,
        privileges: PrivilegeRequest | None = None,
        parser: Callable[[str], Any] | None = None,
    ) -> None:
        super().__init__(manifest)
        self.spec_builder = spec_builder
        self.workspace = Path(workspace)
        self.runner = runner or DockerRunner()
        self.privileges = privileges or PrivilegeRequest()
        self._parser = parser

    def parse(self, output: str) -> Any:
        return self._parser(output) if self._parser else output

    def run(self, request: PluginRequest) -> PluginResult:
        self.validate(request)
        result = self.runner.run(self.spec_builder(request), self.workspace, self.privileges)
        return PluginResult(
            success=result.status is RunStatus.SUCCEEDED,
            output=result.stdout,
            parsed=self.parse(result.stdout) if result.status is RunStatus.SUCCEEDED else None,
            metadata={"stderr": result.stderr, "exit_code": result.exit_code},
        )
