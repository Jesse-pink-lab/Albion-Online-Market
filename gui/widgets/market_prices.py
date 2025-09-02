"""Widget for viewing market prices across cities."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.market_prices import fetch_prices


class MarketPricesWidget(QWidget):
    """Tab for viewing live market prices."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        self.rows: List[Dict[str, Any]] = []
        self.summary: Dict[str, Dict[str, Any]] = {}
        self.init_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def init_ui(self) -> None:
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Server:"))
        self.server_combo = QComboBox()
        self.server_combo.addItems(["europe", "asia", "americas"])
        controls.addWidget(self.server_combo)

        controls.addWidget(QLabel("Cities:"))
        self.city_list = QListWidget()
        self.city_list.setSelectionMode(QAbstractItemView.MultiSelection)
        for city in [
            "Bridgewatch",
            "Martlock",
            "Lymhurst",
            "Thetford",
            "Fort Sterling",
            "Caerleon",
        ]:
            item = QListWidgetItem(city)
            item.setSelected(True)
            self.city_list.addItem(item)
        controls.addWidget(self.city_list)

        controls.addWidget(QLabel("Qualities:"))
        self.quality_list = QListWidget()
        self.quality_list.setSelectionMode(QAbstractItemView.MultiSelection)
        for q in range(1, 6):
            item = QListWidgetItem(str(q))
            if q == 1:
                item.setSelected(True)
            self.quality_list.addItem(item)
        controls.addWidget(self.quality_list)

        layout.addLayout(controls)

        body = QHBoxLayout()
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "Icon",
                "Item",
                "City",
                "Quality",
                "Sell Min",
                "Sell Max",
                "Buy Max",
                "Buy Min",
                "Last Update Sell",
                "Last Update Buy",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.update_summary_from_selection)
        body.addWidget(self.table, 3)

        side_widget = QWidget()
        side_layout = QVBoxLayout(side_widget)
        self.best_buy_label = QLabel("Best Buy: -")
        self.best_sell_label = QLabel("Best Sell: -")
        side_layout.addWidget(self.best_buy_label)
        side_layout.addWidget(self.best_sell_label)
        side_layout.addStretch()
        body.addWidget(side_widget, 1)

        layout.addLayout(body)

    # ------------------------------------------------------------------
    # Data handling
    # ------------------------------------------------------------------
    def load_prices(self, items: List[str]) -> None:
        cities = [i.text() for i in self.city_list.selectedItems()]
        qualities = [int(i.text()) for i in self.quality_list.selectedItems()]
        server = self.server_combo.currentText()

        try:
            rows, summary = fetch_prices(items, cities, qualities, server)
        except Exception as exc:  # pragma: no cover - network errors
            self.logger.error("Failed to fetch prices: %s", exc)
            return

        self.rows = rows
        self.summary = summary
        self.populate_table()

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.rows))
        for row_index, row in enumerate(self.rows):
            # Icon
            icon_label = QLabel()
            try:
                response = requests.get(row["icon_url"], timeout=30)
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                icon_label.setPixmap(pixmap.scaled(40, 40, Qt.KeepAspectRatio))
            except Exception:  # pragma: no cover - network failure
                pass
            self.table.setCellWidget(row_index, 0, icon_label)

            self.table.setItem(row_index, 1, QTableWidgetItem(row["item_id"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(row["city"]))
            self.table.setItem(row_index, 3, QTableWidgetItem(str(row["quality"])))
            self.table.setItem(row_index, 4, QTableWidgetItem(str(row["sell_min"])))
            self.table.setItem(row_index, 5, QTableWidgetItem(str(row["sell_max"])))
            self.table.setItem(row_index, 6, QTableWidgetItem(str(row["buy_max"])))
            self.table.setItem(row_index, 7, QTableWidgetItem(str(row["buy_min"])))
            self.table.setItem(
                row_index, 8, QTableWidgetItem(row["last_update_sell"] or "")
            )
            self.table.setItem(
                row_index, 9, QTableWidgetItem(row["last_update_buy"] or "")
            )

    def update_summary_from_selection(self) -> None:
        items = self.table.selectedItems()
        if not items:
            self.best_buy_label.setText("Best Buy: -")
            self.best_sell_label.setText("Best Sell: -")
            return
        item_id = self.table.item(self.table.currentRow(), 1).text()
        info = self.summary.get(item_id)
        if not info:
            return
        bb = info["best_buy"]
        bs = info["best_sell"]
        if bb["city"] is not None:
            self.best_buy_label.setText(f"Best Buy: {bb['city']} @ {bb['price']}")
        if bs["city"] is not None:
            self.best_sell_label.setText(f"Best Sell: {bs['city']} @ {bs['price']}")
