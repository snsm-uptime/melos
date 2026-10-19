"""Use case for ingredient management"""
from typing import Optional, List
from uuid import UUID
from api.src.domain.ingredient_catalog import Ingredient, IngredientCatalog
from api.src.application.ports import IngredientRepository


class IngredientsUseCase:
    """Create, match, and manage ingredients in kitchen catalog"""

    def __init__(
        self,
        ingredient_repo: IngredientRepository
    ):
        self.ingredient_repo = ingredient_repo

    async def match_or_create_ingredient(
        self,
        kitchen_id: UUID,
        ingredient_name: str,
        category_id: Optional[UUID] = None,
        unit: str = "unit"
    ) -> UUID:
        """Match ingredient to catalog or create if not found"""
        existing_ingredients = await self.ingredient_repo.list_by_kitchen(kitchen_id)

        matched = IngredientCatalog.match_ingredient(
            ingredient_name,
            existing_ingredients
        )

        if matched:
            return matched.id

        canonical_name = IngredientCatalog.normalize_name(ingredient_name)
        new_ingredient = Ingredient(
            kitchen_id=kitchen_id,
            canonical_name=canonical_name,
            category_id=category_id,
            unit=unit,
            aliases=[ingredient_name] if ingredient_name != canonical_name else []
        )

        return await self.ingredient_repo.create(new_ingredient)

    async def list_ingredients(self, kitchen_id: UUID) -> List[Ingredient]:
        """List all ingredients in kitchen catalog"""
        return await self.ingredient_repo.list_by_kitchen(kitchen_id)

    async def get_ingredient(self, ingredient_id: UUID, kitchen_id: UUID) -> Optional[Ingredient]:
        """Get ingredient by ID"""
        return await self.ingredient_repo.get(ingredient_id, kitchen_id)
