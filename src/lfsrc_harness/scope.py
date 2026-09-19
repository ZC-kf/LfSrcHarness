"""Authorized-target scope models and validation."""

from __future__ import annotations

from datetime import UTC, datetime
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, Field, PositiveInt, model_validator


class ScopeViolation(RuntimeError):
    """Raised when an operation is outside the active authorization scope."""


class TimeWindow(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_window(self) -> TimeWindow:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("time window values must include a timezone")
        if self.end <= self.start:
            raise ValueError("time window end must follow start")
        return self

    def contains(self, moment: datetime) -> bool:
        normalized = moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
        return self.start <= normalized <= self.end


class RateLimit(BaseModel):
    requests: PositiveInt = 10
    per_seconds: PositiveInt = 60


class PrivilegeScope(BaseModel):
    allow_privileged_container: bool = False
    allow_host_network: bool = False
    allow_docker_socket: bool = False


class ScopeConfig(BaseModel):
    name: str = Field(min_length=1)
    tenant_id: str = Field(default="default", min_length=1)
    targets: list[str] = Field(min_length=1)
    time_windows: list[TimeWindow] = Field(default_factory=list)
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    prohibited_actions: set[str] = Field(default_factory=set)
    privileges: PrivilegeScope = Field(default_factory=PrivilegeScope)

    @model_validator(mode="after")
    def normalize_values(self) -> ScopeConfig:
        self.targets = [target.strip() for target in self.targets if target.strip()]
        if not self.targets:
            raise ValueError("scope requires at least one target")
        self.prohibited_actions = {
            action.strip().casefold() for action in self.prohibited_actions if action.strip()
        }
        return self

    def is_target_allowed(self, candidate: str) -> bool:
        host = _extract_host(candidate)
        return any(_target_matches(rule, host) for rule in self.targets)

    def assert_target(self, candidate: str) -> None:
        if not self.is_target_allowed(candidate):
            raise ScopeViolation(f"target {candidate!r} is outside the authorized scope")

    def is_active(self, moment: datetime | None = None) -> bool:
        if not self.time_windows:
            return True
        current = moment or datetime.now(UTC)
        return any(window.contains(current) for window in self.time_windows)

    def assert_active(self, moment: datetime | None = None) -> None:
        if not self.is_active(moment):
            raise ScopeViolation("operation is outside every authorized time window")


def load_scope(path: str | Path) -> ScopeConfig:
    scope_path = Path(path)
    with scope_path.open("r", encoding="utf-8") as stream:
        data: Any = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError("scope YAML must contain a mapping")
    return ScopeConfig.model_validate(data)


def _extract_host(candidate: str) -> str:
    value = candidate.strip()
    parsed = urlsplit(value if "://" in value else f"//{value}")
    host = parsed.hostname
    if host is None:
        raise ValueError(f"unable to extract host from target {candidate!r}")
    return host.rstrip(".").casefold()


def _target_matches(rule: str, host: str) -> bool:
    normalized = rule.strip().rstrip(".").casefold()
    try:
        network = ip_network(normalized, strict=False)
        return ip_address(host) in network
    except ValueError:
        pass

    if normalized.startswith("*."):
        suffix = normalized[1:]
        return host.endswith(suffix) and host != normalized[2:]
    return host == _extract_host(normalized)
