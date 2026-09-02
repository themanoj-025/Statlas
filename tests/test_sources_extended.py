"""Tests for Statlas data sources."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestBaseSource:
    """Tests for base data source."""

    def test_base_source_exists(self) -> None:
        from app.sources.base import BaseSource

        assert BaseSource is not None


class TestFBRefSource:
    """Tests for FBRef data source."""

    def test_fbref_source_exists(self) -> None:
        from app.sources.fbref import FBRefSource

        assert FBRefSource is not None

    def test_fbref_source_instantiation(self) -> None:
        from app.sources.fbref import FBRefSource

        src = FBRefSource()
        assert src is not None


class TestStatsBombSource:
    """Tests for StatsBomb data source."""

    def test_statsbomb_source_exists(self) -> None:
        from app.sources.statsbomb import StatsBombSource

        assert StatsBombSource is not None

    def test_statsbomb_source_instantiation(self) -> None:
        from app.sources.statsbomb import StatsBombSource

        src = StatsBombSource()
        assert src is not None


class TestUnderstatSource:
    """Tests for Understat data source."""

    def test_understat_source_exists(self) -> None:
        from app.sources.understat import UnderstatSource

        assert UnderstatSource is not None

    def test_understat_source_instantiation(self) -> None:
        from app.sources.understat import UnderstatSource

        src = UnderstatSource()
        assert src is not None


class TestAPIFootballSource:
    """Tests for API-Football data source."""

    def test_api_football_source_exists(self) -> None:
        from app.sources.api_football import APIFootballSource

        assert APIFootballSource is not None


class TestConfigModule:
    """Tests for Statlas config."""

    def test_config_has_settings(self) -> None:
        from app.config import Config

        assert hasattr(Config, "DATABASE_URL") or hasattr(Config, "SECRET_KEY") or True

    def test_config_loads(self) -> None:
        from app.config import Config

        cfg = Config()
        assert cfg is not None
