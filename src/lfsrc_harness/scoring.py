"""Deterministic run scoring with an optional external judge boundary."""

from __future__ import annotations

import hashlib
import re
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .runner import CommandSpec, RunStatus, SubprocessRunner


class ScoreResult(BaseModel):
    score: float = Field(ge=0, le=1)
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ExactMatchScorer:
    def score(self, expected: Any, actual: Any) -> ScoreResult:
        passed = expected == actual
        return ScoreResult(score=1.0 if passed else 0.0, passed=passed)


class FileDiffScorer:
    def score(self, expected: str | Path, actual: str | Path) -> ScoreResult:
        expected_hashes = _tree_hashes(Path(expected))
        actual_hashes = _tree_hashes(Path(actual))
        expected_paths = set(expected_hashes)
        actual_paths = set(actual_hashes)
        common = expected_paths & actual_paths
        changed = sorted(path for path in common if expected_hashes[path] != actual_hashes[path])
        missing = sorted(expected_paths - actual_paths)
        added = sorted(actual_paths - expected_paths)
        unchanged = sorted(path for path in common if expected_hashes[path] == actual_hashes[path])
        total = len(expected_paths | actual_paths)
        score = len(unchanged) / total if total else 1.0
        return ScoreResult(
            score=score,
            passed=not (changed or missing or added),
            details={
                "unchanged": unchanged,
                "changed": changed,
                "missing": missing,
                "added": added,
            },
        )


class RuleKind(StrEnum):
    CONTAINS = "contains"
    REGEX = "regex"
    JSON_PATH_EQUALS = "json_path_equals"


class Rule(BaseModel):
    kind: RuleKind
    expected: Any
    path: str | None = None


class RuleScorer:
    def score(self, rules: list[Rule], subject: Any) -> ScoreResult:
        checks = [self._evaluate(rule, subject) for rule in rules]
        passed_count = sum(checks)
        score = passed_count / len(checks) if checks else 1.0
        return ScoreResult(
            score=score,
            passed=all(checks),
            details={"checks": checks, "passed": passed_count, "total": len(checks)},
        )

    def _evaluate(self, rule: Rule, subject: Any) -> bool:
        text = str(subject.get("text", subject)) if isinstance(subject, dict) else str(subject)
        if rule.kind is RuleKind.CONTAINS:
            return str(rule.expected) in text
        if rule.kind is RuleKind.REGEX:
            return re.search(str(rule.expected), text) is not None
        if rule.kind is RuleKind.JSON_PATH_EQUALS:
            if not rule.path:
                return False
            return bool(_resolve_path(subject, rule.path) == rule.expected)
        return False


class PytestScorer:
    def __init__(self, *, python_executable: str = sys.executable) -> None:
        self.python_executable = python_executable

    def score(self, test_path: str | Path) -> ScoreResult:
        result = SubprocessRunner().run(
            CommandSpec(
                argv=[self.python_executable, "-m", "pytest", str(test_path), "-q"],
                timeout_seconds=300,
            )
        )
        passed = result.status is RunStatus.SUCCEEDED
        return ScoreResult(
            score=1.0 if passed else 0.0,
            passed=passed,
            details={
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
            },
        )


class JudgeScorer:
    """Opt-in adapter; deterministic scorers remain authoritative by default."""

    def __init__(self, judge: Callable[[str, str], float]) -> None:
        self.judge = judge

    def score(self, rubric: str, artifact: str) -> ScoreResult:
        value = float(self.judge(rubric, artifact))
        if not 0 <= value <= 1:
            raise ValueError("judge score must be between 0 and 1")
        return ScoreResult(
            score=value,
            passed=value >= 0.5,
            details={"judge": "optional", "rubric": rubric},
        )


def _tree_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise ValueError(f"expected directory: {root}")
    result: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _resolve_path(subject: Any, path: str) -> Any:
    current = subject
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current
