"""Utility helpers for working with item identifiers.

The real application ships with a large catalogue of item codes inside
``recipes/items.txt``.  For the purposes of the tests we expose a very
small helper that can parse user input and return the entire catalogue
when requested separately.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from utils.catalog_provider import read_master_catalog

CATALOG_FILE = Path(__file__).resolve().parents[1] / "recipes" / "items.txt"

@lru_cache()
def load_catalog() -> List[str]:
    """Return the full item catalogue.

    Legacy helper retained for compatibility; now delegates to the cached
    master list when available.
    """

    try:
        return list(read_master_catalog())
    except Exception:
        # Fallback to tiny embedded list if master catalogue isn't available.
        items: List[str] = []
        try:
            with CATALOG_FILE.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        items.append(line)
        except FileNotFoundError:  # pragma: no cover - defensive
            pass
        return items

def parse_items(raw: str | None) -> List[str]:
    """Parse comma separated ``raw`` string into UPPERCASE item codes."""
    raw = (raw or "").strip()
    return [t.strip().upper() for t in raw.split(",") if t.strip()]

def items_catalog_codes() -> List[str]:
    """Return the filtered master list of Albion item IDs.

    The identifiers are upper-case strings like ``T4_SWORD``.  The list is
    cached on disk and refreshed automatically by :mod:`utils.catalog_provider`.
    """

    return list(read_master_catalog())

__all__ = ["parse_items", "load_catalog", "items_catalog_codes"]
