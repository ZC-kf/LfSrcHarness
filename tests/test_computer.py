from pathlib import Path

import pytest

from lfsrc_harness.computer import (
    ComputerAction,
    ComputerController,
    ControlDenied,
    ControlKind,
    ControlResult,
    ControlSurface,
)
from lfsrc_harness.events import EventType, replay_events
from lfsrc_harness.policy import ApprovalStore, EmergencyStopRegistry, PolicyEngine
from lfsrc_harness.scope import ScopeConfig


class FakeBackend:
    def __init__(self) -> None:
        self.actions: list[ComputerAction] = []

    def execute(self, action: ComputerAction) -> ControlResult:
        self.actions.append(action)
        return ControlResult(success=True, output={"kind": action.kind.value})


def make_policy() -> tuple[PolicyEngine, ApprovalStore, EmergencyStopRegistry]:
    scope = ScopeConfig.model_validate(
        {
            "name": "local-control",
            "targets": ["local-node"],
            "time_windows": [],
            "rate_limit": {"requests": 20, "per_seconds": 60},
            "prohibited_actions": [],
            "privileges": {},
        }
    )
    approvals = ApprovalStore()
    stops = EmergencyStopRegistry()
    return PolicyEngine(scope, approvals=approvals, stops=stops), approvals, stops


def test_controller_is_disabled_by_default() -> None:
    policy, _, _ = make_policy()
    controller = ComputerController(policy, backends={ControlSurface.SCREEN: FakeBackend()})

    with pytest.raises(ControlDenied, match="disabled"):
        controller.execute(
            "run-1", ComputerAction(surface=ControlSurface.SCREEN, kind=ControlKind.SCREENSHOT)
        )


def test_screen_observation_executes_and_is_audited(tmp_path: Path) -> None:
    policy, _, _ = make_policy()
    backend = FakeBackend()
    controller = ComputerController(
        policy,
        backends={ControlSurface.SCREEN: backend},
        enabled=True,
        event_path=tmp_path / "events.jsonl",
    )

    result = controller.execute(
        "run-1", ComputerAction(surface=ControlSurface.SCREEN, kind=ControlKind.SCREENSHOT)
    )

    assert result.success
    assert len(backend.actions) == 1
    events = list(replay_events(tmp_path / "events.jsonl"))
    assert [event.type for event in events] == [EventType.TOOL_CALL, EventType.TOOL_RESULT]


def test_desktop_input_requires_explicit_approval() -> None:
    policy, approvals, _ = make_policy()
    backend = FakeBackend()
    controller = ComputerController(
        policy, backends={ControlSurface.DESKTOP: backend}, enabled=True
    )
    action = ComputerAction(
        surface=ControlSurface.DESKTOP,
        kind=ControlKind.TYPE_TEXT,
        parameters={"text": "fixture"},
    )

    with pytest.raises(ControlDenied, match="approval") as pending:
        controller.execute("run-1", action)
    approval_id = str(pending.value.approval_id)
    approvals.approve(approval_id, actor="operator")

    assert controller.execute("run-1", action).success
    assert len(backend.actions) == 1


def test_emergency_stop_blocks_browser_control() -> None:
    policy, _, stops = make_policy()
    controller = ComputerController(
        policy, backends={ControlSurface.BROWSER: FakeBackend()}, enabled=True
    )
    stops.stop_global()

    with pytest.raises(ControlDenied, match="emergency stop"):
        controller.execute(
            "run-1",
            ComputerAction(
                surface=ControlSurface.BROWSER,
                kind=ControlKind.BROWSER_SNAPSHOT,
            ),
        )
