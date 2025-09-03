import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from services.market_prices import build_prices_url


def test_url_builder_basic():
    url = build_prices_url("west", ["T4_BAG"], ["Caerleon"], [1, 2])
    assert url.startswith("https://west.albion-online-data.com/api/v2/stats/prices/T4_BAG.json")
    assert "locations=Caerleon" in url
    assert "qualities=1,2" in url
    assert "/api/v2/stats/prices/" in url.lower()
