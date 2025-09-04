import os, sys, pathlib
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

flip_finder = pytest.importorskip("gui.widgets.flip_finder")
FlipFinderWorker = flip_finder.FlipFinderWorker
from services.market_prices import STORE


def test_trimmed_rows_and_roi_conversion(monkeypatch):
    STORE.clear()
    STORE._latest_rows = [
        {
            "item_id": "T4_SWORD",
            "city": "Martlock",
            "quality": 1,
            "buy_price_max": 100,
            "sell_price_min": 200,
            "updated_epoch_hours": 1.0,
            "item_name": "Sword",
        }
    ]

    captured = {}

    def fake_build_flips(*, rows, items_filter, src_cities, dst_cities, qualities, min_profit, min_roi, max_age_hours, max_results):
        captured["rows"] = rows
        captured["min_roi"] = min_roi
        return [], {}

    monkeypatch.setattr(flip_finder, "build_flips", fake_build_flips)

    params = {
        "src_cities": ["Martlock"],
        "dst_cities": ["Lymhurst"],
        "items": None,
        "qualities": None,
        "min_profit": 0,
        "min_roi": 5.0,
        "max_age_hours": 24,
        "max_results": 100,
    }

    worker = FlipFinderWorker(params)
    worker.progress.emit = lambda *a, **k: None
    worker.finished.emit = lambda *a, **k: None
    worker.error.emit = lambda *a, **k: None
    worker.run()

    rows = captured["rows"]
    assert rows and rows[0]["buy"] == 100 and rows[0]["sell"] == 200
    assert captured["min_roi"] == 0.05
