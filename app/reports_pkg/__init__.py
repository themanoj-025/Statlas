"""reports_pkg — focused submodules extracted from the monolithic reports.py.

Re-exports every public name so that `from app.reports_pkg import X` works
exactly as `from app.reports import X` did before the split.
"""

from app.reports_pkg.confidence import compute_report_confidence
from app.reports_pkg.constants import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_WEIGHTS,
    MIN_RECENT_NOTES,
    OUT_OF_SCOPE_RISK,
    POSITION_PEAK_AGES,
    REPORT_SOURCE_LABEL,
    WORKSPACE_SOURCE_LABEL,
    PlayerHasNoData,
    ReportLimitExceeded,
    ReportNotFound,
    ReportNotConfigured,
    _NARRATIVE_FIELDS,
)
from app.reports_pkg.context import (
    _age_from_dob,
    _build_corpus,
    _owned_entry_for_report,
    gather_report_context,
)
from app.reports_pkg.narrators import (
    _narrate_via_anthropic,
    deterministic_narrator,
)
from app.reports_pkg.pipeline import (
    _build_evidence_appendix,
    _player_name,
    _report_payload,
    _snapshot_label,
    delete_report,
    generate_report,
    get_report,
    list_reports,
)
from app.reports_pkg.quota import (
    _consume_report_quota,
    _quota_window,
    get_report_quota,
)
from app.reports_pkg.risk import derive_risk_factors
from app.reports_pkg.verification import (
    _extract_numbers,
    _mask_labels,
    verify_report,
)

__all__ = [
    # constants
    "CONFIDENCE_WEIGHTS",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_MEDIUM",
    "POSITION_PEAK_AGES",
    "REPORT_SOURCE_LABEL",
    "WORKSPACE_SOURCE_LABEL",
    "OUT_OF_SCOPE_RISK",
    "MIN_RECENT_NOTES",
    "_NARRATIVE_FIELDS",
    # errors
    "ReportNotFound",
    "ReportLimitExceeded",
    "ReportNotConfigured",
    "PlayerHasNoData",
    # confidence
    "compute_report_confidence",
    # risk
    "derive_risk_factors",
    # context
    "_age_from_dob",
    "_owned_entry_for_report",
    "_build_corpus",
    "gather_report_context",
    # verification
    "_mask_labels",
    "_extract_numbers",
    "verify_report",
    # narrators
    "deterministic_narrator",
    "_narrate_via_anthropic",
    # quota
    "_quota_window",
    "get_report_quota",
    "_consume_report_quota",
    # pipeline
    "_build_evidence_appendix",
    "_snapshot_label",
    "_report_payload",
    "_player_name",
    "generate_report",
    "list_reports",
    "get_report",
    "delete_report",
]
