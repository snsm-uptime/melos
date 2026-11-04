"""The dashboard (spec 055, contracts/admin-api.md): reads, and one admin recipe delete.

Anyone signed out or not an admin gets the 404 FastAPI gives an unknown path, byte for byte.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict
from typing import Any

from application.admin import AdminDashboard
from domain.errors import AdminNotFoundError, RecipeNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.deps import get_admin_dashboard, optional_user_id
from api.schemas.admin import (
    AdminIngredient,
    AdminIngredientsResponse,
    AdminRecipe,
    AdminRecipesResponse,
    AdminUnit,
    AdminUnitsResponse,
    AdminUser,
    AdminUsersResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


def _read(read: Callable[[uuid.UUID | None], Sequence[Any]], user_id: uuid.UUID | None) -> list:
    try:
        return [asdict(row) for row in read(user_id)]
    except AdminNotFoundError:
        raise _not_found() from None


@router.get("/units", response_model=AdminUnitsResponse)
def admin_units(
    user_id: uuid.UUID | None = Depends(optional_user_id),
    dashboard: AdminDashboard = Depends(get_admin_dashboard),
) -> AdminUnitsResponse:
    rows = _read(dashboard.units, user_id)
    return AdminUnitsResponse(units=[AdminUnit(**row) for row in rows])


@router.get("/ingredients", response_model=AdminIngredientsResponse)
def admin_ingredients(
    user_id: uuid.UUID | None = Depends(optional_user_id),
    dashboard: AdminDashboard = Depends(get_admin_dashboard),
) -> AdminIngredientsResponse:
    rows = _read(dashboard.ingredients, user_id)
    return AdminIngredientsResponse(ingredients=[AdminIngredient(**row) for row in rows])


@router.get("/recipes", response_model=AdminRecipesResponse)
def admin_recipes(
    user_id: uuid.UUID | None = Depends(optional_user_id),
    dashboard: AdminDashboard = Depends(get_admin_dashboard),
) -> AdminRecipesResponse:
    rows = _read(dashboard.recipes, user_id)
    return AdminRecipesResponse(recipes=[AdminRecipe(**row) for row in rows])


@router.get("/users", response_model=AdminUsersResponse)
def admin_users(
    user_id: uuid.UUID | None = Depends(optional_user_id),
    dashboard: AdminDashboard = Depends(get_admin_dashboard),
) -> AdminUsersResponse:
    rows = _read(dashboard.users, user_id)
    return AdminUsersResponse(users=[AdminUser(**row) for row in rows])


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_recipe(
    recipe_id: uuid.UUID,
    user_id: uuid.UUID | None = Depends(optional_user_id),
    dashboard: AdminDashboard = Depends(get_admin_dashboard),
) -> Response:
    """Remove any recipe, whatever its notebook. Other paths still refuse writes below."""
    try:
        dashboard.delete_recipe(user_id, recipe_id)
    except (AdminNotFoundError, RecipeNotFoundError):
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.api_route("/{rest:path}", methods=["POST", "PUT", "PATCH", "DELETE"])
def admin_refuses_writes(rest: str) -> None:
    """No write exists, and a 405 would show that the path does (FR-018)."""
    raise _not_found()
