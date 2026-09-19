from pathlib import Path

from lfsrc_harness.plugins import (
    PluginManifest,
    PluginRegistry,
    PluginResult,
    PluginTransport,
    PythonPlugin,
)
from lfsrc_harness.policy import ApprovalStore, PolicyEngine
from lfsrc_harness.scope import ScopeConfig
from lfsrc_harness.workflow import WorkflowEngine, WorkflowStage, WorkflowStatus


def scope() -> ScopeConfig:
    return ScopeConfig.model_validate(
        {
            "name": "fixture",
            "targets": ["local-node", "*.lab.test"],
            "time_windows": [],
            "rate_limit": {"requests": 10, "per_seconds": 60},
            "prohibited_actions": [],
            "privileges": {},
        }
    )


def add_plugin(registry: PluginRegistry, name: str, capability: str, handler) -> None:
    registry.register(
        PythonPlugin(
            PluginManifest(
                name=name,
                version="1",
                capabilities={capability},
                target_types={"local"},
                transport=PluginTransport.PYTHON,
            ),
            handler,
        )
    )


def registry() -> PluginRegistry:
    plugins = PluginRegistry()
    add_plugin(
        plugins,
        "discover",
        "target_discovery",
        lambda _: PluginResult(success=True, parsed={"targets": ["local-node"]}),
    )
    add_plugin(
        plugins,
        "assess",
        "assessment",
        lambda _: PluginResult(
            success=True,
            output="fixture observation",
            parsed={
                "findings": [
                    {
                        "id": "F-001",
                        "title": "Fixture",
                        "severity": "low",
                        "description": "Local fixture",
                        "remediation": "Update fixture",
                    }
                ]
            },
        ),
    )
    add_plugin(
        plugins,
        "validate",
        "controlled_validation",
        lambda _: PluginResult(success=True, output="validated"),
    )
    add_plugin(plugins, "cleanup", "cleanup", lambda _: PluginResult(success=True))
    return plugins


def test_workflow_pauses_for_approval_then_resumes_and_reports(tmp_path: Path) -> None:
    approvals = ApprovalStore()
    engine = WorkflowEngine(
        scope(),
        registry(),
        PolicyEngine(scope(), approvals=approvals),
        run_root=tmp_path / "runs",
    )

    pending = engine.run("run-1")

    assert pending.status is WorkflowStatus.PENDING_APPROVAL
    assert pending.stage is WorkflowStage.VALIDATE
    approval = approvals.list()[0]
    approvals.approve(approval.id, actor="operator")

    completed = engine.run("run-1")

    assert completed.status is WorkflowStatus.SUCCEEDED
    assert completed.stage is WorkflowStage.COMPLETE
    assert (tmp_path / "runs" / "run-1" / "reports" / "run-1.pdf").is_file()
    assert (tmp_path / "runs" / "run-1" / "events.jsonl").is_file()


def test_discovery_cannot_expand_beyond_scope(tmp_path: Path) -> None:
    plugins = registry()
    plugins = PluginRegistry()
    add_plugin(
        plugins,
        "discover",
        "target_discovery",
        lambda _: PluginResult(success=True, parsed={"targets": ["outside.test"]}),
    )
    engine = WorkflowEngine(scope(), plugins, PolicyEngine(scope()), run_root=tmp_path / "runs")

    result = engine.run("run-2")

    assert result.status is WorkflowStatus.FAILED
    assert "outside" in (result.error or "")


def test_workflow_self_heals_by_trying_next_capability_plugin(tmp_path: Path) -> None:
    plugins = PluginRegistry()
    add_plugin(
        plugins, "assess-a", "assessment", lambda _: PluginResult(success=False, output="failed")
    )
    add_plugin(
        plugins,
        "assess-b",
        "assessment",
        lambda _: PluginResult(success=True, parsed={"findings": []}),
    )
    engine = WorkflowEngine(scope(), plugins, PolicyEngine(scope()), run_root=tmp_path / "runs")

    result = engine.run("run-3", skip_validation=True)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert result.selected_tools["assessment"] == "assess-b"
