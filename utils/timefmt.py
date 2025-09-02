"""Time formatting helpers used across the UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Union


def to_utc(dt_or_str: Union[datetime, str]) -> datetime:
    """Return ``datetime`` converted to UTC.

    Parameters
    ----------
    dt_or_str:
        Either a :class:`datetime` instance or an ISO8601 string.  Strings
        may or may not include a ``Z`` timezone designator.
    """

    if isinstance(dt_or_str, datetime):
        dt = dt_or_str
    else:
        dt = datetime.fromisoformat(dt_or_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def rel_age(utc_dt: datetime) -> str:
    """Return a human friendly age for ``utc_dt`` relative to now."""

    delta = datetime.now(timezone.utc) - utc_dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"


def fmt_tooltip(utc_dt: datetime) -> str:
    """Return ISO8601 string suitable for tooltips."""

    return utc_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
