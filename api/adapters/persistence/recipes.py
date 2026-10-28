"""SQLAlchemy recipe repository (spec 020)."""

from __future__ import annotations

from uuid import UUID

from application.ports import DuplicateSaveKeyError, StoredRecipe
from domain.recipe import NewRecipe
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    RecipeIngredientModel,
    RecipeModel,
    SourceModel,
    StepModel,
)


def _stored(row: RecipeModel) -> StoredRecipe:
    return StoredRecipe(id=row.id, notebook_id=row.notebook_id, title=row.title)


class SqlAlchemyRecipeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_save_key(self, author_id: UUID, save_key: UUID) -> StoredRecipe | None:
        row = self._session.scalars(
            select(RecipeModel).where(
                RecipeModel.author_id == author_id, RecipeModel.save_key == save_key
            )
        ).first()
        return _stored(row) if row else None

    def add(self, recipe: NewRecipe) -> StoredRecipe:
        try:
            # A savepoint, so a duplicate save key leaves the caller's transaction usable.
            with self._session.begin_nested():
                source = SourceModel(
                    user_id=recipe.author_id, type="text", raw_text=recipe.source_text
                )
                self._session.add(source)
                self._session.flush()
                row = RecipeModel(
                    notebook_id=recipe.notebook_id,
                    author_id=recipe.author_id,
                    source_id=source.id,
                    title=recipe.title,
                    base_servings=recipe.base_servings,
                    servings_estimated=recipe.servings_estimated,
                    save_key=recipe.save_key,
                )
                self._session.add(row)
                self._session.flush()
                for position, line in enumerate(recipe.lines):
                    self._session.add(
                        RecipeIngredientModel(
                            recipe_id=row.id,
                            position=position,
                            name=line.name,
                            quantity=None if line.vague else line.quantity,
                            unit=None if line.vague else line.unit,
                            size=None if line.vague else line.size,
                            preparation=line.preparation,
                            # Only a vague amount keeps its words (PRD 1.6 line rules).
                            vague_note=line.note if line.vague else None,
                        )
                    )
                for position, text in enumerate(recipe.steps):
                    self._session.add(StepModel(recipe_id=row.id, position=position, text=text))
                self._session.flush()
        except IntegrityError as exc:
            if recipe.save_key is not None and "uq_recipe_author_save_key" in str(exc.orig):
                raise DuplicateSaveKeyError from exc
            raise
        return _stored(row)
