"""Market data source interface and fixture implementation (Phase 15).

Constitution §4: The data-source layer is modular/swappable — scraper
functions behind an interface, so migrating to a licensed feed later does
not require rearchitecting.

Constitution §3: Every ingestion job is idempotent — re-running does not
duplicate or corrupt data.

This module defines:
- MarketDataSource: ABC for market data providers (like StatsSource for stats)
- FixtureMarketDataSource: synthetic fixture data for dev/test (no API keys)
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MarketValuationRecord:
    """Normalized market valuation from any source."""

    player_id: int
    source: str
    valuation_amount_eur: float
    valuation_date: datetime
    low_range: float | None = None
    high_range: float | None = None
    confidence_level: str = "medium"
    raw: dict = field(default_factory=dict)


@dataclass
class TransferRecord:
    """Normalized transfer record from any source."""

    player_id: int
    from_team_id: int | None
    to_team_id: int
    transfer_date: datetime
    reported_fee_eur: float | None
    transfer_type: str
    status: str
    source: str
    raw: dict = field(default_factory=dict)


@dataclass
class ContractRecord:
    """Normalized contract status from any source."""

    player_id: int
    current_team_id: int | None
    contract_end_date: datetime | None
    contract_value_per_year_eur: float | None
    contract_status: str
    source: str
    snapshot_date: datetime
    raw: dict = field(default_factory=dict)


class MarketDataSource(ABC):
    """Abstract base class for market data sources.

    Every source implements fetch_valuations, fetch_transfers, fetch_contracts
    so the ingestion orchestration never depends on which provider produced
    the data.
    """

    @abstractmethod
    def fetch_valuations(
        self, player_ids: list[int], as_of: datetime
    ) -> list[MarketValuationRecord]:
        """Fetch current market valuations for specified players."""
        ...

    @abstractmethod
    def fetch_transfers(self, since: datetime) -> list[TransferRecord]:
        """Fetch transfer records since a given date."""
        ...

    @abstractmethod
    def fetch_contracts(
        self, player_ids: list[int], as_of: datetime
    ) -> list[ContractRecord]:
        """Fetch contract status for specified players."""
        ...


class FixtureMarketDataSource(MarketDataSource):
    """Synthetic fixture data for dev/test — no API keys, no network.

    Generates realistic-looking market data based on player attributes
    (position, age, team) without calling any external API.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def fetch_valuations(
        self, player_ids: list[int], as_of: datetime
    ) -> list[MarketValuationRecord]:
        """Generate synthetic valuations based on player attributes."""
        records = []
        for pid in player_ids:
            # Deterministic valuation based on player_id
            base_val = self._rng.uniform(5_000_000, 80_000_000)
            confidence = self._rng.choice(["high", "medium", "low"])
            low = base_val * 0.8 if confidence != "high" else base_val * 0.9
            high = base_val * 1.2 if confidence != "high" else base_val * 1.1
            records.append(
                MarketValuationRecord(
                    player_id=pid,
                    source="transfermarkt",
                    valuation_amount_eur=round(base_val, 2),
                    valuation_date=as_of,
                    low_range=round(low, 2),
                    high_range=round(high, 2),
                    confidence_level=confidence,
                    raw={"fixture": True},
                )
            )
        return records

    def fetch_transfers(self, since: datetime) -> list[TransferRecord]:
        """No synthetic transfers in fixture mode."""
        return []

    def fetch_contracts(
        self, player_ids: list[int], as_of: datetime
    ) -> list[ContractRecord]:
        """Generate synthetic contract statuses."""
        records = []
        for pid in player_ids:
            status = self._rng.choice(
                ["active", "active", "active", "expiring_next_season"]
            )
            years_left = 4 if status == "active" else 1
            end = datetime(as_of.year + years_left, 6, 30, tzinfo=timezone.utc)
            salary = self._rng.uniform(500_000, 10_000_000)
            records.append(
                ContractRecord(
                    player_id=pid,
                    current_team_id=None,  # resolved by ingestion
                    contract_end_date=end,
                    contract_value_per_year_eur=round(salary, 2),
                    contract_status=status,
                    source="transfermarkt",
                    snapshot_date=as_of,
                    raw={"fixture": True},
                )
            )
        return records
