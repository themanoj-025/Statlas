"""Tests for Statlas query modules (player, team, league, dashboard, search)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class TestPlayerQueries:
    """Tests for player query functions."""

    def test_get_player_profile_unknown(self, db) -> None:
        from app.queries.player_queries import get_player_profile

        assert get_player_profile(db, 999999) is None

    def test_search_players_empty_db(self, db) -> None:
        from app.queries.player_queries import search_players

        result = search_players(db, "Haaland")
        assert isinstance(result, list)
        assert result == []

    def test_slugify_name(self) -> None:
        from app.queries.player_queries import slugify_name

        assert slugify_name("Kylian Mbappé") == "kylian-mbappe"
        assert slugify_name("Erling Haaland") == "erling-haaland"


class TestTeamQueries:
    """Tests for team query functions."""

    def test_get_team_profile_unknown(self, db) -> None:
        from app.queries.team_queries import get_team_profile

        result = get_team_profile(db, league_slug="nope", team_slug="nope")
        assert result is None


class TestLeagueQueries:
    """Tests for league query functions."""

    def test_get_league_catalog_empty_db(self, db) -> None:
        from app.queries.league_queries import get_league_catalog

        # Catalog is config-driven: every configured league appears even with
        # an empty database (teams/coverage default to zero/empty).
        result = get_league_catalog(db)
        assert isinstance(result, list)
        slugs = [row["slug"] for row in result]
        assert "premier-league" in slugs

    def test_get_league_detail_unknown(self, db) -> None:
        from app.queries.league_queries import get_league_detail

        assert get_league_detail(db, "definitely-not-a-league") is None


class TestDashboardQueries:
    """Tests for dashboard query functions."""

    def test_get_or_create_dashboard_state(self, db) -> None:
        from app.models import User
        from app.queries.dashboard_queries import get_or_create_dashboard_state_local

        user = User(email="dash@statlas.com", password_hash="x" * 64, plan="free")
        db.add(user)
        db.commit()
        db.refresh(user)

        state = get_or_create_dashboard_state_local(db, user.id)
        assert state.user_id == user.id
        # Second call returns the same row (get-or-create is idempotent).
        again = get_or_create_dashboard_state_local(db, user.id)
        assert again.id == state.id


class TestSearchExecution:
    """Tests for structured search execution (validation + empty data)."""

    def test_execute_structured_query_requires_condition(self, db) -> None:
        from app.queries.structured_search import InvalidQuery, execute_structured_query

        with pytest.raises(InvalidQuery):
            execute_structured_query(db, {"conditions": []})

    def test_execute_structured_query_no_season_data(self, db) -> None:
        from app.queries.structured_search import InvalidQuery, execute_structured_query

        with pytest.raises(InvalidQuery, match="season"):
            execute_structured_query(
                db,
                {
                    "conditions": [
                        {
                            "metric": "si_gls_p90",
                            "operator": "percentile_gte",
                            "value": 50,
                        }
                    ]
                },
            )

    def test_mock_db_is_untouched_by_import(self) -> None:
        # Guard: the module imports cleanly (guards the historical circular
        # import between search_execution and structured_search).
        from app.queries import search_execution

        assert search_execution.execute_structured_query is not None


class TestMagicMockQueries:
    """Smoke tests: query modules import cleanly and accept mock sessions."""

    def test_player_queries_module_loads(self) -> None:
        from app.queries import player_queries

        assert callable(player_queries.search_players)
        assert callable(player_queries.get_player_profile)

    def test_team_queries_module_loads(self) -> None:
        from app.queries import team_queries

        assert callable(team_queries.get_team_profile)

    def test_league_queries_module_loads(self) -> None:
        from app.queries import league_queries

        assert callable(league_queries.get_league_catalog)
        assert callable(league_queries.get_league_detail)

    def test_dashboard_queries_module_loads(self) -> None:
        from app.queries import dashboard_queries

        assert callable(dashboard_queries.get_or_create_dashboard_state_local)

    def test_magicmock_session_accepted(self) -> None:
        from app.queries.player_queries import search_players

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        result = search_players(db, "Haaland")
        assert isinstance(result, list)
