
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

"""Tests for the Transfermarkt source parser.

Uses fixture HTML to test parsing logic without network requests.
"""


from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from bs4 import BeautifulSoup

from app.sources.base import SourceError
from app.sources.transfermarkt import (
    TransfermarktSource,
    _parse_date,
    _parse_market_value,
    _parse_transfer_fee,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_html(filename: str) -> str:
    return (FIXTURES / filename).read_text(encoding="utf-8")


def _fixture_soup(filename: str) -> BeautifulSoup:
    return BeautifulSoup(_fixture_html(filename), "html.parser")


# ---------------------------------------------------------------------------
# Unit tests: parsing helpers
# ---------------------------------------------------------------------------


class TestParseMarketValue:
    def test_millions(self) -> None:
        assert _parse_market_value("€85.00m") == 85_000_000.0

    def test_millions_no_decimal(self) -> None:
        assert _parse_market_value("€50m") == 50_000_000.0

    def test_thousands(self) -> None:
        assert _parse_market_value("€500K") == 500_000.0

    def test_billions(self) -> None:
        assert _parse_market_value("€1.50bn") == 1_500_000_000.0

    def test_plain_number(self) -> None:
        assert _parse_market_value("€25000000") == 25_000_000.0

    def test英镑(self) -> None:
        assert _parse_market_value("£85.00m") == 85_000_000.0

    def test_dollar(self) -> None:
        assert _parse_market_value("$50.00m") == 50_000_000.0

    def test_empty(self) -> None:
        assert _parse_market_value("") is None

    def test_none(self) -> None:
        assert _parse_market_value(None) is None

    def test_no_match(self) -> None:
        assert _parse_market_value("price unknown") is None

    def test_with_comma(self) -> None:
        assert _parse_market_value("€1,500.00m") == 1_500_000_000.0

    def test_fixture_value(self) -> None:
        soup = _fixture_soup("transfermarkt_player.html")
        mv_el = soup.select_one(
            "div.data-header__market-value-wrapper"
        )
        assert mv_el is not None
        value = _parse_market_value(mv_el.get_text(strip=True))
        assert value == 180_000_000.0


class TestParseTransferFee:
    def test_free(self) -> None:
        assert _parse_transfer_fee("Free transfer") == 0.0

    def test_numeric(self) -> None:
        assert _parse_transfer_fee("€10.00m") == 10_000_000.0

    def test_loan(self) -> None:
        assert _parse_transfer_fee("Loan") is None

    def test_empty(self) -> None:
        assert _parse_transfer_fee("") is None


class TestParseDate:
    def test_standard(self) -> None:
        dt = _parse_date("Jan 15, 2024")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_european(self) -> None:
        dt = _parse_date("15/01/2024")
        assert dt is not None
        assert dt.year == 2024

    def test_iso(self) -> None:
        dt = _parse_date("2024-01-15")
        assert dt is not None
        assert dt.year == 2024

    def test_empty(self) -> None:
        assert _parse_date("") is None

    def test_none(self) -> None:
        assert _parse_date(None) is None


# ---------------------------------------------------------------------------
# Integration tests: parsing fixture HTML
# ---------------------------------------------------------------------------


class TestPlayerProfileParsing:
    def test_parse_profile(self) -> None:
        soup = _fixture_soup("transfermarkt_player.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        data = source._parse_player_profile(soup)

        assert data.get("name") == "Erling Haaland"
        assert data.get("market_value_eur") == 180_000_000.0
        assert "norway" in data.get("citizenship", "").lower()
        assert "centre-forward" in data.get("position", "").lower()

    def test_contract_from_profile(self) -> None:
        soup = _fixture_soup("transfermarkt_player.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        as_of = datetime(2026, 8, 22, tzinfo=timezone.utc)

        contract = source._parse_contract_from_profile(soup, 418560, as_of)
        assert contract is not None
        assert contract.player_id == 418560
        assert contract.contract_status == "active"  # expires 2034, well in the future
        assert contract.contract_end_date is not None
        assert contract.contract_end_date.year == 2034

    def test_market_value_history(self) -> None:
        soup = _fixture_soup("transfermarkt_player.html")
        source = TransfermarktSource.__new__(TransfermarktSource)

        history = source._extract_market_value_history(soup, 418560)
        assert len(history) == 8
        # First entry: 2017, 500K
        assert history[0]["value"] == 500_000
        # Last entry: 2024, 180M
        assert history[-1]["value"] == 180_000_000
        # Dates are sorted ascending
        assert history[0]["date"] < history[-1]["date"]


# ---------------------------------------------------------------------------
# Mocked network tests
# ---------------------------------------------------------------------------


class TestTransfermarktSourceMocked:
    def test_fetch_valuations_uses_ceapi(self) -> None:
        """Verify fetch_valuations uses the CEAPI JSON endpoint."""
        import json as _json

        ceapi_response = _json.dumps({
            "list": [
                {"x": 1672531200000, "y": 170000000, "mw": "\u20ac170.00m",
                 "datum_mw": "01/01/2023", "verein": "Manchester City", "age": "22"},
                {"x": 1704067200000, "y": 180000000, "mw": "\u20ac180.00m",
                 "datum_mw": "01/01/2024", "verein": "Manchester City", "age": "23"},
            ],
            "current": {"y": 180000000},
            "highest": {"y": 180000000},
        })
        source = TransfermarktSource.__new__(TransfermarktSource)
        source.session = MagicMock()
        source.cache = MagicMock()
        source.cache.get.return_value = ceapi_response
        source.limiter = MagicMock()
        source.tiers = {"leagues": {}}

        records = source.fetch_valuations([418560], datetime(2026, 8, 22, tzinfo=timezone.utc))
        assert len(records) == 1
        assert records[0].source == "transfermarkt"
        assert records[0].valuation_amount_eur == 180_000_000.0
        assert records[0].player_id == 418560

    def test_fetch_valuations_handles_error_gracefully(self) -> None:
        """Failed player lookups should not crash the batch."""
        source = TransfermarktSource.__new__(TransfermarktSource)
        source.session = MagicMock()
        source.cache = MagicMock()
        source.cache.get.return_value = None  # no cache
        source.limiter = MagicMock()
        # Make _fetch raise an error
        source._fetch = MagicMock(side_effect=SourceError("blocked"))
        source.tiers = {"leagues": {}}

        records = source.fetch_valuations(
            [418560, 999999], datetime(2026, 8, 22, tzinfo=timezone.utc)
        )
        # Should return empty list, not raise
        assert records == []
