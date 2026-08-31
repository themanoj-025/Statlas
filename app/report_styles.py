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

