"""FBref (Sports Reference) source — the primary per-90 stats provider.

Compliance posture (see data-compliance-notes.md):
- Self-imposed rate limit: 1 request per 10 seconds (+/- 2s jitter), declared
  in config via FBREF_DELAY_SECONDS / FBREF_JITTER_SECONDS and enforced by the
  RateLimiter at runtime — 40% below FBref's documented 10/minute ceiling.
- Descriptive User-Agent: StatlasAnalytics/0.1 ... (never a browser spoof).
- Aggressive local caching of raw HTML responses.
- Exponential backoff on 429/503, hard abort on 403 (never hammer a block).

Data extraction:
- The league stats page (one request per league-season) contains all stat
  tables: standard, shooting, passing, defense, possession, pressing, keepers,
  keepers_adv, playing_time. Each table is parsed with a combined header name
  (group row + column row) so FBref's duplicated column names (e.g. "xG" in
  both the totals and "Per 90 Minutes" sections) never collide.
- Every extracted field maps to a metric id in config/metric_registry.json —
  no undocumented fields are collected.
- Structural drift raises FBrefSchemaChangedError loudly instead of returning
  partial data (Constitution: fail loudly).

PRODUCTION-READINESS NOTE (per Phase 1 prompt): the parser is developed and
tested against representative fixture HTML. Before this source is declared
production-ready, run one live scrape of a real league page and confirm the
combined-header candidate lists in the metric registry against the live
column structure. FBref actively blocks scrapers; a real run must go through
the declared limiter and cache.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from app.config import get_settings, load_registry, load_tiers
from app.sources.base import (
    HttpCache,
    RateLimiter,
    RawPlayerStatRecord,
    SchemaChangedError,
    StatsSource,
    fetch_with_retry,
)

logger = logging.getLogger(__name__)

FBREF_BASE = "https://fbref.com"

# Canonical league slug -> FBref URL slug. VERIFY against a live page during the
# production-readiness pass (the fbref_comp id is the authoritative key).
FBREF_URL_SLUGS = {
    "premier-league": "Premier-League",
    "la-liga": "La-Liga",
    "serie-a": "Serie-A",
    "bundesliga": "Bundesliga",
    "ligue-1": "Ligue-1",
    "eredivisie": "Eredivisie",
    "primeira-liga": "Primeira-Liga",
    "belgian-pro-league": "Belgian-Pro-League",
    "super-lig": "Super-Lig",
    "scottish-premiership": "Scottish-Premiership",
    "austrian-bundesliga": "Austrian-Bundesliga",
    "swiss-super-league": "Swiss-Super-League",
    "greek-super-league": "Greek-Super-League",
    "danish-superliga": "Danish-Superliga",
    "championship": "Championship",
    "la-liga-2": "Segunda-Division",
    "serie-b": "Serie-B",
    "2-bundesliga": "2-Bundesliga",
    "ligue-2": "Ligue-2",
}

# The stat tables parsed from one league stats page.
FBREF_TABLES = [
    "stats_standard",
    "stats_shooting",
    "stats_passing",
    "stats_defense",
    "stats_possession",
    "stats_pressing",
    "stats_keepers",
    "stats_keeper_adv",
    "stats_playing_time",
]
REQUIRED_TABLES = ["stats_standard", "stats_playing_time"]

# Registry table names -> actual FBref table ids. Most map by simple prefix
# ("standard" -> "stats_standard"), but the advanced goalkeeper table is
# 'stats_keeper_adv' (no 's') while the registry calls it 'keepers_adv'.
FBREF_TABLE_IDS = {"keepers_adv": "stats_keeper_adv"}


def fbref_table_id(table_name: str) -> str:
    """Map a registry table name to the real FBref table id."""
    return FBREF_TABLE_IDS.get(table_name, f"stats_{table_name}")


# Fallback Pos-code -> position group mapping (methodology.md §3).
POSITION_GROUP_MAP = {
    "GK": "GK",
    "DF": "CB",
    "DF,MF": "FB",
    "MF": "CM",
    "MF,FW": "AM",
    "FW": "ST",
    "FW,MF": "W",
}

_PLAYER_ID_RE = re.compile(r"/en/players/([0-9a-f]{8})/")
_TEAMS_AGGREGATE_ROWS = {"2 teams", "3 teams", "4 teams", "5 teams"}


class FBrefSchemaChangedError(SchemaChangedError):
    """FBref's page structure changed in a way the parser refuses to guess at."""


def canonical_season_to_fbref(season: str) -> str:
    """'2025-26' -> '2025-2026' (FBref URL format)."""
    start, _, end = season.partition("-")
    return f"{start}-20{end}" if end else season


def _expand_colspans(tr: Any) -> list[str]:
    """Return the header texts expanded by colspan, e.g. ['Standard']*4."""
    out: list[str] = []
    for th in tr.find_all(["th", "td"]):
        colspan = int(th.get("colspan", "1") or 1)
        text = th.get_text(strip=True)
        out.extend([text] * colspan)
    return out


def parse_fbref_table(
    soup: BeautifulSoup, table_id: str
) -> list[dict[str, Any]] | None:
    """Parse one FBref table into a list of row dicts with combined header names.

    Combined names are "<group> <column>" so duplicates across sections are
    distinguishable (e.g. "Expected xG" vs "Per 90 Minutes xG").
    """
    table = soup.find("table", id=table_id)
    if table is None:
        return None

    thead = table.find("thead")
    if thead is None:
        raise FBrefSchemaChangedError(f"table '{table_id}' has no <thead>")

    header_rows = thead.find_all("tr")
    if not header_rows:
        raise FBrefSchemaChangedError(f"table '{table_id}' has an empty <thead>")

    group_labels = _expand_colspans(header_rows[0])
    column_labels = _expand_colspans(header_rows[-1])

    names: list[str] = []
    for i, col in enumerate(column_labels):
        group = group_labels[i] if i < len(group_labels) else ""
        names.append(f"{group} {col}".strip())

    rows: list[dict[str, Any]] = []
    tbody = table.find("tbody")
    if tbody is None:
        return rows

    for tr in tbody.find_all("tr"):
        if "thead" in (tr.get("class") or []):
            continue  # FBref spacer rows inside tbody
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        record: dict[str, Any] = {"__fbref_id__": None}
        for i, cell in enumerate(cells):
            if i < len(names):
                record[names[i]] = cell.get_text(strip=True)
        anchor = tr.find("a", href=True)
        if anchor and anchor.get("href"):
            m = _PLAYER_ID_RE.search(anchor["href"])
            if m:
                record["__fbref_id__"] = m.group(1)
        # only rows that represent a player (have a Player cell)
        if not record.get("Player"):
            continue
        rows.append(record)

    return rows


def _num(row: dict[str, Any], candidates: list[str]) -> float | None:
    """Read the first present candidate cell as a float. None when absent/empty."""
    for name in candidates:
        raw = row.get(name)
        if raw is None or raw == "":
            continue
        try:
            return float(raw.replace(",", "").replace("%", ""))
        except ValueError:
            continue
    return None


def _first_present(row: dict[str, Any], candidates: list[str]) -> str | None:
    for name in candidates:
        raw = row.get(name)
        if raw is not None and raw != "":
            return raw
    return None


class FBrefSource(StatsSource):
    source_name = "fbref"

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        cache: HttpCache | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        settings = get_settings()
        self.session = session or requests.Session()
        self.cache = cache or HttpCache()
        # Declared compliance limit: 1 request per 10s ± 2s jitter.
        self.limiter = limiter or RateLimiter(
            settings.fbref_delay_seconds, settings.fbref_jitter_seconds
        )
        self.registry = load_registry()
        self.tiers = load_tiers()

    def get_rate_limit_seconds(self) -> float:
        return self.limiter.interval

    # -- URL construction ------------------------------------------------
    def build_url(self, league_slug: str, season: str) -> str:
        comp_id = self.tiers["leagues"][league_slug]["external_ids"].get("fbref_comp")
        if comp_id is None:
            raise FBrefSchemaChangedError(
                f"no fbref_comp id configured for league '{league_slug}'"
            )
        url_slug = FBREF_URL_SLUGS.get(league_slug, league_slug.title())
        return (
            f"{FBREF_BASE}/en/comps/{comp_id}/{canonical_season_to_fbref(season)}/"
            f"{url_slug}-Stats"
        )

    # -- Main interface ---------------------------------------------------
    def fetch_league_stats(
        self, league_slug: str, season: str
    ) -> list[RawPlayerStatRecord]:
        url = self.build_url(league_slug, season)
        logger.info("fetching FBref %s %s", league_slug, season)
        html = fetch_with_retry(
            url,
            limiter=self.limiter,
            cache=self.cache,
            headers={"User-Agent": get_settings().user_agent},
        )
        soup = BeautifulSoup(html, "html.parser")

        tables: dict[str, list[dict[str, Any]]] = {}
        for table_id in FBREF_TABLES:
            tables[table_id] = parse_fbref_table(soup, table_id)

        missing = [t for t in REQUIRED_TABLES if tables.get(t) is None]
        if missing:
            raise FBrefSchemaChangedError(
                f"FBref page for {league_slug}/{season} missing required tables: {missing}"
            )

        # Index rows by fbref player id (robust join across tables; names can
        # collide within a league). Rows without an id are joined by name+team.
        by_id: dict[str, dict[str, Any]] = {}
        for row in tables["stats_standard"]:
            pid = row.get("__fbref_id__")
            if pid:
                by_id.setdefault(pid, row)
        by_key: dict[tuple[str, str], dict[str, Any]] = {
            (row.get("Player", ""), row.get("Squad", "")): row
            for row in tables["stats_standard"]
        }

        def lookup(pid: str | None, name: str, team: str) -> dict[str, Any] | None:
            if pid and pid in by_id:
                return by_id[pid]
            return by_key.get((name, team))

        records: list[RawPlayerStatRecord] = []
        for row in tables["stats_standard"]:
            team = row.get("Squad", "")
            if team.lower() in _TEAMS_AGGREGATE_ROWS:
                continue  # transferred-player aggregate rows are skipped (per-team rows cover them)
            pid = row.get("__fbref_id__")
            name = row.get("Player", "")
            if not name:
                continue

            pt = None
            for t in tables["stats_playing_time"]:
                if (pid and t.get("__fbref_id__") == pid) or (
                    t.get("Player") == name and t.get("Squad") == team
                ):
                    pt = t
                    break

            # Playing-time columns carry the "Playing Time" group prefix in the
            # combined header (e.g. "Playing Time Min"); bare names are the fallback.
            minutes = _num(pt or {}, ["Playing Time Min", "Min"]) if pt else None
            matches = _num(pt or {}, ["Playing Time MP", "MP"]) if pt else None
            if minutes is None:
                logger.warning(
                    "no minutes for %s (%s) — skipping; possible schema change",
                    name,
                    team,
                )
                continue

            pos_code = row.get("Pos") or None
            position_group = POSITION_GROUP_MAP.get(pos_code) if pos_code else None
            if position_group is None:
                logger.info(
                    "unmapped position code '%s' for %s -> reconciliation queue",
                    pos_code,
                    name,
                )

            # Raw totals that some metric rates are derived from.
            totals: dict[str, Any] = {"minutes": minutes}
            totals.update(
                {
                    name_: row.get(name_)
                    for name_ in row
                    if name_ not in ("__fbref_id__",)
                }
            )

            raw_stats = self._extract_metrics(row, tables, position_group, minutes)

            born = row.get("Born")
            dob_year = int(born) if born and born.isdigit() and len(born) == 4 else None

            records.append(
                RawPlayerStatRecord(
                    source="fbref",
                    season=season,
                    league_slug=league_slug,
                    player_name=name,
                    team_name=team,
                    minutes_played=minutes,
                    matches_played=int(matches or 0),
                    raw_stats=raw_stats,
                    position_code=pos_code,
                    position_group=position_group,
                    position_label=None,  # natural-language label lives on player pages (optional enrichment job)
                    dob_year=dob_year,
                    external_ids={"fbref": pid} if pid else {},
                    nation=row.get("Nation") or None,
                )
            )
        return records

    # -- Metric extraction -------------------------------------------------
    def _extract_metrics(
        self,
        row: dict[str, Any],
        tables: dict[str, list[dict[str, Any]]],
        position_group: str | None,
        minutes: float,
    ) -> dict[str, float]:
        """Extract raw_stats keyed by registry metric id.

        Every metric mapped here is named in config/metric_registry.json (which
        derives from methodology.md). No undocumented fields are collected.
        """
        registry = self.registry
        is_gk = position_group == "GK"
        metric_ids = registry["gk_metrics"] if is_gk else registry["outfield_metrics"]
        out: dict[str, float] = {}

        for mid in metric_ids:
            spec = registry["metrics"][mid]
            kind = spec["kind"]
            try:
                if kind == "derived":
                    # Derived metrics define their inputs directly (registry
                    # entries have no 'fbref' key) — e.g. psxg_minus_ga.
                    if spec.get("formula") == "psxg_minus_ga":
                        psxg = self._cell(row, tables, spec["inputs"]["psxg"])
                        ga = self._cell(row, tables, spec["inputs"]["ga"])
                        if psxg is not None and ga is not None:
                            out[mid] = (
                                round((psxg - ga) / minutes * 90, 4)
                                if minutes > 0
                                else 0.0
                            )
                    continue
                fbspec = spec.get("fbref")
                if fbspec is None:
                    continue
                if kind == "per90":
                    total = self._cell(row, tables, fbspec)
                    if total is not None:
                        out[mid] = (
                            round(total / minutes * 90, 4) if minutes > 0 else 0.0
                        )
                elif kind == "rate":
                    val = self._cell(row, tables, fbspec)
                    if val is not None:
                        out[mid] = round(val, 4)
            except KeyError as exc:  # a required input column is missing entirely
                raise FBrefSchemaChangedError(
                    f"metric {mid}: required column missing ({exc}); FBref structure changed"
                ) from exc

            # Sample-floor counts that percentile eligibility and display rules need.
            # floor_column specs share the parent metric's table (they are counts
            # from the same stat table, e.g. pass attempts from the passing table)
            # — they do not carry their own 'table' key.
            if mid in ("si_cmp_pct", "si_save_pct", "si_cross_pct") and fbspec.get(
                "floor_column"
            ):
                floor = dict(fbspec["floor_column"])
                floor.setdefault("table", fbspec.get("table", "standard"))
                count = self._cell(row, tables, floor)
                if count is not None:
                    aux_key = {
                        "si_cmp_pct": "_cmp_attempts",
                        "si_save_pct": "_sota_faced",
                        "si_cross_pct": "_crosses_faced",
                    }[mid]
                    out[aux_key] = count
        return out

    def _cell(
        self,
        row: dict[str, Any],
        tables: dict[str, list[dict[str, Any]]],
        spec: dict[str, Any],
    ) -> float | None:
        """Resolve a metric's value from the correct table for this player row.

        FBref splits some stat tables per goalkeeper/outfield player, so when the
        column is missing from the standard row we search the matching player row
        in the target table (by fbref id, then name+team).
        """
        candidates: list[str] = list(spec.get("candidates", []))
        if spec.get("column") not in candidates:
            candidates.append(spec["column"])
        table_id = fbref_table_id(spec["table"])

        # Fast path: candidates present in this player's standard-table row.
        if self._row_has(row, candidates):
            return _num(row, candidates)

        table_rows = tables.get(table_id)
        if table_rows is None:
            return None  # optional table absent -> metric simply unavailable
        pid = row.get("__fbref_id__")
        name = row.get("Player", "")
        team = row.get("Squad", "")
        for candidate_row in table_rows:
            # SIM114: both match routes are one condition — id match OR name+team.
            match = (pid and candidate_row.get("__fbref_id__") == pid) or (
                candidate_row.get("Player") == name
                and candidate_row.get("Squad") == team
            )
            if match and self._row_has(candidate_row, candidates):
                return _num(candidate_row, candidates)
        return None

    @staticmethod
    def _row_has(row: dict[str, Any], candidates: list[str]) -> bool:
        return any(row.get(c) not in (None, "") for c in candidates)
