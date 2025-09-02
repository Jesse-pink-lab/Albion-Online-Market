#!/usr/bin/env python3
"""
Debug test for crafting optimization.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engine.config import ConfigManager
from engine.crafting import CraftingOptimizer
from recipes.loader import RecipeLoader

def debug_crafting():
    """Debug crafting optimization."""
    print("🔍 Debugging Crafting Optimization")
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        print("✓ Configuration loaded")
        
        # Load recipes
        recipe_loader = RecipeLoader()
        recipes = recipe_loader.load_recipes()
        print(f"✓ Loaded {len(recipes)} recipes")
        
        # Check a specific recipe
        if 'T4_SWORD' in recipes:
            recipe = recipes['T4_SWORD']
            print(f"✓ T4_SWORD recipe found: {type(recipe)}")
            print(f"  - Item ID: {recipe.item_id}")
            print(f"  - Tier: {recipe.tier}")
            print(f"  - Ingredients: {recipe.ingredients}")
            print(f"  - Ingredients type: {type(recipe.ingredients)}")
            
            if recipe.ingredients:
                first_ingredient = recipe.ingredients[0]
                print(f"  - First ingredient: {first_ingredient}")
                print(f"  - First ingredient type: {type(first_ingredient)}")
                
                if isinstance(first_ingredient, dict):
                    print(f"  - First ingredient item_id: {first_ingredient.get('item_id')}")
                    print(f"  - First ingredient quantity: {first_ingredient.get('quantity')}")
        
        # Initialize crafting optimizer
        craft_optimizer = CraftingOptimizer(config, recipe_loader)
        print("✓ Crafting optimizer initialized")
        
        # Test with mock prices
        test_prices = {
            'T4_METALBAR': [
                {'item_id': 'T4_METALBAR', 'city': 'Martlock', 'sell_price_min': 100}
            ],
            'T4_PLANKS': [
                {'item_id': 'T4_PLANKS', 'city': 'Martlock', 'sell_price_min': 80}
            ],
            'T4_SWORD': [
                {'item_id': 'T4_SWORD', 'city': 'Martlock', 'sell_price_min': 2000}
            ]
        }
        
        print("✓ Test prices prepared")
        
        # Try to calculate plan
        print("Calculating crafting plan...")
        plan = craft_optimizer.calculate_min_cost_plan('T4_SWORD', quantity=1, prices_by_item=test_prices)
        
        if plan:
            print(f"✓ Plan generated: {plan.recommended_action}")
            print(f"  - Min cost per unit: {plan.min_cost_per_unit}")
        else:
            print("❌ No plan generated")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_crafting()

