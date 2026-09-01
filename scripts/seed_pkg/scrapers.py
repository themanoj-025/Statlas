"""Statlas development-database seed (Phase 2).

Builds `data/dev.db` by running the REAL pipeline (orchestration, parsers,
reconciliation, anomaly checks, percentile/index computation, publishing)
against labeled fixture data — the same fixtures Phase 1's tests use:

- Premier League: the REAL FBref parser run over `tests/fixtures/fbref_league.html`
  (37 players across Manchester City and Liverpool) + the REAL Understat parser
  over `tests/fixtures/understat_page.html` (xG overlay).
- Every other league: deterministic synthetic demo records (seeded RNG,
  fictional player names, real club names per league) generated to reach
  realistic position-group pools.

HONESTY: this is FIXTURE/DEMO data, not production data. The API reports
`dataset_mode=fixture-demo` and the frontend renders a banner until a real
scrape run + `STATLAS_DATASET_MODE=production`. Run this only to develop the
UI; never point it at a production database.

Usage:
    python scripts/seed_dev_db.py            # rebuild data/dev.db (SQLite)
    STATLAS_DATASET_MODE=production  # set only after a real pipeline run
"""

from __future__ import annotations

import logging
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# The dev database is a file-based SQLite so the API server (separate process)
# reads exactly what the seed wrote. Override with DATABASE_URL for Postgres.
os.environ.setdefault(
    "DATABASE_URL", f"sqlite+pysqlite:///{PROJECT_ROOT / 'data' / 'dev.db'}"
)


from app.sources.base import RawPlayerStatRecord

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("seed")

SEASON = "2025-26"
SNAPSHOT_DATE = datetime(2026, 8, 12, 3, 0, 0, tzinfo=timezone.utc)
SEED = 42

FIXTURES = PROJECT_ROOT / "tests" / "fixtures"
DEV_DB = PROJECT_ROOT / "data" / "dev.db"

# Real club names per league (same precedent as the Phase 1 fixtures: real team
# names, fixture players, fake ids — all under the fixture-demo banner).
TEAMS_BY_LEAGUE: dict[str, list[str]] = {
    "la-liga": [
        "Real Madrid",
        "Barcelona",
        "Atlético Madrid",
        "Sevilla",
        "Real Sociedad",
        "Athletic Club",
        "Villarreal",
        "Real Betis",
    ],
    "serie-a": [
        "Juventus",
        "Inter",
        "Milan",
        "Napoli",
        "Roma",
        "Lazio",
        "Atalanta",
        "Fiorentina",
    ],
    "bundesliga": [
        "Bayern Munich",
        "Borussia Dortmund",
        "RB Leipzig",
        "Bayer Leverkusen",
        "Eintracht Frankfurt",
        "VfB Stuttgart",
        "Wolfsburg",
        "Freiburg",
    ],
    "ligue-1": [
        "Paris Saint-Germain",
        "Marseille",
        "Lyon",
        "Monaco",
        "Lille",
        "Nice",
        "Rennes",
        "Lens",
    ],
    "eredivisie": ["Ajax", "PSV", "Feyenoord", "AZ Alkmaar", "Twente", "Utrecht"],
    "primeira-liga": [
        "Benfica",
        "Porto",
        "Sporting CP",
        "Braga",
        "Vitória Guimarães",
        "Boavista",
    ],
    "belgian-pro-league": [
        "Anderlecht",
        "Club Brugge",
        "Genk",
        "Gent",
        "Antwerp",
        "Standard Liège",
    ],
    "super-lig": [
        "Galatasaray",
        "Fenerbahçe",
        "Beşiktaş",
        "Trabzonspor",
        "Başakşehir",
        "Adana Demirspor",
    ],
    "scottish-premiership": [
        "Celtic",
        "Rangers",
        "Aberdeen",
        "Hearts",
        "Hibernian",
        "Dundee United",
    ],
    "austrian-bundesliga": [
        "Red Bull Salzburg",
        "Sturm Graz",
        "Rapid Wien",
        "LASK",
        "Austria Wien",
        "Wolfsberger AC",
    ],
    "swiss-super-league": [
        "Young Boys",
        "Servette",
        "Basel",
        "Zürich",
        "Lugano",
        "St. Gallen",
    ],
    "greek-super-league": [
        "Olympiacos",
        "PAOK",
        "AEK Athens",
        "Panathinaikos",
        "Aris",
        "Volos",
    ],
    "danish-superliga": [
        "FC Copenhagen",
        "Midtjylland",
        "Brøndby",
        "AGF Aarhus",
        "Nordsjælland",
        "Silkeborg",
    ],
    "championship": [
        "Leeds United",
        "Leicester City",
        "Southampton",
        "Norwich City",
        "West Brom",
        "Sunderland",
        "Stoke City",
        "Middlesbrough",
    ],
    "la-liga-2": [
        "Levante",
        "Sporting Gijón",
        "Racing Santander",
        "Espanyol",
        "Eibar",
        "Zaragoza",
        "Almería",
        "Oviedo",
    ],
    "serie-b": [
        "Parma",
        "Como",
        "Palermo",
        "Cremonese",
        "Bari",
        "Sampdoria",
        "Catanzaro",
        "Modena",
    ],
    "2-bundesliga": [
        "Hamburger SV",
        "Schalke 04",
        "Hannover 96",
        "Hertha Berlin",
        "Fortuna Düsseldorf",
        "Nürnberg",
        "Kaiserslautern",
        "Magdeburg",
    ],
    "ligue-2": [
        "Bordeaux",
        "Saint-Étienne",
        "Metz",
        "Guingamp",
        "Caen",
        "Amiens",
        "Pau",
        "Angers",
    ],
}

TIER_1_SYNTHETIC = ["la-liga", "serie-a", "bundesliga", "ligue-1"]

PL_TEAMS = [
    "Manchester City",
    "Liverpool",
    "Arsenal",
    "Chelsea",
    "Tottenham Hotspur",
    "Newcastle United",
    "Manchester United",
    "Aston Villa",
    "Brighton & Hove Albion",
    "West Ham United",
    "Everton",
    "Brentford",
    "Crystal Palace",
    "Wolverhampton Wanderers",
    "Fulham",
    "Bournemouth",
    "Nottingham Forest",
    "Burnley",
    "Luton Town",
    "Sheffield United",
]
TIER_2_SYNTHETIC = [
    "eredivisie",
    "primeira-liga",
    "belgian-pro-league",
    "super-lig",
    "scottish-premiership",
    "austrian-bundesliga",
    "swiss-super-league",
    "greek-super-league",
    "danish-superliga",
]
TIER_3_SYNTHETIC = ["championship", "la-liga-2", "serie-b", "2-bundesliga", "ligue-2"]

FIRST_NAMES = [
    "Luka",
    "Mateo",
    "Andrés",
    "Julian",
    "Tomas",
    "Viktor",
    "Nico",
    "Marco",
    "Piotr",
    "Elias",
    "Ruben",
    "Sergi",
    "Dani",
    "Kai",
    "Yusuf",
    "Isak",
    "Mikkel",
    "Oscar",
    "Gabriel",
    "Hugo",
    "Theo",
    "Arthur",
    "Emil",
    "Lucas",
    "Adrien",
    "Stefan",
    "Milan",
    "David",
    "Filip",
    "Andre",
    "Jonas",
    "Pablo",
    "Ivan",
    "Anton",
    "Rafael",
    "Nils",
    "Diego",
    "Leon",
    "Felix",
    "Bruno",
]
LAST_NAMES = [
    "Moreau",
    "Silva",
    "Kovac",
    "Andersen",
    "Ferreira",
    "Novak",
    "Mendes",
    "Varga",
    "Petrov",
    "Sousa",
    "Horvat",
    "Nielsen",
    "Costa",
    "Janssen",
    "Keller",
    "Rossi",
    "Larsen",
    "Dubois",
    "Hansen",
    "Marques",
    "Vidal",
    "Ramos",
    "Weber",
    "Kowalski",
    "Bianchi",
    "Fontaine",
    "Ivanov",
    "Schmidt",
    "Oliveira",
    "Fernandez",
    "Russo",
    "Moreno",
    "Jensen",
    "Berg",
    "Martin",
    "Garcia",
    "Torres",
    "Kohler",
    "Dupont",
    "Krstic",
    "Lindberg",
    "Araujo",
]
NATIONS = [
    "England",
    "Spain",
    "France",
    "Germany",
    "Italy",
    "Netherlands",
    "Portugal",
    "Brazil",
    "Argentina",
    "Denmark",
    "Croatia",
    "Belgium",
    "Serbia",
    "Norway",
    "Sweden",
]
MIDDLE_INITIALS = "ABCDEFGHJKLMNPRSTVWY"

POSITION_GROUPS = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"]


# ---------------------------------------------------------------------------
# Real parsers over the Phase 1 fixtures (premier-league only)
# ---------------------------------------------------------------------------


def _fixture_html(filename: str) -> str:
    return (FIXTURES / filename).read_text(encoding="utf-8")


def scrape_premier_league_from_fixtures() -> list[RawPlayerStatRecord]:
    """Run the REAL FBref + Understat parsers over the fixture HTML."""
    import app.sources.fbref as fbref_mod
    import app.sources.understat as understat_mod

    original_fbref = fbref_mod.fetch_with_retry
    original_understat = understat_mod.fetch_with_retry
    fbref_mod.fetch_with_retry = lambda *a, **k: _fixture_html("fbref_league.html")
    understat_mod.fetch_with_retry = lambda *a, **k: _fixture_html(
        "understat_page.html"
    )
    try:
        fbref_source = fbref_mod.FBrefSource()
        understat_source = understat_mod.UnderstatSource()
        fbref_records = fbref_source.fetch_league_stats("premier-league", SEASON)
        understat_records = understat_source.fetch_league_stats(
            "premier-league", SEASON
        )
    finally:
        fbref_mod.fetch_with_retry = original_fbref
        understat_mod.fetch_with_retry = original_understat
    logger.info(
        "fixture parse: %d fbref records, %d understat records",
        len(fbref_records),
        len(understat_records),
    )
    return fbref_records, understat_records


# ---------------------------------------------------------------------------
# Deterministic synthetic demo records for the other leagues
# ---------------------------------------------------------------------------


class _DemoPlayerGen:
    """Seeded generator producing plausible in-bounds per-group stats.

    Every generated value stays inside the registry's anomaly bounds (the
    anomaly check must pass with zero flags on a clean seed). Bounds:
    gls/xg 0–5, sh 0–20, prgp 0–35, prgc 0–30, xag 0–3, kp 0–15, tkl/int 0–15,
    press 0–100, cmp 0–100, dis 0–15, minutes 0–3600, matches 0–80.
    """

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def _u(self, lo: float, hi: float) -> float:
        return self.rng.uniform(lo, hi)

    def raw_for(self, group: str) -> dict[str, float]:
        if group == "GK":
            raw = {
                "si_save_pct": round(self._u(56, 84), 1),
                "si_psxg_ga_p90": round(self._u(-0.4, 0.45), 3),
                "si_ga_p90": round(self._u(0.6, 2.1), 2),
                "si_cross_pct": round(self._u(2, 9.5), 1),
                "_sota_faced": int(self._u(50, 170)),
                "_crosses_faced": int(self._u(40, 120)),
            }
        else:
            gls = {
                "ST": (0.08, 0.85),
                "W": (0.04, 0.5),
                "AM": (0.03, 0.45),
                "CM": (0.0, 0.3),
                "DM": (0.0, 0.18),
                "FB": (0.0, 0.16),
                "CB": (0.0, 0.14),
            }[group]
            g = self._u(*gls)
            raw = {
                "si_gls_p90": round(g, 3),
                "si_xg_p90": round(g * self._u(0.85, 1.25), 3),
                "si_sh_p90": round(self._u(0.4, 4.5), 2),
                "si_prgp_p90": round(self._u(0.4, 9.0), 2),
                "si_prgc_p90": round(self._u(0.2, 7.5), 2),
                "si_xag_p90": round(self._u(0.01, 0.55), 3),
                "si_kp_p90": round(self._u(0.1, 3.0), 2),
                "si_tkl_p90": round(self._u(0.1, 3.0), 2),
                "si_int_p90": round(self._u(0.1, 2.8), 2),
                "si_press_p90": round(self._u(3.0, 24.0), 1),
                "si_cmp_pct": round(self._u(70, 93), 1),
                "si_dis_p90": round(self._u(0.2, 2.8), 2),
                "_cmp_attempts": int(self._u(70, 420)),
            }
        return raw

    def understat_overlay(
        self, fbref_record: RawPlayerStatRecord, understat_id: int
    ) -> RawPlayerStatRecord | None -> None:
        """Understat-model values for a Tier-1 outfield player (xG model rule:
        Tier 1 uses one model — Understat — so every Tier-1 cohort member must
        have an understat snapshot or the xG percentile would mix models).

        Values stay within the anomaly cross-source tolerances (xG 30% rel /
        0.3 abs; shots 30% rel / 2.0 abs) so a clean seed produces zero flags.
        """
        if fbref_record.position_group == "GK":
            return None
        raw = fbref_record.raw_stats
        xg_u = round((raw.get("si_xg_p90") or 0.0) * self._u(0.95, 1.15), 3)
        return RawPlayerStatRecord(
            source="understat",
            season=fbref_record.season,
            league_slug=fbref_record.league_slug,
            player_name=fbref_record.player_name,
            team_name=fbref_record.team_name,
            minutes_played=fbref_record.minutes_played,
            matches_played=fbref_record.matches_played,
            raw_stats={
                "si_xg_p90": xg_u,
                "si_sh_p90": round(
                    (raw.get("si_sh_p90") or 1.0) * self._u(0.95, 1.1), 2
                ),
                "si_xag_p90": round(
                    (raw.get("si_xag_p90") or 0.05) * self._u(0.85, 1.2), 3
                ),
                "si_kp_p90": round(
                    (raw.get("si_kp_p90") or 0.5) * self._u(0.85, 1.2), 2
                ),
            },
            position_group=None,
            dob_year=fbref_record.dob_year,
            external_ids={"understat": understat_id},
            nation=fbref_record.nation,
        )

    def player(
        self,
        league_slug: str,
        team_name: str,
        group: str,
        index: int,
        used_names: set[str],
    ) -> RawPlayerStatRecord -> None:
        # Globally unique names (not per-league): the reconciler's _exact_match
        # falls back to a name+DOB-year match even across teams, so duplicate
        # names would merge distinct players into one canonical player (and put
        # one player in several leagues, breaking percentile pool keys). A
        # middle initial keeps the normalized name distinct.
        name = None
        for _ in range(12):
            candidate = f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}"
            if candidate not in used_names:
                name = candidate
                break
        if name is None:
            name = f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(MIDDLE_INITIALS)}. {self.rng.choice(LAST_NAMES)}"
        used_names.add(name)
        minutes = int(self._u(940, 2700))
        roll = self.rng.random()
        if roll < 0.07:  # below the 900-minute qualifying threshold (demo state)
            minutes = int(self._u(480, 895))
        elif roll < 0.10:  # very low minutes — display-floor / pending states
            minutes = int(self._u(120, 330))
        raw = self.raw_for(group)
        if self.rng.random() < 0.03:  # a few players fail the pass-attempt floor
            raw["_cmp_attempts"] = int(self._u(10, 45))
        return RawPlayerStatRecord(
            source="fbref",
            season=SEASON,
            league_slug=league_slug,
            player_name=name,
            team_name=team_name,
            minutes_played=float(minutes),
            matches_played=min(38, max(1, round(minutes / 90))),
            raw_stats=raw,
            position_code=None,
            position_group=group,
            position_label=None,
            dob_year=self.rng.randint(1990, 2007),
            # Globally unique external id — a per-league prefix would collide
            # across leagues (e.g. la-liga/la-liga-2, ligue-1/ligue-2) and merge
            # distinct players during reconciliation, breaking percentile keys.
            external_ids={"fbref": f"d{index:06d}"},
            nation=self.rng.choice(NATIONS),
        )


