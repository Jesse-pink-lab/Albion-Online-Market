import os, sys, pathlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone

from services.flip_engine import compute_flips


def test_flip_uses_buy_max_and_sell_min():
    rows = [
        {
            "item_id": "T4_SWORD",
            "city": "Martlock",
            "quality": 1,
            "buy_price_max": 100,
            "sell_price_min": 120,
            "updated_dt": datetime.now(timezone.utc),
        },
        {
            "item_id": "T4_SWORD",
            "city": "Lymhurst",
            "quality": 1,
            "buy_price_max": 90,
            "sell_price_min": 160,
            "updated_dt": datetime.now(timezone.utc),
        },
    ]
    flips = compute_flips(rows, cities=["Martlock", "Lymhurst"], qualities=[1], max_results=5, max_age_hours=24)
    assert flips
    best = flips[0]
    assert best["buy_city"] == "Martlock"
    assert best["sell_city"] == "Lymhurst"
    assert best["buy"] == 100
    assert best["sell"] == 160
    assert best["spread"] == 60
