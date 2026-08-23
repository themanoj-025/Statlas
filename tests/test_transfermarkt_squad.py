"""Tests for Transfermarkt squad page parsing and bulk ingestion."""

from __future__ import annotations

from unittest.mock import MagicMock

from bs4 import BeautifulSoup

from app.sources.transfermarkt import TransfermarktSource
from tests.conftest import fixtures_dir


def _fixture_html(filename: str) -> str:
    with open(fixtures_dir() / filename, encoding="utf-8") as f:
        return f.read()


def _fixture_soup(filename: str) -> BeautifulSoup:
    return BeautifulSoup(_fixture_html(filename), "html.parser")


class TestParseSquadPage:
    """Test _parse_squad_page against the fixture HTML."""

    def test_parses_all_players(self):
        soup = _fixture_soup("transfermarkt_squad.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        players = source._parse_squad_page(soup, "Arsenal FC", 11, "premier-league")
        assert len(players) == 4

    def test_extracts_player_ids(self):
        soup = _fixture_soup("transfermarkt_squad.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        players = source._parse_squad_page(soup, "Arsenal FC", 11, "premier-league")
        tm_ids = [p["transfermarkt_id"] for p in players]
        assert tm_ids == [262749, 476862, 316269, 381976]

    def test_extracts_names(self):
        soup = _fixture_soup("transfermarkt_squad.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        players = source._parse_squad_page(soup, "Arsenal FC", 11, "premier-league")
        names = [p["name"] for p in players]
        assert "David Raya" in names
        assert "Martin Odegaard" in names
        assert "Kai Havertz" in names

    def test_extracts_positions(self):
        soup = _fixture_soup("transfermarkt_squad.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        players = source._parse_squad_page(soup, "Arsenal FC", 11, "premier-league")
        by_name = {p["name"]: p for p in players}
        assert by_name["David Raya"]["position"] == "Goalkeeper"
        assert by_name["Kai Havertz"]["position"] == "Centre-Forward"

    def test_extracts_ages(self):
        soup = _fixture_soup("transfermarkt_squad.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        players = source._parse_squad_page(soup, "Arsenal FC", 11, "premier-league")
        by_name = {p["name"]: p for p in players}
        assert by_name["David Raya"]["age"] == 30
        assert by_name["Martin Odegaard"]["age"] == 27

    def test_extracts_contract_dates(self):
        soup = _fixture_soup("transfermarkt_squad.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        players = source._parse_squad_page(soup, "Arsenal FC", 11, "premier-league")
        by_name = {p["name"]: p for p in players}
        assert by_name["David Raya"]["contract_expires"] == "30/06/2028"

    def test_extracts_market_values(self):
        soup = _fixture_soup("transfermarkt_squad.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        players = source._parse_squad_page(soup, "Arsenal FC", 11, "premier-league")
        by_name = {p["name"]: p for p in players}
        assert by_name["David Raya"]["market_value_text"] == "\u20ac30.00m"
        assert by_name["David Raya"]["market_value_eur"] == 30_000_000.0
        assert by_name["Martin Odegaard"]["market_value_eur"] == 120_000_000.0

    def test_includes_club_and_league(self):
        soup = _fixture_soup("transfermarkt_squad.html")
        source = TransfermarktSource.__new__(TransfermarktSource)
        players = source._parse_squad_page(soup, "Arsenal FC", 11, "premier-league")
        for p in players:
            assert p["club_name"] == "Arsenal FC"
            assert p["tm_club_id"] == 11
            assert p["league_slug"] == "premier-league"


class TestExtractClubsFromOverview:
    """Test _extract_clubs_from_overview against a real (cached) page."""

    def test_extracts_clubs_from_live_page(self):
        """Verify club extraction works against the actual TM overview page."""
        source = TransfermarktSource.__new__(TransfermarktSource)
        source.session = MagicMock()
        source.cache = MagicMock()
        # Use the real overview page HTML (fetched once and cached)
        import requests as _requests
        url = "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1"
        r = _requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        clubs = source._extract_clubs_from_overview(soup)
        # Premier League has 20 clubs
        assert len(clubs) >= 18
        # Check that we got valid club data
        names = [c["name"] for c in clubs]
        assert any("Arsenal" in n for n in names)
        assert all(c["tm_club_id"] > 0 for c in clubs)
        assert all(c["squad_url"] for c in clubs)


class TestIngestScriptHelpers:
    """Test helper functions used by the bulk ingestion script."""

    def test_position_to_group(self):
        from scripts.ingest_transfermarkt_squad import position_to_group
        assert position_to_group("Goalkeeper") == "GK"
        assert position_to_group("Centre-Back") == "CB"
        assert position_to_group("Right-Back") == "FB"
        assert position_to_group("Defensive Midfield") == "DM"
        assert position_to_group("Central Midfield") == "CM"
        assert position_to_group("Attacking Midfield") == "AM"
        assert position_to_group("Left Winger") == "W"
        assert position_to_group("Centre-Forward") == "ST"
        assert position_to_group("") is None

    def test_upsert_creates_new_players(self, db):
        from app.models.player import Player
        from scripts.ingest_transfermarkt_squad import upsert_players

        players = [
            {
                "name": "Test Player TM",
                "transfermarkt_id": 9999999,
                "position": "Centre-Forward",
                "club_name": "Test FC",
                "tm_club_id": 0,
                "league_slug": "test",
            }
        ]
        created, updated = upsert_players(db, players, "transfermarkt")
        assert created == 1
        assert updated == 0

        # Verify the player was created
        p = db.query(Player).filter(Player.transfermarkt_id == 9999999).first()
        assert p is not None
        assert p.canonical_name == "Test Player TM"
        assert p.transfermarkt_id == 9999999
        assert p.position_group == "ST"
        assert p.external_ids.get("transfermarkt") == 9999999

    def test_upsert_updates_existing_players(self, db):
        from app.models.player import Player
        from scripts.ingest_transfermarkt_squad import upsert_players

        # Create an existing player
        existing = Player(
            canonical_name="Existing TM Player",
            transfermarkt_id=8888888,
            external_ids={"transfermarkt": 8888888},
        )
        db.add(existing)
        db.flush()

        # Upsert with same TM ID
        players = [
            {
                "name": "Existing TM Player",
                "transfermarkt_id": 8888888,
                "position": "Centre-Back",
                "club_name": "Test FC",
                "tm_club_id": 0,
                "league_slug": "test",
            }
        ]
        created, updated = upsert_players(db, players, "transfermarkt")
        assert created == 0
        assert updated == 1

        # Verify position was updated (was None, now set)
        p = db.query(Player).filter(Player.transfermarkt_id == 8888888).first()
        assert p is not None
        assert p.primary_position == "Centre-Back"
        assert p.position_group == "CB"
