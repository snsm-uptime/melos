"""API routes for recipe management"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from api.src.api.dependencies import get_kitchen, verify_kitchen_access
from api.src.application.use_cases.recipes import RecipesUseCase
from api.src.application.use_cases.ingredients import IngredientsUseCase
from api.src.adapters.llm.gemini import GeminiAdapter
from api.src.adapters.persistence.repositories import RecipeRepository, IngredientRepository


router = APIRouter()


class RecipeIngredientRequest(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str
    notes: Optional[str] = None
    is_linear: bool = True


class SaveRecipeRequest(BaseModel):
    title: str
    instructions: str
    ingredients: List[RecipeIngredientRequest]
    yield_servings: int = 1
    cook_time_minutes: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    difficulty: str = "medium"
    source_id: Optional[UUID] = None


class RecipeResponse(BaseModel):
    id: UUID
    title: str
    instructions: str
    yield_servings: int
    cook_time_minutes: Optional[int]
    prep_time_minutes: Optional[int]
    difficulty: str
    created_by_user_id: UUID
    created_at: str


@router.post("/kitchens/{kitchen_id}/recipes")
async def save_recipe(
    kitchen_id: UUID,
    request: SaveRecipeRequest,
    kitchen = Depends(lambda: get_kitchen(kitchen_id)),
    user = Depends(lambda: get_current_user())
):
    """Save recipe from draft"""
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")

    await verify_kitchen_access(kitchen_id, user.id)

    from api.src.domain.recipe import RecipeDraft

    draft = RecipeDraft(
        title=request.title,
        instructions=request.instructions,
        ingredients=request.ingredients,
        yield_servings=request.yield_servings,
        cook_time_minutes=request.cook_time_minutes,
        prep_time_minutes=request.prep_time_minutes,
        difficulty=request.difficulty
    )

    recipe_repo = RecipeRepository()
    ingredient_repo = IngredientRepository()
    embedder = GeminiAdapter()

    recipes_use_case = RecipesUseCase(recipe_repo, embedder)
    recipe = await recipes_use_case.create_recipe(
        kitchen_id, user.id, draft, request.source_id
    )

    ingredients_use_case = IngredientsUseCase(ingredient_repo)
    for ing in request.ingredients:
        ingredient_id = await ingredients_use_case.match_or_create_ingredient(
            kitchen_id, ing.ingredient_name, unit=ing.unit
        )

        from api.src.domain.recipe import RecipeIngredient
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient_id,
            quantity=ing.quantity,
            unit=ing.unit,
            notes=ing.notes,
            is_linear=ing.is_linear
        )
        await recipe_repo.create_recipe_ingredient(recipe_ingredient)

    return RecipeResponse(
        id=recipe.id,
        title=recipe.title,
        instructions=recipe.instructions,
        yield_servings=recipe.yield_servings,
        cook_time_minutes=recipe.cook_time_minutes,
        prep_time_minutes=recipe.prep_time_minutes,
        difficulty=recipe.difficulty,
        created_by_user_id=recipe.created_by_user_id,
        created_at=recipe.created_at.isoformat()
    )


@router.get("/kitchens/{kitchen_id}/recipes")
async def list_recipes(
    kitchen_id: UUID,
    kitchen = Depends(lambda: get_kitchen(kitchen_id)),
    user = Depends(lambda: get_current_user())
):
    """List all recipes in kitchen"""
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")

    await verify_kitchen_access(kitchen_id, user.id)

    recipe_repo = RecipeRepository()
    recipes_use_case = RecipesUseCase(recipe_repo, None)
    recipes = await recipes_use_case.list_recipes(kitchen_id)

    return [
        RecipeResponse(
            id=r.id,
            title=r.title,
            instructions=r.instructions,
            yield_servings=r.yield_servings,
            cook_time_minutes=r.cook_time_minutes,
            prep_time_minutes=r.prep_time_minutes,
            difficulty=r.difficulty,
            created_by_user_id=r.created_by_user_id,
            created_at=r.created_at.isoformat()
        )
        for r in recipes
    ]


@router.get("/kitchens/{kitchen_id}/recipes/{recipe_id}")
async def get_recipe(
    kitchen_id: UUID,
    recipe_id: UUID,
    kitchen = Depends(lambda: get_kitchen(kitchen_id)),
    user = Depends(lambda: get_current_user())
):
    """Get recipe details"""
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")

    await verify_kitchen_access(kitchen_id, user.id)

    recipe_repo = RecipeRepository()
    recipes_use_case = RecipesUseCase(recipe_repo, None)
    recipe = await recipes_use_case.get_recipe(recipe_id, kitchen_id)

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeResponse(
        id=recipe.id,
        title=recipe.title,
        instructions=recipe.instructions,
        yield_servings=recipe.yield_servings,
        cook_time_minutes=recipe.cook_time_minutes,
        prep_time_minutes=recipe.prep_time_minutes,
        difficulty=recipe.difficulty,
        created_by_user_id=recipe.created_by_user_id,
        created_at=recipe.created_at.isoformat()
    )


@router.delete("/kitchens/{kitchen_id}/recipes/{recipe_id}")
async def delete_recipe(
    kitchen_id: UUID,
    recipe_id: UUID,
    kitchen = Depends(lambda: get_kitchen(kitchen_id)),
    user = Depends(lambda: get_current_user())
):
    """Soft-delete recipe"""
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")

    await verify_kitchen_access(kitchen_id, user.id)

    recipe_repo = RecipeRepository()
    recipes_use_case = RecipesUseCase(recipe_repo, None)
    success = await recipes_use_case.delete_recipe(recipe_id, kitchen_id)

    if not success:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return {"success": True}
