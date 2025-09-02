#!/usr/bin/env python3
"""
Debug test for database operations.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engine.config import ConfigManager
from store.db import DatabaseManager

def debug_database():
    """Debug database operations."""
    print("🔍 Debugging Database Operations")
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        print("✓ Configuration loaded")
        
        # Initialize database
        db_manager = DatabaseManager(config)
        db_manager.initialize_database()
        print("✓ Database initialized")
        
        # Test storing price data
        test_prices = [
            {
                'item_id': 'TEST_ITEM',
                'city': 'Martlock',
                'quality': 1,
                'sell_price_min': 1000,
                'sell_price_max': 1100,
                'buy_price_min': 900,
                'buy_price_max': 950,
                'observed_at_utc': datetime.utcnow()
            }
        ]
        
        print(f"Test data: {test_prices[0]}")
        
        stored_count = db_manager.save_prices(test_prices)
        print(f"✓ Stored {stored_count} price records")
        
        # Test retrieving prices with different parameters
        print("\nTesting retrieval with different parameters:")
        
        # Test 1: Basic retrieval
        retrieved_1 = db_manager.get_recent_prices(['TEST_ITEM'], ['Martlock'])
        print(f"  Basic retrieval: {len(retrieved_1)} records")
        
        # Test 2: With explicit quality
        retrieved_2 = db_manager.get_recent_prices(['TEST_ITEM'], ['Martlock'], quality=1)
        print(f"  With quality=1: {len(retrieved_2)} records")
        
        # Test 3: With longer max age
        retrieved_3 = db_manager.get_recent_prices(['TEST_ITEM'], ['Martlock'], max_age_hours=48, quality=1)
        print(f"  With max_age_hours=48: {len(retrieved_3)} records")
        
        # Test 4: Check what's actually in the database
        stats = db_manager.get_database_stats()
        print(f"  Database stats: {stats}")
        
        # Test 5: Direct query to see all records
        session = db_manager.get_session()
        try:
            from store.models import Price
            all_prices = session.query(Price).all()
            print(f"  All records in database: {len(all_prices)}")
            
            if all_prices:
                price = all_prices[0]
                print(f"    First record: item_id={price.item_id}, city={price.city}, quality={price.quality}")
                print(f"    Observed at: {price.observed_at_utc}")
                
        finally:
            session.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_database()

