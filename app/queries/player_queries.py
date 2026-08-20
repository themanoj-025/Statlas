"""Player queries — internal functions for the Phase 2 player profile page.

All reads filter `is_published = true`: values with unresolved anomalies are
never served, and percentile values carry their snapshot date so the UI can
render the recency line ("Data as of … · computed on …").
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import PercentileSnapshot, Player, StatSnapshot


def get_player_profile(db: Session, player_id: int) -> dict[str, Any] | None:
    """Basic profile facts for the header block."""
    player = db.get(Player, player_id)
    if player is None:
        return None
    from app.models import Team

    team = db.get(Team, player.current_team_id) if player.current_team_id else None
    return {
        "player_id": player.id,
        "name": player.canonical_name,
        "date_of_birth": player.date_of_birth,
        "nationality": player.nationality,
        "position_group": player.position_group,
        "primary_position": player.primary_position,
        "current_team": team.name if team else None,
        "external_ids": player.external_ids or {},
    }


def get_player_percentiles(
    db: Session,
    player_id: int,
    *,
    snapshot_date: datetime | None = None,
    only_published: bool = True,
) -> dict[str, Any] | None:
    """Latest published percentile + index snapshot for a player.

    Returns {"snapshot_date", "computed_date", "percentiles": {metric: value},
    "index": float|None} or None when the player has no published snapshot.

    Blocking semantics (documented, not silent): rows published BEFORE an
    anomaly was flagged stay queryable — the anomaly block stops NEW
    computation (compute_percentiles excludes blocked players from pools), it
    does not retroactively unpublish rows that already passed the gate. A
    player blocked at the latest scrape therefore shows their last cleanly
    published values, with the recency line carrying that snapshot's date.
    """
    registry = load_registry()
    index_id = registry["index_metric_id"]

    query = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(StatSnapshot.player_id == player_id)
    )
    if only_published:
        query = query.filter(PercentileSnapshot.is_published.is_(True))
    if snapshot_date is not None:
        query = query.filter(StatSnapshot.scrape_date == snapshot_date)
    rows = query.order_by(StatSnapshot.scrape_date.desc(), PercentileSnapshot.id).all()

    if not rows:
        return None

    latest_scrape = rows[0][1].scrape_date
    latest_rows = [row for row in rows if row[1].scrape_date == latest_scrape]

    percentiles: dict[str, float] = {}
    index: float | None = None
    computed_dates: set[datetime] = set()
    for percentile, _snap in latest_rows:
        computed_dates.add(percentile.computed_date)
        if percentile.metric_name == index_id:
            index = percentile.index_score
        elif percentile.percentile_value is not None:
            percentiles[percentile.metric_name] = percentile.percentile_value

    return {
        "snapshot_date": latest_scrape,
        "computed_date": max(computed_dates) if computed_dates else None,
        "percentiles": percentiles,
        "index": index,
    }


# ---------------------------------------------------------------------------
# Phase 2 additions: slug resolution, search, raw stats
# ---------------------------------------------------------------------------


def slugify_name(name: str) -> str:
    """Deterministic URL slug from a display name (site-map.md §2).

    Lowercase, diacritics stripped, non-alphanumeric runs -> single hyphen.
    """
    import re
    import unicodedata

    ascii_ = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")
    return slug or "player"


def player_slug_map(db: Session) -> list[dict[str, Any]]:
    """All players with their computed canonical slug (site-map.md §1.1).

    Slug rules: name slug; `-{club-slug}` on collision; `-{id}` last resort.
    Computed over the whole player table so collision detection is exact.
    """
    from app.models import Team

    rows = (
        db.query(Player, Team).outerjoin(Team, Player.current_team_id == Team.id).all()
    )
    by_name_slug: dict[str, list[dict[str, Any]]] = {}
    players: list[dict[str, Any]] = []
    for player, team in rows:
        club_slug = slugify_name(team.name) if team else ""
        entry = {
            "player_id": player.id,
            "name": player.canonical_name,
            "name_slug": slugify_name(player.canonical_name),
            "club_slug": club_slug,
            "slug": "",
        }
        players.append(entry)
        by_name_slug.setdefault(entry["name_slug"], []).append(entry)

    for entry in players:
        same_name = by_name_slug[entry["name_slug"]]
        if len(same_name) == 1:
            entry["slug"] = entry["name_slug"]
        elif (
            entry["club_slug"]
            and sum(1 for p in same_name if p["club_slug"] == entry["club_slug"]) == 1
        ):
            entry["slug"] = f"{entry['name_slug']}-{entry['club_slug']}"
        else:
            entry["slug"] = f"{entry['name_slug']}-{entry['player_id']}"
    return players


def get_player_slug(
    db: Session,
    player_id: int,
    *,
    slug_map: list[dict[str, Any]] | None = None,
) -> str | None:
    """Canonical slug for one player (None when the player does not exist).

    `slug_map` lets callers reuse one `player_slug_map(db)` build across many
    lookups instead of rebuilding it per player (O(N^2) on large pools).
    """
    for entry in slug_map or player_slug_map(db):
        if entry["player_id"] == player_id:
            return entry["slug"]
    return None


def resolve_player_slug(db: Session, slug: str) -> dict[str, Any] | None:
    """Resolve a requested player slug to a player + canonical slug.

    Returns {"player_id", "canonical_slug", "canonical"} — `canonical=False`
    means the requested slug is a non-canonical form and the caller should 301
    to the canonical URL (site-map.md §4). None when nothing matches.
    """
    players = player_slug_map(db)
    by_slug = {p["slug"]: p for p in players}
    if slug in by_slug:
        p = by_slug[slug]
        return {
            "player_id": p["player_id"],
            "canonical_slug": p["slug"],
            "canonical": True,
        }

    # Non-canonical but valid forms, matched against the KNOWN candidate shapes
    # ({name}-{club}, {name}-{id}) rather than parsing the requested slug —
    # rpartition-based parsing mis-splits multi-hyphen slugs like
    # 'player-a-manchester-city' (base would read 'player-a-manchester').
    for p in players:
        if (
            slug == f"{p['name_slug']}-{p['club_slug']}"
            or slug == f"{p['name_slug']}-{p['player_id']}"
        ):
            return {
                "player_id": p["player_id"],
                "canonical_slug": p["slug"],
                "canonical": False,
            }

    # Bare name slug that matches exactly one player (typed without a required
    # club suffix). Ambiguous names (collisions) resolve to None — never a guess.
    name_matches = [p for p in players if p["name_slug"] == slug]
    if len(name_matches) == 1:
        return {
            "player_id": name_matches[0]["player_id"],
            "canonical_slug": name_matches[0]["slug"],
            "canonical": False,
        }
    return None


def search_players(
    db: Session,
    query: str,
    *,
    limit: int = 8,
    include_unqualified: bool = True,
) -> list[dict[str, Any]]:
    """Search-as-you-type against canonical names AND aliases (reconciliation's
    spelling store), so alternate spellings still resolve (Phase 2 B3).

    Returns identity + disambiguation context (club, league, position) since
    common names collide. `include_unqualified` keeps below-threshold players
    in results (they have profile pages with the pending-qualification state).
    """
    from app.models import League, PlayerNameAlias, Team

    q = query.strip().lower()
    if not q:
        return []
    # Escape ILIKE wildcards in user input to prevent unintended matches.
    # SQLAlchemy ilike(escape='\') tells the DB to treat \% and \_ as literals.
    escape_char = "\\"
    escaped = q.replace("%", f"{escape_char}%").replace("_", f"{escape_char}_")
    pattern = f"%{escaped}%"

    player_rows = db.query(Player).filter(
        Player.canonical_name.ilike(pattern, escape=escape_char)
    ).all()
    alias_rows = (
        db.query(PlayerNameAlias)
        .filter(PlayerNameAlias.source_name_string.ilike(pattern, escape=escape_char))
        .all()
    )
    matched: dict[int, Player] = {p.id: p for p in player_rows}
    for alias in alias_rows:
        matched.setdefault(alias.player_id, alias.player)

    if not matched:
        return []

    # Only load teams/leagues for matched players (not ALL teams/leagues)
    team_ids = {p.current_team_id for p in matched.values() if p.current_team_id}
    teams: dict[int, Any] = {}
    if team_ids:
        team_rows = db.query(Team).filter(Team.id.in_(team_ids)).all()
        teams = {t.id: t for t in team_rows}
    league_ids = {t.league_id for t in teams.values() if t.league_id}
    leagues: dict[int, Any] = {}
    if league_ids:
        league_rows = db.query(League).filter(League.id.in_(league_ids)).all()
        leagues = {l.id: l for l in league_rows}

    # Compute slugs only for matched players (not the full player table)
    matched_ids = list(matched.keys())
    slug_map = _compact_slug_map(db, matched_ids, matched, teams)

    results: list[dict[str, Any]] = []
    for player in matched.values():
        team = teams.get(player.current_team_id)
        league = leagues.get(team.league_id) if team else None
        results.append(
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "slug": slug_map.get(player.id),
                "position_group": player.position_group,
                "position_label": player.primary_position,
                "club": team.name if team else None,
                "league": league.name if league else None,
                "league_slug": league.slug if league else None,
                "nationality": player.nationality,
            }
        )

    # name-prefix matches rank above mid-name matches; then alphabetical.
    def _rank(p: dict[str, Any]) -> tuple[int, str]:
        lower = p["name"].lower()
        return (0 if lower.startswith(q) else 1, lower)

    results.sort(key=_rank)
    return results[:limit]


def _compact_slug_map(
    db: Session,
    player_ids: list[int],
    matched: dict[int, Player],
    teams: dict[int, Any],
) -> dict[int, str]:
    """Compute slugs for a small set of matched players without loading the
    full player table. Handles name collisions via club suffix.
    """
    # Group by name slug to detect collisions
    by_name_slug: dict[str, list[int]] = {}
    for pid in player_ids:
        player = matched[pid]
        name_slug = slugify_name(player.canonical_name)
        by_name_slug.setdefault(name_slug, []).append(pid)

    result: dict[int, str] = {}
    for name_slug, pids in by_name_slug.items():
        if len(pids) == 1:
            result[pids[0]] = name_slug
            continue
        # Multiple players with same name — try club disambiguation
        club_slugs: dict[str, list[int]] = {}
        for pid in pids:
            team = teams.get(matched[pid].current_team_id)
            cs = slugify_name(team.name) if team else ""
            club_slugs.setdefault(cs, []).append(pid)
        for cs, cs_pids in club_slugs.items():
            if len(cs_pids) == 1 and cs:
                result[cs_pids[0]] = f"{name_slug}-{cs}"
            else:
                for pid in cs_pids:
                    result[pid] = f"{name_slug}-{pid}"
    return result


def get_player_raw_stats(db: Session, player_id: int) -> dict[str, Any] | None:
    """Latest snapshot's raw per-90 values + sample context (minutes, matches,
    season, source, team, recency). The key-stat summary table's data source
    (site-map.md: "real per-90 values from the latest stat_snapshot").
    """
    from app.models import League, Team

    snap = (
        db.query(StatSnapshot)
        .filter(StatSnapshot.player_id == player_id)
        .order_by(StatSnapshot.scrape_date.desc(), StatSnapshot.id.desc())
        .first()
    )
    if snap is None:
        return None
    team = db.get(Team, snap.team_id) if snap.team_id else None
    league = db.get(League, snap.league_id) if snap.league_id else None
    return {
        "snapshot_date": snap.scrape_date,
        "season": snap.season,
        "source": snap.source,
        "minutes_played": snap.minutes_played,
        "matches_played": snap.matches_played,
        "team_id": snap.team_id,
        "team": team.name if team else None,
        "league": league.name if league else None,
        "league_slug": league.slug if league else None,
        "league_tier": league.tier if league else None,
        "raw_stats": snap.raw_stats or {},
    }
