import os, sys, pathlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone
import pytest
try:  # pragma: no cover - handled in test
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover
    pytest.skip("PySide6 not available", allow_module_level=True)

from services.market_prices import normalize_and_dedupe
from gui.widgets.market_prices import MarketPricesWidget
from utils.timefmt import rel_age, fmt_tooltip


class DummyMain:
    def set_status(self, msg):
        pass
    def set_refresh_enabled(self, flag):
        pass


def test_spread_roi_and_dates():
    records = [
        {
            "item_id": "T4_BAG",
            "city": "Lymhurst",
            "sell_price_min": 150,
            "sell_price_min_date": "2024-01-01T00:00:00Z",
            "buy_price_max": 100,
            "buy_price_max_date": "2024-01-01T00:00:00Z",
        },
        {
            "item_id": "T4_BAG",
            "city": "Martlock",
            "sell_price_min": 180,
            "sell_price_min_date": "2024-01-02T00:00:00Z",
            "buy_price_max": 120,
            "buy_price_max_date": "2024-01-02T00:00:00Z",
        },
    ]
    norm = normalize_and_dedupe(records)[0]
    assert norm["spread"] == max(norm["sell_price_min"] - norm["buy_price_max"], 0)
    expected_roi = (norm["spread"] / norm["buy_price_max"]) * 100 if norm["buy_price_max"] else 0
    assert abs(norm["roi_pct"] - expected_roi) < 0.01

    app = QApplication.instance() or QApplication([])
    widget = MarketPricesWidget(DummyMain())
    widget.rows = [norm]
    widget.populate_table()
    cell = widget.table.item(0, 7)  # Updated column
    dt = norm["updated_dt"]
    assert cell.text() == rel_age(dt)
    assert cell.toolTip() == fmt_tooltip(dt)

