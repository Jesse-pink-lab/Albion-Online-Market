"""Utility helpers for working with item identifiers.

The real application ships with a large catalogue of item codes inside
``recipes/items.txt``.  For the purposes of the tests we expose a very
small helper that can parse user input and optionally return the entire
catalogue when the input is empty and ``fetch_all`` is requested.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List


CATALOG_FILE = Path(__file__).resolve().parents[1] / "recipes" / "items.txt"


@lru_cache()
def load_catalog() -> List[str]:
    """Return the full item catalogue.

    The catalogue file is a simple list of item codes with comments
    beginning with ``#``.  The function is cached so that repeated calls
    are inexpensive.
    """

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


def parse_items(raw: str, fetch_all: bool = False) -> List[str]:
    """Parse comma separated ``raw`` string into item codes.

    Parameters
    ----------
    raw:
        Raw user input.  Items are separated by commas.  Whitespace is
        stripped and codes are upper-cased.  An empty string results in
        an empty list unless ``fetch_all`` is ``True``.
    fetch_all:
        When ``True`` and ``raw`` is empty, the complete catalogue is
        returned.
    """

    raw = (raw or "").strip()
    if raw:
        return [t.strip().upper() for t in raw.split(",") if t.strip()]
    if fetch_all:
        return list(load_catalog())
    return []


def items_catalog_codes() -> List[str]:
    """Return a list of all known item codes."""
    return list(load_catalog())


__all__ = ["parse_items", "load_catalog", "items_catalog_codes"]

