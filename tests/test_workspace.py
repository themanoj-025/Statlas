"""Phase 7 — scouting workspace test suite.

Covers the mandatory Part B4 scenarios:
- CRUD for every workspace query function
- status-transition validation (valid AND explicitly-invalid transitions)
- authorization: a user can never view/modify another user's shortlist data
  (404 semantics — existence must not leak)
- unique-per-shortlist constraint (duplicate add fails cleanly)
- soft-delete preserves status_history for audit
- free-tier caps produce honest upsell errors
- tag suggestions never leak another user's vocabulary
- a multi-step status-history audit trail is complete and ordered
Plus API-level checks (401 unauthenticated, 404 cross-user, 403 upsell).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.db import create_schema, session_scope
from app.models import (
    EntryNote,
    EntryTag,
    League,
    PercentileSnapshot,
    Player,
    Shortlist,
    ShortlistEntry,
    StatSnapshot,
    StatusHistory,
    Subscription,
    Team,
    User,
)
from app.queries import workspace_queries as wq

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_user(db, email: str = "scout@example.com", plan: str = "free") -> User:
    user = User(email=email, password_hash="x" * 64, plan=plan)
    db.add(user)
    db.commit()
    return user


def make_pro_user(db, email: str = "pro@example.com") -> User:
    user = make_user(db, email, plan="pro")
    db.add(
        Subscription(
            user_id=user.id, plan="pro", stripe_subscription_id="sub_x", status="active"
        )
    )
    db.commit()
    return user


def make_league_team(db, league_name: str = "Premier League") -> tuple[League, Team]:
    league = League(
        slug="premier-league",
        name=league_name,
        country="England",
        tier="tier_1",
        external_ids={},
    )
    db.add(league)
    db.commit()
    team = Team(name="Manchester City", league_id=league.id, external_ids={})
    db.add(team)
    db.commit()
    return league, team


def make_player(db, name: str = "Erling Haaland", team: Team | None = None) -> Player:
    player = Player(
        canonical_name=name,
        position_group="ST",
        primary_position="Striker",
        external_ids={},
        current_team_id=team.id if team else None,
    )
    db.add(player)
    db.commit()
    return player


@pytest.fixture()
def workspace_data(db):
    """One free user, one pro user, two players — the shared CRUD scaffold."""
    free = make_user(db, "free@example.com")
    pro = make_pro_user(db, "pro@example.com")
    league, team = make_league_team(db)
    haaland = make_player(db, "Erling Haaland", team)
    salah = make_player(db, "Mohamed Salah", team)
    return {"free": free, "pro": pro, "haaland": haaland, "salah": salah}


# ---------------------------------------------------------------------------
# Shortlists
# ---------------------------------------------------------------------------


def test_default_shortlist_created_lazily(db):
    user = make_user(db)
    shortlists = wq.list_shortlists(db, user.id)
    assert len(shortlists) == 1
    assert shortlists[0]["name"] == wq.DEFAULT_SHORTLIST_NAME
    assert shortlists[0]["entry_count"] == 0


def test_create_and_list_shortlists_with_counts(db, workspace_data):
    user = workspace_data["free"]
    wq.create_shortlist(db, user.id, "Summer 2027 CB targets", "Centre-backs to watch")
    shortlists = wq.list_shortlists(db, user.id)
    # The default shortlist is created lazily ONLY when the user has none —
    # a user who already created one never gets a surprise duplicate.
    assert [s["name"] for s in shortlists] == ["Summer 2027 CB targets"]
    assert shortlists[0]["description"] == "Centre-backs to watch"


def test_create_shortlist_requires_name(db, workspace_data):
    with pytest.raises(ValueError):
        wq.create_shortlist(db, workspace_data["free"].id, "   ")


def test_delete_shortlist_is_soft(db, workspace_data):
    # A pro user (free users are capped at one shortlist).
    user = workspace_data["pro"]
    wq.list_shortlists(db, user.id)  # creates the default shortlist
    sl = wq.create_shortlist(db, user.id, "Temp list")
    wq.delete_shortlist(db, user.id, sl["shortlist_id"])
    # Hidden from listing, row still exists for audit.
    names = [s["name"] for s in wq.list_shortlists(db, user.id)]
    assert "Temp list" not in names
    assert db.query(Shortlist).count() == 2  # default + soft-deleted temp


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------


def test_add_player_sets_discovered_and_history(db, workspace_data):
    user = workspace_data["free"]
    haaland = workspace_data["haaland"]
    shortlists = wq.list_shortlists(db, user.id)
    sl_id = shortlists[0]["shortlist_id"]

    result = wq.add_player_to_shortlist(
        db, user.id, sl_id, haaland.id, initial_note="Elite movement in tight spaces"
    )
    assert result["status"] == "discovered"

    detail = wq.get_shortlist_detail(db, user.id, sl_id)
    assert detail["entry_count"] == 1
    entry = detail["entries"][0]
    assert entry["name"] == "Erling Haaland"
    assert entry["status"] == "discovered"
    assert entry["added_by_note"] == "Elite movement in tight spaces"
    assert entry["club"] == "Manchester City"
    assert entry["position_group"] == "ST"
    # Initial history row: None -> discovered.
    assert len(entry["status_history"]) == 1
    assert entry["status_history"][0]["from_status"] is None
    assert entry["status_history"][0]["to_status"] == "discovered"


def test_add_unknown_player_rejected(db, workspace_data):
    user = workspace_data["free"]
    sl_id = wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    with pytest.raises(wq.PlayerNotFound):
        wq.add_player_to_shortlist(db, user.id, sl_id, 999_999)


def test_duplicate_player_in_same_shortlist_rejected(db, workspace_data):
    user = workspace_data["free"]
    haaland = workspace_data["haaland"]
    sl_id = wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    wq.add_player_to_shortlist(db, user.id, sl_id, haaland.id)
    with pytest.raises(wq.DuplicateEntry):
        wq.add_player_to_shortlist(db, user.id, sl_id, haaland.id)


def test_same_player_ok_in_two_shortlists(db, workspace_data):
    user = workspace_data["pro"]
    haaland = workspace_data["haaland"]
    first = wq.create_shortlist(db, user.id, "Project A")
    second = wq.create_shortlist(db, user.id, "Project B")
    wq.add_player_to_shortlist(db, user.id, first["shortlist_id"], haaland.id)
    wq.add_player_to_shortlist(db, user.id, second["shortlist_id"], haaland.id)  # fine
    assert len(wq.get_shortlist_detail(db, user.id, first["shortlist_id"])["entries"]) == 1


def test_re_add_after_remove_restores_entry(db, workspace_data):
    user = workspace_data["free"]
    haaland = workspace_data["haaland"]
    sl_id = wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    wq.add_player_to_shortlist(db, user.id, sl_id, haaland.id)
    wq.remove_entry(db, user.id, sl_id, haaland.id)
    result = wq.add_player_to_shortlist(db, user.id, sl_id, haaland.id)
    detail = wq.get_shortlist_detail(db, user.id, sl_id)
    assert result["entry_id"] == detail["entries"][0]["entry_id"]
    # History survived the remove + re-add.
    assert len(detail["entries"][0]["status_history"]) >= 1


# ---------------------------------------------------------------------------
# Pipeline transitions
# ---------------------------------------------------------------------------


def _entry(db, workspace_data, user=None):
    user = user or workspace_data["free"]
    haaland = workspace_data["haaland"]
    sl_id = wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    result = wq.add_player_to_shortlist(db, user.id, sl_id, haaland.id)
    return result["entry_id"]


@pytest.mark.parametrize(
    "path",
    [
        ("discovered", "shortlisted"),  # forward skip
        ("discovered", "reviewed"),  # forward skip to the end
        ("shortlisted", "monitoring"),  # backward move
        ("reviewed", "discovered"),  # backward to the start
        ("monitoring", "rejected"),  # into terminal
        ("monitoring", "signed"),  # into terminal
        ("discovered", "signed"),  # straight to signed
        ("rejected", "monitoring"),  # the one documented reconsideration exit
    ],
)
def test_valid_transitions(db, workspace_data, path):
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    wq.update_entry_status(db, user.id, entry_id, path[0])
    result = wq.update_entry_status(db, user.id, entry_id, path[1])
    assert result["history_written"] is True


@pytest.mark.parametrize(
    "path,message_fragment",
    [
        (("signed", "monitoring"), "terminal"),
        (("signed", "rejected"), "terminal"),
        (("rejected", "scouted"), "reconsider"),
        (("rejected", "signed"), "reconsider"),
        (("rejected", "shortlisted"), "reconsider"),
    ],
)
def test_invalid_transitions_rejected(db, workspace_data, path, message_fragment):
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    wq.update_entry_status(db, user.id, entry_id, path[0])
    with pytest.raises(wq.InvalidStatusTransition) as excinfo:
        wq.update_entry_status(db, user.id, entry_id, path[1])
    assert message_fragment in str(excinfo.value)


def test_same_status_is_noop_no_history_row(db, workspace_data):
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    result = wq.update_entry_status(db, user.id, entry_id, "discovered")
    assert result["history_written"] is False
    detail = wq.get_shortlist_detail(
        db, user.id, wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    )
    assert len(detail["entries"][0]["status_history"]) == 1  # only the initial row


def test_unknown_status_rejected(db, workspace_data):
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    with pytest.raises(wq.InvalidStatusTransition):
        wq.update_entry_status(db, user.id, entry_id, "watching-on-tv")


def test_status_history_audit_trail_complete(db, workspace_data):
    """Multi-step scenario: several transitions over time — the full history
    must be queryable and ordered (Part E gate)."""
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    for status, reason in [
        ("monitoring", "Season started — tracking weekly minutes"),
        ("scouted", "Watched vs Arsenal; strong press"),
        ("shortlisted", None),
        ("rejected", "Fee demands too high"),
        ("monitoring", "Agent reopened talks — reconsidering"),
        ("reviewed", "Final review"),
    ]:
        wq.update_entry_status(db, user.id, entry_id, status, reason_note=reason)

    detail = wq.get_shortlist_detail(
        db, user.id, wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    )
    history = detail["entries"][0]["status_history"]
    # Newest first: initial row (None -> discovered) is last.
    assert len(history) == 7
    assert history[0]["to_status"] == "reviewed"
    assert history[0]["reason_note"] == "Final review"
    assert history[-1]["from_status"] is None
    assert history[-1]["to_status"] == "discovered"
    # The full path is reconstructable in order.
    path = [h["to_status"] for h in reversed(history)]
    assert path == [
        "discovered",
        "monitoring",
        "scouted",
        "shortlisted",
        "rejected",
        "monitoring",
        "reviewed",
    ]


# ---------------------------------------------------------------------------
# Notes, tags, priority
# ---------------------------------------------------------------------------


def test_notes_appended_and_timestamped(db, workspace_data):
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    wq.add_entry_note(db, user.id, entry_id, "First observation")
    wq.add_entry_note(db, user.id, entry_id, "Second observation")
    detail = wq.get_shortlist_detail(
        db, user.id, wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    )
    notes = detail["entries"][0]["notes"]
    assert [n["note_text"] for n in notes] == ["Second observation", "First observation"]
    assert notes[0]["author_user_id"] == user.id


def test_empty_note_rejected(db, workspace_data):
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    with pytest.raises(ValueError):
        wq.add_entry_note(db, user.id, entry_id, "   ")


def test_tags_add_normalize_and_remove(db, workspace_data):
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    wq.add_entry_tag(db, user.id, entry_id, "Left-Footed")
    wq.add_entry_tag(db, user.id, entry_id, "contract expiring")
    # Idempotent: adding the same tag again is a no-op, not an error.
    wq.add_entry_tag(db, user.id, entry_id, "left-footed")
    detail = wq.get_shortlist_detail(
        db, user.id, wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    )
    assert sorted(detail["entries"][0]["tags"]) == ["contract expiring", "left-footed"]

    wq.remove_entry_tag(db, user.id, entry_id, "LEFT-FOOTED")
    detail = wq.get_shortlist_detail(
        db, user.id, wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    )
    assert detail["entries"][0]["tags"] == ["contract expiring"]


def test_priority_set_and_cleared(db, workspace_data):
    user = workspace_data["free"]
    entry_id = _entry(db, workspace_data, user)
    wq.set_entry_priority(db, user.id, entry_id, "high")
    assert wq.set_entry_priority(db, user.id, entry_id, "high")["priority"] == "high"
    with pytest.raises(ValueError):
        wq.set_entry_priority(db, user.id, entry_id, "urgent")
    wq.set_entry_priority(db, user.id, entry_id, None)
    detail = wq.get_shortlist_detail(
        db, user.id, wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    )
    assert detail["entries"][0]["priority"] is None


# ---------------------------------------------------------------------------
# Authorization (B2 — the critical one)
# ---------------------------------------------------------------------------


def test_cannot_view_another_users_shortlist(db, workspace_data):
    free, pro = workspace_data["free"], workspace_data["pro"]
    sl_id = wq.list_shortlists(db, free.id)[0]["shortlist_id"]
    with pytest.raises(wq.ShortlistNotFound):
        wq.get_shortlist_detail(db, pro.id, sl_id)


def test_cannot_modify_another_users_entry(db, workspace_data):
    free, pro = workspace_data["free"], workspace_data["pro"]
    entry_id = _entry(db, workspace_data, free)
    with pytest.raises(wq.ShortlistNotFound):
        wq.update_entry_status(db, pro.id, entry_id, "monitoring")
    with pytest.raises(wq.ShortlistNotFound):
        wq.add_entry_note(db, pro.id, entry_id, "sneaky note")
    with pytest.raises(wq.ShortlistNotFound):
        wq.add_entry_tag(db, pro.id, entry_id, "sneaky-tag")
    with pytest.raises(wq.ShortlistNotFound):
        wq.remove_entry_by_id(db, pro.id, entry_id)


def test_cannot_add_to_another_users_shortlist(db, workspace_data):
    free, pro = workspace_data["free"], workspace_data["pro"]
    haaland = workspace_data["haaland"]
    sl_id = wq.list_shortlists(db, free.id)[0]["shortlist_id"]
    with pytest.raises(wq.ShortlistNotFound):
        wq.add_player_to_shortlist(db, pro.id, sl_id, haaland.id)


def test_memberships_only_own(db, workspace_data):
    free, pro = workspace_data["free"], workspace_data["pro"]
    haaland = workspace_data["haaland"]
    sl_id = wq.list_shortlists(db, free.id)[0]["shortlist_id"]
    wq.add_player_to_shortlist(db, free.id, sl_id, haaland.id)
    assert wq.get_shortlist_memberships(db, free.id, haaland.id) == [sl_id]
    assert wq.get_shortlist_memberships(db, pro.id, haaland.id) == []


# ---------------------------------------------------------------------------
# Soft delete preserves audit (B4)
# ---------------------------------------------------------------------------


def test_soft_delete_preserves_history_and_notes(db, workspace_data):
    user = workspace_data["free"]
    haaland = workspace_data["haaland"]
    sl_id = wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    entry_id = _entry(db, workspace_data, user)
    wq.add_entry_note(db, user.id, entry_id, "Keep an eye on this one")
    wq.add_entry_tag(db, user.id, entry_id, "watchlist")
    wq.update_entry_status(db, user.id, entry_id, "monitoring", reason_note="tracking")

    wq.remove_entry(db, user.id, sl_id, haaland.id)

    # Entry hidden from the detail view...
    detail = wq.get_shortlist_detail(db, user.id, sl_id)
    assert detail["entry_count"] == 0
    # ...but the audit trail is fully intact and queryable.
    assert db.query(StatusHistory).count() == 2  # initial + monitoring
    assert db.query(EntryNote).count() == 1
    assert db.query(EntryTag).count() == 1
    removed = db.query(ShortlistEntry).filter_by(player_id=haaland.id).first()
    assert removed.removed_at is not None


# ---------------------------------------------------------------------------
# Tier caps (B2 — honest upsell)
# ---------------------------------------------------------------------------


def test_free_user_capped_at_one_shortlist(db, workspace_data):
    user = workspace_data["free"]
    wq.create_shortlist(db, user.id, "Second list")
    with pytest.raises(wq.WorkspaceLimitExceeded) as excinfo:
        wq.create_shortlist(db, user.id, "Third list")
    assert "Upgrade to Pro" in str(excinfo.value)


def test_pro_user_unlimited_shortlists(db, workspace_data):
    user = workspace_data["pro"]
    for i in range(3):
        wq.create_shortlist(db, user.id, f"List {i}")
    # No lazy default: the user already has shortlists by the time they list.
    assert len(wq.list_shortlists(db, user.id)) == 3


def test_free_entry_cap(db, workspace_data):
    user = workspace_data["free"]
    sl_id = wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    limit = 10
    for i in range(limit):
        wq.add_player_to_shortlist(db, user.id, sl_id, make_player(db, f"Player {i}").id)
    with pytest.raises(wq.WorkspaceLimitExceeded) as excinfo:
        wq.add_player_to_shortlist(
            db, user.id, sl_id, make_player(db, "Player overflow").id
        )
    assert "10 players" in str(excinfo.value)


def test_removed_entries_do_not_count_toward_cap(db, workspace_data):
    """Soft-removed players free their slot (honest accounting)."""
    user = workspace_data["free"]
    sl_id = wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    players = [make_player(db, f"P{i}") for i in range(10)]
    for p in players:
        wq.add_player_to_shortlist(db, user.id, sl_id, p.id)
    wq.remove_entry(db, user.id, sl_id, players[0].id)
    wq.add_player_to_shortlist(db, user.id, sl_id, make_player(db, "Replacement").id)  # fits


# ---------------------------------------------------------------------------
# Tag suggestions (B3 — own vocabulary only)
# ---------------------------------------------------------------------------


def test_tag_suggestions_own_only_and_prefix_filtered(db, workspace_data):
    free, pro = workspace_data["free"], workspace_data["pro"]
    free_entry = _entry(db, workspace_data, free)
    wq.add_entry_tag(db, free.id, free_entry, "left-footed")
    wq.add_entry_tag(db, free.id, free_entry, "contract expiring")
    # A second free shortlist entry with the same tag bumps its frequency.
    wq.add_player_to_shortlist(
        db, free.id, wq.list_shortlists(db, free.id)[0]["shortlist_id"],
        workspace_data["salah"].id,
    )
    other = wq.get_shortlist_detail(db, free.id, wq.list_shortlists(db, free.id)[0]["shortlist_id"])
    wq.add_entry_tag(db, free.id, other["entries"][0]["entry_id"], "left-footed")

    # Pro user tags their own private vocabulary.
    pro_sl = wq.create_shortlist(db, pro.id, "Pro secret list")
    pro_entry = wq.add_player_to_shortlist(db, pro.id, pro_sl["shortlist_id"], workspace_data["haaland"].id)
    wq.add_entry_tag(db, pro.id, pro_entry["entry_id"], "secret-target")

    suggestions = wq.get_user_tag_suggestions(db, free.id, "left")
    assert suggestions == ["left-footed"]
    # Frequency ordering: left-footed (2) before contract expiring (1).
    assert wq.get_user_tag_suggestions(db, free.id, "") == ["left-footed", "contract expiring"]
    # Pro's private tag never surfaces for free.
    assert "secret-target" not in wq.get_user_tag_suggestions(db, free.id, "")
    assert wq.get_user_tag_suggestions(db, pro.id, "secret") == ["secret-target"]


# ---------------------------------------------------------------------------
# Detail payload joins player summary + latest index percentile
# ---------------------------------------------------------------------------


def test_detail_includes_index_percentile(db, workspace_data):
    user = workspace_data["free"]
    haaland = workspace_data["haaland"]
    # Reuse the league/team the workspace_data fixture already created.
    league = db.query(League).first()
    team = db.query(Team).first()
    now = datetime(2026, 8, 12, 3, 0, 0, tzinfo=timezone.utc)
    snap = StatSnapshot(
        player_id=haaland.id,
        team_id=team.id,
        league_id=league.id,
        season="2025-26",
        scrape_date=now,
        source="fbref",
        raw_stats={},
        minutes_played=1800.0,
        matches_played=20,
        status="published",
    )
    db.add(snap)
    db.flush()
    db.add(
        PercentileSnapshot(
            stat_snapshot_id=snap.id,
            computed_date=now,
            position_group="ST",
            league_tier="tier_1",
            metric_name="si_index",
            percentile_value=None,
            index_score=91.3,
            is_published=True,
        )
    )
    db.commit()

    sl_id = wq.list_shortlists(db, user.id)[0]["shortlist_id"]
    wq.add_player_to_shortlist(db, user.id, sl_id, haaland.id)
    entry = wq.get_shortlist_detail(db, user.id, sl_id)["entries"][0]
    assert entry["index"] == 91.3
    assert entry["snapshot_date"] == now.isoformat()


# ---------------------------------------------------------------------------
# API level (auth + error mapping + honest upsell)
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    db_module._engine = None
    db_module._session_factory = None
    create_schema()
    with TestClient(app) as c:
        yield c


from app.api.main import app  # noqa: E402


def _register(client, email: str = "api-scout@example.com"):
    resp = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "hunter2hunter"}
    )
    assert resp.status_code == 201, resp.text


def _seed_players_via_orm():
    with session_scope() as db:
        league = League(
            slug="premier-league",
            name="Premier League",
            country="England",
            tier="tier_1",
            external_ids={},
        )
        db.add(league)
        db.commit()
        team = Team(name="Arsenal", league_id=league.id, external_ids={})
        db.add(team)
        db.commit()
        player = Player(
            canonical_name="Bukayo Saka", position_group="W", external_ids={},
            current_team_id=team.id,
        )
        db.add(player)
        db.commit()
        return player.id


def test_api_workspace_requires_signin(client):
    resp = client.get("/api/v1/workspace")
    assert resp.status_code == 401


def test_api_full_flow_and_free_gate(client):
    _register(client)
    player_id = _seed_players_via_orm()

    # Overview: default shortlist auto-created for the new account.
    resp = client.get("/api/v1/workspace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["limits"]["shortlists_max"] == 1
    assert len(body["shortlists"]) == 1
    assert body["shortlists"][0]["name"] == wq.DEFAULT_SHORTLIST_NAME
    sl_id = body["shortlists"][0]["shortlist_id"]

    # Free user attempting a SECOND shortlist -> honest 403 upsell.
    resp = client.post("/api/v1/workspace", json={"name": "Second list"})
    assert resp.status_code == 403
    assert "Upgrade to Pro" in resp.json()["detail"]

    # Add a player from the (simulated) profile page.
    resp = client.post(
        f"/api/v1/workspace/{sl_id}/entries", json={"player_id": player_id}
    )
    assert resp.status_code == 201, resp.text

    # Detail carries the entry + plan context.
    resp = client.get(f"/api/v1/workspace/{sl_id}")
    assert resp.status_code == 200
    assert resp.json()["entry_count"] == 1
    entry_id = resp.json()["entries"][0]["entry_id"]
    assert resp.json()["entries"][0]["name"] == "Bukayo Saka"

    # Status change + invalid transition rejected with the specific error.
    resp = client.post(
        f"/api/v1/workspace/entries/{entry_id}/status",
        json={"status": "signed", "reason_note": "Deal done"},
    )
    assert resp.status_code == 200
    resp = client.post(
        f"/api/v1/workspace/entries/{entry_id}/status", json={"status": "monitoring"}
    )
    assert resp.status_code == 400
    assert "terminal" in resp.json()["detail"]

    # Notes + tags.
    assert (
        client.post(
            f"/api/v1/workspace/entries/{entry_id}/notes",
            json={"note_text": "Watched vs Chelsea"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/workspace/entries/{entry_id}/tags", json={"tag_text": "left-footed"}
        ).status_code
        == 201
    )
    suggestions = client.get("/api/v1/workspace/tag-suggestions?prefix=lef")
    assert suggestions.json()["tags"] == ["left-footed"]

    # Soft remove entry -> 200, then hidden from detail.
    assert (
        client.post(f"/api/v1/workspace/entries/{entry_id}/remove").status_code == 200
    )
    resp = client.get(f"/api/v1/workspace/{sl_id}")
    assert resp.json()["entry_count"] == 0


def test_api_cross_user_404_not_403(client):
    _register(client, "first@example.com")
    # Fetch the first user's shortlist id while STILL signed in as them.
    first = client.get("/api/v1/workspace").json()["shortlists"][0]["shortlist_id"]

    # Switch to a second account entirely.
    client.post("/api/v1/auth/logout")
    _register(client, "second@example.com")
    # 404 — never a 403 that would confirm the shortlist exists.
    resp = client.get(f"/api/v1/workspace/{first}")
    assert resp.status_code == 404
    resp = client.post(f"/api/v1/workspace/{first}/entries", json={"player_id": 1})
    assert resp.status_code == 404
