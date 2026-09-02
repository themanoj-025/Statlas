"""Tests for app.api.schemas — Pydantic response models."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestErrorSchemas:
    """ErrorDetail and ErrorResponse models."""

    def test_error_detail(self) -> None:
        from app.api.schemas import ErrorDetail
        e = ErrorDetail(code="not_found", message="Player not found")
        assert e.code == "not_found"
        assert e.message == "Player not found"

    def test_error_response(self) -> None:
        from app.api.schemas import ErrorDetail, ErrorResponse
        r = ErrorResponse(error=ErrorDetail(code="err", message="msg"))
        assert r.error.code == "err"

    def test_error_detail_forbids_extra(self) -> None:
        from app.api.schemas import ErrorDetail
        with pytest.raises(Exception):
            ErrorDetail(code="e", message="m", extra_field="bad")  # type: ignore[arg-type]


class TestLeaderboardSchemas:
    """LeaderboardEntry and LeaderboardResponse models."""

    def test_leaderboard_entry(self) -> None:
        from app.api.schemas import LeaderboardEntry
        from datetime import datetime, timezone
        e = LeaderboardEntry(
            player_id=1,
            name="Test Player",
            position_group="FWD",
            minutes=900,
            value=85.0,
            snapshot_date=datetime.now(timezone.utc),
        )
        assert e.player_id == 1
        assert e.name == "Test Player"

    def test_leaderboard_response(self) -> None:
        from app.api.schemas import LeaderboardResponse, LeaderboardEntry
        from datetime import datetime, timezone
        e = LeaderboardEntry(
            player_id=1, name="P", position_group="MID", minutes=100, value=50.0
        )
        r = LeaderboardResponse(entries=[e], total=1, limit=10, offset=0, has_more=False)
        assert r.total == 1
        assert len(r.entries) == 1
        assert r.has_more is False


class TestPlayerProfileSchema:
    """PlayerProfile allows extra fields (dynamic keys)."""

    def test_player_profile(self) -> None:
        from app.api.schemas import PlayerProfile
        p = PlayerProfile(player_id=1, name="Test", extra_field="allowed")
        assert p.player_id == 1
        assert p.extra_field == "allowed"
