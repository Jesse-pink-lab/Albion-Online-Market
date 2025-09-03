"""Market price fetching utilities with batching and backoff.

This module provides a small wrapper around the Albion Online Data
Project API.  The real application performs far more work but for the
tests we focus on request construction, basic error handling and the
normalisation of returned records.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import requests

from datasources.aodp import SESSION
from datasources.aodp_url import (
    base_for,
    build_prices_url as _build_prices_url,
    DEFAULT_CITIES,
)
from utils.timefmt import to_utc

logger = logging.getLogger(__name__)

# Default locations and qualities when the UI fields are empty
DEFAULT_QUALITIES = [1, 2, 3, 4]


def build_prices_url(
    server: str,
    items: Iterable[str],
    locations: Iterable[str],
    qualities: Iterable[int],
) -> str:
    """Construct the prices endpoint URL for the given arguments."""

    base = base_for(server)
    items_str = ",".join(items)
    locs = ",".join(locations)
    quals = ",".join(str(q) for q in qualities)
    return _build_prices_url(base, items_str, locs, quals)


def _fetch_chunk(url: str, session: requests.Session) -> List[Dict[str, object]]:
    """Fetch a single chunk with exponential backoff."""

    delays = [0.5, 1, 2, 4]
    for attempt, delay in enumerate(delays, start=1):
        logger.debug("Fetching %s attempt=%s", url, attempt)
        resp = session.get(url, timeout=(5, 10))
        if resp.status_code in {429} or resp.status_code >= 500:
            logger.warning("AODP backoff: attempt=%d status=%s", attempt, resp.status_code)
            if attempt == len(delays):
                logger.info("AODP RESP: status=%s records=%d", resp.status_code, 0)
                resp.raise_for_status()
            time.sleep(delay)
            continue
        resp.raise_for_status()
        data = resp.json()
        logger.info("AODP RESP: status=%s records=%d", resp.status_code, len(data))
        return data
    return []  # pragma: no cover - should never reach


def fetch_prices(
    item_ids: Iterable[str],
    locations: Optional[Iterable[str]] = None,
    qualities: Optional[Iterable[int]] = None,
    server: str = "europe",
    chunk_size: int = 150,
    session: requests.Session = SESSION,
) -> List[Dict[str, object]]:
    """Fetch and normalise market prices.

    The function handles chunking and merges the results into a per item
    summary consisting of the best bid/ask information as well as simple
    spread/ROI calculations.
    """

    items = list(item_ids)
    if not items:
        return []

    locs = list(locations) if locations else list(DEFAULT_CITIES)
    quals = list(qualities) if qualities else list(DEFAULT_QUALITIES)

    base = base_for(server)
    quals_csv = ",".join(str(q) for q in quals)

    raw_records: List[Dict[str, object]] = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i : i + chunk_size]
        items_csv = ",".join(chunk)
        cities_csv = ",".join(locs)
        url = _build_prices_url(base, items_csv, cities_csv, quals_csv)
        logger.info(
            "AODP GET: base=%s items=%d cities=%d quals=%s",
            base,
            len(chunk),
            len(locs),
            quals_csv,
        )
        logger.debug("AODP URL: %s", url)
        data = _fetch_chunk(url, session)
        raw_records.extend(data)

    return [normalize_item(item_id, recs) for item_id, recs in _group_by_item(raw_records).items()]


def _group_by_item(records: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    grouped: Dict[str, List[Dict[str, object]]] = {}
    for rec in records:
        grouped.setdefault(rec.get("item_id"), []).append(rec)
    return grouped


@dataclass
class Normalized:
    item_id: str
    buy_price_max: Optional[int]
    buy_city: Optional[str]
    buy_date: Optional[object]
    sell_price_min: Optional[int]
    sell_city: Optional[str]
    sell_date: Optional[object]
    spread: Optional[int]
    roi_pct: Optional[float]


def normalize_item(item_id: str, records: List[Dict[str, object]]) -> Dict[str, object]:
    """Normalise API records for a single item."""

    best_buy = {"price": None, "city": None, "date": None}
    best_sell = {"price": None, "city": None, "date": None}

    for rec in records:
        buy = rec.get("buy_price_max")
        sell = rec.get("sell_price_min")
        city = rec.get("city")
        buy_date = rec.get("buy_price_max_date")
        sell_date = rec.get("sell_price_min_date")

        if buy is not None and (best_buy["price"] is None or buy > best_buy["price"]):
            best_buy = {
                "price": buy,
                "city": city,
                "date": to_utc(buy_date) if buy_date else None,
            }
        if sell is not None and (best_sell["price"] is None or sell < best_sell["price"]):
            best_sell = {
                "price": sell,
                "city": city,
                "date": to_utc(sell_date) if sell_date else None,
            }

    spread = None
    roi = None
    if best_buy["price"] is not None and best_sell["price"] is not None:
        spread = best_sell["price"] - best_buy["price"]
        if best_buy["price"]:
            roi = (spread / best_buy["price"]) * 100

    return {
        "item_id": item_id,
        "buy_price_max": best_buy["price"],
        "buy_city": best_buy["city"],
        "buy_date": best_buy["date"],
        "sell_price_min": best_sell["price"],
        "sell_city": best_sell["city"],
        "sell_date": best_sell["date"],
        "spread": spread,
        "roi_pct": roi,
    }


__all__ = [
    "fetch_prices",
    "build_prices_url",
    "normalize_item",
    "DEFAULT_CITIES",
    "DEFAULT_QUALITIES",
]

