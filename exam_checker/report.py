"""Utilities for producing structured inspection reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class PageReport:
    page_number: int
    content: str

    def to_dict(self) -> dict:
        return {"page_number": self.page_number, "content": self.content}


class ReportFormatter:
    """Assemble multiple page reports and persist them to disk."""

    def __init__(self) -> None:
        self.reports: List[PageReport] = []

    def add_page_report(self, report: PageReport) -> None:
        self.reports.append(report)

    def to_markdown(self) -> str:
        sections = []
        for report in self.reports:
            sections.append(f"## 페이지 {report.page_number}\n\n{report.content}\n")
        return "\n".join(sections)

    def save_markdown(self, output_path: Path) -> None:
        output_path.write_text(self.to_markdown(), encoding="utf-8")

    def save_json(self, output_path: Path) -> None:
        payload = [report.to_dict() for report in self.reports]
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
