"""
Data Manager widget for Albion Trade Optimizer.

Manages data sources, caching, and import/export functionality.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QFrame, QTextEdit,
    QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from core.signals import signals
from utils.timefmt import fmt_tooltip


class DataManagerWidget(QWidget):
    """Widget for managing data sources and operations."""
    
    def __init__(self, main_window):
        """Initialize data manager widget."""
        super().__init__()
        
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Data status
        self.last_update = None
        self.data_stats = {}
        
        self.init_ui()
        self.init_timer()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create header
        self.create_header(layout)
        
        # Create data status section
        self.create_data_status_section(layout)
        
        # Create data operations section
        self.create_data_operations_section(layout)
        
        # Create data sources section
        self.create_data_sources_section(layout)
        
        # Create footer
        self.create_footer(layout)
    
    def create_header(self, parent_layout):
        """Create header with title."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("📡 Data Manager")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Status")
        refresh_btn.clicked.connect(self.refresh_status)
        header_layout.addWidget(refresh_btn)
        
        parent_layout.addWidget(header_frame)
    
    def create_data_status_section(self, parent_layout):
        """Create data status overview section."""
        status_group = QGroupBox("Data Status")
        status_layout = QGridLayout(status_group)
        
        # Status cards
        self.create_status_cards(status_layout)
        
        parent_layout.addWidget(status_group)
    
    def create_status_cards(self, parent_layout):
        """Create status information cards."""
        # API Status card
        self.api_status_card = self.create_status_card(
            "🌐 API Status",
            "Checking...",
            "AODP Connection",
            QColor(25, 118, 210)
        )
        parent_layout.addWidget(self.api_status_card, 0, 0)
        
        # Database Status card
        self.db_status_card = self.create_status_card(
            "💾 Database",
            "Checking...",
            "Local Storage",
            QColor(46, 125, 50)
        )
        parent_layout.addWidget(self.db_status_card, 0, 1)
        
        # Data Freshness card
        self.freshness_card = self.create_status_card(
            "🕒 Data Age",
            "Unknown",
            "Last Update",
            QColor(255, 152, 0)
        )
        parent_layout.addWidget(self.freshness_card, 0, 2)
        
        # Cache Size card
        self.cache_card = self.create_status_card(
            "📊 Cache Size",
            "Unknown",
            "Stored Records",
            QColor(156, 39, 176)
        )
        parent_layout.addWidget(self.cache_card, 0, 3)
    
    def create_status_card(self, title: str, value: str, subtitle: str, color: QColor) -> QGroupBox:
        """Create a status card widget."""
        card = QGroupBox()
        card.setFixedHeight(100)
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
        value_font.setPointSize(12)
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
    
    def create_data_operations_section(self, parent_layout):
        """Create data operations section."""
        operations_group = QGroupBox("Data Operations")
        operations_layout = QGridLayout(operations_group)
        
        row = 0
        
        # Refresh data button
        refresh_data_btn = QPushButton("🔄 Refresh Market Data")
        refresh_data_btn.setToolTip("Fetch latest market prices from API")
        refresh_data_btn.clicked.connect(self.refresh_market_data)
        operations_layout.addWidget(refresh_data_btn, row, 0)
        
        # Clear cache button
        clear_cache_btn = QPushButton("🗑️ Clear Cache")
        clear_cache_btn.setToolTip("Clear all cached market data")
        clear_cache_btn.clicked.connect(self.clear_cache)
        operations_layout.addWidget(clear_cache_btn, row, 1)
        row += 1
        
        # Export data button
        export_btn = QPushButton("📤 Export Data")
        export_btn.setToolTip("Export market data to file")
        export_btn.clicked.connect(self.export_data)
        operations_layout.addWidget(export_btn, row, 0)
        
        # Import data button
        import_btn = QPushButton("📥 Import Data")
        import_btn.setToolTip("Import market data from file")
        import_btn.clicked.connect(self.import_data)
        operations_layout.addWidget(import_btn, row, 1)
        row += 1
        
        parent_layout.addWidget(operations_group)
    
    def create_data_sources_section(self, parent_layout):
        """Create data sources information section."""
        sources_group = QGroupBox("Data Sources")
        sources_layout = QVBoxLayout(sources_group)
        
        # Data sources table
        self.sources_table = QTableWidget()
        self.sources_table.setColumnCount(4)
        self.sources_table.setHorizontalHeaderLabels([
            "Source", "Status", "Last Update", "Records"
        ])
        
        # Configure table
        header = self.sources_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.sources_table.setMaximumHeight(150)
        
        sources_layout.addWidget(self.sources_table)
        
        parent_layout.addWidget(sources_group)
    
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
    
    def init_timer(self):
        """Initialize status update timer."""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(30000)  # Update every 30 seconds

        # Initial status update
        signals.health_changed.connect(self.on_health_changed)
        self.update_status()
    
    def update_status(self):
        """Update data status information."""
        try:
            # Check API status
            api_client = self.main_window.get_api_client()
            if api_client:
                api_client.get_server_status()
            else:
                self.api_status_card.value_label.setText("❌ N/A")
                self.api_status_card.subtitle_label.setText("Not Initialized")
            
            # Check database status
            db_manager = self.main_window.get_db_manager()
            if db_manager:
                try:
                    # Try to get some basic stats
                    stats = db_manager.get_database_stats()
                    self.db_status_card.value_label.setText("🟢 Ready")
                    self.db_status_card.subtitle_label.setText(f"{stats.get('total_records', 0)} records")
                    
                    # Update cache card
                    self.cache_card.value_label.setText(f"{stats.get('total_records', 0):,}")
                    self.cache_card.subtitle_label.setText("Price Records")
                    
                except Exception:
                    self.db_status_card.value_label.setText("🟡 Limited")
                    self.db_status_card.subtitle_label.setText("Access Issues")
            else:
                self.db_status_card.value_label.setText("❌ N/A")
                self.db_status_card.subtitle_label.setText("Not Initialized")
            
            # Update data freshness
            if self.last_update:
                age = datetime.now() - self.last_update
                hours = age.total_seconds() / 3600
                self.freshness_card.value_label.setText(f"{hours:.1f}h")
                self.freshness_card.subtitle_label.setText("Since Last Update")
            else:
                self.freshness_card.value_label.setText("Never")
                self.freshness_card.subtitle_label.setText("No Updates")
            
            # Update data sources table
            self.update_sources_table()
            
        except Exception as e:
            self.logger.error(f"Failed to update status: {e}")

    def on_health_changed(self, store) -> None:
        if store.aodp_online:
            self.api_status_card.value_label.setText("🟢 Online")
            if store.last_checked:
                self.api_status_card.subtitle_label.setText(fmt_tooltip(store.last_checked))
        else:
            self.api_status_card.value_label.setText("🔴 Offline")
            self.api_status_card.subtitle_label.setText("Connection Error")
    
    def update_sources_table(self):
        """Update data sources table."""
        try:
            sources = [
                {
                    'name': 'AODP API',
                    'status': '🟢 Active' if self.main_window.get_api_client() else '🔴 Inactive',
                    'last_update': self.last_update.strftime('%H:%M:%S') if self.last_update else 'Never',
                    'records': 'Real-time'
                },
                {
                    'name': 'Local Database',
                    'status': '🟢 Ready' if self.main_window.get_db_manager() else '🔴 Error',
                    'last_update': 'Continuous',
                    'records': f"{self.data_stats.get('total_records', 0):,}"
                },
                {
                    'name': 'Recipe Data',
                    'status': '🟢 Loaded',
                    'last_update': 'Static',
                    'records': f"{self.data_stats.get('recipe_count', 9):,}"
                }
            ]
            
            self.sources_table.setRowCount(len(sources))
            
            for row, source in enumerate(sources):
                self.sources_table.setItem(row, 0, QTableWidgetItem(source['name']))
                self.sources_table.setItem(row, 1, QTableWidgetItem(source['status']))
                self.sources_table.setItem(row, 2, QTableWidgetItem(source['last_update']))
                self.sources_table.setItem(row, 3, QTableWidgetItem(source['records']))
            
        except Exception as e:
            self.logger.error(f"Failed to update sources table: {e}")
    
    def refresh_status(self):
        """Manually refresh status."""
        self.set_status("Refreshing status...")
        self.update_status()
        self.set_status("Status refreshed")
    
    def refresh_market_data(self):
        """Refresh market data from API."""
        self.set_status("Refreshing market data...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        try:
            # Trigger refresh in main window
            self.main_window.refresh_data()
            self.last_update = datetime.now()
            self.set_status("Market data refreshed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh market data: {e}")
            self.set_status(f"Refresh failed: {e}")
        
        finally:
            self.progress_bar.setVisible(False)
    
    def clear_cache(self):
        """Clear cached data."""
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "Are you sure you want to clear all cached market data?\n\nThis will remove all stored price information.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Clear database cache
                db_manager = self.main_window.get_db_manager()
                if db_manager:
                    db_manager.clear_cache()
                
                # Clear application cache
                self.main_window.clear_cache()
                
                self.last_update = None
                self.data_stats = {}
                self.set_status("Cache cleared successfully")
                self.update_status()
                
            except Exception as e:
                self.logger.error(f"Failed to clear cache: {e}")
                self.set_status(f"Clear cache failed: {e}")
                QMessageBox.critical(
                    self,
                    "Clear Cache Error",
                    f"Failed to clear cache:\n{e}"
                )
    
    def export_data(self):
        """Export data to file."""
        # Placeholder for export functionality
        QMessageBox.information(
            self,
            "Export Data",
            "Data export functionality will be implemented in a future version.\n\nThis will allow you to export market data to CSV, JSON, or Excel formats."
        )
        self.set_status("Export feature coming soon")
    
    def import_data(self):
        """Import data from file."""
        # Placeholder for import functionality
        QMessageBox.information(
            self,
            "Import Data",
            "Data import functionality will be implemented in a future version.\n\nThis will allow you to import market data from CSV, JSON, or Excel files."
        )
        self.set_status("Import feature coming soon")
    
    def refresh_data(self):
        """Refresh data (called from main window)."""
        self.refresh_market_data()
    
    def set_status(self, message: str):
        """Set status message."""
        self.status_label.setText(message)
        self.logger.debug(f"Data manager status: {message}")

