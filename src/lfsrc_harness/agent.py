"""Adapters for invoking Agents through Python, CLI, HTTP, or gRPC."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterable, Iterator
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from .proto import lfsrc_harness_pb2


class AgentRequest(BaseModel):
    run_id: str
    objective: str
    scope_path: str
    context: dict[str, Any] = Field(default_factory=dict)


class AgentEvent(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentAdapter(Protocol):
    def run(self, request: AgentRequest) -> Iterator[AgentEvent]: ...


class PythonAgentAdapter:
    def __init__(
        self, handler: Callable[[AgentRequest], Iterable[dict[str, Any] | AgentEvent]]
    ) -> None:
        self.handler = handler

    def run(self, request: AgentRequest) -> Iterator[AgentEvent]:
        for item in self.handler(request):
            yield _normalize_event(item)


class CliAgentAdapter:
    def __init__(self, command: list[str], *, timeout_seconds: float = 3600) -> None:
        if not command:
            raise ValueError("Agent command must not be empty")
        self.command = command
        self.timeout_seconds = timeout_seconds

    def run(self, request: AgentRequest) -> Iterator[AgentEvent]:
        completed = subprocess.run(
            self.command,
            input=request.model_dump_json(),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
            shell=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Agent process failed")
        for line in completed.stdout.splitlines():
            if line.strip():
                yield _normalize_event(json.loads(line))


class HttpAgentAdapter:
    def __init__(self, endpoint: str, *, client: httpx.Client | None = None) -> None:
        self.endpoint = endpoint
        self.client = client or httpx.Client(timeout=3600)

    def run(self, request: AgentRequest) -> Iterator[AgentEvent]:
        response = self.client.post(self.endpoint, json=request.model_dump(mode="json"))
        response.raise_for_status()
        for item in response.json().get("events", []):
            yield _normalize_event(item)


class GrpcAgentAdapter:
    def __init__(
        self,
        channel: Any,
        *,
        method: str = "/lfsrc.Agent/Run",
        timeout_seconds: float = 3600,
        token: str | None = None,
    ) -> None:
        self.channel = channel
        self.method = method
        self.timeout_seconds = timeout_seconds
        self.token = token

    def run(self, request: AgentRequest) -> Iterator[AgentEvent]:
        invoke = self.channel.unary_unary(
            self.method,
            request_serializer=lfsrc_harness_pb2.JsonEnvelope.SerializeToString,
            response_deserializer=lfsrc_harness_pb2.JsonEnvelope.FromString,
        )
        metadata = (("authorization", f"Bearer {self.token}"),) if self.token else ()
        response = invoke(
            lfsrc_harness_pb2.JsonEnvelope(json=request.model_dump_json().encode()),
            timeout=self.timeout_seconds,
            metadata=metadata,
        )
        for item in json.loads(response.json).get("events", []):
            yield _normalize_event(item)


def _normalize_event(item: dict[str, Any] | AgentEvent) -> AgentEvent:
    if isinstance(item, AgentEvent):
        return item
    event_type = str(item.get("type", "message"))
    if isinstance(item.get("data"), dict):
        data = dict(item["data"])
    else:
        data = {key: value for key, value in item.items() if key != "type"}
    return AgentEvent(type=event_type, data=data)
