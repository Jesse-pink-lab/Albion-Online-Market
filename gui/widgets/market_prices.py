"""Widget for viewing market prices across cities."""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from datetime import datetime

import requests
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.market_prices import fetch_prices
from utils.timefmt import to_utc, rel_age, fmt_tooltip
from core.signals import signals


class MarketPricesWidget(QWidget):
    """Tab for viewing live market prices."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        self.rows: List[Dict[str, Any]] = []
        self.summary: Dict[str, Dict[str, Any]] = {}
        self.refresh_running = False
        self.refresh_pending = False
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

        self.refresh_btn = QPushButton("Refresh Market Data")
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        controls.addWidget(self.refresh_btn)

        layout.addLayout(controls)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel()
        layout.addWidget(self.progress_label)

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
                "Updated Sell",
                "Updated Buy",
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

            sell_dt = row.get("last_update_sell")
            item = QTableWidgetItem("")
            if sell_dt:
                dt = to_utc(sell_dt)
                item.setText(rel_age(dt))
                item.setToolTip(fmt_tooltip(dt))
            self.table.setItem(row_index, 8, item)

            buy_dt = row.get("last_update_buy")
            item = QTableWidgetItem("")
            if buy_dt:
                dt = to_utc(buy_dt)
                item.setText(rel_age(dt))
                item.setToolTip(fmt_tooltip(dt))
            self.table.setItem(row_index, 9, item)

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
        bb = info.get("sell_price_min", {})
        bs = info.get("buy_price_max", {})
        age = None
        if bs.get("date"):
            dt = to_utc(bs["date"])
            age = rel_age(dt)
        if bb.get("city") is not None and bs.get("city") is not None:
            self.best_buy_label.setText(
                f"Buy @ {bb['city']} {bb['price']} | Sell @ {bs['city']} {bs['price']} ({age or '?'})"
            )
        else:
            self.best_buy_label.setText("Best Buy: -")
        self.best_sell_label.setText("")

    # ------------------------------------------------------------------
    # Refresh handling
    # ------------------------------------------------------------------
    def collect_refresh_params(self) -> Dict[str, Any]:
        cities = [i.text() for i in self.city_list.selectedItems()]
        qualities = [int(i.text()) for i in self.quality_list.selectedItems()]
        server = self.server_combo.currentText()
        return {"server": server, "city": cities[0] if cities else "", "qualities": qualities}

    def on_refresh_clicked(self) -> None:
        if self.refresh_running:
            self.refresh_pending = True
            self.main_window.set_status("Refresh already running… queued")
            self.logger.info("Refresh queued while busy")
            return
        self.start_refresh()

    def start_refresh(self) -> None:
        self.refresh_running = True
        self.refresh_btn.setEnabled(False)
        self.main_window.set_refresh_enabled(False)
        params = self.collect_refresh_params()
        self.logger.info("Market refresh requested: %s", params)

        from gui.threads import RefreshWorker

        self._thread = QThread(self)
        self._worker = RefreshWorker(params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_refresh_progress)
        self._worker.finished.connect(self.on_refresh_done)
        self._worker.error.connect(self.on_refresh_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def on_refresh_progress(self, pct: int, msg: str) -> None:
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    def _refresh_cleanup(self) -> None:
        self.refresh_running = False
        self.refresh_btn.setEnabled(True)
        self.main_window.set_refresh_enabled(True)
        self.progress_bar.setVisible(False)
        if self.refresh_pending:
            self.refresh_pending = False
            self.start_refresh()

    def on_refresh_done(self, payload: Dict[str, Any]) -> None:
        elapsed = payload.get("elapsed", 0)
        self.main_window.set_status(f"Refresh done in {elapsed:.2f}s")
        self.logger.info(
            "Market refresh completed: items=%s records=%s elapsed=%.2fs",
            payload.get("result", {}).get("items"),
            payload.get("result", {}).get("records"),
            elapsed,
        )
        summary = {
            "last_update_utc": datetime.utcnow().isoformat() + "Z",
            "records": payload.get("result", {}).get("records"),
            "best_flip": None,
            "best_craft": None,
            "activity": None,
        }
        signals.market_data_ready.emit(summary)
        self._refresh_cleanup()

    def on_refresh_error(self, err: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(self, "Refresh failed", err)
        self.main_window.set_status("Refresh failed")
        self._refresh_cleanup()
