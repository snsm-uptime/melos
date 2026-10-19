"""Recipe domain model"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from uuid import UUID


class Unit(str, Enum):
    """Measurement units"""
    CUP = "cup"
    TABLESPOON = "tbsp"
    TEASPOON = "tsp"
    OUNCE = "oz"
    POUND = "lb"
    GRAM = "g"
    MILLILITER = "ml"
    UNIT = "unit"


class Difficulty(str, Enum):
    """Recipe difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class RecipeIngredient:
    """Single ingredient in a recipe"""
    ingredient_id: UUID
    quantity: float
    unit: str
    is_linear: bool = True


@dataclass
class Recipe:
    """Complete recipe with metadata"""
    id: UUID
    kitchen_id: UUID
    title: str
    instructions: str
    ingredients: List[RecipeIngredient]
    yield_servings: int = 1
    cook_time_minutes: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    source_id: Optional[UUID] = None
    created_by_user_id: Optional[UUID] = None

    @property
    def total_time_minutes(self) -> int:
        """Total cooking time"""
        cook = self.cook_time_minutes or 0
        prep = self.prep_time_minutes or 0
        return cook + prep


@dataclass
class ParseResult:
    """Result of recipe extraction"""
    is_recipe: bool
    reason: str
    draft: Optional['RecipeDraft'] = None


@dataclass
class RecipeDraft:
    """Draft recipe before saving"""
    title: str
    instructions: str
    ingredients: List[RecipeIngredient]
    yield_servings: int = 1
    cook_time_minutes: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    source_id: Optional[UUID] = None
    error: Optional[str] = None
