import json
import sys

import httpx

from lfsrc_harness.agent import (
    AgentRequest,
    CliAgentAdapter,
    GrpcAgentAdapter,
    HttpAgentAdapter,
    PythonAgentAdapter,
)
from lfsrc_harness.proto import lfsrc_harness_pb2


def request() -> AgentRequest:
    return AgentRequest(run_id="run-1", objective="inspect fixture", scope_path="scope.yaml")


def test_python_agent_adapter_normalizes_events() -> None:
    adapter = PythonAgentAdapter(lambda item: [{"type": "message", "objective": item.objective}])

    events = list(adapter.run(request()))

    assert events[0].type == "message"
    assert events[0].data["objective"] == "inspect fixture"


def test_cli_agent_adapter_reads_jsonl_from_stdout() -> None:
    code = "import json; print(json.dumps({'type':'done','data':{'ok':True}}))"
    adapter = CliAgentAdapter([sys.executable, "-c", code])

    events = list(adapter.run(request()))

    assert events[0].type == "done"
    assert events[0].data == {"ok": True}


def test_http_agent_adapter_accepts_event_array() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"events": [{"type": "done", "data": {}}]})
        )
    )
    adapter = HttpAgentAdapter("https://agent.invalid/run", client=client)

    assert next(iter(adapter.run(request()))).type == "done"


def test_grpc_agent_adapter_uses_json_wire_contract() -> None:
    class Channel:
        def unary_unary(self, _: str, **__: object):
            def invoke(payload: lfsrc_harness_pb2.JsonEnvelope, **kwargs: object):
                assert kwargs["metadata"] == (("authorization", "Bearer fixture-token"),)
                return lfsrc_harness_pb2.JsonEnvelope(
                    json=json.dumps(
                        {
                            "events": [
                                {
                                    "type": "done",
                                    "data": {"request": json.loads(payload.json)["run_id"]},
                                }
                            ]
                        }
                    ).encode()
                )

            return invoke

    adapter = GrpcAgentAdapter(Channel(), token="fixture-token")

    assert next(iter(adapter.run(request()))).data["request"] == "run-1"
