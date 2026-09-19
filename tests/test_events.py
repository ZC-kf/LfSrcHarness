import json
from pathlib import Path

import pytest

from lfsrc_harness.events import (
    AuditEvent,
    EventLedger,
    EventType,
    IntegrityError,
    replay_events,
)
from lfsrc_harness.evidence import EvidenceStore


@pytest.mark.parametrize("event_type", list(EventType))
def test_ledger_writes_each_canonical_event_type(tmp_path: Path, event_type: EventType) -> None:
    ledger = EventLedger(tmp_path / "events.jsonl", run_id="run-1")

    event = ledger.append(event_type, {"value": 1})

    assert event.type is event_type
    assert event.sequence == 1
    assert event.timestamp.tzinfo is not None
    restored = list(replay_events(tmp_path / "events.jsonl"))
    assert restored == [event]


def test_ledger_redacts_nested_credentials(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    ledger = EventLedger(path, run_id="run-1")

    ledger.append(
        EventType.TOOL_CALL,
        {
            "authorization": "Bearer value",
            "nested": {"api_token": "value", "safe": "visible"},
        },
    )

    raw = path.read_text(encoding="utf-8")
    assert "Bearer value" not in raw
    assert '"safe":"visible"' in raw
    assert raw.count("***REDACTED***") == 2


def test_replay_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    ledger = EventLedger(path, run_id="run-1")
    ledger.append(EventType.RUN_START, {"state": "started"})
    ledger.append(EventType.RUN_END, {"state": "complete"})
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = json.loads(lines[1])
    changed["data"]["state"] = "changed"
    lines[1] = json.dumps(changed, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(IntegrityError, match="hash"):
        list(replay_events(path))


def test_evidence_store_is_content_addressed_and_deduplicated(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")

    first = store.add_bytes(b"proof", media_type="text/plain", source="tool")
    second = store.add_bytes(b"proof", media_type="text/plain", source="tool")

    assert first.sha256 == second.sha256
    assert first.path == second.path
    assert Path(first.path).read_bytes() == b"proof"
    assert len(list((tmp_path / "evidence").rglob("*.bin"))) == 1


def test_audit_event_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone"):
        AuditEvent.model_validate(
            {
                "run_id": "run-1",
                "sequence": 1,
                "type": "run_start",
                "timestamp": "2026-01-01T00:00:00",
                "data": {},
                "previous_hash": "0" * 64,
                "event_hash": "0" * 64,
            }
        )
