"""
Settings widget for Albion Trade Optimizer.

Allows users to configure application settings and preferences.
"""

import logging
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QCheckBox,
    QComboBox, QGroupBox, QFrame, QDoubleSpinBox,
    QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class SettingsWidget(QWidget):
    """Widget for application settings and configuration."""
    
    def __init__(self, main_window):
        """Initialize settings widget."""
        super().__init__()
        
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Settings data
        self.config = main_window.get_config()
        self.modified = False
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create header
        self.create_header(layout)
        
        # Create settings sections
        self.create_api_settings(layout)
        self.create_trading_settings(layout)
        self.create_app_settings(layout)
        
        # Create footer with save/reset buttons
        self.create_footer(layout)
        
        layout.addStretch()
    
    def create_header(self, parent_layout):
        """Create header with title."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("⚙️ Settings")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        parent_layout.addWidget(header_frame)
    
    def create_api_settings(self, parent_layout):
        """Create API settings section."""
        api_group = QGroupBox("API Settings")
        api_layout = QGridLayout(api_group)
        
        row = 0
        
        # API base URL
        api_layout.addWidget(QLabel("API Base URL:"), row, 0)
        self.api_url_edit = QLineEdit()
        api_layout.addWidget(self.api_url_edit, row, 1)
        row += 1
        
        # Rate limiting
        api_layout.addWidget(QLabel("Rate Delay (seconds):"), row, 0)
        self.rate_delay_spin = QDoubleSpinBox()
        self.rate_delay_spin.setRange(0.1, 10.0)
        self.rate_delay_spin.setSingleStep(0.1)
        api_layout.addWidget(self.rate_delay_spin, row, 1)
        row += 1
        
        # Timeout
        api_layout.addWidget(QLabel("Request Timeout (seconds):"), row, 0)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        api_layout.addWidget(self.timeout_spin, row, 1)
        row += 1
        
        # Chunk size
        api_layout.addWidget(QLabel("Items per Request:"), row, 0)
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1, 100)
        api_layout.addWidget(self.chunk_size_spin, row, 1)
        row += 1
        
        parent_layout.addWidget(api_group)
    
    def create_trading_settings(self, parent_layout):
        """Create trading settings section."""
        trading_group = QGroupBox("Trading Settings")
        trading_layout = QGridLayout(trading_group)
        
        row = 0
        
        # Premium status
        trading_layout.addWidget(QLabel("Premium Account:"), row, 0)
        self.premium_check = QCheckBox("I have premium status")
        trading_layout.addWidget(self.premium_check, row, 1)
        row += 1
        
        # Default cities
        trading_layout.addWidget(QLabel("Default Cities:"), row, 0)
        self.cities_edit = QLineEdit()
        self.cities_edit.setPlaceholderText("Martlock,Lymhurst,Bridgewatch,Fort Sterling,Thetford,Caerleon")
        trading_layout.addWidget(self.cities_edit, row, 1)
        row += 1
        
        # Min profit threshold
        trading_layout.addWidget(QLabel("Min Profit Threshold:"), row, 0)
        self.min_profit_spin = QSpinBox()
        self.min_profit_spin.setRange(0, 1000000)
        self.min_profit_spin.setSuffix(" silver")
        trading_layout.addWidget(self.min_profit_spin, row, 1)
        row += 1
        
        # Min ROI threshold
        trading_layout.addWidget(QLabel("Min ROI Threshold:"), row, 0)
        self.min_roi_spin = QDoubleSpinBox()
        self.min_roi_spin.setRange(0, 1000)
        self.min_roi_spin.setSuffix("%")
        trading_layout.addWidget(self.min_roi_spin, row, 1)
        row += 1
        
        parent_layout.addWidget(trading_group)
    
    def create_app_settings(self, parent_layout):
        """Create application settings section."""
        app_group = QGroupBox("Application Settings")
        app_layout = QGridLayout(app_group)
        
        row = 0
        
        # Auto-refresh interval
        app_layout.addWidget(QLabel("Auto-refresh Interval:"), row, 0)
        self.auto_refresh_spin = QSpinBox()
        self.auto_refresh_spin.setRange(0, 1440)  # 0 to 24 hours
        self.auto_refresh_spin.setSuffix(" minutes (0 = disabled)")
        app_layout.addWidget(self.auto_refresh_spin, row, 1)
        row += 1
        
        # Data freshness
        app_layout.addWidget(QLabel("Max Data Age:"), row, 0)
        self.max_age_spin = QSpinBox()
        self.max_age_spin.setRange(1, 168)  # 1 hour to 1 week
        self.max_age_spin.setSuffix(" hours")
        app_layout.addWidget(self.max_age_spin, row, 1)
        row += 1
        
        # Log level
        app_layout.addWidget(QLabel("Log Level:"), row, 0)
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        app_layout.addWidget(self.log_level_combo, row, 1)
        row += 1
        
        parent_layout.addWidget(app_group)
    
    def create_footer(self, parent_layout):
        """Create footer with action buttons."""
        footer_frame = QFrame()
        footer_frame.setFrameStyle(QFrame.StyledPanel)
        footer_layout = QHBoxLayout(footer_frame)
        
        # Status label
        self.status_label = QLabel("Ready")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        # Reset button
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        footer_layout.addWidget(reset_btn)
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_settings)
        footer_layout.addWidget(save_btn)
        
        parent_layout.addWidget(footer_frame)
    
    def load_settings(self):
        """Load settings from configuration."""
        try:
            # API settings
            aodp_config = self.config.get('aodp', {})
            self.api_url_edit.setText(aodp_config.get('base_url', ''))
            self.rate_delay_spin.setValue(aodp_config.get('rate_delay_seconds', 1.0))
            self.timeout_spin.setValue(aodp_config.get('timeout_seconds', 30))
            self.chunk_size_spin.setValue(aodp_config.get('chunk_size', 40))
            
            # Trading settings
            fees_config = self.config.get('fees', {})
            self.premium_check.setChecked(fees_config.get('premium', False))
            
            cities = self.config.get('cities', [])
            self.cities_edit.setText(','.join(cities))
            
            thresholds = self.config.get('thresholds', {})
            self.min_profit_spin.setValue(thresholds.get('min_profit', 1000))
            self.min_roi_spin.setValue(thresholds.get('min_roi_percent', 5.0))
            
            # App settings
            app_config = self.config.get('app', {})
            self.auto_refresh_spin.setValue(app_config.get('auto_refresh_minutes', 0))
            
            freshness_config = self.config.get('freshness', {})
            self.max_age_spin.setValue(freshness_config.get('max_age_hours', 24))
            
            self.log_level_combo.setCurrentText(app_config.get('log_level', 'INFO'))
            
            self.set_status("Settings loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")
            self.set_status(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save settings to configuration."""
        try:
            # Update configuration
            config = self.config.copy()
            
            # API settings
            if 'aodp' not in config:
                config['aodp'] = {}
            config['aodp']['base_url'] = self.api_url_edit.text()
            config['aodp']['rate_delay_seconds'] = self.rate_delay_spin.value()
            config['aodp']['timeout_seconds'] = self.timeout_spin.value()
            config['aodp']['chunk_size'] = self.chunk_size_spin.value()
            
            # Trading settings
            if 'fees' not in config:
                config['fees'] = {}
            config['fees']['premium'] = self.premium_check.isChecked()
            
            cities_text = self.cities_edit.text().strip()
            if cities_text:
                config['cities'] = [city.strip() for city in cities_text.split(',')]
            
            if 'thresholds' not in config:
                config['thresholds'] = {}
            config['thresholds']['min_profit'] = self.min_profit_spin.value()
            config['thresholds']['min_roi_percent'] = self.min_roi_spin.value()
            
            # App settings
            if 'app' not in config:
                config['app'] = {}
            config['app']['auto_refresh_minutes'] = self.auto_refresh_spin.value()
            config['app']['log_level'] = self.log_level_combo.currentText()
            
            if 'freshness' not in config:
                config['freshness'] = {}
            config['freshness']['max_age_hours'] = self.max_age_spin.value()
            
            # Save configuration
            self.main_window.config_manager.save_config(config)
            self.config = config
            self.modified = False
            
            self.set_status("Settings saved successfully")
            
            # Show restart message
            QMessageBox.information(
                self,
                "Settings Saved",
                "Settings have been saved successfully.\n\nSome changes may require restarting the application to take effect."
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            self.set_status(f"Error saving settings: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings:\n{e}"
            )
    
    def reset_to_defaults(self):
        """Reset settings to default values."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Load default configuration
                default_config = self.main_window.config_manager.get_default_config()
                self.config = default_config
                self.load_settings()
                self.modified = True
                self.set_status("Settings reset to defaults")
                
            except Exception as e:
                self.logger.error(f"Failed to reset settings: {e}")
                self.set_status(f"Error resetting settings: {e}")
    
    def refresh_data(self):
        """Refresh data (called from main window)."""
        self.load_settings()
    
    def set_status(self, message: str):
        """Set status message."""
        self.status_label.setText(message)
        self.logger.debug(f"Settings status: {message}")

