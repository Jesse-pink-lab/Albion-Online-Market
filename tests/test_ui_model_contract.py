import os, sys, pathlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone, timedelta

from services.market_prices import normalize_and_dedupe
from utils.timefmt import rel_age


def test_rows_ready_for_ui():
    now = datetime.now(timezone.utc)
    raw = [
        {
            "item_id": "T4_BAG",
            "city": "Lymhurst",
            "quality": 1,
            "sell_price_min": 150,
            "sell_price_min_date": (now - timedelta(minutes=30)).isoformat(),
            "buy_price_max": 100,
            "buy_price_max_date": (now - timedelta(minutes=40)).isoformat(),
        }
    ]
    rows = normalize_and_dedupe(raw)
    assert len(rows) == 1
    r = rows[0]
    for key in (
        "buy_price_max",
        "sell_price_min",
        "spread",
        "roi_pct",
        "updated_dt",
        "updated_human",
    ):
        assert key in r
    assert r["spread"] == r["sell_price_min"] - r["buy_price_max"]
    expected_roi = 100 * r["spread"] / max(1, r["buy_price_max"])
    assert abs(r["roi_pct"] - expected_roi) < 0.01
    assert r["updated_human"] == rel_age(r["updated_dt"])
