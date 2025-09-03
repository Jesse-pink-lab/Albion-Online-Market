"""Download and cache the master list of Albion Online items.

This module fetches the official item catalogue from the Albion Online Data
Project (AODP) repository.  The heavy lifting is done once every 24 hours and
the results are cached locally under ``data/items_master.json``.  Only items
that are marketable are kept – internal placeholders, quest items and test
entries are filtered out.

The catalogue is used throughout the application whenever a complete list of
items is required.  Access through :func:`read_master_catalog` to avoid
accidental refreshes during runtime.
"""

from __future__ import annotations

import json
import os
import time
import re
from typing import Iterable
import urllib.request

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AODP_ITEMS_JSON = (
    "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/formatted/items.json"
)

CACHE_DIR = os.path.join("data")
CACHE_PATH = os.path.join(CACHE_DIR, "items_master.json")
CACHE_TTL_SEC = 24 * 3600  # 24h


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def _should_refresh(path: str, ttl: int) -> bool:
    """Return ``True`` if the cache at ``path`` is stale or missing."""

    try:
        st = os.stat(path)
        return (_now() - st.st_mtime) > ttl
    except FileNotFoundError:
        return True


def _download_items() -> list[dict]:
    """Download the full AODP items list."""

    with urllib.request.urlopen(AODP_ITEMS_JSON, timeout=20) as resp:
        return json.load(resp)


def _filter_marketable(rows: list[dict]) -> list[str]:
    """Filter out non marketable items and return a list of item IDs."""

    ids: list[str] = []
    for r in rows:
        uid = r.get("UniqueName") or ""
        if not uid:
            continue
        u = uid.strip().upper()
        # Exclusions: tests, unused, quest, internal placeholders
        if any(tag in u for tag in ("TEST", "UNUSED", "QUESTITEM", "DUMMY")):
            continue
        ids.append(u)

    # de-dupe while keeping order
    seen: set[str] = set()
    out: list[str] = []
    for u in ids:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_master_catalog(cache_ttl_sec: int = CACHE_TTL_SEC) -> list[str]:
    """Ensure the master catalogue exists locally and return the IDs.

    The catalogue is refreshed if it is missing or older than ``cache_ttl_sec``
    seconds.  The caller receives the fresh list of item identifiers.
    """

    os.makedirs(CACHE_DIR, exist_ok=True)
    if _should_refresh(CACHE_PATH, cache_ttl_sec):
        rows = _download_items()
        ids = _filter_marketable(rows)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(ids, f)
        return ids

    # load existing cache
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def read_master_catalog() -> list[str]:
    """Read the cached catalogue without refreshing it."""

    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return ensure_master_catalog()


__all__ = ["ensure_master_catalog", "read_master_catalog"]

