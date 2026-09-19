"""Checkpointed end-to-end authorized assessment workflow."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .events import EventLedger, EventType
from .evidence import EvidenceStore
from .plugins import PluginRegistry, PluginRequest, PluginResult
from .policy import ActionRequest, ActionTier, Decision, PolicyEngine
from .reporting import Finding, ReportData, ReportRenderer
from .scope import ScopeConfig, ScopeViolation


class WorkflowStage(StrEnum):
    DISCOVER = "discover"
    PLAN = "plan"
    ASSESS = "assess"
    VALIDATE = "validate"
    EVIDENCE = "evidence"
    REPORT = "report"
    CLEANUP = "cleanup"
    COMPLETE = "complete"


class WorkflowStatus(StrEnum):
    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    STOPPED = "stopped"


class WorkflowState(BaseModel):
    run_id: str
    status: WorkflowStatus = WorkflowStatus.RUNNING
    stage: WorkflowStage = WorkflowStage.DISCOVER
    targets: list[str] = Field(default_factory=list)
    selected_tools: dict[str, str] = Field(default_factory=dict)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    approval_id: str | None = None
    error: str | None = None
    skip_validation: bool = False


class WorkflowEngine:
    def __init__(
        self,
        scope: ScopeConfig,
        plugins: PluginRegistry,
        policy: PolicyEngine,
        *,
        run_root: str | Path,
    ) -> None:
        self.scope = scope
        self.plugins = plugins
        self.policy = policy
        self.run_root = Path(run_root)

    def run(self, run_id: str, *, skip_validation: bool = False) -> WorkflowState:
        directory = self.run_root / run_id
        directory.mkdir(parents=True, exist_ok=True)
        state_path = directory / "workflow-state.json"
        is_new = not state_path.exists()
        state = (
            WorkflowState(run_id=run_id, skip_validation=skip_validation)
            if is_new
            else WorkflowState.model_validate_json(state_path.read_text(encoding="utf-8"))
        )
        if state.status is WorkflowStatus.PENDING_APPROVAL:
            state.status = WorkflowStatus.RUNNING
        if state.status in {
            WorkflowStatus.SUCCEEDED,
            WorkflowStatus.FAILED,
            WorkflowStatus.STOPPED,
        }:
            return state
        ledger = EventLedger(
            directory / "events.jsonl", run_id=run_id, tenant_id=self.scope.tenant_id
        )
        if is_new:
            ledger.append(EventType.RUN_START, {"workflow": "authorized-assessment"})

        try:
            while state.stage is not WorkflowStage.COMPLETE:
                self.scope.assert_active()
                if state.stage is WorkflowStage.DISCOVER:
                    self._discover(state, ledger)
                    state.stage = WorkflowStage.PLAN
                elif state.stage is WorkflowStage.PLAN:
                    self._plan(state)
                    state.stage = WorkflowStage.ASSESS
                elif state.stage is WorkflowStage.ASSESS:
                    result, plugin_name = self._run_capability(
                        state, ledger, "assessment", ActionTier.SCAN, required=True
                    )
                    state.selected_tools["assessment"] = plugin_name
                    parsed = result.parsed if isinstance(result.parsed, dict) else {}
                    findings = parsed.get("findings", [])
                    if isinstance(findings, list):
                        state.findings.extend(item for item in findings if isinstance(item, dict))
                        for finding in findings:
                            if isinstance(finding, dict):
                                ledger.append(EventType.FINDING, finding)
                    state.stage = (
                        WorkflowStage.EVIDENCE if state.skip_validation else WorkflowStage.VALIDATE
                    )
                elif state.stage is WorkflowStage.VALIDATE:
                    candidates = self._candidates("controlled_validation")
                    if candidates:
                        request = ActionRequest(
                            run_id=state.run_id,
                            target=state.targets[0],
                            action=candidates[0],
                            tier=ActionTier.EXPLOIT,
                        )
                        decision = self.policy.evaluate(request)
                        if decision.decision is Decision.PENDING:
                            state.status = WorkflowStatus.PENDING_APPROVAL
                            state.approval_id = decision.approval_id
                            self._save(state_path, state)
                            return state
                        if decision.decision is Decision.DENY:
                            raise RuntimeError(decision.reason)
                        result, plugin_name = self._execute_candidates(
                            state, ledger, "controlled_validation", candidates
                        )
                        if not result.success:
                            raise RuntimeError(result.output or "validation failed")
                        state.selected_tools["controlled_validation"] = plugin_name
                    state.stage = WorkflowStage.EVIDENCE
                elif state.stage is WorkflowStage.EVIDENCE:
                    store = EvidenceStore(directory / "evidence")
                    payload = json.dumps(
                        state.findings, ensure_ascii=False, sort_keys=True
                    ).encode()
                    reference = store.add_bytes(
                        payload, media_type="application/json", source="workflow-findings"
                    )
                    state.evidence = [reference.sha256]
                    state.stage = WorkflowStage.REPORT
                elif state.stage is WorkflowStage.REPORT:
                    report_findings = [
                        self._finding(item, state.evidence) for item in state.findings
                    ]
                    ReportRenderer().render_all(
                        ReportData(
                            run_id=state.run_id,
                            title="Authorized assessment report",
                            summary=f"Completed workflow with {len(report_findings)} finding(s).",
                            scope=state.targets,
                            methodology=[
                                "scope validation",
                                "plugin selection",
                                "controlled assessment",
                                "evidence hashing",
                            ],
                            findings=report_findings,
                            appendix={"selected_tools": state.selected_tools},
                        ),
                        directory / "reports",
                    )
                    state.stage = WorkflowStage.CLEANUP
                elif state.stage is WorkflowStage.CLEANUP:
                    if self._candidates("cleanup"):
                        self._run_capability(
                            state, ledger, "cleanup", ActionTier.VALIDATE, required=False
                        )
                    state.stage = WorkflowStage.COMPLETE
                self._save(state_path, state)

            state.status = WorkflowStatus.SUCCEEDED
            self._save(state_path, state)
            ledger.append(EventType.RUN_END, {"status": state.status.value})
            return state
        except (ScopeViolation, RuntimeError, ValueError, KeyError) as exc:
            state.status = WorkflowStatus.FAILED
            state.error = str(exc)
            self._save(state_path, state)
            ledger.append(EventType.RUN_END, {"status": state.status.value, "error": str(exc)})
            return state

    def _discover(self, state: WorkflowState, ledger: EventLedger) -> None:
        candidates = self._candidates("target_discovery")
        if not candidates:
            state.targets = [self.scope.targets[0]]
            return
        result, plugin_name = self._execute_candidates(
            state, ledger, "target_discovery", candidates, target=self.scope.targets[0]
        )
        if not result.success:
            raise RuntimeError(result.output or "target discovery failed")
        parsed = result.parsed if isinstance(result.parsed, dict) else {}
        targets = parsed.get("targets", [])
        if not isinstance(targets, list) or not targets:
            targets = [self.scope.targets[0]]
        for target in targets:
            self.scope.assert_target(str(target))
        state.targets = [str(target) for target in targets]
        state.selected_tools["target_discovery"] = plugin_name

    def _plan(self, state: WorkflowState) -> None:
        if not state.targets:
            raise ValueError("workflow has no authorized target")
        for target in state.targets:
            self.scope.assert_target(target)
        if not self._candidates("assessment"):
            raise RuntimeError("no assessment plugin is registered")

    def _run_capability(
        self,
        state: WorkflowState,
        ledger: EventLedger,
        capability: str,
        tier: ActionTier,
        *,
        required: bool,
    ) -> tuple[PluginResult, str]:
        candidates = self._candidates(capability)
        if not candidates:
            if required:
                raise RuntimeError(f"no plugin provides capability {capability!r}")
            return PluginResult(success=True), ""
        decision = self.policy.evaluate(
            ActionRequest(
                run_id=state.run_id,
                target=state.targets[0],
                action=candidates[0],
                tier=tier,
            )
        )
        if decision.decision is not Decision.ALLOW:
            raise RuntimeError(decision.reason)
        result, plugin_name = self._execute_candidates(state, ledger, capability, candidates)
        if required and not result.success:
            raise RuntimeError(result.output or f"all {capability} plugins failed")
        return result, plugin_name

    def _execute_candidates(
        self,
        state: WorkflowState,
        ledger: EventLedger,
        capability: str,
        candidates: list[str],
        *,
        target: str | None = None,
    ) -> tuple[PluginResult, str]:
        last = PluginResult(success=False, output="no candidate executed")
        selected = candidates[-1]
        for name in candidates:
            selected = name
            ledger.append(EventType.TOOL_CALL, {"plugin": name, "capability": capability})
            last = self.plugins.get(name).run(
                PluginRequest(run_id=state.run_id, target=target or state.targets[0])
            )
            ledger.append(
                EventType.TOOL_RESULT,
                {"plugin": name, "capability": capability, "success": last.success},
            )
            if last.success:
                return last, name
        return last, selected

    def _candidates(self, capability: str) -> list[str]:
        return [
            manifest.name for manifest in self.plugins.list() if capability in manifest.capabilities
        ]

    @staticmethod
    def _finding(data: dict[str, Any], evidence: list[str]) -> Finding:
        return Finding.model_validate(
            {
                "id": data.get("id", "F-UNNUMBERED"),
                "title": data.get("title", "Observation"),
                "severity": data.get("severity", "info"),
                "description": data.get("description", ""),
                "evidence": data.get("evidence", evidence),
                "reproduction": data.get("reproduction", []),
                "remediation": data.get("remediation", "Review the documented configuration."),
                "target": data.get("target"),
            }
        )

    @staticmethod
    def _save(path: Path, state: WorkflowState) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)
