"""Player domain models — League, Team, Player, aliases, fixtures, emerging scores."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    POSITION_GROUP_ENUM,
    SOURCE_ENUM,
    TIER_ENUM,
    Base,
)


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[str] = mapped_column(TIER_ENUM, nullable=False)
    external_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    external_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("name", "league_id", name="uq_teams_name_league"),
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    position_group: Mapped[str | None] = mapped_column(POSITION_GROUP_ENUM, nullable=True)
    external_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_players_canonical_name", "canonical_name"),
        Index("ix_players_position_group", "position_group"),
    )


class PlayerNameAlias(Base):
    __tablename__ = "player_name_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    source: Mapped[str] = mapped_column(SOURCE_ENUM, nullable=False)
    source_name_string: Mapped[str] = mapped_column(String(128), nullable=False)
    player: Mapped[Player] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "player_id", "source", "source_name_string",
            name="uq_alias_player_source_name",
        ),
        Index("ix_aliases_source_name", "source", "source_name_string"),
    )


class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    api_fixture_id: Mapped[int] = mapped_column(Integer, nullable=False)
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    home_team_name: Mapped[str] = mapped_column(String(128), nullable=False)
    away_team_name: Mapped[str] = mapped_column(String(128), nullable=False)
    kickoff_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("api_fixture_id", name="uq_fixture_api_id"),
        Index("ix_fixtures_league_season", "league_id", "season"),
    )


class EmergingPlayerScore(Base):
    __tablename__ = "emerging_player_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    computed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    contributing_factors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    player: Mapped[Player] = relationship(lazy="selectin")
    league: Mapped[League] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "player_id", "league_id", "computed_date",
            name="uq_emerging_player_league_date",
        ),
        Index("ix_emerging_league_date", "league_id", "computed_date"),
        Index("ix_emerging_score", "league_id", "computed_date", "score"),
    )
