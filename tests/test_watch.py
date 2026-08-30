"""Phase 10 — Watchlist & alerts test suite.

The two non-negotiable quality bars (docs/product/alert-trigger-definitions.md):

1. NOISE-AVOIDANCE — "what counts as alert-worthy" is precise and boundary-
   tested. Hand-calculated synthetic snapshot pairs verify: a movement just
   below the threshold does NOT alert, just above DOES, exactly at the
   threshold DOES (inclusive). Idempotency: re-running detection for the same
   snapshot transition creates no duplicates. Club change fires ONCE per
   transfer, never per subsequent weekly snapshot.
2. PREFERENCE COMPLIANCE — delivery never sends email for an opted-out
   trigger type or channel. This is tested as rigorously as an authorization
   check: generate a trigger for an opted-out user and assert no email is
   sent. Digest batching combines multiple alerts into ONE email.

Plus: watch CRUD with ownership (404 pattern, never 403), free-tier cap with
honest upsell, alert read/dismiss, one-click unsubscribe (signed link),
new-season and coverage-change triggers, and API-level checks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.config import get_settings
from app.db import create_schema
from app.models import (

pytestmark = pytest.mark.slow
    DataCoverage,
    IngestionAnomaly,
    League,
    NotificationPreferences,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Subscription,
    Team,
    User,
    Watch,
    WatchAlert,
)
from app.queries import watch_queries as wq
from app.watch import delivery
from app.watch.detection import (
    ALERT_TYPE_CLUB,
    ALERT_TYPE_COVERAGE,
    ALERT_TYPE_NEW_SEASON,
    ALERT_TYPE_PERCENTILE,
    detect_watch_triggers,
)

SNAPSHOT_1 = datetime(2026, 8, 5, 3, 0, 0, tzinfo=timezone.utc)
SNAPSHOT_2 = datetime(2026, 8, 12, 3, 0, 0, tzinfo=timezone.utc)
SNAPSHOT_3 = datetime(2026, 8, 19, 3, 0, 0, tzinfo=timezone.utc)
SEASON = "2025-26"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_user(db, email: str = "watcher@example.com", plan: str = "free") -> User:
    user = User(email=email, password_hash="x" * 64, plan=plan)
    db.add(user)
    db.commit()
    return user


def make_pro_user(db, email: str = "pro-watcher@example.com") -> User:
    user = make_user(db, email, plan="pro")
    db.add(
        Subscription(
            user_id=user.id, plan="pro", stripe_subscription_id="sub_x", status="active"
        )
    )
    db.commit()
    return user


@pytest.fixture()
def watch_data(db):
    """One free + one pro user, one league, two teams, two players."""
    free = make_user(db, "free-watcher@example.com")
    pro = make_pro_user(db, "pro-watcher@example.com")
    league = League(
        slug="premier-league",
        name="Premier League",
        country="England",
        tier="tier_1",
        external_ids={},
    )
    db.add(league)
    db.commit()
    city = Team(name="Manchester City", league_id=league.id, external_ids={})
    db.add(city)
    db.commit()
    arsenal = Team(name="Arsenal", league_id=league.id, external_ids={})
    db.add(arsenal)
    db.commit()
    haaland = Player(
        canonical_name="Erling Haaland",
        position_group="ST",
        primary_position="Striker",
        external_ids={},
        current_team_id=city.id,
    )
    db.add(haaland)
    db.commit()
    return {
        "free": free,
        "pro": pro,
        "league": league,
        "city": city,
        "arsenal": arsenal,
        "haaland": haaland,
    }


def seed_snapshot(
    db,
    player: Player,
    *,
    snapshot_date: datetime,
    season: str = SEASON,
    team: Team | None = None,
    minutes: float = 1800.0,
    percentiles: dict[str, float] | None = None,
) -> StatSnapshot:
    """One published snapshot with hand-set percentile values (published so the
    detection job's published-only queries see it)."""
    team = team or (
        db.get(Team, player.current_team_id) if player.current_team_id else None
    )
    league_tier = "tier_1"
    if team is not None:
        league = db.get(League, team.league_id)
        league_tier = league.tier if league else "tier_1"
    snap = StatSnapshot(
        player_id=player.id,
        team_id=team.id if team else None,
        league_id=team.league_id if team else None,
        season=season,
        scrape_date=snapshot_date,
        source="fbref",
        raw_stats={},
        minutes_played=minutes,
        matches_played=int(minutes / 90),
        status="published",
    )
    db.add(snap)
    db.flush()
    for metric, value in (percentiles or {}).items():
        db.add(
            PercentileSnapshot(
                stat_snapshot_id=snap.id,
                computed_date=snapshot_date,
                position_group=player.position_group,
                league_tier=league_tier,
                metric_name=metric,
                percentile_value=value,
                index_score=None,
                is_published=True,
            )
        )
    db.commit()
    return snap


def seed_watch(db, user: User, entity_type: str, entity_id: int, **kw) -> Watch:
    w = Watch(user_id=user.id, entity_type=entity_type, entity_id=entity_id, **kw)
    db.add(w)
    db.commit()
    return w


PCT_METRIC = "si_prgp_p90"


# ---------------------------------------------------------------------------
# Detection — percentile-movement boundary behavior (Part C3)
# ---------------------------------------------------------------------------


def test_movement_below_threshold_does_not_alert(db, watch_data):
    """62 -> 74 = +12: below the 15-point bar -> NO alert."""
    user, haaland = watch_data["pro"], watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 62.0})
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 74.0})

    report = detect_watch_triggers(db, SNAPSHOT_2)
    assert report.alerts_created == 0
    assert db.query(WatchAlert).count() == 0


def test_movement_above_threshold_alerts(db, watch_data):
    """62 -> 81 = +19: above the bar -> alert with real detail values."""
    user, haaland = watch_data["pro"], watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 62.0})
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 81.0})

    report = detect_watch_triggers(db, SNAPSHOT_2)
    assert report.alerts_created == 1
    assert report.by_type[ALERT_TYPE_PERCENTILE] == 1
    alert = db.query(WatchAlert).one()
    assert alert.alert_type == ALERT_TYPE_PERCENTILE
    # detail is traceable to the real snapshot rows
    detail = alert.detail
    assert detail["metric"] == PCT_METRIC
    assert detail["metric_name"] == "Progressive passes per 90"
    assert detail["from_percentile"] == 62.0
    assert detail["to_percentile"] == 81.0
    assert detail["from_snapshot_date"] == SNAPSHOT_1.date().isoformat()
    assert detail["to_snapshot_date"] == SNAPSHOT_2.date().isoformat()
    assert detail["entity_name"] == "Erling Haaland"


def test_movement_exactly_at_threshold_alerts_inclusive(db, watch_data):
    """62 -> 77 = +15: exactly at the bar -> alerts (documented INCLUSIVE)."""
    user, haaland = watch_data["pro"], watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 62.0})
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 77.0})
    report = detect_watch_triggers(db, SNAPSHOT_2)
    assert report.alerts_created == 1


def test_movement_below_qualification_never_alerts(db, watch_data):
    """A movement where either snapshot is below the qualification floor does
    not alert (a player who isn't reliably measurable can't have a meaningful
    percentile move)."""
    user, haaland = watch_data["pro"], watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_1,
        minutes=800.0,
        percentiles={PCT_METRIC: 40.0},
    )
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_2,
        minutes=1500.0,
        percentiles={PCT_METRIC: 80.0},
    )
    report = detect_watch_triggers(db, SNAPSHOT_2)
    assert report.alerts_created == 0


def test_watched_metrics_refinement_limits_alerts(db, watch_data):
    """A watch with followed_metrics=[...] alerts ONLY on those metrics — a big
    move in an unwatched metric stays silent."""
    user, haaland = watch_data["pro"], watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id, followed_metrics=["si_tkl_p90"])
    # prgp moves +30 (would alert under broad watch) but tkl moves +2.
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_1,
        percentiles={PCT_METRIC: 50.0, "si_tkl_p90": 55.0},
    )
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_2,
        percentiles={PCT_METRIC: 80.0, "si_tkl_p90": 57.0},
    )
    report = detect_watch_triggers(db, SNAPSHOT_2)
    assert report.alerts_created == 0


# ---------------------------------------------------------------------------
# Idempotency (Part C1/C3)
# ---------------------------------------------------------------------------


def test_detection_is_idempotent_no_duplicate_alerts(db, watch_data):
    user, haaland = watch_data["pro"], watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 62.0})
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 81.0})

    first = detect_watch_triggers(db, SNAPSHOT_2)
    second = detect_watch_triggers(db, SNAPSHOT_2)
    assert first.alerts_created == 1
    assert second.alerts_created == 0  # re-run creates nothing
    assert db.query(WatchAlert).count() == 1


# ---------------------------------------------------------------------------
# Club change fires once (Part A2/C3)
# ---------------------------------------------------------------------------


def test_club_change_alerts_and_fires_once(db, watch_data):
    """3 consecutive snapshots with ONE transfer: exactly one club-change
    alert, not one per subsequent snapshot."""
    user, haaland = watch_data["pro"], watch_data["haaland"]
    city, arsenal = watch_data["city"], watch_data["arsenal"]
    seed_watch(db, user, "player", haaland.id)
    # Snapshot 1: at City. Snapshot 2: transfer to Arsenal (detected).
    # Snapshot 3: still at Arsenal — no second alert.
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_1,
        team=city,
        percentiles={PCT_METRIC: 60.0},
    )
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_2,
        team=arsenal,
        percentiles={PCT_METRIC: 65.0},
    )
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_3,
        team=arsenal,
        percentiles={PCT_METRIC: 66.0},
    )

    detect_watch_triggers(db, SNAPSHOT_2)
    detect_watch_triggers(db, SNAPSHOT_3)  # same club — no new alert
    club_alerts = (
        db.query(WatchAlert).filter(WatchAlert.alert_type == ALERT_TYPE_CLUB).all()
    )
    assert len(club_alerts) == 1
    detail = club_alerts[0].detail
    assert detail["from_team"] == "Manchester City"
    assert detail["to_team"] == "Arsenal"
    assert detail["snapshot_date"] == SNAPSHOT_2.date().isoformat()
    assert detail["entity_name"] == "Erling Haaland"


# ---------------------------------------------------------------------------
# New-season + coverage triggers (Part A2/C2)
# ---------------------------------------------------------------------------


def test_new_season_data_alerts_once(db, watch_data):
    user, haaland = watch_data["pro"], watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_1,
        season="2024-25",
        percentiles={PCT_METRIC: 60.0},
    )
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_2,
        season="2025-26",
        percentiles={PCT_METRIC: 62.0},
    )
    detect_watch_triggers(db, SNAPSHOT_2)
    detect_watch_triggers(db, SNAPSHOT_2)  # idempotent
    season_alerts = (
        db.query(WatchAlert)
        .filter(WatchAlert.alert_type == ALERT_TYPE_NEW_SEASON)
        .all()
    )
    assert len(season_alerts) == 1
    assert season_alerts[0].detail["new_season"] == "2025-26"
    assert season_alerts[0].detail["previous_season"] == "2024-25"


def test_coverage_gained_alerts(db, watch_data):
    user, haaland = watch_data["pro"], watch_data["haaland"]
    league = watch_data["league"]
    seed_watch(db, user, "player", haaland.id)
    # Previous season: NO statsbomb coverage. New season: coverage exists.
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_1,
        season="2024-25",
        percentiles={PCT_METRIC: 60.0},
    )
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_2,
        season="2025-26",
        percentiles={PCT_METRIC: 62.0},
    )
    db.add(
        DataCoverage(
            league_id=league.id,
            source="statsbomb",
            source_identifier="statsbomb:2:2025-26",
            seasons_available=["2025-26"],
            status="active",
        )
    )
    db.commit()

    detect_watch_triggers(db, SNAPSHOT_2)
    coverage_alerts = (
        db.query(WatchAlert).filter(WatchAlert.alert_type == ALERT_TYPE_COVERAGE).all()
    )
    assert len(coverage_alerts) == 1
    assert coverage_alerts[0].detail["signal"] == "coverage_gained"
    assert coverage_alerts[0].detail["coverage_source"] == "statsbomb"


def test_source_anomaly_alerts(db, watch_data):
    user, haaland = watch_data["pro"], watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 60.0})
    snap = seed_snapshot(
        db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 62.0}
    )
    db.add(
        IngestionAnomaly(
            stat_snapshot_id=snap.id,
            field_name="minutes_played",
            raw_value="999999",
            expected_range="0-4000",
            resolved=False,
        )
    )
    db.commit()

    detect_watch_triggers(db, SNAPSHOT_2)
    alerts = db.query(WatchAlert).all()
    assert any(
        a.alert_type == ALERT_TYPE_COVERAGE and a.detail["signal"] == "source_anomaly"
        for a in alerts
    )


# ---------------------------------------------------------------------------
# Watch CRUD + authorization (Part B2/E)
# ---------------------------------------------------------------------------


def test_follow_and_list(db, watch_data):
    user, haaland = watch_data["free"], watch_data["haaland"]
    payload = wq.follow_entity(db, user.id, "player", haaland.id)
    assert payload["entity_name"] == "Erling Haaland"
    assert payload["followed_metrics"] is None

    watches = wq.list_watches(db, user.id)
    assert len(watches) == 1
    assert watches[0]["entity_name"] == "Erling Haaland"
    assert watches[0]["unread_alert_count"] == 0


def test_follow_is_idempotent_unique_entity(db, watch_data):
    user, haaland = watch_data["free"], watch_data["haaland"]
    first = wq.follow_entity(db, user.id, "player", haaland.id)
    second = wq.follow_entity(db, user.id, "player", haaland.id)
    assert first["watch_id"] == second["watch_id"]
    assert db.query(Watch).count() == 1


def test_follow_unknown_entity_rejected(db, watch_data):
    user = watch_data["free"]
    with pytest.raises(wq.EntityNotFound):
        wq.follow_entity(db, user.id, "player", 999_999)
    with pytest.raises(wq.EntityNotFound):
        wq.follow_entity(db, user.id, "team", 999_999)


def test_follow_team(db, watch_data):
    user, city = watch_data["free"], watch_data["city"]
    payload = wq.follow_entity(db, user.id, "team", city.id)
    assert payload["entity_name"] == "Manchester City"
    watches = wq.list_watches(db, user.id)
    assert watches[0]["entity_type"] == "team"
    assert watches[0]["league"] == "Premier League"


def test_unfollow_deletes_watch_keeps_alerts(db, watch_data):
    user, haaland = watch_data["pro"], watch_data["haaland"]
    watch = seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 62.0})
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 81.0})
    detect_watch_triggers(db, SNAPSHOT_2)
    assert db.query(WatchAlert).count() == 1

    wq.unfollow_entity(db, user.id, watch.id)
    assert db.query(Watch).count() == 0
    # Alert history retained (audit bias — never silently destroyed).
    assert db.query(WatchAlert).count() == 1


def test_cannot_view_or_modify_another_users_watch(db, watch_data):
    free, pro = watch_data["free"], watch_data["pro"]
    haaland = watch_data["haaland"]
    watch = seed_watch(db, free, "player", haaland.id)
    with pytest.raises(wq.WatchNotFound):
        wq.unfollow_entity(db, pro.id, watch.id)
    # The pro user's own watchlist is simply empty — nothing leaked.
    assert wq.list_watches(db, pro.id) == []
    assert wq.list_watches(db, free.id)[0]["watch_id"] == watch.id


def test_free_tier_watch_cap(db, watch_data):
    user, league = watch_data["free"], watch_data["league"]
    limit = 10
    for i in range(limit):
        team = Team(name=f"Team {i}", league_id=league.id, external_ids={})
        db.add(team)
        db.commit()
        wq.follow_entity(db, user.id, "team", team.id)
    overflow = Team(name="Overflow FC", league_id=league.id, external_ids={})
    db.add(overflow)
    db.commit()
    with pytest.raises(wq.WatchLimitExceeded) as excinfo:
        wq.follow_entity(db, user.id, "team", overflow.id)
    assert "Upgrade to Pro" in str(excinfo.value)


def test_pro_user_unlimited_watches(db, watch_data):
    user, league = watch_data["pro"], watch_data["league"]
    for i in range(12):  # above the free cap
        team = Team(name=f"Pro Team {i}", league_id=league.id, external_ids={})
        db.add(team)
        db.commit()
        wq.follow_entity(db, user.id, "team", team.id)
    assert len(wq.list_watches(db, user.id)) == 12


# ---------------------------------------------------------------------------
# Alerts read/dismiss + ownership
# ---------------------------------------------------------------------------


def _make_alert(db, watch_data, user=None) -> WatchAlert:
    user = user or watch_data["pro"]
    haaland = watch_data["haaland"]
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 62.0})
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 81.0})
    detect_watch_triggers(db, SNAPSHOT_2)
    return db.query(WatchAlert).one()


def test_alert_read_and_dismiss(db, watch_data):
    user = watch_data["pro"]
    alert = _make_alert(db, watch_data, user)

    unread = wq.list_alerts(db, user.id)
    assert len(unread) == 1

    wq.mark_alert_read(db, user.id, alert.id)
    assert wq.list_alerts(db, user.id) == []  # default view: unread only
    assert len(wq.list_alerts(db, user.id, include_read=True)) == 1

    wq.dismiss_alert(db, user.id, alert.id)
    assert wq.list_alerts(db, user.id, include_read=True) == []
    assert (
        len(wq.list_alerts(db, user.id, include_read=True, include_dismissed=True)) == 1
    )

    detail = wq.get_alert(db, user.id, alert.id)
    assert detail["alert_type"] == ALERT_TYPE_PERCENTILE
    assert detail["detail"]["from_percentile"] == 62.0
    assert detail["detail"]["to_percentile"] == 81.0
    assert detail["entity_name"] == "Erling Haaland"


def test_cannot_read_another_users_alert(db, watch_data):
    free, pro = watch_data["free"], watch_data["pro"]
    alert = _make_alert(db, watch_data, pro)
    with pytest.raises(wq.WatchNotFound):
        wq.get_alert(db, free.id, alert.id)
    with pytest.raises(wq.WatchNotFound):
        wq.mark_alert_read(db, free.id, alert.id)
    with pytest.raises(wq.WatchNotFound):
        wq.dismiss_alert(db, free.id, alert.id)


# ---------------------------------------------------------------------------
# Preferences (Part B2/D)
# ---------------------------------------------------------------------------


def test_preferences_defaults_and_update(db, watch_data):
    user = watch_data["free"]
    prefs = wq.get_preferences(db, user.id)
    assert prefs["email_enabled"] is True
    assert prefs["digest_frequency"] == "immediate"
    assert prefs["alert_type_preferences"][ALERT_TYPE_PERCENTILE] is True

    updated = wq.update_preferences(
        db,
        user.id,
        email_enabled=False,
        alert_type_preferences={ALERT_TYPE_CLUB: False},
        digest_frequency="weekly_digest",
    )
    assert updated["email_enabled"] is False
    assert updated["alert_type_preferences"] == {ALERT_TYPE_CLUB: False}
    assert updated["digest_frequency"] == "weekly_digest"

    # Partial update leaves other fields untouched.
    again = wq.update_preferences(db, user.id, email_enabled=True)
    assert again["email_enabled"] is True
    assert again["digest_frequency"] == "weekly_digest"


def test_preferences_reject_unknown_values(db, watch_data):
    user = watch_data["free"]
    with pytest.raises(ValueError) as excinfo:
        wq.update_preferences(
            db, user.id, alert_type_preferences={"transfer_rumours": True}
        )
    assert "transfer_rumours" in str(excinfo.value)
    with pytest.raises(ValueError):
        wq.update_preferences(db, user.id, digest_frequency="hourly_digest")


# ---------------------------------------------------------------------------
# Delivery — preference compliance (Part D4 — the critical category)
# ---------------------------------------------------------------------------


def _fake_sender(sent: list):
    from app.notifications.email import EmailMessage

    def send(message: EmailMessage):
        sent.append(message)

    return send


def test_opted_out_trigger_type_produces_no_email(db, watch_data):
    """THE preference-compliance test: a user opted out of percentile-movement
    alerts gets NO email even though a real trigger fired."""
    user = watch_data["pro"]
    wq.update_preferences(
        db, user.id, alert_type_preferences={ALERT_TYPE_PERCENTILE: False}
    )
    _make_alert(db, watch_data, user)  # the trigger fired

    sent: list = []
    stats = delivery.deliver_immediate(db, sender=_fake_sender(sent))
    assert stats["delivered"] == 0
    assert stats["skipped_opt_out"] == 1
    assert sent == []  # no email — compliance is absolute


def test_email_disabled_produces_no_email(db, watch_data):
    user = watch_data["pro"]
    wq.update_preferences(db, user.id, email_enabled=False)
    _make_alert(db, watch_data, user)

    sent: list = []
    stats = delivery.deliver_immediate(db, sender=_fake_sender(sent))
    assert stats["delivered"] == 0
    assert stats["skipped_opt_out"] == 1
    assert sent == []


def test_digest_frequency_user_gets_no_immediate_email(db, watch_data):
    user = watch_data["pro"]
    wq.update_preferences(db, user.id, digest_frequency="daily_digest")
    _make_alert(db, watch_data, user)

    sent: list = []
    stats = delivery.deliver_immediate(db, sender=_fake_sender(sent))
    assert stats["delivered"] == 0
    assert stats["skipped_opt_out"] == 1
    assert sent == []


def test_immediate_email_sent_with_real_content_and_unsubscribe(db, watch_data):
    user = watch_data["pro"]
    _make_alert(db, watch_data, user)

    sent: list = []
    stats = delivery.deliver_immediate(db, sender=_fake_sender(sent))
    assert stats["delivered"] == 1
    assert len(sent) == 1
    message = sent[0]
    assert message.to == user.email
    # Real, specific copy — real numbers from the alert detail, never generic.
    assert "Progressive passes per 90" in message.subject
    assert "62nd" in message.html
    assert "81st" in message.html
    assert "Erling Haaland" in message.html
    # One-click unsubscribe: List-Unsubscribe header + footer link present.
    assert "List-Unsubscribe" in message.headers
    assert "List-Unsubscribe=One-Click" in message.headers.get(
        "List-Unsubscribe-Post", ""
    )
    assert "unsubscribe" in message.headers["List-Unsubscribe"].lower()

    # Delivered alerts are not re-sent.
    stats2 = delivery.deliver_immediate(db, sender=_fake_sender(sent))
    assert stats2["delivered"] == 0
    assert len(sent) == 1


def test_digest_batches_multiple_alerts_into_one_email(db, watch_data):
    """Two alerts in the period -> ONE digest email, not two."""
    user, haaland = watch_data["pro"], watch_data["haaland"]
    wq.update_preferences(db, user.id, digest_frequency="daily_digest")
    seed_watch(db, user, "player", haaland.id)
    # Two distinct metrics crossing the threshold in the same transition.
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_1,
        percentiles={PCT_METRIC: 62.0, "si_tkl_p90": 40.0},
    )
    seed_snapshot(
        db,
        haaland,
        snapshot_date=SNAPSHOT_2,
        percentiles={PCT_METRIC: 81.0, "si_tkl_p90": 70.0},
    )
    report = detect_watch_triggers(db, SNAPSHOT_2)
    assert report.alerts_created == 2

    sent: list = []
    stats = delivery.send_digests(db, "daily_digest", sender=_fake_sender(sent))
    assert stats["digests_sent"] == 1
    assert stats["alerts_included"] == 2
    assert len(sent) == 1  # batched — one email
    assert "2 watchlist updates" in sent[0].subject
    assert "Progressive passes per 90" in sent[0].html
    assert "Tackles per 90" in sent[0].html

    # Both alerts marked delivered; a second digest run sends nothing.
    stats2 = delivery.send_digests(db, "daily_digest", sender=_fake_sender(sent))
    assert stats2["digests_sent"] == 0
    assert len(sent) == 1


def test_digest_respects_per_type_opt_out(db, watch_data):
    """A digest user opted out of percentile alerts: the digest skips that
    alert entirely (it is neither emailed nor marked delivered)."""
    user, haaland = watch_data["pro"], watch_data["haaland"]
    wq.update_preferences(
        db,
        user.id,
        digest_frequency="daily_digest",
        alert_type_preferences={ALERT_TYPE_PERCENTILE: False},
    )
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 62.0})
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 81.0})
    detect_watch_triggers(db, SNAPSHOT_2)
    assert db.query(WatchAlert).count() == 1

    sent: list = []
    stats = delivery.send_digests(db, "daily_digest", sender=_fake_sender(sent))
    assert stats["digests_sent"] == 0
    assert sent == []


def test_weekly_digest_only_on_monday(db, watch_data):
    user, haaland = watch_data["pro"], watch_data["haaland"]
    wq.update_preferences(db, user.id, digest_frequency="weekly_digest")
    seed_watch(db, user, "player", haaland.id)
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_1, percentiles={PCT_METRIC: 62.0})
    seed_snapshot(db, haaland, snapshot_date=SNAPSHOT_2, percentiles={PCT_METRIC: 81.0})
    detect_watch_triggers(db, SNAPSHOT_2)

    sent: list = []
    # Wednesday (2026-08-12) — weekly digest NOT due.
    wednesday = datetime(2026, 8, 12, 3, 0, 0, tzinfo=timezone.utc)
    results = delivery.run_due_digests(db, sender=_fake_sender(sent), now=wednesday)
    assert results["weekly_digest"] == 0
    assert sent == []
    # Monday (2026-08-17) — due.
    monday = datetime(2026, 8, 17, 3, 0, 0, tzinfo=timezone.utc)
    results = delivery.run_due_digests(db, sender=_fake_sender(sent), now=monday)
    assert results["weekly_digest"] == 1
    assert len(sent) == 1


# ---------------------------------------------------------------------------
# One-click unsubscribe (Part D1)
# ---------------------------------------------------------------------------


def test_unsubscribe_token_rotation(db, watch_data):
    user = watch_data["free"]
    wq.get_preferences(db, user.id)
    first = wq.rotate_unsubscribe_token(db, user.id)["unsubscribe_token"]
    second = wq.rotate_unsubscribe_token(db, user.id)["unsubscribe_token"]
    assert first != second  # old email links are invalidated


# ---------------------------------------------------------------------------
# API level
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    db_module._engine = None
    db_module._session_factory = None
    create_schema()
    with TestClient(app) as c:
        yield c


from app.api.main import app


def _register(client, email: str = "api-watcher@example.com"):
    resp = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Hunter2hunter!"}
    )
    assert resp.status_code == 201, resp.text


def _seed_api_entity(db):
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
        canonical_name="Bukayo Saka",
        position_group="W",
        external_ids={},
        current_team_id=team.id,
    )
    db.add(player)
    db.commit()
    return player.id, team.id


def test_api_watch_requires_signin(client):
    assert client.get("/api/v1/watch").status_code == 401
    assert client.get("/api/v1/watch/alerts").status_code == 401
    assert client.get("/api/v1/watch/preferences").status_code == 401


def test_api_follow_flow_alert_list_and_preferences(client, db):
    with db_module.session_scope() as session:
        player_id, _team_id = _seed_api_entity(session)
    _register(client)

    resp = client.post(
        "/api/v1/watch", json={"entity_type": "player", "entity_id": player_id}
    )
    assert resp.status_code == 201, resp.text
    watch_id = resp.json()["watch_id"]

    watches = client.get("/api/v1/watch").json()["watches"]
    assert watches[0]["entity_name"] == "Bukayo Saka"

    # Preferences round-trip.
    prefs = client.get("/api/v1/watch/preferences").json()
    assert prefs["email_enabled"] is True
    resp = client.put(
        "/api/v1/watch/preferences",
        json={
            "digest_frequency": "weekly_digest",
            "alert_type_preferences": {"club_change": False},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["digest_frequency"] == "weekly_digest"

    # Unfollow.
    resp = client.post(f"/api/v1/watch/{watch_id}/unfollow")
    assert resp.status_code == 200
    assert client.get("/api/v1/watch").json()["watches"] == []


def test_api_free_cap_honest_upsell(client, db):
    with db_module.session_scope() as session:
        _league = League(
            slug="premier-league",
            name="Premier League",
            country="England",
            tier="tier_1",
            external_ids={},
        )
        session.add(_league)
        session.commit()
        team_ids = []
        for i in range(11):
            t = Team(name=f"Team {i}", league_id=_league.id, external_ids={})
            session.add(t)
            session.commit()
            team_ids.append(t.id)
    _register(client)
    for tid in team_ids[:10]:
        resp = client.post(
            "/api/v1/watch", json={"entity_type": "team", "entity_id": tid}
        )
        assert resp.status_code == 201, resp.text
    resp = client.post(
        "/api/v1/watch", json={"entity_type": "team", "entity_id": team_ids[10]}
    )
    assert resp.status_code == 403
    body = resp.json()
    msg = body.get("detail") or body.get("error", {}).get("message", "")
    assert "Upgrade to Pro" in msg


def test_api_cross_user_watch_404(client, db):
    with db_module.session_scope() as session:
        player_id, _ = _seed_api_entity(session)
    _register(client, "first@example.com")
    watch_id = client.post(
        "/api/v1/watch", json={"entity_type": "player", "entity_id": player_id}
    ).json()["watch_id"]

    client.post("/api/v1/auth/logout")
    _register(client, "second@example.com")
    resp = client.post(f"/api/v1/watch/{watch_id}/unfollow")
    assert resp.status_code == 404  # never 403 — existence must not leak


def test_e2e_seed_alert_fixture_disabled_outside_e2e(client):
    """The e2e fixture route (seed-alert) is hard-disabled when the e2e flag
    is not set — production can never create alerts through it."""
    resp = client.post(
        "/api/v1/e2e/seed-alert",
        json={"email": "x@example.com", "player_id": 1},
    )
    assert resp.status_code == 403
    body = resp.json()
    msg = body.get("detail") or body.get("error", {}).get("message", "")
    assert "e2e fixtures are disabled" in msg


def test_api_unsubscribe_sessionless(client, db):
    """The one-click unsubscribe link works without a session (it's clicked
    from email) and invalid signatures are rejected honestly."""
    with db_module.session_scope() as session:
        _seed_api_entity(session)
    _register(client)
    token = client.post("/api/v1/watch/preferences/rotate-token").json()[
        "unsubscribe_token"
    ]
    client.get("/api/v1/watch/preferences")  # ensure the row exists

    settings = get_settings()
    settings.alert_signing_secret = "test-secret"
    import hashlib
    import hmac

    # Simulate the email link (signed by the same secret).
    def _make_url(uid, tok):
        sig = hmac.new(
            b"test-secret", f"{uid}:{tok}".encode(), hashlib.sha256
        ).hexdigest()[:32]
        return f"/api/v1/watch/unsubscribe?user={uid}&token={tok}&sig={sig}"

    # Find the user id from the DB.
    with db_module.session_scope() as session:
        from app.models import User as UserModel


        uid = session.query(UserModel).first().id

    client.post("/api/v1/auth/logout")  # sessionless click

    # Invalid signature -> honest 400.
    resp = client.get(
        f"/api/v1/watch/unsubscribe?user={uid}&token={token}&sig=deadbeef"
    )
    assert resp.status_code == 400

    # Valid signature -> 200, email disabled.
    resp = client.get(_make_url(uid, token))
    assert resp.status_code == 200
    with db_module.session_scope() as session:
        prefs = session.query(NotificationPreferences).filter_by(user_id=uid).first()
        assert prefs.email_enabled is False
