"""Policy-gated screen, desktop, and browser control contracts."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from .events import EventLedger, EventType
from .policy import ActionRequest, ActionTier, Decision, PolicyEngine


class ControlSurface(StrEnum):
    SCREEN = "screen"
    DESKTOP = "desktop"
    BROWSER = "browser"


class ControlKind(StrEnum):
    SCREENSHOT = "screenshot"
    MOVE_POINTER = "move_pointer"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    LAUNCH_APP = "launch_app"
    BROWSER_NAVIGATE = "browser_navigate"
    BROWSER_CLICK = "browser_click"
    BROWSER_TYPE = "browser_type"
    BROWSER_SNAPSHOT = "browser_snapshot"


class ComputerAction(BaseModel):
    surface: ControlSurface
    kind: ControlKind
    target: str = "local-node"
    parameters: dict[str, Any] = Field(default_factory=dict)


class ControlResult(BaseModel):
    success: bool
    output: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlBackend(Protocol):
    def execute(self, action: ComputerAction) -> ControlResult: ...


class ControlDenied(RuntimeError):
    def __init__(self, message: str, *, approval_id: str | None = None) -> None:
        super().__init__(message)
        self.approval_id = approval_id


class ComputerController:
    def __init__(
        self,
        policy: PolicyEngine,
        *,
        backends: dict[ControlSurface, ControlBackend],
        enabled: bool = False,
        event_path: str | Path | None = None,
    ) -> None:
        self.policy = policy
        self.backends = backends
        self.enabled = enabled
        self.event_path = Path(event_path) if event_path is not None else None
        self._ledgers: dict[str, EventLedger] = {}

    def execute(self, run_id: str, action: ComputerAction) -> ControlResult:
        if not self.enabled:
            raise ControlDenied("interactive control is disabled on this node")
        backend = self.backends.get(action.surface)
        if backend is None:
            raise ControlDenied(f"no backend is configured for {action.surface.value}")

        request = ActionRequest(
            run_id=run_id,
            target=action.target,
            action=f"computer.{action.kind.value}",
            tier=_tier_for(action.kind),
        )
        decision = self.policy.evaluate(request)
        if decision.decision is not Decision.ALLOW:
            raise ControlDenied(decision.reason, approval_id=decision.approval_id)

        ledger = self._ledger(run_id)
        if ledger is not None:
            ledger.append(
                EventType.TOOL_CALL,
                {
                    "tool": "computer",
                    "surface": action.surface.value,
                    "action": action.kind.value,
                    "parameter_names": sorted(action.parameters),
                },
            )
        result = backend.execute(action)
        if ledger is not None:
            ledger.append(
                EventType.TOOL_RESULT,
                {
                    "tool": "computer",
                    "surface": action.surface.value,
                    "action": action.kind.value,
                    "success": result.success,
                    "metadata": result.metadata,
                },
            )
        return result

    def _ledger(self, run_id: str) -> EventLedger | None:
        if self.event_path is None:
            return None
        if run_id not in self._ledgers:
            self._ledgers[run_id] = EventLedger(self.event_path, run_id=run_id)
        return self._ledgers[run_id]


class MssScreenBackend:
    """Optional screen-capture backend; imports `mss` only when invoked."""

    def execute(self, action: ComputerAction) -> ControlResult:
        if action.kind is not ControlKind.SCREENSHOT:
            raise ValueError("screen backend only supports screenshots")
        import mss  # type: ignore[import-not-found]
        import mss.tools  # type: ignore[import-not-found]

        monitor_index = int(action.parameters.get("monitor", 0))
        with mss.mss() as capture:
            monitor = capture.monitors[monitor_index]
            shot = capture.grab(monitor)
            png = mss.tools.to_png(shot.rgb, shot.size)
        return ControlResult(
            success=True,
            output=png,
            metadata={"media_type": "image/png", "monitor": monitor_index},
        )


class PyAutoGuiDesktopBackend:
    """Optional desktop backend; the controller performs policy checks first."""

    def execute(self, action: ComputerAction) -> ControlResult:
        import pyautogui

        values = action.parameters
        if action.kind is ControlKind.MOVE_POINTER:
            pyautogui.moveTo(
                int(values["x"]), int(values["y"]), duration=float(values.get("duration", 0))
            )
        elif action.kind is ControlKind.CLICK:
            pyautogui.click(
                int(values["x"]), int(values["y"]), button=str(values.get("button", "left"))
            )
        elif action.kind is ControlKind.TYPE_TEXT:
            pyautogui.write(str(values["text"]), interval=float(values.get("interval", 0)))
        elif action.kind is ControlKind.HOTKEY:
            pyautogui.hotkey(*[str(key) for key in values["keys"]])
        else:
            raise ValueError(f"unsupported desktop action: {action.kind.value}")
        return ControlResult(success=True, metadata={"backend": "pyautogui"})


class PlaywrightBrowserBackend:
    """Browser backend over an injected Playwright page."""

    def __init__(self, page: Any) -> None:
        self.page = page

    def execute(self, action: ComputerAction) -> ControlResult:
        values = action.parameters
        if action.kind is ControlKind.BROWSER_NAVIGATE:
            response = self.page.goto(str(values["url"]))
            status = response.status if response is not None else None
            return ControlResult(success=True, metadata={"status": status})
        if action.kind is ControlKind.BROWSER_CLICK:
            self.page.locator(str(values["selector"])).click()
            return ControlResult(success=True)
        if action.kind is ControlKind.BROWSER_TYPE:
            self.page.locator(str(values["selector"])).fill(str(values["text"]))
            return ControlResult(success=True)
        if action.kind is ControlKind.BROWSER_SNAPSHOT:
            return ControlResult(
                success=True,
                output=self.page.screenshot(full_page=bool(values.get("full_page", True))),
                metadata={"media_type": "image/png"},
            )
        raise ValueError(f"unsupported browser action: {action.kind.value}")


def _tier_for(kind: ControlKind) -> ActionTier:
    if kind in {ControlKind.SCREENSHOT, ControlKind.BROWSER_SNAPSHOT}:
        return ActionTier.READ_ONLY
    if kind in {ControlKind.MOVE_POINTER, ControlKind.BROWSER_NAVIGATE}:
        return ActionTier.VALIDATE
    return ActionTier.HIGH_RISK
