"""Widget for viewing market prices across cities."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from PySide6.QtCore import Qt, QThread, QSize
from PySide6.QtGui import QIcon, QPixmap
from services.item_icons import fetch_icon_bytes
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

from utils.timefmt import rel_age, fmt_tooltip


class MarketPricesWidget(QWidget):
    """Tab for viewing live market prices."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        self.rows: List[Dict[str, Any]] = []
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
        # Use region keys expected by the data service
        self.server_combo.addItems(["europe", "east", "west"])
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
        self.table = QTableWidget(0, 7)
        self.table.setIconSize(QSize(24, 24))
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setHorizontalHeaderLabels(
            [
                "Item",
                "Route",
                "Buy (max)",
                "Sell (min)",
                "Spread",
                "ROI%",
                "Updated",
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

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.rows))
        for row_index, row in enumerate(self.rows):
            item_id = row.get("item_id", "")
            quality = row.get("quality")
            item_item = QTableWidgetItem(item_id)
            self.table.setItem(row_index, 0, item_item)

            data = fetch_icon_bytes(item_id, quality or 1)
            if data:
                pm = QPixmap()
                pm.loadFromData(data)
                if not pm.isNull():
                    item_item.setIcon(QIcon(pm))
            route = f"{row.get('buy_city') or '-'} → {row.get('sell_city') or '-'}"
            self.table.setItem(row_index, 1, QTableWidgetItem(route))
            self.table.setItem(row_index, 2, QTableWidgetItem(str(row.get("buy_price_max"))))
            self.table.setItem(row_index, 3, QTableWidgetItem(str(row.get("sell_price_min"))))
            self.table.setItem(row_index, 4, QTableWidgetItem(str(row.get("spread"))))
            roi = row.get("roi_pct")
            self.table.setItem(
                row_index,
                5,
                QTableWidgetItem(f"{roi:.1f}" if roi is not None else ""),
            )

            dt = row.get("updated_dt")
            item = QTableWidgetItem("")
            if dt:
                item.setText(rel_age(dt))
                item.setToolTip(fmt_tooltip(dt))
            self.table.setItem(row_index, 6, item)

    def update_summary_from_selection(self) -> None:
        items = self.table.selectedItems()
        if not items:
            self.best_buy_label.setText("Best Buy: -")
            return
        row = self.rows[self.table.currentRow()]
        buy = row.get("buy_city"), row.get("buy_price_max")
        sell = row.get("sell_city"), row.get("sell_price_min")
        dt = row.get("updated_dt")
        age = rel_age(dt) if dt else "?"
        if buy[0] and sell[0]:
            self.best_buy_label.setText(
                f"Buy @ {buy[0]} {buy[1]} | Sell @ {sell[0]} {sell[1]} ({age})"
            )
        else:
            self.best_buy_label.setText("Best Buy: -")

    # ------------------------------------------------------------------
    # Refresh handling
    # ------------------------------------------------------------------
    def collect_refresh_params(self) -> Dict[str, Any]:
        cities = [i.text() for i in self.city_list.selectedItems()]
        qualities = [int(i.text()) for i in self.quality_list.selectedItems()]
        server = self.server_combo.currentText()
        fetch_all = bool(self.main_window.get_config().get("fetch_all_items", True))
        params = {
            "server": server,
            "cities": ",".join(cities) if isinstance(cities, list) else (cities or ""),
            "qualities": ",".join(str(q) for q in qualities) if isinstance(qualities, list) else (qualities or ""),
            "fetch_all": fetch_all,
        }
        return params

    def on_refresh_clicked(self) -> None:
        if self.refresh_running:
            self.refresh_pending = True
            self.main_window.set_status("Refresh already running… queued")
            self.logger.info("Refresh queued while busy")
            return
        self.start_refresh()

    def start_refresh(self) -> None:
        items_text = getattr(getattr(self, "itemsEdit", None), "text", lambda: "")().strip()
        fetch_all = bool(self.main_window.get_config().get("fetch_all_items", True))
        if not items_text and not fetch_all:
            self.main_window.set_status(
                "No items selected. Type IDs or enable 'Fetch all items' in Settings."
            )
            return
        self.refresh_running = True
        self.refresh_btn.setEnabled(False)
        self.main_window.set_refresh_enabled(False)
        params = self.collect_refresh_params()
        self.logger.info("Market refresh requested: %s", params)

        from gui.threads import RefreshWorker

        self._thread = QThread(self)
        # Pass application settings so the worker can honour fetch_all_items
        self._worker = RefreshWorker(params, settings=self.main_window.get_config())
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
            payload.get("result", {}).get("unique_items"),
            payload.get("result", {}).get("records"),
            elapsed,
        )
        self._refresh_cleanup()

    def on_refresh_error(self, err: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(self, "Refresh failed", err)
        self.main_window.set_status("Refresh failed")
        self._refresh_cleanup()
