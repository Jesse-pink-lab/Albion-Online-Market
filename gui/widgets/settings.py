"""
Settings widget for Albion Trade Optimizer.

Allows users to configure application settings and preferences.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QCheckBox,
    QComboBox, QGroupBox, QFrame, QDoubleSpinBox,
    QTextEdit, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from utils.pecheck import is_valid_win64_exe


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
        self.create_uploader_settings(layout)
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
        # The base URL is derived from the selected server region and is
        # provided here purely for diagnostics, so keep it read-only.
        self.api_url_edit.setReadOnly(True)
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

        # Max concurrency
        api_layout.addWidget(QLabel("Max Concurrency:"), row, 0)
        self.max_conc_spin = QSpinBox()
        self.max_conc_spin.setRange(1, 8)
        api_layout.addWidget(self.max_conc_spin, row, 1)
        row += 1

        # Global rate
        api_layout.addWidget(QLabel("Global Rate (req/s):"), row, 0)
        self.global_rate_spin = QDoubleSpinBox()
        self.global_rate_spin.setRange(0.5, 5.0)
        self.global_rate_spin.setSingleStep(0.1)
        api_layout.addWidget(self.global_rate_spin, row, 1)
        row += 1

        # Cache TTL
        api_layout.addWidget(QLabel("Cache TTL (seconds):"), row, 0)
        self.cache_ttl_spin = QSpinBox()
        self.cache_ttl_spin.setRange(0, 300)
        api_layout.addWidget(self.cache_ttl_spin, row, 1)
        row += 1
        
        parent_layout.addWidget(api_group)

    def create_uploader_settings(self, parent_layout):
        """Create uploader settings section."""
        uploader_group = QGroupBox("Uploader")
        uploader_layout = QGridLayout(uploader_group)
        row = 0

        self.uploader_enable_check = QCheckBox("Enable uploader")
        uploader_layout.addWidget(self.uploader_enable_check, row, 0, 1, 2)
        row += 1

        uploader_layout.addWidget(QLabel("Interface:"), row, 0)
        self.uploader_interface_edit = QLineEdit()
        uploader_layout.addWidget(self.uploader_interface_edit, row, 1)
        row += 1

        uploader_layout.addWidget(QLabel("Albion Data Client Path:"), row, 0)
        self.albion_client_path_edit = QLineEdit()
        self.albion_client_path_edit.textChanged.connect(self.update_albion_client_status)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_albion_client_path)
        uploader_layout.addWidget(self.albion_client_path_edit, row, 1)
        uploader_layout.addWidget(browse_btn, row, 2)
        row += 1

        self.albion_client_status = QLabel("not validated")
        uploader_layout.addWidget(self.albion_client_status, row, 1, 1, 2)
        row += 1

        program_btn = QPushButton("Use Program Files")
        program_btn.clicked.connect(self.use_program_files)
        uploader_layout.addWidget(program_btn, row, 0)

        bundled_btn = QPushButton("Use Bundled")
        bundled_btn.clicked.connect(self.use_bundled_client)
        uploader_layout.addWidget(bundled_btn, row, 1)

        download_btn = QPushButton("Download Latest")
        download_btn.clicked.connect(self.download_official_client)
        uploader_layout.addWidget(download_btn, row, 2)
        row += 1

        self.uploader_ws_check = QCheckBox("Enable WebSocket")
        uploader_layout.addWidget(self.uploader_ws_check, row, 0, 1, 2)
        row += 1

        uploader_layout.addWidget(QLabel("Ingest Base:"), row, 0)
        self.uploader_ingest_edit = QLineEdit()
        uploader_layout.addWidget(self.uploader_ingest_edit, row, 1)

        parent_layout.addWidget(uploader_group)

    def browse_albion_client_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Albion Data Client",
            "",
            "Executable (*.exe)" if os.name == "nt" else "",
        )
        if path:
            self.albion_client_path_edit.setText(path)
            self.update_albion_client_status()

    def use_bundled_client(self):
        from services.albion_client import ensure_managed_from_embedded

        try:
            path = ensure_managed_from_embedded()
            self.albion_client_path_edit.setText(path)
            self.update_albion_client_status()
            QMessageBox.information(self, "Bundled Client", "Bundled client ready")
        except Exception as e:  # pragma: no cover - GUI warning
            QMessageBox.warning(self, "Bundled Client", str(e))

    def use_program_files(self):
        from services.albion_client import DEFAULT_PROG_FILES

        path = DEFAULT_PROG_FILES
        valid, reason = is_valid_win64_exe(path)
        if valid:
            self.albion_client_path_edit.setText(path)
            self.update_albion_client_status()
        else:
            QMessageBox.warning(self, "Program Files", reason)

    def download_official_client(self):
        from services.albion_client_fetch import fetch_latest_windows_client
        from services.albion_client import managed_client_path

        dest = managed_client_path()
        try:
            data = fetch_latest_windows_client()
            if not data:
                raise RuntimeError("Download failed")
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            Path(dest).write_bytes(data)
            self.albion_client_path_edit.setText(dest)
            self.update_albion_client_status()
            QMessageBox.information(self, "Download", "Download complete")
        except Exception as e:  # pragma: no cover - network path
            QMessageBox.warning(self, "Download failed", str(e))

    def update_albion_client_status(self):
        path = self.albion_client_path_edit.text().strip()
        if not path:
            self.albion_client_status.setText("no path")
            return
        valid, reason = is_valid_win64_exe(path)
        self.albion_client_status.setText("ok" if valid else reason)
        self.logger.info(
            "Albion client path set to %s -> %s", path, "ok" if valid else reason
        )
        self.modified = True
    
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

        # Fetch all items toggle
        trading_layout.addWidget(QLabel("Fetch Scope:"), row, 0)
        self.fetch_all_check = QCheckBox("Fetch all items")
        trading_layout.addWidget(self.fetch_all_check, row, 1)
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

        # City batch size
        app_layout.addWidget(QLabel("City Batch Size:"), row, 0)
        self.city_batch_spin = QSpinBox()
        self.city_batch_spin.setRange(1, 7)
        app_layout.addWidget(self.city_batch_spin, row, 1)
        row += 1

        # Only refresh visible first
        self.visible_first_check = QCheckBox("Only refresh visible pages first")
        app_layout.addWidget(self.visible_first_check, row, 0, 1, 2)
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
            self.max_conc_spin.setValue(self.config.get('max_concurrency', 4))
            self.global_rate_spin.setValue(self.config.get('global_rate_per_sec', 2.0))
            self.cache_ttl_spin.setValue(self.config.get('cache_ttl_sec', 120))

            # Trading settings
            self.premium_check.setChecked(self.config.get('premium_enabled', True))
            
            cities = self.config.get('cities', [])
            self.cities_edit.setText(','.join(cities))
            
            thresholds = self.config.get('thresholds', {})
            self.min_profit_spin.setValue(thresholds.get('min_profit', 1000))
            self.min_roi_spin.setValue(thresholds.get('min_roi_percent', 5.0))

            self.fetch_all_check.setChecked(self.config.get('fetch_all_items', True))
            
            # App settings
            app_config = self.config.get('app', {})
            self.auto_refresh_spin.setValue(app_config.get('auto_refresh_minutes', 0))
            self.city_batch_spin.setValue(self.config.get('city_batch_size', 3))
            self.visible_first_check.setChecked(self.config.get('only_visible_first', True))

            freshness_config = self.config.get('freshness', {})
            self.max_age_spin.setValue(freshness_config.get('max_age_hours', 24))

            logging_config = self.config.get('logging', {})
            # Migration: handle old app.log_level
            if 'log_level' in app_config and 'level' not in logging_config:
                logging_config['level'] = app_config['log_level']
                del app_config['log_level']
            self.log_level_combo.setCurrentText(logging_config.get('level', 'INFO'))

            # Uploader settings
            uploader_cfg = self.main_window.config_manager.get_uploader_config()
            self.uploader_enable_check.setChecked(uploader_cfg.get('enabled', True))
            self.uploader_interface_edit.setText(uploader_cfg.get('interface') or '')
            self.uploader_ws_check.setChecked(uploader_cfg.get('enable_websocket', True))
            self.uploader_ingest_edit.setText(uploader_cfg.get('ingest_base', 'http+pow://albion-online-data.com'))
            self.albion_client_path_edit.setText(self.config.get('albion_client_path', '') or '')
            
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
            config['max_concurrency'] = self.max_conc_spin.value()
            config['global_rate_per_sec'] = self.global_rate_spin.value()
            config['cache_ttl_sec'] = self.cache_ttl_spin.value()
            
            # Trading settings
            config['premium_enabled'] = self.premium_check.isChecked()
            
            cities_text = self.cities_edit.text().strip()
            if cities_text:
                config['cities'] = [city.strip() for city in cities_text.split(',')]
            
            if 'thresholds' not in config:
                config['thresholds'] = {}
            config['thresholds']['min_profit'] = self.min_profit_spin.value()
            config['thresholds']['min_roi_percent'] = self.min_roi_spin.value()
            config['fetch_all_items'] = self.fetch_all_check.isChecked()
            
            # App settings
            if 'app' not in config:
                config['app'] = {}
            config['app']['auto_refresh_minutes'] = self.auto_refresh_spin.value()
            config['city_batch_size'] = self.city_batch_spin.value()
            config['only_visible_first'] = self.visible_first_check.isChecked()
            config['app'].pop('log_level', None)
            if 'logging' not in config:
                config['logging'] = {}
            config['logging']['level'] = self.log_level_combo.currentText()
            
            if 'freshness' not in config:
                config['freshness'] = {}
            config['freshness']['max_age_hours'] = self.max_age_spin.value()

            # Uploader settings
            config['uploader'] = {
                'enabled': self.uploader_enable_check.isChecked(),
                'interface': self.uploader_interface_edit.text() or None,
                'enable_websocket': self.uploader_ws_check.isChecked(),
                'ingest_base': self.uploader_ingest_edit.text() or 'http+pow://albion-online-data.com',
            }
            config['albion_client_path'] = self.albion_client_path_edit.text() or None

            # Save configuration
            self.main_window.config_manager.save_config(config)
            self.config = config
            self.main_window.config = config
            self.modified = False

            self.set_status("Settings saved successfully")

            # Show restart message
            QMessageBox.information(
                self,
                "Settings Saved",
                "Settings have been saved successfully.\n\nSome changes may require restarting the application to take effect."
            )

            if hasattr(self.main_window, 'on_toggle_uploader'):
                self.main_window.on_toggle_uploader(config['uploader']['enabled'])
            
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

