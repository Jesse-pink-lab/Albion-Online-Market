import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session_local = threading.local()

def _new_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=50, max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent": "AlbionTradeOptimizer/1.0 (+https://github.com/<repo>; contact: you@example.com)",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    })
    return s

def get_shared_session() -> requests.Session:
    s = getattr(_session_local, "session", None)
    if s is None:
        s = _new_session()
        _session_local.session = s
    return s
