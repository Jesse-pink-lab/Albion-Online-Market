"""Flip opportunity computations for normalized market rows."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Sequence

import logging

from utils.timefmt import rel_age
from utils.constants import MAX_DATA_AGE_HOURS

log = logging.getLogger(__name__)


def _ensure_utc(dt) -> datetime | None:
    """Return ``dt`` as a timezone aware UTC datetime or ``None``."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(dt, str):  # ISO 8601
        try:
            return datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:  # pragma: no cover - defensive
            return None
    return None


def _is_fresh(dt: datetime | None, max_age_hours: int) -> bool:
    if dt is None:
        return False
    if max_age_hours <= 0:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return dt >= cutoff


def compute_flips(
    rows: List[Dict],
    cities: Optional[Sequence[str]] = None,
    qualities: Optional[Sequence[int]] = None,
    min_profit: int = 0,
    min_roi: float = 0.0,
    max_results: int = 1000,
    max_age_hours: int = MAX_DATA_AGE_HOURS,
) -> List[Dict]:
    """Public entry point – delegates to the pure Python implementation."""

    return compute_flips_py(
        rows,
        cities=cities,
        qualities=qualities,
        min_profit=min_profit,
        min_roi=min_roi,
        max_results=max_results,
        max_age_hours=max_age_hours,
    )


def compute_flips_py(
    rows: List[Dict],
    cities: Optional[Sequence[str]] = None,
    qualities: Optional[Sequence[int]] = None,
    min_profit: int = 0,
    min_roi: float = 0.0,
    max_results: int = 1000,
    max_age_hours: int = MAX_DATA_AGE_HOURS,
) -> List[Dict]:
    """Compute flip opportunities from normalized rows using only Python."""

    if not rows:
        return []

    cities_set = set(cities or [])
    qualities_set = set(qualities or [])

    # Maps: (item_id, quality) -> city -> value
    best_buy: Dict[tuple, Dict[str, int]] = defaultdict(dict)
    best_sell: Dict[tuple, Dict[str, int]] = defaultdict(dict)
    updated: Dict[tuple, Dict[str, datetime]] = defaultdict(dict)
    names: Dict[tuple, str] = {}

    for r in rows:
        item = r.get("item_id")
        city = r.get("city")
        quality = int(r.get("quality") or 1)
        if cities_set and city not in cities_set:
            continue
        if qualities_set and quality not in qualities_set:
            continue

        udt = _ensure_utc(r.get("updated_dt"))
        if not _is_fresh(udt, max_age_hours):
            continue

        key = (item, quality)
        names[key] = r.get("item_name") or item

        buy = int(r.get("buy_price_max") or 0)
        sell = int(r.get("sell_price_min") or 0)

        if buy > 0:
            prev = best_buy[key].get(city, 0)
            if buy > prev:
                best_buy[key][city] = buy
        if sell > 0:
            prev_s = best_sell[key].get(city)
            if prev_s is None or sell < prev_s:
                best_sell[key][city] = sell
        if udt and (updated[key].get(city) is None or udt > updated[key][city]):
            updated[key][city] = udt

    out: List[Dict] = []
    for key, buys in best_buy.items():
        sells = best_sell.get(key, {})
        item, quality = key
        for src, buy_price in buys.items():
            for dst, sell_price in sells.items():
                if src == dst:
                    continue
                spread = sell_price - buy_price
                if buy_price <= 0 or sell_price <= 0 or spread <= 0:
                    continue
                roi = (spread / buy_price) * 100.0
                if spread < max(0, int(min_profit)):
                    continue
                if roi < float(min_roi):
                    continue
                udt = max(updated[key].get(src), updated[key].get(dst))
                out.append(
                    {
                        "item_id": item,
                        "item_name": names.get(key, item),
                        "from": src,
                        "to": dst,
                        "quality": quality,
                        "buy": buy_price,
                        "sell": sell_price,
                        "spread": spread,
                        "roi_pct": roi,
                        "updated_dt": udt,
                        "updated_human": rel_age(udt) if udt else "",
                    }
                )

    out.sort(key=lambda r: (r["roi_pct"], r["spread"]), reverse=True)
    return out[: int(max_results)]


__all__ = ["compute_flips", "compute_flips_py"]
