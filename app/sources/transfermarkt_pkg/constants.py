"""Transfermarkt constants -- base URL and league slug mappings."""

from __future__ import annotations


TRANSFERMARKT_BASE = "https://www.transfermarkt.com"

# Transfermarkt league slug -> wettbewerb code (must match tiers.json).
# Verified against live Transfermarkt URLs as of 2026-08.
LEAGUE_URL_SLUGS = {
    "premier-league": "premier-league",
    "la-liga": "laliga",
    "serie-a": "serie-a",
    "bundesliga": "bundesliga",
    "ligue-1": "ligue-1",
    "eredivisie": "eredivisie",
    "primeira-liga": "liga-portugal",
    "belgian-pro-league": "jupiler-pro-league",
    "super-lig": "super-lig",
    "scottish-premiership": "scottish-premiership",
    "austrian-bundesliga": "bundesliga",
    "swiss-super-league": "super-league",
    "greek-super-league": "super-league-1",
    "danish-superliga": "superligaen",
    "championship": "championship",
    "la-liga-2": "laliga2",
    "serie-b": "serie-b",
    "2-bundesliga": "2-bundesliga",
    "ligue-2": "ligue-2",
}

