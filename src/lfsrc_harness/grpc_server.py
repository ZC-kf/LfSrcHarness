"""gRPC server exposing the same JSON Agent contract as the other adapters."""

from __future__ import annotations

import json
import os
import secrets
from concurrent import futures
from typing import Any

import grpc

from .agent import AgentAdapter, AgentRequest, CliAgentAdapter, PythonAgentAdapter
from .proto import lfsrc_harness_pb2


class JsonAgentService:
    def __init__(self, adapter: AgentAdapter, *, token: str | None = None) -> None:
        self.adapter = adapter
        self.token = token

    def run(
        self,
        payload: lfsrc_harness_pb2.JsonEnvelope,
        context: grpc.ServicerContext[Any, Any],
    ) -> lfsrc_harness_pb2.JsonEnvelope:
        if self.token:
            authorization = next(
                (value for key, value in context.invocation_metadata() if key == "authorization"),
                "",
            )
            if not secrets.compare_digest(authorization, f"Bearer {self.token}"):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid bearer token")
        try:
            request = AgentRequest.model_validate_json(payload.json)
            events = [event.model_dump(mode="json") for event in self.adapter.run(request)]
            return lfsrc_harness_pb2.JsonEnvelope(
                json=json.dumps({"events": events}, separators=(",", ":")).encode()
            )
        except (ValueError, RuntimeError) as exc:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            raise AssertionError("context.abort must terminate the RPC") from exc


def create_server(
    adapter: AgentAdapter,
    *,
    host: str = "127.0.0.1",
    port: int = 8621,
    workers: int = 8,
    token: str | None = None,
) -> tuple[grpc.Server, int]:
    if host not in {"127.0.0.1", "::1", "localhost"} and not token:
        raise ValueError("gRPC token is required for nonlocal binding")
    service = JsonAgentService(adapter, token=token)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=workers))
    method = grpc.unary_unary_rpc_method_handler(
        service.run,
        request_deserializer=lfsrc_harness_pb2.JsonEnvelope.FromString,
        response_serializer=lfsrc_harness_pb2.JsonEnvelope.SerializeToString,
    )
    server.add_generic_rpc_handlers(
        (grpc.method_handlers_generic_handler("lfsrc.Agent", {"Run": method}),)
    )
    bound_port = server.add_insecure_port(f"{host}:{port}")
    if bound_port == 0:
        raise RuntimeError(f"unable to bind gRPC server on {host}:{port}")
    return server, bound_port


def main() -> None:
    command_json = os.environ.get("LFSRC_AGENT_COMMAND_JSON")
    if command_json:
        command = json.loads(command_json)
        if not isinstance(command, list) or not all(isinstance(value, str) for value in command):
            raise RuntimeError("LFSRC_AGENT_COMMAND_JSON must be a JSON string array")
        adapter: AgentAdapter = CliAgentAdapter(command)
    else:
        adapter = PythonAgentAdapter(
            lambda _: [{"type": "error", "data": {"message": "Agent command is not configured"}}]
        )
    host = os.environ.get("LFSRC_GRPC_HOST", "0.0.0.0")
    port = int(os.environ.get("LFSRC_GRPC_PORT", "8621"))
    server, _ = create_server(
        adapter, host=host, port=port, token=os.environ.get("LFSRC_GRPC_TOKEN")
    )
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    main()
