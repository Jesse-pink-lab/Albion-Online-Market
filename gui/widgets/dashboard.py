"""Minimal dashboard rendering real market summaries."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)
from PySide6.QtCore import Qt

from core.signals import signals
from utils.timefmt import rel_age, fmt_tooltip


class DashboardWidget(QWidget):
    """Dashboard showing last update, record count and top opportunities."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._build_ui()
        signals.market_data_ready.connect(self.on_market_data_ready)
        self.set_loading_state(True)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        stats = QHBoxLayout()
        stats.addWidget(QLabel("Last update:"))
        self.lblLastUpdate = QLabel("Loading…")
        stats.addWidget(self.lblLastUpdate)
        stats.addStretch()
        stats.addWidget(QLabel("Records:"))
        self.lblRecords = QLabel("0")
        stats.addWidget(self.lblRecords)
        layout.addLayout(stats)

        self.topTable = QTableWidget(0, 7)
        self.topTable.setHorizontalHeaderLabels(
            ["Item", "Route", "Buy", "Sell", "Spread", "ROI%", "Updated"]
        )
        self.topTable.verticalHeader().setVisible(False)
        self.topTable.setSelectionMode(QTableWidget.NoSelection)
        layout.addWidget(self.topTable)

    def _setCell(self, row: int, col: int, text: str, tooltip: str | None = None) -> None:
        item = QTableWidgetItem(text)
        if tooltip:
            item.setToolTip(tooltip)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.topTable.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def set_loading_state(self, loading: bool) -> None:
        if loading:
            self.lblLastUpdate.setText("Loading…")
            self.topTable.clearContents()
            self.topTable.setRowCount(0)
        self.cards.setLoading(loading) if hasattr(self, "cards") else None

    def on_market_data_ready(self, summary: dict) -> None:
        self.set_loading_state(False)
        ts = summary.get("last_update_utc")
        if ts:
            self.lblLastUpdate.setText(f"{rel_age(ts)} ago")
            self.lblLastUpdate.setToolTip(fmt_tooltip(ts))
        self.lblRecords.setText(str(summary.get("records", 0)))

        tops = summary.get("top_opportunities") or []
        self.topTable.clearContents()
        self.topTable.setRowCount(len(tops))
        for i, t in enumerate(tops):
            self._setCell(i, 0, t["item"])
            self._setCell(i, 1, f'{t["buy_city"]} \u2192 {t["sell_city"]}')
            self._setCell(i, 2, str(t["buy_price"]))
            self._setCell(i, 3, str(t["sell_price"]))
            self._setCell(i, 4, f'{t["spread"]}')
            self._setCell(i, 5, f'{t["roi_pct"]:.1f}%')
            self._setCell(
                i,
                6,
                rel_age(t["updated_dt"]),
                tooltip=fmt_tooltip(t["updated_dt"]),
            )
        if not tops:
            self.topTable.setRowCount(1)
            self._setCell(
                0,
                0,
                "No opportunities",
                tooltip="Try widening cities/qualities or lower min ROI",
            )
