import os
import sys
import pathlib
import logging
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover
    pytest.skip("PySide6 not available", allow_module_level=True)

from gui.threads import RefreshWorker


def test_refresh_worker_summary(monkeypatch, caplog):
    app = QApplication.instance() or QApplication([])

    rows = [{"item_id": "A"}, {"item_id": "A"}, {"item_id": "B"}]

    class DummyStore:
        def fetch_prices(self, **kwargs):
            return rows

    monkeypatch.setattr("gui.threads.STORE", DummyStore())
    monkeypatch.setattr("gui.threads.get_shared_session", lambda: None)
    monkeypatch.setattr("gui.threads.mark_online_on_data_success", lambda: None)

    worker = RefreshWorker({"server": "europe"}, settings={})
    payloads = []
    worker.finished.connect(lambda p: payloads.append(p))

    with caplog.at_level(logging.INFO):
        worker.run()

    assert "items=2 records=3" in caplog.text
    assert payloads and payloads[0]["result"]["unique_items"] == 2
    assert payloads[0]["result"]["records"] == 3
