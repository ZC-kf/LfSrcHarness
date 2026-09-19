"""Minimal LfSrcHarness Python entry-point plugin."""

from lfsrc_harness.plugins import (
    PluginManifest,
    PluginRequest,
    PluginResult,
    PluginTransport,
    PythonPlugin,
)


def _run(request: PluginRequest) -> PluginResult:
    return PluginResult(success=True, parsed={"target": request.target})


plugin = PythonPlugin(
    PluginManifest(
        name="example-plugin",
        version="1.0.0",
        capabilities={"example"},
        target_types={"local"},
        transport=PluginTransport.PYTHON,
    ),
    _run,
)
