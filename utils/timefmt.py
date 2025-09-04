"""Time formatting helpers used across the UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Union
import math

try:
    from dateutil import parser as du_parser  # optional
except Exception:  # pragma: no cover - optional dep
    du_parser = None


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


def _to_dt(value: Any) -> Optional[datetime]:
    """
    Convert several timestamp representations to UTC-aware datetime.
    Returns None if the string/number cannot be parsed.
    Accepted forms:
      - aware/naive datetime (naive -> assume UTC)
      - ISO-8601 string
      - int/float unix seconds
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)) and math.isfinite(value):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            if du_parser is not None:
                try:
                    dt = du_parser.isoparse(v)
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    return None
            return None

    return None


def rel_age(dt_like) -> str:
    """Return a human friendly age for ``dt_like`` relative to now."""

    dt = _to_dt(dt_like) or datetime.now(timezone.utc)
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

    dt = _to_dt(dt_like) or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%SZ")


def now_utc_iso() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["to_utc", "rel_age", "fmt_tooltip", "now_utc_iso"]
