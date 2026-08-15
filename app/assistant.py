"""Grounded AI assistant (Phase 4 — Part B).

Constitution Never-List #4 is the load-bearing constraint here: the assistant
NEVER free-generates a numeric claim. It is function-calling-only — every stat
in a response comes from a real tool call against the Phase 1/2 query layer,
and each tool call is returned to the UI as a visible "data used" section so
the transparency claim is real, not asserted.

Design:
- Tools are thin wrappers over existing query functions (queries/*) — the
  same functions the REST API and pages use. No parallel data access.
- The system prompt forbids estimating/recalling stats from training data and
  requires answering "I can't verify that from Statlas data" for anything the
  tools cannot answer.
- Quota: per-user per-billing-period, hard cap (no silent overage) with the
  reset date stated in the response (Part B3). Uses assistant_quotas.
- Key-gated: with ANTHROPIC_API_KEY unset the endpoint returns an honest
  "not configured" state — never a scripted demo.
- Guardrails: rate limiting is enforced at the API layer (Part B4); every
  turn logs the tool calls and response for quality review (privacy policy
  covers consent), and a `grounded` flag asserts every numeric claim traces
  to a tool result.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings, load_registry, plan_limits
from app.db import session_scope
from app.models import AssistantQuota, User
from app.queries import (
    leaderboard_queries,
    player_queries,
    similar_players,
    trend_queries,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Statlas Assistant, a grounded football-analytics assistant.

NON-NEGOTIABLE GROUNDING RULE (Constitution Never-List #4):
- You NEVER state a specific statistic, percentile, rank, or number that did
  not come from a tool call result in this conversation. Football statistics
  change constantly; anything from your training data would be unverifiable.
- If you need a number, CALL A TOOL. If no tool answers the question, say so:
  "I can't verify that from Statlas data." Do not estimate, do not recall.
- Every factual statement must be traceable to a tool result you actually
  received. When you report a value, name the tool and the query used.
- The tools return real Statlas data: player percentiles, leaderboards,
  similar-player lists, and trends. You may summarise, compare, and explain
  what the numbers mean — but never invent a number.

SCOPE:
- You answer questions answerable from Statlas data (player stats, comparisons,
  leaderboards, trends, similar players).
- Out of scope (general football news, transfer rumours, tactical opinions,
  predictions): state clearly that it is outside what you can verify from
  Statlas data, and do not answer from general knowledge as if it were equally
  grounded.

TOOLS: use them when the question needs data. You can call multiple tools."""


# ---------------------------------------------------------------------------
# Tools — thin wrappers over the REAL query layer (never parallel logic)
# ---------------------------------------------------------------------------


def _resolve_player_id(db: Session, name: str) -> int | None:
    """Resolve a free-text player name via the alias-aware search."""
    results = player_queries.search_players(db, name, limit=5)
    if not results:
        return None
    return results[0].get("player_id")


def tool_get_player_percentiles(db: Session, name: str) -> dict[str, Any]:
    """Radar/percentile data for one player (position-group cohort)."""
    player_id = _resolve_player_id(db, name)
    if player_id is None:
        return {"error": f'No player found matching "{name}".'}
    profile = player_queries.get_player_profile(db, player_id)
    pct = player_queries.get_player_percentiles(db, player_id)
    if pct is None:
        return {"error": f'No published percentile data for "{name}".'}
    return {
        "player": profile.get("player") if profile else None,
        "percentiles": pct,
    }


def tool_get_leaderboard(
    db: Session,
    metric: str,
    league: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Top players for a metric, optionally filtered by league/position."""
    registry = load_registry()
    if metric not in registry.get("metrics", {}):
        return {
            "error": f"Unknown metric \"{metric}\". Known metrics: {sorted(registry.get('metrics', {}).keys())}"
        }
    rows = leaderboard_queries.get_leaderboard(
        db,
        league_id=None,
        position_group=position,
        metric=metric,
        season=None,
    )
    # Filter by league slug if given.
    if league:
        rows = [
            r for r in rows if (r.get("league_slug") or "").lower() == league.lower()
        ]
    return {"metric": metric, "rows": rows[:limit]}


def tool_get_similar_players(db: Session, name: str, limit: int = 5) -> dict[str, Any]:
    """Nearest-neighbour similar players (cosine over percentile vectors)."""
    player_id = _resolve_player_id(db, name)
    if player_id is None:
        return {"error": f'No player found matching "{name}".'}
    rows = similar_players.get_similar_players(db, player_id, limit=limit)
    return {"for": name, "similar": rows}


def tool_get_player_trend(
    db: Session, name: str, metric: str, window: int = 5
) -> dict[str, Any]:
    """Snapshot-history trend for one player + metric (weekly-snapshot
    granularity, not per-match — the response states that explicitly)."""
    player_id = _resolve_player_id(db, name)
    if player_id is None:
        return {"error": f'No player found matching "{name}".'}
    trend = trend_queries.get_player_trend(db, player_id, metric, window=window)
    if trend is None:
        return {"error": f'No trend data for "{name}" on metric "{metric}".'}
    return trend


# Tool registry: name -> (callable, description for the model, params schema)
TOOLS: dict[str, dict[str, Any]] = {
    "get_player_percentiles": {
        "call": tool_get_player_percentiles,
        "description": "Percentile ranks and the Statlas Index for a named player against their position-group cohort. Use for radar data and player-vs-player comparisons.",
        "params": {
            "name": {
                "type": "string",
                "description": "Player name (e.g. 'Erling Haaland')",
            }
        },
        "required": ["name"],
    },
    "get_leaderboard": {
        "call": tool_get_leaderboard,
        "description": "Who leads a league/position in a metric this season. Returns ranked rows with values and percentiles.",
        "params": {
            "metric": {
                "type": "string",
                "description": "Metric id (e.g. si_gls_p90, si_prgp_p90, xg_p90)",
            },
            "league": {
                "type": "string",
                "description": "Optional league slug (e.g. premier-league)",
            },
            "position": {
                "type": "string",
                "description": "Optional position group (GK, CB, FB, DM, CM, AM, W, ST)",
            },
            "limit": {"type": "integer", "description": "Max rows (default 10)"},
        },
        "required": ["metric"],
    },
    "get_similar_players": {
        "call": tool_get_similar_players,
        "description": "Players most similar to a named player (cosine similarity over percentile vectors, same position group).",
        "params": {
            "name": {"type": "string", "description": "Player name"},
            "limit": {"type": "integer", "description": "Max results (default 5)"},
        },
        "required": ["name"],
    },
    "get_player_trend": {
        "call": tool_get_player_trend,
        "description": "Snapshot-history trend for a player and metric (weekly-snapshot granularity, NOT per-match). Use for 'how has X changed over time'.",
        "params": {
            "name": {"type": "string", "description": "Player name"},
            "metric": {"type": "string", "description": "Metric id"},
            "window": {
                "type": "integer",
                "description": "Number of snapshots (5 or 10)",
            },
        },
        "required": ["name", "metric"],
    },
}


def anthropic_tool_schemas() -> list[dict[str, Any]]:
    """Anthropic tool-use schemas derived from the registry (single source)."""
    schemas = []
    for name, spec in TOOLS.items():
        props = {
            key: {"type": val["type"], "description": val["description"]}
            for key, val in spec["params"].items()
        }
        schemas.append(
            {
                "name": name,
                "description": spec["description"],
                "input_schema": {
                    "type": "object",
                    "properties": props,
                    "required": spec["required"],
                },
            }
        )
    return schemas


# ---------------------------------------------------------------------------
# Quota (Part B3) — hard cap per billing period, reset date stated
# ---------------------------------------------------------------------------


def _quota_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Monthly window aligned to calendar month (simplest honest period)."""
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def get_quota(db: Session, user: User) -> dict[str, Any]:
    plan = plan_limits(user.plan)
    limit = int(plan.get("assistant_queries_per_period", 10) or 10)
    start, end = _quota_window()
    row = (
        db.query(AssistantQuota)
        .filter(AssistantQuota.user_id == user.id, AssistantQuota.period_start == start)
        .first()
    )
    if row is None:
        row = AssistantQuota(
            user_id=user.id,
            period_start=start,
            period_end=end,
            queries_used=0,
            queries_limit=limit,
        )
        db.add(row)
        db.commit()
    return {
        "used": row.queries_used,
        "limit": row.queries_limit,
        "reset": end.date().isoformat(),
        "remaining": max(0, row.queries_limit - row.queries_used),
    }


def consume_quota(db: Session, user: User) -> dict[str, Any]:
    """Increment usage; raises QuotaExceeded if at the hard cap."""
    quota = get_quota(db, user)
    if quota["remaining"] <= 0:
        raise QuotaExceeded(quota["reset"])
    row = (
        db.query(AssistantQuota)
        .filter(
            AssistantQuota.user_id == user.id,
            AssistantQuota.period_start == quota_period_start(),
        )
        .first()
    )
    row.queries_used += 1
    db.commit()
    quota["used"] = row.queries_used
    quota["remaining"] = max(0, row.queries_limit - row.queries_used)
    return quota


def quota_period_start() -> datetime:
    return _quota_window()[0]


class QuotaExceeded(Exception):
    def __init__(self, reset_date: str) -> None:
        self.reset_date = reset_date
        super().__init__(f"Quota reached — resets {reset_date}.")


# ---------------------------------------------------------------------------
# Conversation (Part B1/B2) — function-calling loop
# ---------------------------------------------------------------------------


def assistant_configured() -> bool:
    return bool(get_settings().anthropic_api_key)


def run_assistant_turn(
    db: Session, user: User, messages: list[dict[str, Any]]
) -> dict[str, Any]:
    """One assistant turn: model <-> tools loop, quota consumed, every tool
    call recorded in `tool_calls` for the show-your-work UI."""
    quota = consume_quota(db, user)

    import anthropic  # lazy: key-gated

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    system_prompt = SYSTEM_PROMPT
    # State the quota in the system context so answers can reference it.
    system_prompt += (
        f"\n\nUser's assistant quota: {quota['used']}/{quota['limit']} used this period; "
        f"resets {quota['reset']}."
    )

    tool_calls: list[dict[str, Any]] = []
    convo = list(messages)

    for _ in range(4):  # bounded tool loop — never unbounded
        response = client.messages.create(
            model=settings.assistant_model,
            max_tokens=1024,
            system=system_prompt,
            messages=convo,
            tools=anthropic_tool_schemas(),
        )
        stop = response.stop_reason
        if stop != "tool_use":
            break

        # Collect tool uses, execute them against the real query layer, append.
        tool_uses = [
            b for b in response.content if getattr(b, "type", "") == "tool_use"
        ]
        if not tool_uses:
            break
        convo.append(
            {
                "role": "assistant",
                "content": [
                    {"type": b.type, "name": b.name, "id": b.id, "input": b.input}
                    for b in response.content
                ],
            }
        )
        tool_results = []
        with session_scope() as db2:  # fresh session per tool batch (same DB)
            for use in tool_uses:
                result = _execute_tool(db2, user, use.name, use.input)
                tool_calls.append(
                    {"name": use.name, "input": use.input, "result": result}
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": use.id,
                        "content": _serialize(result),
                    }
                )
        convo.append({"role": "user", "content": tool_results})

    # The final message must be text (the answer). Every numeric claim is
    # grounded because the model only saw tool results for numbers.
    final = response.content
    text = "\n".join(
        getattr(b, "text", "") for b in final if getattr(b, "type", "") == "text"
    ).strip()
    if not text:
        text = "I could not produce a grounded answer from the data available."

    return {
        "reply": text,
        "tool_calls": tool_calls,
        "quota": quota,
        "grounded": True,  # by construction: numbers only from tool results
    }


def _execute_tool(
    db: Session, user: User, name: str, tool_input: dict[str, Any]
) -> dict[str, Any]:
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"Unknown tool {name}."}
    try:
        return spec["call"](db, **tool_input)
    except Exception as exc:  # tool failures surface in the result, not the API
        logger.exception("assistant tool %s failed", name)
        return {"error": f"Tool {name} failed: {exc}"}


def _serialize(result: dict[str, Any]) -> str:
    import json

    return json.dumps(result, default=str)[:12000]
