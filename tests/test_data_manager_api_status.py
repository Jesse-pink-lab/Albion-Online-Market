import os, sys, pathlib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover
    pytest.skip("PySide6 not available", allow_module_level=True)

import core.health as health
from core.health import store
from gui.widgets.data_manager import DataManagerWidget


class DummyMain:
    def get_db_manager(self):
        return None

    def get_api_client(self):
        return None

    def refresh_data(self):
        pass

    def set_status(self, msg):
        pass


def test_api_status_tile(monkeypatch):
    app = QApplication.instance() or QApplication([])

    def online_ping(server):
        store.set_online(True)
        return True

    monkeypatch.setattr(health, "ping_aodp", online_ping)
    w = DataManagerWidget(DummyMain())
    assert w.lblApiStatus.text() == "Online"
    assert w.api_status_card.value_label.text().startswith("🟢")

    def offline_ping(server):
        store.set_online(False)
        return False

    monkeypatch.setattr(health, "ping_aodp", offline_ping)
    w.refreshApiStatus()
    assert w.lblApiStatus.text() == "Offline"
    assert w.api_status_card.value_label.text().startswith("🔴")
