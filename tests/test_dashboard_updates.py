import os, sys, pathlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime
import pytest
try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover
    pytest.skip("PySide6 not available", allow_module_level=True)

from core.signals import signals
from gui.widgets.dashboard import DashboardWidget
from utils.timefmt import now_utc_iso


def test_dashboard_updates():
    app = QApplication.instance() or QApplication([])
    w = DashboardWidget()
    assert w.lblLastUpdate.text() == "Loading…"

    updates: list[dict] = []
    signals.market_data_ready.connect(lambda s: updates.append(s))

    dt = datetime.utcnow()
    summary = {
        "last_update_utc": now_utc_iso(),
        "records": 5,
        "top_opportunities": [
            {
                "item": "T4_BAG",
                "buy_city": "Lymhurst",
                "buy_price": 100,
                "sell_city": "Martlock",
                "sell_price": 150,
                "spread": 50,
                "roi_pct": 50.0,
                "updated_dt": dt,
            }
        ],
    }
    signals.market_data_ready.emit(summary)
    app.processEvents()

    assert len(updates) == 1
    assert w.lblRecords.text() == "5"
    assert w.topTable.rowCount() == 1
    assert w.lblLastUpdate.text().endswith("ago")

    from gui.widgets.market_prices import MarketPricesWidget

    class DummyMain:
        def set_status(self, msg):
            pass

        def set_refresh_enabled(self, flag):
            pass

    mpw = MarketPricesWidget(DummyMain())
    mpw.on_refresh_done({"elapsed": 0, "result": {"items": 0, "records": 0}})
    app.processEvents()

    assert len(updates) == 1
