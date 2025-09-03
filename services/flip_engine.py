from __future__ import annotations

from typing import List, Dict, Sequence, Optional
from datetime import datetime, timezone
import math
import logging
import numpy as np
try:  # pragma: no cover - optional dependency
    import pandas as pd
except Exception:  # pragma: no cover - handled in tests
    pd = None

from utils.timefmt import rel_age

log = logging.getLogger(__name__)


def _to_py_utc(dt):
    """Best-effort conversion of ``dt`` to a timezone-aware UTC ``datetime``."""
    if dt is None:
        return None
    if isinstance(dt, float):
        if pd is not None:
            if pd.isna(dt):
                return None
        else:
            if math.isnan(dt):
                return None
    try:
        if pd is not None and isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            if dt.year < 2000 or dt.year > 2100:
                return None
            return dt
    except Exception:  # pragma: no cover - defensive
        pass
    return None


def _coerce_datetime_series(s):
    import pandas as pd
    # First, try generic parse (handles ISO/Timestamp/None)
    dt = pd.to_datetime(s, utc=True, errors="coerce")

    # For entries still NaT, try numeric epoch seconds
    mask = dt.isna()
    if mask.any():
        num = pd.to_numeric(s[mask], errors="coerce")
        dt_s = pd.to_datetime(num, unit="s", utc=True, errors="coerce")
        dt = dt.mask(mask, dt_s)

    # For entries still NaT, try ms
    mask = dt.isna()
    if mask.any():
        num = pd.to_numeric(s[mask], errors="coerce")
        dt_ms = pd.to_datetime(num, unit="ms", utc=True, errors="coerce")
        dt = dt.mask(mask, dt_ms)

    # For entries still NaT, try µs
    mask = dt.isna()
    if mask.any():
        num = pd.to_numeric(s[mask], errors="coerce")
        dt_us = pd.to_datetime(num, unit="us", utc=True, errors="coerce")
        dt = dt.mask(mask, dt_us)

    return dt


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
    if pd is None:
        return compute_flips_py(
            rows, cities, qualities, min_profit, min_roi, max_results, max_age_hours
        )

    try:
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
            dt = _coerce_datetime_series(df["updated_dt"])
            cutoff = pd.Timestamp.utcnow() - pd.Timedelta(hours=max_age_hours)
            df = df[dt >= cutoff]
        df = df.copy()
        df["udt"] = _coerce_datetime_series(df["updated_dt"])
        # clean numeric columns and drop zeros/negatives
        df["buy_price_max"] = pd.to_numeric(df["buy_price_max"], errors="coerce").fillna(0).astype(np.int64)
        df["sell_price_min"] = pd.to_numeric(df["sell_price_min"], errors="coerce").fillna(0).astype(np.int64)

        if df.empty:
            return []

        # Per item×city bests
        grp = df.groupby(["item_id", "city"], as_index=False, observed=False).agg(
            buy=("buy_price_max", "max"),
            sell=("sell_price_min", "min"),
            updated=("udt", "max"),
            qual=("quality", "max"),
        )

        # Drop zeros and non-sense
        grp = grp[(grp["buy"] > 0) | (grp["sell"] > 0)]
        grp = grp[(grp["buy"] >= 0) & (grp["sell"] >= 0)]
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
        # guard against absurd ROI (e.g., stale bad quotes)
        pairs = pairs.replace([np.inf, -np.inf], np.nan).dropna(subset=["roi_pct"])
        pairs = pairs[pairs["roi_pct"] < 100000]  # 1e5% max cap

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

        out = []
        for r in pairs.itertuples(index=False):
            raw_dt = r.updated_buy if pd.notna(r.updated_buy) else r.updated_sell
            udt = _to_py_utc(raw_dt)
            out.append(
                {
                    "item": r.item_id,
                    "buy_city": r.buy_city,
                    "sell_city": r.sell_city,
                    "buy": int(r.buy),
                    "sell": int(r.sell),
                    "spread": int(r.spread),
                    "roi_pct": float(r.roi_pct),
                    "updated_dt": udt,
                    "updated": rel_age(udt) if udt else "",
                }
            )
        return out
    except ImportError:
        return compute_flips_py(
            rows, cities, qualities, min_profit, min_roi, max_results, max_age_hours
        )


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
        dtv = _to_py_utc(dt)
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
        u = _to_py_utc(r.get("updated_dt"))
        if prev is None or (u and prev and u > prev):
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
                udt = u
                out.append(
                    {
                        "item": it,
                        "buy_city": cb,
                        "sell_city": cs,
                        "buy": b,
                        "sell": se,
                        "spread": spread,
                        "roi_pct": roi,
                        "updated_dt": udt,
                        "updated": rel_age(udt) if udt else "",
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
