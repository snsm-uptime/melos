"""SQLAlchemy recipe list reads (spec 021)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from application.ports import RecipeCardRow, RecipePage
from sqlalchemy import func, literal, or_, select
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    NotebookModel,
    RecipeIngredientModel,
    RecipeModel,
    UserModel,
)

_ESCAPE = "\\"


def _like_pattern(key: str) -> str:
    """The key as a literal substring pattern: the member's % and _ match themselves."""
    escaped = (
        key.replace(_ESCAPE, _ESCAPE * 2).replace("%", f"{_ESCAPE}%").replace("_", f"{_ESCAPE}_")
    )
    return f"%{escaped}%"


def _folded(column):
    return func.unaccent(func.lower(column))


class SqlAlchemyRecipeListRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_page(
        self, notebook_ids: Sequence[UUID], key: str, offset: int, limit: int
    ) -> RecipePage:
        if not notebook_ids:
            return RecipePage(items=[], total=0)

        where = [RecipeModel.notebook_id.in_(list(notebook_ids))]
        if key:
            pattern = _like_pattern(key)
            in_ingredient = (
                select(literal(1))
                .where(
                    RecipeIngredientModel.recipe_id == RecipeModel.id,
                    _folded(RecipeIngredientModel.name).like(pattern, escape=_ESCAPE),
                )
                .exists()
            )
            where.append(
                or_(_folded(RecipeModel.title).like(pattern, escape=_ESCAPE), in_ingredient)
            )

        total = self._session.scalar(select(func.count()).select_from(RecipeModel).where(*where))

        count_lines = (
            select(func.count(RecipeIngredientModel.id))
            .where(RecipeIngredientModel.recipe_id == RecipeModel.id)
            .correlate(RecipeModel)
            .scalar_subquery()
        )
        rows = self._session.execute(
            select(
                RecipeModel.id,
                RecipeModel.title,
                UserModel.alias,
                count_lines,
                RecipeModel.notebook_id,
                NotebookModel.name,
                RecipeModel.created_at,
            )
            .join(NotebookModel, NotebookModel.id == RecipeModel.notebook_id)
            .outerjoin(UserModel, UserModel.id == RecipeModel.author_id)
            .where(*where)
            .order_by(RecipeModel.created_at.desc(), RecipeModel.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        items = [
            RecipeCardRow(
                id=row[0],
                title=row[1],
                author_alias=row[2],
                ingredient_count=row[3],
                notebook_id=row[4],
                notebook_name=row[5],
                created_at=row[6],
            )
            for row in rows
        ]
        return RecipePage(items=items, total=total or 0)
