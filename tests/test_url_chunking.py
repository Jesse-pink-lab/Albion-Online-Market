import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import types

from services.market_prices import _chunk_by_len_and_count, _estimate_url_len, fetch_prices, chunk_by_url, MAX_URL_LEN

class DummyResp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or []
    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code not in (414, 429):
            raise Exception("error")
    def json(self):
        return self._data


def test_chunk_by_len_and_count_respects_url():
    base = "https://example.com"
    cities_csv = "Caerleon"
    quals_csv = "1"
    items = ["X" * 500, "Y" * 500]
    chunks = _chunk_by_len_and_count(items, base, cities_csv, quals_csv, 10, max_url=1000)
    assert all(_estimate_url_len(base, c, cities_csv, quals_csv) <= 1000 for c in chunks)


def test_chunk_by_url_uses_constant():
    base = "https://example.com"
    cities = ["Caerleon"]
    quals = [1]
    items = [f"ITEM{i}" for i in range(100)]
    chunks = list(chunk_by_url(items, base, cities, quals))
    cities_csv = ",".join(cities)
    quals_csv = ",".join(map(str, quals))
    assert all(
        _estimate_url_len(base, c, cities_csv, quals_csv) <= MAX_URL_LEN
        for c in chunks
    )


def test_auto_split_on_414(monkeypatch):
    responses = [
        DummyResp(414),
        DummyResp(200, [{"item_id": "A", "city": "Caerleon", "sell_price_min": 1, "buy_price_max": 1}]),
        DummyResp(200, [{"item_id": "B", "city": "Caerleon", "sell_price_min": 2, "buy_price_max": 1}]),
    ]
    def fake_get(url, params=None, timeout=None):
        return responses.pop(0)
    session = types.SimpleNamespace(get=fake_get)
    settings = types.SimpleNamespace(fetch_all_items=False)
    rows = fetch_prices("europe", "A,B", "Caerleon", "1", session=session, settings=settings)
    assert {r["item_id"] for r in rows} == {"A", "B"}
