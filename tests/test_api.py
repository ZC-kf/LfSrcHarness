from pathlib import Path

from fastapi.testclient import TestClient

from lfsrc_harness.api import create_app
from lfsrc_harness.events import EventLedger, EventType
from lfsrc_harness.policy import ActionRequest, ActionTier, ApprovalStore
from lfsrc_harness.scope import ScopeConfig


def make_scope() -> ScopeConfig:
    return ScopeConfig.model_validate(
        {
            "name": "local",
            "targets": ["local-node"],
            "time_windows": [],
            "rate_limit": {"requests": 10, "per_seconds": 60},
            "prohibited_actions": [],
            "privileges": {},
        }
    )


def client(tmp_path: Path) -> tuple[TestClient, ApprovalStore]:
    approvals = ApprovalStore()
    app = create_app(
        scope=make_scope(),
        database=tmp_path / "state.sqlite3",
        runs_root=tmp_path / "runs",
        report_root=tmp_path / "reports",
        evidence_root=tmp_path / "evidence",
        tokens={"viewer-token": "viewer", "operator-token": "operator", "admin-token": "admin"},
        approvals=approvals,
    )
    return TestClient(app), approvals


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_authentication_and_rbac(tmp_path: Path) -> None:
    api, _ = client(tmp_path)
    payload = {"target": "local-node", "objective": "fixture", "plugin": "fixture"}

    assert api.get("/api/tasks").status_code == 401
    assert api.post("/api/tasks", json=payload, headers=headers("viewer-token")).status_code == 403
    created = api.post("/api/tasks", json=payload, headers=headers("operator-token"))

    assert created.status_code == 201
    task_id = created.json()["id"]
    listed = api.get("/api/tasks", headers=headers("viewer-token"))
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == task_id


def test_api_rejects_out_of_scope_target_and_supports_stop(tmp_path: Path) -> None:
    api, _ = client(tmp_path)
    bad = api.post(
        "/api/tasks",
        json={"target": "outside.test", "objective": "fixture", "plugin": "fixture"},
        headers=headers("operator-token"),
    )
    assert bad.status_code == 422

    created = api.post(
        "/api/tasks",
        json={"target": "local-node", "objective": "fixture", "plugin": "fixture"},
        headers=headers("operator-token"),
    ).json()
    stopped = api.post(f"/api/tasks/{created['id']}/stop", headers=headers("operator-token"))

    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"


def test_approval_requires_admin_role(tmp_path: Path) -> None:
    api, approvals = client(tmp_path)
    record = approvals.get_or_create(
        ActionRequest(
            run_id="run-1",
            target="local-node",
            action="fixture",
            tier=ActionTier.HIGH_RISK,
        ).fingerprint()
    )

    forbidden = api.post(f"/api/approvals/{record.id}/approve", headers=headers("operator-token"))
    approved = api.post(f"/api/approvals/{record.id}/approve", headers=headers("admin-token"))

    assert forbidden.status_code == 403
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_events_json_and_sse_endpoints_replay_ledger(tmp_path: Path) -> None:
    api, _ = client(tmp_path)
    path = tmp_path / "runs" / "run-1" / "events.jsonl"
    EventLedger(path, run_id="run-1").append(EventType.RUN_START, {"ok": True})

    events = api.get("/api/runs/run-1/events", headers=headers("viewer-token"))
    stream = api.get("/api/runs/run-1/events/stream", headers=headers("viewer-token"))

    assert events.status_code == 200
    assert events.json()[0]["type"] == "run_start"
    assert stream.status_code == 200
    assert "event: run_start" in stream.text
    assert "data:" in stream.text


def test_all_required_resource_routes_exist(tmp_path: Path) -> None:
    api, _ = client(tmp_path)
    paths = {route.path for route in api.app.routes}

    for path in [
        "/api/tasks",
        "/api/targets",
        "/api/runs/{run_id}",
        "/api/runs/{run_id}/events",
        "/api/evidence/{sha256}",
        "/api/reports/{run_id}",
        "/api/approvals",
        "/api/emergency-stop",
    ]:
        assert path in paths
