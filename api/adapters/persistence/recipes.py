"""SQLAlchemy recipe repository (specs 020 and 027)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from application.ports import (
    DuplicateSaveKeyError,
    KitchenRecipeCopy,
    RecipeDetail,
    RecipeLineDetail,
    StoredRecipe,
)
from domain.errors import NotebookNotFoundError, RecipeChangedError, RecipeNotFoundError
from domain.recipe import EditedRecipe, NewRecipe
from domain.recipe_draft import IngredientLine
from sqlalchemy import Select, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    NotebookModel,
    RecipeIngredientModel,
    RecipeModel,
    SourceModel,
    StepModel,
    UserModel,
)


def _recipe_columns() -> Select[Any]:
    return select(
        RecipeModel.id,
        RecipeModel.source_id,
        RecipeModel.author_id,
        RecipeModel.title,
        RecipeModel.base_servings,
        RecipeModel.servings_estimated,
        RecipeModel.created_at,
        RecipeModel.preview_image_base64,
        RecipeModel.language,
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
                if recipe.source_url is not None:
                    # A link capture stores the address only, never the page (FR-019).
                    source = SourceModel(
                        user_id=recipe.author_id, type="url", url=recipe.source_url, raw_text=None
                    )
                else:
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
                    preview_image_base64=recipe.preview_image,
                    language=recipe.language,
                )
                self._session.add(row)
                self._session.flush()
                self._add_content(row.id, recipe.lines, recipe.steps)
                self._session.flush()
        except IntegrityError as exc:
            if recipe.save_key is not None and "uq_recipe_author_save_key" in str(exc.orig):
                raise DuplicateSaveKeyError from exc
            # The notebook was deleted after it was read (spec 059 research R4).
            if "recipe_notebook_id_fkey" in str(exc.orig):
                raise NotebookNotFoundError from exc
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
                    vague=line.vague,
                    quantity=None if line.vague else line.quantity,
                    unit=None if line.vague else line.unit,
                    size=None if line.vague else line.size,
                    preparation=line.preparation,
                    # The words are kept on every line, so unchecking "Vague amount" hides them.
                    vague_note=line.vague_text,
                    note=line.note,
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
                    vague=line.vague,
                    quantity=None if line.quantity is None else float(line.quantity),
                    unit=line.unit,
                    size=line.size,
                    preparation=line.preparation,
                    vague_text=line.vague_note,
                    note=line.note,
                )
                for line in lines
            ),
            steps=tuple(steps),
            source_type=source_type,
            source_url=source_url,
            created_at=row.created_at,
            updated_at=row.updated_at,
            preview_image=row.preview_image_base64,
            language=row.language,
            proposed_language=row.proposed_language,
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
        if recipe.change_image:
            row.preview_image_base64 = recipe.preview_image
        if recipe.language is not None:
            row.language = recipe.language
            row.proposed_language = None
        elif recipe.dismiss_proposal:
            row.proposed_language = None
        # clock_timestamp, not now(): the token must move even inside one long transaction.
        row.updated_at = func.clock_timestamp()
        self._session.flush()
        detail = self.get_detail(recipe_id)
        assert detail is not None
        return detail

    def copy_all(self, source_id: UUID, target_id: UUID) -> int:
        # FOR SHARE: an edit being saved finishes first, and none starts until this commits, so
        # a recipe's lines and steps can't come from two versions (spec 035 research R4).
        recipes = self._session.execute(
            _recipe_columns().where(RecipeModel.notebook_id == source_id).with_for_update(read=True)
        ).all()
        if not recipes:
            return 0
        new_recipe_ids = {recipe.id: uuid4() for recipe in recipes}
        new_source_ids = self._copy_sources(recipes)
        self._insert(
            RecipeModel,
            [
                {
                    "id": new_recipe_ids[recipe.id],
                    "notebook_id": target_id,
                    "author_id": recipe.author_id,
                    "source_id": new_source_ids.get(recipe.source_id),
                    "title": recipe.title,
                    "base_servings": recipe.base_servings,
                    "servings_estimated": recipe.servings_estimated,
                    # Kept, because the kitchen list sorts by it (research R5).
                    "created_at": recipe.created_at,
                    "preview_image_base64": recipe.preview_image_base64,
                    "language": recipe.language,
                }
                for recipe in recipes
            ],
        )
        self._copy_content(new_recipe_ids)
        return len(recipes)

    def copy_one(
        self,
        source_recipe_id: UUID,
        target_notebook_id: UUID,
        author_id: UUID,
        *,
        link_source: bool = True,
    ) -> UUID | None:
        source = self._session.execute(
            _recipe_columns().where(RecipeModel.id == source_recipe_id).with_for_update(read=True)
        ).first()
        if source is None:
            return None
        new_id = uuid4()
        new_source_ids = self._copy_sources([source])
        # The copy is new in the kitchen (spec 069 R2). clock_timestamp, not now(): two copies in
        # one transaction still order, so "the latest copy" is the one made last.
        self._session.execute(
            insert(RecipeModel).values(
                {
                    "id": new_id,
                    "notebook_id": target_notebook_id,
                    "author_id": author_id,
                    "source_id": new_source_ids.get(source.source_id),
                    "title": source.title,
                    "base_servings": source.base_servings,
                    "servings_estimated": source.servings_estimated,
                    "preview_image_base64": source.preview_image_base64,
                    "language": source.language,
                    "copied_from_recipe_id": source.id if link_source else None,
                    "created_at": func.clock_timestamp(),
                    "updated_at": func.clock_timestamp(),
                }
            )
        )
        self._copy_content({source.id: new_id})
        return new_id

    def rename_line_names(self, recipe_id: UUID, renames: Mapping[str, str]) -> None:
        for old_name, new_name in renames.items():
            self._session.execute(
                update(RecipeIngredientModel)
                .where(
                    RecipeIngredientModel.recipe_id == recipe_id,
                    RecipeIngredientModel.name == old_name,
                )
                .values(name=new_name)
            )

    def set_language(self, recipe_id: UUID, language: str | None) -> None:
        row = self._lock(recipe_id)
        if language is not None and language != row.language:
            row.language = language
            # Lines now show other variants: an open edit form must reload (spec 027 token).
            row.updated_at = func.clock_timestamp()
        row.proposed_language = None
        self._session.flush()

    def overwrite_from(
        self, target_recipe_id: UUID, source_recipe_id: UUID, author_id: UUID
    ) -> bool:
        source = self._session.execute(
            _recipe_columns().where(RecipeModel.id == source_recipe_id).with_for_update(read=True)
        ).first()
        if source is None:
            return False
        try:
            row = self._lock(target_recipe_id)
        except RecipeNotFoundError:
            return False
        old_source_id = row.source_id
        self._session.execute(
            delete(RecipeIngredientModel).where(RecipeIngredientModel.recipe_id == target_recipe_id)
        )
        self._session.execute(delete(StepModel).where(StepModel.recipe_id == target_recipe_id))
        new_source_ids = self._copy_sources([source])
        row.source_id = new_source_ids.get(source.source_id)
        row.title = source.title
        row.base_servings = source.base_servings
        row.servings_estimated = source.servings_estimated
        row.preview_image_base64 = source.preview_image_base64
        row.language = source.language
        row.author_id = author_id
        row.updated_at = func.clock_timestamp()
        self._session.flush()
        if old_source_id is not None:
            self._session.execute(delete(SourceModel).where(SourceModel.id == old_source_id))
        self._copy_content({source.id: target_recipe_id})
        self._session.flush()
        return True

    def latest_copy_in_kitchen(
        self, source_recipe_id: UUID, kitchen_id: UUID
    ) -> KitchenRecipeCopy | None:
        found = self._session.execute(
            select(RecipeModel.id, NotebookModel.id, NotebookModel.name)
            .join(NotebookModel, NotebookModel.id == RecipeModel.notebook_id)
            .where(
                RecipeModel.copied_from_recipe_id == source_recipe_id,
                NotebookModel.kitchen_id == kitchen_id,
            )
            .order_by(RecipeModel.created_at.desc(), RecipeModel.id.desc())
            .limit(1)
        ).first()
        if found is None:
            return None
        return KitchenRecipeCopy(recipe_id=found[0], notebook_id=found[1], notebook_name=found[2])

    def _copy_sources(self, recipes: Sequence[Any]) -> dict[UUID, UUID]:
        """A copy gets its own source row: deleting a recipe deletes its source (spec 035 R5)."""
        new_source_ids = {recipe.source_id: uuid4() for recipe in recipes if recipe.source_id}
        if not new_source_ids:
            return new_source_ids
        sources = self._session.execute(
            select(
                SourceModel.id,
                SourceModel.user_id,
                SourceModel.type,
                SourceModel.url,
                SourceModel.raw_text,
                SourceModel.created_at,
            ).where(SourceModel.id.in_(new_source_ids))
        ).all()
        self._insert(
            SourceModel,
            [
                {
                    "id": new_source_ids[source.id],
                    "user_id": source.user_id,
                    "type": source.type,
                    "url": source.url,
                    "raw_text": source.raw_text,
                    "created_at": source.created_at,
                }
                for source in sources
            ],
        )
        return new_source_ids

    def _copy_content(self, new_recipe_ids: dict[UUID, UUID]) -> None:
        """Copy the lines and steps of each key recipe to its value recipe."""
        lines = self._session.execute(
            select(
                RecipeIngredientModel.recipe_id,
                RecipeIngredientModel.position,
                RecipeIngredientModel.name,
                RecipeIngredientModel.quantity,
                RecipeIngredientModel.unit,
                RecipeIngredientModel.size,
                RecipeIngredientModel.preparation,
                RecipeIngredientModel.vague_note,
                RecipeIngredientModel.note,
                RecipeIngredientModel.vague,
            ).where(RecipeIngredientModel.recipe_id.in_(new_recipe_ids))
        ).all()
        self._insert(
            RecipeIngredientModel,
            [{**line._asdict(), "recipe_id": new_recipe_ids[line.recipe_id]} for line in lines],
        )
        steps = self._session.execute(
            select(StepModel.recipe_id, StepModel.position, StepModel.text).where(
                StepModel.recipe_id.in_(new_recipe_ids)
            )
        ).all()
        self._insert(
            StepModel,
            [{**step._asdict(), "recipe_id": new_recipe_ids[step.recipe_id]} for step in steps],
        )

    def _insert(self, model: type[Any], rows: Sequence[dict[str, Any]]) -> None:
        # An empty list would insert one row of defaults.
        if rows:
            self._session.execute(insert(model), rows)

    def delete(self, recipe_id: UUID) -> None:
        row = self._lock(recipe_id)
        source_id = row.source_id
        self._session.expunge(row)
        # Lines and steps go with the recipe (ON DELETE CASCADE).
        self._session.execute(delete(RecipeModel).where(RecipeModel.id == recipe_id))
        if source_id is not None:
            self._session.execute(delete(SourceModel).where(SourceModel.id == source_id))
        self._session.flush()
