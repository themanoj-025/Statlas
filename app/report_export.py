"""Report export — JSON, CSV, and PDF generation.

Implementation split across:
- report_styles.py: design tokens and paragraph styles
- report_pdf.py: radar chart drawing and PDF export
- report_export.py: JSON/CSV export and formatting helpers
"""

from __future__ import annotations

from typing import Any

import json
import csv
import io

from app.report_pdf import export_pdf  # noqa: F401


def export_json(report_doc: dict[str, Any]) -> str:
    """Serialize a report document to JSON."""
    return json.dumps(report_doc, indent=2, default=str)


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _fmt_num(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return str(value)


def _fmt_pct(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1f}%"
    return str(value)


def _fmt_ts(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_inline(value: Any) -> str:
    return json.dumps(value, default=str)


def export_csv(report_doc: dict[str, Any], player_name: str | None = None) -> str:
    """Export a report document to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Report", report_doc.get("title", "Untitled")])
    writer.writerow(["Player", player_name or report_doc.get("player_name", "")])
    writer.writerow([])

    for section in report_doc.get("sections", []):
        writer.writerow([section.get("heading", "")])
        for item in section.get("items", []):
            if isinstance(item, dict):
                writer.writerow([item.get("label", ""), item.get("value", "")])
            else:
                writer.writerow([str(item)])
        writer.writerow([])

    return output.getvalue()
