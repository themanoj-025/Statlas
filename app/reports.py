"""AI scouting reports -- the grounded report pipeline (Phase 9).

.. deprecated::
    This module is now a thin re-exporter.  All implementation lives in
    ``app.reports_pkg.*`` submodules.  Existing ``from app.reports import X``
    imports continue to work unchanged.
"""

from __future__ import annotations

# Re-export every public name so existing ``from app.reports import X`` and
# ``reports.X`` usages continue to work without modification.
from app.reports_pkg import (  # noqa: F401
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
    _age_from_dob,
    _build_corpus,
    _build_evidence_appendix,
    _consume_report_quota,
    _extract_numbers,
    _mask_labels,
    _narrate_via_anthropic,
    _owned_entry_for_report,
    _player_name,
    _quota_window,
    _report_payload,
    _snapshot_label,
    compute_report_confidence,
    delete_report,
    derive_risk_factors,
    gather_report_context,
    generate_report,
    get_report,
    get_report_quota,
    list_reports,
    deterministic_narrator,
    verify_report,
)
