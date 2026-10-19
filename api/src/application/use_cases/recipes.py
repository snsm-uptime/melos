"""Use case for recipe management"""
from typing import Optional, List
from uuid import UUID
from src.domain.recipe import Recipe, RecipeDraft, RecipeIngredient
from src.application.ports import RecipeRepository, Embedder


class RecipesUseCase:
    """Create, list, retrieve, and delete recipes"""

    def __init__(
        self,
        recipe_repo: RecipeRepository,
        embedder: Embedder
    ):
        self.recipe_repo = recipe_repo
        self.embedder = embedder

    async def create_recipe(
        self,
        kitchen_id: UUID,
        user_id: UUID,
        draft: RecipeDraft,
        source_id: Optional[UUID] = None
    ) -> Recipe:
        """Save recipe draft to database with embedding"""
        recipe = Recipe(
            kitchen_id=kitchen_id,
            title=draft.title,
            instructions=draft.instructions,
            yield_servings=draft.yield_servings,
            cook_time_minutes=draft.cook_time_minutes,
            prep_time_minutes=draft.prep_time_minutes,
            difficulty=draft.difficulty,
            source_id=source_id,
            created_by_user_id=user_id
        )

        recipe_text = f"{recipe.title} {recipe.instructions}"
        embedding = await self.embedder.embed_recipe(recipe_text)
        recipe.embedding = embedding

        recipe_id = await self.recipe_repo.create(recipe)
        return recipe

    async def list_recipes(self, kitchen_id: UUID) -> List[Recipe]:
        """List all recipes in kitchen"""
        return await self.recipe_repo.list_by_kitchen(kitchen_id)

    async def get_recipe(self, recipe_id: UUID, kitchen_id: UUID) -> Optional[Recipe]:
        """Get recipe by ID"""
        return await self.recipe_repo.get(recipe_id, kitchen_id)

    async def delete_recipe(self, recipe_id: UUID, kitchen_id: UUID) -> bool:
        """Soft-delete recipe"""
        return await self.recipe_repo.delete(recipe_id, kitchen_id)
