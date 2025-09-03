"""Time formatting helpers used across the UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Union


def to_utc(dt_or_str: Union[datetime, str]) -> datetime:
    """Return ``datetime`` converted to UTC."""

    if isinstance(dt_or_str, datetime):
        dt = dt_or_str
    else:
        dt = datetime.fromisoformat(dt_or_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _to_dt(x):
    """Best-effort conversion of ``x`` to an aware ``datetime`` in UTC."""
    if isinstance(x, datetime):
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    if isinstance(x, str):
        s = x.rstrip("Z")
        try:
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        except Exception:  # pragma: no cover - defensive
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def rel_age(dt_like) -> str:
    """Return a human friendly age for ``dt_like`` relative to now."""

    dt = _to_dt(dt_like)
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m"
    hours = mins // 60
    return f"{hours}h"


def fmt_tooltip(dt_like) -> str:
    """Return formatted UTC timestamp suitable for tooltips."""

    dt = _to_dt(dt_like)
    return dt.strftime("%Y-%m-%d %H:%M:%SZ")


def now_utc_iso() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["to_utc", "rel_age", "fmt_tooltip", "now_utc_iso"]
