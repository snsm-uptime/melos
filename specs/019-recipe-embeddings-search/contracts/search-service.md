# Contract: recipe search (in-process use case)

This story adds no HTTP route. S-030 (assistant), S-044 (list search) and S-032 (MCP) call this use
case and add their own routes. The contract is what they may rely on.

## SearchRecipesService.execute(command) -> SearchAnswer

`application/recipe_search.py`

```text
SearchRecipesCommand
  actor_user_id: UUID
  scope: Kitchen(kitchen_id) | MyNotebooks() | OneNotebook(notebook_id)
  question: str                       # trimmed; empty → InvalidSearchQuestionError
  feature: "assistant" | "list_search" | "mcp" | "test"
  filters: SearchFilters = SearchFilters()
    author_id: UUID | None
    created_after: datetime | None
    created_before: datetime | None
    ingredient_names: tuple[str, ...]   # every one must be on the recipe (FR-015a)
    exclude_recipe_ids: tuple[UUID, ...]

SearchAnswer
  search_id: UUID | None             # None only when nothing was searched (empty scope)
  results: tuple[SearchHit, ...]      # 0 to 5, closest first
SearchHit
  recipe_id: UUID
  notebook_id: UUID
  title: str
  score: float                        # 1 - cosine distance
  mark: "close" | "weak"
```

### Order of steps

1. Validate the question and the filters (domain). On failure, raise `InvalidSearchQuestionError`
   or `InvalidSearchFiltersError` and record nothing.
2. Resolve the scope to notebook ids (research R13). If access fails, raise `KitchenNotFoundError`
   or `NotebookNotFoundError`, the same errors the lists raise (404).
3. If there are no notebook ids, return an empty answer without calling Gemini and record nothing.
4. Embed the question (`Embedder.embed_query`). A failure raises
   `SearchQuestionNotEmbedded` (below), and nothing is recorded.
5. Query: filters first, then exact cosine order, `LIMIT 5`, current embeddings of the configured
   model only.
6. Mark each hit against `SEARCH_MIN_CLOSENESS`.
7. Record one `search_event` (even with 0 results) and one `search_result` per hit, in the caller's
   transaction.

### Errors

| Raised | When | Consumer maps to (PRD 1.7) |
|---|---|---|
| `KitchenNotFoundError` / `NotebookNotFoundError` | no access, or does not exist | 404 |
| `InvalidSearchQuestionError` / `InvalidSearchFiltersError` | empty question, after > before | 422 |
| `SearchQuestionNotEmbedded(outcome)` | the question could not be embedded; `outcome` is the embedder's result, unchanged | mapped as capture already does (`api/api/routes/recipe_capture.py`): `LimitReached` → 429 + `Retry-After`; `Unavailable`, `AIProviderError` (also "not configured") → 503; `InvalidOutput` (wrong vector length, empty answer) → 422 |

No new AI error types are added: the result classes of `application/recipe_extraction.py` are the
single vocabulary for Gemini failures.

## MarkSearchResultUsed.execute(search_id, recipe_id) -> bool

Sets `used_at` once (later calls keep the first time). Returns `False` when the pair does not
exist. It is called by consumers that have already checked the person's access to the recipe. It
never raises for unknown ids, so it reveals nothing.

## Ports added to `application/ports.py`

```text
Embedder
  model: str
  dimension: int
  embed_documents(texts: Sequence[str], titles: Sequence[str], timeout_s) -> EmbedBatchResult
      # Embedded(vectors, token_counts, truncated) | LimitReached | Unavailable | InvalidOutput | AIProviderError
  embed_query(text: str, timeout_s) -> EmbedQueryResult
  count_tokens(text: str, timeout_s) -> int | None

EmbedTextStrategy
  name: str
  render(recipe: RecipeDetail) -> str

EmbeddingJobs
  enqueue(recipe_ids: Sequence[UUID]) -> None
  enqueue_notebook(notebook_id: UUID) -> None
  enqueue_missing(model: str, *, other_strategy_of: str | None = None) -> int
  claim(batch: int, lease_s: float) -> list[UUID]
  fail(recipe_id: UUID, wait_s: float, failure: str) -> None
  release_changed(recipe_id: UUID) -> None
  backlog() -> Backlog(count: int, oldest_enqueued_at: datetime | None)

RecipeEmbeddings
  content_for(recipe_ids) -> list[(RecipeDetail, updated_at)]
  write_if_current(recipe_id, read_version, model, vector, strategy, tokens) -> bool
  search(notebook_ids, filters, model, query_vector, limit) -> list[RawHit]

SearchRecords
  record(event, hits) -> UUID
  mark_used(search_id, recipe_id) -> bool
  delete_older_than(cutoff: datetime) -> int
  score_bands(width: float) -> list[Band(low, high, shown, used)]
```

The fakes (`FakeEmbedder`, `FakeEmbeddingJobs`, `FakeRecipeEmbeddings`, `FakeSearchRecords`) live
in `api/tests/embedding_fakes.py`. `FakeEmbedder` returns deterministic vectors from a hash of the
text, can be told to fail with a given result class, and counts calls.
