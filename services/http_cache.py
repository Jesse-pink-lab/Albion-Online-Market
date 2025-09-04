from collections import OrderedDict
import threading
from typing import Optional

HTTP_CACHE_CAPACITY = 256

class _LRU:
    def __init__(self, capacity: int):
        self._cap = max(1, capacity)
        self._lock = threading.RLock()
        self._map: OrderedDict[str, bytes] = OrderedDict()

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            val = self._map.get(key)
            if val is None:
                return None
            self._map.move_to_end(key, last=True)
            return val

    def set(self, key: str, value: bytes) -> None:
        with self._lock:
            if key in self._map:
                self._map.move_to_end(key, last=True)
            self._map[key] = value
            while len(self._map) > self._cap:
                self._map.popitem(last=False)

_cache = _LRU(HTTP_CACHE_CAPACITY)

def cache_get(key: str) -> Optional[bytes]:
    return _cache.get(key)


def cache_set(key: str, value: bytes) -> None:
    _cache.set(key, value)
