import threading
import time
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from services.http_cache import cache_set, cache_get, HTTP_CACHE_CAPACITY


def test_http_cache_thread_safe_capacity():
    def worker(n):
        key = f"k{n}"
        cache_set(key, str(n).encode())
        cache_get(key)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(HTTP_CACHE_CAPACITY * 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    hits = sum(1 for i in range(HTTP_CACHE_CAPACITY * 2) if cache_get(f"k{i}") is not None)
    assert hits <= HTTP_CACHE_CAPACITY


def test_http_cache_ttl_expiry():
    cache_set("tmp", b"1", ttl=1.0)
    assert cache_get("tmp") == b"1"
    time.sleep(1.1)
    assert cache_get("tmp") is None
