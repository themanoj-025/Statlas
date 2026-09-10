"""Report export — JSON, CSV, and PDF generation.

Implementation split across:
- report_styles.py: design tokens and paragraph styles
- report_pdf.py: radar chart drawing and PDF export
- report_export.py: JSON/CSV export and formatting helpers
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

# PDF export lives in report_pdf.py (reportlab); re-exported here so callers
# can keep using a single import surface: `from app import report_export`.
from app.report_pdf import export_pdf
from app.report_styles import _fmt_num, _fmt_pct, _fmt_ts, _json_inline

__all__ = ["export_csv", "export_json", "export_pdf"]


def export_json(report_doc: dict[str, Any]) -> str:
    """Serialize a report document to JSON."""
    return json.dumps(report_doc, indent=2, default=str)


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


# Formatters live in the leaf module (report_styles.py); re-imported here so
# existing `from app.report_export import _fmt_num` callers keep working.


def export_csv(report_doc: dict[str, Any], player_name: str | None = None) -> str:
    """Export a report's tabular data to CSV.

    Surfaces the quantitative profile — one row per metric
    (metric,metric_name,value,percentile) — plus the comparable-players table.
    Narrative sections (overview, role, strengths…) are prose and intentionally
    excluded from the CSV; JSON remains the canonical verbatim export.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        ["Report", report_doc.get("title", "Statlas Scouting Report — Statistical Profile")]
    )
    writer.writerow(["Player", player_name or report_doc.get("player_name", "")])
    writer.writerow([])

    sections = report_doc.get("sections", {})
    if isinstance(sections, dict):
        writer.writerow(["metric", "metric_name", "value", "percentile"])
        for m in sections.get("statistical_profile", {}).get("metrics", []):
            value = m.get("value")
            pct = m.get("percentile")
            writer.writerow(
                [
                    m.get("metric", ""),
                    m.get("metric_name", ""),
                    "" if value is None else value,
                    "" if pct is None else pct,
                ]
            )
        writer.writerow([])
        writer.writerow(["Comparable Players (Phase 6 similarity)"])
        writer.writerow(["name", "similarity", "club"])
        for c in sections.get("comparable_players", []) or []:
            similarity = c.get("similarity")
            writer.writerow([c.get("name", ""), "" if similarity is None else similarity, c.get("club") or ""])

    return output.getvalue()
