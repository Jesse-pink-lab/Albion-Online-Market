from datetime import datetime, timedelta, timezone

from services.flip_engine import compute_flips
from utils.constants import MAX_DATA_AGE_HOURS


def _sample_rows():
    now = datetime.now(timezone.utc)
    return [
        {
            "item_id": "T4_SWORD",
            "item_name": "T4 Sword",
            "city": "Martlock",
            "quality": 1,
            "buy_price_max": 100,
            "sell_price_min": 0,
            "updated_dt": now - timedelta(minutes=5),
            "updated_human": "5m",
        },
        {
            "item_id": "T4_SWORD",
            "item_name": "T4 Sword",
            "city": "Lymhurst",
            "quality": 1,
            "buy_price_max": 0,
            "sell_price_min": 150,
            "updated_dt": now - timedelta(minutes=3),
            "updated_human": "3m",
        },
    ]


def test_compute_flips_basic():
    rows = _sample_rows()
    flips = compute_flips(rows, cities=["Martlock", "Lymhurst"], qualities=[1], max_age_hours=24)
    assert flips
    flip = flips[0]
    assert flip["item_id"] == "T4_SWORD"
    assert flip["from"] == "Martlock"
    assert flip["to"] == "Lymhurst"
    assert flip["buy"] == 100
    assert flip["sell"] == 150
    assert flip["spread"] == 50
    assert round(flip["roi_pct"], 2) == 50.0


def test_compute_flips_stale_dropped():
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=MAX_DATA_AGE_HOURS + 1)
    rows = [
        {
            "item_id": "T4_SWORD",
            "item_name": "T4 Sword",
            "city": "Martlock",
            "quality": 1,
            "buy_price_max": 100,
            "sell_price_min": 0,
            "updated_dt": old,
            "updated_human": "old",
        },
        {
            "item_id": "T4_SWORD",
            "item_name": "T4 Sword",
            "city": "Lymhurst",
            "quality": 1,
            "buy_price_max": 0,
            "sell_price_min": 150,
            "updated_dt": now,
            "updated_human": "now",
        },
    ]
    flips = compute_flips(rows, cities=["Martlock", "Lymhurst"], qualities=[1])
    assert flips == []
