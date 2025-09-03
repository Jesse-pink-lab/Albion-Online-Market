import os, sys, pathlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone, timedelta
import pytest
try:  # pragma: no cover - handled in test
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover
    pytest.skip("PySide6 not available", allow_module_level=True)

from services.market_prices import normalize_and_dedupe
from gui.widgets.market_prices import MarketPricesWidget
from utils.timefmt import rel_age, fmt_tooltip
from utils.constants import MAX_DATA_AGE_HOURS


class DummyMain:
    def set_status(self, msg):
        pass
    def set_refresh_enabled(self, flag):
        pass


def test_dedupe_and_freshness():
    now = datetime.now(timezone.utc)
    records = [
        {
            "item_id": "T4_BAG",
            "city": "Lymhurst",
            "quality": 1,
            "sell_price_min": 150,
            "sell_price_min_date": (now - timedelta(hours=2)).isoformat(),
            "buy_price_max": 100,
            "buy_price_max_date": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "item_id": "T4_BAG",
            "city": "Lymhurst",
            "quality": 1,
            "sell_price_min": 140,
            "sell_price_min_date": (now - timedelta(hours=1)).isoformat(),
            "buy_price_max": 110,
            "buy_price_max_date": (now - timedelta(hours=1)).isoformat(),
        },
        {
            "item_id": "T4_SWORD",
            "city": "Martlock",
            "quality": 1,
            "sell_price_min": 200,
            "sell_price_min_date": (now - timedelta(hours=MAX_DATA_AGE_HOURS + 1)).isoformat(),
            "buy_price_max": 180,
            "buy_price_max_date": (now - timedelta(hours=MAX_DATA_AGE_HOURS + 1)).isoformat(),
        },
    ]
    norm = normalize_and_dedupe(records)
    assert len(norm) == 1  # stale row dropped and duplicates collapsed
    row = norm[0]
    assert row["buy_price_max"] == 110
    assert row["sell_price_min"] == 140
    assert row["spread"] == 30
    assert round(row["roi_pct"], 2) == round(30 / 110 * 100, 2)
    assert row["updated_human"] == rel_age(row["updated_dt"])

    app = QApplication.instance() or QApplication([])
    widget = MarketPricesWidget(DummyMain())
    widget.rows = norm
    widget.populate_table()
    cell = widget.table.item(0, 6)  # Updated column
    dt = row["updated_dt"]
    assert cell.text() == rel_age(dt)
    assert cell.toolTip() == fmt_tooltip(dt)


def test_aggregate_prices_basic():
    import pandas as pd
    from services.market_prices import aggregate_prices

    df = pd.DataFrame([
        {
            "item_id": "T4_SWORD",
            "city": "Martlock",
            "quality": 1,
            "sell_price_min": 10000,
            "buy_price_max": 9000,
            "updated_dt": pd.Timestamp("2025-01-01"),
        },
        {
            "item_id": "T4_SWORD",
            "city": "Martlock",
            "quality": 1,
            "sell_price_min": 9900,
            "buy_price_max": 9200,
            "updated_dt": pd.Timestamp("2025-01-02"),
        },
    ])

    out = aggregate_prices(df)
    r = out.iloc[0]
    assert r.sell_min == 9900
    assert r.buy_max == 9200
    assert r.spread == 700
    assert 0.07 - 1e-6 <= r.roi <= 0.07 + 1e-6

