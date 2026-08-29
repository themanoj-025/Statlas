"""Report constants and domain errors (extracted from reports.py)."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants (documented in docs/product/scouting-reports.md)
# ---------------------------------------------------------------------------

CONFIDENCE_WEIGHTS = {"sample_size": 0.5, "data_completeness": 0.3, "recency": 0.2}
CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.60

# Age vs. position development curve (scouting-reports.md section 4). Typical
# peak ranges by position group -- the ONLY age-based risk signal the
# generator uses.
POSITION_PEAK_AGES: dict[str, tuple[int, int]] = {
    "GK": (26, 33),
    "CB": (26, 33),
    "FB": (24, 30),
    "DM": (24, 30),
    "CM": (24, 30),
    "AM": (22, 28),
    "W": (22, 28),
    "ST": (23, 29),
}

REPORT_SOURCE_LABEL = "player_profile"
WORKSPACE_SOURCE_LABEL = "shortlist_entry"

OUT_OF_SCOPE_RISK = (
    "Not assessed: injury history, attitude and off-field factors are outside "
    "what Statlas data can support -- this report does not cover them."
)

MIN_RECENT_NOTES = 3  # most recent workspace notes included in the report

# Narrative text fields verified by verify_report (walked for numbers/metrics).
_NARRATIVE_FIELDS = (
    ("overview", "text"),
    ("role_and_position", "text"),
    ("development_trajectory", "trend_summary"),
    ("recommendation", "text"),
)


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------


class ReportNotFound(ValueError):
    """Missing OR not owned -- mapped to HTTP 404 (existence must not leak)."""


class ReportLimitExceeded(ValueError):
    """Free tier or quota cap reached -- honest, specific upsell message."""


class ReportNotConfigured(ValueError):
    """ANTHROPIC_API_KEY unset -- honest not-configured state, never a scripted demo."""


class PlayerHasNoData(ValueError):
    """The player has no published percentile data -- a report cannot be grounded."""
