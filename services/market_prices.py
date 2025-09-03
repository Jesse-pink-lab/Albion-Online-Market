"""Market price fetching utilities with batching and backoff."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
from typing import List, Dict
import requests

from datasources.aodp import SESSION
from datasources.aodp_url import base_for, build_prices_request, DEFAULT_CITIES
from utils.params import qualities_to_csv, cities_to_list
from utils.items import parse_items, items_catalog_codes
from utils.timefmt import to_utc
from core.health import mark_online_on_data_success

log = logging.getLogger(__name__)

DEFAULT_QUALITIES = "1,2,3,4,5"  # include 5 (Masterpiece)


def fetch_prices(
    server: str,
    items_edit_text: str,
    cities_sel,
    qual_sel,
    session: requests.Session = SESSION,
    settings=None,
    on_progress=None,
    cancel=lambda: False,
) -> List[Dict]:
    """Fetch raw price rows from AODP with chunking and backoff."""

    # 1) Items
    typed = parse_items(items_edit_text)
    items = (
        list(items_catalog_codes())
        if (not typed and getattr(settings, "fetch_all_items", False))
        else typed
    )
    if not items:
        log.info(
            "No items to request (typed=%d, fetch_all=%s).",
            len(typed),
            getattr(settings, "fetch_all_items", False),
        )
        return []

    # 2) Cities / qualities
    cities = cities_to_list(cities_sel, DEFAULT_CITIES)
    quals_csv = qualities_to_csv(qual_sel)

    # 3) Chunking
    chunk_size, max_workers = 150, 4
    chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]

    base = base_for(server)
    results: List[Dict] = []
    total = len(chunks)

    def pull(chunk, attempt=1):
        url, params = build_prices_request(base, chunk, cities, quals_csv)
        log.info(
            "AODP GET: base=%s items=%d cities=%d quals=%s attempt=%d",
            base,
            len(chunk),
            len(cities),
            quals_csv,
            attempt,
        )
        log.debug("AODP URL: %s params=%s", url, params)
        r = session.get(url, params=params, timeout=(5, 10))
        if r.status_code in (429, 500, 502, 503, 504):
            if attempt <= 4:
                delay = 0.5 * (2 ** (attempt - 1))
                time.sleep(delay)
                return pull(chunk, attempt + 1)
        r.raise_for_status()
        data = r.json() or []
        log.info("AODP RESP: status=%s records=%d", r.status_code, len(data))
        return data

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(pull, c) for c in chunks]
        for idx, fut in enumerate(as_completed(futs), 1):
            if cancel():
                break
            results.extend(fut.result())
            if on_progress:
                on_progress(int(idx / total * 100), f"Fetched {idx}/{total} chunks")

    if results:
        mark_online_on_data_success()
    return results


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
            try:
                return to_utc(d)
            except Exception:
                return None

        sell_dt = ts(row.get("sell_price_min_date"))
        buy_dt = ts(row.get("buy_price_max_date"))
        best_dt = sell_dt or buy_dt

        prev = out.get(key)
        if (not prev) or (best_dt and prev.get("updated_dt") and best_dt > prev["updated_dt"]):
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
                "updated_dt": best_dt or to_utc("1970-01-01T00:00:00Z"),
            }
    return list(out.values())


__all__ = ["fetch_prices", "normalize_and_dedupe", "DEFAULT_CITIES", "DEFAULT_QUALITIES"]
