#!/usr/bin/env python3
"""
Albion Trade Optimizer - Main Entry Point

A desktop application for optimizing trade and crafting decisions in Albion Online.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir
from PySide6.QtGui import QIcon

from gui.main_window import MainWindow
from store.db import DatabaseManager
from engine.config import ConfigManager


def setup_logging(config):
    """Setup application logging."""
    log_dir = Path(config.get('logging', {}).get('file', 'logs/albion_trade.log')).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.get('logging', {}).get('level', 'INFO')),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.get('logging', {}).get('file', 'logs/albion_trade.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )


def setup_data_directory():
    """Setup application data directory."""
    data_dir = Path('data')
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def main():
    """Main application entry point."""
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Albion Trade Optimizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Manus AI")
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Setup logging
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("Starting Albion Trade Optimizer")
        
        # Setup data directory
        data_dir = setup_data_directory()
        
        # Initialize database
        db_manager = DatabaseManager(config)
        db_manager.initialize_database()
        
        # Create and show main window
        main_window = MainWindow(config, db_manager)
        main_window.show()
        
        logger.info("Application started successfully")
        
        # Run the application
        return app.exec()
        
    except Exception as e:
        logging.error(f"Failed to start application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

