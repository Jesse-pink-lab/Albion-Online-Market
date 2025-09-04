from __future__ import annotations

import time
from collections import OrderedDict
import threading
from typing import Optional, Tuple


HTTP_CACHE_CAPACITY = 256
HTTP_CACHE_DEFAULT_TTL = 900.0  # 15 minutes


class _LRU:
    def __init__(self, capacity: int, default_ttl: float):
        self._cap = max(1, capacity)
        self._ttl = max(1.0, default_ttl)
        self._lock = threading.RLock()
        # key -> (bytes_value, expires_at_monotonic)
        self._map: OrderedDict[str, Tuple[bytes, float]] = OrderedDict()

    def _purge_expired(self) -> None:
        now = time.monotonic()
        # Ordered oldest→newest; stop at first non-expired
        dead = [k for k, (_, exp) in self._map.items() if exp <= now]
        for k in dead:
            self._map.pop(k, None)

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            self._purge_expired()
            pair = self._map.get(key)
            if pair is None:
                return None
            val, exp = pair
            if exp <= time.monotonic():
                self._map.pop(key, None)
                return None
            self._map.move_to_end(key, last=True)
            return val

    def set(self, key: str, value: bytes, ttl: Optional[float] = None) -> None:
        ttl = self._ttl if ttl is None else max(1.0, ttl)
        expires_at = time.monotonic() + ttl
        with self._lock:
            self._purge_expired()
            if key in self._map:
                self._map.move_to_end(key, last=True)
            self._map[key] = (value, expires_at)
            while len(self._map) > self._cap:
                self._map.popitem(last=False)


_cache = _LRU(HTTP_CACHE_CAPACITY, HTTP_CACHE_DEFAULT_TTL)


def cache_get(key: str) -> Optional[bytes]:
    return _cache.get(key)


def cache_set(key: str, value: bytes, ttl: Optional[float] = None) -> None:
    _cache.set(key, value, ttl=ttl)

