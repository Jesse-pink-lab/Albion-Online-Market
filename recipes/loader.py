"""
Recipe loader for Albion Trade Optimizer.

Loads and validates crafting recipes from JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass


@dataclass
class Recipe:
    """Represents a crafting recipe."""
    item_id: str
    tier: int
    category: str
    subcategory: str
    ingredients: List[Dict[str, Any]]
    station_type: str
    station_fee: float
    crafting_time_seconds: int
    focus_cost: int


class RecipeValidationError(Exception):
    """Exception raised when recipe validation fails."""
    pass


class RecipeLoader:
    """Loads and manages crafting recipes."""
    
    def __init__(self, recipes_file: Optional[str] = None):
        """Initialize recipe loader."""
        self.logger = logging.getLogger(__name__)
        
        if recipes_file:
            self.recipes_file = Path(recipes_file)
        else:
            # Default to recipes.json in the recipes directory
            self.recipes_file = Path(__file__).parent / "recipes.json"
        
        self.recipes = {}
        self.metadata = {}
        self._dependency_graph = {}
        
    def load_recipes(self) -> Dict[str, Recipe]:
        """Load recipes from the JSON file."""
        try:
            with open(self.recipes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.metadata = data.get('metadata', {})

            recipes: Dict[str, Recipe] = {}
            for item_id, rec in data.get('recipes', {}).items():
                recipes[item_id] = Recipe(
                    item_id=rec.get('item_id', item_id),
                    tier=rec.get('tier', 0),
                    category=rec.get('category', ''),
                    subcategory=rec.get('subcategory', ''),
                    ingredients=rec.get('ingredients', []),
                    station_type=rec.get('station_type', ''),
                    station_fee=rec.get('station_fee', 0.0),
                    crafting_time_seconds=rec.get('crafting_time_seconds', 0),
                    focus_cost=rec.get('focus_cost', 0),
                )

            self.recipes = recipes
            self._dependency_graph = {
                item: {ing['item_id'] for ing in recipe.ingredients}
                for item, recipe in recipes.items()
            }

            return self.recipes

        except FileNotFoundError:
            self.logger.error(f"Recipes file not found: {self.recipes_file}")
            self.recipes = {}
            self._dependency_graph = {}
            return {}

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse recipes file: {e}")
            self.recipes = {}
            self._dependency_graph = {}
            return {}

    def get_dependencies(self, item_id: str) -> Set[str]:
        """Get all dependencies for a recipe recursively."""
        deps: Set[str] = set()
        for dep in self._dependency_graph.get(item_id, set()):
            if dep not in deps:
                deps.add(dep)
                deps.update(self.get_dependencies(dep))
        return deps

    def get_crafting_tree(self, item_id: str) -> Dict[str, Any]:
        """Get crafting tree structure for an item."""
        if item_id not in self.recipes:
            return {'item_id': item_id, 'craftable': False, 'ingredients': []}

        recipe = self.recipes[item_id]
        return {
            'item_id': item_id,
            'craftable': True,
            'ingredients': [self.get_crafting_tree(ing['item_id']) for ing in recipe.ingredients],
        }

    def validate_all_recipes(self) -> Dict[str, Any]:
        """Validate all recipes and return a report."""
        errors: List[str] = []
        for item_id, recipe in self.recipes.items():
            for ing in recipe.ingredients:
                if ing['item_id'] not in self.recipes:
                    errors.append(
                        f"Unknown ingredient {ing['item_id']} referenced in recipe {item_id}"
                    )

        return {'errors': errors, 'warnings': []}

    # Utility methods -------------------------------------------------

    def import_recipes_from_dict(self, recipes_dict: Dict[str, Any]):
        """Import recipes from a dictionary and save to the recipes file."""
        data = {'recipes': recipes_dict, 'metadata': {'imported': True}}
        with open(self.recipes_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # Populate internal structures
        recipes: Dict[str, Recipe] = {}
        for item_id, rec in recipes_dict.items():
            recipes[item_id] = Recipe(
                item_id=rec.get('item_id', item_id),
                tier=rec.get('tier', 0),
                category=rec.get('category', ''),
                subcategory=rec.get('subcategory', ''),
                ingredients=rec.get('ingredients', []),
                station_type=rec.get('station_type', ''),
                station_fee=rec.get('station_fee', 0.0),
                crafting_time_seconds=rec.get('crafting_time_seconds', 0),
                focus_cost=rec.get('focus_cost', 0),
            )

        self.recipes = recipes
        self._dependency_graph = {
            item: {ing['item_id'] for ing in recipe.ingredients}
            for item, recipe in recipes.items()
        }

    def get_recipe(self, item_id: str) -> Optional[Recipe]:
        """Get a recipe by item id."""
        return self.recipes.get(item_id)

    def is_craftable(self, item_id: str) -> bool:
        """Return True if a recipe exists for the item."""
        return item_id in self.recipes