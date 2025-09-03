"""Market price fetching utilities with batching and backoff."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
from typing import List, Dict
from urllib.parse import urlencode
import requests
from requests import HTTPError
import pandas as pd

from datasources.http import get_shared_session
from datasources.aodp_url import base_for, build_prices_request, DEFAULT_CITIES
from utils.params import qualities_to_csv, cities_to_list
from utils.items import parse_items, items_catalog_codes
from utils.timefmt import to_utc, now_utc_iso
from core.signals import signals

log = logging.getLogger(__name__)

DEFAULT_QUALITIES = "1,2,3,4,5"  # include 5 (Masterpiece)

# Cache of the latest normalized and aggregated rows
LATEST_ROWS: list[dict] = []
LATEST_RAW_DF: pd.DataFrame | None = None
LATEST_AGG_DF: pd.DataFrame | None = None

# Conservative safety margin; many proxies reject > ~2000 bytes.
MAX_URL_LEN = 1800


def _estimate_url_len(base: str, items: list[str], cities_csv: str, quals_csv: str) -> int:
    """Estimate URL length for the given parameters."""
    path = f"{base}/api/v2/stats/prices/{','.join(items)}.json"
    q = urlencode({"locations": cities_csv, "qualities": quals_csv})
    return len(path) + 1 + len(q)  # +1 for "?"


def _chunk_by_len_and_count(
    all_items: list[str],
    base: str,
    cities_csv: str,
    quals_csv: str,
    max_count: int,
    max_url: int = MAX_URL_LEN,
) -> list[list[str]]:
    """Chunk ``all_items`` by item count and estimated URL length."""
    chunks: list[list[str]] = []
    cur: list[str] = []
    for it in all_items:
        probe = cur + [it]
        if (
            len(probe) > 0
            and len(probe) <= max_count
            and _estimate_url_len(base, probe, cities_csv, quals_csv) <= max_url
        ):
            cur = probe
            continue
        if cur:
            chunks.append(cur)
            cur = []
        if _estimate_url_len(base, [it], cities_csv, quals_csv) <= max_url and max_count >= 1:
            cur = [it]
        else:
            chunks.append([it])
    if cur:
        chunks.append(cur)
    return chunks


def fetch_prices(
    server,
    items_edit_text,
    cities_sel,
    qual_sel,
    session: requests.Session | None = None,
    settings=None,
    on_progress=None,
    cancel=lambda: False,
    fetch_all: bool | None = None,
):
    sess = session or get_shared_session()
    typed = parse_items(items_edit_text)
    use_all = (
        fetch_all
        if fetch_all is not None
        else bool(getattr(settings, "fetch_all_items", True))
    )
    if (not typed) and not use_all:
        log.info("No items to request (typed=%d, fetch_all=%s).", len(typed), use_all)
        return []

    catalog: list[str] = []
    if (not typed) or use_all:
        catalog = list(items_catalog_codes())
    items = catalog if (not typed and use_all) else typed
    log.info(
        "Item selection: catalog=%d typed=%d fetch_all=%s -> final=%d",
        len(catalog), len(typed), use_all, len(items),
    )

    cities = cities_to_list(cities_sel, DEFAULT_CITIES)
    cities_csv = ",".join(cities)
    quals_csv = qualities_to_csv(qual_sel)
    base = base_for(server)

    # Respect settings.ItemsPerRequest if present (default 150)
    chunk_size = int(
        getattr(settings, "items_per_request", None)
        or (settings.get("items_per_request") if isinstance(settings, dict) else None)
        or 150
    )
    max_workers = 4
    chunks = _chunk_by_len_and_count(items, base, cities_csv, quals_csv, chunk_size)
    results: List[Dict] = []

    def pull(chunk, attempt=1):
        url, params = build_prices_request(base, chunk, cities, quals_csv)
        log.info(
            "AODP GET: base=%s items=%d cities=%d quals=%s attempt=%d",
            base, len(chunk), len(cities), quals_csv, attempt,
        )
        log.debug("AODP URL: %s params=%s", url, params)
        r = sess.get(url, params=params, timeout=(5,10))
        if r.status_code == 414:
            if len(chunk) == 1:
                log.warning("414 on single item; skipping id=%s", chunk[0])
                return []
            mid = max(1, len(chunk)//2)
            left = pull(chunk[:mid], 1)
            right = pull(chunk[mid:], 1)
            return (left or []) + (right or [])
        if r.status_code in (429,500,502,503,504) and attempt <= 4:
            time.sleep(0.5 * (2 ** (attempt-1)))
            return pull(chunk, attempt+1)
        r.raise_for_status()
        data = r.json() or []
        log.info("AODP RESP: status=%s records=%d", r.status_code, len(data))
        return data

    failed = 0
    failed_chunks: list[list[str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_chunk = {ex.submit(pull, c): c for c in chunks}
        total = len(future_to_chunk)
        for idx, fut in enumerate(as_completed(future_to_chunk), 1):
            if cancel():
                break
            chunk = future_to_chunk[fut]
            try:
                results.extend(fut.result())
            except HTTPError as e:
                if getattr(e.response, "status_code", None) == 429:
                    failed_chunks.append(chunk)
                failed += 1
                log.error("Chunk failed (%d/%d): %r", idx, total, e)
            except Exception as e:
                failed += 1
                log.error("Chunk failed (%d/%d): %r", idx, total, e)
            if on_progress:
                on_progress(int(idx / total * 100), f"Fetched {idx}/{total} chunks")
    if failed_chunks:
        log.info("Retry tail for %d 429-chunks at low rate", len(failed_chunks))
        for c in failed_chunks:
            try:
                data = pull(c, attempt=1)  # pull already has backoff
                results.extend(data or [])
            except Exception as e:
                log.warning("Tail retry failed: %r", e)
            time.sleep(0.4)
    if failed:
        log.warning("Refresh completed with %d failed chunks (see logs)", failed)
    norm = normalize_and_dedupe(results)
    on_fetch_completed(norm)
    return norm


def normalize_and_dedupe(rows: List[Dict]) -> List[Dict]:
    out: Dict[tuple, Dict] = {}
    for row in rows:
        item = row.get("item_id")
        city = row.get("city")
        quality = int(row.get("quality") or 1)
        key = (item, city, quality)

        buy = int(row.get("buy_price_max") or 0)
        sell = int(row.get("sell_price_min") or 0)
        spread = max(sell - buy, 0)
        roi = (spread / buy * 100.0) if buy > 0 else 0.0

        def ts(d):
            try: return to_utc(d)
            except: return None
        sell_dt = ts(row.get("sell_price_min_date"))
        buy_dt  = ts(row.get("buy_price_max_date"))
        best_dt = sell_dt or buy_dt

        prev = out.get(key)
        keep = (prev is None)
        if prev and best_dt:
            keep = best_dt > prev["updated_dt"]
        if keep:
            out[key] = {
                "item_id": item,
                "city": city,
                "quality": quality,
                "buy_price_max": buy,
                "sell_price_min": sell,
                "spread": spread,
                "roi_pct": roi,
                "buy_city": city if buy else None,
                "sell_city": city if sell else None,
                "updated_dt": best_dt,
            }
    return list(out.values())


AGG_COLS = {
    "sell_price_min": "min",
    "buy_price_max": "max",
    "updated_dt": "max",
}


def aggregate_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse raw rows to one per (item_id, city, quality)."""
    if df.empty:
        return df
    grp = (
        df.groupby(["item_id", "city", "quality"], as_index=False)
        .agg(AGG_COLS)
        .rename(columns={"sell_price_min": "sell_min", "buy_price_max": "buy_max"})
    )
    grp["spread"] = (grp["sell_min"] - grp["buy_max"]).clip(lower=0)
    grp["roi"] = (
        (grp["sell_min"] - grp["buy_max"]) / grp["buy_max"]
    ).replace([pd.NA, pd.NaT], 0).fillna(0)
    return grp


def top_opportunities(df: pd.DataFrame, limit: int = 20) -> list[dict]:
    """Compute top arbitrage opportunities from aggregated rows."""
    if df.empty:
        return []
    cands = df[(df["buy_max"] > 0) & (df["sell_min"] > 0) & (df["spread"] > 0)]
    cands = cands.sort_values(["roi", "spread"], ascending=[False, False]).head(limit)
    out = []
    for r in cands.itertuples(index=False):
        out.append(
            {
                "item": r.item_id,
                "buy_city": r.city,
                "sell_city": r.city,
                "buy_price": int(r.buy_max),
                "sell_price": int(r.sell_min),
                "spread": int(r.spread),
                "roi_pct": float(r.roi * 100),
                "updated_dt": r.updated_dt,
            }
        )
    return out


def emit_summary(df: pd.DataFrame):
    summary = {
        "last_update_utc": now_utc_iso(),
        "records": int(len(df)),
        "top_opportunities": top_opportunities(df, 20),
    }
    signals.market_data_ready.emit(summary)


def on_fetch_completed(norm_rows: list[dict]):
    """Cache and emit latest normalized rows."""
    global LATEST_ROWS, LATEST_RAW_DF, LATEST_AGG_DF
    LATEST_RAW_DF = pd.DataFrame(norm_rows or [])
    LATEST_AGG_DF = aggregate_prices(LATEST_RAW_DF)
    LATEST_ROWS = LATEST_AGG_DF.to_dict("records")
    signals.market_rows_updated.emit(LATEST_ROWS)
    emit_summary(LATEST_AGG_DF)


__all__ = [
    "fetch_prices",
    "normalize_and_dedupe",
    "aggregate_prices",
    "DEFAULT_CITIES",
    "DEFAULT_QUALITIES",
    "top_opportunities",
    "emit_summary",
    "on_fetch_completed",
    "LATEST_ROWS",
    "LATEST_RAW_DF",
    "LATEST_AGG_DF",
]
