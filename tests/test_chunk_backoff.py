import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import types

from services.market_prices import fetch_prices


class DummyResp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or []

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 429:
            raise Exception("error")

    def json(self):
        return self._data


def test_backoff_and_merge(monkeypatch):
    responses = [
        DummyResp(429),
        DummyResp(200, [
            {"item_id": "A", "city": "Caerleon", "sell_price_min": 10, "buy_price_max": 5},
            {"item_id": "B", "city": "Caerleon", "sell_price_min": 12, "buy_price_max": 6},
        ]),
    ]

    def fake_get(url, params=None, timeout=None):
        return responses.pop(0)

    session = types.SimpleNamespace(get=fake_get)
    settings = types.SimpleNamespace(fetch_all_items=False)
    rows = fetch_prices("europe", "A,B", ["Caerleon"], "1", session, settings)
    assert {r["item_id"] for r in rows} == {"A", "B"}

