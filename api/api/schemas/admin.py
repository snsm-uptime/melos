"""Dashboard answers (spec 055 contracts/admin-api.md).

Each model lists its fields by hand, so a new field reaches the answer only on purpose (FR-019).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AdminUnit(BaseModel):
    name: str
    user_references: list[UUID]
    # Aliases of the people in user_references, alias-sorted; None for an account with no alias.
    user_aliases: list[str | None]
    reference_count: int
    is_default: bool
    created_at: datetime


class AdminUnitsResponse(BaseModel):
    units: list[AdminUnit]


class AdminIngredient(BaseModel):
    name: str
    recipes: int
    people: int


class AdminIngredientsResponse(BaseModel):
    ingredients: list[AdminIngredient]


class AdminRecipe(BaseModel):
    id: UUID
    title: str
    cart_adds: int
    notebook_name: str
    notebook_kind: Literal["personal", "kitchen"]
    people_with_access: int
    # Aliases of everyone who can read the recipe, alias-sorted; None for an account with no alias.
    people_aliases: list[str | None]


class AdminRecipesResponse(BaseModel):
    recipes: list[AdminRecipe]


class AdminUser(BaseModel):
    id: UUID
    alias: str | None
    open_sessions: int
    newest_session_at: datetime | None
    recipes_authored: int
    latest_recipe_at: datetime | None
    carts_created: int
    carts_edited: int
    carts_closed: int
    latest_cart_action_at: datetime | None


class AdminUsersResponse(BaseModel):
    users: list[AdminUser]
