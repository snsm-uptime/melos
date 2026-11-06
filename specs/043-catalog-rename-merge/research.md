# Research: Catalog Management (rename and merge ingredient names)

Spec: [spec.md](spec.md). Each entry: Decision, Rationale, Alternatives considered.

## R1. What a recipe line stores after a merge

**Decision**: A recipe line keeps carrying a plain name, and that name is always the ingredient's
**kept name** (`ingredient.name`). Merge and rename rewrite `recipe_ingredient.name` from the old
name to the kept name in the affected notebooks. What a line *shows* is resolved at read time:
the ingredient's name variant in the recipe's language, or the kept name when it has none (FR-006).

**Rationale**: AGENTS.md and PRD 1.6 say recipe and shopping list lines carry the name, not an id;
this keeps that rule. With every line on a kept name, "a line refers to an ingredient of the
catalog" (SC-005) is one equality, delete-if-unused (FR-013) is one count, and the shopping list
groups by kept name with no extra lookup. Display by language needs only one small map per notebook
(kept name → variants), read with the recipe.

**Alternatives considered**: (a) Lines keep their own wording ("cebolla") and every reader resolves
any name to its ingredient: no rewrite on merge, but every count, group and delete check must go
through the other-names table, and two lines of one ingredient can carry different text. Rejected
as more reads everywhere for no user gain. (b) Lines point at `ingredient.id`: breaks the PRD rule
and every existing reader. Rejected.

## R2. Where other names live

**Decision**: New table `ingredient_name` (one row per other name: name variant or alternative
spelling), owned by an `ingredient` row; `ingredient` gains `language` (`en`/`es`/null), the
language of the kept name. The variant for language L is `ingredient.name` when
`ingredient.language = L`, else the `ingredient_name` row with `kind = 'variant'` and
`language = L`. A name is unique across kept names and other names of one notebook: within each
table by a unique index on `(notebook_id, name)`, and across the two tables by the domain check
`domain.ingredient_catalog.name_taken` run under the row locks of R6. See
[data-model.md](data-model.md).

**Rationale**: The kept name stays where every current reader looks (`ingredient.name`), so the
existing catalog reads, the S-070 catalog page and the admin ingredients table keep working
unchanged. Other names are only read by matching, display and the management page.

**Alternatives considered**: All names as rows of one table with a `kept` flag: changes every
current catalog read. Rejected. JSONB array on `ingredient`: no unique index across names. Rejected.

## R3. Recipe language

**Decision**: `recipe.language` (`en`/`es`), added nullable by the migration, filled in the same
migration by the fallback rule of FR-005a (kitchen `content_language` for a kitchen notebook, the
author's `users.language` for a personal one, else `es`), then set `NOT NULL`. The extractor
returns `language` with each draft (prompt gains one field), the draft carries it, save stores it,
and recipe edit (spec 027) can change it. A one-off operator command,
`python -m scripts.recipe_languages detect`, then asks the model for each recipe's language once and
stores it in `recipe.proposed_language` where it differs from the fallback. The recipe page shows
"Detected: {language}. Apply?"; a person applies or dismisses it (spec Q5 as refined by analyze C1,
constitution 5: the model never changes saved data by itself).

**Rationale**: Filling by the fallback in the migration means no recipe is ever without a language,
so no reader needs a null branch; the model pass only proposes. The command copies the
`scripts.embeddings` pattern (constitution 1: no queue, no worker beyond the existing thread). A
`recipe.language_detected_at` column makes the command safe to repeat and resume.

**Alternatives considered**: Detect in the embedding worker thread: mixes two concerns and needs a
job table. Rejected. Detect with a fixed word list: unreliable on short recipes. Rejected. Leave
null until set: every display needs a null branch, and spec Q5 chose the model.

## R4. Matching with other names (FR-008)

**Decision**: `domain.ingredient_catalog` gains a `CatalogIndex`: for one notebook, a map from the
normalized key of every name (kept and other, with their S-018 singular forms) to the kept name.
`match_line`, `propose_entry` and `names_to_add` take the index instead of a bare list of kept
names; a hit on an other name returns the kept name and is listed as a change
(`NameChange(from_name="cebollas", to="onion")`), as today. The extractor still receives kept names
plus other names in its catalog TOON, so the model can propose "onion" for "cebolla"; the domain
confirms by the index. `resolve_line_names` resolves to kept names through the index too.

**Rationale**: One place for the rule (constitution 3); every caller (capture, URL capture, save,
edit, share/copy, notebook join) already passes the result of `names_for_notebook`, so the port
change is `names_for_notebook` → `index_for_notebook` with the same call sites
(`application/recipe_capture.py`, `recipe_capture_url.py`, `recipe_save.py`, `recipe_manage.py`,
`recipe_share.py`, `notebook_invites.py`).

**Alternatives considered**: Let the model decide matches of other names: violates the S-018 rule
that the domain confirms every proposal. Rejected.

## R5. Merge across notebooks (FR-002a)

**Decision**: `MergeIngredientsService` (application) takes the actor, the merged name, the kept
name, the confirmed languages, and the set of notebook ids shown in the preview. A preview call
(`POST .../merge-preview`) returns the notebooks the actor can write to whose catalogs have both
names (by the R4 index), with the count of recipes using the merged name in each. The confirm call
re-checks each notebook and merges each in its own savepoint: one notebook failing its re-check
(name gone, access lost) is skipped and reported; the rest commit together in one transaction.

**Rationale**: Matches the spec's "each notebook is complete or not done; the result lists skipped
ones". Notebooks are few per person (tens), so a single request is fine (SC-004: 10 notebooks, 200
recipes, under 2 s: a few UPDATEs per notebook).

**Alternatives considered**: One transaction for all, failing all on one conflict: the spec asks to
skip. Rejected. Background job: needs a worker. Rejected.

## R6. Concurrency

**Decision**: Every catalog write of this story locks the notebook's `ingredient` rows touched
(`SELECT ... FOR UPDATE` on the two ingredient rows) and re-reads both names before changing
anything; a missing name gives `409 name_changed` (FR-015) for single-notebook actions, and a
"skipped" entry for a notebook in a merge. Recipe saves that add names already insert with
`ON CONFLICT DO NOTHING` (spec 020); a save racing a merge may add the merged name back as a new
kept name: the save re-resolves through the index inside its transaction, so the window is the
single statement; accepted and documented in the spec edge cases.

**Rationale**: Same pattern as spec 070 place writes and spec 058 ownership passing. Recipe edit
locks (spec 027) are not taken: the spec says a merge goes ahead and the editor's save matches.

## R7. Shopping list display by viewer language (FR-007, FR-007a)

**Decision**: Cart-based lines keep grouping by kept name (R1, unchanged consolidation). When the
active list is refreshed, each cart-based `shopping_list_item` stores `names` (JSONB,
`{"en": ..., "es": ...}` for the variants that exist) next to `name` (kept name). The list view
picks `names[viewer language]` or `name`. Hand items have `names = {}` and show `name`. Places
(spec 070) are looked up by every name of the item (kept name first, then variants), so the
viewer's choice applies under any name. Closed lists keep their stored `names` (FR-016).

Grouping across notebooks: two notebooks may both have "onion" but only one merged "cebolla" into
it; lines group by kept name, so "cebolla" from the unmerged notebook stays its own line. The
`names` of a group come from the kitchen notebook with the most recipes in the group whose
ingredient has variants (ties broken by notebook id), so the choice is stable when the cart order
changes. Lines are sorted by `name_sort_key` of the name each viewer sees (FR-007).

**Rationale**: Per-viewer display without a per-viewer list; the list remains one shared row set.

**Alternatives considered**: Translate at read time from the catalogs: a closed list would change
when catalogs change, against FR-016. Rejected.

## R8. Places on merge and rename (FR-009, FR-012)

**Decision**: In the same transaction, `ingredient_place` rows keyed by the merged (or old) name
are moved to the kept (or new) name for each person who has no row for the kept name; rows for
the old name are kept when the person also has one for the new name (FR-009: any other choice is
unchanged; lookups use the kept name first, so the leftover row does nothing). Places are per person, not per notebook, so this runs once per
merge, not per notebook. The person-wide catalog page (spec 070) lists kept names only; other
names appear under their ingredient.

## R9. Suggested pairs (FR-009a–d)

**Decision**: New port `IngredientPairSuggester` in `application/ports.py`, adapter
`adapters/llm/gemini_pair_suggester.py` with prompt template
`adapters/llm/prompts/ingredient_pairs_system.md` (README's one-template-per-prompt rule). Input:
the notebook's kept names with their language (or null) as TOON; output: JSON list of
`{en, es}` pairs. The domain (`domain.ingredient_catalog.filter_pairs`) drops pairs whose names are
not both kept names of the catalog, are the same ingredient, or are in `ingredient_pair_dismissal`.
Catalogs over 300 names are sent in batches of 300 (same batching idea as recipe page parts). A
fake suggester serves application tests; AI eval fixtures go in
`api/tests/fixtures/ai_eval/pairs/` (constitution 6).

**Rationale**: Same structure as the extractor (port, Gemini adapter, prompt file, fake); the model
proposes and the domain filters (constitution 5). Model name from `GEMINI_CHAT_MODEL`.

## R10. Embeddings

**Decision**: Recipes whose lines change by merge or rename are enqueued on `embedding_job` in the
same transaction, as recipe edit does (spec 019 FR-002).

## R11. UI

**Decision**: The `/ingredients` page (spec 070) gains a notebook selector ("All" keeps today's
place view; picking a writable notebook shows its catalog with Rename, Merge, Delete and the
ingredient's other names, plus "Suggest pairs"). Dialogs reuse `ActionDialog` and `Sheet`; the
table reuses `DataTable` (spec 066). The recipe detail shows and edits the language (spec 027
editor). Strings in `ui/lib/i18n/` (en, es).
