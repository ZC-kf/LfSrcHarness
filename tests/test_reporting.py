import json
from pathlib import Path

from lfsrc_harness.reporting import (
    Finding,
    ReportArchive,
    ReportData,
    ReportRenderer,
    Severity,
    compare_reports,
)


def make_report(*, finding_id: str = "F-001") -> ReportData:
    return ReportData(
        run_id="run-1",
        title="Authorized assessment",
        summary="One validated observation.",
        scope=["127.0.0.1"],
        methodology=["local fixture inspection"],
        findings=[
            Finding(
                id=finding_id,
                title="Sample observation",
                severity=Severity.LOW,
                description="A deterministic sample.",
                evidence=["sha256:abc"],
                reproduction=["Run the local fixture"],
                remediation="Apply the documented configuration.",
            )
        ],
        appendix={"tool_versions": {"fixture": "1.0"}},
    )


def test_renderer_writes_markdown_json_html_pdf_and_sarif(tmp_path: Path) -> None:
    outputs = ReportRenderer().render_all(make_report(), tmp_path)

    assert set(outputs) == {"markdown", "json", "html", "pdf", "sarif"}
    assert outputs["markdown"].read_text(encoding="utf-8").startswith("# Authorized")
    assert json.loads(outputs["json"].read_text(encoding="utf-8"))["run_id"] == "run-1"
    assert "<html" in outputs["html"].read_text(encoding="utf-8").lower()
    assert outputs["pdf"].read_bytes().startswith(b"%PDF")
    sarif = json.loads(outputs["sarif"].read_text(encoding="utf-8"))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"][0]["ruleId"] == "F-001"


def test_report_comparison_tracks_added_resolved_and_unchanged() -> None:
    previous = make_report(finding_id="F-old")
    current = make_report(finding_id="F-new")
    current.findings.append(make_report(finding_id="F-old").findings[0])

    comparison = compare_reports(previous, current)

    assert comparison.added == ["F-new"]
    assert comparison.resolved == []
    assert comparison.unchanged == ["F-old"]


def test_archive_copies_outputs_and_invokes_uploader(tmp_path: Path) -> None:
    rendered = ReportRenderer().render_all(make_report(), tmp_path / "rendered")
    uploaded: list[Path] = []
    archive = ReportArchive(tmp_path / "archive", uploader=lambda path: uploaded.append(path))

    archived = archive.store("run-1", rendered)

    assert set(archived) == set(rendered)
    assert all(path.exists() for path in archived.values())
    assert sorted(path.name for path in uploaded) == sorted(path.name for path in archived.values())
