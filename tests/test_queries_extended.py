"""Tests for Statlas queries module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestPlayerQueries:
    """Tests for player query functions."""

    def test_get_player_stats(self) -> None:
        from app.queries.player_queries import get_player_stats

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = get_player_stats(db, "P1")
        assert isinstance(result, (dict, list, type(None)))

    def test_search_players(self) -> None:
        from app.queries.player_queries import search_players

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = search_players(db, "Haaland")
        assert isinstance(result, list)


class TestTeamQueries:
    """Tests for team query functions."""

    def test_get_team_info(self) -> None:
        from app.queries.team_queries import get_team_info

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        result = get_team_info(db, "T1")
        assert result is None

    def test_get_team_players(self) -> None:
        from app.queries.team_queries import get_team_players

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = get_team_players(db, "T1")
        assert isinstance(result, list)


class TestLeagueQueries:
    """Tests for league query functions."""

    def test_get_league_info(self) -> None:
        from app.queries.league_queries import get_league_info

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        result = get_league_info(db, "L1")
        assert result is None

    def test_get_league_teams(self) -> None:
        from app.queries.league_queries import get_league_teams

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = get_league_teams(db, "L1")
        assert isinstance(result, list)


class TestDashboardQueries:
    """Tests for dashboard query functions."""

    def test_get_dashboard_stats(self) -> None:
        from app.queries.dashboard_queries import get_dashboard_stats

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = {"total_players": 0}
        result = get_dashboard_stats(db)
        assert isinstance(result, dict)


class TestSearchExecution:
    """Tests for search execution."""

    def test_execute_search(self) -> None:
        from app.queries.search_execution import execute_search

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = execute_search(db, {"query": "test"})
        assert isinstance(result, (list, dict))
