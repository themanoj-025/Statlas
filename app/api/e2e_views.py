"""E2E fixture routes (dev/test only — never available in production).

Playwright needs to exercise Pro-gated features (Phase 9 reports) and alert
generation (Phase 10 watchlist) against the real stack. These routes are hard-
gated behind REPORTS_DEV_NARRATOR=1 — the flag ONLY e2e-server.sh and the
unit-test fixtures set; production never sets it, so these routes 403 there.
Registering a real subscription via Stripe in a browser test would be both
slow and flaky; this fixture grants the same Subscription row the unit suite
creates directly. The alert fixture seeds the same published snapshot pair the
unit suite constructs by hand (a percentile move crossing the documented 15-
point threshold) and runs the real detection job.

If future phases need more e2e fixtures, generalise this router rather than
adding another flag.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import get_settings, load_registry
from app.db import session_scope
from app.models import (
    League,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Subscription,
    Team,
    User,
    Watch,
    WatchAlert,
)

router = APIRouter(prefix="/api/v1/e2e", tags=["e2e-fixtures"])


def _require_e2e() -> None:
    if not get_settings().reports_dev_narrator:
        raise HTTPException(status_code=403, detail="e2e fixtures are disabled")


class GrantProBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)


@router.post("/grant-pro")
def grant_pro(
    body: GrantProBody, _request: Request
) -> dict[str, str]:
    """Give a registered account active Pro access (an e2e fixture)."""
    _require_e2e()
    with session_scope() as db:
        user = db.query(User).filter_by(email=body.email).first()
        if user is None:
            raise HTTPException(
                status_code=404, detail="user not found — register first"
            )
        existing = (
            db.query(Subscription)
            .filter(Subscription.user_id == user.id, Subscription.status == "active")
            .first()
        )
        if existing is None:
            db.add(
                Subscription(
                    user_id=user.id,
                    plan="pro",
                    stripe_subscription_id=f"e2e_{user.id}",
                    status="active",
                )
            )
            db.commit()
    return {"ok": True}


class SeedAlertBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    player_id: int
    metric: str = "si_prgp_p90"
    from_percentile: float = 45.0
    to_percentile: float = 72.0  # +27 — well past the 15-point threshold


@router.post("/seed-alert")
def seed_alert(body: SeedAlertBody) -> dict[str, str]:
    """Follow a player for the account and generate a REAL percentile-movement
    alert via the actual detection job (an e2e fixture; disabled outside e2e).

    Seeds a published snapshot pair with a hand-set percentile movement past
    the documented threshold (alert-trigger-definitions.md §2.1), then runs
    detect_watch_triggers exactly as the weekly refresh does. Every value in
    the resulting alert is traceable to the seeded snapshot rows.
    """
    _require_e2e()
    with session_scope() as db:
        user = db.query(User).filter_by(email=body.email).first()
        if user is None:
            raise HTTPException(
                status_code=404, detail="user not found — register first"
            )
        player = db.get(Player, body.player_id)
        if player is None:
            raise HTTPException(status_code=404, detail="player not found")

        # Follow (idempotent) and pin the followed metric so the detection job
        # evaluates THIS metric regardless of the player's position-group set
        # (e.g. progressive_passes_p90 is not a GK metric — see
        # alert-trigger-definitions.md §3 on metric-specific follows).
        watch = (
            db.query(Watch)
            .filter(
                Watch.user_id == user.id,
                Watch.entity_type == "player",
                Watch.entity_id == player.id,
            )
            .first()
        )
        if watch is None:
            watch = Watch(user_id=user.id, entity_type="player", entity_id=player.id)
            db.add(watch)
            db.flush()
        watch.followed_metrics = [body.metric]

        # This watch's alerts are fixture-owned — purge them so re-runs are
        # deterministic (fresh detection creates them again).
        db.query(WatchAlert).filter(WatchAlert.watch_id == watch.id).delete(
            synchronize_session=False
        )

        # Purge this fixture's OWN prior seeds for the player (identified by
        # the fixture signature: empty raw_stats). Real pipeline snapshots
        # always carry real raw_stats, so they are never touched.
        prior = (
            db.query(StatSnapshot)
            .filter(
                StatSnapshot.player_id == player.id,
                StatSnapshot.raw_stats == {},
            )
            .all()
        )
        if prior:
            prior_ids = [s.id for s in prior]
            db.query(PercentileSnapshot).filter(
                PercentileSnapshot.stat_snapshot_id.in_(prior_ids)
            ).delete(synchronize_session=False)
            for s in prior:
                db.delete(s)
            db.flush()

        # A league/team context for the player (reuse existing snapshot data if
        # present, otherwise create one so the detection queries resolve).
        existing_snap = (
            db.query(StatSnapshot).filter(StatSnapshot.player_id == player.id).first()
        )
        if existing_snap is not None:
            team_id, league_id, season = (
                existing_snap.team_id,
                existing_snap.league_id,
                existing_snap.season,
            )
        else:
            league = db.query(League).first()
            team = db.query(Team).first()
            if league is None or team is None:
                raise HTTPException(
                    status_code=500, detail="no league/team seeded — seed data first"
                )
            from app.config import CURRENT_SEASON
            team_id, league_id, season = team.id, league.id, CURRENT_SEASON

        # The fixture pair must BE the two most recent published snapshots for
        # the player — otherwise the detection job compares against whatever
        # real snapshot exists and the seeded movement is invisible. Both dates
        # are anchored strictly AFTER the player's newest existing published
        # snapshot, so no real snapshot can sit between them.
        newest = (
            db.query(StatSnapshot.scrape_date)
            .join(
                PercentileSnapshot,
                PercentileSnapshot.stat_snapshot_id == StatSnapshot.id,
            )
            .filter(
                StatSnapshot.player_id == player.id,
                PercentileSnapshot.is_published.is_(True),
            )
            .order_by(StatSnapshot.scrape_date.desc())
            .first()
        )
        anchor = newest[0] if newest and newest[0] else datetime.now(timezone.utc)
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=timezone.utc)
        prev_date = anchor + timedelta(days=1)
        curr_date = anchor + timedelta(days=2)
        registry = load_registry()
        minutes = float(registry["qualifying_minutes"]) + 500

        def _seed_snapshot(date: datetime, percentile: float) -> StatSnapshot:
            snap = StatSnapshot(
                player_id=player.id,
                team_id=team_id,
                league_id=league_id,
                season=season,
                scrape_date=date,
                source="fbref",
                raw_stats={},
                minutes_played=minutes,
                matches_played=20,
                status="published",
            )
            db.add(snap)
            db.flush()
            db.add(
                PercentileSnapshot(
                    stat_snapshot_id=snap.id,
                    computed_date=date,
                    position_group=player.position_group or "ST",
                    league_tier=(
                        db.get(League, league_id).tier
                        if db.get(League, league_id)
                        else "tier_1"
                    ),
                    metric_name=body.metric,
                    percentile_value=percentile,
                    index_score=None,
                    is_published=True,
                )
            )
            return snap

        _seed_snapshot(prev_date, body.from_percentile)
        _seed_snapshot(curr_date, body.to_percentile)
        db.commit()

        # Run the REAL detection job (same entry point the weekly refresh calls).
        from app.watch.detection import detect_watch_triggers

        report = detect_watch_triggers(db, curr_date)
        return {
            "alerts_created": report.alerts_created,
            "player": player.canonical_name,
            "metric": body.metric,
            "from_percentile": body.from_percentile,
            "to_percentile": body.to_percentile,
        }
