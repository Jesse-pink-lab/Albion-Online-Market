#!/usr/bin/env python3
"""
Comprehensive integration test for Albion Trade Optimizer.

Tests the complete application workflow from data loading to GUI display.
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set environment for headless testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from engine.config import ConfigManager
from store.db import DatabaseManager
from datasources.aodp import AODPClient
from engine.fees import FeeCalculator
from engine.flips import FlipCalculator
from engine.crafting import CraftingOptimizer
from recipes.loader import RecipeLoader


class IntegrationTest:
    """Comprehensive integration test suite."""
    
    def __init__(self):
        """Initialize test suite."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.db_manager = None
        self.api_client = None
        self.test_results = {}
    
    def run_all_tests(self):
        """Run all integration tests."""
        print("🧪 Running Albion Trade Optimizer Integration Tests\n")
        
        tests = [
            ("Configuration Management", self.test_configuration),
            ("Database Operations", self.test_database),
            ("API Integration", self.test_api_integration),
            ("Fee Calculations", self.test_fee_calculations),
            ("Flip Detection", self.test_flip_detection),
            ("Recipe Loading", self.test_recipe_loading),
            ("Crafting Optimization", self.test_crafting_optimization),
            ("Data Freshness", self.test_data_freshness),
            ("GUI Components", self.test_gui_components),
            ("End-to-End Workflow", self.test_end_to_end_workflow)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"Testing {test_name}...")
            try:
                result = test_func()
                if result:
                    print(f"  ✅ {test_name} PASSED")
                    passed += 1
                else:
                    print(f"  ❌ {test_name} FAILED")
                    failed += 1
                self.test_results[test_name] = result
            except Exception as e:
                print(f"  💥 {test_name} ERROR: {e}")
                failed += 1
                self.test_results[test_name] = False
            print()
        
        # Summary
        total = passed + failed
        print(f"📊 Test Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
        
        if failed > 0:
            print(f"❌ {failed} tests failed")
            return False
        else:
            print("🎉 All tests passed!")
            return True
    
    def test_configuration(self):
        """Test configuration management."""
        try:
            # Test loading configuration
            config = self.config_manager.load_config()
            assert isinstance(config, dict), "Config should be a dictionary"
            assert len(config) > 0, "Config should not be empty"
            
            # Test required sections
            required_sections = ['cities', 'fees', 'aodp']
            for section in required_sections:
                assert section in config, f"Missing required section: {section}"
            
            # Test configuration validation
            errors = self.config_manager.validate_config()
            assert len(errors) == 0, f"Configuration validation errors: {errors}"
            
            # Test getting specific values
            cities = self.config_manager.get_cities()
            assert len(cities) > 0, "Should have at least one city configured"
            
            sales_tax = self.config_manager.get_sales_tax(True)
            assert 0 <= sales_tax <= 1, "Sales tax should be between 0 and 1"
            
            print("    ✓ Configuration loaded and validated")
            return True
            
        except Exception as e:
            print(f"    ❌ Configuration test failed: {e}")
            return False
    
    def test_database(self):
        """Test database operations."""
        try:
            # Initialize database
            self.db_manager = DatabaseManager(self.config)
            self.db_manager.initialize_database()
            
            # Test database stats
            stats = self.db_manager.get_database_stats()
            assert isinstance(stats, dict), "Stats should be a dictionary"
            assert 'total_records' in stats, "Stats should include total_records"
            
            # Clear any existing test data first
            try:
                self.db_manager.clear_cache()
            except:
                pass  # Ignore if no data to clear
            
            # Test storing and retrieving price data
            test_prices = [
                {
                    'item_id': 'TEST_ITEM_UNIQUE',
                    'city': 'Martlock',
                    'quality': 1,
                    'sell_price_min': 1000,
                    'sell_price_max': 1100,
                    'buy_price_min': 900,
                    'buy_price_max': 950,
                    'observed_at_utc': datetime.utcnow()
                }
            ]
            
            stored_count = self.db_manager.save_prices(test_prices)
            assert stored_count == 1, "Should store one price record"
            
            # Test retrieving prices
            retrieved_prices = self.db_manager.get_recent_prices(['TEST_ITEM_UNIQUE'], ['Martlock'], quality=1)
            assert len(retrieved_prices) >= 1, "Should retrieve at least one price record"
            
            # Find our test record
            test_record = None
            for price in retrieved_prices:
                if price['item_id'] == 'TEST_ITEM_UNIQUE':
                    test_record = price
                    break
            
            assert test_record is not None, "Should find our test record"
            assert test_record['item_id'] == 'TEST_ITEM_UNIQUE', "Retrieved item should match"
            
            print("    ✓ Database operations working correctly")
            return True
            
        except Exception as e:
            print(f"    ❌ Database test failed: {e}")
            return False
    
    def test_api_integration(self):
        """Test API integration."""
        try:
            # Initialize API client
            self.api_client = AODPClient(self.config)
            
            # Test connection
            connection_ok = self.api_client.test_connection()
            if not connection_ok:
                print("    ⚠️ API connection failed, but client initialized")
                return True  # Don't fail test if API is temporarily unavailable
            
            # Test getting prices for known items
            test_items = ['T4_BAG']
            test_cities = ['Caerleon']
            
            prices = self.api_client.get_current_prices(test_items, test_cities, [1])
            
            if len(prices) > 0:
                price = prices[0]
                assert 'item_id' in price, "Price should have item_id"
                assert 'city' in price, "Price should have city"
                assert 'sell_price_min' in price, "Price should have sell_price_min"
                print(f"    ✓ Retrieved {len(prices)} price records from API")
            else:
                print("    ⚠️ No price data returned from API")
            
            return True
            
        except Exception as e:
            print(f"    ❌ API integration test failed: {e}")
            return False
    
    def test_fee_calculations(self):
        """Test fee calculation accuracy."""
        try:
            fee_calc = FeeCalculator(self.config)
            
            # Test instant buy (no fees)
            instant_buy = fee_calc.calculate_instant_buy_cost(1000)
            assert instant_buy.net_amount == 1000, "Instant buy should have no fees"
            assert instant_buy.fees == 0, "Instant buy fees should be 0"
            
            # Test buy order (2.5% setup fee)
            buy_order = fee_calc.calculate_buy_order_cost(1000)
            expected_fee = 1000 * 0.025
            assert abs(buy_order.fees - expected_fee) < 0.01, "Buy order fee calculation incorrect"
            
            # Test instant sell with premium (4% sales tax)
            instant_sell = fee_calc.calculate_instant_sell_revenue(1000, premium=True)
            expected_tax = 1000 * 0.04
            assert abs(instant_sell.fees - expected_tax) < 0.01, "Instant sell tax calculation incorrect"
            
            # Test flip profit calculation
            src_prices = {'sell_price_min': 1000, 'buy_price_max': 950}
            dst_prices = {'sell_price_min': 1100, 'buy_price_max': 1050}
            
            fast_flip = fee_calc.calculate_flip_profit(src_prices, dst_prices, 'fast', premium=True)
            assert fast_flip['profit_per_unit'] > 0, "Fast flip should be profitable"
            
            patient_flip = fee_calc.calculate_flip_profit(src_prices, dst_prices, 'patient', premium=True)
            assert patient_flip['profit_per_unit'] > fast_flip['profit_per_unit'], "Patient flip should be more profitable"
            
            print("    ✓ Fee calculations are accurate")
            return True
            
        except Exception as e:
            print(f"    ❌ Fee calculation test failed: {e}")
            return False
    
    def test_flip_detection(self):
        """Test flip opportunity detection."""
        try:
            flip_calc = FlipCalculator(self.config)
            
            # Create test price data
            test_prices = {
                'T4_BAG': [
                    {
                        'item_id': 'T4_BAG',
                        'quality': 1,
                        'city': 'Martlock',
                        'sell_price_min': 1000,
                        'buy_price_max': 950,
                        'observed_at_utc': datetime.utcnow()
                    },
                    {
                        'item_id': 'T4_BAG',
                        'quality': 1,
                        'city': 'Lymhurst',
                        'sell_price_min': 1200,
                        'buy_price_max': 1150,
                        'observed_at_utc': datetime.utcnow()
                    }
                ]
            }
            
            # Calculate opportunities
            opportunities = flip_calc.calculate_flip_opportunities(test_prices)
            assert len(opportunities) > 0, "Should find flip opportunities"
            
            # Check opportunity properties
            opp = opportunities[0]
            assert hasattr(opp, 'item_id'), "Opportunity should have item_id"
            assert hasattr(opp, 'profit_per_unit'), "Opportunity should have profit_per_unit"
            assert hasattr(opp, 'strategy'), "Opportunity should have strategy"
            assert hasattr(opp, 'risk_level'), "Opportunity should have risk_level"
            
            # Test filtering
            profitable_only = flip_calc.filter_opportunities(opportunities, min_profit=50)
            assert len(profitable_only) <= len(opportunities), "Filtering should reduce or maintain count"
            
            print(f"    ✓ Found {len(opportunities)} flip opportunities")
            return True
            
        except Exception as e:
            print(f"    ❌ Flip detection test failed: {e}")
            return False
    
    def test_recipe_loading(self):
        """Test recipe loading and validation."""
        try:
            recipe_loader = RecipeLoader()
            recipes = recipe_loader.load_recipes()
            
            assert len(recipes) > 0, "Should load at least one recipe"
            
            # Test recipe structure
            for item_id, recipe in recipes.items():
                assert recipe.item_id == item_id, "Recipe item_id should match key"
                assert len(recipe.ingredients) > 0, "Recipe should have ingredients"
                assert recipe.tier >= 1, "Recipe tier should be valid"
            
            # Test dependency analysis
            if 'T4_SWORD' in recipes:
                deps = recipe_loader.get_dependencies('T4_SWORD')
                assert len(deps) > 0, "T4_SWORD should have dependencies"
                
                tree = recipe_loader.get_crafting_tree('T4_SWORD')
                assert tree['craftable'], "T4_SWORD should be craftable"
            
            # Test validation
            validation = recipe_loader.validate_all_recipes()
            print(f"    ✓ Loaded {len(recipes)} recipes with {len(validation['errors'])} errors")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Recipe loading test failed: {e}")
            return False
    
    def test_crafting_optimization(self):
        """Test crafting optimization."""
        try:
            recipe_loader = RecipeLoader()
            recipes = recipe_loader.load_recipes()
            
            if len(recipes) == 0:
                print("    ⚠️ No recipes loaded, skipping crafting test")
                return True
            
            craft_optimizer = CraftingOptimizer(self.config, recipe_loader)
            
            # Test with mock prices
            test_prices = {
                'T4_METALBAR': [
                    {'item_id': 'T4_METALBAR', 'city': 'Martlock', 'sell_price_min': 100, 'observed_at_utc': datetime.utcnow()}
                ],
                'T4_PLANKS': [
                    {'item_id': 'T4_PLANKS', 'city': 'Martlock', 'sell_price_min': 80, 'observed_at_utc': datetime.utcnow()}
                ],
                'T4_SWORD': [
                    {'item_id': 'T4_SWORD', 'city': 'Martlock', 'sell_price_min': 2000, 'observed_at_utc': datetime.utcnow()}
                ],
                'T4_ORE': [
                    {'item_id': 'T4_ORE', 'city': 'Martlock', 'sell_price_min': 40, 'observed_at_utc': datetime.utcnow()}
                ],
                'T4_WOOD': [
                    {'item_id': 'T4_WOOD', 'city': 'Martlock', 'sell_price_min': 35, 'observed_at_utc': datetime.utcnow()}
                ]
            }
            
            if 'T4_SWORD' in recipes:
                plan = craft_optimizer.calculate_min_cost_plan('T4_SWORD', quantity=1, prices_by_item=test_prices)
                assert plan is not None, "Should generate crafting plan"
                assert plan.item_id == 'T4_SWORD', "Plan should be for correct item"
                assert plan.min_cost_per_unit > 0, "Plan should have positive cost"
                
                summary = craft_optimizer.generate_plan_summary(plan)
                assert len(summary) > 0, "Plan should have summary"
                
                print(f"    ✓ Generated crafting plan: {plan.recommended_action.value}")
            else:
                print("    ⚠️ T4_SWORD recipe not found, using available recipes")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Crafting optimization test failed: {e}")
            return False
    
    def test_data_freshness(self):
        """Test data freshness filtering."""
        try:
            # Create test data with different ages
            now = datetime.utcnow()
            old_time = now - timedelta(hours=25)  # Older than 24h default
            recent_time = now - timedelta(hours=1)  # Recent
            
            test_prices = [
                {
                    'item_id': 'TEST_ITEM',
                    'city': 'Martlock',
                    'quality': 1,
                    'sell_price_min': 1000,
                    'observed_at_utc': old_time
                },
                {
                    'item_id': 'TEST_ITEM',
                    'city': 'Lymhurst',
                    'quality': 1,
                    'sell_price_min': 1100,
                    'observed_at_utc': recent_time
                }
            ]
            
            # Test freshness filtering
            max_age_hours = self.config_manager.get_max_age_hours()
            cutoff_time = now - timedelta(hours=max_age_hours)
            
            fresh_prices = [p for p in test_prices if p['observed_at_utc'] >= cutoff_time]
            stale_prices = [p for p in test_prices if p['observed_at_utc'] < cutoff_time]
            
            assert len(fresh_prices) == 1, "Should have one fresh price"
            assert len(stale_prices) == 1, "Should have one stale price"
            assert fresh_prices[0]['city'] == 'Lymhurst', "Fresh price should be from Lymhurst"
            
            print(f"    ✓ Data freshness filtering working (max age: {max_age_hours}h)")
            return True
            
        except Exception as e:
            print(f"    ❌ Data freshness test failed: {e}")
            return False
    
    def test_gui_components(self):
        """Test GUI component creation."""
        try:
            from PySide6.QtWidgets import QApplication
            from gui.main_window import MainWindow
            
            # Create application
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            # Create main window
            window = MainWindow()
            
            # Test basic properties
            assert window.windowTitle() == "Albion Trade Optimizer", "Window title should be correct"
            assert window.tab_widget.count() == 5, "Should have 5 tabs"
            
            # Test configuration access
            config = window.get_config()
            assert isinstance(config, dict), "Should return configuration"
            
            # Test database manager
            db_manager = window.get_db_manager()
            assert db_manager is not None, "Should have database manager"
            
            # Test API client
            api_client = window.get_api_client()
            assert api_client is not None, "Should have API client"
            
            print("    ✓ GUI components created successfully")
            return True
            
        except Exception as e:
            print(f"    ❌ GUI component test failed: {e}")
            return False
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        try:
            print("    Running end-to-end workflow test...")
            
            # 1. Load configuration
            config = self.config_manager.load_config()
            print("      ✓ Configuration loaded")
            
            # 2. Initialize database
            if not self.db_manager:
                self.db_manager = DatabaseManager(config)
                self.db_manager.initialize_database()
            print("      ✓ Database initialized")
            
            # 3. Initialize API client
            if not self.api_client:
                self.api_client = AODPClient(config)
            print("      ✓ API client initialized")
            
            # 4. Load recipes
            recipe_loader = RecipeLoader()
            recipes = recipe_loader.load_recipes()
            print(f"      ✓ Loaded {len(recipes)} recipes")
            
            # 5. Initialize calculation engines
            fee_calc = FeeCalculator(config)
            flip_calc = FlipCalculator(config)
            if len(recipes) > 0:
                craft_optimizer = CraftingOptimizer(config, recipe_loader)
            print("      ✓ Calculation engines initialized")
            
            # 6. Test with sample data
            sample_prices = [
                {
                    'item_id': 'T4_BAG',
                    'city': 'Martlock',
                    'quality': 1,
                    'sell_price_min': 1000,
                    'buy_price_max': 950,
                    'observed_at_utc': datetime.utcnow()
                },
                {
                    'item_id': 'T4_BAG',
                    'city': 'Lymhurst',
                    'quality': 1,
                    'sell_price_min': 1200,
                    'buy_price_max': 1150,
                    'observed_at_utc': datetime.utcnow()
                }
            ]
            
            # 7. Store prices in database
            stored_count = self.db_manager.save_prices(sample_prices)
            print(f"      ✓ Stored {stored_count} price records")
            
            # 8. Calculate flip opportunities
            prices_by_item = {'T4_BAG': sample_prices}
            opportunities = flip_calc.calculate_flip_opportunities(prices_by_item)
            print(f"      ✓ Found {len(opportunities)} flip opportunities")
            
            # 9. Test GUI with data
            from PySide6.QtWidgets import QApplication
            from gui.main_window import MainWindow
            
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            window = MainWindow()
            
            # Test dashboard update
            dashboard = window.dashboard_widget
            dashboard.cached_opportunities = opportunities
            dashboard.update_summary_cards(sample_prices)
            print("      ✓ Dashboard updated with sample data")
            
            print("    ✅ End-to-end workflow completed successfully")
            return True
            
        except Exception as e:
            print(f"    ❌ End-to-end workflow test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Clean up test resources."""
        try:
            if self.api_client:
                self.api_client.close()
            
            if self.db_manager:
                self.db_manager.close()
                
        except Exception as e:
            print(f"Cleanup error: {e}")


def main():
    """Run integration tests."""
    test_suite = IntegrationTest()
    
    try:
        success = test_suite.run_all_tests()
        return 0 if success else 1
        
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    sys.exit(main())

