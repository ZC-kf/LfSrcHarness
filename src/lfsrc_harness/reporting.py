"""Normalized findings and multi-format report rendering."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from html import escape
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from pydantic import BaseModel, Field
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Finding(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    severity: Severity
    description: str
    evidence: list[str] = Field(default_factory=list)
    reproduction: list[str] = Field(default_factory=list)
    remediation: str
    target: str | None = None


class ReportData(BaseModel):
    run_id: str
    title: str
    summary: str
    scope: list[str]
    methodology: list[str]
    findings: list[Finding]
    appendix: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReportComparison(BaseModel):
    added: list[str]
    resolved: list[str]
    unchanged: list[str]


class ReportRenderer:
    def __init__(self, template_directory: str | Path | None = None) -> None:
        directory = (
            Path(template_directory)
            if template_directory
            else Path(__file__).with_name("templates")
        )
        self.environment = Environment(
            loader=FileSystemLoader(directory),
            undefined=StrictUndefined,
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_all(self, report: ReportData, output_directory: str | Path) -> dict[str, Path]:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        markdown_path = output / f"{report.run_id}.md"
        json_path = output / f"{report.run_id}.json"
        html_path = output / f"{report.run_id}.html"
        pdf_path = output / f"{report.run_id}.pdf"
        sarif_path = output / f"{report.run_id}.sarif.json"

        markdown_text = self.environment.get_template("report.md.j2").render(report=report)
        markdown_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        body = markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])
        html_text = self.environment.get_template("report.html.j2").render(report=report, body=body)
        html_path.write_text(html_text, encoding="utf-8")
        self._render_pdf(report, pdf_path)
        sarif_path.write_text(
            json.dumps(_to_sarif(report), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return {
            "markdown": markdown_path,
            "json": json_path,
            "html": html_path,
            "pdf": pdf_path,
            "sarif": sarif_path,
        }

    def _render_pdf(self, report: ReportData, path: Path) -> None:
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "LfTitle", parent=styles["Title"], alignment=TA_CENTER, spaceAfter=12
        )
        document = SimpleDocTemplate(
            str(path),
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )
        story: list[Any] = [Paragraph(escape(report.title), title_style)]
        story.extend(
            [
                Paragraph(f"Run: {escape(report.run_id)}", styles["Normal"]),
                Spacer(1, 8),
                Paragraph("Summary", styles["Heading1"]),
                Paragraph(escape(report.summary), styles["BodyText"]),
                Paragraph("Scope", styles["Heading1"]),
            ]
        )
        story.extend(Paragraph(f"• {escape(item)}", styles["BodyText"]) for item in report.scope)
        story.extend([PageBreak(), Paragraph("Findings", styles["Heading1"])])
        for finding in report.findings:
            story.extend(
                [
                    Paragraph(
                        f"{escape(finding.id)} — {escape(finding.title)}", styles["Heading2"]
                    ),
                    Paragraph(f"Severity: {finding.severity.value}", styles["BodyText"]),
                    Paragraph(escape(finding.description), styles["BodyText"]),
                    Paragraph(f"Remediation: {escape(finding.remediation)}", styles["BodyText"]),
                    Spacer(1, 8),
                ]
            )
        document.build(story)


class ReportArchive:
    def __init__(
        self,
        root: str | Path,
        *,
        uploader: Callable[[Path], None] | None = None,
    ) -> None:
        self.root = Path(root)
        self.uploader = uploader

    def store(self, run_id: str, outputs: dict[str, Path]) -> dict[str, Path]:
        destination = self.root / run_id
        destination.mkdir(parents=True, exist_ok=True)
        archived: dict[str, Path] = {}
        for format_name, source in outputs.items():
            target = destination / source.name
            shutil.copy2(source, target)
            archived[format_name] = target
            if self.uploader is not None:
                self.uploader(target)
        return archived


def compare_reports(previous: ReportData, current: ReportData) -> ReportComparison:
    previous_ids = {finding.id for finding in previous.findings}
    current_ids = {finding.id for finding in current.findings}
    return ReportComparison(
        added=sorted(current_ids - previous_ids),
        resolved=sorted(previous_ids - current_ids),
        unchanged=sorted(previous_ids & current_ids),
    )


def _to_sarif(report: ReportData) -> dict[str, Any]:
    level_map = {
        Severity.INFO: "note",
        Severity.LOW: "note",
        Severity.MEDIUM: "warning",
        Severity.HIGH: "error",
        Severity.CRITICAL: "error",
    }
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "LfSrcHarness",
                        "version": "0.1.0",
                        "rules": [
                            {
                                "id": finding.id,
                                "name": finding.title,
                                "shortDescription": {"text": finding.description},
                            }
                            for finding in report.findings
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": finding.id,
                        "level": level_map[finding.severity],
                        "message": {"text": finding.description},
                        "properties": {
                            "severity": finding.severity.value,
                            "evidence": finding.evidence,
                            "remediation": finding.remediation,
                        },
                    }
                    for finding in report.findings
                ],
            }
        ],
    }
