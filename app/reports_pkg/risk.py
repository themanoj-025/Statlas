"""A3 - risk factors derived from real signals (never invented)."""

from __future__ import annotations

from app.reports_pkg.constants import OUT_OF_SCOPE_RISK, POSITION_PEAK_AGES


def derive_risk_factors(
    *,
    minutes_played: float,
    qualifying_minutes: float,
    seasons: int,
    has_event_data: bool,
    age: int | None,
    position_group: str | None,
) -> list[dict[str, str]] -> None:
    """Real-signal risk factors + the explicit out-of-scope statement.

    Only signals Statlas actually has data for are allowed (scouting-reports.md
    section 4): sample size, single-season coverage, event-data availability,
    and age vs. the documented position peak range. The out-of-scope statement
    is always appended so silence never implies completeness.
    """
    risks: list[dict[str, str]] = []
    if minutes_played < 2 * qualifying_minutes:
        risks.append(
            {
                "point": (
                    f"Limited sample size: {minutes_played:,.0f} minutes played, "
                    f"below twice the {qualifying_minutes:,.0f}-minute "
                    "qualification threshold. Percentile ranks are less stable "
                    "with a small sample."
                ),
                "basis": "sample_size",
            }
        )
    if seasons <= 1:
        risks.append(
            {
                "point": (
                    "Single-season assessment: Statlas only has snapshot "
                    "history for one season for this player, so no "
                    "multi-season development trend can be established."
                ),
                "basis": "single_season",
            }
        )
    if not has_event_data:
        risks.append(
            {
                "point": (
                    "No event-level data available: shot/pass maps for this "
                    "player are not in coverage, so tactical assessment from "
                    "event data is not possible in this report."
                ),
                "basis": "no_event_data",
            }
        )
    if age is not None and position_group in POSITION_PEAK_AGES:
        peak_min, peak_max = POSITION_PEAK_AGES[position_group]
        if age < peak_min:
            risks.append(
                {
                    "point": (
                        f"Age {age} is below the typical peak range "
                        f"({peak_min}-{peak_max}) for {position_group}s -- "
                        "development trajectory should be weighted when "
                        "interpreting current output."
                    ),
                    "basis": "age_vs_position",
                }
            )
        elif age > peak_max:
            risks.append(
                {
                    "point": (
                        f"Age {age} is above the typical peak range "
                        f"({peak_min}-{peak_max}) for {position_group}s -- "
                        "recent output may already be past peak."
                    ),
                    "basis": "age_vs_position",
                }
            )
    risks.append({"point": OUT_OF_SCOPE_RISK, "basis": "out_of_scope"})
    return risks
