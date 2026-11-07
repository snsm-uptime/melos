"""In-memory catalog, places and pair suggester for catalog management tests (spec 043).

The fake catalog mirrors SqlAlchemyIngredientCatalog: entries per notebook, recipe lines that
carry kept names, and dismissed pairs. Access comes from the notebook World fakes.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

from domain.errors import AIUnavailableError
from domain.ingredient_catalog import (
    CatalogEntry,
    CatalogIndex,
    Language,
    MergePlan,
    SplitPlan,
    normalize_name,
    sorted_pair,
)


@dataclass
class FakeRecipe:
    notebook_id: UUID
    language: str
    lines: list[str]


@dataclass
class FakeManagedCatalog:
    entries: dict[UUID, dict[str, CatalogEntry]] = field(default_factory=dict)
    recipes: dict[UUID, FakeRecipe] = field(default_factory=dict)
    dismissed: dict[UUID, set[tuple[str, str]]] = field(default_factory=dict)
    locked: list[tuple[UUID, tuple[str, ...]]] = field(default_factory=list)
    # Called inside lock_entries, to play a write that lands while this one waits.
    on_lock: list = field(default_factory=list)

    # --- setup ------------------------------------------------------------------------------

    def add(self, notebook_id: UUID, *entries: CatalogEntry | str) -> None:
        book = self.entries.setdefault(notebook_id, {})
        for entry in entries:
            item = CatalogEntry(entry) if isinstance(entry, str) else entry
            book[item.name] = item

    def recipe(self, notebook_id: UUID, language: str, *names: str) -> UUID:
        recipe_id = uuid4()
        self.recipes[recipe_id] = FakeRecipe(notebook_id, language, list(names))
        return recipe_id

    # --- reads ------------------------------------------------------------------------------

    def index_for_notebook(self, notebook_id: UUID) -> CatalogIndex:
        return CatalogIndex.build(self.entries.get(notebook_id, {}).values())

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        return sorted(self.entries.get(notebook_id, {}))

    def recipe_counts(self, notebook_id: UUID) -> dict[str, int]:
        counts: dict[str, int] = {}
        for recipe in self.recipes.values():
            if recipe.notebook_id == notebook_id:
                for name in set(recipe.lines):
                    counts[name] = counts.get(name, 0) + 1
        return counts

    def language_counts(self, notebook_id: UUID, name: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for recipe in self.recipes.values():
            if recipe.notebook_id == notebook_id and name in recipe.lines:
                counts[recipe.language] = counts.get(recipe.language, 0) + 1
        return counts

    def dismissed_pairs(self, notebook_id: UUID) -> list[tuple[str, str]]:
        return sorted(self.dismissed.get(notebook_id, set()))

    # --- writes -----------------------------------------------------------------------------

    @contextmanager
    def savepoint(self) -> Iterator[object]:
        snapshot = (
            {k: dict(v) for k, v in self.entries.items()},
            {k: replace(v, lines=list(v.lines)) for k, v in self.recipes.items()},
        )
        try:
            yield None
        except BaseException:
            self.entries, self.recipes = snapshot
            raise

    def lock_entries(self, notebook_id: UUID, names: Sequence[str]) -> None:
        self.locked.append((notebook_id, tuple(names)))
        while self.on_lock:
            self.on_lock.pop(0)()

    def _rename_lines(self, notebook_id: UUID, old: str, new: str, language: str | None = None):
        changed: list[UUID] = []
        for recipe_id, recipe in self.recipes.items():
            if recipe.notebook_id != notebook_id or old not in recipe.lines:
                continue
            if language is not None and recipe.language != language:
                continue
            recipe.lines = [new if name == old else name for name in recipe.lines]
            changed.append(recipe_id)
        return changed

    def apply_merge(self, notebook_id: UUID, plan: MergePlan) -> list[UUID]:
        book = self.entries[notebook_id]
        changed = self._rename_lines(notebook_id, plan.merged, plan.kept)
        del book[plan.merged]
        kept = book[plan.kept]
        variants: dict[Language, str] = dict(kept.variants)
        spellings = list(kept.spellings)
        for other in plan.other_names:
            if other.kind == "variant" and other.language is not None:
                variants[other.language] = other.name
            else:
                spellings.append(other.name)
        book[plan.kept] = replace(
            kept, language=plan.kept_language, variants=variants, spellings=tuple(spellings)
        )
        pairs = self.dismissed.get(notebook_id, set())
        self.dismissed[notebook_id] = {p for p in pairs if plan.merged not in p}
        return changed

    def apply_rename(self, notebook_id: UUID, old: str, new: str) -> list[UUID]:
        book = self.entries[notebook_id]
        book[new] = replace(book.pop(old), name=new)
        pairs = self.dismissed.get(notebook_id, set())
        self.dismissed[notebook_id] = {
            sorted_pair(*(new if n == old else n for n in pair)) for pair in pairs
        }
        return self._rename_lines(notebook_id, old, new)

    def set_language(self, notebook_id: UUID, name: str, language: str | None) -> None:
        book = self.entries[notebook_id]
        book[name] = replace(book[name], language=language)  # type: ignore[arg-type]

    def delete_unused(self, notebook_id: UUID, name: str) -> int:
        count = self.recipe_counts(notebook_id).get(name, 0)
        if not count:
            del self.entries[notebook_id][name]
        return count

    def apply_split(self, notebook_id: UUID, kept: str, plan: SplitPlan) -> list[UUID]:
        book = self.entries[notebook_id]
        entry = book[kept]
        book[kept] = replace(
            entry,
            variants={k: v for k, v in entry.variants.items() if v != plan.name},
            spellings=tuple(s for s in entry.spellings if s != plan.name),
        )
        book[plan.name] = CatalogEntry(plan.name, plan.language)
        if plan.move_language is None:
            return []
        return self._rename_lines(notebook_id, kept, plan.name, plan.move_language)

    def dismiss_pair(self, notebook_id: UUID, first: str, second: str, user_id: UUID) -> None:
        self.dismissed.setdefault(notebook_id, set()).add(sorted_pair(first, second))


@dataclass
class FakePlaces:
    """One person's choices per normalized name, enough for move_choices."""

    choices: dict[tuple[UUID, str], str] = field(default_factory=dict)

    def move_choices(self, old_name: str, new_name: str) -> None:
        old, new = normalize_name(old_name), normalize_name(new_name)
        for user_id, name in list(self.choices):
            if name == old and (user_id, new) not in self.choices:
                self.choices[(user_id, new)] = self.choices.pop((user_id, name))


@dataclass
class FakePairSuggester:
    pairs: list[tuple[str, str]] = field(default_factory=list)
    unavailable: bool = False
    calls: list[list[tuple[str, str | None]]] = field(default_factory=list)

    def suggest(self, names: Sequence[tuple[str, str | None]]) -> list[tuple[str, str]]:
        self.calls.append(list(names))
        if self.unavailable:
            raise AIUnavailableError()
        return list(self.pairs)
