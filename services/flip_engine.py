"""Flip opportunity computations with drop-reason statistics."""

from __future__ import annotations

from collections import defaultdict
import logging
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from utils.constants import MAX_DATA_AGE_HOURS

log = logging.getLogger(__name__)


def build_flips(
    *,
    rows: Sequence[Dict],
    items_filter: Optional[Set[str]],
    src_cities: Iterable[str],
    dst_cities: Iterable[str],
    qualities: Iterable[int] | None,
    min_profit: int,
    min_roi: float,
    max_age_hours: int,
    max_results: int,
) -> tuple[list[dict], dict[str, int]]:
    """Core flip builder returning flips and drop statistics."""

    stats: Dict[str, int] = defaultdict(int)
    now_hours = time.time() / 3600.0
    src_set, dst_set = set(src_cities or []), set(dst_cities or [])
    qual_set = set(qualities or [])
    item_set = set(items_filter) if items_filter else None

    best_buy: Dict[tuple, Dict[str, int]] = defaultdict(dict)
    best_sell: Dict[tuple, Dict[str, int]] = defaultdict(dict)
    updated: Dict[tuple, Dict[str, float]] = defaultdict(dict)
    names: Dict[tuple, str] = {}

    for r in rows:
        stats["seen_rows"] += 1
        item = r.get("item_id")
        if item_set is not None and item not in item_set:
            stats["not_in_items"] += 1
            continue
        city = r.get("city")
        if city not in src_set and city not in dst_set:
            stats["bad_city"] += 1
            continue
        quality = int(r.get("quality") or 1)
        if qual_set and quality not in qual_set:
            continue
        upd = float(r.get("updated_epoch_hours") or 0.0)
        if max_age_hours > 0 and (upd <= 0 or (now_hours - upd) > max_age_hours):
            stats["stale"] += 1
            continue

        key = (item, quality)
        names[key] = r.get("item_name") or item
        buy = int(r.get("buy_price_max") or 0)
        sell = int(r.get("sell_price_min") or 0)
        if buy > 0:
            prev = best_buy[key].get(city, 0)
            if buy > prev:
                best_buy[key][city] = buy
                updated[key][city] = upd
        if sell > 0:
            prev_s = best_sell[key].get(city)
            if prev_s is None or sell < prev_s:
                best_sell[key][city] = sell
                updated[key][city] = upd

    dedupe: Dict[Tuple[str, int, str, str], dict] = {}
    for (item, quality), buys in best_buy.items():
        sells = best_sell.get((item, quality), {})
        for src in src_set:
            for dst in dst_set:
                if src == dst:
                    stats["same_city"] += 1
                    continue
                buy = buys.get(src)
                if not buy:
                    stats["no_buy"] += 1
                    continue
                sell = sells.get(dst)
                if not sell:
                    stats["no_sell"] += 1
                    continue
                spread = sell - buy
                if spread <= 0:
                    stats["nonpos_spread"] += 1
                    continue
                if spread < int(min_profit):
                    stats["low_profit"] += 1
                    continue
                roi = spread / buy
                if roi < float(min_roi):
                    stats["low_roi"] += 1
                    continue
                upd = max(updated[(item, quality)].get(src, 0.0), updated[(item, quality)].get(dst, 0.0))
                flip = {
                    "item_id": item,
                    "item_name": names.get((item, quality), item),
                    "quality": quality,
                    "buy_city": src,
                    "sell_city": dst,
                    "buy": buy,
                    "sell": sell,
                    "spread": spread,
                    "roi": roi,
                    "roi_pct": roi * 100.0,
                    "updated_epoch_hours": upd,
                }
                key = (item, quality, src, dst)
                cur = dedupe.get(key)
                if cur is None or spread > cur["spread"]:
                    dedupe[key] = flip

    flips = list(dedupe.values())
    stats["kept"] = len(flips)
    flips.sort(key=lambda r: (r["roi"], r["spread"]), reverse=True)
    return flips[: int(max_results)], dict(stats)


def compute_flips(
    rows: List[Dict],
    cities: Optional[Sequence[str]] = None,
    qualities: Optional[Sequence[int]] = None,
    min_profit: int = 0,
    min_roi: float = 0.0,
    max_results: int = 1000,
    max_age_hours: int = MAX_DATA_AGE_HOURS,
) -> List[Dict]:
    """Compatibility wrapper returning only flips."""

    adapted: List[Dict] = []
    for r in rows:
        rr = dict(r)
        if "updated_epoch_hours" not in rr:
            udt = r.get("updated_dt")
            if isinstance(udt, datetime):
                rr["updated_epoch_hours"] = udt.timestamp() / 3600.0
            else:
                rr["updated_epoch_hours"] = 0.0
        adapted.append(rr)

    roi_decimal = float(min_roi) / 100.0 if min_roi > 1 else float(min_roi)
    flips, _ = build_flips(
        rows=adapted,
        items_filter=None,
        src_cities=set(cities or []),
        dst_cities=set(cities or []),
        qualities=qualities,
        min_profit=min_profit,
        min_roi=roi_decimal,
        max_age_hours=max_age_hours,
        max_results=max_results,
    )
    for f in flips:
        f["from"] = f["buy_city"]
        f["to"] = f["sell_city"]
    return flips


compute_flips_py = compute_flips

__all__ = ["build_flips", "compute_flips", "compute_flips_py"]

