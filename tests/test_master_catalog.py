import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import io
import json
import types

from utils import catalog_provider as cp
from services import market_prices as mp
from engine.config import ConfigManager


def test_catalog_provider_downloads_and_caches(tmp_path, monkeypatch):
    """ensure_master_catalog downloads and caches the master list"""

    # Prepare fake HTTP response with many unique items
    rows = [{"UniqueName": f"T4_ITEM_{i}"} for i in range(1500)]

    def fake_urlopen(url, timeout=20):
        return io.StringIO(json.dumps(rows))

    monkeypatch.setattr(cp.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(cp, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(cp, "CACHE_PATH", str(tmp_path / "items_master.json"))

    ids = cp.ensure_master_catalog(cache_ttl_sec=0)
    assert len(ids) > 1000
    assert (tmp_path / "items_master.json").exists()


def test_fetch_prices_uses_catalog_when_empty_and_fetch_all_true(monkeypatch):
    catalog = ["A", "B", "C"]
    monkeypatch.setattr(mp, "items_catalog_codes", lambda: catalog)

    captured = {}

    def fake_build_prices_request(base, item_ids, cities, quals):
        captured["count"] = len(item_ids)
        return "http://example", {}

    monkeypatch.setattr(mp, "build_prices_request", fake_build_prices_request)

    def fake_get(url, params=None, timeout=None):
        class R:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return []

        return R()

    session = types.SimpleNamespace(get=fake_get)

    # With fetch_all True we should request all catalog items
    mp.fetch_prices("europe", "", "", "", session=session, fetch_all=True)
    assert captured["count"] == len(catalog)

    # When fetch_all is False there should be no request
    captured.clear()
    mp.fetch_prices("europe", "", "", "", session=session, fetch_all=False)
    assert captured == {}


def test_settings_default_fetch_all_true():
    cfg = ConfigManager().get_default_config()
    assert cfg.get("fetch_all_items") is True

