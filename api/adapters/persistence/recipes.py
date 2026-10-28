"""SQLAlchemy recipe repository (specs 020 and 027)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from application.ports import (
    DuplicateSaveKeyError,
    RecipeDetail,
    RecipeLineDetail,
    StoredRecipe,
)
from domain.errors import RecipeChangedError, RecipeNotFoundError
from domain.recipe import EditedRecipe, NewRecipe
from domain.recipe_draft import IngredientLine
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    RecipeIngredientModel,
    RecipeModel,
    SourceModel,
    StepModel,
    UserModel,
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
                self._add_content(row.id, recipe.lines, recipe.steps)
                self._session.flush()
        except IntegrityError as exc:
            if recipe.save_key is not None and "uq_recipe_author_save_key" in str(exc.orig):
                raise DuplicateSaveKeyError from exc
            raise
        return _stored(row)

    def _add_content(
        self, recipe_id: UUID, lines: Sequence[IngredientLine], steps: Sequence[str]
    ) -> None:
        for position, line in enumerate(lines):
            self._session.add(
                RecipeIngredientModel(
                    recipe_id=recipe_id,
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
        for position, text in enumerate(steps):
            self._session.add(StepModel(recipe_id=recipe_id, position=position, text=text))

    def get_detail(self, recipe_id: UUID) -> RecipeDetail | None:
        found = self._session.execute(
            select(RecipeModel, UserModel.alias, SourceModel.type, SourceModel.url)
            .outerjoin(UserModel, UserModel.id == RecipeModel.author_id)
            .outerjoin(SourceModel, SourceModel.id == RecipeModel.source_id)
            .where(RecipeModel.id == recipe_id)
            .execution_options(populate_existing=True)
        ).first()
        if found is None:
            return None
        row, alias, source_type, source_url = found
        lines = self._session.scalars(
            select(RecipeIngredientModel)
            .where(RecipeIngredientModel.recipe_id == recipe_id)
            .order_by(RecipeIngredientModel.position)
        ).all()
        steps = self._session.scalars(
            select(StepModel.text)
            .where(StepModel.recipe_id == recipe_id)
            .order_by(StepModel.position)
        ).all()
        return RecipeDetail(
            id=row.id,
            notebook_id=row.notebook_id,
            title=row.title,
            base_servings=row.base_servings,
            servings_estimated=row.servings_estimated,
            author_alias=alias,
            lines=tuple(
                RecipeLineDetail(
                    name=line.name,
                    vague=line.vague_note is not None,
                    quantity=None if line.quantity is None else float(line.quantity),
                    unit=line.unit,
                    size=line.size,
                    preparation=line.preparation,
                    note=line.vague_note,
                )
                for line in lines
            ),
            steps=tuple(steps),
            source_type=source_type,
            source_url=source_url,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _lock(self, recipe_id: UUID) -> RecipeModel:
        row = self._session.scalars(
            select(RecipeModel)
            .where(RecipeModel.id == recipe_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).first()
        if row is None:
            raise RecipeNotFoundError()
        return row

    def replace(self, recipe_id: UUID, version: datetime, recipe: EditedRecipe) -> RecipeDetail:
        row = self._lock(recipe_id)
        if row.updated_at != version:
            raise RecipeChangedError()
        self._session.execute(
            delete(RecipeIngredientModel).where(RecipeIngredientModel.recipe_id == recipe_id)
        )
        self._session.execute(delete(StepModel).where(StepModel.recipe_id == recipe_id))
        self._session.flush()
        self._add_content(recipe_id, recipe.lines, recipe.steps)
        row.title = recipe.title
        row.base_servings = recipe.base_servings
        row.servings_estimated = recipe.servings_estimated
        # clock_timestamp, not now(): the token must move even inside one long transaction.
        row.updated_at = func.clock_timestamp()
        self._session.flush()
        detail = self.get_detail(recipe_id)
        assert detail is not None
        return detail

    def delete(self, recipe_id: UUID) -> None:
        row = self._lock(recipe_id)
        source_id = row.source_id
        self._session.expunge(row)
        # Lines and steps go with the recipe (ON DELETE CASCADE).
        self._session.execute(delete(RecipeModel).where(RecipeModel.id == recipe_id))
        if source_id is not None:
            self._session.execute(delete(SourceModel).where(SourceModel.id == source_id))
        self._session.flush()
