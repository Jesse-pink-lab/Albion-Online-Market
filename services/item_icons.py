from __future__ import annotations

from typing import Optional

from datasources.http import get_shared_session
from services.http_cache import cache_get, cache_set

_ICON_TTL = 24 * 3600.0  # 24h


def _icon_url(item_id: str, quality: int = 1) -> str:
    return f"https://render.albiononline.com/v1/item/{item_id}.png?quality={quality}"


def fetch_icon_bytes(item_id: str, quality: int = 1) -> Optional[bytes]:
    key = f"icon:{item_id}:{quality}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    url = _icon_url(item_id, quality)
    s = get_shared_session()
    r = s.get(url, timeout=15)
    r.raise_for_status()
    data = r.content
    cache_set(key, data, ttl=_ICON_TTL)
    return data


__all__ = ["fetch_icon_bytes"]

