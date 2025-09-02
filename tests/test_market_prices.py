import requests
from datetime import datetime
import sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from services.market_prices import build_icon_url, fetch_prices


def test_build_icon_url():
    url = build_icon_url("T4_BAG", 2, 32)
    assert url == "https://render.albiononline.com/v1/item/T4_BAG.png?quality=2&size=32"


def test_fetch_prices_parses_and_summarises(monkeypatch):
    sample = [
        {
            "item_id": "T4_BAG",
            "city": "Bridgewatch",
            "quality": 1,
            "sell_price_min": 1000,
            "sell_price_max": 1500,
            "buy_price_min": 800,
            "buy_price_max": 900,
            "sell_price_min_date": "2024-01-01T10:00:00",
            "buy_price_max_date": "2024-01-01T10:05:00",
        },
        {
            "item_id": "T4_BAG",
            "city": "Martlock",
            "quality": 1,
            "sell_price_min": 950,
            "sell_price_max": 1400,
            "buy_price_min": 850,
            "buy_price_max": 950,
            "sell_price_min_date": "2024-01-02T12:00:00",
            "buy_price_max_date": "2024-01-02T12:05:00",
        },
    ]

    class MockResponse:
        def __init__(self, data):
            self._data = data
            self.status_code = 200

        def json(self):
            return self._data

        def raise_for_status(self):
            pass

    def mock_get(url, params=None, timeout=30):
        return MockResponse(sample)

    monkeypatch.setattr(requests, "get", mock_get)

    rows, summary = fetch_prices(["T4_BAG"], ["Bridgewatch", "Martlock"])
    assert len(rows) == 2
    for row in rows:
        assert isinstance(row["sell_min"], (int, float))
        assert isinstance(row["buy_max"], (int, float))
        # Ensure datetime can be parsed
        datetime.fromisoformat(row["last_update_buy"].replace("Z", "+00:00"))
        assert row["icon_url"].startswith(
            "https://render.albiononline.com/v1/item/T4_BAG"
        )

    info = summary["T4_BAG"]
    assert info["sell_price_min"]["city"] == "Martlock"
    assert info["buy_price_max"]["city"] == "Martlock"
    assert info["spread"] == 0
    assert info["roi_percent"] == 0
