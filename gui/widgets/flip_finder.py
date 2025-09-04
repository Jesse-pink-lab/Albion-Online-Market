"""
Flip Finder widget for Albion Trade Optimizer.

Allows users to search for and analyze flip opportunities.
"""

import logging
from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QGroupBox,
    QHeaderView, QAbstractItemView, QSplitter, QTextEdit,
    QProgressBar, QFrame, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap

from services.item_icons import fetch_icon_bytes
from utils.timefmt import rel_age
from utils.items import parse_item_input
from utils.params import parse_quality_input, parse_city_selection
import pandas as pd
from datetime import datetime

from services.flip_engine import build_flips
from services.market_prices import STORE

log = logging.getLogger(__name__)


class SortableTableWidgetItem(QTableWidgetItem):
    """Table item that sorts by Qt.UserRole if available."""

    def __lt__(self, other):  # type: ignore[override]
        if isinstance(other, QTableWidgetItem):
            sd = self.data(Qt.UserRole)
            od = other.data(Qt.UserRole)
            if sd is not None and od is not None:
                return sd < od
        return super().__lt__(other)


class FlipFinderWorker(QThread):
    """Background worker for computing flip opportunities."""

    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(int, str)

    def __init__(self, params: Dict[str, Any]):
        super().__init__()
        self.params = params
        self.log = logging.getLogger(__name__)

    def run(self):
        try:
            self.progress.emit(10, "Preparing data...")
            rows = STORE.latest_rows()
            trimmed = []

            def _num(row, *keys, default=0):
                for k in keys:
                    if k in row and row[k] is not None:
                        try:
                            return float(row[k])
                        except Exception:
                            pass
                return float(default)

            for r in rows:
                buy_val = _num(r, "buy_price_max", "buy_max", "BuyMax", default=0)
                sell_val = _num(r, "sell_price_min", "sell_min", "SellMin", default=0)
                if buy_val > 0 or sell_val > 0:
                    row_norm = dict(r)
                    row_norm["buy_price_max"] = buy_val
                    row_norm["sell_price_min"] = sell_val
                    row_norm["buy"] = buy_val
                    row_norm["sell"] = sell_val
                    trimmed.append(row_norm)

            self.log.debug(
                "FlipFinder trimmed rows: %s (examples: %s)",
                len(trimmed),
                trimmed[:2],
            )
            self.progress.emit(50, "Computing...")
            src_cities = set(self.params.get("src_cities") or self.params.get("cities") or [])
            dst_cities = set(self.params.get("dst_cities") or self.params.get("cities") or [])
            parsed_items = self.params.get("items")
            ui_min_profit = int(self.params.get("min_profit", 0))
            ui_min_roi_pct = float(self.params.get("min_roi", 0.0))
            min_roi_decimal = ui_min_roi_pct / 100.0
            self.log.debug("UI ROI percent=%s -> decimal=%s", ui_min_roi_pct, min_roi_decimal)
            ui_max_age = int(self.params.get("max_age_hours", 24))
            tiers = [
                {"tag": "strict", "min_profit": ui_min_profit, "min_roi": min_roi_decimal, "max_age": ui_max_age, "items": parsed_items},
                {"tag": "relaxed-1", "min_profit": 1, "min_roi": 0.10, "max_age": max(ui_max_age, 168), "items": parsed_items},
                {"tag": "relaxed-2", "min_profit": 1, "min_roi": 0.10, "max_age": max(ui_max_age, 168), "items": None},
                {"tag": "relaxed-3", "min_profit": 1, "min_roi": 0.01, "max_age": max(ui_max_age, 336), "items": None},
            ]

            flips = []
            tag = tiers[-1]["tag"]
            all_stats = []
            stats = {}
            for tier in tiers:
                flips, stats = build_flips(
                    rows=trimmed,
                    items_filter=tier["items"],
                    src_cities=src_cities,
                    dst_cities=dst_cities,
                    qualities=self.params.get("qualities"),
                    min_profit=tier["min_profit"],
                    min_roi=tier["min_roi"],
                    max_age_hours=tier["max_age"],
                    max_results=self.params.get("max_results", 100),
                )
                if flips:
                    tag = tier["tag"]
                    all_stats.append((tier["tag"], stats, len(flips)))
                    break
                all_stats.append((tier["tag"], stats, 0))

            self.progress.emit(100, "Done")
            self.finished.emit({"flips": flips, "tag": tag, "stats": stats, "all_stats": all_stats})
        except Exception as e:
            self.log.exception("Flip search failed: %r", e)
            self.error.emit(str(e))


class FlipFinderWidget(QWidget):
    """Widget for finding and analyzing flip opportunities."""
    
    def __init__(self, main_window):
        """Initialize flip finder widget."""
        super().__init__()
        
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Worker and data
        self.worker = None
        self._pending = False
        self.current_flips: List[Dict[str, Any]] = []

        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create header
        self.create_header(layout)
        
        # Create main content with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Search controls
        self.create_search_panel(splitter)
        
        # Right panel: Results
        self.create_results_panel(splitter)
        
        # Set splitter proportions
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
        # Create footer
        self.create_footer(layout)
    
    def create_header(self, parent_layout):
        """Create header with title and quick actions."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("💰 Flip Finder")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Quick search button
        quick_search_btn = QPushButton("🔍 Quick Search")
        quick_search_btn.clicked.connect(self.quick_search)
        header_layout.addWidget(quick_search_btn)
        
        # Clear results button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_results)
        header_layout.addWidget(clear_btn)
        
        parent_layout.addWidget(header_frame)
    
    def create_search_panel(self, parent_splitter):
        """Create search controls panel."""
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(5, 5, 5, 5)
        
        # Search parameters group
        params_group = QGroupBox("Search Parameters")
        params_layout = QGridLayout(params_group)
        
        row = 0
        
        # Items filter
        params_layout.addWidget(QLabel("Items:"), row, 0)
        self.items_edit = QLineEdit()
        self.items_edit.setPlaceholderText("T4_SWORD,T5_SWORD (leave empty for all)")
        params_layout.addWidget(self.items_edit, row, 1)
        row += 1
        
        # Cities filter
        params_layout.addWidget(QLabel("Cities:"), row, 0)
        self.cities_combo = QComboBox()
        self.cities_combo.addItems(["All Cities", "Royal Cities Only", "Black Market Only", "Custom"])
        params_layout.addWidget(self.cities_combo, row, 1)
        row += 1
        
        # Quality filter
        params_layout.addWidget(QLabel("Quality:"), row, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Normal (1)", "Good (2)", "Outstanding (3)", "Excellent (4)", "Masterpiece (5)", "All"])
        params_layout.addWidget(self.quality_combo, row, 1)
        row += 1
        
        # Strategy filter
        params_layout.addWidget(QLabel("Strategy:"), row, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["All", "Fast", "Patient"])
        params_layout.addWidget(self.strategy_combo, row, 1)
        row += 1
        
        search_layout.addWidget(params_group)
        
        # Filters group
        filters_group = QGroupBox("Filters")
        filters_layout = QGridLayout(filters_group)
        
        row = 0
        
        # Min profit filter
        filters_layout.addWidget(QLabel("Min Profit:"), row, 0)
        self.min_profit_spin = QSpinBox()
        self.min_profit_spin.setRange(0, 1000000)
        self.min_profit_spin.setSuffix(" silver")
        self.min_profit_spin.setValue(1000)
        filters_layout.addWidget(self.min_profit_spin, row, 1)
        row += 1
        
        # Min ROI filter
        filters_layout.addWidget(QLabel("Min ROI:"), row, 0)
        self.min_roi_spin = QDoubleSpinBox()
        self.min_roi_spin.setRange(0, 1000)
        self.min_roi_spin.setSuffix("%")
        self.min_roi_spin.setValue(5.0)
        filters_layout.addWidget(self.min_roi_spin, row, 1)
        row += 1

        # Max age filter
        filters_layout.addWidget(QLabel("Max Age (h):"), row, 0)
        self.max_age_spin = QSpinBox()
        self.max_age_spin.setRange(1, 168)
        self.max_age_spin.setValue(24)
        filters_layout.addWidget(self.max_age_spin, row, 1)
        row += 1

        # Max results
        filters_layout.addWidget(QLabel("Max Results:"), row, 0)
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 1000)
        self.max_results_spin.setValue(100)
        filters_layout.addWidget(self.max_results_spin, row, 1)
        row += 1
        
        search_layout.addWidget(filters_group)
        
        # Search button
        self.search_btn = QPushButton("🔍 Search Opportunities")
        self.search_btn.clicked.connect(self.search_opportunities)
        search_layout.addWidget(self.search_btn)
        
        search_layout.addStretch()
        
        parent_splitter.addWidget(search_widget)
    
    def create_results_panel(self, parent_splitter):
        """Create results display panel."""
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(5, 5, 5, 5)
        
        # Results header
        results_header = QHBoxLayout()
        
        self.results_label = QLabel("No search performed")
        results_header.addWidget(self.results_label)
        
        results_header.addStretch()
        
        # Export button
        export_btn = QPushButton("📄 Export")
        export_btn.clicked.connect(self.export_results)
        results_header.addWidget(export_btn)
        
        results_layout.addLayout(results_header)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setIconSize(QSize(24, 24))
        self.results_table.verticalHeader().setDefaultSectionSize(28)
        self.results_table.setHorizontalHeaderLabels([
            "Item", "Route", "Buy", "Sell", "Spread", "ROI %", "Updated"
        ])
        
        # Configure table
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Item column
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        
        # Connect selection change
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        results_layout.addWidget(self.results_table)
        
        # Details panel
        self.create_details_panel(results_layout)
        
        parent_splitter.addWidget(results_widget)
    
    def create_details_panel(self, parent_layout):
        """Create opportunity details panel."""
        details_group = QGroupBox("Opportunity Details")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(150)
        self.details_text.setReadOnly(True)
        self.details_text.setPlainText("Select an opportunity to view details.")
        
        details_layout.addWidget(self.details_text)
        
        parent_layout.addWidget(details_group)
    
    def create_footer(self, parent_layout):
        """Create footer with status and progress."""
        footer_frame = QFrame()
        footer_frame.setFrameStyle(QFrame.StyledPanel)
        footer_layout = QHBoxLayout(footer_frame)
        
        # Status label
        self.status_label = QLabel("Ready")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        footer_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(footer_frame)
    
    def quick_search(self):
        """Perform a quick search with default parameters."""
        # Set default values
        self.items_edit.clear()
        self.cities_combo.setCurrentText("Royal Cities Only")
        self.quality_combo.setCurrentText("Normal (1)")
        self.strategy_combo.setCurrentText("All")
        self.min_profit_spin.setValue(1000)
        self.min_roi_spin.setValue(5.0)
        self.max_age_spin.setValue(24)

        # Start search
        self.search_opportunities()

    def search_opportunities(self):
        """Search for flip opportunities."""
        if self.worker and self.worker.isRunning():
            self._pending = True
            self.logger.info("Search queued while another is running")
            return

        params = self.get_search_parameters()

        self.worker = FlipFinderWorker(params)
        self.worker.finished.connect(self.on_flips_found)
        self.worker.error.connect(self.on_search_error)
        self.worker.progress.connect(self.on_progress_updated)

        self.search_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.set_status("Searching...")

        self.worker.start()
    
    def get_search_parameters(self) -> Dict[str, Any]:
        """Get search parameters from UI."""
        params = {}

        # Items
        params['items'] = parse_item_input(self.items_edit.text())

        # Cities - same set for src and dst
        cities_selection = self.cities_combo.currentText()
        all_cities = ["Martlock", "Lymhurst", "Bridgewatch", "Fort Sterling", "Thetford", "Caerleon"]
        cities_set = parse_city_selection(cities_selection, all_cities)
        params['cities'] = list(cities_set)
        params['src_cities'] = list(cities_set)
        params['dst_cities'] = list(cities_set)

        # Quality
        quality_text = self.quality_combo.currentText()
        params['qualities'] = parse_quality_input(quality_text)

        # Filters
        params['min_profit'] = self.min_profit_spin.value()
        params['min_roi'] = self.min_roi_spin.value()
        params['max_results'] = self.max_results_spin.value()
        params['max_age_hours'] = self.max_age_spin.value()

        return params
    
    def on_flips_found(self, payload: Dict[str, Any]):
        """Handle search results."""
        flips = payload.get("flips", [])
        self.current_flips = flips
        self.populate_results_table(flips)

        self.results_label.setText(f"Found {len(flips)} opportunities")
        self.set_status(f"Search complete: {len(flips)} opportunities found")

        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if self._pending:
            self._pending = False
            self.search_opportunities()
    
    def on_progress_updated(self, progress: int, message: str):
        """Handle progress updates."""
        self.progress_bar.setValue(progress)
        self.set_status(message)
    
    def on_search_error(self, error_message: str):
        """Handle search errors."""
        self.logger.error(f"Search error: {error_message}")
        self.set_status(f"Search failed: {error_message}")

        # Reset UI
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._pending = False
    
    def populate_results_table(self, flips: List[Dict[str, Any]]):
        """Populate results table with flip data."""
        self.results_table.setRowCount(len(flips))

        for row, flip in enumerate(flips):
            item_id = flip.get("item_id") or flip.get("item") or ""
            quality = flip.get("quality")
            item_text = flip.get("item_name") or item_id or "—"
            item_cell = QTableWidgetItem(item_text)
            item_cell.setData(Qt.UserRole, flip)
            self.results_table.setItem(row, 0, item_cell)

            def _apply_icon(icon, cell=item_cell):
                cell.setIcon(icon)

            data = fetch_icon_bytes(item_id, quality or 1)
            if data:
                pm = QPixmap()
                pm.loadFromData(data)
                if not pm.isNull():
                    _apply_icon(QIcon(pm))

            route_str = f"{flip['buy_city']} → {flip['sell_city']}"
            flip.setdefault("route", route_str)
            route_item = QTableWidgetItem(route_str)
            self.results_table.setItem(row, 1, route_item)

            buy_item = QTableWidgetItem(f"{flip['buy']:,}")
            buy_item.setData(Qt.EditRole, flip['buy'])
            self.results_table.setItem(row, 2, buy_item)

            sell_item = QTableWidgetItem(f"{flip['sell']:,}")
            sell_item.setData(Qt.EditRole, flip['sell'])
            self.results_table.setItem(row, 3, sell_item)

            spread_item = QTableWidgetItem(f"{flip['spread']:,}")
            spread_item.setData(Qt.EditRole, flip['spread'])
            self.results_table.setItem(row, 4, spread_item)

            roi_item = QTableWidgetItem(f"{flip['roi_pct']:.1f}%")
            roi_item.setData(Qt.EditRole, flip['roi_pct'])
            self.results_table.setItem(row, 5, roi_item)

            udisp = flip.get("updated") or ""
            udt = flip.get("updated_dt")
            if not udisp and isinstance(udt, (datetime, pd.Timestamp)):
                if isinstance(udt, pd.Timestamp):
                    udt = udt.to_pydatetime()
                udisp = rel_age(udt)
            updated_item = SortableTableWidgetItem(str(udisp))
            if isinstance(udt, datetime):
                updated_item.setData(Qt.UserRole, int(udt.timestamp()))
            self.results_table.setItem(row, 6, updated_item)

        self.results_table.sortItems(5, Qt.DescendingOrder)
    
    def on_selection_changed(self):
        """Handle table selection change."""
        selected_rows = {item.row() for item in self.results_table.selectedItems()}
        if selected_rows:
            row = min(selected_rows)
            if 0 <= row < len(self.current_flips):
                self.show_opportunity_details(self.current_flips[row])
        else:
            self.details_text.setPlainText("Select an opportunity to view details.")

    def show_opportunity_details(self, flip: Dict[str, Any]):
        """Show detailed information about a flip."""
        item_name = flip.get("item_name") or flip.get("item_id") or str(flip.get("item", "N/A"))
        buy = flip.get("buy", 0)
        sell = flip.get("sell", 0)
        spread = flip.get("spread", sell - buy)
        roi = flip.get("roi", 0)
        route = flip.get("route") or f"{flip.get('buy_city', '')} → {flip.get('sell_city', '')}"
        updated = flip.get("updated_ago") or flip.get("updated") or ""
        self.details_text.setPlainText(
            f"Item: {item_name}\n"
            f"Route: {route}\n"
            f"Buy: {int(buy):,}\nSell: {int(sell):,}\n"
            f"Profit: {int(spread):,}\nROI: {roi*100:.2f}%\n"
            f"Updated: {updated}"
        )
    
    def clear_results(self):
        """Clear search results."""
        self.current_flips = []
        self.results_table.setRowCount(0)
        self.results_label.setText("No search performed")
        self.details_text.setPlainText("Select an opportunity to view details.")
        self.set_status("Results cleared")
    
    def export_results(self):
        """Export results to file."""
        if not self.current_flips:
            self.set_status("No results to export")
            return
        
        # This would open a file dialog and export to CSV/Excel
        self.set_status("Export feature not yet implemented")
    
    def refresh_data(self):
        """Refresh data (called from main window)."""
        if self.current_flips:
            self.search_opportunities()

    def set_opportunities(self, flips: List[Dict[str, Any]]):
        """Set opportunities from external source (e.g., dashboard)."""
        self.current_flips = flips
        self.populate_results_table(flips)
        self.results_label.setText(f"Showing {len(flips)} opportunities")
    
    def set_status(self, message: str):
        """Set status message."""
        self.status_label.setText(message)
        self.logger.debug(f"Flip finder status: {message}")

