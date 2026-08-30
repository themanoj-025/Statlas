"""PDF and CSV report generation helpers."""

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
