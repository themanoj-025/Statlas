"""Transfer domain models — valuations, transfer history, contract status."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    CONTRACT_STATUS_ENUM,
    MARKET_SOURCE_ENUM,
    TRANSFER_STATUS_ENUM,
    TRANSFER_TYPE_ENUM,
    VALUATION_CONFIDENCE_ENUM,
    Base,
)


class MarketValuation(Base):
    __tablename__ = "market_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    source: Mapped[str] = mapped_column(MARKET_SOURCE_ENUM, nullable=False)
    valuation_amount_eur: Mapped[float] = mapped_column(Float, nullable=False)
    valuation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    low_range: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_range: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[str] = mapped_column(
        VALUATION_CONFIDENCE_ENUM, nullable=False, default="medium"
    )
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    player = relationship("Player")

    __table_args__ = (
        UniqueConstraint(
            "player_id", "source", "valuation_date",
            name="uq_market_valuation_player_source_date",
        ),
        Index("ix_market_valuation_player", "player_id", "valuation_date"),
        Index("ix_market_valuation_date", "valuation_date"),
    )


class TransferHistory(Base):
    __tablename__ = "transfer_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    from_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    to_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    transfer_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reported_fee_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    transfer_type: Mapped[str] = mapped_column(TRANSFER_TYPE_ENUM, nullable=False)
    status: Mapped[str] = mapped_column(TRANSFER_STATUS_ENUM, nullable=False, default="reported")
    source: Mapped[str] = mapped_column(MARKET_SOURCE_ENUM, nullable=False)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    player = relationship("Player")
    from_team = relationship("Team", foreign_keys=[from_team_id])
    to_team = relationship("Team", foreign_keys=[to_team_id])

    __table_args__ = (
        Index("ix_transfer_player", "player_id"),
        Index("ix_transfer_date", "transfer_date"),
        Index("ix_transfer_to_team", "to_team_id"),
    )


class ContractStatus(Base):
    __tablename__ = "contract_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    current_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    contract_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contract_value_per_year_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    contract_status: Mapped[str] = mapped_column(
        CONTRACT_STATUS_ENUM, nullable=False, default="active"
    )
    source: Mapped[str] = mapped_column(MARKET_SOURCE_ENUM, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    player = relationship("Player")
    current_team = relationship("Team")

    __table_args__ = (
        UniqueConstraint(
            "player_id", "source", "snapshot_date",
            name="uq_contract_status_player_source_date",
        ),
        Index("ix_contract_player", "player_id"),
    )
