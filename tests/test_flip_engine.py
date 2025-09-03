import builtins

from datetime import datetime, timedelta, timezone

from services.flip_engine import compute_flips


def _sample_rows():
    now = datetime.now(timezone.utc)
    return [
        {
            "item_id": "T4_SWORD",
            "city": "Martlock",
            "quality": 1,
            "buy_price_max": 100,
            "sell_price_min": 0,
            "updated_dt": (now - timedelta(minutes=5)).isoformat(),
        },
        {
            "item_id": "T4_SWORD",
            "city": "Lymhurst",
            "quality": 1,
            "buy_price_max": 0,
            "sell_price_min": 150,
            "updated_dt": (now - timedelta(minutes=3)).isoformat(),
        },
    ]


def test_compute_flips_basic():
    rows = _sample_rows()
    flips = compute_flips(rows, cities=["Martlock", "Lymhurst"], qualities=[1], max_age_hours=24)
    assert flips
    flip = flips[0]
    assert flip["item"] == "T4_SWORD"
    assert flip["buy_city"] == "Martlock"
    assert flip["sell_city"] == "Lymhurst"
    assert flip["spread"] == 50
    assert round(flip["roi_pct"], 2) == 50.0


def test_compute_flips_fallback(monkeypatch):
    rows = _sample_rows()
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("no pandas")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    flips = compute_flips(rows, cities=["Martlock", "Lymhurst"], qualities=[1], max_age_hours=24)
    assert flips
    assert flips[0]["spread"] == 50
