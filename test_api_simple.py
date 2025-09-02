#!/usr/bin/env python3
"""
Simple API test with known working items.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engine.config import ConfigManager
from datasources.aodp import AODPClient


def test_working_items():
    """Test with items we know work."""
    print("Testing AODP API with known working items...")
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    client = AODPClient(config)
    
    # Test with T4_BAG which we know works
    print("  Testing T4_BAG...")
    try:
        prices = client.get_current_prices(['T4_BAG'], ['Caerleon'], [1])
        print(f"  ✓ Retrieved {len(prices)} price records for T4_BAG")
        
        if prices:
            price = prices[0]
            print(f"  Sample: {price['item_id']} in {price['city']} - sell_min: {price['sell_price_min']}, buy_max: {price['buy_price_max']}")
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
    
    # Test with multiple items
    print("  Testing multiple bag items...")
    try:
        prices = client.get_current_prices(['T4_BAG', 'T5_BAG'], ['Caerleon'], [1])
        print(f"  ✓ Retrieved {len(prices)} price records for multiple bags")
        
        for price in prices[:3]:  # Show first 3
            print(f"    {price['item_id']} Q{price['quality']}: {price['sell_price_min']}")
    
    except Exception as e:
        print(f"  ❌ Failed: {e}")
    
    client.close()
    print("✅ Simple API test completed!")


if __name__ == "__main__":
    test_working_items()

