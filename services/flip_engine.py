from __future__ import annotations

from typing import List, Dict, Sequence, Optional
from datetime import datetime, timezone
import math
import logging

log = logging.getLogger(__name__)


def _to_dt(x):
    from datetime import datetime, timezone
    if isinstance(x, datetime):
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    if isinstance(x, str):
        s = x.rstrip("Z")
        try:
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def compute_flips(
    rows: List[Dict],
    cities: Optional[Sequence[str]] = None,
    qualities: Optional[Sequence[int]] = None,
    min_profit: int = 0,
    min_roi: float = 0.0,
    max_results: int = 1000,
    max_age_hours: int = 24,
) -> List[Dict]:
    """Compute flip opportunities from normalized rows."""
    log.info(
        "Flip search: rows_in=%d, cities=%s, quals=%s, max_age=%dh",
        len(rows),
        len(cities) if cities else "All",
        "All" if not qualities else len(qualities),
        max_age_hours,
    )
    try:
        import pandas as pd
    except Exception:
        return compute_flips_py(
            rows, cities, qualities, min_profit, min_roi, max_results, max_age_hours
        )

    if not rows:
        return []

    df = pd.DataFrame(
        rows,
        columns=[
            "item_id",
            "city",
            "quality",
            "buy_price_max",
            "sell_price_min",
            "updated_dt",
        ],
    )

    # Reduce to necessary columns and drop zeros early
    df = df[(df["buy_price_max"] > 0) | (df["sell_price_min"] > 0)]
    df["item_id"] = df["item_id"].astype("category")
    df["city"] = df["city"].astype("category")

    # Filters
    if cities:
        df = df[df["city"].isin(list(cities))]
    if qualities:
        df = df[df["quality"].isin(list(qualities))]

    # Age filter
    if max_age_hours and max_age_hours > 0:
        dt = pd.to_datetime(df["updated_dt"].apply(_to_dt), utc=True)
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(hours=max_age_hours)
        df = df[dt >= cutoff]

    if df.empty:
        return []

    # Per item×city bests
    grp = df.groupby(["item_id", "city"], as_index=False).agg(
        buy=("buy_price_max", "max"),
        sell=("sell_price_min", "min"),
        updated=("updated_dt", "max"),
        qual=("quality", "max"),
    )

    grp = grp[(grp["buy"] > 0) | (grp["sell"] > 0)]
    log.info("Flip search: grouped item×city = %d (after filters)", len(grp))
    if grp.empty:
        return []

    # Build city→city pairs per item
    left = grp[["item_id", "city", "buy", "updated"]].rename(
        columns={"city": "buy_city", "buy": "buy", "updated": "updated_buy"}
    )
    right = grp[["item_id", "city", "sell", "updated"]].rename(
        columns={"city": "sell_city", "sell": "sell", "updated": "updated_sell"}
    )

    pairs = left.merge(right, on="item_id", how="inner")
    pairs = pairs[pairs["buy_city"] != pairs["sell_city"]]
    pair_count = len(pairs)

    pairs = pairs[pairs["buy"] > 0]
    pairs["spread"] = (pairs["sell"] - pairs["buy"]).clip(lower=0)
    pairs["roi_pct"] = (pairs["spread"] / pairs["buy"]) * 100.0

    before_threshold = len(pairs)
    if min_profit:
        pairs = pairs[pairs["spread"] >= int(min_profit)]
    if min_roi:
        pairs = pairs[pairs["roi_pct"] >= float(min_roi)]
    after_threshold = len(pairs)
    log.info(
        "Flip search: pairs computed = %d, candidates after thresholds = %d",
        pair_count,
        after_threshold,
    )

    if pairs.empty:
        return []

    pairs = pairs.sort_values(["roi_pct", "spread"], ascending=[False, False]).head(
        int(max_results)
    )

    now = pd.Timestamp.utcnow()

    def rel(dt):
        if not pd.isna(dt):
            secs = (now - pd.to_datetime(dt, utc=True)).total_seconds()
            if secs < 60:
                return f"{int(secs)}s"
            mins = int(secs // 60)
            if mins < 60:
                return f"{mins}m"
            return f"{int(mins // 60)}h"
        return ""

    out = []
    for r in pairs.itertuples(index=False):
        out.append(
            {
                "item": r.item_id,
                "buy_city": r.buy_city,
                "sell_city": r.sell_city,
                "buy": int(r.buy),
                "sell": int(r.sell),
                "spread": int(r.spread),
                "roi_pct": float(r.roi_pct),
                "updated_age": rel(r.updated_buy if pd.notna(r.updated_buy) else r.updated_sell),
                "updated_dt": str(r.updated_buy or r.updated_sell),
            }
        )
    return out


def compute_flips_py(rows, cities, qualities, min_profit, min_roi, max_results, max_age_hours):
    from collections import defaultdict

    if not rows:
        return []

    log.info(
        "Flip search: rows_in=%d, cities=%s, quals=%s, max_age=%dh",
        len(rows),
        len(cities) if cities else "All",
        "All" if not qualities else len(qualities),
        max_age_hours,
    )

    def recent(dt):
        dtv = _to_dt(dt)
        if dtv is None:
            return False
        if max_age_hours <= 0:
            return True
        return (datetime.now(timezone.utc) - dtv).total_seconds() <= max_age_hours * 3600

    best_buy = defaultdict(lambda: defaultdict(int))
    best_sell = defaultdict(lambda: defaultdict(lambda: math.inf))
    updated = defaultdict(lambda: defaultdict(lambda: None))

    for r in rows:
        if cities and r["city"] not in cities:
            continue
        if qualities and r["quality"] not in qualities:
            continue
        if max_age_hours > 0 and not recent(r.get("updated_dt")):
            continue
        b = int(r.get("buy_price_max") or 0)
        s = int(r.get("sell_price_min") or 0)
        if b <= 0 and s <= 0:
            continue
        it, c = r["item_id"], r["city"]
        if b > best_buy[it][c]:
            best_buy[it][c] = b
        if s > 0 and s < best_sell[it][c]:
            best_sell[it][c] = s
        prev = updated[it][c]
        u = r.get("updated_dt")
        if prev is None or (_to_dt(u) and _to_dt(prev) and _to_dt(u) > _to_dt(prev)):
            updated[it][c] = u

    out = []
    pair_count = 0
    for it, buys in best_buy.items():
        sells = best_sell.get(it, {})
        cities_b = list(buys.keys())
        cities_s = list(sells.keys())
        for cb in cities_b:
            b = buys[cb]
            if b <= 0:
                continue
            for cs in cities_s:
                if cs == cb:
                    continue
                se = sells[cs]
                if not math.isfinite(se) or se <= 0:
                    continue
                pair_count += 1
                spread = se - b
                if spread < max(0, int(min_profit)):
                    continue
                roi = (spread / b) * 100.0
                if roi < float(min_roi):
                    continue
                u = updated[it][cb] or updated[it].get(cs)
                age = ""
                udt = _to_dt(u)
                if udt:
                    secs = (datetime.now(timezone.utc) - udt).total_seconds()
                    age = (
                        f"{int(secs)}s"
                        if secs < 60
                        else (f"{int(secs // 60)}m" if secs < 3600 else f"{int(secs // 3600)}h")
                    )
                out.append(
                    {
                        "item": it,
                        "buy_city": cb,
                        "sell_city": cs,
                        "buy": b,
                        "sell": se,
                        "spread": spread,
                        "roi_pct": roi,
                        "updated_age": age,
                        "updated_dt": u,
                    }
                )
    after_threshold = len(out)
    log.info(
        "Flip search: pairs computed = %d, candidates after thresholds = %d",
        pair_count,
        after_threshold,
    )
    out.sort(key=lambda r: (r["roi_pct"], r["spread"]), reverse=True)
    return out[: int(max_results)]


__all__ = ["compute_flips"]
