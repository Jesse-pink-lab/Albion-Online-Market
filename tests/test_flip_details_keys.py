import os, sys, pathlib
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication
flip_finder = pytest.importorskip("gui.widgets.flip_finder")
FlipFinderWidget = flip_finder.FlipFinderWidget


def test_detail_panel_uses_item_name(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(flip_finder, "fetch_icon_bytes", lambda *a, **k: None)
    widget = FlipFinderWidget(None)
    flip = {
        "item_id": "T4_SWORD",
        "item_name": "Sword",
        "buy_city": "Martlock",
        "sell_city": "Lymhurst",
        "buy": 100,
        "sell": 150,
        "spread": 50,
        "roi": 0.5,
        "roi_pct": 50.0,
        "updated": "just now",
    }
    widget.current_flips = [flip]
    widget.populate_results_table([flip])
    widget.results_table.selectRow(0)
    widget.on_selection_changed()
    text = widget.details_text.toPlainText()
    assert "Sword" in text
