"""Phase 9 — AI scouting reports test suite.

The single most important test in this phase is the verification-rejection
test (B5): it proves the hard-enforcement mechanism actually catches a
fabricated claim — not just a documentation claim that it would. Every other
category follows:

- verification gate: fabricated number / metric name / comparable / wrong
  confidence level all fail; grounded output passes (B2)
- confidence scoring (A2): deterministic, higher for full-season/complete-data
  players than barely-qualifying/sparse ones
- risk factors (A3): only real signals + the explicit out-of-scope statement
- full pipeline (B1/B5): deterministic narrator -> verified -> stored, with
  quota consumption and evidence appendix
- workspace context (B4): present when generated from a shortlist entry,
  absent when generated ad hoc
- authorization (D4): cross-user access -> 404, never a 403 that leaks
  existence (the Phase 7/8 pattern)
- tier gating (D5): free-tier -> honest upsell 403; pro quota cap enforced
- exports (C): JSON verbatim, PDF bytes, CSV tabular surfaces
- API level: 401 unauthenticated, generation flow with the dev narrator
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app import report_export, reports
from app.db import create_schema, session_scope
from app.models import (
    League,
    PercentileSnapshot,
    Player,
    Report,
    StatSnapshot,
    Subscription,
    Team,
    User,
)

pytestmark = pytest.mark.slow
from app.queries import workspace_queries as wq

SNAPSHOT_DATE = datetime(2026, 8, 12, 3, 0, 0, tzinfo=timezone.utc)
SEASON = "2025-26"
NOW = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)  # 3 days after snapshot

# A full ST percentile vector — every outfield metric present.
FULL_VECTOR = {
    "si_gls_p90": 82,
    "si_xg_p90": 78,
    "si_sh_p90": 74,
    "si_prgp_p90": 71,
    "si_prgc_p90": 73,
    "si_xag_p90": 22,
    "si_kp_p90": 41,
    "si_tkl_p90": 32,
    "si_int_p90": 56,
    "si_press_p90": 61,
    "si_cmp_pct": 66,
    "si_dis_p90": 48,
}


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


def seed_player(
    db,
    name: str,
    *,
    position: str = "ST",
    minutes: float = 2700.0,
    percentiles: dict[str, float] | None = None,
    index_score: float = 80.0,
    dob: str | None = "2001-05-15",
    league: League | None = None,
    team: Team | None = None,
) -> Player:
    """Seed a player with a published snapshot + percentile vector, so
    gather_report_context() has everything it needs (profile, percentiles,
    snapshot date, comparables, trend)."""
    league = league or db.query(League).first()
    team = team or db.query(Team).first()
    player = Player(
        canonical_name=name,
        position_group=position,
        primary_position=position,
        date_of_birth=datetime.fromisoformat(dob).date() if dob else None,
        nationality="England",
        external_ids={},
        current_team_id=team.id,
    )
    db.add(player)
    db.flush()
    snap = StatSnapshot(
        player_id=player.id,
        team_id=team.id,
        league_id=league.id,
        season=SEASON,
        scrape_date=SNAPSHOT_DATE,
        source="fbref",
        raw_stats=dict.fromkeys(percentiles or {}, 1.0),
        minutes_played=minutes,
        matches_played=int(minutes / 90),
        status="published",
    )
    db.add(snap)
    db.flush()
    db.add(
        PercentileSnapshot(
            stat_snapshot_id=snap.id,
            computed_date=SNAPSHOT_DATE,
            position_group=position,
            league_tier=league.tier,
            metric_name="si_index",
            percentile_value=None,
            index_score=index_score,
            is_published=True,
        )
    )
    for metric, value in (percentiles or {}).items():
        db.add(
            PercentileSnapshot(
                stat_snapshot_id=snap.id,
                computed_date=SNAPSHOT_DATE,
                position_group=position,
                league_tier=league.tier,
                metric_name=metric,
                percentile_value=value,
                index_score=None,
                is_published=True,
            )
        )
    db.commit()
    return player


@pytest.fixture()
def report_data(db) -> dict[str, object]:
    """One free + one pro user, one tier-1 league/team, and a population of
    three ST players with full percentile vectors so similarity works."""
    free = make_user(db, "free@example.com")
    pro = make_pro_user(db, "pro@example.com")
    league = League(
        slug="test-league",
        name="Test League",
        country="England",
        tier="tier_1",
        external_ids={},
    )
    db.add(league)
    db.commit()
    team = Team(name="Test FC", league_id=league.id, external_ids={})
    db.add(team)
    db.commit()

    anchor = seed_player(
        db,
        "Anchor Striker",
        position="ST",
        minutes=2700.0,
        percentiles=FULL_VECTOR,
        index_score=88.0,
        dob="2001-05-15",
        league=league,
        team=team,
    )
    seed_player(
        db,
        "Comparable One",
        position="ST",
        minutes=2500.0,
        percentiles={k: v + 2 for k, v in FULL_VECTOR.items()},
        index_score=84.0,
        dob="2000-02-10",
        league=league,
        team=team,
    )
    seed_player(
        db,
        "Comparable Two",
        position="ST",
        minutes=2300.0,
        percentiles={k: v - 3 for k, v in FULL_VECTOR.items()},
        index_score=79.0,
        dob="2002-08-22",
        league=league,
        team=team,
    )
    return {"free": free, "pro": pro, "anchor": anchor, "league": league, "team": team}


def _context(db, player_id, entry_id=None):
    return reports.gather_report_context(db, player_id, entry_id)


# ---------------------------------------------------------------------------
# B5 — THE verification-rejection test (hard enforcement actually works)
# ---------------------------------------------------------------------------


def test_verification_catches_fabricated_number(db, report_data) -> None:
    """A report claiming a percentile that is not in the verified context must
    FAIL verification — the mechanism is code, not prompt discipline."""
    context = _context(db, report_data["anchor"].id)
    draft = reports.deterministic_narrator(context)
    # Inject a fabricated statistic: 97th percentile for goals — the corpus
    # only contains 82 (the real value), so 97 must be flagged.
    draft["sections"]["overview"]["text"] = (
        draft["sections"]["overview"]["text"]
        + " The player ranks in the 97th percentile for goals."
    )
    result = reports.verify_report(draft, context)
    assert result["passed"] is False
    assert any("97" in u["claim"] for u in result["unverified"])


def test_verification_catches_fabricated_metric_name(db, report_data) -> None:
    context = _context(db, report_data["anchor"].id)
    draft = reports.deterministic_narrator(context)
    draft["sections"]["strengths"][0]["supporting_metric"] = "si_not_a_metric"
    result = reports.verify_report(draft, context)
    assert result["passed"] is False
    assert any("si_not_a_metric" in u["claim"] for u in result["unverified"])


def test_verification_catches_invented_comparable(db, report_data) -> None:
    context = _context(db, report_data["anchor"].id)
    draft = reports.deterministic_narrator(context)
    draft["sections"]["comparable_players"].append(
        {
            "player_id": 999_999,
            "name": "Nobody",
            "similarity": 0.95,
            "explanation": {},
        }
    )
    result = reports.verify_report(draft, context)
    assert result["passed"] is False
    assert any("999999" in u["claim"] for u in result["unverified"])


def test_verification_catches_wrong_confidence_level(db, report_data) -> None:
    context = _context(db, report_data["anchor"].id)
    draft = reports.deterministic_narrator(context)
    draft["sections"]["recommendation"]["confidence_level"] = (
        "low" if context["confidence"]["level"] != "low" else "high"
    )
    result = reports.verify_report(draft, context)
    assert result["passed"] is False
    assert any(u["kind"] == "confidence" for u in result["unverified"])


def test_verification_passes_grounded_output(db, report_data) -> None:
    """The deterministic narrator emits ONLY context values, so its output must
    pass — proving the gate accepts genuinely grounded reports, not just that
    it rejects everything."""
    context = _context(db, report_data["anchor"].id)
    draft = reports.deterministic_narrator(context)
    result = reports.verify_report(draft, context)
    assert result["passed"] is True, result["unverified"]


# ---------------------------------------------------------------------------
# A2 — confidence scoring is deterministic and factor-based
# ---------------------------------------------------------------------------


def test_confidence_full_season_complete_data_is_high(db, report_data) -> None:
    conf = reports.compute_report_confidence(
        minutes_played=2700.0,
        qualifying_minutes=900,
        metrics_present=12,
        metrics_expected=12,
        snapshot_date=SNAPSHOT_DATE,
        now=NOW,
    )
    assert conf["level"] == "high"
    assert conf["composite"] >= reports.CONFIDENCE_HIGH
    assert "2,700" in conf["rationale"]
    assert "full-season" in conf["rationale"]


def test_confidence_barely_qualifying_sparse_is_lower(db, report_data) -> None:
    conf = reports.compute_report_confidence(
        minutes_played=950.0,
        qualifying_minutes=900,
        metrics_present=5,
        metrics_expected=12,
        snapshot_date=datetime(2026, 5, 1, tzinfo=timezone.utc),  # >60 days old
        now=NOW,
    )
    assert conf["level"] in ("medium", "low")
    assert conf["composite"] < reports.CONFIDENCE_HIGH
    # The rationale names the actual factors — checkable, not vibes.
    assert "950" in conf["rationale"]
    assert "5/12" in conf["rationale"]


def test_confidence_below_threshold_is_low(db, report_data) -> None:
    conf = reports.compute_report_confidence(
        minutes_played=500.0,
        qualifying_minutes=900,
        metrics_present=3,
        metrics_expected=12,
        snapshot_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        now=NOW,
    )
    assert conf["level"] == "low"
    assert conf["factors"]["sample_size"]["level"] == "below-threshold"


def test_confidence_stale_snapshot_lowers_score(db, report_data) -> None:
    fresh = reports.compute_report_confidence(
        minutes_played=2700.0,
        qualifying_minutes=900,
        metrics_present=12,
        metrics_expected=12,
        snapshot_date=SNAPSHOT_DATE,
        now=NOW,
    )
    stale = reports.compute_report_confidence(
        minutes_played=2700.0,
        qualifying_minutes=900,
        metrics_present=12,
        metrics_expected=12,
        snapshot_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        now=NOW,
    )
    assert stale["composite"] < fresh["composite"]
    assert stale["factors"]["recency"]["level"] == "stale"


# ---------------------------------------------------------------------------
# A3 — risk factors from real signals only
# ---------------------------------------------------------------------------


def test_risk_factors_limited_sample(db, report_data) -> None:
    risks = reports.derive_risk_factors(
        minutes_played=1200.0,
        qualifying_minutes=900,
        seasons=1,
        has_event_data=True,
        age=25,
        position_group="ST",
    )
    assert any(r["basis"] == "sample_size" for r in risks)
    assert any(r["basis"] == "single_season" for r in risks)


def test_risk_factors_event_data_and_age(db, report_data) -> None:
    risks = reports.derive_risk_factors(
        minutes_played=3000.0,
        qualifying_minutes=900,
        seasons=2,
        has_event_data=False,
        age=17,
        position_group="ST",
    )
    assert any(r["basis"] == "no_event_data" for r in risks)
    assert any(r["basis"] == "age_vs_position" for r in risks)
    # The out-of-scope statement is ALWAYS present (silence never implies
    # completeness — A3).
    assert risks[-1]["basis"] == "out_of_scope"
    assert "injury history" in risks[-1]["point"]
    assert "outside" in risks[-1]["point"]


def test_risk_factors_no_invented_dimensions(db, report_data) -> None:
    """No vague personality/attitude claims — only the documented signals plus
    the out-of-scope statement. The out-of-scope statement may NAME the
    unassessed dimensions (that is its point), but no real risk factor may
    claim to assess them."""
    risks = reports.derive_risk_factors(
        minutes_played=3000.0,
        qualifying_minutes=900,
        seasons=2,
        has_event_data=True,
        age=26,
        position_group="ST",
    )
    bases = {r["basis"] for r in risks}
    assert bases <= {
        "sample_size",
        "single_season",
        "no_event_data",
        "age_vs_position",
        "out_of_scope",
    }
    for r in risks[:-1]:  # every real risk factor except the out-of-scope note
        lowered = r["point"].lower()
        assert "personality" not in lowered
        assert "attitude" not in lowered
        assert "injury history" not in lowered


# ---------------------------------------------------------------------------
# B1/B5 — full pipeline: gather -> narrate -> verify -> store
# ---------------------------------------------------------------------------


def test_generate_report_pipeline_verified_and_stored(db, report_data) -> None:
    pro = report_data["pro"]
    anchor = report_data["anchor"]
    result = reports.generate_report(
        db, pro.id, anchor.id, narrator=reports.deterministic_narrator, now=NOW
    )
    assert result["status"] == "generated"
    assert result["report"]["verification"]["status"] == "passed"
    assert result["report"]["player_id"] == anchor.id
    assert result["report"]["data_snapshot_date"] == "2026-08-12"
    assert result["report"]["generated_by_user_id"] == pro.id
    # The evidence appendix makes every claim traceable.
    appendix = result["report"]["evidence_appendix"]
    assert len(appendix) >= 3
    assert any(a["source_call"] == "similar_players" for a in appendix)
    # Stored, not ephemeral.
    assert db.query(Report).count() == 1
    row = db.query(Report).first()
    assert row.user_id == pro.id
    assert row.status == "generated"
    assert row.verification_log["passed"] is True


def test_generate_report_sections_structure(db, report_data) -> None:
    pro = report_data["pro"]
    result = reports.generate_report(
        db,
        pro.id,
        report_data["anchor"].id,
        narrator=reports.deterministic_narrator,
        now=NOW,
    )
    sections = result["report"]["sections"]
    for key in (
        "overview",
        "statistical_profile",
        "role_and_position",
        "strengths",
        "weaknesses",
        "comparable_players",
        "development_trajectory",
        "risk_factors",
        "recommendation",
    ):
        assert key in sections, key
    # Every strength/weakness carries a real metric + value.
    for s in sections["strengths"]:
        assert s["supporting_metric"] in FULL_VECTOR
        assert s["percentile"] is not None
    # Comparables come VERBATIM from Phase 6 (B3) — never LLM-computed.
    assert len(sections["comparable_players"]) == 2
    for c in sections["comparable_players"]:
        assert "similarity" in c
        assert "explanation" in c
    # Confidence level equals the deterministic computation.
    assert (
        sections["recommendation"]["confidence_level"]
        == result["report"]["confidence"]["level"]
    )


def test_generate_requires_pro(db, report_data) -> None:
    free = report_data["free"]
    with pytest.raises(reports.ReportLimitExceeded) as excinfo:
        reports.generate_report(
            db,
            free.id,
            report_data["anchor"].id,
            narrator=reports.deterministic_narrator,
        )
    assert "Pro feature" in str(excinfo.value)
    # Nothing stored, nothing consumed.
    assert db.query(Report).count() == 0


def test_generate_unknown_player(db, report_data) -> None:
    pro = report_data["pro"]
    with pytest.raises(reports.PlayerHasNoData):
        reports.generate_report(
            db,
            pro.id,
            999_999,
            narrator=reports.deterministic_narrator,
        )


def test_generate_unpublished_player(db, report_data) -> None:
    """A player with no published percentiles cannot have a grounded report."""
    pro = report_data["pro"]
    league = report_data["league"]
    team = report_data["team"]
    bare = seed_player(
        db,
        "Bare Player",
        position="ST",
        minutes=3000.0,
        percentiles={},
        league=league,
        team=team,
    )
    with pytest.raises(reports.PlayerHasNoData):
        reports.generate_report(
            db, pro.id, bare.id, narrator=reports.deterministic_narrator
        )


# ---------------------------------------------------------------------------
# B4 — workspace context: present from an entry, absent ad hoc
# ---------------------------------------------------------------------------


def test_workspace_context_included_when_generated_from_entry(db, report_data) -> None:
    pro = report_data["pro"]
    anchor = report_data["anchor"]
    sl = wq.create_shortlist(db, pro.id, "Targets")
    entry = wq.add_player_to_shortlist(
        db, pro.id, sl["shortlist_id"], anchor.id, initial_note="Watched vs City"
    )
    wq.add_entry_tag(db, pro.id, entry["entry_id"], "left-footed")
    wq.add_entry_note(db, pro.id, entry["entry_id"], "Strong press engagement")

    result = reports.generate_report(
        db,
        pro.id,
        anchor.id,
        shortlist_entry_id=entry["entry_id"],
        narrator=reports.deterministic_narrator,
        now=NOW,
    )
    wc = result["report"]["sections"]["workspace_context"]
    assert wc is not None
    assert wc["shortlist_status"] == "discovered"
    assert wc["tags"] == ["left-footed"]
    assert any("Strong press engagement" in n["note_text"] for n in wc["recent_notes"])
    # Clearly labelled as the user's own input, not an AI finding.
    assert "user's own scouting notes" in wc["label"]
    assert result["report"]["source"] == "shortlist_entry"
    assert result["report"]["shortlist_entry_id"] == entry["entry_id"]


def test_workspace_context_omitted_when_generated_ad_hoc(db, report_data) -> None:
    pro = report_data["pro"]
    result = reports.generate_report(
        db,
        pro.id,
        report_data["anchor"].id,
        narrator=reports.deterministic_narrator,
        now=NOW,
    )
    assert result["report"]["sections"]["workspace_context"] is None
    assert result["report"]["source"] == "player_profile"
    assert result["report"]["shortlist_entry_id"] is None


def test_workspace_entry_of_another_user_rejected(db, report_data) -> None:
    """The workspace-context lookup must not leak another user's entry."""
    free = report_data["free"]
    anchor = report_data["anchor"]
    sl = wq.create_shortlist(db, free.id, "Private")
    entry = wq.add_player_to_shortlist(db, free.id, sl["shortlist_id"], anchor.id)
    pro = report_data["pro"]
    with pytest.raises(reports.ReportNotFound):
        reports.generate_report(
            db,
            pro.id,
            anchor.id,
            shortlist_entry_id=entry["entry_id"],
            narrator=reports.deterministic_narrator,
        )


# ---------------------------------------------------------------------------
# D5 — quota (separate from chat quota, honest upsell)
# ---------------------------------------------------------------------------


def test_pro_quota_consumed_and_capped(db, report_data) -> None:
    pro = report_data["pro"]
    quota = reports.get_report_quota(db, pro.id)
    assert quota["remaining"] == quota["limit"]
    reports.generate_report(
        db,
        pro.id,
        report_data["anchor"].id,
        narrator=reports.deterministic_narrator,
        now=NOW,
    )
    after = reports.get_report_quota(db, pro.id)
    assert after["used"] == 1
    assert after["remaining"] == quota["limit"] - 1

    # Exhaust the allowance -> honest, specific upsell, not a generic error.
    for _ in range(after["remaining"]):
        reports.generate_report(
            db,
            pro.id,
            report_data["anchor"].id,
            narrator=reports.deterministic_narrator,
            now=NOW,
        )
    with pytest.raises(reports.ReportLimitExceeded) as excinfo:
        reports.generate_report(
            db,
            pro.id,
            report_data["anchor"].id,
            narrator=reports.deterministic_narrator,
            now=NOW,
        )
    assert "allowance" in str(excinfo.value)
    assert "resets" in str(excinfo.value)


# ---------------------------------------------------------------------------
# D4 — authorization: cross-user access is a 404, never a 403
# ---------------------------------------------------------------------------


def test_cross_user_get_404(db, report_data) -> None:
    pro = report_data["pro"]
    other = make_pro_user(db, "other@example.com")
    result = reports.generate_report(
        db,
        pro.id,
        report_data["anchor"].id,
        narrator=reports.deterministic_narrator,
        now=NOW,
    )
    with pytest.raises(reports.ReportNotFound):
        reports.get_report(db, other.id, result["report_id"])
    with pytest.raises(reports.ReportNotFound):
        reports.delete_report(db, other.id, result["report_id"])
    # The other user's list stays empty — nothing leaked.
    assert reports.list_reports(db, other.id) == []


def test_list_reports_own_only_and_ordered(db, report_data) -> None:
    pro = report_data["pro"]
    reports.generate_report(
        db,
        pro.id,
        report_data["anchor"].id,
        narrator=reports.deterministic_narrator,
        now=NOW,
    )
    reports.generate_report(
        db,
        pro.id,
        report_data["anchor"].id,
        narrator=reports.deterministic_narrator,
        now=NOW,
    )
    listing = reports.list_reports(db, pro.id)
    assert len(listing) == 2
    assert listing[0]["report_id"] > listing[1]["report_id"]  # newest first
    assert listing[0]["player_name"] == "Anchor Striker"
    assert listing[0]["verification_status"] == "passed"


def test_delete_report_own(db, report_data) -> None:
    pro = report_data["pro"]
    result = reports.generate_report(
        db,
        pro.id,
        report_data["anchor"].id,
        narrator=reports.deterministic_narrator,
        now=NOW,
    )
    reports.delete_report(db, pro.id, result["report_id"])
    assert reports.list_reports(db, pro.id) == []


# ---------------------------------------------------------------------------
# C — exports: JSON verbatim, PDF, CSV (all derived from the one object)
# ---------------------------------------------------------------------------


def _make_stored(db, report_data):
    pro = report_data["pro"]
    return reports.generate_report(
        db,
        pro.id,
        report_data["anchor"].id,
        narrator=reports.deterministic_narrator,
        now=NOW,
    )


def test_export_json_verbatim(db, report_data) -> None:
    stored = _make_stored(db, report_data)
    text = report_export.export_json(stored["report"])
    parsed = json.loads(text)
    assert parsed == stored["report"]  # verbatim — canonical source of truth
    assert "evidence_appendix" in parsed
    assert len(parsed["evidence_appendix"]) >= 3


def test_export_pdf_wellformed(db, report_data) -> None:
    stored = _make_stored(db, report_data)
    pdf = report_export.export_pdf(stored["report"], player_name="Anchor Striker")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 4000  # a real document, not a stub
    assert b"STATLAS" in pdf


def test_export_pdf_needs_review_contains_warning(db, report_data) -> None:
    stored = _make_stored(db, report_data)
    stored["report"]["verification"]["status"] = "needs_review"
    pdf = report_export.export_pdf(stored["report"], player_name="Anchor Striker")
    assert b"Needs review" in pdf


def test_export_csv_tabular_surfaces(db, report_data) -> None:
    stored = _make_stored(db, report_data)
    csv_text = report_export.export_csv(stored["report"], player_name="Anchor Striker")
    assert "Statlas Scouting Report — Statistical Profile" in csv_text
    assert "metric,metric_name,value,percentile" in csv_text
    assert "Comparable Players (Phase 6 similarity)" in csv_text
    assert "Anchor Striker" in csv_text
    # Narrative sections are NOT in the CSV (documented in the export UI).
    assert "Overview" not in csv_text.split("\n")[0]


# ---------------------------------------------------------------------------
# API level — auth, error mapping, dev-narrator generation flow
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(monkeypatch) -> bool:
    db_module._engine = None
    db_module._session_factory = None
    create_schema()
    # The API uses the deterministic narrator when REPORTS_DEV_NARRATOR is set —
    # the same pipeline with the same verification gate, just no LLM call.
    # The fake delegates to the real settings so auth/session attributes stay
    # intact; only the narrator switch is overridden.
    import app.api.report_views as rv
    import app.config as config

    real = config.get_settings()

    class _FakeSettings:
        def __getattr__(self, name) -> None:
            return getattr(real, name)

        @property
        def reports_dev_narrator(self) -> bool:
            return True

    monkeypatch.setattr(rv, "get_settings", lambda: _FakeSettings())
    with TestClient(app) as c:
        yield c


from app.api.main import app

pytestmark = pytest.mark.unit


def _register(client, email: str = "pro-api@example.com") -> None:
    resp = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Hunter2hunter!"}
    )
    assert resp.status_code == 201, resp.text
    # Reports are Pro-gated — grant the account Pro access.
    with session_scope() as db:
        user = db.query(User).filter_by(email=email).first()
        db.add(
            Subscription(
                user_id=user.id,
                plan="pro",
                stripe_subscription_id="sub_api",
                status="active",
            )
        )
        db.commit()


def _seed_api_data() -> None:
    with session_scope() as db:
        league = League(
            slug="test-league",
            name="Test League",
            country="England",
            tier="tier_1",
            external_ids={},
        )
        db.add(league)
        db.commit()
        team = Team(name="Test FC", league_id=league.id, external_ids={})
        db.add(team)
        db.commit()
        seed_player(
            db,
            "API Striker",
            position="ST",
            minutes=2700.0,
            percentiles=FULL_VECTOR,
            index_score=88.0,
            league=league,
            team=team,
        )
        seed_player(
            db,
            "API Comparable",
            position="ST",
            minutes=2500.0,
            percentiles={k: v + 2 for k, v in FULL_VECTOR.items()},
            index_score=84.0,
            league=league,
            team=team,
        )


def test_api_reports_require_signin(client) -> None:
    assert client.get("/api/v1/reports").status_code == 401
    assert client.get("/api/v1/reports/quota").status_code == 401
    resp = client.post("/api/v1/reports", json={"player_id": 1})
    assert resp.status_code == 401


def test_api_generate_list_export_flow(client) -> None:
    _seed_api_data()
    _register(client)

    resp = client.get("/api/v1/reports/quota")
    assert resp.status_code == 200
    assert resp.json()["has_pro"] is True

    player_id = None
    with session_scope() as db:
        player_id = db.query(Player).filter_by(canonical_name="API Striker").first().id

    resp = client.post("/api/v1/reports", json={"player_id": player_id})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "generated"
    assert body["report"]["verification"]["status"] == "passed"
    report_id = body["report_id"]

    # List + detail.
    assert len(client.get("/api/v1/reports").json()["reports"]) == 1
    detail = client.get(f"/api/v1/reports/{report_id}")
    assert detail.status_code == 200
    assert detail.json()["report"]["sections"]["overview"]["text"]

    # Exports derive from the verified object.
    js = client.get(f"/api/v1/reports/{report_id}/export.json")
    assert js.status_code == 200
    assert json.loads(js.content)["player_id"] == player_id
    pdf = client.get(f"/api/v1/reports/{report_id}/export.pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    csv_resp = client.get(f"/api/v1/reports/{report_id}/export.csv")
    assert csv_resp.status_code == 200
    assert b"Statistical Profile" in csv_resp.content

    # Regenerate creates a FRESH report against current data — the stored
    # report is never mutated.
    resp = client.post(f"/api/v1/reports/{report_id}/regenerate")
    assert resp.status_code == 201
    assert resp.json()["report_id"] != report_id
    assert len(client.get("/api/v1/reports").json()["reports"]) == 2

    # Delete.
    assert client.delete(f"/api/v1/reports/{report_id}").status_code == 204
    assert client.get(f"/api/v1/reports/{report_id}").status_code == 404


def test_api_free_tier_honest_upsell(client) -> None:
    _seed_api_data()
    _register(client, "free-api@example.com")
    # Pro access comes from the subscription row (auth.has_pro_access) — revoke
    # it so the account is genuinely Free.
    with session_scope() as db:
        user = db.query(User).filter_by(email="free-api@example.com").first()
        db.query(Subscription).filter_by(user_id=user.id).delete()
        user.plan = "free"
        db.commit()
    player_id = None
    with session_scope() as db:
        player_id = db.query(Player).filter_by(canonical_name="API Striker").first().id
    resp = client.post("/api/v1/reports", json={"player_id": player_id})
    assert resp.status_code == 403
    body = resp.json()
    msg = body.get("detail") or body.get("error", {}).get("message", "")
    assert "Pro feature" in msg


def test_e2e_grant_fixture_disabled_without_flag(client_plain) -> None:
    """The e2e grant fixture 403s unless the e2e-only flag is set — it can
    never grant Pro on a normal deployment."""
    resp = client_plain.post(
        "/api/v1/e2e/grant-pro", json={"email": "anyone@example.com"}
    )
    assert resp.status_code == 403


@pytest.fixture()
def client_plain() -> None:
    """A TestClient WITHOUT the e2e narrator flag — normal operation."""
    db_module._engine = None
    db_module._session_factory = None
    create_schema()
    with TestClient(app) as c:
        yield c


def test_api_cross_user_404(client) -> None:
    _seed_api_data()
    _register(client, "first@example.com")
    player_id = None
    with session_scope() as db:
        player_id = db.query(Player).filter_by(canonical_name="API Striker").first().id
    report_id = client.post("/api/v1/reports", json={"player_id": player_id}).json()[
        "report_id"
    ]

    client.post("/api/v1/auth/logout")
    _register(client, "second@example.com")
    assert client.get(f"/api/v1/reports/{report_id}").status_code == 404
    assert client.delete(f"/api/v1/reports/{report_id}").status_code == 404
    assert client.post(f"/api/v1/reports/{report_id}/regenerate").status_code == 404
    assert client.get(f"/api/v1/reports/{report_id}/export.json").status_code == 404
