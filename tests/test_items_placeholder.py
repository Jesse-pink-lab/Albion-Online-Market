import sys, pathlib, types
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from services.market_prices import fetch_prices


class DummyResp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or []
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("error")
    def json(self):
        return self._data


def test_empty_items_fetch_all(monkeypatch):
    calls = []
    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return DummyResp(200, [])
    session = types.SimpleNamespace(get=fake_get)
    monkeypatch.setattr('services.market_prices.items_catalog_codes', lambda: ['A','B'])
    rows = fetch_prices('europe', '', '', '', session=session, fetch_all=True)
    assert calls and rows == []


def test_empty_items_no_fetch(monkeypatch):
    calls = []
    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return DummyResp(200, [])
    session = types.SimpleNamespace(get=fake_get)
    rows = fetch_prices('europe', '', '', '', session=session, fetch_all=False)
    assert rows == [] and calls == []

