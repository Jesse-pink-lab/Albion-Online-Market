#!/usr/bin/env python3
"""
Test script for core calculation engines.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engine.config import ConfigManager
from engine.fees import FeeCalculator
from engine.flips import FlipCalculator
from engine.crafting import CraftingOptimizer, RecipeLoader
import json


def test_fee_calculator():
    """Test fee calculation engine."""
    print("Testing Fee Calculator...")
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    fee_calc = FeeCalculator(config)
    
    # Test instant buy (no fees)
    instant_buy = fee_calc.calculate_instant_buy_cost(1000)
    assert instant_buy.net_amount == 1000
    assert instant_buy.fees == 0
    print("✓ Instant buy calculation correct")
    
    # Test buy order (2.5% setup fee)
    buy_order = fee_calc.calculate_buy_order_cost(1000)
    expected_fee = 1000 * 0.025
    assert abs(buy_order.fees - expected_fee) < 0.01
    assert abs(buy_order.net_amount - (1000 + expected_fee)) < 0.01
    print("✓ Buy order calculation correct")
    
    # Test instant sell (4% sales tax with premium)
    instant_sell = fee_calc.calculate_instant_sell_revenue(1000, premium=True)
    expected_tax = 1000 * 0.04
    assert abs(instant_sell.fees - expected_tax) < 0.01
    assert abs(instant_sell.net_amount - (1000 - expected_tax)) < 0.01
    print("✓ Instant sell calculation correct")
    
    # Test sell order (4% sales tax + 2.5% setup fee with premium)
    sell_order = fee_calc.calculate_sell_order_revenue(1000, premium=True)
    expected_total_fees = 1000 * 0.04 + 1000 * 0.025
    assert abs(sell_order.fees - expected_total_fees) < 0.01
    assert abs(sell_order.net_amount - (1000 - expected_total_fees)) < 0.01
    print("✓ Sell order calculation correct")
    
    # Test flip profit calculation
    src_prices = {'sell_price_min': 1000, 'buy_price_max': 950}
    dst_prices = {'sell_price_min': 1100, 'buy_price_max': 1050}
    
    fast_flip = fee_calc.calculate_flip_profit(src_prices, dst_prices, 'fast', premium=True)
    # Fast: buy at 1000, sell at 1050 with 4% tax
    expected_revenue = 1050 * (1 - 0.04)  # 1008
    expected_profit = expected_revenue - 1000  # 8
    assert abs(fast_flip['profit_per_unit'] - expected_profit) < 0.01
    print(f"✓ Fast flip calculation correct: {fast_flip['profit_per_unit']:.2f}")
    
    patient_flip = fee_calc.calculate_flip_profit(src_prices, dst_prices, 'patient', premium=True)
    # Patient: buy order at 950 + 2.5% fee, sell order at 1100 - 4% tax - 2.5% fee
    buy_cost = 950 * (1 + 0.025)  # 973.75
    sell_revenue = 1100 * (1 - 0.04 - 0.025)  # 1028.5
    expected_profit = sell_revenue - buy_cost  # 54.75
    assert abs(patient_flip['profit_per_unit'] - expected_profit) < 0.01
    print(f"✓ Patient flip calculation correct: {patient_flip['profit_per_unit']:.2f}")
    
    print("✅ Fee Calculator tests passed!\n")


def test_flip_calculator():
    """Test flip opportunity calculator."""
    print("Testing Flip Calculator...")
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    flip_calc = FlipCalculator(config)
    
    # Test risk classification
    risk_low = flip_calc.risk_classifier.classify_route_risk('Martlock', 'Lymhurst')
    assert risk_low == 'low'
    print("✓ Low risk route classification correct")
    
    risk_high = flip_calc.risk_classifier.classify_route_risk('Martlock', 'Caerleon')
    assert risk_high == 'high'
    print("✓ High risk route classification correct")
    
    # Test flip opportunity calculation
    test_prices = {
        'T4_SWORD': [
            {
                'item_id': 'T4_SWORD',
                'quality': 1,
                'city': 'Martlock',
                'sell_price_min': 1000,
                'buy_price_max': 950,
                'observed_at_utc': datetime.utcnow()
            },
            {
                'item_id': 'T4_SWORD',
                'quality': 1,
                'city': 'Lymhurst',
                'sell_price_min': 1100,
                'buy_price_max': 1050,
                'observed_at_utc': datetime.utcnow()
            }
        ]
    }
    
    opportunities = flip_calc.calculate_flip_opportunities(test_prices)
    assert len(opportunities) > 0
    print(f"✓ Found {len(opportunities)} flip opportunities")
    
    # Check that both strategies are present
    strategies = set(opp.strategy for opp in opportunities)
    assert 'fast' in strategies
    assert 'patient' in strategies
    print("✓ Both fast and patient strategies calculated")
    
    # Test filtering
    profitable_only = flip_calc.filter_opportunities(opportunities, min_profit=10)
    print(f"✓ Filtered to {len(profitable_only)} profitable opportunities")
    
    print("✅ Flip Calculator tests passed!\n")


def test_crafting_optimizer():
    """Test crafting optimization engine."""
    print("Testing Crafting Optimizer...")
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # Load recipes
    with open('recipes/recipes.json', 'r') as f:
        recipes_data = json.load(f)
    
    recipe_loader = RecipeLoader(recipes_data)
    craft_optimizer = CraftingOptimizer(config, recipe_loader)
    
    # Test recipe loading
    sword_recipe = recipe_loader.get_recipe('T4_SWORD')
    assert sword_recipe is not None
    assert recipe_loader.is_craftable('T4_SWORD')
    print("✓ Recipe loading works")
    
    # Test crafting cost calculation with mock prices
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
    
    plan = craft_optimizer.calculate_min_cost_plan('T4_SWORD', quantity=1, prices_by_item=test_prices)
    assert plan is not None
    assert plan.item_id == 'T4_SWORD'
    assert plan.recommended_action is not None
    print(f"✓ Crafting plan calculated: {plan.recommended_action.value}")
    print(f"  - Min cost per unit: {plan.min_cost_per_unit:.2f}")
    print(f"  - Total cost: {plan.total_cost:.2f}")
    
    # Test plan summary
    summary = craft_optimizer.generate_plan_summary(plan)
    assert len(summary) > 0
    print(f"✓ Plan summary: {summary}")
    
    print("✅ Crafting Optimizer tests passed!\n")


def test_integration():
    """Test integration between engines."""
    print("Testing Engine Integration...")
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # Test that all engines can work together
    fee_calc = FeeCalculator(config)
    flip_calc = FlipCalculator(config)
    
    # Load recipes
    with open('recipes/recipes.json', 'r') as f:
        recipes_data = json.load(f)
    
    recipe_loader = RecipeLoader(recipes_data)
    craft_optimizer = CraftingOptimizer(config, recipe_loader)
    
    # Test configuration consistency
    assert fee_calc.get_sales_tax(True) == config.get('fees', {}).get('sales_tax_premium', 0.04)
    assert flip_calc.fee_calculator.setup_fee == config.get('fees', {}).get('setup_fee', 0.025)
    print("✓ Configuration consistency across engines")
    
    # Test that crafting optimizer can use flip data
    test_prices = {
        'T4_SWORD': [
            {'item_id': 'T4_SWORD', 'city': 'Martlock', 'sell_price_min': 2000, 'observed_at_utc': datetime.utcnow()}
        ]
    }
    
    plan = craft_optimizer.calculate_min_cost_plan('T4_SWORD', prices_by_item=test_prices)
    flip_comparison = craft_optimizer.compare_with_flip(plan, [])  # Empty flip list
    assert not flip_comparison['has_flip_alternative']
    print("✓ Craft vs flip comparison works")
    
    print("✅ Engine Integration tests passed!\n")


def main():
    """Run all engine tests."""
    print("Testing Albion Trade Optimizer Core Engines...\n")
    
    try:
        test_fee_calculator()
        test_flip_calculator()
        test_crafting_optimizer()
        test_integration()
        
        print("🎉 All engine tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

