# Feature Specification: Recipe embeddings and search pre-filtered by kitchen

**Feature Branch**: `019-recipe-embeddings-search` (built on `worktree-kitchen-vectors`)

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "@dev/docs/backlog.yaml @dev/docs/prd.md 019"

**Backlog story**: S-019 (Must). **PRD**: §1.5 flows A, B, E, F and G, §1.6 (`recipe_embedding`), §1.7, Appendix B.3, Appendix D (embedding model).

**Related**: Spec 020 FR-015 (recipes saved before embeddings exist must be picked up), spec 027 FR-016 (editing re-embeds, deleting removes the recipe from search), spec 035 FR-013 (snapshot copies must be searchable). Consumers that come later: the kitchen assistant (S-030), semantic search in the recipe list (S-044), copy to notebook (S-048) and the MCP service (S-032).

## Summary

Every recipe gets a meaning-based search fingerprint (an *embedding*), so that later features can find "the recipes about this question" instead of matching words. This story builds the fingerprints and the search behind them, and keeps them correct as recipes are saved, edited, copied and deleted. A search covers one scope, which follows where the person searches from (a kitchen, their personal notebooks, or one notebook), looks only at notebooks the person may read, is narrowed first by the filters given, and returns the five closest recipes.

Members see nothing new in this story. What they get is that saving and editing a recipe keep working exactly as today, even while the assistant service is down, and that the assistant and search stories that follow have complete, private and current data to work on.

## Clarifications

### Session 2026-11-02

- Q: Which embedding model? → A: `gemini-embedding-001`, replacing the configured default `text-embedding-004`, which the provider reportedly no longer serves. The PRD's 768 dimensions are kept. This closes the PRD Appendix D open item once one live call confirms the model returns 768 values. Approved by the owner (a Gemini model change needs approval, AGENTS.md).
- Q: What does a member experience when the embedding call fails or times out on Save or Edit? → A: The save or edit succeeds and shows no error. A worker left running inside the api retries the embedding later.
- Q: How are recipes that have no embedding caught up (saved before this story, failed, or copied by a snapshot)? → A: A catch-up runs when the api starts, without delaying start-up, and can also be run by a command. Running it again is safe.
- Q: With several ingredient names in the filter, must a recipe contain all of them or any one? → A: All of them. A search screen that offers this filter shows each chosen ingredient as a chip below the search bar, with a close icon that removes that ingredient from the filter, so it is clear every result holds all the chosen ingredients. The chips are only offered from ingredients already in the searched notebooks' catalogs.
- Q: Should search always return the five closest recipes, or drop those below a minimum closeness? → A: Return up to five, each marked "close" or "weak" against a configured minimum. Every search's results (rank, score, mark) are recorded, together with which result the person or the assistant then used, so the minimum can later be set from evidence instead of a guess.
- Q: When a recipe keeps failing to embed, does the worker retry forever or give up? → A: Retry forever. After each failed try the wait grows by 50%, up to a cap of two hours. This is the default retry rule for any background job of the app that may take longer, not only embeddings.
- Q: Can one search mix a kitchen's notebooks with personal ones? → A: No; the scope follows where the person searches from. On a kitchen: all of that kitchen's notebooks. On the Notebooks tab: all the notebooks it lists (the person's personal notebooks). On one notebook: only that notebook's recipes.
- Q: How long are search result records kept? → A: 180 days, then deleted by a daily clean-up.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every recipe becomes findable (Priority: P1)

A member saves a captured recipe, edits one, or already has recipes saved before this story. Each of them gets an embedding without the member doing anything, and an edited recipe's embedding follows its new content.

**Why this priority**: Without embeddings there is nothing to search; the assistant (S-030) and semantic search (S-044) both depend on this.

**Independent Test**: Save a recipe, edit another, and start the service against a database holding older recipes with no embeddings; check that each recipe ends up with one current embedding and that saving felt the same as before.

**Acceptance Scenarios**:

1. **Given** a member saves a confirmed draft, **When** the save completes, **Then** the recipe is stored as today, and within a minute it has an embedding of its title, ingredients and steps.
2. **Given** a recipe with an embedding, **When** a member edits its title, ingredients or steps, **Then** the old embedding stops being used at once, and a new one made from the edited content replaces it.
3. **Given** recipes saved before this story, **When** the api starts, **Then** every one of them is embedded without delaying start-up, and no recipe is embedded twice.
4. **Given** a repeated Save of the same draft (the same save key), **When** it returns the recipe already stored, **Then** no second embedding is made.

---

### User Story 2 - Search returns only what the person may read (Priority: P1)

A later feature asks for "the five recipes closest to this question" on behalf of a person, in one scope that follows where they search from: a kitchen (all its notebooks), the Notebooks tab (all their personal notebooks) or one notebook. The answer holds only recipes from notebooks that person may read, narrowed first by the filters given.

**Why this priority**: The search is the deliverable that S-030 and S-044 call. A recipe from another household appearing in it would break the privacy promise of the whole product (PRD §3).

**Independent Test**: With two kitchens and two people's personal notebooks, run searches for each person and check that results never include a recipe from a notebook they do not belong to, whatever filters are passed.

**Acceptance Scenarios**:

1. **Given** a member of kitchen A, **When** they search within kitchen A, **Then** results come only from kitchen A's notebooks, at most five, closest first.
2. **Given** a person who is not a member of kitchen B, **When** they search within kitchen B, **Then** they get the same not-found answer as for a kitchen that does not exist.
3. **Given** a person searching one notebook they do not belong to, **When** it runs, **Then** it answers not-found and returns nothing, the same as for a notebook that does not exist.
3a. **Given** a person who owns two personal notebooks, is a member of a third and belongs to a kitchen, **When** they search from the Notebooks tab, **Then** results come from those three personal notebooks only, never from the kitchen's notebooks.
3b. **Given** a person on one notebook's page, **When** they search, **Then** results come from that notebook only, even when they belong to other notebooks with closer recipes.
4. **Given** filters for author, date range, ingredient names or recipes to exclude, **When** a search runs, **Then** only recipes matching every filter are compared, and the five closest of those are returned.
5. **Given** fewer than five recipes match the filters, **When** a search runs, **Then** all matching recipes are returned, closest first, and none from outside the filters are added.
6. **Given** an ingredient filter of "chicken" and "rice", **When** a search runs, **Then** only recipes containing both are compared; a recipe with chicken and no rice is never returned.
7. **Given** a kitchen where no recipe has an embedding yet, **When** a search runs, **Then** it returns an empty result, not an error.

---

### User Story 3 - An outage never blocks saving, and heals on its own (Priority: P2)

While the assistant service is slow, out of quota or unreachable, members keep saving and editing recipes. When the service comes back, the recipes left without an embedding are embedded without anyone acting.

**Why this priority**: Saving recipes is the core of the app; search is secondary. The owner decided search may lag but saving must not fail.

**Independent Test**: Make the embedding service fail, save and edit recipes, then make it succeed again; check that every save succeeded with no error shown and that all recipes become searchable afterwards.

**Acceptance Scenarios**:

1. **Given** the embedding service is failing, **When** a member saves or edits a recipe, **Then** the save or edit succeeds, no error is shown, and it takes no noticeably longer than when the service answers.
2. **Given** recipes left without an embedding by a failure, **When** the service answers again, **Then** the worker embeds them without anyone acting.
3. **Given** the service keeps failing, **When** the worker retries a recipe, **Then** each wait is 50% longer than the last (1 min, 1.5 min, 2.25 min, …) until it reaches 2 hours, after which it retries every 2 hours without giving up; a "try again later" wait from the service is honoured when it is longer.
4. **Given** the api restarts while recipes are waiting for an embedding, **When** it starts again, **Then** those recipes are still embedded; nothing is lost.

---

### User Story 4 - Snapshot copies are searchable (Priority: P2)

A member adds one of their personal notebooks to a kitchen as a snapshot. Every copied recipe becomes part of the kitchen's search like any other recipe of the kitchen.

**Why this priority**: Spec 035 FR-013 promises it; a snapshot is the main way personal recipes reach a kitchen.

**Independent Test**: Add a snapshot of a notebook with several recipes; check that adding it takes as long as before this story, and that the copies are then found by a kitchen search.

**Acceptance Scenarios**:

1. **Given** a member adds a snapshot of a notebook with 50 recipes, **When** the snapshot is created, **Then** it is created as quickly as before this story, and the copies become searchable within the kitchen within 5 minutes (SC-006).
2. **Given** a snapshot copy is edited, **When** a search runs, **Then** it reflects the copy's new content, and the original recipe's embedding is unchanged.

---

### User Story 5 - Embedding strategies can be compared (Priority: P3)

The owner wants to compare ways of turning a recipe into the text that is embedded (for example the structured form the assistant reads against plain text), to see which gives better search and uses fewer tokens.

**Why this priority**: It supports the course's "test and improve" evaluation (PRD §1.8 item 5) but no member depends on it.

**Independent Test**: Embed recipes, read their stored records, and check that each names its strategy, its model, its input size and when it was made.

**Acceptance Scenarios**:

1. **Given** a recipe has been embedded, **When** its record is read, **Then** it names the model, the strategy used, the input token count and the time it was made.
2. **Given** the configured strategy is changed, **When** the catch-up runs, **Then** recipes embedded with another strategy are not touched unless asked; a command can re-embed them with the configured one.

---

### Edge Cases

- A recipe is deleted while its embedding is being made: the embedding is discarded and never appears in search.
- A recipe is edited twice quickly: only an embedding of the latest content is kept and used.
- A notebook or a kitchen is deleted: the embeddings of its recipes go with them.
- A person leaves a kitchen or a personal notebook, or is removed: their next search no longer includes it.
- An archived kitchen: its recipes stay searchable for its members, as its lists stay readable.
- The question text of a search cannot be embedded (service down, quota, bad answer): the search fails with the PRD §1.7 message for that case, and nothing is saved.
- The configured model or dimension does not match the stored embeddings (for example after a model change): stored embeddings of another model are never compared with the new model's question; recipes are re-embedded with the configured model.
- The service returns a different number of values than configured: that answer is refused and counted as a failure; nothing is stored.
- No API key or no embedding model is configured (common in local development and tests): saving and editing still work, search answers that it is unavailable, and the worker waits quietly instead of failing in a loop.
- Several api processes run at once: each recipe is embedded once, not once per process.
- A recipe with an empty step list or a single line still gets an embedding.
- All five results are weak: they are still returned, all marked weak, so the assistant can say the recipes don't cover the question and still name the closest one.
- A search returns nothing: no result records are written, but the search itself is counted so empty searches are visible.
- A recipe is deleted: its search result records go with it.
- A personal recipe with a vague-only ingredient list is embedded like any other.

## Requirements *(mandatory)*

### Functional Requirements

**Making and keeping embeddings**

- **FR-001**: Every recipe in every notebook, personal and kitchen, MUST get one embedding per configured model, made from its title, base servings, ingredient lines and steps.
- **FR-002**: Saving a confirmed draft (spec 020) MUST lead to an embedding of the new recipe. The attempt MUST NOT add noticeable time to the save (within 10%, SC-002), and its failure MUST NOT fail the save or show an error.
- **FR-003**: Editing a recipe's content (spec 027) MUST stop its current embedding from being used at once, and lead to a new one made from the edited content. A failure MUST NOT fail the edit or show an error.
- **FR-004**: A recipe whose content changed MUST never be returned on the strength of its old embedding. Until it is re-embedded it is left out of search.
- **FR-005**: Deleting a recipe MUST remove its embeddings in the same step (spec 027 FR-016). Deleting a notebook or a kitchen MUST remove the embeddings of its recipes.
- **FR-006**: Recipes copied by a snapshot (spec 035) MUST get their own embeddings, made after the snapshot is created. Adding a snapshot MUST NOT wait for them. A copy's embedding is independent of the original's.
- **FR-007**: A repeated Save that returns the recipe already stored MUST NOT make a second embedding.

**Retry worker and catch-up**

- **FR-008**: A worker running inside the api MUST find recipes that lack a current embedding for the configured model and embed them. It adds no new service and no external queue (see Assumptions on the constitution).
- **FR-009**: When an attempt fails, the worker MUST retry the recipe later, with no limit on the number of tries. Each wait MUST be 50% longer than the one before, starting from a configured first wait (1 minute by default) and capped at 2 hours. When the service gives a "try again later" wait, the worker MUST wait at least that long. Each attempt is a single call to the service (PRD §1.7); the retry is a later attempt, not a loop around one call. A success resets the recipe's wait.
- **FR-009a**: This retry rule (first wait, 50% growth, 2-hour cap, retry forever, service wait honoured) MUST be one shared rule that other background jobs of the app reuse by default, with the first wait, growth and cap configurable per job.
- **FR-009b**: The number of recipes waiting for an embedding, and the longest wait among them, MUST be visible to an operator (in the logs at each pass, and from the command), so a recipe that never succeeds is noticed.
- **FR-010**: A catch-up of every recipe without a current embedding MUST start when the api starts, without delaying the api's readiness or health check.
- **FR-011**: The same catch-up MUST be runnable as a command by an operator. Running it again, or while the worker runs, MUST be safe: no recipe is embedded twice and none is skipped.
- **FR-012**: With several api processes, each recipe MUST be embedded by one of them only. A restart MUST NOT lose recipes waiting for an embedding.
- **FR-013**: The command MUST offer a way to re-embed recipes made with another model or strategy. By default the catch-up re-embeds only recipes with no embedding for the configured model.
- **FR-014**: With no API key or no embedding model configured, saving and editing MUST still work, and the worker MUST wait without logging an error on every pass.

**Search**

- **FR-015**: Search MUST take a person, exactly one scope, the question text, and optional filters: author, created after, created before, ingredient names, and recipes to exclude (PRD flow F). The scope follows where the person is searching from:
  - **Kitchen**: every notebook of that kitchen (searching from a kitchen's page, and the assistant).
  - **My notebooks**: every personal notebook the person owns or is a member of, the notebooks the Notebooks tab lists (searching from the Notebooks tab).
  - **One notebook**: only that notebook's recipes, personal or kitchen (searching from a notebook's page).
  A search never mixes scopes: kitchen notebooks never appear in a "My notebooks" search, and personal notebooks never appear in a kitchen search.
- **FR-015a**: With several ingredient names given, a recipe MUST contain every one of them (in any line, vague or measured) to be compared. Names are compared in their normalized form (trimmed, lower-case, singular).
- **FR-015b**: Any screen that offers the ingredient filter (first S-044, built later) MUST show each chosen ingredient as a chip below the search bar, with a close icon that removes it from the filter and re-runs the search. Ingredients are offered only from the catalogs of the notebooks being searched. This story builds no screen; it fixes the rule so S-044 follows it.
- **FR-016**: Search MUST check access before anything else. A kitchen the person does not belong to, or a single notebook they may not read, MUST give the same not-found answer as one that does not exist. "My notebooks" is worked out from the person's memberships at the time of the search, never from a list the caller sends. No filter can widen the scope.
- **FR-017**: Search MUST first narrow recipes by every filter given, then rank the remaining recipes by closeness of meaning to the question, and return at most five, closest first, each with its closeness score and a mark: "close" when the score reaches the configured minimum, "weak" otherwise. Weak results are returned, not dropped.
- **FR-017a**: The minimum closeness MUST come from configuration, not code, so it can be changed without a release. Its first value is a provisional one chosen during planning.
- **FR-017b**: Every search MUST record, for each result returned: the search it belongs to, the recipe, its rank, its score, its mark, the model and strategy, which feature asked (assistant, list search, MCP, or a test), and when. A search with no results MUST still be counted, with its asking feature and time. The question text and the person's identity MUST NOT be recorded.
- **FR-017c**: The system MUST let a consumer record that a result was used (for example the assistant cited it, or the person opened it from the results). Consumers that come later (S-030, S-044, S-032) MUST report use this way; this story provides the way to record it.
- **FR-017d**: An operator MUST be able to read, from these records, how often results were used at each score band (for example in steps of 0.05), to choose a default minimum. Records are internal and never shown to members.
- **FR-017e**: Search result records MUST be deleted 180 days after the search, by a clean-up that runs at least once a day inside the api and follows the shared retry rule (FR-009a) when it fails.
- **FR-018**: Search MUST compare the question only with embeddings made by the same model; recipes without a current one are left out, as FR-004 says.
- **FR-019**: The question MUST be embedded the same way recipes are, by the same model. When it cannot be embedded, search MUST fail with the matching error of PRD §1.7 (limit reached, with how long to wait; service not answering; unusable answer), and no member input is lost.
- **FR-020**: Filters on main ingredients and cuisines are out of scope (S-061, Appendix E).

**Recording and privacy**

- **FR-021**: Each embedding MUST record its recipe, model, strategy used, input token count and when it was made (PRD §1.5 E, §1.6).
- **FR-022**: The text sent to be embedded MUST be built from the same single source as the assistant's recipe context, by a swappable strategy whose default is the structured form of PRD Appendix B.3.
- **FR-023**: Logs MUST hold only outcomes and counts: never recipe text, question text, embedding values, keys or service messages (constitution §4).
- **FR-024**: Embeddings MUST NOT be exposed to members, through any screen, route or tool (PRD Appendix A, RecipeEmbedding: internal).
- **FR-025**: The embedding dimension MUST come from configuration (768) and be checked against every answer; an answer of another size is a failure and is not stored.

### Key Entities

- **Recipe embedding**: The search fingerprint of one recipe for one model. Holds the recipe it belongs to, the model, the vector of numbers, the strategy that built its input, the input token count and when it was made. At most one per recipe and model. Goes when its recipe goes. Internal only.
- **Embedding strategy**: A named way of turning a recipe into the text that is embedded. The default is the structured recipe form also given to the assistant. Its name is recorded on every embedding.
- **Search request**: A person, one scope (a kitchen, "My notebooks", or one notebook), the question, and optional filters. Not stored.
- **Search result**: Up to five recipes from the allowed notebooks, each with its closeness score and its "close" or "weak" mark, closest first.
- **Search result record**: One row per result returned by a search: search id, recipe, rank, score, mark, model, strategy, the asking feature, time, and whether it was later used. No question text and no person. Goes when its recipe goes, or 180 days after the search. Internal only; used to choose the default minimum closeness.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the embedding service answering, 95% of newly saved or edited recipes are searchable within 1 minute of the save, and all within 5 minutes.
- **SC-002**: During a full embedding outage, 100% of saves and edits succeed with no error shown, and their response time stays within 10% of the time with the service answering.
- **SC-003**: After an outage ends, every recipe saved or edited during it is searchable, with no one acting, within its current wait plus 5 minutes: within 15 minutes for an outage under 10 minutes, and never more than 2 hours 5 minutes for any outage. Restarting the api or running the command makes them searchable sooner.
- **SC-004**: Across a test set of at least three kitchens and three personal notebooks belonging to different people, zero search results come from a notebook the searching person may not read, for every combination of filters.
- **SC-005**: After the catch-up on a database of 500 existing recipes, 100% have exactly one current embedding for the configured model, and running the catch-up a second time makes no new embeddings.
- **SC-006**: Adding a snapshot of a 50-recipe notebook takes no longer than before this story (within 10%), and all 50 copies are searchable within 5 minutes.
- **SC-007**: A search over a kitchen with 1,000 recipes returns its results in under 1 second, apart from the time to embed the question.
- **SC-008**: An edited recipe is never returned by a search on the strength of its pre-edit content: 0 such results in a test that edits and searches repeatedly.
- **SC-009**: 100% of results returned by searches have a record with their score and mark, and an operator can produce the "used share per score band" summary in under 5 minutes.

## Assumptions

- **Worker and the constitution**: Constitution principle 1 and PRD §1.1 say "No queue, no worker". The owner decided on 2026-11-02 that a worker left running inside the api retries embeddings. This spec reads that as a background task in the existing api process, using the existing database for its state: no fifth service and no queue system. It still needs an exception documented under the constitution's "Exceptions" section (and the PRD §1.1 wording updated), which is a separate change needing approval.
- **Model**: `gemini-embedding-001` at 768 dimensions, set through configuration, never in code. If a live call shows it cannot return 768 values, the dimension is reopened with the owner before the stored shape is fixed.
- **Scope of embedding**: All recipes are embedded, personal ones included, because semantic search in personal notebooks (S-044) and the MCP service need them. The cost is accepted.
- **No member-facing surface**: This story adds no screen, page or public route. The assistant (S-030), semantic search (S-044) and MCP (S-032) add their own and call this search. Tests and the command exercise it directly.
- **Kitchen archive**: Recipes of an archived kitchen stay embedded and searchable for its members, since its notebooks stay readable.
- **Reading access** follows the existing notebook rules (spec 056, PRD §3): a personal notebook for its owner and members, a kitchen notebook for the kitchen's members. The admin dashboard exception does not apply to search.
- **Timeouts**: Embedding a recipe or a question uses the configured text timeout (10 s, PRD §1.7).
- **Copies by "Copy to notebook"** (S-048) will use the same path as snapshots when that story is built.

## Out of Scope

- The assistant, its citations and "recipe removed" (S-030); semantic search in the recipe list (S-044); the MCP tools (S-032); copy to notebook (S-048).
- Main ingredient and cuisine filters (S-061).
- Choosing between strategies; this story only records them so they can be compared.
- Editing the constitution or the PRD; this spec only records the decisions and the needed exception.
