import json
import sys
from pathlib import Path

import httpx
import pytest

from lfsrc_harness.plugins import (
    GrpcPlugin,
    HttpPlugin,
    PluginManifest,
    PluginRegistry,
    PluginRequest,
    PluginTransport,
    SubprocessPlugin,
)


def manifest(transport: PluginTransport) -> PluginManifest:
    return PluginManifest(
        name=f"fixture-{transport.value}",
        version="1.0.0",
        capabilities={"fixture"},
        target_types={"local"},
        transport=transport,
    )


def test_registry_registers_and_rejects_duplicate_plugins() -> None:
    registry = PluginRegistry()
    plugin = SubprocessPlugin(
        manifest(PluginTransport.SUBPROCESS),
        command_builder=lambda _: [sys.executable, "-c", "print('ok')"],
    )

    registry.register(plugin)

    assert registry.get(plugin.manifest.name) is plugin
    assert registry.list()[0].capabilities == {"fixture"}
    with pytest.raises(ValueError, match="already registered"):
        registry.register(plugin)


def test_subprocess_plugin_runs_without_shell_and_parses_json() -> None:
    plugin = SubprocessPlugin(
        manifest(PluginTransport.SUBPROCESS),
        command_builder=lambda request: [
            sys.executable,
            "-c",
            f"import json; print(json.dumps({{'target': {request.target!r}}}))",
        ],
        parser=json.loads,
    )

    result = plugin.run(PluginRequest(run_id="run-1", target="127.0.0.1"))

    assert result.success
    assert result.parsed == {"target": "127.0.0.1"}


def test_http_plugin_uses_injected_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(200, json={"received": body["target"]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    plugin = HttpPlugin(
        manifest(PluginTransport.HTTP), endpoint="https://plugin.invalid/run", client=client
    )

    result = plugin.run(PluginRequest(run_id="run-1", target="local.test"))

    assert result.success
    assert result.parsed == {"received": "local.test"}


def test_grpc_plugin_uses_json_wire_contract() -> None:
    requests: list[dict[str, object]] = []

    class FakeChannel:
        def unary_unary(self, method: str):
            assert method == "/lfsrc.Plugin/Run"

            def invoke(payload: bytes, timeout: float) -> bytes:
                assert timeout == 30
                requests.append(json.loads(payload))
                return json.dumps({"ok": True}).encode()

            return invoke

    plugin = GrpcPlugin(
        manifest(PluginTransport.GRPC), channel=FakeChannel(), method="/lfsrc.Plugin/Run"
    )

    result = plugin.run(PluginRequest(run_id="run-1", target="local.test"))

    assert result.success
    assert result.parsed == {"ok": True}
    assert requests[0]["target"] == "local.test"


def test_plugin_examples_and_template_are_shipped() -> None:
    root = Path(__file__).parents[1]

    assert (root / "plugins" / "examples" / "builtin-tools.yaml").is_file()
    assert (root / "plugins" / "template" / "plugin.py").is_file()
