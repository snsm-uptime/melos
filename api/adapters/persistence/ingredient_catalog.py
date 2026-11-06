"""SQLAlchemy ingredient catalog per notebook and the personal catalog (spec 056, research R9)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from domain.errors import CatalogNameChangedError
from domain.ingredient_catalog import (
    CatalogEntry,
    CatalogIndex,
    Language,
    MergePlan,
    SplitPlan,
    as_language,
    sorted_pair,
)
from sqlalchemy import Select, literal, select, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    IngredientModel,
    IngredientNameModel,
    IngredientPairDismissalModel,
    NotebookMembershipModel,
    NotebookModel,
)


def build_entries(
    kept: Sequence[Any],
    others: Sequence[Any],
) -> list[CatalogEntry]:
    """Entries from (id, name, language) rows and (ingredient id, name, kind, language) rows."""
    variants: dict[UUID, dict[Language, str]] = {}
    spellings: dict[UUID, list[str]] = {}
    for ingredient_id, name, kind, language in others:
        lang = as_language(language)
        if kind == "variant" and lang is not None:
            variants.setdefault(ingredient_id, {})[lang] = name
        else:
            spellings.setdefault(ingredient_id, []).append(name)
    return [
        CatalogEntry(
            name=name,
            language=as_language(language),
            variants=variants.get(ingredient_id, {}),
            spellings=tuple(sorted(spellings.get(ingredient_id, []))),
        )
        for ingredient_id, name, language in kept
    ]


def _personal_names(user_id: UUID) -> Select[Any]:
    """Names in the personal notebooks the user owns or is a member of, never kitchen notebooks."""
    return (
        select(IngredientModel.name)
        .join(NotebookModel, NotebookModel.id == IngredientModel.notebook_id)
        .join(
            NotebookMembershipModel,
            NotebookMembershipModel.notebook_id == NotebookModel.id,
        )
        .where(
            NotebookMembershipModel.user_id == user_id,
            NotebookModel.kitchen_id.is_(None),
        )
    )


class SqlAlchemyIngredientCatalog:
    def __init__(self, session: Session) -> None:
        self._session = session

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        stmt = (
            select(IngredientModel.name)
            .where(IngredientModel.notebook_id == notebook_id)
            .order_by(IngredientModel.name)
        )
        return list(self._session.scalars(stmt).all())

    def index_for_notebook(self, notebook_id: UUID) -> CatalogIndex:
        kept = self._session.execute(
            select(IngredientModel.id, IngredientModel.name, IngredientModel.language)
            .where(IngredientModel.notebook_id == notebook_id)
            .order_by(IngredientModel.name)
        ).all()
        others = self._session.execute(
            select(
                IngredientNameModel.ingredient_id,
                IngredientNameModel.name,
                IngredientNameModel.kind,
                IngredientNameModel.language,
            ).where(IngredientNameModel.notebook_id == notebook_id)
        ).all()
        return CatalogIndex.build(build_entries(kept, others))

    def names_for_person(self, user_id: UUID) -> list[str]:
        stmt = _personal_names(user_id).distinct().order_by(IngredientModel.name)
        return list(self._session.scalars(stmt).all())

    def seed_from_person(self, notebook_id: UUID, user_id: UUID) -> None:
        names = _personal_names(user_id).distinct().subquery()
        source = select(literal(notebook_id, PgUUID(as_uuid=True)), names.c.name)
        self._session.execute(
            insert(IngredientModel)
            .from_select(["notebook_id", "name"], source)
            .on_conflict_do_nothing(index_elements=["notebook_id", "name"])
        )

    def copy_names(self, source_id: UUID, target_id: UUID) -> None:
        names = select(
            literal(target_id, PgUUID(as_uuid=True)),
            IngredientModel.name,
            IngredientModel.language,
        ).where(IngredientModel.notebook_id == source_id)
        self._session.execute(
            insert(IngredientModel).from_select(["notebook_id", "name", "language"], names)
        )
        # Other names follow their kept name to the target's ingredient of that name (spec 043).
        self._session.execute(
            text(
                """
                INSERT INTO ingredient_name (ingredient_id, notebook_id, name, kind, language)
                SELECT target.id, :target, other.name, other.kind, other.language
                FROM ingredient_name AS other
                JOIN ingredient AS kept ON kept.id = other.ingredient_id
                JOIN ingredient AS target
                  ON target.notebook_id = :target AND target.name = kept.name
                WHERE other.notebook_id = :source
                """
            ),
            {"source": source_id, "target": target_id},
        )

    def add_names(self, notebook_id: UUID, names: Sequence[str]) -> None:
        if not names:
            return
        self._session.execute(
            insert(IngredientModel)
            .values([{"notebook_id": notebook_id, "name": name} for name in names])
            .on_conflict_do_nothing(index_elements=["notebook_id", "name"])
        )

    # --- catalog management (spec 043) --------------------------------------------------------

    @contextmanager
    def savepoint(self) -> Iterator[object]:
        try:
            with self._session.begin_nested() as nested:
                yield nested
        except IntegrityError as exc:
            # Another write got there first, for example the same other name (FR-015).
            raise CatalogNameChangedError() from exc

    def lock_entries(self, notebook_id: UUID, names: Sequence[str]) -> None:
        if not names:
            return
        self._session.execute(
            select(IngredientModel.id)
            .where(IngredientModel.notebook_id == notebook_id, IngredientModel.name.in_(names))
            .order_by(IngredientModel.name)
            .with_for_update()
        ).all()

    def recipe_counts(self, notebook_id: UUID) -> dict[str, int]:
        rows = self._session.execute(
            text(
                """
                SELECT ri.name, count(DISTINCT ri.recipe_id)
                FROM recipe_ingredient AS ri
                JOIN recipe AS r ON r.id = ri.recipe_id
                WHERE r.notebook_id = :notebook
                GROUP BY ri.name
                """
            ),
            {"notebook": notebook_id},
        ).all()
        return {name: count for name, count in rows}

    def language_counts(self, notebook_id: UUID, name: str) -> dict[str, int]:
        rows = self._session.execute(
            text(
                """
                SELECT r.language, count(DISTINCT r.id)
                FROM recipe AS r
                JOIN recipe_ingredient AS ri ON ri.recipe_id = r.id
                WHERE r.notebook_id = :notebook AND ri.name = :name
                GROUP BY r.language
                """
            ),
            {"notebook": notebook_id, "name": name},
        ).all()
        return {language: count for language, count in rows}

    def _rename_lines(self, notebook_id: UUID, old: str, new: str) -> list[UUID]:
        rows = self._session.execute(
            text(
                """
                UPDATE recipe_ingredient AS ri
                SET name = :new
                FROM recipe AS r
                WHERE r.id = ri.recipe_id AND r.notebook_id = :notebook AND ri.name = :old
                RETURNING ri.recipe_id
                """
            ),
            {"notebook": notebook_id, "old": old, "new": new},
        ).all()
        return sorted({row[0] for row in rows})

    def _forget_dismissals(self, notebook_id: UUID, name: str) -> list[tuple[str, str]]:
        rows = self._session.execute(
            text(
                """
                DELETE FROM ingredient_pair_dismissal
                WHERE notebook_id = :notebook AND (name_a = :name OR name_b = :name)
                RETURNING name_a, name_b, dismissed_by
                """
            ),
            {"notebook": notebook_id, "name": name},
        ).all()
        return [(a, b, by) for a, b, by in rows]  # type: ignore[misc]

    def apply_merge(self, notebook_id: UUID, plan: MergePlan) -> list[UUID]:
        changed = self._rename_lines(notebook_id, plan.merged, plan.kept)
        # Its other names go with it (cascade) and come back under the kept entry below.
        self._session.execute(
            text("DELETE FROM ingredient WHERE notebook_id = :notebook AND name = :name"),
            {"notebook": notebook_id, "name": plan.merged},
        )
        kept_id = self._session.execute(
            text(
                """
                UPDATE ingredient SET language = :language
                WHERE notebook_id = :notebook AND name = :name
                RETURNING id
                """
            ),
            {"notebook": notebook_id, "name": plan.kept, "language": plan.kept_language},
        ).scalar_one()
        if plan.other_names:
            self._session.execute(
                insert(IngredientNameModel).values(
                    [
                        {
                            "ingredient_id": kept_id,
                            "notebook_id": notebook_id,
                            "name": other.name,
                            "kind": other.kind,
                            "language": other.language,
                        }
                        for other in plan.other_names
                    ]
                )
            )
        # The merged name is no longer a kept name, so no pair can name it (data-model).
        self._forget_dismissals(notebook_id, plan.merged)
        return changed

    def apply_rename(self, notebook_id: UUID, old: str, new: str) -> list[UUID]:
        self._session.execute(
            text("UPDATE ingredient SET name = :new WHERE notebook_id = :notebook AND name = :old"),
            {"notebook": notebook_id, "old": old, "new": new},
        )
        changed = self._rename_lines(notebook_id, old, new)
        for first, second, by in self._forget_dismissals(notebook_id, old):  # type: ignore[misc]
            other = second if first == old else first
            if other != new:
                self.dismiss_pair(notebook_id, other, new, by)
        return changed

    def set_language(self, notebook_id: UUID, name: str, language: str | None) -> None:
        self._session.execute(
            text(
                "UPDATE ingredient SET language = :language "
                "WHERE notebook_id = :notebook AND name = :name"
            ),
            {"notebook": notebook_id, "name": name, "language": language},
        )

    def delete_unused(self, notebook_id: UUID, name: str) -> int:
        count = self.recipe_counts(notebook_id).get(name, 0)
        if count:
            return count
        self._session.execute(
            text("DELETE FROM ingredient WHERE notebook_id = :notebook AND name = :name"),
            {"notebook": notebook_id, "name": name},
        )
        return 0

    def apply_split(self, notebook_id: UUID, kept: str, plan: SplitPlan) -> list[UUID]:
        self._session.execute(
            text("DELETE FROM ingredient_name WHERE notebook_id = :notebook AND name = :name"),
            {"notebook": notebook_id, "name": plan.name},
        )
        self._session.execute(
            insert(IngredientModel).values(
                notebook_id=notebook_id, name=plan.name, language=plan.language
            )
        )
        if plan.move_language is None:
            return []
        rows = self._session.execute(
            text(
                """
                UPDATE recipe_ingredient AS ri
                SET name = :new
                FROM recipe AS r
                WHERE r.id = ri.recipe_id AND r.notebook_id = :notebook
                  AND r.language = :language AND ri.name = :old
                RETURNING ri.recipe_id
                """
            ),
            {
                "notebook": notebook_id,
                "old": kept,
                "new": plan.name,
                "language": plan.move_language,
            },
        ).all()
        return sorted({row[0] for row in rows})

    def dismissed_pairs(self, notebook_id: UUID) -> list[tuple[str, str]]:
        rows = self._session.execute(
            select(IngredientPairDismissalModel.name_a, IngredientPairDismissalModel.name_b).where(
                IngredientPairDismissalModel.notebook_id == notebook_id
            )
        ).all()
        return [(a, b) for a, b in rows]

    def dismiss_pair(
        self, notebook_id: UUID, first: str, second: str, user_id: UUID | None
    ) -> None:
        name_a, name_b = sorted_pair(first, second)
        if name_a == name_b:
            return
        self._session.execute(
            insert(IngredientPairDismissalModel)
            .values(notebook_id=notebook_id, name_a=name_a, name_b=name_b, dismissed_by=user_id)
            .on_conflict_do_nothing()
        )
