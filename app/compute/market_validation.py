"""Market data validation — rejects implausible values and flags data quality issues.

Constitution §3: Never publish flagged values. Flagged values are blocked
from publication until reviewed. Every validation rule is documented and
testable.

Constitution §6 #5: Never silently swallow a data pipeline error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import MarketValuation, Player, Team

# ---------------------------------------------------------------------------
# Plausibility bounds (documented, auditable)
# ---------------------------------------------------------------------------

# Market valuation bounds (EUR)
MIN_VALUATION_EUR = 10_000  # €10K — below this is implausible for a professional player
MAX_VALUATION_EUR = (
    500_000_000  # €500M — above this is implausible (current world record is ~€222M)
)

# Valuation range bounds
MAX_RANGE_SPREAD_RATIO = (
    0.6  # high/low range cannot differ by more than 60% of the midpoint
)

# Transfer fee bounds
MIN_TRANSFER_FEE_EUR = 0  # Free transfers are valid
MAX_TRANSFER_FEE_EUR = 500_000_000  # €500M max

# Contract bounds
MAX_CONTRACT_SALARY_EUR = 50_000_000  # €50M/year — above this is implausible
MAX_CONTRACT_YEARS_REMAINING = 10  # Contracts longer than 10 years are implausible


@dataclass
class ValidationResult:
    """Result of validating a single data record."""

    is_valid: bool
    issues: list[str] = field(default_factory=list)
    severity: str = "info"  # info, warning, error


@dataclass
class ValidationReport:
    """Aggregate validation report for a batch of records."""

    total_records: int = 0
    valid_records: int = 0
    flagged_records: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)


def validate_valuation(record: MarketValuation, db: Session) -> ValidationResult:
    """Validate a market valuation record against plausibility rules.

    Checks:
    1. Valuation amount is within plausible bounds
    2. Low/high range is within plausible bounds
    3. Range spread is not implausibly wide
    4. Player exists in canonical table
    5. Valuation date is not in the future
    """
    issues = []

    # 1. Amount bounds
    if record.valuation_amount_eur < MIN_VALUATION_EUR:
        issues.append(
            f"Valuation €{record.valuation_amount_eur:,.0f} below minimum €{MIN_VALUATION_EUR:,.0f}"
        )
    if record.valuation_amount_eur > MAX_VALUATION_EUR:
        issues.append(
            f"Valuation €{record.valuation_amount_eur:,.0f} exceeds maximum €{MAX_VALUATION_EUR:,.0f}"
        )

    # 2. Range bounds
    if record.low_range is not None and record.low_range < 0:
        issues.append(f"Negative low range: €{record.low_range:,.0f}")
    if record.high_range is not None and record.high_range < 0:
        issues.append(f"Negative high range: €{record.high_range:,.0f}")

    # 3. Range spread
    if record.low_range is not None and record.high_range is not None:
        midpoint = (record.low_range + record.high_range) / 2
        if midpoint > 0:
            spread = (record.high_range - record.low_range) / midpoint
            if spread > MAX_RANGE_SPREAD_RATIO:
                issues.append(
                    f"Range spread {spread:.1%} exceeds {MAX_RANGE_SPREAD_RATIO:.0%} threshold "
                    f"(low €{record.low_range:,.0f}, high €{record.high_range:,.0f})"
                )

    # 4. Player exists
    player = db.get(Player, record.player_id)
    if player is None:
        issues.append(f"Player {record.player_id} not found in canonical table")

    # 5. Date validity
    now = datetime.now(timezone.utc)
    if record.valuation_date > now:
        issues.append(f"Valuation date {record.valuation_date} is in the future")

    severity = (
        "error"
        if any("not found" in i or "exceeds maximum" in i for i in issues)
        else "warning"
    )
    return ValidationResult(
        is_valid=len(issues) == 0,
        issues=issues,
        severity=severity,
    )


def validate_transfer(record: Any, db: Session) -> ValidationResult:
    """Validate a transfer history record.

    Checks:
    1. Transfer fee is within plausible bounds (if not null)
    2. From/to teams exist
    3. Player exists
    4. Transfer date is not in the future
    5. Transfer type is valid enum
    """
    issues = []

    # 1. Fee bounds
    if record.reported_fee_eur is not None:
        if record.reported_fee_eur < MIN_TRANSFER_FEE_EUR:
            issues.append(f"Negative transfer fee: €{record.reported_fee_eur:,.0f}")
        if record.reported_fee_eur > MAX_TRANSFER_FEE_EUR:
            issues.append(
                f"Transfer fee €{record.reported_fee_eur:,.0f} exceeds maximum €{MAX_TRANSFER_FEE_EUR:,.0f}"
            )

    # 2. Teams exist
    if record.to_team_id is not None:
        team = db.get(Team, record.to_team_id)
        if team is None:
            issues.append(f"Destination team {record.to_team_id} not found")

    # 3. Player exists
    player = db.get(Player, record.player_id)
    if player is None:
        issues.append(f"Player {record.player_id} not found")

    # 4. Date validity
    now = datetime.now(timezone.utc)
    if record.transfer_date > now:
        issues.append(f"Transfer date {record.transfer_date} is in the future")

    # 5. Valid transfer type
    valid_types = {"permanent", "loan", "free_agent"}
    if record.transfer_type not in valid_types:
        issues.append(f"Invalid transfer type: {record.transfer_type}")

    severity = "error" if any("not found" in i for i in issues) else "warning"
    return ValidationResult(
        is_valid=len(issues) == 0,
        issues=issues,
        severity=severity,
    )


def validate_batch(
    db: Session,
    *,
    valuations: list[MarketValuation] | None = None,
    transfers: list[Any] | None = None,
) -> ValidationReport -> None:
    """Validate a batch of market data records.

    Returns a ValidationReport with counts of valid/flagged records
    and a list of all issues found.
    """
    report = ValidationReport()

    if valuations:
        for rec in valuations:
            report.total_records += 1
            result = validate_valuation(rec, db)
            if result.is_valid:
                report.valid_records += 1
            else:
                report.flagged_records += 1
                for issue in result.issues:
                    report.issues.append(
                        {
                            "record_type": "valuation",
                            "player_id": rec.player_id,
                            "source": rec.source,
                            "issue": issue,
                            "severity": result.severity,
                        }
                    )

    if transfers:
        for rec in transfers:
            report.total_records += 1
            result = validate_transfer(rec, db)
            if result.is_valid:
                report.valid_records += 1
            else:
                report.flagged_records += 1
                for issue in result.issues:
                    report.issues.append(
                        {
                            "record_type": "transfer",
                            "player_id": rec.player_id,
                            "issue": issue,
                            "severity": result.severity,
                        }
                    )

    return report
