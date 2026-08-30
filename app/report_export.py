"""Report export formats (Phase 9 — Part C).

The single verified report object from app/reports.py is the canonical source
of truth: JSON exports it verbatim, and PDF/CSV are DERIVED from it — never
independently generated (scouting-reports.md §5).

- export_json: the full structured object including the evidence appendix —
  the most complete/auditable format.
- export_pdf: a real reportlab PDF applying the Constitution's design tokens
  (pitch-green palette from web/styles/tokens.css), with a native radar chart
  drawn from the report's own percentile data, branding, a data-snapshot
  footer, and basic document metadata for accessibility.
- export_csv: the tabular surfaces (statistical profile + comparables) that
  map naturally to a spreadsheet; narrative sections are necessarily omitted
  and the export UI says so (scouting-reports.md §5.3).
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from reportlab.graphics.shapes import Drawing, Line, Polygon, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --- Design tokens (mirror of web/styles/tokens.css, adapted for print) ----
PITCH_600 = colors.HexColor("#1A5F3E")  # primary headings / wordmark
PITCH_700 = colors.HexColor("#144E33")  # link/emphasis text
PITCH_400 = colors.HexColor("#2E8A5B")  # chart fill
GRAY_900 = colors.HexColor("#1A1814")  # body text
GRAY_600 = colors.HexColor("#5C574C")  # secondary text
GRAY_300 = colors.HexColor("#C9C4B8")  # hairline borders
AMBER_700 = colors.HexColor("#8A4B0B")  # accent (confidence/notes)
SURFACE = colors.HexColor("#FAF9F6")

BRAND = "STATLAS"

_PAGE_W, _PAGE_H = A4
_MARGIN = 16 * mm


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "wordmark": ParagraphStyle(
            "Wordmark",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=PITCH_600,
            spaceAfter=0,
        ),
        "tagline": ParagraphStyle(
            "Tagline",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=GRAY_600,
            spaceAfter=0,
        ),
        "h1": ParagraphStyle(
            "H1",
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=GRAY_900,
            spaceBefore=6,
            spaceAfter=2,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=PITCH_700,
            spaceBefore=12,
            spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "H3",
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=GRAY_900,
            spaceBefore=8,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=GRAY_900,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "muted": ParagraphStyle(
            "Muted",
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=GRAY_600,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=GRAY_600,
            spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=GRAY_600,
            spaceAfter=0,
        ),
        "cell": ParagraphStyle(
            "Cell",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=GRAY_900,
        ),
        "cellhead": ParagraphStyle(
            "CellHead",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        ),
    }


# ---------------------------------------------------------------------------
# JSON — the canonical, verbatim export
# ---------------------------------------------------------------------------


def export_json(report_doc: dict[str, Any]) -> str:
    """The full structured report object, verbatim (evidence appendix included).

    This is the canonical format; PDF/CSV derive from it.
    """
    return json.dumps(report_doc, indent=2, default=str)


# ---------------------------------------------------------------------------
# Radar chart — drawn natively with the design tokens, from report data
# ---------------------------------------------------------------------------


def _radar_drawing(items: list[dict[str, Any]], size: int = 150) -> Drawing:
    """Mini percentile radar from the report's own statistical_profile.

    items: [{metric_name, percentile (0-100 or None)}] — draws only metrics
    with a real percentile; a missing metric is omitted (never drawn as zero).
    """
    radius = size / 2 - 16
    cx, cy = size / 2, size / 2
    drawing = Drawing(size, size)

    labelled = [
        (i["metric_name"], i["percentile"])
        for i in items
        if i.get("percentile") is not None
    ]
    if not labelled:
        drawing.add(
            String(cx - 30, cy, "no percentile data", fontSize=7, fillColor=GRAY_600)
        )
        return drawing
    labelled = labelled[:12]
    n = len(labelled)
    ring_colors = [colors.HexColor("#E6E2D8"), colors.HexColor("#D2CDBE")]

    def _ring_points(level: float) -> list[float]:
        flat: list[float] = []
        for i in range(n):
            ang = -90 + i * 360 / n
            flat.extend(
                (cx + radius * level * _cos(ang), cy + radius * level * _sin(ang))
            )
        return flat

    # Grid rings (25/50/75/100).
    for level, color in zip((0.25, 0.5, 0.75, 1.0), ring_colors * 2):
        drawing.add(
            Polygon(
                _ring_points(level), strokeColor=color, strokeWidth=0.5, fillColor=None
            )
        )

    # Spokes.
    for i in range(n):
        ang = -90 + i * 360 / n
        drawing.add(
            Line(
                cx,
                cy,
                cx + radius * _cos(ang),
                cy + radius * _sin(ang),
                strokeColor=GRAY_300,
                strokeWidth=0.5,
            )
        )

    # Value polygon.
    value_points: list[float] = []
    for i in range(n):
        ang = -90 + i * 360 / n
        value = min(max(float(labelled[i][1]), 0.0), 100.0) / 100.0
        value_points.extend(
            (cx + radius * value * _cos(ang), cy + radius * value * _sin(ang))
        )
    drawing.add(
        Polygon(
            value_points,
            strokeColor=PITCH_600,
            strokeWidth=1.4,
            fillColor=PITCH_400,
            fillOpacity=0.22,
        )
    )

    # Labels.
    for i, (name, _) in enumerate(labelled):
        ang = -90 + i * 360 / n
        lx, ly = cx + (radius + 12) * _cos(ang), cy + (radius + 12) * _sin(ang)
        drawing.add(
            String(
                lx,
                ly - 3,
                name,
                fontSize=5.5,
                fillColor=GRAY_600,
                textAnchor=(
                    "middle"
                    if abs(_cos(ang)) < 0.3
                    else ("start" if _cos(ang) > 0 else "end")
                ),
            )
        )
    return drawing


def _cos(deg: float) -> float:
    import math

    return math.cos(math.radians(deg))


def _sin(deg: float) -> float:
    import math

    return math.sin(math.radians(deg))


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def _header_footer(canvas, doc) -> tuple[str, str]:
    canvas.saveState()
    canvas.setFillColor(SURFACE)
    canvas.rect(0, _PAGE_H - 30 * mm, _PAGE_W, 30 * mm, stroke=0, fill=1)
    canvas.setFillColor(PITCH_600)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(_MARGIN, _PAGE_H - 17 * mm, BRAND)
    canvas.setFillColor(GRAY_600)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(
        _MARGIN,
        _PAGE_H - 22 * mm,
        "AI Scouting Report — generated from verified Statlas data",
    )
    canvas.setFillColor(GRAY_300)
    canvas.line(_MARGIN, _PAGE_H - 25 * mm, _PAGE_W - _MARGIN, _PAGE_H - 25 * mm)
    canvas.setFillColor(GRAY_600)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(
        _MARGIN, 10 * mm, f"Page {doc.page} · data as of {doc.data_snapshot_label}"
    )
    canvas.drawRightString(
        _PAGE_W - _MARGIN,
        10 * mm,
        "statlas.app — reflects snapshot data, not real-time",
    )
    canvas.restoreState()


def export_pdf(report_doc: dict[str, Any], player_name: str | None = None) -> bytes:
    """A professionally formatted, token-consistent PDF derived from the doc.

    Sections: wordmark header, player heading, data-snapshot line, overview,
    statistical profile table, radar, strengths, weaknesses, comparables,
    trajectory, risks, recommendation + confidence, workspace context (if any),
    and the evidence appendix. Footer states the snapshot date + not-real-time
    note. Document metadata is set for basic accessibility.
    """
    buf = io.BytesIO()
    player_label = player_name or f"Player {report_doc.get('player_id')}"
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=32 * mm,
        bottomMargin=16 * mm,
        title=f"Statlas Scouting Report — {player_label}",
        author="Statlas",
        subject=f"Scouting report generated {report_doc.get('generated_at')}",
        # Uncompressed content streams: keeps the branding/footer text
        # extractable by PDF tools and screen readers (accessibility).
        pageCompression=0,
    )
    st = _styles()
    sections = report_doc.get("sections", {})
    snapshot_label = report_doc.get("data_snapshot_date", "unknown")
    doc.data_snapshot_label = snapshot_label  # used by header_footer
