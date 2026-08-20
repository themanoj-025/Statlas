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


def _header_footer(canvas, doc):
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

    story: list[Any] = []

    def body(text: str | None) -> None:
        if text:
            story.append(Paragraph(text, st["body"]))

    # Branding block.
    story.append(Paragraph(BRAND, st["wordmark"]))
    story.append(
        Paragraph(
            "AI scouting report · every claim traced to real Statlas data",
            st["tagline"],
        )
    )
    story.append(
        HRFlowable(
            width="100%", thickness=1.2, color=PITCH_600, spaceBefore=4, spaceAfter=10
        )
    )

    # Heading + snapshot.
    story.append(
        Paragraph(player_name or f"Player #{report_doc.get('player_id')}", st["h1"])
    )
    story.append(
        Paragraph(
            f"Generated {_fmt_ts(report_doc.get('generated_at'))} · data snapshot {snapshot_label} — "
            f"this report reflects data as of that date, not real-time.",
            st["muted"],
        )
    )
    status = report_doc.get("verification", {}).get("status", "passed")
    if status == "needs_review":
        story.append(
            Paragraph(
                "<b>Needs review:</b> this report contains a claim that failed "
                "automated verification against Statlas data. Treat every "
                "unverified figure with caution.",
                ParagraphStyle(
                    "warn", parent=st["body"], textColor=AMBER_700, spaceBefore=6
                ),
            )
        )

    # Overview.
    story.append(Paragraph("Overview", st["h2"]))
    body(sections.get("overview", {}).get("text"))

    # Statistical profile + radar.
    story.append(Paragraph("Statistical Profile", st["h2"]))
    metrics = sections.get("statistical_profile", {}).get("metrics", [])
    if metrics:
        rows = [
            [
                Paragraph("Metric", st["cellhead"]),
                Paragraph("Value", st["cellhead"]),
                Paragraph("Percentile", st["cellhead"]),
            ]
        ]
        for m in metrics:
            value = m.get("value")
            pct = m.get("percentile")
            rows.append(
                [
                    Paragraph(m.get("metric_name", m.get("metric", "")), st["cell"]),
                    Paragraph("—" if value is None else _fmt_num(value), st["cell"]),
                    Paragraph("—" if pct is None else f"{_fmt_num(pct)}th", st["cell"]),
                ]
            )
        table = Table(rows, colWidths=[78 * mm, 38 * mm, 40 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PITCH_600),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
                    ("GRID", (0, 0), (-1, -1), 0.4, GRAY_300),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 4))
        story.append(Paragraph("Percentile radar (vs. position cohort)", st["h3"]))
        story.append(_radar_drawing(metrics))
    else:
        story.append(Paragraph("No statistical profile in this report.", st["muted"]))

    # Strengths / weaknesses.
    story.append(Paragraph("Strengths", st["h2"]))
    _bullet_list(story, sections.get("strengths", []), st)
    story.append(Paragraph("Weaknesses", st["h2"]))
    _bullet_list(story, sections.get("weaknesses", []), st)

    # Comparable players.
    story.append(Paragraph("Comparable Players", st["h2"]))
    comparables = sections.get("comparable_players", [])
    if comparables:
        for c in comparables:
            sim = c.get("similarity")
            c_label = c.get("name") or f"Player {c.get('player_id')}"
            line = f"<b>{c_label}</b> — {_fmt_pct(sim)} similar"
            story.append(Paragraph(line, st["body"]))
            expl = c.get("explanation") or {}
            matched = expl.get("matched_strengths", [])
            diffs = expl.get("key_differences", [])
            if matched:
                story.append(
                    Paragraph(
                        "Matched strengths: "
                        + ", ".join(
                            f"{m.get('metric_name', m.get('metric'))} ({_fmt_num(m.get('player_a_percentile'))}th vs {_fmt_num(m.get('player_b_percentile'))}th)"
                            for m in matched[:3]
                        ),
                        st["small"],
                    )
                )
            if diffs:
                story.append(
                    Paragraph(
                        "Key differences: "
                        + ", ".join(
                            f"{m.get('metric_name', m.get('metric'))} ({_fmt_num(m.get('difference'))} pts)"
                            for m in diffs[:3]
                        ),
                        st["small"],
                    )
                )
    else:
        story.append(
            Paragraph(
                "No comparable players with published data were found.", st["muted"]
            )
        )

    # Trajectory + risks.
    story.append(Paragraph("Development Trajectory", st["h2"]))
    body(sections.get("development_trajectory", {}).get("trend_summary"))
    story.append(Paragraph("Risk Factors", st["h2"]))
    _bullet_list(story, sections.get("risk_factors", []), st)

    # Recommendation + confidence.
    story.append(Paragraph("Recommendation", st["h2"]))
    rec = sections.get("recommendation", {})
    body(rec.get("text"))
    story.append(
        Paragraph(
            f"Confidence: <b>{rec.get('confidence_level', 'n/a')}</b> — {rec.get('confidence_rationale', '')}",
            st["body"],
        )
    )

    # Workspace context (the user's own Phase 7 data, clearly labelled).
    wc = sections.get("workspace_context")
    if wc:
        story.append(PageBreak())
        story.append(Paragraph("Workspace Context", st["h2"]))
        story.append(
            Paragraph(wc.get("label", "user's own scouting notes"), st["muted"])
        )
        status = wc.get("shortlist_status")
        priority = wc.get("priority")
        tags = wc.get("tags") or []
        notes = wc.get("recent_notes") or []
        story.append(
            Paragraph(
                f"Status: <b>{status or '—'}</b> · Priority: <b>{priority or '—'}</b>"
                + (f" · Tags: {', '.join(tags)}" if tags else ""),
                st["body"],
            )
        )
        for note in notes:
            story.append(
                Paragraph(
                    f"“{note.get('note_text', '')}” <i>({_fmt_ts(note.get('created_at'))})</i>",
                    st["small"],
                )
            )

    # Evidence appendix.
    story.append(PageBreak())
    story.append(Paragraph("Evidence Appendix", st["h2"]))
    story.append(
        Paragraph(
            "Every claim in this report traces to a real tool-call result from "
            "the verified context gathered at generation time (scouting-reports.md §5).",
            st["muted"],
        )
    )
    appendix = report_doc.get("evidence_appendix", [])
    if appendix:
        rows = [
            [
                Paragraph("Claim", st["cellhead"]),
                Paragraph("Source call", st["cellhead"]),
                Paragraph("Raw result", st["cellhead"]),
            ]
        ]
        for item in appendix:
            raw = item.get("raw_result")
            rows.append(
                [
                    Paragraph(str(item.get("claim", "")), st["cell"]),
                    Paragraph(str(item.get("source_call", "")), st["cell"]),
                    Paragraph(_json_inline(raw), st["cell"]),
                ]
            )
        table = Table(rows, colWidths=[56 * mm, 30 * mm, 70 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GRAY_900),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
                    ("GRID", (0, 0), (-1, -1), 0.4, GRAY_300),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No evidence appendix in this report.", st["muted"]))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()


def _bullet_list(
    story: list[Any], items: list[dict[str, Any]], st: dict[str, ParagraphStyle]
) -> None:
    for item in items:
        text = item.get("point") or item.get("text")
        if not text:
            continue
        extra = ""
        if item.get("supporting_metric"):
            pct = item.get("percentile")
            value = item.get("value")
            if pct is not None:
                extra = f" — {_fmt_num(pct)}th percentile"
            if value is not None:
                extra += f" ({_fmt_num(value)} per 90)"
        story.append(Paragraph(f"• {text}{extra}", st["body"]))


def _fmt_num(value: Any) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if num == int(num):
        return f"{int(num):,}"
    return f"{num:,.1f}"


def _fmt_pct(value: Any) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{num * 100:.0f}%"


def _fmt_ts(value: Any) -> str:
    if not value:
        return "—"
    text = str(value)
    return text[:10]


def _json_inline(value: Any) -> str:
    return json.dumps(value, default=str)[:400]


# ---------------------------------------------------------------------------
# CSV — the tabular surfaces only; narrative omitted and documented
# ---------------------------------------------------------------------------


def export_csv(report_doc: dict[str, Any], player_name: str | None = None) -> str:
    """Two tables a spreadsheet can actually use.

    Sheet 1 — statistical profile (metric, value, percentile); sheet 2 —
    comparable players (name, similarity, top matched/difference). Narrative
    sections are omitted by design; the export UI documents this.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    sections = report_doc.get("sections", {})

    writer.writerow(["Statlas Scouting Report — Statistical Profile"])
    writer.writerow(["player", player_name or report_doc.get("player_id")])
    writer.writerow(["generated_at", report_doc.get("generated_at")])
    writer.writerow(["data_snapshot_date", report_doc.get("data_snapshot_date")])
    writer.writerow([])
    writer.writerow(["metric", "metric_name", "value", "percentile"])
    for m in sections.get("statistical_profile", {}).get("metrics", []):
        writer.writerow(
            [
                m.get("metric", ""),
                m.get("metric_name", ""),
                "" if m.get("value") is None else m.get("value"),
                "" if m.get("percentile") is None else m.get("percentile"),
            ]
        )

    writer.writerow([])
    writer.writerow([])
    writer.writerow(["Comparable Players (Phase 6 similarity)"])
    writer.writerow(
        [
            "player_id",
            "name",
            "similarity",
            "top_matched_strength",
            "top_key_difference",
        ]
    )
    for c in sections.get("comparable_players", []):
        expl = c.get("explanation") or {}
        matched = expl.get("matched_strengths") or []
        diffs = expl.get("key_differences") or []
        top_m = matched[0].get("metric") if matched else ""
        top_d = diffs[0].get("metric") if diffs else ""
        writer.writerow(
            [
                c.get("player_id", ""),
                c.get("name", ""),
                c.get("similarity", ""),
                top_m,
                top_d,
            ]
        )

    return buf.getvalue()
