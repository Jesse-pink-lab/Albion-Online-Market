"""Market price fetching utilities with batching and backoff."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
from typing import List, Dict
from urllib.parse import urlencode
import json
import requests
from requests import HTTPError
import pandas as pd

from datasources.http import get_shared_session
from datasources.aodp_url import base_for, build_prices_request, DEFAULT_CITIES
from utils.params import qualities_to_csv, cities_to_list
from utils.items import parse_items, items_catalog_codes
from utils.timefmt import to_utc, now_utc_iso, rel_age
from utils.constants import MAX_DATA_AGE_HOURS
from core.signals import signals
from services.netlimit import bucket
from services.http_cache import get_cached, put_cached

log = logging.getLogger(__name__)

DEFAULT_QUALITIES = "1,2,3,4,5"  # include 5 (Masterpiece)

# Cache of the latest normalized and aggregated rows
LATEST_ROWS: list[dict] = []
LATEST_RAW_DF: pd.DataFrame | None = None
LATEST_AGG_DF: pd.DataFrame | None = None

# Conservative safety margin; many proxies reject > ~2000 bytes.
MAX_URL_LEN = 1800


def chunk_by_url(
    items: list[str],
    base: str,
    cities: list[str],
    qualities: list[int],
    max_url: int = 1900,
):
    """Yield chunks of items whose request URL stays under ``max_url`` characters."""
    cur: list[str] = []
    for it in items:
        test = ",".join(cur + [it])
        url = (
            f"{base}/api/v2/stats/prices/{test}.json"
            f"?locations={','.join(cities)}&qualities={','.join(map(str, qualities))}"
        )
        if len(url) > max_url and cur:
            yield cur
            cur = [it]
        else:
            cur.append(it)
    if cur:
        yield cur


# Backwards compatibility helpers for tests
def _estimate_url_len(base: str, items: list[str], cities_csv: str, quals_csv: str) -> int:
    path = f"{base}/api/v2/stats/prices/{','.join(items)}.json"
    q = urlencode({"locations": cities_csv, "qualities": quals_csv})
    return len(path) + 1 + len(q)


def _chunk_by_len_and_count(
    all_items: list[str],
    base: str,
    cities_csv: str,
    quals_csv: str,
    max_count: int,
    max_url: int = MAX_URL_LEN,
) -> list[list[str]]:
    chunks: list[list[str]] = []
    cur: list[str] = []
    for it in all_items:
        probe = cur + [it]
        if (
            len(probe) <= max_count
            and _estimate_url_len(base, probe, cities_csv, quals_csv) <= max_url
        ):
            cur = probe
        else:
            if cur:
                chunks.append(cur)
            cur = [it]
    if cur:
        chunks.append(cur)
    return chunks


MIN_CONC, MAX_CONC = 1, 6
_conc = 4
_last429 = 0


def _on_result(status_code: int) -> None:
    global _conc, _last429
    if status_code == 429:
        _last429 += 1
        _conc = max(MIN_CONC, _conc - 1)
    else:
        _last429 = max(0, _last429 - 1)
        if _last429 == 0:
            _conc = min(MAX_CONC, _conc + 1)


def current_concurrency() -> int:
    return _conc


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
    global MAX_CONC, _conc
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
    quals_list = [int(q) for q in quals_csv.split(",") if q]
    base = base_for(server)

    cache_ttl = int(
        getattr(settings, "cache_ttl_sec", None)
        or (settings.get("cache_ttl_sec") if isinstance(settings, dict) else None)
        or 120
    )

    max_conf = int(
        getattr(settings, "max_concurrency", None)
        or (settings.get("max_concurrency") if isinstance(settings, dict) else None)
        or MAX_CONC
    )
    MAX_CONC = max(1, min(8, max_conf))
    _conc = min(_conc, MAX_CONC)
    bucket.rate = float(
        getattr(settings, "global_rate_per_sec", None)
        or (settings.get("global_rate_per_sec") if isinstance(settings, dict) else None)
        or bucket.rate
    )
    bucket.capacity = int(
        getattr(settings, "global_rate_capacity", None)
        or (settings.get("global_rate_capacity") if isinstance(settings, dict) else None)
        or bucket.capacity
    )
    bucket.tokens = bucket.capacity

    chunks = list(chunk_by_url(items, base, cities, quals_list))
    max_workers = current_concurrency()
    results: List[Dict] = []

    def pull(chunk, attempt=1):
        url, params = build_prices_request(base, chunk, cities, quals_csv)
        full_url = requests.Request("GET", url, params=params).prepare().url
        log.info(
            "AODP GET: base=%s items=%d cities=%d quals=%s attempt=%d",
            base, len(chunk), len(cities), quals_csv, attempt,
        )
        log.debug("AODP URL: %s params=%s", url, params)
        cached = get_cached(full_url)
        if cached:
            body, status, headers = cached
            r = None
        else:
            bucket.acquire()
            r = sess.get(url, params=params, timeout=(5, 10))
            status = r.status_code
            _on_result(status)
            body = getattr(r, "content", b"")
            headers = getattr(r, "headers", {})
            if status == 200 and body:
                put_cached(full_url, body, status, headers, ttl=cache_ttl)
        if status == 414:
            if len(chunk) == 1:
                log.warning("414 on single item; skipping id=%s", chunk[0])
                return []
            mid = max(1, len(chunk) // 2)
            left = pull(chunk[:mid], 1)
            right = pull(chunk[mid:], 1)
            return (left or []) + (right or [])
        if status in (429, 500, 502, 503, 504) and attempt <= 4:
            time.sleep(0.5 * (2 ** (attempt - 1)))
            return pull(chunk, attempt + 1)
        if status != 200:
            raise HTTPError(f"Unexpected status {status}")
        try:
            if body:
                data = json.loads(body.decode("utf-8"))
            elif r is not None:
                data = r.json() or []
            else:
                data = []
        except Exception:
            data = []
        log.info("AODP RESP: status=%s records=%d", status, len(data))
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
    """Normalize raw API rows into one record per (item_id, city, quality).

    The returned dictionaries contain all values required by the UI so that no
    additional calculations are needed later.  Older records beyond
    ``MAX_DATA_AGE_HOURS`` are discarded.
    """

    cutoff = None
    if MAX_DATA_AGE_HOURS and MAX_DATA_AGE_HOURS > 0:
        from datetime import datetime, timezone, timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_DATA_AGE_HOURS)

    out: Dict[tuple, Dict] = {}
    for row in rows:
        item_id = (row.get("item_id") or "").strip().upper()
        city = row.get("city")
        quality = int(row.get("quality") or 1)
        key = (item_id, city, quality)

        buy = int(row.get("buy_price_max") or 0)
        sell = int(row.get("sell_price_min") or 0)

        def ts(d):
            try:
                return to_utc(d)
            except Exception:  # pragma: no cover - defensive
                return None

        sell_dt = ts(row.get("sell_price_min_date"))
        buy_dt = ts(row.get("buy_price_max_date"))
        from datetime import datetime, timezone
        updated_dt = max(
            [d for d in (sell_dt, buy_dt) if d is not None],
            default=datetime.now(timezone.utc),
        )
        if cutoff and updated_dt < cutoff:
            continue

        prev = out.get(key)
        if prev is None:
            out[key] = {
                "item_id": item_id,
                "item_name": row.get("item_name") or item_id,
                "city": city,
                "quality": quality,
                "buy_price_max": buy,
                "sell_price_min": sell if sell > 0 else 0,
                "updated_dt": updated_dt,
            }
        else:
            prev["buy_price_max"] = max(prev["buy_price_max"], buy)
            if sell > 0:
                prev_sell = prev.get("sell_price_min") or 0
                prev["sell_price_min"] = min(prev_sell or sell, sell) if prev_sell else sell
            if updated_dt and (prev.get("updated_dt") is None or updated_dt > prev["updated_dt"]):
                prev["updated_dt"] = updated_dt

    normalized: List[Dict] = []
    for rec in out.values():
        buy = int(rec.get("buy_price_max") or 0)
        sell = int(rec.get("sell_price_min") or 0)
        spread = sell - buy
        if spread < 0:
            spread = 0
        roi = 100.0 * spread / max(1, buy)
        udt = rec.get("updated_dt")
        rec.update(
            {
                "spread": spread,
                "roi_pct": roi,
                "updated_human": rel_age(udt) if udt else "",
            }
        )
        if udt:
            rec["updated_iso"] = udt.isoformat()
            rec["updated_epoch_hours"] = udt.timestamp() / 3600.0
        else:
            rec["updated_iso"] = None
            rec["updated_epoch_hours"] = 0.0
        normalized.append(rec)

    return normalized


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
    """Compute top opportunities from normalized rows.

    This is a simple ranking of rows by ROI and spread; it does not attempt to
    cross-reference cities.  The structure of the returned dictionaries matches
    the historical API used by the dashboard widget.
    """
    if df.empty:
        return []
    cands = df[(df["buy_price_max"] > 0) & (df["sell_price_min"] > 0) & (df["spread"] > 0)]
    cands = cands.sort_values(["roi_pct", "spread"], ascending=[False, False]).head(limit)
    out = []
    for r in cands.itertuples(index=False):
        out.append(
            {
                "item": r.item_id,
                "buy_city": r.city,
                "sell_city": r.city,
                "buy_price": int(r.buy_price_max),
                "sell_price": int(r.sell_price_min),
                "spread": int(r.spread),
                "roi_pct": float(r.roi_pct),
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
    LATEST_AGG_DF = LATEST_RAW_DF  # already aggregated by normalization
    LATEST_ROWS = norm_rows
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
