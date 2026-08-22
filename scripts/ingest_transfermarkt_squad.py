#!/usr/bin/env python3
"""Bulk ingestion: scrape all players from a Transfermarkt league squad page.

For each club in the league, this script:
1. Fetches the squad page listing all players
2. Extracts name, TM ID, position, age, contract, and market value
3. Optionally fetches detailed profiles (DOB, nationality, height) per player
4. Upserts everything into the Player model with transfermarkt_id

Usage:
    # Single league, current season
    python scripts/ingest_transfermarkt_squad.py --league premier-league

    # Specific season
    python scripts/ingest_transfermarkt_squad.py --league la-liga --season 2025-26

    # Multiple leagues
    python scripts/ingest_transfermarkt_squad.py --league premier-league,la-liga

    # All leagues (19 leagues, ~15 min due to rate limits)
    python scripts/ingest_transfermarkt_squad.py --all

    # Dry-run: scrape and print, no DB writes
    python scripts/ingest_transfermarkt_squad.py --league premier-league --dry-run

    # With profile detail fetch (slower: 5s per player for DOB/nationality)
    python scripts/ingest_transfermarkt_squad.py --league premier-league --profiles

Environment variables:
    DATABASE_URL             -- target database (default: SQLite at data/dev.db)
    STATLAS_LOG_LEVEL        -- logging verbosity (default: INFO)
"""

from __future__ import annotations

import argparse
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Any

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings, load_tiers
from app.sources.transfermarkt import (
    LEAGUE_URL_SLUGS,
    TransfermarktSource,
    _parse_market_value,
)

logger = logging.getLogger("tm_squad")

# All leagues with Transfermarkt codes
ALL_LEAGUES = sorted(LEAGUE_URL_SLUGS.keys())


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Bulk scrape Transfermarkt squad pages into the database."
    )
    p.add_argument(
        "--league", "-l",
        help="Comma-separated league slugs (e.g. premier-league,la-liga)",
    )
    p.add_argument(
        "--all", "-a",
        action="store_true",
        help="Scrape all 19 leagues in tiers.json",
    )
    p.add_argument(
        "--season", "-s",
        help="Season in YYYY-YY format (default: current)",
    )
    p.add_argument(
        "--profiles",
        action="store_true",
        help="Also fetch individual player profiles for DOB/nationality/height",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and print without writing to DB",
    )
    p.add_argument(
        "--list-leagues",
        action="store_true",
        help="Print available league slugs and exit",
    )
    return p.parse_args()


def position_to_group(pos: str) -> str | None:
    """Map Transfermarkt position string to PositionGroup enum.

    Enum values: GK, CB, FB, DM, CM, AM, W, ST
    """
    pos_lower = pos.lower()
    if "goalkeeper" in pos_lower or "torwart" in pos_lower:
        return "GK"
    # Centre-back
    if any(x in pos_lower for x in ("centre-back", "center-back")):
        return "CB"
    # Full-back (left/right back, wing-back)
    if any(x in pos_lower for x in (
        "left-back", "right-back", "full-back", "wing-back",
        "aussenverteidiger",
    )):
        return "FB"
    # Defensive midfield
    if "defensive mid" in pos_lower or "defensives mittelfeld" in pos_lower:
        return "DM"
    # Central midfield
    if any(x in pos_lower for x in ("central mid", "zentrales mittelfeld")):
        return "CM"
    # Attacking midfield
    if any(x in pos_lower for x in (
        "attacking mid", "offensives mittelfeld", "playmaker",
    )):
        return "AM"
    # Winger
    if any(x in pos_lower for x in (
        "left wing", "right wing", "winger",
        "links", "rechts", "ausen",
    )):
        return "W"
    # Striker / forward
    if any(x in pos_lower for x in (
        "centre-forward", "center-forward", "striker",
        "forward", "attack", "mittelstuermer",
    )):
        return "ST"
    return None


def upsert_players(
    db, players: list[dict[str, Any]], source_label: str
) -> tuple[int, int]:
    """Upsert a list of player dicts into the Player table.

    Returns (created_count, updated_count).
    """
    from app.models.player import Player

    created = 0
    updated = 0

    for p in players:
        tm_id = p.get("transfermarkt_id")
        if not tm_id:
            continue

        existing = None
        if tm_id:
            existing = db.query(Player).filter(Player.transfermarkt_id == tm_id).first()

        if existing:
            # Update fields that are currently None
            changed = False
            if not existing.nationality and p.get("nationality"):
                existing.nationality = p["nationality"]
                changed = True
            if not existing.date_of_birth and p.get("date_of_birth"):
                existing.date_of_birth = p["date_of_birth"]
                changed = True
            if not existing.primary_position and p.get("position"):
                existing.primary_position = p["position"]
                changed = True
            pg = position_to_group(p.get("position", ""))
            if pg and not existing.position_group:
                existing.position_group = pg
                changed = True
            # Always update external_ids with transfermarkt
            ext = dict(existing.external_ids or {})
            if ext.get("transfermarkt") != tm_id:
                ext["transfermarkt"] = tm_id
                existing.external_ids = ext
                changed = True
            if changed:
                updated += 1
        else:
            ext_ids = {"transfermarkt": tm_id}
            pg = position_to_group(p.get("position", ""))
            player = Player(
                canonical_name=p["name"],
                transfermarkt_id=tm_id,
                external_ids=ext_ids,
                primary_position=p.get("position") or None,
                position_group=pg,
                nationality=p.get("nationality") or None,
                date_of_birth=p.get("date_of_birth"),
            )
            db.add(player)
            created += 1

    db.flush()
    return created, updated


def fetch_profile_detail(
    src: TransfermarktSource, tm_id: int
) -> dict[str, Any]:
    """Fetch a player's profile page for DOB, nationality, height."""
    from datetime import date as date_cls

    try:
        profile_url = f"https://www.transfermarkt.com/profil/spieler/{tm_id}"
        # Use the resolve approach: we need the slug
        # For profile fetch we just use the CEAPI + profile combo
        # The profile page needs a slug, so we search for it
        slug = src._resolve_slug(tm_id)
        if not slug:
            return {}
        full_url = f"https://www.transfermarkt.com/{slug}/profil/spieler/{tm_id}"
        soup = src._soup(full_url)
        profile = src._parse_player_profile(soup)

        result: dict[str, Any] = {}
        dob_text = profile.get("date of birth/age", "")
        if dob_text:
            # Format: "Jul 21, 2000 (26)" or "20/12/1998 (27)"
            import re as _re
            m = _re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})", dob_text)
            if m:
                for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(m.group(1), fmt)
                        result["date_of_birth"] = dt.date()
                        break
                    except ValueError:
                        continue

        nationality = profile.get("citizenship") or profile.get("nationality")
        if nationality:
            result["nationality"] = nationality

        height = profile.get("height")
        if height:
            result["height"] = height

        return result
    except Exception as exc:
        logger.debug("Profile fetch failed for TM %s: %s", tm_id, exc)
        return {}


def run(args: argparse.Namespace) -> None:
    tiers = load_tiers()
    src = TransfermarktSource()

    # Determine leagues to process
    if args.all:
        leagues = ALL_LEAGUES
    elif args.league:
        leagues = [s.strip() for s in args.league.split(",")]
    else:
        print("Error: specify --league or --all")
        sys.exit(1)

    # Validate leagues
    for lg in leagues:
        if lg not in LEAGUE_URL_SLUGS:
            print(f"Error: unknown league '{lg}'")
            print(f"Available: {', '.join(ALL_LEAGUES)}")
            sys.exit(1)

    season = args.season
    logger.info(
        "Transfermarkt squad ingestion: %d leagues, season=%s, profiles=%s",
        len(leagues), season or "current", args.profiles,
    )

    all_players: list[dict[str, Any]] = []

    for i, lg in enumerate(leagues, 1):
        logger.info("[%d/%d] Scraping %s ...", i, len(leagues), lg)
        try:
            players = src.fetch_squad_players(lg, season=season)
            all_players.extend(players)
            logger.info("  %s: %d players scraped", lg, len(players))
        except Exception as exc:
            logger.error("  %s FAILED: %s", lg, exc)

    if not all_players:
        logger.warning("No players scraped. Exiting.")
        return

    logger.info("Total players scraped: %d", len(all_players))

    # Optionally fetch profile details
    if args.profiles and not args.dry_run:
        logger.info("Fetching profile details for %d players ...", len(all_players))
        for i, p in enumerate(all_players, 1):
            tm_id = p.get("transfermarkt_id")
            if not tm_id:
                continue
            if i % 50 == 0:
                logger.info("  Progress: %d/%d", i, len(all_players))
            detail = fetch_profile_detail(src, tm_id)
            p.update(detail)

    if args.dry_run:
        # Use replace to handle Windows console encoding issues
        import io
        out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        out.write(f"\n{'=' * 70}\n")
        out.write(f"DRY RUN: {len(all_players)} players scraped\n")
        out.write(f"{'=' * 70}\n")
        # Print summary by club
        clubs: dict[str, list] = {}
        for p in all_players:
            clubs.setdefault(p["club_name"], []).append(p)
        for club_name, club_players in sorted(clubs.items()):
            out.write(f"\n{club_name} ({len(club_players)} players):\n")
            for p in club_players[:5]:
                mv = p.get("market_value_text", "N/A")
                pos = p.get("position", "?")
                age = p.get("age", "?")
                out.write(f"  {p['name']:<30} {pos:<20} Age {age:<4} {mv}\n")
            if len(club_players) > 5:
                out.write(f"  ... and {len(club_players) - 5} more\n")
        out.write(f"\n{'=' * 70}\n")
        out.flush()
        return

    # Write to database
    from app.db import session_scope

    with session_scope() as db:
        created, updated = upsert_players(db, all_players, "transfermarkt")
        logger.info("Upsert complete: %d created, %d updated", created, updated)

    # Print summary
    clubs_summary: dict[str, int] = {}
    for p in all_players:
        clubs_summary[p["club_name"]] = clubs_summary.get(p["club_name"], 0) + 1

    print(f"\n{'=' * 60}")
    print(f"TRANSFERMARKT SQUAD INGESTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total players: {len(all_players)}")
    print(f"Clubs: {len(clubs_summary)}")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"\nBy club:")
    for club, count in sorted(clubs_summary.items()):
        print(f"  {club:<30} {count} players")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args()

    if args.list_leagues:
        print("Available leagues:")
        for lg in ALL_LEAGUES:
            print(f"  {lg}")
        sys.exit(0)

    run(args)
