"""
Main window for Albion Trade Optimizer.

Provides the primary user interface for the application.
"""

import sys
import logging
import os
import webbrowser
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QMenuBar, QStatusBar, QToolBar, QSplitter,
    QLabel, QPushButton, QProgressBar, QMessageBox, QSystemTrayIcon
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSettings
from PySide6.QtGui import QAction, QIcon, QPixmap

# Import custom widgets
from gui.widgets.dashboard import DashboardWidget
from gui.widgets.flip_finder import FlipFinderWidget
from gui.widgets.crafting_optimizer import CraftingOptimizerWidget
from gui.widgets.settings import SettingsWidget
from gui.widgets.data_manager import DataManagerWidget
from gui.widgets.market_prices import MarketPricesWidget

# Import backend components
from engine.config import ConfigManager
from datasources.aodp import AODPClient
from store.db import DatabaseManager
from services.albion_client import (
    find_client,
    launch_client_with_fallback,
    capture_subproc_version,
)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, db_manager: Optional[DatabaseManager] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        self.config = config or self.config_manager.load_config()
        self.db_manager = db_manager or DatabaseManager(self.config)
        self.api_client = None
        self.settings = QSettings('AlbionTradeOptimizer', 'AlbionTradeOptimizer')
        self.albion_proc: Optional[subprocess.Popen] = None
        self.init_ui(); self.init_menu_bar(); self.init_tool_bar()
        self.init_status_bar(); self.init_system_tray()
        self.init_backend(); self.restore_window_state(); self.init_timers()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Albion Trade Optimizer")
        self.setMinimumSize(1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget for main content
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create and add tabs
        self.create_tabs()
    
    def create_tabs(self):
        """Create and configure all tabs."""
        # Dashboard tab
        self.dashboard_widget = DashboardWidget(self)
        self.tab_widget.addTab(self.dashboard_widget, "📊 Dashboard")
        
        # Flip Finder tab
        self.flip_finder_widget = FlipFinderWidget(self)
        self.tab_widget.addTab(self.flip_finder_widget, "💰 Flip Finder")

        # Crafting Optimizer tab
        self.crafting_optimizer_widget = CraftingOptimizerWidget(self)
        self.tab_widget.addTab(self.crafting_optimizer_widget, "🔨 Crafting")

        # Data Manager tab
        self.data_manager_widget = DataManagerWidget(self)
        self.tab_widget.addTab(self.data_manager_widget, "📡 Data")

        # Market Prices tab
        self.market_prices_widget = MarketPricesWidget(self)
        self.tab_widget.addTab(self.market_prices_widget, "💹 Prices")
        
        # Settings tab
        self.settings_widget = SettingsWidget(self)
        self.tab_widget.addTab(self.settings_widget, "⚙️ Settings")
    
    def init_menu_bar(self):
        """Initialize the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        # Export data action
        export_action = QAction('&Export Data...', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        # Import data action
        import_action = QAction('&Import Data...', self)
        import_action.setShortcut('Ctrl+I')
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('&Tools')
        
        # Refresh data action
        refresh_action = QAction('&Refresh Data', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_data)
        tools_menu.addAction(refresh_action)
        
        # Clear cache action
        clear_cache_action = QAction('&Clear Cache', self)
        clear_cache_action.triggered.connect(self.clear_cache)
        tools_menu.addAction(clear_cache_action)
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        # About action
        about_action = QAction('&About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_tool_bar(self):
        """Initialize the tool bar."""
        toolbar = self.addToolBar('Main')
        toolbar.setMovable(False)
        
        # Refresh button
        refresh_action = QAction('🔄 Refresh', self)
        refresh_action.setToolTip('Refresh market data (F5)')
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Quick search button
        search_action = QAction('🔍 Search', self)
        search_action.setToolTip('Quick item search')
        search_action.triggered.connect(self.show_quick_search)
        toolbar.addAction(search_action)
        
        toolbar.addSeparator()
        
        # Settings button
        settings_action = QAction('⚙️ Settings', self)
        settings_action.setToolTip('Open settings')
        settings_action.triggered.connect(lambda: self.tab_widget.setCurrentWidget(self.settings_widget))
        toolbar.addAction(settings_action)
    
    def init_status_bar(self):
        """Initialize the status bar."""
        self.status_bar = self.statusBar()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Connection status
        self.connection_label = QLabel("🔴 Disconnected")
        self.status_bar.addPermanentWidget(self.connection_label)
    
    def init_system_tray(self):
        """Initialize system tray icon."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # Create tray icon (use a simple colored square for now)
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.blue)
            self.tray_icon.setIcon(QIcon(pixmap))
            
            self.tray_icon.setToolTip("Albion Trade Optimizer")
            self.tray_icon.show()
    
    def init_backend(self):
        """Initialize backend components."""
        try:
            # Initialize database
            self.db_manager.initialize_database()
            self.logger.info("Database initialized")
            
            # Initialize API client
            self.api_client = AODPClient(self.config)
            self.logger.info("API client initialized")
            
            # Test API connection
            self.test_api_connection()

            client_path = find_client(
                self.config.get('albion_client_path'),
                ask_download=self._prompt_download_client,
            )
            if not client_path:
                self.logger.error("Albion Data Client not found or invalid. Install the 64-bit client under 'C:\\Program Files\\Albion Data Client\\' or set a valid path in Settings.")
            else:
                try:
                    flags = list(self.config.get("client", {}).get("flags", []))
                    self.albion_proc = launch_client_with_fallback(
                        client_path, flags
                    )
                    capture_subproc_version(client_path)
                except Exception as e:
                    self.logger.exception("Failed to initialize backend components: %s", e)

        except Exception as e:
            self.logger.error(f"Failed to initialize backend: {e}")
            self.show_error("Backend Initialization Error",
                          f"Failed to initialize backend components:\n{e}")
    
    def init_timers(self):
        """Initialize periodic timers."""
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_data)
        
        # Start auto-refresh if enabled
        auto_refresh_minutes = self.config.get('app', {}).get('auto_refresh_minutes', 0)
        if auto_refresh_minutes > 0:
            self.refresh_timer.start(auto_refresh_minutes * 60 * 1000)
            self.logger.info(f"Auto-refresh enabled: every {auto_refresh_minutes} minutes")
    
    def test_api_connection(self):
        """Test API connection and update status."""
        try:
            if self.api_client and self.api_client.test_connection():
                self.connection_label.setText("🟢 Connected")
                self.connection_label.setToolTip("API connection active")
                self.logger.info("API connection test successful")
            else:
                self.connection_label.setText("🟡 Limited")
                self.connection_label.setToolTip("API connection issues")
                self.logger.warning("API connection test failed")

        except Exception as e:
            self.connection_label.setText("🔴 Disconnected")
            self.connection_label.setToolTip(f"API connection error: {e}")
            self.logger.error(f"API connection test error: {e}")

    def _prompt_download_client(self) -> bool:
        reply = QMessageBox.question(
            self,
            "Albion Data Client",
            "Download the official Windows client now?",
            QMessageBox.Yes | QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def on_toggle_uploader(self, enabled: bool):
        if enabled:
            client_path = find_client(
                self.config.get('albion_client_path'),
                ask_download=self._prompt_download_client,
            )
            if not client_path:
                self.logger.error("Albion Data Client not found or invalid. Install the 64-bit client under 'C:\\Program Files\\Albion Data Client\\' or set a valid path in Settings.")
                return
            try:
                flags = list(self.config.get("client", {}).get("flags", []))
                self.albion_proc = launch_client_with_fallback(client_path, flags)
            except Exception as e:
                self.logger.exception("Failed to launch Albion Data Client: %s", e)
        else:
            if self.albion_proc and self.albion_proc.poll() is None:
                try:
                    self.albion_proc.terminate()
                except Exception:
                    pass
                self.albion_proc = None
    
    def refresh_data(self):
        """Refresh market data."""
        self.set_status("Refreshing market data...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        try:
            # Trigger refresh in all widgets
            self.dashboard_widget.refresh_data()
            self.flip_finder_widget.refresh_data()
            self.crafting_optimizer_widget.refresh_data()
            self.data_manager_widget.refresh_data()
            
            self.set_status("Data refreshed successfully")
            
        except Exception as e:
            self.logger.error(f"Data refresh failed: {e}")
            self.show_error("Refresh Error", f"Failed to refresh data:\n{e}")
            self.set_status("Data refresh failed")
        
        finally:
            self.progress_bar.setVisible(False)
    
    def auto_refresh_data(self):
        """Automatically refresh data (called by timer)."""
        self.logger.info("Auto-refreshing data")
        self.refresh_data()
    
    def clear_cache(self):
        """Clear cached data."""
        try:
            # Clear database cache
            self.db_manager.clear_cache()
            
            # Clear any in-memory caches
            if hasattr(self.dashboard_widget, 'clear_cache'):
                self.dashboard_widget.clear_cache()
            
            self.set_status("Cache cleared")
            self.logger.info("Cache cleared successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            self.show_error("Cache Error", f"Failed to clear cache:\n{e}")
    
    def export_data(self):
        """Export data to file."""
        # This will be implemented by the data manager widget
        self.tab_widget.setCurrentWidget(self.data_manager_widget)
        self.data_manager_widget.export_data()
    
    def import_data(self):
        """Import data from file."""
        # This will be implemented by the data manager widget
        self.tab_widget.setCurrentWidget(self.data_manager_widget)
        self.data_manager_widget.import_data()
    
    def show_quick_search(self):
        """Show quick search dialog."""
        # This will be implemented later
        self.show_info("Quick Search", "Quick search feature coming soon!")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """
        <h2>Albion Trade Optimizer</h2>
        <p>Version 1.0.0</p>
        <p>A desktop application for optimizing trade and crafting decisions in Albion Online.</p>
        <p><b>Features:</b></p>
        <ul>
        <li>Real-time market price analysis</li>
        <li>Flip opportunity detection</li>
        <li>Crafting profit optimization</li>
        <li>Risk assessment for trade routes</li>
        </ul>
        <p><b>Data Source:</b> Albion Online Data Project (AODP)</p>
        <p>© 2025 Albion Trade Optimizer</p>
        """
        
        QMessageBox.about(self, "About Albion Trade Optimizer", about_text)
    
    def set_status(self, message: str):
        """Set status bar message."""
        self.status_label.setText(message)
        self.logger.debug(f"Status: {message}")
    
    def show_error(self, title: str, message: str):
        """Show error message dialog."""
        QMessageBox.critical(self, title, message)
    
    def show_warning(self, title: str, message: str):
        """Show warning message dialog."""
        QMessageBox.warning(self, title, message)
    
    def show_info(self, title: str, message: str):
        """Show information message dialog."""
        QMessageBox.information(self, title, message)
    
    def get_config(self) -> Dict[str, Any]:
        """Get application configuration."""
        return self.config
    
    def get_db_manager(self) -> DatabaseManager:
        """Get database manager."""
        return self.db_manager
    
    def get_api_client(self) -> Optional[AODPClient]:
        """Get API client."""
        return self.api_client
    
    def save_window_state(self):
        """Save window state to settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("currentTab", self.tab_widget.currentIndex())
    
    def restore_window_state(self):
        """Restore window state from settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
        
        current_tab = self.settings.value("currentTab", 0, type=int)
        if 0 <= current_tab < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(current_tab)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save window state
        self.save_window_state()
        
        # Clean up resources
        if self.api_client:
            self.api_client.close()
        
        if self.db_manager:
            self.db_manager.close()

        # Stop timers
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()

        if getattr(self, 'albion_proc', None):
            try:
                if self.albion_proc.poll() is None:
                    self.albion_proc.terminate()
            except Exception:
                pass

        self.logger.info("Application closing")
        event.accept()


def main():
    """Main entry point for the GUI application."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Albion Trade Optimizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Albion Trade Optimizer")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

