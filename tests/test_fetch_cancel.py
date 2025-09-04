import types
import types
import time
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from services import market_prices as mp


class DummyResp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or []

    def json(self):
        return self._data


def test_fetch_prices_cancel(monkeypatch):
    # Prepare session that records calls
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        time.sleep(0.01)
        return DummyResp(200, [])

    session = types.SimpleNamespace(get=fake_get)
    settings = types.SimpleNamespace(fetch_all_items=False)

    monkeypatch.setattr(mp, "chunk_by_url", lambda items, base, cities, qualities, max_url=None: [["A"], ["B"], ["C"], ["D"]])

    def cancel():
        return len(calls) >= 1

    rows = mp.fetch_prices("europe", "A,B,C,D", "Caerleon", "1", session=session, settings=settings, cancel=cancel)
    assert rows == []
    assert len(calls) < 4
