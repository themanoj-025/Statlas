"""E2E fixture routes (dev/test only — never available in production).

Playwright needs to exercise Pro-gated features (Phase 9 reports) against the
real stack. These routes are hard-gated behind REPORTS_DEV_NARRATOR=1 — the
flag ONLY e2e-server.sh and the unit-test fixtures set; production never sets
it, so these routes 403 there. Registering a real subscription via Stripe in a
browser test would be both slow and flaky; this fixture grants the same
Subscription row the unit suite creates directly.

If future phases need more e2e fixtures, generalise this router rather than
adding another flag.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import session_scope
from app.models import Subscription, User

router = APIRouter(prefix="/api/v1/e2e", tags=["e2e-fixtures"])


def _require_e2e() -> None:
    if not get_settings().reports_dev_narrator:
        raise HTTPException(status_code=403, detail="e2e fixtures are disabled")


class GrantProBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)


@router.post("/grant-pro")
def grant_pro(body: GrantProBody, request: Request):  # noqa: ARG001 — Request kept for symmetry
    """Give a registered account active Pro access (an e2e fixture)."""
    _require_e2e()
    with session_scope() as db:
        user = db.query(User).filter_by(email=body.email).first()
        if user is None:
            raise HTTPException(status_code=404, detail="user not found — register first")
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
