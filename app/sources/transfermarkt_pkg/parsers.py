"""Transfermarkt HTML parsers -- market value, fee, and date extraction."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.sources.base import SourceError


class TransfermarktSchemaChangedError(SourceError):
    """Transfermarkt's HTML structure changed in a way we refuse to guess at."""


def _parse_market_value(text: str) -> float | None:
    """Parse Transfermarkt market value strings like '€85.00m' or '€500K' to EUR.

    Returns None when the text is unparseable (e.g. ' цена неизвестна').
    """
    if not text:
        return None
    text = text.strip().replace("\xa0", " ")
    # Match patterns like: €85.00m, €500K, €1.50bn, €23.50m, £85.00m
    m = re.search(r"[€$£]\s*([\d.,]+)\s*(bn|mn|m|k|K|M|B)?", text, re.IGNORECASE)
    if not m:
        return None
    num_str = m.group(1).replace(",", "")
    try:
        num = float(num_str)
    except ValueError:
        return None
    suffix = (m.group(2) or "").lower()
    if suffix in ("bn", "b"):
        num *= 1_000_000_000
    elif suffix in ("mn", "m"):
        num *= 1_000_000
    elif suffix in ("k",):
        num *= 1_000
    return num


def _parse_transfer_fee(text: str) -> float | None:
    """Parse transfer fee text. Handles 'Free transfer', 'Loan', numeric values."""
    if not text:
        return None
    text = text.strip().lower()
    if "free" in text or "ablösefrei" in text:
        return 0.0
    if "loan" in text or "leihgeschäft" in text:
        return None  # loan fees are not always public
    return _parse_market_value(text)


def _parse_date(text: str) -> datetime | None:
    """Parse Transfermarkt date formats (DD/MM/YYYY, MMM D, YYYY, etc.)."""
    if not text:
        return None
    text = text.strip()
    for fmt in ("%b %d, %Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

