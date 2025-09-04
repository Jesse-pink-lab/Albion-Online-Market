#!/usr/bin/env python3
"""
Test script for database functionality.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engine.config import ConfigManager
from store.db import DatabaseManager
from utils.paths import init_app_paths


def test_database():
    """Test database operations."""
    print("Testing Albion Trade Optimizer Database...")
    
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load_config()
    print(f"✓ Configuration loaded")

    init_app_paths()
    # Initialize database
    db_manager = DatabaseManager(config)
    db_manager.initialize_database()
    print(f"✓ Database initialized at {db_manager.db_path}")
    
    # Test saving prices
    test_prices = [
        {
            'item_id': 'T4_SWORD',
            'quality': 1,
            'city': 'Martlock',
            'sell_price_min': 1000,
            'sell_price_max': 1200,
            'buy_price_min': 800,
            'buy_price_max': 950,
            'observed_at_utc': datetime.utcnow()
        },
        {
            'item_id': 'T4_SWORD',
            'quality': 1,
            'city': 'Lymhurst',
            'sell_price_min': 1100,
            'sell_price_max': 1300,
            'buy_price_min': 900,
            'buy_price_max': 1050,
            'observed_at_utc': datetime.utcnow()
        }
    ]
    
    saved_count = db_manager.save_prices(test_prices)
    print(f"✓ Saved {saved_count} price records")
    
    # Test retrieving prices
    prices = db_manager.get_latest_prices(['T4_SWORD'], ['Martlock', 'Lymhurst'])
    print(f"✓ Retrieved {len(prices)} price records")
    
    for price in prices:
        print(f"  - {price.item_id} in {price.city}: sell_min={price.sell_price_min}, buy_max={price.buy_price_max}")
    
    # Test creating scan
    scan = db_manager.create_scan(items_count=1, cities_count=2)
    print(f"✓ Created scan {scan.id}")
    
    # Test saving flips
    test_flips = [
        {
            'item_id': 'T4_SWORD',
            'quality': 1,
            'src_city': 'Martlock',
            'dst_city': 'Lymhurst',
            'strategy': 'fast',
            'profit_per_unit': 50,
            'suggested_qty': 10,
            'expected_profit': 500,
            'risk': 'low',
            'buy_price': 1000,
            'sell_price': 1050,
            'buy_fees': 0,
            'sell_fees': 42
        }
    ]
    
    flips_count = db_manager.save_flips(scan.id, test_flips)
    print(f"✓ Saved {flips_count} flip opportunities")
    
    # Test retrieving flips
    top_flips = db_manager.get_top_flips(scan_id=scan.id)
    print(f"✓ Retrieved {len(top_flips)} flip opportunities")
    
    for flip in top_flips:
        print(f"  - {flip.item_id}: {flip.src_city} -> {flip.dst_city}, profit={flip.profit_per_unit}")
    
    # Test finishing scan
    db_manager.finish_scan(scan.id, status='completed')
    print(f"✓ Finished scan {scan.id}")
    
    # Test settings
    db_manager.set_setting('test_setting', 'test_value', 'Test setting for validation')
    setting_value = db_manager.get_setting('test_setting')
    print(f"✓ Settings test: saved and retrieved '{setting_value}'")
    
    print("\n✅ All database tests passed!")


if __name__ == "__main__":
    test_database()

