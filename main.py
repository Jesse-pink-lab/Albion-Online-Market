#!/usr/bin/env python3
"""
Albion Trade Optimizer - Main Entry Point

A desktop application for optimizing trade and crafting decisions in Albion Online.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logging_config import get_logger

log = get_logger(__name__)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir
from PySide6.QtGui import QIcon

from gui.main_window import MainWindow
from store.db import DatabaseManager
from engine.config import ConfigManager
from utils.paths import init_app_paths


def main() -> int:
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Albion Trade Optimizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Manus AI")

    try:
        init_app_paths()
        config_manager = ConfigManager()
        config = config_manager.load_config()

        log.info("Starting Albion Trade Optimizer")

        db_manager = DatabaseManager(config)
        db_manager.initialize_database()

        main_window = MainWindow(config, db_manager)
        main_window.show()

        log.info("Application started successfully")

        return app.exec()
    except Exception as e:  # pragma: no cover - startup errors
        log.error("Failed to start application: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
