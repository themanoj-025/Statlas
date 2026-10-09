"""Statlas data-source layer.

Every source implements the `StatsSource` interface from `sources.base` so the
ingestion orchestration (and all downstream consumers) never depends on which
provider produced the data — the swappable-source architecture required by
Constitution §4. Migrating from scraped FBref to a licensed feed later is an
implementation swap, not a rearchitecture.
"""
