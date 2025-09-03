import requests
_session = None

def get_shared_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": "AlbionTradeOptimizer/1.0"})
    return _session
