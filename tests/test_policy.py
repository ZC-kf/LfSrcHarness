from datetime import UTC, datetime

from lfsrc_harness.policy import (
    ActionRequest,
    ActionTier,
    ApprovalStore,
    Decision,
    EmergencyStopRegistry,
    PolicyEngine,
    PrivilegeRequest,
)
from lfsrc_harness.scope import ScopeConfig


def make_scope(*, allow_privileged: bool = False) -> ScopeConfig:
    return ScopeConfig.model_validate(
        {
            "name": "test",
            "targets": ["127.0.0.1", "*.lab.test"],
            "time_windows": [],
            "rate_limit": {"requests": 5, "per_seconds": 10},
            "prohibited_actions": ["persistence"],
            "privileges": {
                "allow_privileged_container": allow_privileged,
                "allow_host_network": False,
                "allow_docker_socket": False,
            },
        }
    )


def request(
    *,
    tier: ActionTier = ActionTier.SCAN,
    action: str = "inventory",
    target: str = "127.0.0.1",
    run_id: str = "run-1",
    privileges: PrivilegeRequest | None = None,
) -> ActionRequest:
    return ActionRequest(
        run_id=run_id,
        target=target,
        action=action,
        tier=tier,
        privileges=privileges or PrivilegeRequest(),
        requested_at=datetime.now(UTC),
    )


def test_low_risk_scoped_action_is_allowed() -> None:
    engine = PolicyEngine(make_scope())

    result = engine.evaluate(request())

    assert result.decision is Decision.ALLOW


def test_exploit_and_high_risk_actions_require_approval() -> None:
    approvals = ApprovalStore()
    engine = PolicyEngine(make_scope(), approvals=approvals)
    item = request(tier=ActionTier.EXPLOIT, action="controlled_validation")

    pending = engine.evaluate(item)
    assert pending.decision is Decision.PENDING
    assert pending.approval_id

    approvals.approve(pending.approval_id, actor="operator")
    allowed = engine.evaluate(item)
    assert allowed.decision is Decision.ALLOW
    assert allowed.approved_by == "operator"


def test_prohibited_action_is_denied_even_if_approved() -> None:
    approvals = ApprovalStore()
    engine = PolicyEngine(make_scope(), approvals=approvals)
    item = request(tier=ActionTier.HIGH_RISK, action="persistence")

    first = engine.evaluate(item)
    assert first.decision is Decision.DENY
    assert "prohibited" in first.reason


def test_privilege_must_be_in_scope_then_approved() -> None:
    privileged = PrivilegeRequest(privileged_container=True)

    denied = PolicyEngine(make_scope()).evaluate(request(privileges=privileged))
    assert denied.decision is Decision.DENY
    assert "not permitted by scope" in denied.reason

    approvals = ApprovalStore()
    engine = PolicyEngine(make_scope(allow_privileged=True), approvals=approvals)
    item = request(privileges=privileged)
    pending = engine.evaluate(item)
    assert pending.decision is Decision.PENDING
    approvals.approve(pending.approval_id or "", actor="admin")
    assert engine.evaluate(item).decision is Decision.ALLOW


def test_global_run_and_target_stops_override_allow_rules() -> None:
    stops = EmergencyStopRegistry()
    engine = PolicyEngine(make_scope(), stops=stops)

    stops.stop_target("127.0.0.1")
    assert engine.evaluate(request()).decision is Decision.DENY
    stops.resume_target("127.0.0.1")

    stops.stop_run("run-1")
    assert engine.evaluate(request()).decision is Decision.DENY
    stops.resume_run("run-1")

    stops.stop_global()
    assert engine.evaluate(request(run_id="run-2")).decision is Decision.DENY
    stops.resume_global()
    assert engine.evaluate(request(run_id="run-2")).decision is Decision.ALLOW


def test_out_of_scope_target_is_denied() -> None:
    result = PolicyEngine(make_scope()).evaluate(request(target="outside.test"))

    assert result.decision is Decision.DENY
    assert "outside" in result.reason
