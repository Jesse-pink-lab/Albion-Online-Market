import os, sys, pathlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
try:
    from gui.widgets.market_prices import MarketPricesWidget
except Exception:  # pragma: no cover
    pytest.skip("PySide6 not available", allow_module_level=True)


class DummyMain:
    def set_status(self, msg):
        pass

    def set_refresh_enabled(self, flag):
        pass


def test_single_flight(qtbot):
    widget = MarketPricesWidget(DummyMain())
    count = {"n": 0}

    def fake_start():
        count["n"] += 1
        widget.refresh_running = True
        widget.refresh_btn.setEnabled(False)

    widget.start_refresh = fake_start

    widget.on_refresh_clicked()
    assert count["n"] == 1
    assert widget.refresh_pending is False
    assert not widget.refresh_btn.isEnabled()

    widget.on_refresh_clicked()
    assert widget.refresh_pending is True

    widget._refresh_cleanup()  # completes first run, triggers queued
    assert count["n"] == 2

    widget._refresh_cleanup()  # completes second run
    assert widget.refresh_pending is False
    assert widget.refresh_btn.isEnabled()
