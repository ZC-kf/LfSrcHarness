import grpc
import pytest

from lfsrc_harness.agent import AgentRequest, GrpcAgentAdapter, PythonAgentAdapter
from lfsrc_harness.grpc_server import create_server
from lfsrc_harness.proto import lfsrc_harness_pb2


def test_grpc_server_exposes_agent_json_contract() -> None:
    adapter = PythonAgentAdapter(
        lambda request: [{"type": "done", "data": {"objective": request.objective}}]
    )
    server, port = create_server(adapter, host="127.0.0.1", port=0)
    server.start()
    try:
        channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        client = GrpcAgentAdapter(channel)

        events = list(
            client.run(AgentRequest(run_id="run-1", objective="fixture", scope_path="scope.yaml"))
        )

        assert events[0].type == "done"
        assert events[0].data["objective"] == "fixture"
    finally:
        server.stop(grace=0).wait()


def test_grpc_wire_matches_published_protobuf_contract() -> None:
    adapter = PythonAgentAdapter(lambda _: [{"type": "done", "data": {"ok": True}}])
    server, port = create_server(adapter, host="127.0.0.1", port=0)
    server.start()
    try:
        channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        invoke = channel.unary_unary(
            "/lfsrc.Agent/Run",
            request_serializer=lfsrc_harness_pb2.JsonEnvelope.SerializeToString,
            response_deserializer=lfsrc_harness_pb2.JsonEnvelope.FromString,
        )
        request = AgentRequest(run_id="run-1", objective="fixture", scope_path="scope.yaml")
        response = invoke(lfsrc_harness_pb2.JsonEnvelope(json=request.model_dump_json().encode()))

        assert b'"type":"done"' in response.json
    finally:
        server.stop(grace=0).wait()


def test_grpc_token_blocks_unauthenticated_invocation() -> None:
    adapter = PythonAgentAdapter(lambda _: [{"type": "done", "data": {}}])
    server, port = create_server(adapter, host="127.0.0.1", port=0, token="local-test-token")
    server.start()
    try:
        channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        request = AgentRequest(run_id="run-1", objective="fixture", scope_path="scope.yaml")
        with pytest.raises(grpc.RpcError) as denied:
            list(GrpcAgentAdapter(channel).run(request))
        assert denied.value.code() is grpc.StatusCode.UNAUTHENTICATED
        assert (
            next(iter(GrpcAgentAdapter(channel, token="local-test-token").run(request))).type
            == "done"
        )
    finally:
        server.stop(grace=0).wait()


def test_grpc_nonlocal_bind_requires_token() -> None:
    adapter = PythonAgentAdapter(lambda _: [])
    with pytest.raises(ValueError, match="token"):
        create_server(adapter, host="0.0.0.0", port=0)
