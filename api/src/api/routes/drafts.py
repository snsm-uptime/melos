"""API routes for recipe draft capture"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from uuid import UUID
from src.api.dependencies import get_kitchen, verify_kitchen_access
from src.application.use_cases.capture_recipe import CaptureRecipeUseCase
from src.adapters.llm.gemini import GeminiAdapter


router = APIRouter()


class TextRecipeRequest(BaseModel):
    text: str


class UrlRecipeRequest(BaseModel):
    url: str


class RecipeDraftResponse(BaseModel):
    is_recipe: bool
    reason: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    ingredients: Optional[list] = None
    yield_servings: Optional[int] = 1
    cook_time_minutes: Optional[int] = None
    prep_time_minutes: Optional[int] = None


@router.post("/kitchens/{kitchen_id}/recipes/draft")
async def capture_recipe_text(
    kitchen_id: UUID,
    request: TextRecipeRequest,
    kitchen = Depends(lambda: get_kitchen(kitchen_id)),
    user = Depends(lambda: get_current_user())
):
    """Capture recipe from pasted text"""
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")

    await verify_kitchen_access(kitchen_id, user.id)

    gemini = GeminiAdapter()
    use_case = CaptureRecipeUseCase(gemini, None)

    result = await use_case.capture_from_text(request.text)

    return RecipeDraftResponse(
        is_recipe=result.is_recipe,
        reason=result.reason,
        title=result.draft.title if result.draft else None,
        instructions=result.draft.instructions if result.draft else None,
        ingredients=result.draft.ingredients if result.draft else None,
        yield_servings=result.draft.yield_servings if result.draft else 1,
        cook_time_minutes=result.draft.cook_time_minutes if result.draft else None,
        prep_time_minutes=result.draft.prep_time_minutes if result.draft else None
    )


@router.post("/kitchens/{kitchen_id}/recipes/draft")
async def capture_recipe_url(
    kitchen_id: UUID,
    request: UrlRecipeRequest,
    kitchen = Depends(lambda: get_kitchen(kitchen_id)),
    user = Depends(lambda: get_current_user())
):
    """Capture recipe from URL"""
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")

    await verify_kitchen_access(kitchen_id, user.id)

    gemini = GeminiAdapter()
    use_case = CaptureRecipeUseCase(gemini, None)

    result = await use_case.capture_from_url(request.url)

    return RecipeDraftResponse(
        is_recipe=result.is_recipe,
        reason=result.reason,
        title=result.draft.title if result.draft else None,
        instructions=result.draft.instructions if result.draft else None,
        ingredients=result.draft.ingredients if result.draft else None,
        yield_servings=result.draft.yield_servings if result.draft else 1,
        cook_time_minutes=result.draft.cook_time_minutes if result.draft else None,
        prep_time_minutes=result.draft.prep_time_minutes if result.draft else None
    )


@router.post("/kitchens/{kitchen_id}/recipes/draft/photo")
async def capture_recipe_photo(
    kitchen_id: UUID,
    file: UploadFile = File(...),
    kitchen = Depends(lambda: get_kitchen(kitchen_id)),
    user = Depends(lambda: get_current_user())
):
    """Capture recipe from photo"""
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")

    await verify_kitchen_access(kitchen_id, user.id)

    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are supported"
        )

    image_data = await file.read()

    gemini = GeminiAdapter()
    use_case = CaptureRecipeUseCase(gemini, None)

    result = await use_case.capture_from_photo(image_data)

    return RecipeDraftResponse(
        is_recipe=result.is_recipe,
        reason=result.reason,
        title=result.draft.title if result.draft else None,
        instructions=result.draft.instructions if result.draft else None,
        ingredients=result.draft.ingredients if result.draft else None,
        yield_servings=result.draft.yield_servings if result.draft else 1,
        cook_time_minutes=result.draft.cook_time_minutes if result.draft else None,
        prep_time_minutes=result.draft.prep_time_minutes if result.draft else None
    )
