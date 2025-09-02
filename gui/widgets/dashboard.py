"""
Dashboard widget for Albion Trade Optimizer.

Provides an overview of market data, opportunities, and system status.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QScrollArea, QFrame, QProgressBar,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QPalette, QColor

from engine.flips import FlipCalculator
from engine.crafting import CraftingOptimizer
from recipes.loader import RecipeLoader
from core.signals import signals
from utils.timefmt import to_utc, rel_age, fmt_tooltip


class DashboardWidget(QWidget):
    """Dashboard widget showing overview information."""
    
    def __init__(self, main_window):
        """Initialize dashboard widget."""
        super().__init__()
        
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.flip_calculator = None
        self.crafting_optimizer = None
        self.recipe_loader = None
        
        # Data cache
        self.cached_opportunities = []
        self.cached_crafting_plans = []
        self.last_update = None
        
        self.init_ui()
        self.init_backend()
        signals.market_data_ready.connect(self.on_market_data_ready)
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create header
        self.create_header(layout)
        
        # Create main content area
        self.create_main_content(layout)
        
        # Create footer
        self.create_footer(layout)
    
    def create_header(self, parent_layout):
        """Create dashboard header."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("📊 Market Dashboard")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Last update label
        self.last_update_label = QLabel("Last update: Never")
        header_layout.addWidget(self.last_update_label)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.main_window.refresh_data)
        header_layout.addWidget(refresh_btn)
        
        parent_layout.addWidget(header_frame)
    
    def create_main_content(self, parent_layout):
        """Create main dashboard content."""
        # Create scroll area for main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Main content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # Create summary cards
        self.create_summary_cards(content_layout)
        
        # Create opportunities section
        self.create_opportunities_section(content_layout)
        
        # Create market trends section
        self.create_market_trends_section(content_layout)
        
        scroll_area.setWidget(content_widget)
        parent_layout.addWidget(scroll_area)
    
    def create_summary_cards(self, parent_layout):
        """Create summary information cards."""
        cards_frame = QFrame()
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setSpacing(10)
        
        # Best flip opportunity card
        self.flip_card = self.create_summary_card(
            "💰 Best Flip",
            "No data",
            "Loading...",
            QColor(46, 125, 50)  # Green
        )
        cards_layout.addWidget(self.flip_card, 0, 0)
        
        # Best crafting opportunity card
        self.crafting_card = self.create_summary_card(
            "🔨 Best Craft",
            "No data",
            "Loading...",
            QColor(25, 118, 210)  # Blue
        )
        cards_layout.addWidget(self.crafting_card, 0, 1)
        
        # Market activity card
        self.activity_card = self.create_summary_card(
            "📈 Market Activity",
            "No data",
            "Loading...",
            QColor(156, 39, 176)  # Purple
        )
        cards_layout.addWidget(self.activity_card, 0, 2)
        
        # Data freshness card
        self.freshness_card = self.create_summary_card(
            "🕒 Data Age",
            "No data",
            "Loading...",
            QColor(255, 152, 0)  # Orange
        )
        cards_layout.addWidget(self.freshness_card, 0, 3)
        
        parent_layout.addWidget(cards_frame)
    
    def create_summary_card(self, title: str, value: str, subtitle: str, color: QColor) -> QGroupBox:
        """Create a summary card widget."""
        card = QGroupBox()
        card.setFixedHeight(120)
        card.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {color.name()};
                border-radius: 8px;
                margin-top: 10px;
                background-color: rgba({color.red()}, {color.green()}, {color.blue()}, 0.1);
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 15, 10, 10)
        
        # Title
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(14)
        value_font.setBold(True)
        value_label.setFont(value_font)
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        # Subtitle
        subtitle_label = QLabel(subtitle)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: gray;")
        layout.addWidget(subtitle_label)
        
        # Store labels for updates
        card.value_label = value_label
        card.subtitle_label = subtitle_label
        
        return card

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def on_market_data_ready(self, summary: Dict[str, Any]) -> None:
        """Update dashboard cards when new market data arrives."""

        # Stop loading subtitles
        for card in [self.flip_card, self.crafting_card, self.activity_card, self.freshness_card]:
            if card.subtitle_label.text() == "Loading...":
                card.subtitle_label.setText("")

        best_flip = summary.get("best_flip")
        if best_flip:
            self.flip_card.value_label.setText(str(best_flip))
        else:
            self.flip_card.value_label.setText("No data")

        best_craft = summary.get("best_craft")
        if best_craft:
            self.crafting_card.value_label.setText(str(best_craft))
        else:
            self.crafting_card.value_label.setText("No data")

        activity = summary.get("activity")
        if activity:
            self.activity_card.value_label.setText(str(activity))
        else:
            self.activity_card.value_label.setText("No data")

        last_update = summary.get("last_update_utc")
        if last_update:
            dt = to_utc(last_update)
            self.last_update_label.setText(f"Last update: {rel_age(dt)}")
            self.last_update_label.setToolTip(fmt_tooltip(dt))

    
    def create_opportunities_section(self, parent_layout):
        """Create opportunities overview section."""
        opportunities_group = QGroupBox("🎯 Top Opportunities")
        opportunities_layout = QVBoxLayout(opportunities_group)
        
        # Create opportunities table
        self.opportunities_table = QTableWidget()
        self.opportunities_table.setColumnCount(6)
        self.opportunities_table.setHorizontalHeaderLabels([
            "Type", "Item", "Route", "Profit", "ROI %", "Risk"
        ])
        
        # Configure table
        header = self.opportunities_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.opportunities_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.opportunities_table.setAlternatingRowColors(True)
        self.opportunities_table.setMaximumHeight(200)
        
        opportunities_layout.addWidget(self.opportunities_table)
        
        # Add "View All" button
        view_all_btn = QPushButton("View All Opportunities")
        view_all_btn.clicked.connect(self.view_all_opportunities)
        opportunities_layout.addWidget(view_all_btn)
        
        parent_layout.addWidget(opportunities_group)
    
    def create_market_trends_section(self, parent_layout):
        """Create market trends section."""
        trends_group = QGroupBox("📊 Market Trends")
        trends_layout = QVBoxLayout(trends_group)
        
        # Placeholder for market trends
        trends_label = QLabel("Market trends visualization will be implemented here.")
        trends_label.setAlignment(Qt.AlignCenter)
        trends_label.setStyleSheet("color: gray; font-style: italic;")
        trends_layout.addWidget(trends_label)
        
        parent_layout.addWidget(trends_group)
    
    def create_footer(self, parent_layout):
        """Create dashboard footer."""
        footer_frame = QFrame()
        footer_frame.setFrameStyle(QFrame.StyledPanel)
        footer_layout = QHBoxLayout(footer_frame)
        
        # Status information
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
            
            # Initialize flip calculator
            self.flip_calculator = FlipCalculator(config)
            
            # Initialize recipe loader and crafting optimizer
            self.recipe_loader = RecipeLoader()
            recipes = self.recipe_loader.load_recipes()
            
            if recipes:
                self.crafting_optimizer = CraftingOptimizer(config, self.recipe_loader)
                self.logger.info("Backend components initialized successfully")
            else:
                self.logger.warning("No recipes loaded, crafting optimizer disabled")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backend: {e}")
    
    def refresh_data(self):
        """Refresh dashboard data."""
        self.set_status("Refreshing dashboard data...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        try:
            # Get fresh market data
            api_client = self.main_window.get_api_client()
            if not api_client:
                raise Exception("API client not available")
            
            # Get sample data for dashboard
            sample_items = ['T4_BAG', 'T5_BAG', 'T4_SWORD', 'T5_SWORD']
            sample_cities = ['Caerleon', 'Martlock', 'Lymhurst']
            
            prices = api_client.get_current_prices(sample_items, sample_cities, [1])
            
            if prices:
                # Update opportunities
                self.update_opportunities(prices)
                
                # Update summary cards
                self.update_summary_cards(prices)
                
                # Update last update time
                self.last_update = datetime.now()
                self.last_update_label.setText(f"Last update: {self.last_update.strftime('%H:%M:%S')}")
                
                self.set_status("Dashboard updated successfully")
            else:
                self.set_status("No market data available")
            
        except Exception as e:
            self.logger.error(f"Dashboard refresh failed: {e}")
            self.set_status(f"Refresh failed: {e}")
        
        finally:
            self.progress_bar.setVisible(False)
    
    def update_opportunities(self, prices: List[Dict[str, Any]]):
        """Update opportunities table."""
        try:
            if not self.flip_calculator:
                return
            
            # Group prices by item
            prices_by_item = {}
            for price in prices:
                item_id = price['item_id']
                if item_id not in prices_by_item:
                    prices_by_item[item_id] = []
                prices_by_item[item_id].append(price)
            
            # Calculate flip opportunities
            opportunities = self.flip_calculator.calculate_flip_opportunities(prices_by_item)
            
            # Sort by profit and take top 10
            opportunities.sort(key=lambda x: x.profit_per_unit, reverse=True)
            top_opportunities = opportunities[:10]
            
            # Update table
            self.opportunities_table.setRowCount(len(top_opportunities))
            
            for row, opp in enumerate(top_opportunities):
                # Type
                type_item = QTableWidgetItem("Flip")
                self.opportunities_table.setItem(row, 0, type_item)
                
                # Item
                item_item = QTableWidgetItem(opp.item_id)
                self.opportunities_table.setItem(row, 1, item_item)
                
                # Route
                route_item = QTableWidgetItem(f"{opp.source_city} → {opp.destination_city}")
                self.opportunities_table.setItem(row, 2, route_item)
                
                # Profit
                profit_item = QTableWidgetItem(f"{opp.profit_per_unit:,.0f}")
                self.opportunities_table.setItem(row, 3, profit_item)
                
                # ROI
                roi_item = QTableWidgetItem(f"{opp.roi_percent:.1f}%")
                self.opportunities_table.setItem(row, 4, roi_item)
                
                # Risk
                risk_item = QTableWidgetItem(opp.risk_level.title())
                if opp.risk_level == 'low':
                    risk_item.setBackground(QColor(200, 255, 200))
                elif opp.risk_level == 'medium':
                    risk_item.setBackground(QColor(255, 255, 200))
                else:
                    risk_item.setBackground(QColor(255, 200, 200))
                self.opportunities_table.setItem(row, 5, risk_item)
            
            self.cached_opportunities = top_opportunities
            
        except Exception as e:
            self.logger.error(f"Failed to update opportunities: {e}")
    
    def update_summary_cards(self, prices: List[Dict[str, Any]]):
        """Update summary cards with latest data."""
        try:
            # Best flip opportunity
            if self.cached_opportunities:
                best_flip = self.cached_opportunities[0]
                self.flip_card.value_label.setText(f"{best_flip.profit_per_unit:,.0f}")
                self.flip_card.subtitle_label.setText(f"{best_flip.item_id} ({best_flip.roi_percent:.1f}% ROI)")
            else:
                self.flip_card.value_label.setText("No data")
                self.flip_card.subtitle_label.setText("No opportunities found")
            
            # Market activity (number of recent price updates)
            recent_prices = [p for p in prices if 
                           (datetime.utcnow() - p['observed_at_utc']).total_seconds() < 3600]
            self.activity_card.value_label.setText(str(len(recent_prices)))
            self.activity_card.subtitle_label.setText(f"Updates in last hour")
            
            # Data freshness
            if prices:
                latest_price = max(prices, key=lambda x: x['observed_at_utc'])
                age_hours = (datetime.utcnow() - latest_price['observed_at_utc']).total_seconds() / 3600
                self.freshness_card.value_label.setText(f"{age_hours:.1f}h")
                self.freshness_card.subtitle_label.setText("Latest data age")
            else:
                self.freshness_card.value_label.setText("No data")
                self.freshness_card.subtitle_label.setText("No price data")
            
            # Crafting opportunities (placeholder)
            self.crafting_card.value_label.setText("Coming soon")
            self.crafting_card.subtitle_label.setText("Crafting analysis")
            
        except Exception as e:
            self.logger.error(f"Failed to update summary cards: {e}")
    
    def view_all_opportunities(self):
        """Switch to flip finder tab to view all opportunities."""
        main_window = self.main_window
        flip_finder_widget = main_window.flip_finder_widget
        main_window.tab_widget.setCurrentWidget(flip_finder_widget)
        
        # Trigger refresh in flip finder if it has cached data
        if hasattr(flip_finder_widget, 'set_opportunities') and self.cached_opportunities:
            flip_finder_widget.set_opportunities(self.cached_opportunities)
    
    def set_status(self, message: str):
        """Set status message."""
        self.status_label.setText(message)
        self.logger.debug(f"Dashboard status: {message}")
    
    def clear_cache(self):
        """Clear cached data."""
        self.cached_opportunities = []
        self.cached_crafting_plans = []
        self.last_update = None
        
        # Clear table
        self.opportunities_table.setRowCount(0)
        
        # Reset summary cards
        for card in [self.flip_card, self.crafting_card, self.activity_card, self.freshness_card]:
            card.value_label.setText("No data")
            card.subtitle_label.setText("Loading...")
        
        self.last_update_label.setText("Last update: Never")
        self.set_status("Cache cleared")

