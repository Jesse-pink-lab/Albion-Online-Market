import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import types

from services.market_prices import fetch_prices


def test_no_items_short_circuit():
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return None

    session = types.SimpleNamespace(get=fake_get)
    settings = types.SimpleNamespace(fetch_all_items=False)
    rows = fetch_prices("europe", "", None, None, session=session, settings=settings, fetch_all=False)
    assert rows == []
    assert calls == []

