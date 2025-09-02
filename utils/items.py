"""Utility helpers for item handling."""

from typing import Iterable, List, Optional


def parse_items_input(raw: str, fetch_all: bool = False, all_items: Optional[Iterable[str]] = None) -> List[str]:
    raw = raw.strip()
    items = [t.strip() for t in raw.split(',') if t.strip()] if raw else []
    if not items and fetch_all and all_items:
        return list(all_items)
    return items
