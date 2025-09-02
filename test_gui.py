#!/usr/bin/env python3
"""
Test script for GUI components.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variable to use offscreen rendering for testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

try:
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    
    def test_gui_creation():
        """Test GUI component creation."""
        print("Testing GUI component creation...")
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Albion Trade Optimizer Test")
        
        try:
            # Create main window
            print("  Creating main window...")
            window = MainWindow()
            print("  ✓ Main window created successfully")
            
            # Test basic functionality
            print("  Testing basic functionality...")
            
            # Test configuration access
            config = window.get_config()
            print(f"  ✓ Configuration loaded: {len(config)} sections")
            
            # Test database manager
            db_manager = window.get_db_manager()
            if db_manager:
                print("  ✓ Database manager initialized")
            else:
                print("  ⚠ Database manager not available")
            
            # Test API client
            api_client = window.get_api_client()
            if api_client:
                print("  ✓ API client initialized")
            else:
                print("  ⚠ API client not available")
            
            # Test widget creation
            print("  Testing widget creation...")
            
            # Check if all tabs are created
            tab_count = window.tab_widget.count()
            print(f"  ✓ Created {tab_count} tabs")
            
            # Test tab names
            tab_names = []
            for i in range(tab_count):
                tab_names.append(window.tab_widget.tabText(i))
            print(f"  ✓ Tab names: {tab_names}")
            
            print("✅ GUI creation test passed!")
            return True
            
        except Exception as e:
            print(f"❌ GUI creation test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            app.quit()
    
    if __name__ == "__main__":
        success = test_gui_creation()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("PySide6 may not be installed. Install with: pip install PySide6")
    sys.exit(1)

