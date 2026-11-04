# Implementation notes: spec 019

## T001 · Live model check (2026-11-02)

One throwaway script outside the repo called the Gemini Developer API (API key, `google-genai`
2.32) with `models.embed_content(model="gemini-embedding-001", config={task_type:
RETRIEVAL_DOCUMENT, title, output_dimensionality: 768})`. The key was read from the worktree
`.env` by the script and never printed.

| Check | Result |
|---|---|
| Vector length with `output_dimensionality=768` | **768** (documents and queries) |
| Norm of the returned vector | about 0.59, so **not normalized**: the adapter must L2-normalize (research R1) |
| `statistics.token_count` | **empty** (`None`) on the Developer API |
| `statistics.truncated` | **empty** (`None`) |
| `metadata` | `None` |
| Two texts in one call | **succeeded**, two vectors of 768 |
| `models.count_tokens(model="gemini-embedding-001")` | works (4 tokens for "arroz con tomate") |

Consequences:

- The 768 dimension stands; no need to reopen it with the owner.
- The token count comes from the `count_tokens` fallback of research R2 on every embedding, one
  extra call per recipe. `input_truncated` stays false, since the service does not report it.
- `EMBED_BATCH_SIZE` keeps its default of 1 (plan). The Developer API accepts several texts for
  this model, so the operator may raise it later.

## Changes from the design documents

- `EmbeddingJobs.claim` returns `ClaimedJob(recipe_id, attempts, last_wait_s)` rather than bare
  ids, since the retry rule needs each job's last wait. `EmbeddingJobs.failure_counts()` was added
  for the `status` command.
- `Embedder` gained a `configured` property, so the worker can wait quietly without a key
  (FR-014) without calling the service.
- A job ends (`write_if_current`) or fails (`fail`) only while it is still claimed. An edit's
  enqueue clears the claim, so a worker that finishes the old content cannot drop the job for the
  new content, even when it waits on the edit's row lock.
- `enqueue_missing` (start-up catch-up and the `catch-up` command) also makes jobs that are
  already waiting due now, keeping their attempts and last wait. Found in the walk: without it,
  a restart after an outage did not make recipes searchable any sooner, against SC-003. It still
  counts only new rows, so a second run prints `queued=0`.
- The worker waits 0.5 s after a wake-up before claiming. The request's transaction commits only
  after the response, so an immediate claim can miss the new job (seen in the walk, below).
- The snapshot route builds its service inline, as before; the jobs port is passed there rather
  than through a new `deps.py` factory.
- Search filters compare ingredient names as `unaccent(lower(btrim(name)))` against
  `normalize_name` values, so "limon" finds "limón".
- An index on `search_result.recipe_id` was added so a recipe delete finds its records without a
  scan.

## T047 · Automated checks (2026-11-03)

| Run | Passed | Failed |
|---|---|---|
| HEAD `57ee845`, before this story (its own sources mounted, separate scratch database) | 1451 | 2 |
| This branch | 1591 | 2 |

The same two tests fail on both: `test_recipe_capture_integration.py::test_empty_and_too_long_text_are_refused_with_no_assistant_call`
and `::test_vocabulary_lists_the_controlled_values`. They expect a paste limit of 5,000, and this
worktree's `.env` sets `RECIPE_TEXT_MAX_CHARS=10000`. Not caused by this story. The live 768 check
(`test_live_model_returns_768_values`) ran and passed, since the key is set. `uv run ruff check .`
and `ruff format --check .` are clean.

## T048 · Quickstart walk (2026-11-03)

Worktree stack `melos-kitchen-vectors` (API 8050), invented accounts `walk_ana_…@example.com` and
`walk_ben_…@example.com`, invented recipes. No browser: the walk used the API and the operator
command.

| Step | Result |
|---|---|
| 0. Automated checks | Passed (T047) |
| 1. Model check | Passed (T001, and the live test in the suite) |
| 2. Saving during an outage | Passed. With an invalid key (a scratch Compose override, `.env` untouched): saves median 13 ms, edit 19 ms, against 15 ms and 22 ms with the service answering. `status` showed the recipes waiting with failures of class `InvalidOutput`, not `AIProviderError` as the quickstart expected: Gemini answers a bad key with HTTP 400, which the shared mapping (unchanged from the extractor) files as unusable output. Waits grew 60 s → 90 s. Logs held class names, counts and request refs only |
| 3. Healing and catch-up | Passed. With the key back, the waiting recipes were embedded when their waits ran out, and `catch-up` printed `queued=0`. SC-001: 21 recipes saved in a burst, 95th percentile 9.1 s and maximum 9.4 s from save to embedding (one embed call and one token count per recipe, in sequence). Tokens 73–88, nothing truncated, norm 1.0, 768 values |
| 4. Search scope and filters | Passed, with the live embedder inside the api container. My notebooks returned 5, all from Ana's notebook; one notebook of Ben's as Ana gave `NotebookNotFoundError`; Ana's kitchen as Ben gave `KitchenNotFoundError`; the chicken + rice filter returned only a recipe with both; a kitchen with no notebook returned an empty answer with no record. "postre dulce con leche" ranked "Arroz con leche" first (0.67). Each search wrote one `search_event` |
| 5. Edit and delete | Passed. The edited recipes ("Tomato rice with peas", the one edited in the outage) carry current embeddings of their new content. A deleted recipe left no `recipe_embedding`, `embedding_job` or `search_result` row. "Never returned while stale" is covered by the integration tests, not timed live |
| 6. Snapshot | Passed. A 26-recipe snapshot answered in 39 ms; all 26 copies were embedded 11.2 s after it |
| 7. Records and report | Passed. `score-report` printed four bands (0.55–0.75); `cleanup` printed `deleted=0` (no record was 180 days old; the age rule is covered by the integration tests); a width of 0 is refused with exit 2 |

Observations, not changed:

- Live scores for these short recipes sit between about 0.55 and 0.71. The provisional minimum of
  0.65 marks some plain matches "close" (a rice dish for "chicken and rice"). The records are
  there to set it from evidence (FR-017d).
- The first request right after a sign-in sometimes answers 401, and the next one succeeds. The
  session row seems to commit just after the response is sent. Auth code and `get_db` are not
  changed by this story; the walk waited 0.5 s after sign-in.
- The dev seed (`scripts/seed_dev_user.py`) fails at start with `SaveRecipeDraft.__init__() missing
  1 required keyword-only argument: 'units'`. It predates this story (the seed does not pass the
  `units` argument added in spec 055).

## T050 · Drafts for the owner (not applied)

These need the owner's explicit approval as separate changes.

**Constitution, `.specify/memory/constitution.md`**: add under "Exceptions", and bump the version
to 1.1.0 (a new documented exception to a principle):

> **Approved exceptions**
>
> - **In-api background worker** (principle 1, "No queue, no worker"). Approved in writing by the
>   project lead on 2026-11-02 (specs/019-recipe-embeddings-search/spec.md, Clarifications).
>   Scope: background jobs that run as a thread inside the `api` process and keep their state in
>   Postgres, first the recipe embedding worker and the daily clean-up of search records. Still
>   four services and no queue system. Each job retries by the shared rule in
>   `api/domain/retry.py`. Documented in `api/api/worker.py`.

and in principle 1, change "Only four services: `db`, `api`, `ui`, `mcp`. No queue, no worker." to:

> Only four services: `db`, `api`, `ui`, `mcp`. No queue. Background work runs only as a thread
> inside `api` with its state in Postgres (see Exceptions).

**PRD `dev/docs/prd.md` §1.1**: change "No queue and no worker." to:

> No queue. One worker thread inside the api makes recipe embeddings and retries them later, so
> saving never waits for or fails on Gemini (spec 019).

**PRD Appendix D**: replace the first item with:

> - **✓ Embedding model** (2026-11-02, spec 019): `gemini-embedding-001` at 768 dimensions
>   (`output_dimensionality=768`), checked with a live call. The Developer API returns those
>   vectors unnormalized and without token statistics, so the adapter normalizes them and counts
>   tokens with `count_tokens`. The chat model stays open.
