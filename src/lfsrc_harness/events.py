"""Tamper-evident JSONL event ledger and replay."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from threading import RLock
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Tracer
from pydantic import BaseModel, Field, field_validator


class EventType(StrEnum):
    RUN_START = "run_start"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_EDIT = "file_edit"
    FINDING = "finding"
    RUN_END = "run_end"


class IntegrityError(RuntimeError):
    pass


class AuditEvent(BaseModel):
    run_id: str = Field(min_length=1)
    tenant_id: str = Field(default="default", min_length=1)
    sequence: int = Field(ge=1)
    type: EventType
    timestamp: datetime
    data: dict[str, Any]
    previous_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value


class EventLedger:
    def __init__(
        self,
        path: str | Path,
        *,
        run_id: str,
        tenant_id: str = "default",
        tracer: Tracer | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.tenant_id = tenant_id
        self.tracer = tracer or trace.get_tracer("lfsrc_harness.events")
        self._lock = RLock()
        existing = list(replay_events(self.path)) if self.path.exists() else []
        self._sequence = existing[-1].sequence if existing else 0
        self._previous_hash = existing[-1].event_hash if existing else "0" * 64

    def append(self, event_type: EventType, data: Mapping[str, Any]) -> AuditEvent:
        with self.tracer.start_as_current_span("lfsrc.event.append") as span:
            span.set_attribute("run.id", self.run_id)
            span.set_attribute("tenant.id", self.tenant_id)
            span.set_attribute("event.type", event_type.value)
            with self._lock:
                payload = {
                    "run_id": self.run_id,
                    "tenant_id": self.tenant_id,
                    "sequence": self._sequence + 1,
                    "type": event_type,
                    "timestamp": datetime.now(UTC),
                    "data": redact(dict(data)),
                    "previous_hash": self._previous_hash,
                }
                event_hash = _hash_payload(payload)
                event = AuditEvent.model_validate({**payload, "event_hash": event_hash})
                serialized = event.model_dump_json() + "\n"
                with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(serialized)
                    stream.flush()
                    os.fsync(stream.fileno())
                self._sequence = event.sequence
                self._previous_hash = event.event_hash
                span.set_attribute("event.sequence", event.sequence)
                span.set_attribute("event.hash", event.event_hash)
                return event


def replay_events(path: str | Path) -> Iterator[AuditEvent]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return
    expected_sequence = 1
    previous_hash = "0" * 64
    with ledger_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                event = AuditEvent.model_validate_json(line)
            except ValueError as exc:
                raise IntegrityError(f"invalid event at line {line_number}: {exc}") from exc
            if event.sequence != expected_sequence:
                raise IntegrityError(f"event sequence mismatch at line {line_number}")
            if event.previous_hash != previous_hash:
                raise IntegrityError(f"previous hash mismatch at line {line_number}")
            calculated = _hash_payload(event.model_dump(exclude={"event_hash"}))
            if calculated != event.event_hash:
                raise IntegrityError(f"event hash mismatch at line {line_number}")
            yield event
            expected_sequence += 1
            previous_hash = event.event_hash


def _hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _json_ready(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_ready(item) for item in value]
    return value


def redact(value: Any, *, key: str = "") -> Any:
    sensitive = ("password", "secret", "token", "authorization", "cookie", "private_key")
    if any(marker in key.casefold() for marker in sensitive):
        return "***REDACTED***"
    if isinstance(value, Mapping):
        return {str(item_key): redact(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    return value
