"""Market price fetching utilities.

Provides helper functions for retrieving and normalising market
price information from the Albion Online Data API.  The core
entry point is :func:`fetch_prices` which returns a list of
normalised rows and a per-item summary describing the best place to
buy and sell.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

import requests

API_BASE = "https://www.albion-online-data.com/api/v2/stats"
RENDER_BASE = "https://render.albiononline.com/v1/item"

# minimum delay between requests to respect 180 req/min limit
_MIN_INTERVAL = 60.0 / 180.0
_last_request: float = 0.0


def _rate_limit() -> None:
    """Simple rate limiter to roughly respect the API limits.

    The Albion Online Data API allows 180 requests per minute.  We
    keep track of the time of the last request and sleep if required
    to maintain the minimum interval.  This is intentionally very
    small and lightweight as the application typically bundles
    multiple items and locations into a single request.
    """

    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request = time.time()


def build_icon_url(item_id: str, quality: int = 1, size: int = 64) -> str:
    """Return the URL to the rendered icon for ``item_id``.

    Parameters
    ----------
    item_id:
        The Albion item identifier, e.g. ``"T4_BAG"``.
    quality:
        Item quality (1-5).
    size:
        Icon size in pixels.  The API defaults to ``64`` so we mirror
        that behaviour here.
    """

    return f"{RENDER_BASE}/{item_id}.png?quality={quality}&size={size}"


def _parse_date(value: str | None) -> str | None:
    """Parse API timestamp into ISO8601 UTC string.

    The API sometimes omits the ``Z`` timezone designator; in that
    case we assume UTC.
    """

    if not value:
        return None
    try:
        if value.endswith("Z"):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(value)
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def fetch_prices(
    item_ids: Iterable[str],
    cities: Iterable[str],
    qualities: Iterable[int] | None = None,
    server: str = "europe",
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Fetch market prices for the given ``item_ids`` and ``cities``.

    Parameters
    ----------
    item_ids:
        Iterable of item identifiers.
    cities:
        Iterable of city names.
    qualities:
        Iterable of quality levels.  Defaults to ``[1]``.
    server:
        Game server region (``"europe"``, ``"asia"`` or ``"americas"``).

    Returns
    -------
    rows, summary
        ``rows`` is a list of dictionaries with normalised price
        information.  ``summary`` maps each item id to a dictionary
        describing the best place to buy (lowest ``sell_min``) and the
        best place to sell (highest ``buy_max``).
    """

    item_ids = list(item_ids)
    if not item_ids:
        return [], {}

    cities = list(cities)
    qualities = list(qualities) if qualities is not None else [1]

    items_str = ",".join(item_ids)
    params = {
        "locations": ",".join(cities),
        "qualities": ",".join(map(str, qualities)),
        "server": server,
    }

    url = f"{API_BASE}/prices/{items_str}.json"

    _rate_limit()
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    rows: List[Dict[str, Any]] = []
    summary: Dict[str, Dict[str, Any]] = {}

    for record in data:
        item_id = record.get("item_id")
        city = record.get("city")
        quality = record.get("quality", 1)
        sell_min = record.get("sell_price_min")
        sell_max = record.get("sell_price_max")
        buy_min = record.get("buy_price_min")
        buy_max = record.get("buy_price_max")
        last_sell = _parse_date(record.get("sell_price_min_date"))
        last_buy = _parse_date(record.get("buy_price_max_date"))
        icon_url = build_icon_url(item_id, quality)

        row = {
            "item_id": item_id,
            "city": city,
            "quality": quality,
            "sell_min": sell_min,
            "sell_max": sell_max,
            "buy_min": buy_min,
            "buy_max": buy_max,
            "last_update_sell": last_sell,
            "last_update_buy": last_buy,
            "icon_url": icon_url,
        }
        rows.append(row)

        # Update per-item summary
        item_summary = summary.setdefault(
            item_id,
            {
                "sell_price_min": {"city": None, "price": float("inf"), "date": None},
                "buy_price_max": {"city": None, "price": 0, "date": None},
            },
        )
        if (
            sell_min is not None
            and sell_min < item_summary["sell_price_min"]["price"]
        ):
            item_summary["sell_price_min"] = {
                "city": city,
                "price": sell_min,
                "date": last_sell,
            }
        if (
            buy_max is not None
            and buy_max > item_summary["buy_price_max"]["price"]
        ):
            item_summary["buy_price_max"] = {
                "city": city,
                "price": buy_max,
                "date": last_buy,
            }

    # Clean up and compute derived metrics
    for item_id, info in summary.items():
        if info["sell_price_min"]["price"] == float("inf"):
            info["sell_price_min"]["price"] = None
        if info["buy_price_max"]["price"] == 0:
            info["buy_price_max"]["price"] = None

        buy = info["sell_price_min"]["price"]
        sell = info["buy_price_max"]["price"]
        if buy is not None and sell is not None and buy > 0:
            spread = sell - buy
            roi = (spread / buy) * 100
        else:
            spread = None
            roi = None
        info["spread"] = spread
        info["roi_percent"] = roi

    return rows, summary


__all__ = ["fetch_prices", "build_icon_url"]
