"""
Crafting optimizer for Albion Trade Optimizer.

Implements recursive hybrid min-cost algorithm for crafting vs buying decisions.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from .fees import FeeCalculator


class ActionType(Enum):
    """Type of action for obtaining an item."""
    BUY = "buy"
    CRAFT = "craft"
    HYBRID = "hybrid"


@dataclass
class CraftingStep:
    """Represents a step in a crafting plan."""
    item_id: str
    action: ActionType
    quantity: int
    cost_per_unit: float
    total_cost: float
    city: Optional[str] = None  # For buy actions
    ingredients: Optional[List['CraftingStep']] = None  # For craft actions


@dataclass
class CraftingPlan:
    """Complete crafting plan for an item."""
    item_id: str
    target_quantity: int
    min_cost_per_unit: float
    total_cost: float
    recommended_action: ActionType
    plan_tree: CraftingStep
    buy_cost_per_unit: Optional[float] = None
    craft_cost_per_unit: Optional[float] = None
    savings: float = 0.0


class RecipeLoader:
    """Loads and manages crafting recipes."""
    
    def __init__(self, recipes_data: Dict[str, Any]):
        """Initialize with recipes data."""
        self.recipes = recipes_data.get('recipes', {})
        self.logger = logging.getLogger(__name__)
    
    def get_recipe(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get recipe for an item."""
        return self.recipes.get(item_id)
    
    def is_craftable(self, item_id: str) -> bool:
        """Check if an item is craftable."""
        return item_id in self.recipes
    
    def get_ingredients(self, item_id: str) -> List[Dict[str, Any]]:
        """Get ingredients for an item."""
        recipe = self.get_recipe(item_id)
        if recipe:
            return recipe.get('ingredients', [])
        return []


class CraftingOptimizer:
    """Optimizes crafting decisions using recursive min-cost algorithm."""
    
    def __init__(self, config: Dict[str, Any], recipe_loader: RecipeLoader):
        """Initialize crafting optimizer."""
        self.config = config
        self.recipe_loader = recipe_loader
        self.fee_calculator = FeeCalculator(config)
        self.logger = logging.getLogger(__name__)
        
        # Crafting configuration
        self.resource_return_rate = config.get('crafting', {}).get('resource_return_rate', 0.15)
        self.focus_return_rate = config.get('crafting', {}).get('focus_return_rate', 0.35)
        self.use_focus = config.get('crafting', {}).get('use_focus', False)
        self.default_station_fee = config.get('crafting', {}).get('default_station_fee', 0)
        
        # Cache for memoization
        self._cost_cache = {}
    
    def calculate_min_cost_plan(self, item_id: str, quantity: int = 1,
                              prices_by_item: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> CraftingPlan:
        """
        Calculate the minimum cost plan for obtaining an item.
        
        Uses recursive hybrid strategy: for each ingredient, choose between buying or crafting.
        """
        if prices_by_item is None:
            prices_by_item = {}
        
        # Clear cache for new calculation
        self._cost_cache.clear()
        
        # Calculate min cost per unit
        min_cost_result = self._calculate_min_cost_recursive(item_id, prices_by_item)
        
        # Build the plan tree
        plan_tree = self._build_plan_tree(item_id, quantity, prices_by_item)
        
        # Calculate buy cost for comparison
        buy_cost = self._get_cheapest_buy_cost(item_id, prices_by_item)
        
        # Determine recommended action
        craft_cost = min_cost_result['cost']
        
        if buy_cost is None:
            recommended_action = ActionType.CRAFT
            savings = 0
        elif craft_cost < buy_cost:
            recommended_action = ActionType.CRAFT
            savings = (buy_cost - craft_cost) * quantity
        else:
            recommended_action = ActionType.BUY
            savings = (craft_cost - buy_cost) * quantity
        
        return CraftingPlan(
            item_id=item_id,
            target_quantity=quantity,
            min_cost_per_unit=min(craft_cost, buy_cost or float('inf')),
            total_cost=min(craft_cost, buy_cost or float('inf')) * quantity,
            recommended_action=recommended_action,
            plan_tree=plan_tree,
            buy_cost_per_unit=buy_cost,
            craft_cost_per_unit=craft_cost,
            savings=abs(savings)
        )
    
    def _calculate_min_cost_recursive(self, item_id: str, prices_by_item: Dict[str, List[Dict[str, Any]]],
                                    visited: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Recursively calculate minimum cost to obtain one unit of an item.
        
        Returns the cheaper option between buying and crafting.
        """
        if visited is None:
            visited = set()
        
        # Prevent infinite recursion
        if item_id in visited:
            self.logger.warning(f"Circular dependency detected for {item_id}")
            return {'cost': float('inf'), 'action': ActionType.BUY, 'details': {}}
        
        # Check cache
        if item_id in self._cost_cache:
            return self._cost_cache[item_id]
        
        visited.add(item_id)
        
        try:
            # Calculate buy cost
            buy_cost = self._get_cheapest_buy_cost(item_id, prices_by_item)
            
            # Calculate craft cost if recipe exists
            craft_cost = None
            craft_details = {}
            
            if self.recipe_loader.is_craftable(item_id):
                craft_result = self._calculate_craft_cost(item_id, prices_by_item, visited.copy())
                craft_cost = craft_result['cost']
                craft_details = craft_result['details']
            
            # Choose the cheaper option
            if buy_cost is None and craft_cost is None:
                result = {'cost': float('inf'), 'action': ActionType.BUY, 'details': {}}
            elif buy_cost is None:
                result = {'cost': craft_cost, 'action': ActionType.CRAFT, 'details': craft_details}
            elif craft_cost is None:
                result = {'cost': buy_cost, 'action': ActionType.BUY, 'details': {'city': self._get_cheapest_city(item_id, prices_by_item)}}
            elif craft_cost < buy_cost:
                result = {'cost': craft_cost, 'action': ActionType.CRAFT, 'details': craft_details}
            else:
                result = {'cost': buy_cost, 'action': ActionType.BUY, 'details': {'city': self._get_cheapest_city(item_id, prices_by_item)}}
            
            # Cache result
            self._cost_cache[item_id] = result
            return result
            
        finally:
            visited.remove(item_id)
    
    def _calculate_craft_cost(self, item_id: str, prices_by_item: Dict[str, List[Dict[str, Any]]],
                            visited: Set[str]) -> Dict[str, Any]:
        """Calculate the cost to craft one unit of an item."""
        recipe = self.recipe_loader.get_recipe(item_id)
        if not recipe:
            return {'cost': float('inf'), 'details': {}}
        
        ingredients = recipe.get('ingredients', [])
        station_fee = recipe.get('station_fee', 0) or self.default_station_fee
        
        # Calculate ingredient costs
        ingredient_costs = {}
        ingredient_details = {}
        
        for ingredient in ingredients:
            ingredient_id = ingredient['item_id']
            ingredient_qty = ingredient['quantity']
            
            # Recursively calculate min cost for ingredient
            ingredient_result = self._calculate_min_cost_recursive(ingredient_id, prices_by_item, visited)
            ingredient_cost_per_unit = ingredient_result['cost']
            
            if ingredient_cost_per_unit == float('inf'):
                return {'cost': float('inf'), 'details': {}}
            
            ingredient_costs[ingredient_id] = ingredient_cost_per_unit * ingredient_qty
            ingredient_details[ingredient_id] = {
                'cost_per_unit': ingredient_cost_per_unit,
                'quantity': ingredient_qty,
                'total_cost': ingredient_cost_per_unit * ingredient_qty,
                'action': ingredient_result['action'],
                'details': ingredient_result['details']
            }
        
        # Calculate effective cost with returns and fees
        cost_calculation = self.fee_calculator.calculate_crafting_costs(
            ingredient_costs=ingredient_costs,
            resource_return_rate=self.resource_return_rate,
            focus_return_rate=self.focus_return_rate,
            use_focus=self.use_focus,
            station_fee=station_fee
        )
        
        return {
            'cost': cost_calculation['effective_cost'],
            'details': {
                'ingredients': ingredient_details,
                'cost_breakdown': cost_calculation,
                'station_fee': station_fee
            }
        }
    
    def _get_cheapest_buy_cost(self, item_id: str, prices_by_item: Dict[str, List[Dict[str, Any]]]) -> Optional[float]:
        """Get the cheapest buy cost for an item across all cities."""
        if item_id not in prices_by_item:
            return None
        
        prices = prices_by_item[item_id]
        min_price = None
        
        for price in prices:
            sell_price_min = price.get('sell_price_min')
            if sell_price_min is not None:
                if min_price is None or sell_price_min < min_price:
                    min_price = sell_price_min
        
        return min_price
    
    def _get_cheapest_city(self, item_id: str, prices_by_item: Dict[str, List[Dict[str, Any]]]) -> Optional[str]:
        """Get the city with the cheapest price for an item."""
        if item_id not in prices_by_item:
            return None
        
        prices = prices_by_item[item_id]
        min_price = None
        cheapest_city = None
        
        for price in prices:
            sell_price_min = price.get('sell_price_min')
            if sell_price_min is not None:
                if min_price is None or sell_price_min < min_price:
                    min_price = sell_price_min
                    cheapest_city = price.get('city')
        
        return cheapest_city
    
    def _build_plan_tree(self, item_id: str, quantity: int, prices_by_item: Dict[str, List[Dict[str, Any]]]) -> CraftingStep:
        """Build a detailed plan tree for the optimal strategy."""
        min_cost_result = self._cost_cache.get(item_id)
        if not min_cost_result:
            min_cost_result = self._calculate_min_cost_recursive(item_id, prices_by_item)
        
        action = min_cost_result['action']
        cost_per_unit = min_cost_result['cost']
        
        if action == ActionType.BUY:
            city = min_cost_result['details'].get('city')
            return CraftingStep(
                item_id=item_id,
                action=action,
                quantity=quantity,
                cost_per_unit=cost_per_unit,
                total_cost=cost_per_unit * quantity,
                city=city
            )
        
        elif action == ActionType.CRAFT:
            # Build ingredient steps
            ingredient_steps = []
            details = min_cost_result['details']
            
            if 'ingredients' in details:
                recipe = self.recipe_loader.get_recipe(item_id)
                for ingredient in recipe.get('ingredients', []):
                    ingredient_id = ingredient['item_id']
                    ingredient_qty = ingredient['quantity'] * quantity  # Scale by target quantity
                    
                    ingredient_step = self._build_plan_tree(ingredient_id, ingredient_qty, prices_by_item)
                    ingredient_steps.append(ingredient_step)
            
            return CraftingStep(
                item_id=item_id,
                action=action,
                quantity=quantity,
                cost_per_unit=cost_per_unit,
                total_cost=cost_per_unit * quantity,
                ingredients=ingredient_steps
            )
        
        else:
            # Fallback
            return CraftingStep(
                item_id=item_id,
                action=ActionType.BUY,
                quantity=quantity,
                cost_per_unit=cost_per_unit,
                total_cost=cost_per_unit * quantity
            )
    
    def generate_plan_summary(self, plan: CraftingPlan) -> str:
        """Generate a human-readable summary of the crafting plan."""
        if plan.recommended_action == ActionType.BUY:
            city = plan.plan_tree.city or "unknown city"
            return f"Buy {plan.target_quantity}× {plan.item_id} from {city} (cost: {plan.total_cost:.0f})"
        
        summary_parts = []
        self._collect_plan_summary(plan.plan_tree, summary_parts)
        
        return "; ".join(summary_parts)
    
    def _collect_plan_summary(self, step: CraftingStep, summary_parts: List[str]):
        """Recursively collect plan summary parts."""
        if step.action == ActionType.BUY:
            city = step.city or "unknown city"
            summary_parts.append(f"Buy {step.quantity}× {step.item_id} from {city}")
        
        elif step.action == ActionType.CRAFT:
            summary_parts.append(f"Craft {step.quantity}× {step.item_id}")
            
            if step.ingredients:
                for ingredient_step in step.ingredients:
                    self._collect_plan_summary(ingredient_step, summary_parts)
    
    def compare_with_flip(self, plan: CraftingPlan, flip_opportunities: List[Any]) -> Dict[str, Any]:
        """
        Compare crafting plan with available flip opportunities for the same item.
        
        Returns analysis of whether crafting or flipping is more profitable.
        """
        item_flips = [flip for flip in flip_opportunities if flip.item_id == plan.item_id]
        
        if not item_flips:
            return {
                'has_flip_alternative': False,
                'recommendation': 'craft',
                'reason': 'No flip opportunities available'
            }
        
        # Find best flip opportunity
        best_flip = max(item_flips, key=lambda x: x.profit_per_unit)
        
        # Calculate flip profit vs craft savings
        flip_profit = best_flip.profit_per_unit * plan.target_quantity
        craft_cost = plan.total_cost
        
        if plan.buy_cost_per_unit:
            buy_cost = plan.buy_cost_per_unit * plan.target_quantity
            craft_savings = buy_cost - craft_cost
        else:
            craft_savings = 0
        
        if flip_profit > craft_savings:
            return {
                'has_flip_alternative': True,
                'recommendation': 'flip',
                'reason': f'Flipping more profitable: {flip_profit:.0f} vs {craft_savings:.0f} savings',
                'best_flip': best_flip,
                'flip_profit': flip_profit,
                'craft_savings': craft_savings
            }
        else:
            return {
                'has_flip_alternative': True,
                'recommendation': 'craft',
                'reason': f'Crafting more profitable: {craft_savings:.0f} vs {flip_profit:.0f} flip profit',
                'best_flip': best_flip,
                'flip_profit': flip_profit,
                'craft_savings': craft_savings
            }

