"""Transactional email delivery (Phase 10 — Part D).

Provider: Resend (developer-first transactional email; strong deliverability
reputation and first-class List-Unsubscribe support for one-click
unsubscribe — the product's first outbound-email feature, so sender
reputation matters for all future mail including Phase 4 billing).

Design rules (docs/product/notification-delivery.md):

- KEY-GATED: with no RESEND_API_KEY the sender is an honest "not configured"
  state — callers get a clear NotConfiguredError, never a silent success.
- INJECTABLE: `send` accepts any callable(send_email: EmailMessage)->None for
  tests; production uses the Resend HTTP client.
- BRANDED: HTML is built from the Constitution design tokens (colors,
  typography) — a Statlas email is visually recognizable, not a generic
  template.
- ONE-CLICK UNSUBSCRIBE: every email carries a List-Unsubscribe header with a
  signed token URL, and the footer links the same preferences page.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any, Callable

from app.config import get_settings

logger = logging.getLogger(__name__)

# Constitution §3 design tokens (mirrored from web/app/globals.css).
BRAND_PRIMARY = "#0f766e"  # teal-700
BRAND_DARK = "#0b3b38"
TEXT_MAIN = "#1a2e35"
TEXT_MUTED = "#5b6b72"
BG_CANVAS = "#f4f7f6"
SURFACE = "#ffffff"
BORDER = "#dce5e2"
DANGER = "#b42318"
SUCCESS = "#157347"

EMAIL_BG = BG_CANVAS
CONTENT_BG = SURFACE


class EmailDeliveryError(RuntimeError):
    """The email backend failed or is not configured."""


class NotConfiguredError(EmailDeliveryError):
    """RESEND_API_KEY is unset — delivery is honestly unavailable."""


@dataclass
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str
    headers: dict[str, str] | None = None


SendFn = Callable[[EmailMessage], None]


def _sign(payload: str) -> str:
    """HMAC signature for one-click unsubscribe links."""
    settings = get_settings()
    secret = settings.alert_signing_secret or ""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def unsubscribe_url(user_id: int, token: str) -> str:
    """Signed one-click unsubscribe / preferences link."""
    settings = get_settings()
    payload = f"{user_id}:{token}"
    sig = _sign(payload)
    base = settings.public_base_url.rstrip("/")
    return (
        f"{base}/notifications/unsubscribe?" f"user={user_id}&token={token}&sig={sig}"
    )


def _email_for(
    *,
    to: str,
    subject: str,
    body_html: str,
    body_text: str,
    user_id: int,
    unsubscribe_token: str,
    extra_headers: dict[str, str] | None = None,
) -> EmailMessage:
    unsub = unsubscribe_url(user_id, unsubscribe_token)
    footer = (
        f'<tr><td style="padding:24px 32px;border-top:1px solid {BORDER};'
        f"font-family:Inter,Helvetica,Arial,sans-serif;font-size:12px;"
        f'color:{TEXT_MUTED};line-height:1.6;">'
        f'<p style="margin:0 0 8px;">Statlas — transparent football analytics.<br>'
        f"You're receiving this because you follow players/teams on Statlas and "
        f"have email notifications enabled.</p>"
        f'<p style="margin:0;">'
        f'<a href="{unsub}" style="color:{BRAND_PRIMARY};text-decoration:underline;">'
        f"Manage notification preferences or unsubscribe</a>"
        f"</p></td></tr>"
    )
    html = (
        f'<html><body style="margin:0;padding:0;background:{EMAIL_BG};">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{EMAIL_BG};padding:24px 0;">'
        f'<tr><td align="center">'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        f'style="max-width:600px;width:100%;background:{CONTENT_BG};'
        f'border:1px solid {BORDER};border-radius:12px;overflow:hidden;">'
        f'<tr><td style="background:{BRAND_DARK};padding:20px 32px;">'
        f'<span style="color:#ffffff;font-family:Inter,Helvetica,Arial,sans-serif;'
        f'font-size:20px;font-weight:700;letter-spacing:0.3px;">STATLAS</span>'
        f'<span style="color:#7dd3c8;font-family:Inter,Helvetica,Arial,sans-serif;'
        f"font-size:12px;font-weight:600;margin-left:10px;"
        f'letter-spacing:1.2px;text-transform:uppercase;">Scouting Alerts</span>'
        f"</td></tr>"
        f"{body_html}"
        f"{footer}"
        f"</table></td></tr></table></body></html>"
    )
    headers = {
        "List-Unsubscribe": f"<{unsub}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }
    if extra_headers:
        headers.update(extra_headers)
    return EmailMessage(
        to=to,
        subject=subject,
        html=html,
        text=body_text + f"\n\nManage preferences or unsubscribe: {unsub}",
        headers=headers,
    )


# ---------------------------------------------------------------------------
# The senders
# ---------------------------------------------------------------------------


def resend_sender() -> SendFn:
    """Production sender backed by Resend's HTTP API (key-gated)."""

    def _send(message: EmailMessage) -> None:
        settings = get_settings()
        if not settings.resend_api_key:
            raise NotConfiguredError(
                "Email delivery is not configured: RESEND_API_KEY is unset. "
                "Alerts are still recorded in-app; enable the key to start "
                "sending emails."
            )
        try:
            import requests  # already a project dependency

            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.resend_from_email,
                    "to": [message.to],
                    "subject": message.subject,
                    "html": message.html,
                    "text": message.text,
                    "headers": message.headers or {},
                },
                timeout=15,
            )
            if resp.status_code >= 400:
                raise EmailDeliveryError(
                    f"Resend API error {resp.status_code}: {resp.text[:300]}"
                )
        except requests.RequestException as exc:
            raise EmailDeliveryError(f"Resend request failed: {exc}") from exc

    return _send


def get_sender() -> SendFn:
    """The configured sender — override for tests via `set_sender`."""
    return _active_sender


_active_sender: SendFn = resend_sender()


def set_sender(sender: SendFn | None) -> None:
    """Test seam: install a fake sender (or restore production with None)."""
    global _active_sender
    _active_sender = sender if sender is not None else resend_sender()


# ---------------------------------------------------------------------------
# Content builders (real, specific copy — populated from alert detail data)
# ---------------------------------------------------------------------------


def _metric_label(metric: str) -> str:
    from app.config import load_registry

    meta = load_registry()["metrics"].get(metric)
    return meta["name"] if meta else metric


def _pct(value: float | None) -> str:
    """Percentile with a proper ordinal suffix: 1st, 2nd, 3rd, 11th, 12th,
    13th, 21st, 22nd, 23rd, ... (never a flat '62th')."""
    if value is None:
        return "—"
    n = round(value)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def alert_email_content(alert_type: str, detail: dict[str, Any]) -> tuple[str, str]:
    """(subject, html-body) for a single alert, written from real detail data."""
    name = detail.get("entity_name") or "Player"
    if alert_type == "percentile_movement":
        metric = _metric_label(detail.get("metric", ""))
        subject = (
            f"{name}: {metric} jumped to {_pct(detail.get('to_percentile'))} percentile"
        )
        body = (
            f'<tr><td style="padding:28px 32px;">'
            f'<p style="margin:0 0 12px;font-family:Inter,Helvetica,Arial,sans-serif;'
            f'font-size:15px;color:{TEXT_MAIN};line-height:1.6;">'
            f"<strong>{name}</strong>&#8217;s <strong>{metric}</strong> has moved "
            f"from the <strong>{_pct(detail.get('from_percentile'))}</strong> to the "
            f"<strong>{_pct(detail.get('to_percentile'))}</strong> percentile "
            f"between weekly snapshots.</p>"
            f'<p style="margin:0 0 4px;font-family:Inter,Helvetica,Arial,sans-serif;'
            f'font-size:13px;color:{TEXT_MUTED};">'
            f"Snapshot dates: {detail.get('from_snapshot_date')} &#8594; "
            f"{detail.get('to_snapshot_date')} &#8226; "
            f"Minutes: {detail.get('from_minutes')} &#8594; {detail.get('to_minutes')}</p>"
            f"</td></tr>"
        )
    elif alert_type == "club_change":
        from_team = detail.get("from_team") or "unknown club"
        to_team = detail.get("to_team") or "unknown club"
        subject = f"{name} has joined {to_team}"
        body = (
            f'<tr><td style="padding:28px 32px;">'
            f'<p style="margin:0 0 12px;font-family:Inter,Helvetica,Arial,sans-serif;'
            f'font-size:15px;color:{TEXT_MAIN};line-height:1.6;">'
            f"<strong>{name}</strong> has moved from <strong>{from_team}</strong> "
            f"to <strong>{to_team}</strong> (detected in the latest weekly data).</p>"
            f'<p style="margin:0;font-family:Inter,Helvetica,Arial,sans-serif;'
            f'font-size:13px;color:{TEXT_MUTED};">'
            f"Snapshot date: {detail.get('snapshot_date')}</p></td></tr>"
        )
    elif alert_type == "new_season_data":
        subject = f"{name}: {detail.get('new_season')} season data is in"
        body = (
            f'<tr><td style="padding:28px 32px;">'
            f'<p style="margin:0;font-family:Inter,Helvetica,Arial,sans-serif;'
            f'font-size:15px;color:{TEXT_MAIN};line-height:1.6;">'
            f"The first qualifying snapshot of the <strong>{detail.get('new_season')}</strong> "
            f"season is available for <strong>{name}</strong> (previous season: "
            f"{detail.get('previous_season')}).</p></td></tr>"
        )
    elif alert_type == "data_coverage_change":
        signal = detail.get("signal")
        if signal == "coverage_gained":
            subject = (
                f"{name}: detailed {detail.get('coverage_source')} data now available"
            )
            body = (
                f'<tr><td style="padding:28px 32px;">'
                f'<p style="margin:0;font-family:Inter,Helvetica,Arial,sans-serif;'
                f'font-size:15px;color:{TEXT_MAIN};line-height:1.6;">'
                f"Shot/pass-level {detail.get('coverage_source')} event data is now "
                f"available for <strong>{name}</strong> in the "
                f"{detail.get('season')} season ({detail.get('league')}).</p></td></tr>"
            )
        else:  # source_anomaly
            subject = f"{name}: a data-quality flag needs your attention"
            body = (
                f'<tr><td style="padding:28px 32px;">'
                f'<p style="margin:0 0 12px;font-family:Inter,Helvetica,Arial,sans-serif;'
                f'font-size:15px;color:{TEXT_MAIN};line-height:1.6;">'
                f"Our data-quality checks flagged <strong>{detail.get('anomaly_count')}</strong> "
                f"unresolved issue(s) on <strong>{name}</strong>&#8217;s latest snapshot "
                f"({detail.get('snapshot_date')}). Their numbers may be unreliable "
                f"until reviewed.</p>"
                f'<p style="margin:0;font-family:Inter,Helvetica,Arial,sans-serif;'
                f'font-size:13px;color:{TEXT_MUTED};">'
                f"Statlas never hides data-quality problems — this is one of them.</p>"
                f"</td></tr>"
            )
    else:
        subject = f"{name}: watchlist alert"
        body = (
            f'<tr><td style="padding:28px 32px;">'
            f'<p style="margin:0;font-family:Inter,Helvetica,Arial,sans-serif;'
            f'font-size:15px;color:{TEXT_MAIN};">A change was detected for '
            f"<strong>{name}</strong>.</p></td></tr>"
        )
    return subject, body


def digest_email_content(
    user_name: str | None,
    alerts: list[tuple[str, dict[str, Any]]],
    frequency: str,
) -> tuple[str, str]:
    """(subject, html-body) for a digest batching multiple alerts (D1: one
    email per digest period, never one per alert)."""
    count = len(alerts)
    period = "daily" if frequency == "daily_digest" else "weekly"
    subject = f"Statlas digest: {count} watchlist update{'s' if count != 1 else ''}"
    rows = []
    for alert_type, detail in alerts:
        _subj, body = alert_email_content(alert_type, detail)
        rows.append(body)
    body_html = (
        f'<tr><td style="padding:28px 32px;">'
        f'<p style="margin:0 0 4px;font-family:Inter,Helvetica,Arial,sans-serif;'
        f"font-size:12px;font-weight:600;letter-spacing:1.2px;"
        f'text-transform:uppercase;color:{BRAND_PRIMARY};">{period} digest</p>'
        f'<p style="margin:0 0 16px;font-family:Inter,Helvetica,Arial,sans-serif;'
        f'font-size:18px;font-weight:700;color:{TEXT_MAIN};">'
        f"{count} update{'s' if count != 1 else ''} from your watchlist</p>"
        f"</td></tr>" + "".join(rows)
    )
    return subject, body_html
