"""Meaning search over recipes, in one scope the person may read (spec 019 US2).

An in-process use case: S-030 (assistant), S-044 (list search) and S-032 (MCP) call it and add
their own routes (contracts/search-service.md). Order of steps:

1. the question and the filters are checked (domain);
2. the scope becomes notebook ids, with the same access checks the lists use, so a kitchen or a
   notebook the person may not read is not found (FR-016);
3. no notebook: an empty answer, with no service call and no record;
4. the question is embedded; a failure raises SearchQuestionNotEmbedded with the service result;
5. filters first, then exact cosine order, at most SEARCH_LIMIT current embeddings of the
   configured model (FR-017, FR-018);
6. each hit is marked close or weak, and the search is recorded, even with no hit (FR-017b).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from domain.errors import NotebookNotFoundError
from domain.recipe_search import (
    SEARCH_LIMIT,
    Kitchen,
    Mark,
    MyNotebooks,
    OneNotebook,
    SearchFeature,
    SearchFilters,
    SearchScope,
    mark,
    search_question,
)

from application.kitchen_access import AuthorizeKitchenAccessCommand, AuthorizeKitchenAccessService
from application.kitchens import KitchenRepository
from application.notebooks import notebook_view
from application.ports import (
    Embedded,
    Embedder,
    EmbedFailure,
    NotebookRepository,
    RecipeEmbeddings,
    RecordedHit,
    SearchEventRecord,
    SearchRecords,
)

logger = logging.getLogger(__name__)


class SearchQuestionNotEmbedded(Exception):  # noqa: N818 (named in the contract)
    """The question could not be embedded. `outcome` is the embedder's result, unchanged.

    Map it as recipe capture does (api/routes/recipe_capture.py): LimitReached → 429 with
    Retry-After; Unavailable and AIProviderError → 503; InvalidOutput → 422.
    """

    def __init__(self, outcome: EmbedFailure) -> None:
        super().__init__(type(outcome).__name__)
        self.outcome = outcome


@dataclass(frozen=True, slots=True)
class SearchRecipesCommand:
    actor_user_id: UUID
    scope: SearchScope
    question: str
    feature: SearchFeature
    filters: SearchFilters = SearchFilters()


@dataclass(frozen=True, slots=True)
class SearchHit:
    recipe_id: UUID
    notebook_id: UUID
    title: str
    score: float
    mark: Mark


@dataclass(frozen=True, slots=True)
class SearchAnswer:
    # None only when nothing was searched (an empty scope).
    search_id: UUID | None
    results: tuple[SearchHit, ...]


class SearchRecipesService:
    def __init__(
        self,
        kitchens: KitchenRepository,
        notebooks: NotebookRepository,
        embeddings: RecipeEmbeddings,
        embedder: Embedder,
        records: SearchRecords,
        *,
        strategy: str,
        min_closeness: float,
        timeout_s: float,
    ) -> None:
        self._kitchens = kitchens
        self._notebooks = notebooks
        self._embeddings = embeddings
        self._embedder = embedder
        self._records = records
        self._strategy = strategy
        self._min_closeness = min_closeness
        self._timeout_s = timeout_s

    def execute(self, command: SearchRecipesCommand) -> SearchAnswer:
        question = search_question(command.question)
        notebook_ids = self._notebook_ids(command.actor_user_id, command.scope)
        if not notebook_ids:
            logger.info("recipe search outcome=empty_scope scope=%s", command.scope.kind)
            return SearchAnswer(search_id=None, results=())

        embedded = self._embedder.embed_query(question, self._timeout_s)
        if not isinstance(embedded, Embedded):
            logger.warning("recipe search outcome=not_embedded class=%s", type(embedded).__name__)
            raise SearchQuestionNotEmbedded(embedded)

        raw = self._embeddings.search(
            notebook_ids,
            command.filters,
            self._embedder.model,
            embedded.vectors[0],
            SEARCH_LIMIT,
        )
        hits = tuple(
            SearchHit(
                recipe_id=hit.recipe_id,
                notebook_id=hit.notebook_id,
                title=hit.title,
                score=hit.score,
                mark=mark(hit.score, self._min_closeness),
            )
            for hit in raw[:SEARCH_LIMIT]
        )
        search_id = self._records.record(
            SearchEventRecord(
                feature=command.feature,
                scope_kind=command.scope.kind,
                model=self._embedder.model,
                strategy=self._strategy,
                min_closeness=self._min_closeness,
            ),
            [
                RecordedHit(recipe_id=hit.recipe_id, rank=rank, score=hit.score, mark=hit.mark)
                for rank, hit in enumerate(hits, start=1)
            ],
        )
        logger.info(
            "recipe search outcome=searched scope=%s results=%d close=%d",
            command.scope.kind,
            len(hits),
            sum(1 for hit in hits if hit.mark == "close"),
        )
        return SearchAnswer(search_id=search_id, results=hits)

    def _notebook_ids(self, user_id: UUID, scope: SearchScope) -> list[UUID]:
        if isinstance(scope, Kitchen):
            grant = AuthorizeKitchenAccessService(self._kitchens).execute(
                AuthorizeKitchenAccessCommand(
                    acting_user_id=user_id, kitchen_id=scope.kitchen_id, action="read_kitchen"
                )
            )
            kitchen = self._kitchens.get_kitchen_with_grant(grant, scope.kitchen_id)
            return self._notebooks.kitchen_ids_for(kitchen.id)
        if isinstance(scope, MyNotebooks):
            return self._notebooks.personal_ids_for(user_id)
        if isinstance(scope, OneNotebook):
            facts = self._notebooks.facts_for(user_id, scope.notebook_id)
            if facts is None:
                raise NotebookNotFoundError()
            notebook_view(facts)  # raises NotebookNotFoundError when the caller has no access
            return [scope.notebook_id]
        raise TypeError(f"unknown search scope {scope!r}")


class MarkSearchResultUsed:
    """Record that a result was used (FR-017c). Callers have already checked recipe access."""

    def __init__(self, records: SearchRecords) -> None:
        self._records = records

    def execute(self, search_id: UUID, recipe_id: UUID) -> bool:
        return self._records.mark_used(search_id, recipe_id)
