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
    """Return formatted UTC timestamp suitable for tooltips.

    The specification for the UI requires a slightly more human friendly
    representation than :func:`datetime.isoformat`; the ``T`` separator is
    replaced with a space, e.g. ``"2024-01-02 03:04:05Z"``.
    """

    return utc_dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def now_utc_iso() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["to_utc", "rel_age", "fmt_tooltip", "now_utc_iso"]
