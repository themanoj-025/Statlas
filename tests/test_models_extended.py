"""Tests for Statlas domain models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit



class TestPlayerModel:
    """Tests for Player model."""

    def test_player_creation(self) -> None:
        from app.models.player import Player

        p = Player(
            player_id="P1",
            name="Test Player",
            team_id="T1",
            position="FW",
            nationality="England",
        )
        assert p.name == "Test Player"
        assert p.position == "FW"

    def test_player_to_dict(self) -> None:
        from app.models.player import Player

        p = Player(
            player_id="P1",
            name="Test",
            team_id="T1",
            position="MF",
            nationality="Spain",
        )
        d = p.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "Test"


class TestTeamModel:
    """Tests for Team model."""

    def test_team_creation(self) -> None:
        from app.models.player import Team

        t = Team(team_id="T1", name="Arsenal", league_id="L1", country="England")
        assert t.name == "Arsenal"

    def test_team_to_dict(self) -> None:
        from app.models.player import Team

        t = Team(team_id="T1", name="Barcelona", league_id="L1", country="Spain")
        d = t.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "Barcelona"


class TestReportModel:
    """Tests for Report model."""

    def test_report_creation(self) -> None:
        from app.models.report import Report

        r = Report(
            report_id="R1",
            player_id="P1",
            report_type="scouting",
            content="Good player",
            created_by="scout1",
        )
        assert r.report_type == "scouting"

    def test_report_to_dict(self) -> None:
        from app.models.report import Report

        r = Report(
            report_id="R1",
            player_id="P1",
            report_type="analysis",
            content="Analysis",
            created_by="analyst1",
        )
        d = r.to_dict()
        assert isinstance(d, dict)


class TestWorkspaceModel:
    """Tests for Workspace model."""

    def test_workspace_creation(self) -> None:
        from app.models.workspace import Workspace

        ws = Workspace(
            workspace_id="W1",
            name="Scouting Board",
            owner_id="user1",
            workspace_type="shortlist",
        )
        assert ws.name == "Scouting Board"

    def test_workspace_to_dict(self) -> None:
        from app.models.workspace import Workspace

        ws = Workspace(
            workspace_id="W1",
            name="Transfer Targets",
            owner_id="user1",
            workspace_type="shortlist",
        )
        d = ws.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "Transfer Targets"


class TestCacheModule:
    """Tests for cache module."""

    def test_cache_set_get(self) -> None:
        from app.cache import Cache

        cache = Cache()
        cache.set("key1", "value1", ttl=60)
        assert cache.get("key1") == "value1"

    def test_cache_miss(self) -> None:
        from app.cache import Cache

        cache = Cache()
        assert cache.get("nonexistent") is None

    def test_cache_delete(self) -> None:
        from app.cache import Cache

        cache = Cache()
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None
