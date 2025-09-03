import time
from typing import Optional, Tuple, Dict

_cache: Dict[str, Tuple[float, bytes, int, dict]] = {}

def get_cached(url: str) -> Optional[Tuple[bytes, int, dict]]:
    now = time.time()
    hit = _cache.get(url)
    if hit and hit[0] > now:
        return hit[1], hit[2], hit[3]
    return None

def put_cached(url: str, body: bytes, status: int, headers: dict, ttl: int = 120) -> None:
    _cache[url] = (time.time() + ttl, body, status, headers)
