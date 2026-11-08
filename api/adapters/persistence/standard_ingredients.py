"""SQLAlchemy StandardCatalog: the standard ingredient table the scheduled job writes (spec 073).

Discovery reads recipe line names and creates one standard ingredient per new key (T020). The
translation step reads pending ingredients and writes an AI name with its check marker in one
transaction (T028). No notebook catalog table is read or written here (FR-021).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from application.ports import PendingStandardIngredient, RecipeScan
from domain.ingredient_discovery import Candidate, RecipeLineName
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from adapters.persistence.models import (
    RecipeIngredientModel,
    RecipeModel,
    StandardIngredientModel,
    StandardIngredientNameModel,
)

SESSION_LANGUAGES = ("en", "es")


class SqlAlchemyStandardCatalog:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def recipe_scan_since(self, since: datetime | None) -> RecipeScan:
        stmt = select(RecipeIngredientModel.name, RecipeModel.language, RecipeModel.id).join(
            RecipeModel, RecipeModel.id == RecipeIngredientModel.recipe_id
        )
        if since is not None:
            stmt = stmt.where(RecipeModel.updated_at >= since)
        with self._session_factory() as session:
            rows = session.execute(stmt).all()
        lines = [RecipeLineName(name=name, recipe_language=language) for name, language, _ in rows]
        return RecipeScan(lines=lines, recipes_scanned=len({recipe_id for _, _, recipe_id in rows}))

    def add_discovered(self, candidates: Sequence[Candidate]) -> int:
        """One standard ingredient per new key, with its discovery name. ON CONFLICT keeps the
        first language and name, so an existing row is never changed (data-model)."""
        created = 0
        with self._session_factory.begin() as session:
            for candidate in candidates:
                row = (
                    insert(StandardIngredientModel)
                    .values(normalized_name=candidate.key, language=candidate.language)
                    .on_conflict_do_nothing(index_elements=["normalized_name"])
                    .returning(StandardIngredientModel.id)
                )
                ingredient_id = session.execute(row).scalar_one_or_none()
                if ingredient_id is None:
                    continue
                session.add(
                    StandardIngredientNameModel(
                        standard_ingredient_id=ingredient_id,
                        name=candidate.name,
                        language=candidate.language,
                        source="discovery",
                        model=None,
                    )
                )
                created += 1
        return created

    def pending_translations(self, limit: int) -> list[PendingStandardIngredient]:
        stmt = (
            select(StandardIngredientModel, StandardIngredientNameModel.name)
            .join(
                StandardIngredientNameModel,
                (StandardIngredientNameModel.standard_ingredient_id == StandardIngredientModel.id)
                & (StandardIngredientNameModel.language == StandardIngredientModel.language)
                & (StandardIngredientNameModel.source == "discovery"),
            )
            .where(StandardIngredientModel.ai_checked_at.is_(None))
            .order_by(StandardIngredientModel.created_at, StandardIngredientModel.id)
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(stmt).all()
        return [
            PendingStandardIngredient(
                id=ingredient.id,
                name=name,
                language=_language(ingredient.language),
            )
            for ingredient, name in rows
        ]

    def has_name_in_language(self, ingredient_id: UUID, language: Literal["en", "es"]) -> bool:
        stmt = select(StandardIngredientNameModel.id).where(
            StandardIngredientNameModel.standard_ingredient_id == ingredient_id,
            StandardIngredientNameModel.language == language,
        )
        with self._session_factory() as session:
            return session.execute(stmt).first() is not None

    def save_translation(
        self,
        ingredient_id: UUID,
        name: str,
        language: Literal["en", "es"],
        model: str,
        checked_at: datetime,
    ) -> None:
        with self._session_factory.begin() as session:
            session.add(
                StandardIngredientNameModel(
                    standard_ingredient_id=ingredient_id,
                    name=name,
                    language=language,
                    source="ai",
                    model=model,
                )
            )
            session.execute(
                update(StandardIngredientModel)
                .where(StandardIngredientModel.id == ingredient_id)
                .values(ai_checked_at=checked_at)
            )

    def mark_checked(self, ingredient_id: UUID, checked_at: datetime) -> None:
        with self._session_factory.begin() as session:
            session.execute(
                update(StandardIngredientModel)
                .where(StandardIngredientModel.id == ingredient_id)
                .values(ai_checked_at=checked_at)
            )


def _language(value: str) -> Literal["en", "es"]:
    if value == "en":
        return "en"
    if value == "es":
        return "es"
    raise ValueError("a standard ingredient language is en or es")
