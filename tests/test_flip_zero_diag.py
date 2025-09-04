import time

from services.flip_engine import build_flips


def test_zero_relaxed_fallback():
    now_h = time.time() / 3600.0
    rows = [
        {
            "item_id": "T4_SWORD",
            "item_name": "T4 Sword",
            "city": "Martlock",
            "quality": 1,
            "buy_price_max": 100,
            "sell_price_min": 0,
            "updated_epoch_hours": now_h - 100,
        },
        {
            "item_id": "T4_SWORD",
            "item_name": "T4 Sword",
            "city": "Lymhurst",
            "quality": 1,
            "buy_price_max": 0,
            "sell_price_min": 160,
            "updated_epoch_hours": now_h - 1,
        },
    ]

    tiers = [
        {"tag": "strict", "min_profit": 50, "min_roi": 0.5, "max_age": 24, "items": {"T4_SWORD"}},
        {"tag": "relaxed-1", "min_profit": 1, "min_roi": 0.10, "max_age": 168, "items": {"T4_SWORD"}},
    ]

    src = {"Martlock"}
    dst = {"Lymhurst"}

    chosen_tag = None
    flips = []
    stats = {}
    all_stats = []
    for tier in tiers:
        flips, stats = build_flips(
            rows=rows,
            items_filter=tier["items"],
            src_cities=src,
            dst_cities=dst,
            qualities=[1],
            min_profit=tier["min_profit"],
            min_roi=tier["min_roi"],
            max_age_hours=tier["max_age"],
            max_results=10,
        )
        if flips:
            chosen_tag = tier["tag"]
            break
        all_stats.append((tier["tag"], stats, 0))

    assert chosen_tag == "relaxed-1"
    assert all(f["spread"] > 0 and f["roi"] > 0 for f in flips)
    strict_stats = all_stats[0][1]
    assert strict_stats.get("no_buy", 0) > 0 or strict_stats.get("stale", 0) > 0

