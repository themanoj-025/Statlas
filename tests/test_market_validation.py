"""Tests for app.compute.market_validation — valuation plausibility checks."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestValidationResult:
    """ValidationResult dataclass basics."""

    def test_valid_result(self) -> None:
        from app.compute.market_validation import ValidationResult
        r = ValidationResult(is_valid=True)
        assert r.is_valid is True
        assert r.issues == []
        assert r.severity == "info"

    def test_invalid_result(self) -> None:
        from app.compute.market_validation import ValidationResult
        r = ValidationResult(is_valid=False, issues=["too low"], severity="error")
        assert r.is_valid is False
        assert len(r.issues) == 1
        assert r.severity == "error"


class TestValidationReport:
    """ValidationReport aggregation."""

    def test_empty_report(self) -> None:
        from app.compute.market_validation import ValidationReport
        r = ValidationReport()
        assert r.total_records == 0
        assert r.flagged_records == 0
        assert r.issues == []


class TestPlausibilityBounds:
    """Verify documented bounds are sensible."""

    def test_valuation_bounds(self) -> None:
        from app.compute.market_validation import MAX_VALUATION_EUR, MIN_VALUATION_EUR
        assert MIN_VALUATION_EUR == 10_000
        assert MAX_VALUATION_EUR == 500_000_000
        assert MIN_VALUATION_EUR < MAX_VALUATION_EUR

    def test_transfer_fee_bounds(self) -> None:
        from app.compute.market_validation import (
            MAX_TRANSFER_FEE_EUR,
            MIN_TRANSFER_FEE_EUR,
        )
        assert MIN_TRANSFER_FEE_EUR == 0
        assert MAX_TRANSFER_FEE_EUR == 500_000_000

    def test_contract_bounds(self) -> None:
        from app.compute.market_validation import (
            MAX_CONTRACT_SALARY_EUR,
            MAX_CONTRACT_YEARS_REMAINING,
        )
        assert MAX_CONTRACT_SALARY_EUR == 50_000_000
        assert MAX_CONTRACT_YEARS_REMAINING == 10
