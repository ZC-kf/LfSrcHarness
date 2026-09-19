from __future__ import annotations

import json
import logging

from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from lfsrc_harness.events import EventLedger, EventType
from lfsrc_harness.observability import JsonFormatter, build_tracer_provider


def test_json_formatter_emits_structured_record_and_redacts_secrets() -> None:
    record = logging.LogRecord(
        name="lfsrc.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="task started",
        args=(),
        exc_info=None,
    )
    record.event_data = {"task_id": "task-1", "api_token": "do-not-log"}

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "task started"
    assert payload["event_data"]["task_id"] == "task-1"
    assert payload["event_data"]["api_token"] == "***REDACTED***"


def test_event_append_emits_opentelemetry_span(tmp_path) -> None:
    exporter = InMemorySpanExporter()
    provider = build_tracer_provider("lfsrc-test")
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    ledger = EventLedger(tmp_path / "events.jsonl", run_id="run-1", tracer=tracer)

    ledger.append(EventType.RUN_START, {"source": "test"})

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "lfsrc.event.append"
    assert spans[0].attributes["event.type"] == "run_start"
    assert spans[0].attributes["run.id"] == "run-1"
