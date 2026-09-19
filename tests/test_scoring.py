import sys
from pathlib import Path

from lfsrc_harness.scoring import (
    ExactMatchScorer,
    FileDiffScorer,
    JudgeScorer,
    PytestScorer,
    Rule,
    RuleKind,
    RuleScorer,
)


def test_exact_match_scorer_is_deterministic() -> None:
    scorer = ExactMatchScorer()

    assert scorer.score("same", "same").score == 1.0
    assert scorer.score("same", "different").score == 0.0


def test_file_diff_reports_changed_missing_and_added(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    (expected / "same.txt").write_text("same", encoding="utf-8")
    (actual / "same.txt").write_text("same", encoding="utf-8")
    (expected / "changed.txt").write_text("old", encoding="utf-8")
    (actual / "changed.txt").write_text("new", encoding="utf-8")
    (expected / "missing.txt").write_text("missing", encoding="utf-8")
    (actual / "added.txt").write_text("added", encoding="utf-8")

    result = FileDiffScorer().score(expected, actual)

    assert result.score == 0.25
    assert result.details["changed"] == ["changed.txt"]
    assert result.details["missing"] == ["missing.txt"]
    assert result.details["added"] == ["added.txt"]


def test_rule_scorer_supports_contains_regex_and_json_path() -> None:
    rules = [
        Rule(kind=RuleKind.CONTAINS, expected="complete"),
        Rule(kind=RuleKind.REGEX, expected=r"run-\d+"),
        Rule(kind=RuleKind.JSON_PATH_EQUALS, path="result.severity", expected="low"),
    ]
    subject = {"text": "run-42 complete", "result": {"severity": "low"}}

    result = RuleScorer().score(rules, subject)

    assert result.passed
    assert result.score == 1.0


def test_pytest_scorer_runs_requested_test_path(tmp_path: Path) -> None:
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_ok():\n    assert 2 + 2 == 4\n", encoding="utf-8")

    result = PytestScorer(python_executable=sys.executable).score(test_file)

    assert result.passed
    assert "1 passed" in result.details["stdout"]


def test_optional_judge_adapter_is_explicit() -> None:
    calls: list[tuple[str, str]] = []

    def judge(rubric: str, artifact: str) -> float:
        calls.append((rubric, artifact))
        return 0.75

    result = JudgeScorer(judge).score("clarity", "artifact")

    assert result.score == 0.75
    assert calls == [("clarity", "artifact")]
