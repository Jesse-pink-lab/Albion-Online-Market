import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtTest import QTest

from gui.widgets.market_prices import MarketPricesWidget
import gui.threads as threads
from PySide6.QtWidgets import QMessageBox


@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyMainWindow:
    def __init__(self):
        self.enabled = True
    def set_status(self, msg):
        pass
    def set_refresh_enabled(self, enabled: bool):
        self.enabled = enabled


def test_single_flight(app, monkeypatch):
    run_calls = []

    class DummyWorker(QObject):
        finished = Signal(dict)
        progress = Signal(int, str)
        error = Signal(str)

        def __init__(self, params):
            super().__init__()

        def run(self):
            run_calls.append(1)
            QTimer.singleShot(10, lambda: self.finished.emit({"ok": True, "elapsed": 0, "result": {}}))

    monkeypatch.setattr(threads, "RefreshWorker", DummyWorker)

    widget = MarketPricesWidget(DummyMainWindow())
    widget.on_refresh_clicked()
    assert not widget.refresh_btn.isEnabled()
    widget.on_refresh_clicked()  # should queue
    assert len(run_calls) == 1

    QTest.qWait(50)
    assert len(run_calls) == 2
    QTest.qWait(50)
    assert widget.refresh_btn.isEnabled()


def test_error_reenables(app, monkeypatch):
    class ErrorWorker(QObject):
        finished = Signal(dict)
        progress = Signal(int, str)
        error = Signal(str)

        def __init__(self, params):
            super().__init__()

        def run(self):
            QTimer.singleShot(10, lambda: self.error.emit("boom"))

    monkeypatch.setattr(threads, "RefreshWorker", ErrorWorker)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    widget = MarketPricesWidget(DummyMainWindow())
    widget.on_refresh_clicked()
    assert not widget.refresh_btn.isEnabled()
    QTest.qWait(50)
    assert widget.refresh_btn.isEnabled()
