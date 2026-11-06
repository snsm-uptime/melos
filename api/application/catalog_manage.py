"""Catalog management: rename, merge, delete and split names, and suggested pairs (spec 043).

Access follows the notebook rules (spec 056): a person who cannot read the notebook gets
not-found, one who can only read it gets read-only for any change. Each write locks the
ingredient rows it reads, re-reads the catalog under the lock, and plans with the pure rules of
`domain.ingredient_catalog`. Nothing is committed here: the request's transaction decides, and
each notebook of a merge runs in its own savepoint so one conflict skips only that notebook.
Logs carry counts only, never names (constitution 4).
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from domain.errors import (
    CatalogNameChangedError,
    CatalogNameInUseError,
    CatalogNameUnknownError,
    CatalogReadOnlyError,
    NotebookNotFoundError,
    SameIngredientError,
)
from domain.ingredient_catalog import (
    CatalogEntry,
    CatalogIndex,
    Language,
    MergePlan,
    as_language,
    check_rename,
    filter_pairs,
    plan_merge,
    propose_entry,
    split_plan,
)
from domain.notebook import can_write_recipes

from application.notebooks import NotebookView, notebook_view
from application.ports import (
    EmbeddingJobs,
    IngredientCatalog,
    IngredientPairSuggester,
    NotebookRepository,
    PlaceRepository,
    RecipeRepository,
)

logger = logging.getLogger(__name__)


def match_copied_names(
    recipes: RecipeRepository,
    catalog: IngredientCatalog,
    recipe_id: UUID,
    notebook_id: UUID,
    names: Sequence[str],
) -> None:
    """Give a copied recipe's lines the target catalog's kept names, and add the rest (FR-008).

    A name the target knows under any of its names (an other name, a plural) takes the kept
    name, so a copy never brings a merged name back. Names it lacks are added as they are.
    """
    index = catalog.index_for_notebook(notebook_id)
    renames: dict[str, str] = {}
    for name in dict.fromkeys(names):
        entry = propose_entry(name, index)
        if entry is not None and entry != name:
            renames[name] = entry
    if renames:
        recipes.rename_line_names(recipe_id, renames)
    catalog.add_names(notebook_id, list(dict.fromkeys(renames.get(n, n) for n in names)))


# --- reads --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CatalogItem:
    name: str
    language: Language | None
    recipe_count: int
    variants: Mapping[Language, str]
    spellings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CatalogView:
    notebook_id: UUID
    can_write: bool
    items: tuple[CatalogItem, ...]

    def item(self, name: str) -> CatalogItem | None:
        return next((item for item in self.items if item.name == name), None)


def _view(notebooks: NotebookRepository, user_id: UUID, notebook_id: UUID) -> NotebookView:
    facts = notebooks.facts_for(user_id, notebook_id)
    if facts is None:
        raise NotebookNotFoundError()
    return notebook_view(facts)


def _can_write(view: NotebookView) -> bool:
    return can_write_recipes(view.access, view.kitchen_is_archived)


def _writable(notebooks: NotebookRepository, user_id: UUID, notebook_id: UUID) -> NotebookView:
    view = _view(notebooks, user_id, notebook_id)
    if not _can_write(view):
        raise CatalogReadOnlyError()
    return view


def _item(entry: CatalogEntry, counts: Mapping[str, int]) -> CatalogItem:
    return CatalogItem(
        name=entry.name,
        language=entry.language,
        recipe_count=counts.get(entry.name, 0),
        variants=dict(entry.variants),
        spellings=entry.spellings,
    )


def read_catalog(catalog: IngredientCatalog, notebook_id: UUID, can_write: bool) -> CatalogView:
    index = catalog.index_for_notebook(notebook_id)
    counts = catalog.recipe_counts(notebook_id)
    items = []
    for name in sorted(index.kept_names()):
        entry = index.entry(name)
        assert entry is not None
        items.append(_item(entry, counts))
    return CatalogView(notebook_id=notebook_id, can_write=can_write, items=tuple(items))


class GetCatalogService:
    """One notebook's catalog with other names and use counts (contracts GET .../catalog)."""

    def __init__(self, notebooks: NotebookRepository, catalog: IngredientCatalog) -> None:
        self._notebooks = notebooks
        self._catalog = catalog

    def execute(self, user_id: UUID, notebook_id: UUID) -> CatalogView:
        view = _view(self._notebooks, user_id, notebook_id)
        return read_catalog(self._catalog, notebook_id, _can_write(view))


# --- merge (User Story 1, FR-002a to FR-009) ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class MergePreviewCommand:
    actor_user_id: UUID
    from_notebook_id: UUID
    merged: str
    kept: str


@dataclass(frozen=True, slots=True)
class MergeNotebook:
    notebook_id: UUID
    name: str
    recipe_count: int


@dataclass(frozen=True, slots=True)
class MergePreview:
    merged: str
    kept: str
    merged_language: Language | None
    kept_language: Language | None
    notebooks: tuple[MergeNotebook, ...]


def _writable_views(notebooks: NotebookRepository, user_id: UUID) -> list[NotebookView]:
    views: list[NotebookView] = []
    for facts in notebooks.visible_facts_for(user_id):
        try:
            view = notebook_view(facts)
        except NotebookNotFoundError:
            continue
        if _can_write(view):
            views.append(view)
    return views


def _most_common(counts: Counter[str]) -> Language | None:
    if not counts:
        return None
    # Ties go to the language that sorts first, so the answer is the same on every call.
    best = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return as_language(best)


class MergePreviewService:
    """What a merge would change, before anything does (FR-004).

    Both names must be in the starting notebook's catalog (FR-003). The merge then reaches every
    notebook the person can write to whose catalog has both, as two ingredients (FR-002a). Each
    name's language is prefilled from the recipes using it, else its stored language.
    """

    def __init__(self, notebooks: NotebookRepository, catalog: IngredientCatalog) -> None:
        self._notebooks = notebooks
        self._catalog = catalog

    def execute(self, command: MergePreviewCommand) -> MergePreview:
        _writable(self._notebooks, command.actor_user_id, command.from_notebook_id)
        start = self._catalog.index_for_notebook(command.from_notebook_id)
        first = plan_merge(start, command.merged, command.kept, None, None)

        found: list[MergeNotebook] = []
        merged_languages: Counter[str] = Counter()
        kept_languages: Counter[str] = Counter()
        stored: dict[str, Language | None] = {}
        for view in _writable_views(self._notebooks, command.actor_user_id):
            index = self._catalog.index_for_notebook(view.id)
            try:
                plan = plan_merge(index, first.merged, first.kept, None, None)
            except (CatalogNameUnknownError, SameIngredientError):
                continue
            counts = self._catalog.recipe_counts(view.id)
            found.append(MergeNotebook(view.id, view.name, counts.get(plan.merged, 0)))
            merged_languages.update(self._catalog.language_counts(view.id, plan.merged))
            kept_languages.update(self._catalog.language_counts(view.id, plan.kept))
            for name in (plan.merged, plan.kept):
                entry = index.entry(name)
                if entry is not None and entry.language is not None:
                    stored.setdefault(name, entry.language)
        return MergePreview(
            merged=first.merged,
            kept=first.kept,
            merged_language=_most_common(merged_languages) or stored.get(first.merged),
            kept_language=_most_common(kept_languages) or stored.get(first.kept),
            notebooks=tuple(found),
        )


SkipReason = Literal["name_changed", "no_access"]


@dataclass(frozen=True, slots=True)
class MergeCommand:
    actor_user_id: UUID
    merged: str
    kept: str
    merged_language: str | None
    kept_language: str | None
    notebook_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class MergeResult:
    merged: tuple[tuple[UUID, int], ...]
    skipped: tuple[tuple[UUID, SkipReason], ...]


class MergeService:
    """Merge two names in each notebook the preview listed that still qualifies (FR-002a, R5).

    Every notebook is re-checked under its row locks: lost access skips it as `no_access`, a
    name gone or already merged skips it as `name_changed`. The rest are written together.
    """

    def __init__(
        self,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        places: PlaceRepository,
        *,
        embedding_jobs: EmbeddingJobs | None = None,
    ) -> None:
        self._notebooks = notebooks
        self._catalog = catalog
        self._places = places
        self._embedding_jobs = embedding_jobs

    def execute(self, command: MergeCommand) -> MergeResult:
        merged: list[tuple[UUID, int]] = []
        skipped: list[tuple[UUID, SkipReason]] = []
        changed: list[UUID] = []
        moves: dict[str, str] = {}
        for notebook_id in dict.fromkeys(command.notebook_ids):
            try:
                _writable(self._notebooks, command.actor_user_id, notebook_id)
            except (NotebookNotFoundError, CatalogReadOnlyError):
                skipped.append((notebook_id, "no_access"))
                continue
            try:
                plan, recipe_ids = self._merge_one(notebook_id, command)
            except (CatalogNameUnknownError, SameIngredientError, CatalogNameChangedError):
                skipped.append((notebook_id, "name_changed"))
                continue
            merged.append((notebook_id, len(recipe_ids)))
            changed.extend(recipe_ids)
            moves.setdefault(plan.merged, plan.kept)
        for old, new in moves.items():
            self._places.move_choices(old, new)
        _enqueue(self._embedding_jobs, changed)
        logger.info(
            "catalog merge notebooks=%d skipped=%d recipes=%d",
            len(merged),
            len(skipped),
            len(changed),
        )
        return MergeResult(merged=tuple(merged), skipped=tuple(skipped))

    def _merge_one(self, notebook_id: UUID, command: MergeCommand) -> tuple[MergePlan, list[UUID]]:
        with self._catalog.savepoint():
            first = self._catalog.index_for_notebook(notebook_id)
            names = [n for n in (first.kept_for(command.merged), first.kept_for(command.kept)) if n]
            self._catalog.lock_entries(notebook_id, names)
            index = self._catalog.index_for_notebook(notebook_id)
            plan = plan_merge(
                index,
                command.merged,
                command.kept,
                command.merged_language,
                command.kept_language,
            )
            return plan, self._catalog.apply_merge(notebook_id, plan)


def _enqueue(jobs: EmbeddingJobs | None, recipe_ids: Sequence[UUID]) -> None:
    # Same transaction as the change: a changed recipe cannot miss its embedding (R10).
    if jobs is not None and recipe_ids:
        jobs.enqueue(sorted(set(recipe_ids)))


# --- rename, language, delete, split (User Stories 2 to 4) --------------------------------------


@dataclass(frozen=True, slots=True)
class RenameCommand:
    actor_user_id: UUID
    notebook_id: UUID
    name: str
    new_name: str
    # Only when `set_language` is True: the kept name's language, None for none (FR-012).
    language: str | None = None
    set_language: bool = False


@dataclass(frozen=True, slots=True)
class RenameResult:
    item: CatalogItem
    recipes_changed: int


class _NotebookWrite:
    def __init__(
        self,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        places: PlaceRepository | None = None,
        *,
        embedding_jobs: EmbeddingJobs | None = None,
    ) -> None:
        self._notebooks = notebooks
        self._catalog = catalog
        self._places = places
        self._embedding_jobs = embedding_jobs

    def _locked_index(self, user_id: UUID, notebook_id: UUID, name: str) -> CatalogIndex:
        _writable(self._notebooks, user_id, notebook_id)
        self._catalog.lock_entries(notebook_id, [name])
        index = self._catalog.index_for_notebook(notebook_id)
        if index.entry(name) is None:
            raise CatalogNameChangedError()
        return index

    def _item(self, notebook_id: UUID, name: str) -> CatalogItem:
        item = read_catalog(self._catalog, notebook_id, True).item(name)
        assert item is not None
        return item


class RenameService(_NotebookWrite):
    """Rename a kept name, and/or set its language (FR-010 to FR-012)."""

    def execute(self, command: RenameCommand) -> RenameResult:
        self._locked_index(command.actor_user_id, command.notebook_id, command.name)
        index = self._catalog.index_for_notebook(command.notebook_id)
        new = check_rename(index, command.name, command.new_name)
        name = command.name
        changed: list[UUID] = []
        if new is not None:
            changed = self._catalog.apply_rename(command.notebook_id, command.name, new)
            if self._places is not None:
                self._places.move_choices(command.name, new)
            name = new
        if command.set_language:
            self._catalog.set_language(command.notebook_id, name, as_language(command.language))
        _enqueue(self._embedding_jobs, changed)
        logger.info("catalog rename recipes=%d", len(changed))
        return RenameResult(
            item=self._item(command.notebook_id, name), recipes_changed=len(changed)
        )


class DeleteNameService(_NotebookWrite):
    """Delete a name no recipe uses, with its other names (FR-013)."""

    def execute(self, user_id: UUID, notebook_id: UUID, name: str) -> None:
        self._locked_index(user_id, notebook_id, name)
        in_use = self._catalog.delete_unused(notebook_id, name)
        if in_use:
            raise CatalogNameInUseError(in_use)


@dataclass(frozen=True, slots=True)
class SplitResult:
    kept: CatalogItem
    split: CatalogItem
    recipes_changed: int


class SplitService(_NotebookWrite):
    """Make an other name its own ingredient again; no recipe shows other text (FR-014)."""

    def execute(self, user_id: UUID, notebook_id: UUID, name: str, other_name: str) -> SplitResult:
        index = self._locked_index(user_id, notebook_id, name)
        entry = index.entry(name)
        assert entry is not None
        plan = split_plan(entry, other_name)
        changed = self._catalog.apply_split(notebook_id, name, plan)
        _enqueue(self._embedding_jobs, changed)
        logger.info("catalog split recipes=%d", len(changed))
        catalog = read_catalog(self._catalog, notebook_id, True)
        kept, split = catalog.item(name), catalog.item(plan.name)
        assert kept is not None and split is not None
        return SplitResult(kept=kept, split=split, recipes_changed=len(changed))


# --- suggested pairs (User Story 5, FR-009a to FR-009d) -----------------------------------------


@dataclass(frozen=True, slots=True)
class SuggestedPairs:
    pairs: tuple[tuple[str, str], ...] = field(default=())


class SuggestPairsService:
    """Ask the model for (en, es) pairs and keep only real, undismissed ones (FR-009b).

    Only names reach the model, never recipe text (constitution 4). The model's errors raise
    AIUnavailableError from the adapter; nothing is written either way.
    """

    def __init__(
        self,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        suggester: IngredientPairSuggester,
    ) -> None:
        self._notebooks = notebooks
        self._catalog = catalog
        self._suggester = suggester

    def execute(self, user_id: UUID, notebook_id: UUID) -> SuggestedPairs:
        _writable(self._notebooks, user_id, notebook_id)
        index = self._catalog.index_for_notebook(notebook_id)
        names: list[tuple[str, Language | None]] = []
        for name in sorted(index.kept_names()):
            entry = index.entry(name)
            assert entry is not None
            names.append((name, entry.language))
        if len(names) < 2:
            return SuggestedPairs()
        proposed = self._suggester.suggest(names)
        pairs = filter_pairs(index, self._catalog.dismissed_pairs(notebook_id), proposed)
        logger.info(
            "catalog pairs names=%d proposed=%d kept=%d", len(names), len(proposed), len(pairs)
        )
        return SuggestedPairs(pairs=tuple(pairs))


class DismissPairService:
    """Remember that a pair is not one ingredient in this notebook (FR-009d)."""

    def __init__(self, notebooks: NotebookRepository, catalog: IngredientCatalog) -> None:
        self._notebooks = notebooks
        self._catalog = catalog

    def execute(self, user_id: UUID, notebook_id: UUID, english: str, spanish: str) -> None:
        _writable(self._notebooks, user_id, notebook_id)
        self._catalog.dismiss_pair(notebook_id, english, spanish, user_id)
