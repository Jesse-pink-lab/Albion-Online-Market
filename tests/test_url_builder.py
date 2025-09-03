import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datasources.aodp_url import base_for, build_prices_request


def test_url_builder_basic():
    base = base_for("west")
    url, params = build_prices_request(base, ["T4_BAG"], ["Caerleon"], "1,2")
    assert url == "https://west.albion-online-data.com/api/v2/stats/prices/T4_BAG.json"
    assert params["locations"] == "Caerleon"
    assert params["qualities"] == "1,2"
    assert "/api/v2/stats/prices/" in url.lower()
    assert "?" not in url

