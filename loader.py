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
