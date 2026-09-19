"""Structured logging and OpenTelemetry helpers."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from lfsrc_harness.events import redact


class JsonFormatter(logging.Formatter):
    """Emit one machine-readable, secret-redacted JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event_data = getattr(record, "event_data", None)
        if event_data is not None:
            payload["event_data"] = redact(event_data)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the process root logger with a JSON stream handler."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def build_tracer_provider(service_name: str) -> TracerProvider:
    """Create an SDK tracer provider to which callers can attach exporters."""

    resource = Resource.create({"service.name": service_name})
    return TracerProvider(resource=resource)
