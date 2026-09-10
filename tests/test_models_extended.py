"""Tests for Statlas domain models (ORM construction + constraint surface)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import League, Player, Report, Shortlist, Team

pytestmark = pytest.mark.unit


class TestPlayerModel:
    """Tests for the Player ORM model."""

    def test_player_creation(self, db: Session) -> None:
        from tests.test_tactical import _make_league, _make_team

        league = _make_league(db)
        team = _make_team(db, league)
        p = Player(
            canonical_name="Test Player",
            nationality="England",
            position_group="CM",
            current_team_id=team.id,
        )
        db.add(p)
        db.flush()
        assert p.id is not None
        assert p.canonical_name == "Test Player"
        assert p.position_group == "CM"
        assert p.external_ids == {} or p.external_ids is not None

    def test_player_default_external_ids(self, db: Session) -> None:
        p = Player(canonical_name="Test")
        db.add(p)
        db.flush()
        assert isinstance(p.external_ids, dict)

    def test_player_optional_fields(self, db: Session) -> None:
        p = Player(
            canonical_name="Test",
            date_of_birth=datetime(2000, 1, 1, tzinfo=timezone.utc),
            transfermarkt_id=418560,
        )
        db.add(p)
        db.flush()
        assert p.transfermarkt_id == 418560
        assert p.current_team_id is None


class TestTeamModel:
    """Tests for the Team ORM model."""

    def test_team_creation(self, db: Session) -> None:
        league = League(
            slug="test-league",
            name="Test League",
            country="England",
            tier="tier_1",
        )
        db.add(league)
        db.flush()
        t = Team(name="Arsenal", league_id=league.id, external_ids={})
        db.add(t)
        db.flush()
        assert t.name == "Arsenal"
        assert t.league_id == league.id

    def test_team_optional_fields(self, db: Session) -> None:
        league = League(
            slug="test-league-2",
            name="Test League 2",
            country="Spain",
            tier="tier_1",
        )
        db.add(league)
        db.flush()
        t = Team(
            name="Barcelona",
            league_id=league.id,
            external_ids={},
            founded_year=1899,
        )
        db.add(t)
        db.flush()
        assert t.founded_year == 1899
        assert t.logo_url is None


class TestReportModel:
    """Tests for the Report ORM model."""

    def test_report_creation(self, db: Session) -> None:
        from app.models import User

        league = League(
            slug="test-league-3",
            name="Test League 3",
            country="England",
            tier="tier_1",
        )
        db.add(league)
        db.flush()
        team = Team(name="Arsenal FC", league_id=league.id, external_ids={})
        db.add(team)
        db.flush()
        player = Player(canonical_name="Bukayo Saka", current_team_id=team.id)
        db.add(player)
        user = User(email="reporter@statlas.com", password_hash="x" * 64, plan="pro")
        db.add(user)
        db.flush()

        r = Report(
            user_id=user.id,
            player_id=player.id,
            data_snapshot_date=datetime.now(timezone.utc),
            report_json={"sections": {"overview": {"text": "Good player"}}},
        )
        db.add(r)
        db.flush()
        assert r.status == "generated"
        assert r.report_json["sections"]["overview"]["text"] == "Good player"
        assert r.visibility == "personal"

    def test_report_defaults(self, db: Session) -> None:
        from app.models import User

        league = League(
            slug="test-league-4",
            name="Test League 4",
            country="England",
            tier="tier_1",
        )
        db.add(league)
        db.flush()
        team = Team(name="Arsenal FC2", league_id=league.id, external_ids={})
        db.add(team)
        db.flush()
        player = Player(canonical_name="Bukayo Saka 2", current_team_id=team.id)
        db.add(player)
        user = User(email="reporter2@statlas.com", password_hash="x" * 64, plan="pro")
        db.add(user)
        db.flush()

        r = Report(
            user_id=user.id,
            player_id=player.id,
            data_snapshot_date=datetime.now(timezone.utc),
            report_json={},
        )
        db.add(r)
        db.flush()
        assert isinstance(r.verification_log, dict)
        assert r.verification_log == {}


class TestWorkspaceModel:
    """Tests for the workspace (shortlist) models."""

    def test_shortlist_creation(self, db: Session) -> None:
        from app.models import User

        user = User(email="scout-ws@statlas.com", password_hash="x" * 64, plan="free")
        db.add(user)
        db.flush()

        ws = Shortlist(user_id=user.id, name="Scouting Board")
        db.add(ws)
        db.flush()
        assert ws.name == "Scouting Board"
        assert ws.visibility == "personal"

    def test_shortlist_defaults(self, db: Session) -> None:
        from app.models import User

        user = User(email="scout-ws2@statlas.com", password_hash="x" * 64, plan="free")
        db.add(user)
        db.flush()

        ws = Shortlist(user_id=user.id, name="Transfer Targets")
        db.add(ws)
        db.flush()
        assert ws.deleted_at is None
        assert ws.restricted_access is None


class TestCacheModule:
    """Tests for the in-process cache backend (see test_cache.py for the full suite)."""

    def test_cache_set_get(self) -> None:
        from app.cache import InMemoryCacheBackend

        cache = InMemoryCacheBackend()
        cache.set("key1", "value1", ttl=60)
        assert cache.get("key1") == "value1"

    def test_cache_miss(self) -> None:
        from app.cache import InMemoryCacheBackend

        cache = InMemoryCacheBackend()
        assert cache.get("nonexistent") is None

    def test_cache_delete(self) -> None:
        from app.cache import InMemoryCacheBackend

        cache = InMemoryCacheBackend()
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None
