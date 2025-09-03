"""
Flip Finder widget for Albion Trade Optimizer.

Allows users to search for and analyze flip opportunities.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QGroupBox, QCheckBox,
    QHeaderView, QAbstractItemView, QSplitter, QTextEdit,
    QProgressBar, QFrame, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from utils.timefmt import to_utc, rel_age, fmt_tooltip
from utils.items import parse_items, items_catalog_codes
from PySide6.QtGui import QFont, QColor

from engine.flips import FlipCalculator, FlipOpportunity


class FlipSearchThread(QThread):
    """Thread for searching flip opportunities."""
    
    opportunities_found = Signal(list)
    progress_updated = Signal(int, str)
    error_occurred = Signal(str)
    
    def __init__(self, api_client, flip_calculator, search_params):
        super().__init__()
        self.api_client = api_client
        self.flip_calculator = flip_calculator
        self.search_params = search_params
    
    def run(self):
        """Run flip search in background thread."""
        try:
            self.progress_updated.emit(10, "Fetching market data...")
            
            # Get market prices
            items = self.search_params.get('items', [])
            cities = self.search_params.get('cities', [])
            qualities = self.search_params.get('qualities', [1])
            
            prices = self.api_client.get_current_prices(items, cities, qualities)
            
            self.progress_updated.emit(50, "Analyzing opportunities...")
            
            # Group prices by item
            prices_by_item = {}
            for price in prices:
                item_id = price['item_id']
                if item_id not in prices_by_item:
                    prices_by_item[item_id] = []
                prices_by_item[item_id].append(price)
            
            # Calculate opportunities
            opportunities = self.flip_calculator.calculate_flip_opportunities(prices_by_item)
            
            self.progress_updated.emit(80, "Filtering results...")
            
            # Apply filters
            filtered_opportunities = self.apply_filters(opportunities)
            
            self.progress_updated.emit(100, "Complete")
            self.opportunities_found.emit(filtered_opportunities)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def apply_filters(self, opportunities: List[FlipOpportunity]) -> List[FlipOpportunity]:
        """Apply search filters to opportunities."""
        filtered = opportunities
        
        # Min profit filter
        min_profit = self.search_params.get('min_profit', 0)
        if min_profit > 0:
            filtered = [opp for opp in filtered if opp.profit_per_unit >= min_profit]
        
        # Min ROI filter
        min_roi = self.search_params.get('min_roi', 0)
        if min_roi > 0:
            filtered = [opp for opp in filtered if opp.roi_percent >= min_roi]
        
        # Risk level filter
        max_risk = self.search_params.get('max_risk', 'high')
        risk_levels = ['low', 'medium', 'high']
        max_risk_index = risk_levels.index(max_risk)
        filtered = [opp for opp in filtered if risk_levels.index(opp.risk_level) <= max_risk_index]
        
        # Strategy filter
        strategy = self.search_params.get('strategy')
        if strategy and strategy != 'all':
            filtered = [opp for opp in filtered if opp.strategy == strategy]
        
        # Sort by profit (descending)
        filtered.sort(key=lambda x: x.profit_per_unit, reverse=True)
        
        # Limit results
        max_results = self.search_params.get('max_results', 100)
        return filtered[:max_results]


class FlipFinderWidget(QWidget):
    """Widget for finding and analyzing flip opportunities."""
    
    def __init__(self, main_window):
        """Initialize flip finder widget."""
        super().__init__()
        
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.flip_calculator = None
        self.search_thread = None
        
        # Data
        self.current_opportunities = []
        
        self.init_ui()
        self.init_backend()
    
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
        
        # Max risk filter
        filters_layout.addWidget(QLabel("Max Risk:"), row, 0)
        self.max_risk_combo = QComboBox()
        self.max_risk_combo.addItems(["Low", "Medium", "High"])
        self.max_risk_combo.setCurrentText("High")
        filters_layout.addWidget(self.max_risk_combo, row, 1)
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
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "Item", "Quality", "Strategy", "Route", "Profit", "ROI %", "Investment", "Risk", "Updated"
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
    
    def init_backend(self):
        """Initialize backend components."""
        try:
            config = self.main_window.get_config()
            self.flip_calculator = FlipCalculator(config)
            self.logger.info("Flip finder backend initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize flip finder backend: {e}")
    
    def quick_search(self):
        """Perform a quick search with default parameters."""
        # Set default values
        self.items_edit.clear()
        self.cities_combo.setCurrentText("Royal Cities Only")
        self.quality_combo.setCurrentText("Normal (1)")
        self.strategy_combo.setCurrentText("All")
        self.min_profit_spin.setValue(1000)
        self.min_roi_spin.setValue(5.0)
        self.max_risk_combo.setCurrentText("Medium")
        
        # Start search
        self.search_opportunities()
    
    def search_opportunities(self):
        """Search for flip opportunities."""
        if self.search_thread and self.search_thread.isRunning():
            self.logger.warning("Search already in progress")
            return
        
        api_client = self.main_window.get_api_client()
        if not api_client:
            self.set_status("Error: API client not available")
            return
        
        if not self.flip_calculator:
            self.set_status("Error: Flip calculator not available")
            return
        
        # Prepare search parameters
        search_params = self.get_search_parameters()
        
        # Start search thread
        self.search_thread = FlipSearchThread(api_client, self.flip_calculator, search_params)
        self.search_thread.opportunities_found.connect(self.on_opportunities_found)
        self.search_thread.progress_updated.connect(self.on_progress_updated)
        self.search_thread.error_occurred.connect(self.on_search_error)
        
        # Update UI
        self.search_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.set_status("Searching...")
        
        self.search_thread.start()
    
    def get_search_parameters(self) -> Dict[str, Any]:
        """Get search parameters from UI."""
        params = {}
        
        # Items
        cfg = self.main_window.get_config()
        fetch_all = bool(cfg.get('fetch_all_items', True))
        raw = self.items_edit.text()
        typed = parse_items(raw)
        catalog = list(items_catalog_codes())
        items = catalog if (not typed and fetch_all) else typed
        self.logger.info(
            "Item selection: catalog=%d typed=%d fetch_all=%s -> final=%d",
            len(catalog), len(typed), fetch_all, len(items),
        )
        self.logger.debug("Items(head 12): %s", items[:12])
        if items:
            params['items'] = items
        params['fetch_all'] = fetch_all
        
        # Cities
        cities_selection = self.cities_combo.currentText()
        if cities_selection == "Royal Cities Only":
            params['cities'] = ['Martlock', 'Lymhurst', 'Bridgewatch', 'Fort Sterling', 'Thetford']
        elif cities_selection == "Black Market Only":
            params['cities'] = ['Caerleon']
        elif cities_selection == "Custom":
            # For now, use all cities
            params['cities'] = ['Martlock', 'Lymhurst', 'Bridgewatch', 'Fort Sterling', 'Thetford', 'Caerleon']
        else:  # All Cities
            params['cities'] = ['Martlock', 'Lymhurst', 'Bridgewatch', 'Fort Sterling', 'Thetford', 'Caerleon']
        
        # Quality
        quality_text = self.quality_combo.currentText()
        if "All" in quality_text:
            params['qualities'] = [1, 2, 3, 4, 5]
        else:
            # Extract quality number from text like "Normal (1)"
            quality_num = int(quality_text.split('(')[1].split(')')[0])
            params['qualities'] = [quality_num]
        
        # Strategy
        strategy = self.strategy_combo.currentText().lower()
        params['strategy'] = strategy if strategy != 'all' else None
        
        # Filters
        params['min_profit'] = self.min_profit_spin.value()
        params['min_roi'] = self.min_roi_spin.value()
        params['max_risk'] = self.max_risk_combo.currentText().lower()
        params['max_results'] = self.max_results_spin.value()
        
        return params
    
    def on_opportunities_found(self, opportunities: List[FlipOpportunity]):
        """Handle search results."""
        self.current_opportunities = opportunities
        self.populate_results_table(opportunities)
        
        # Update status
        self.results_label.setText(f"Found {len(opportunities)} opportunities")
        self.set_status(f"Search complete: {len(opportunities)} opportunities found")
        
        # Reset UI
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
    
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
    
    def populate_results_table(self, opportunities: List[FlipOpportunity]):
        """Populate results table with opportunities."""
        self.results_table.setRowCount(len(opportunities))
        
        for row, opp in enumerate(opportunities):
            # Item
            item_item = QTableWidgetItem(opp.item_id)
            self.results_table.setItem(row, 0, item_item)
            
            # Quality
            quality_item = QTableWidgetItem(str(opp.quality))
            self.results_table.setItem(row, 1, quality_item)
            
            # Strategy
            strategy_item = QTableWidgetItem(opp.strategy.title())
            self.results_table.setItem(row, 2, strategy_item)
            
            # Route
            route_item = QTableWidgetItem(f"{opp.source_city} → {opp.destination_city}")
            self.results_table.setItem(row, 3, route_item)
            
            # Profit
            profit_item = QTableWidgetItem(f"{opp.profit_per_unit:,.0f}")
            profit_item.setData(Qt.UserRole, opp.profit_per_unit)  # For sorting
            self.results_table.setItem(row, 4, profit_item)
            
            # ROI
            roi_item = QTableWidgetItem(f"{opp.roi_percent:.1f}%")
            roi_item.setData(Qt.UserRole, opp.roi_percent)
            self.results_table.setItem(row, 5, roi_item)
            
            # Investment
            investment_item = QTableWidgetItem(f"{opp.investment_per_unit:,.0f}")
            investment_item.setData(Qt.UserRole, opp.investment_per_unit)
            self.results_table.setItem(row, 6, investment_item)
            
            # Risk
            risk_item = QTableWidgetItem(opp.risk_level.title())
            if opp.risk_level == 'low':
                risk_item.setBackground(QColor(200, 255, 200))
            elif opp.risk_level == 'medium':
                risk_item.setBackground(QColor(255, 255, 200))
            else:
                risk_item.setBackground(QColor(255, 200, 200))
            self.results_table.setItem(row, 7, risk_item)
            
            # Updated (time since last price update)
            dt = datetime.utcnow() - timedelta(hours=opp.last_update_age_hours)
            dt = dt.replace(tzinfo=timezone.utc)
            updated_item = QTableWidgetItem(rel_age(dt))
            updated_item.setToolTip(fmt_tooltip(dt))
            self.results_table.setItem(row, 8, updated_item)
        
        # Sort by profit (descending) by default
        self.results_table.sortItems(4, Qt.DescendingOrder)
    
    def on_selection_changed(self):
        """Handle table selection change."""
        selected_rows = set()
        for item in self.results_table.selectedItems():
            selected_rows.add(item.row())
        
        if selected_rows:
            row = min(selected_rows)
            if 0 <= row < len(self.current_opportunities):
                opportunity = self.current_opportunities[row]
                self.show_opportunity_details(opportunity)
        else:
            self.details_text.setPlainText("Select an opportunity to view details.")
    
    def show_opportunity_details(self, opportunity: FlipOpportunity):
        """Show detailed information about an opportunity."""
        details = f"""
Item: {opportunity.item_id} (Quality {opportunity.quality})
Strategy: {opportunity.strategy.title()}
Route: {opportunity.source_city} → {opportunity.destination_city}

Financial Analysis:
• Profit per unit: {opportunity.profit_per_unit:,.0f} silver
• Investment per unit: {opportunity.investment_per_unit:,.0f} silver
• Return on Investment: {opportunity.roi_percent:.1f}%
• Break-even quantity: {getattr(opportunity, 'break_even_qty', 'N/A')}

Risk Assessment:
• Risk level: {opportunity.risk_level.title()}
• Route type: {'PvP zone' if opportunity.risk_level == 'high' else 'Safe zone'}

Market Data:
• Source price: {getattr(opportunity, 'source_price', 'N/A')} silver
• Destination price: {getattr(opportunity, 'destination_price', 'N/A')} silver
• Price difference: {getattr(opportunity, 'price_difference', 'N/A')} silver

Notes:
• Consider market volatility and competition
• Verify current prices before executing trades
• Factor in travel time and carrying capacity
        """.strip()
        
        self.details_text.setPlainText(details)
    
    def clear_results(self):
        """Clear search results."""
        self.current_opportunities = []
        self.results_table.setRowCount(0)
        self.results_label.setText("No search performed")
        self.details_text.setPlainText("Select an opportunity to view details.")
        self.set_status("Results cleared")
    
    def export_results(self):
        """Export results to file."""
        if not self.current_opportunities:
            self.set_status("No results to export")
            return
        
        # This would open a file dialog and export to CSV/Excel
        self.set_status("Export feature not yet implemented")
    
    def refresh_data(self):
        """Refresh data (called from main window)."""
        if self.current_opportunities:
            # Re-run the last search
            self.search_opportunities()
    
    def set_opportunities(self, opportunities: List[FlipOpportunity]):
        """Set opportunities from external source (e.g., dashboard)."""
        self.current_opportunities = opportunities
        self.populate_results_table(opportunities)
        self.results_label.setText(f"Showing {len(opportunities)} opportunities")
    
    def set_status(self, message: str):
        """Set status message."""
        self.status_label.setText(message)
        self.logger.debug(f"Flip finder status: {message}")

