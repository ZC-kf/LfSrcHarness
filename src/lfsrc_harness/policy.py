"""Action classification, approvals, and emergency-stop policy."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from threading import RLock
from uuid import uuid4

from pydantic import BaseModel, Field

from .scope import ScopeConfig, ScopeViolation


class ActionTier(IntEnum):
    READ_ONLY = 10
    SCAN = 20
    VALIDATE = 30
    EXPLOIT = 40
    HIGH_RISK = 50


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    PENDING = "pending"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PrivilegeRequest(BaseModel):
    privileged_container: bool = False
    host_network: bool = False
    docker_socket: bool = False

    def requested(self) -> bool:
        return self.privileged_container or self.host_network or self.docker_socket


class ActionRequest(BaseModel):
    run_id: str = Field(min_length=1)
    target: str = Field(min_length=1)
    action: str = Field(min_length=1)
    tier: ActionTier
    privileges: PrivilegeRequest = Field(default_factory=PrivilegeRequest)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"requested_at"})
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()


class PolicyResult(BaseModel):
    decision: Decision
    reason: str
    approval_id: str | None = None
    approved_by: str | None = None


class ApprovalRecord(BaseModel):
    id: str
    request_fingerprint: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    actor: str | None = None
    decided_at: datetime | None = None


class ApprovalStore:
    """Thread-safe in-memory approval store; persistence is added by orchestration."""

    def __init__(self) -> None:
        self._records: dict[str, ApprovalRecord] = {}
        self._by_fingerprint: dict[str, str] = {}
        self._lock = RLock()

    def get_or_create(self, request_fingerprint: str) -> ApprovalRecord:
        with self._lock:
            existing_id = self._by_fingerprint.get(request_fingerprint)
            if existing_id is not None:
                return self._records[existing_id]
            record = ApprovalRecord(
                id=f"approval-{uuid4().hex}",
                request_fingerprint=request_fingerprint,
            )
            self._records[record.id] = record
            self._by_fingerprint[request_fingerprint] = record.id
            return record

    def approve(self, approval_id: str, *, actor: str) -> ApprovalRecord:
        return self._decide(approval_id, ApprovalStatus.APPROVED, actor)

    def reject(self, approval_id: str, *, actor: str) -> ApprovalRecord:
        return self._decide(approval_id, ApprovalStatus.REJECTED, actor)

    def _decide(self, approval_id: str, status: ApprovalStatus, actor: str) -> ApprovalRecord:
        with self._lock:
            record = self._records[approval_id]
            updated = record.model_copy(
                update={"status": status, "actor": actor, "decided_at": datetime.now(UTC)}
            )
            self._records[approval_id] = updated
            return updated

    def list(self) -> list[ApprovalRecord]:
        with self._lock:
            return list(self._records.values())


class EmergencyStopRegistry:
    def __init__(self) -> None:
        self._global = False
        self._runs: set[str] = set()
        self._targets: set[str] = set()
        self._lock = RLock()

    def stop_global(self) -> None:
        with self._lock:
            self._global = True

    def resume_global(self) -> None:
        with self._lock:
            self._global = False

    def stop_run(self, run_id: str) -> None:
        with self._lock:
            self._runs.add(run_id)

    def resume_run(self, run_id: str) -> None:
        with self._lock:
            self._runs.discard(run_id)

    def stop_target(self, target: str) -> None:
        with self._lock:
            self._targets.add(target.casefold())

    def resume_target(self, target: str) -> None:
        with self._lock:
            self._targets.discard(target.casefold())

    def blocking_reason(self, run_id: str, target: str) -> str | None:
        with self._lock:
            if self._global:
                return "global emergency stop is active"
            if run_id in self._runs:
                return f"run {run_id!r} is stopped"
            if target.casefold() in self._targets:
                return f"target {target!r} is stopped"
            return None


class PolicyEngine:
    def __init__(
        self,
        scope: ScopeConfig,
        *,
        approvals: ApprovalStore | None = None,
        stops: EmergencyStopRegistry | None = None,
    ) -> None:
        self.scope = scope
        self.approvals = approvals or ApprovalStore()
        self.stops = stops or EmergencyStopRegistry()

    def evaluate(self, request: ActionRequest) -> PolicyResult:
        try:
            self.scope.assert_active(request.requested_at)
            self.scope.assert_target(request.target)
        except ScopeViolation as exc:
            return PolicyResult(decision=Decision.DENY, reason=str(exc))

        stop_reason = self.stops.blocking_reason(request.run_id, request.target)
        if stop_reason is not None:
            return PolicyResult(decision=Decision.DENY, reason=stop_reason)

        if request.action.casefold() in self.scope.prohibited_actions:
            return PolicyResult(
                decision=Decision.DENY,
                reason=f"action {request.action!r} is prohibited by scope",
            )

        privilege_error = self._privilege_error(request.privileges)
        if privilege_error is not None:
            return PolicyResult(decision=Decision.DENY, reason=privilege_error)

        needs_approval = request.tier >= ActionTier.EXPLOIT or request.privileges.requested()
        if not needs_approval:
            return PolicyResult(decision=Decision.ALLOW, reason="scope and policy allow action")

        approval = self.approvals.get_or_create(request.fingerprint())
        if approval.status is ApprovalStatus.APPROVED:
            return PolicyResult(
                decision=Decision.ALLOW,
                reason="operator approval granted",
                approval_id=approval.id,
                approved_by=approval.actor,
            )
        if approval.status is ApprovalStatus.REJECTED:
            return PolicyResult(
                decision=Decision.DENY,
                reason="operator rejected action",
                approval_id=approval.id,
                approved_by=approval.actor,
            )
        return PolicyResult(
            decision=Decision.PENDING,
            reason="operator approval required",
            approval_id=approval.id,
        )

    def _privilege_error(self, request: PrivilegeRequest) -> str | None:
        allowed = self.scope.privileges
        denied = (
            (request.privileged_container and not allowed.allow_privileged_container)
            or (request.host_network and not allowed.allow_host_network)
            or (request.docker_socket and not allowed.allow_docker_socket)
        )
        return "requested privilege is not permitted by scope" if denied else None
