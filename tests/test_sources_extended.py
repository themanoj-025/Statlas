"""Tests for app.sources — market data and transfermarkt parsers."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestMarketDataSource:
    """Test market data source module."""

    def test_module_importable(self) -> None:
        import app.sources.market_data as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.sources.market_data as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestTransfermarktFetching:
    """Test transfermarkt fetching module."""

    def test_module_importable(self) -> None:
        import app.sources.transfermarkt_pkg.fetching as mod
        assert hasattr(mod, "__file__")


class TestTransfermarktMarketData:
    """Test transfermarkt market data module."""

    def test_module_importable(self) -> None:
        import app.sources.transfermarkt_pkg.market_data as mod
        assert hasattr(mod, "__file__")


class TestTransfermarktParsers:
    """Test transfermarkt parsers module."""

    def test_module_importable(self) -> None:
        import app.sources.transfermarkt_pkg.parsers as mod
        assert hasattr(mod, "__file__")


class TestTransfermarktTransfers:
    """Test transfermarkt transfers module."""

    def test_module_importable(self) -> None:
        import app.sources.transfermarkt_pkg.transfers as mod
        assert hasattr(mod, "__file__")
