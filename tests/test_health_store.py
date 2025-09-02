from PySide6.QtCore import QCoreApplication

from PySide6.QtCore import QCoreApplication
import sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from core.health import update_aodp_status
from core.signals import signals


app = QCoreApplication.instance() or QCoreApplication([])


def test_health_signal_updates_receivers():
    received = []
    received2 = []

    def handler(store):
        received.append(store)

    def handler2(store):
        received2.append(store)

    signals.health_changed.connect(handler)
    signals.health_changed.connect(handler2)

    update_aodp_status(True)

    assert received and received2
    assert received[-1].aodp_online is True
    assert received2[-1].aodp_online is True
