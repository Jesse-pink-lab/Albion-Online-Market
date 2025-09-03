"""Utility helper for loading and caching item icons."""

from __future__ import annotations

import os
import pathlib
from functools import lru_cache

import requests
from PySide6.QtGui import QIcon

from utils.constants import ICON_BASE


def _cache_dir() -> pathlib.Path:
    base = pathlib.Path(os.path.expanduser("~"))
    cache = base / ".albiontradeoptimizer" / "cache" / "icons"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


@lru_cache(maxsize=512)
def get_icon(item_dict: dict) -> QIcon:
    """Return a QIcon for ``item_dict``.

    This is a simplified helper used in tests; icons are cached on disk to
    avoid repeated downloads.  If the download fails, an empty icon is
    returned.
    """

    item_id = item_dict.get("item_id") or ""
    quality = int(item_dict.get("quality") or 1)
    url = ICON_BASE.format(id=item_id)
    url = f"{url}?quality={quality}"
    fname = _cache_dir() / f"{item_id}_{quality}.png"
    if not fname.exists():
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                fname.write_bytes(resp.content)
        except Exception:  # pragma: no cover - network errors ignored
            return QIcon()
    return QIcon(str(fname))


__all__ = ["get_icon"]
