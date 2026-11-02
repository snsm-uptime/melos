## 171026

- Decisions (AI/search): embeddings are always TOON-based behind an `EmbedTextStrategy` (Strategy pattern, A/B-testable, tracks strategy and input tokens); pgvector searches are always pre-filtered by `kitchen_id`, plus optional creator, date range, ingredients, categories and exclusions.
- Decisions (MCP): separate `mcp` container (port 9000 in dev, nginx in prod) with per-user Bearer API keys scoped to the user's own kitchens; exposes kitchen/member ops, `capture_recipe` (capture + save), cart edits, shopping-list read/edit and chat `ask`. MCP is Must scope; the API-key UI on Account is Should.
- Decisions (shopping lists and chat): finalized shopping lists are stored as snapshots (`shopping_list` + `shopping_list_item`, `closing_date`); the kitchen assistant queries them via a `shopping_list_history` tool and returns TOON that the UI renders as clickable cards.
- Finished changes: PRD appendices A, B.2, B.3 and C updated to match the above.

## 201026

- Decisions (spec 003, recipe extraction adapter): unit typo rule (one edit, units of 5+ characters); vague-phrase list in FR-006c, with number words such as "un par" converted rather than vague; reason "Only one recipe at a time" with the member message "Upload only one recipe at a time" from S-016; input refusal raised, not returned; image wait recorded for S-040 only.
- Finished changes: spec.md, PRD J2 and Appendix B.1, data-model, contract, tasks and plan updated to match. Details in `dev/memory/201026.md`.

## 211026

- Decisions (spec 003, categories): controlled vocabulary replaces free labels and kitchen-first ordering (closes CHK012); main ingredient may be zero; cuisine gate of at least 2 title dishes and 3 ingredient keywords (combine: all); avocado under fruit; cuisine falls back to international; chip labels in the pasted text's language.
- Finished changes: spec.md, PRD J2 and Appendix B.1, AGENTS.md, data model, contract, tasks, plan, quickstart and dev/docs/category-prompt.md updated to match. Details in `dev/memory/211026.md`. Open: combine all or any; category management for members.
- Re-specified cuisine matching (21/10/26): the app scores every cuisine (title coverage at least 0.70, or more than 4 ingredients in the steps), ranked by total matches; the model returns only the main ingredient. PRD, spec and supporting docs updated. Checklists: 35 items in extraction.md and "No implementation details" in requirements.md marked reviewed. Details in `dev/memory/211026.md`.
- Cuisine matching refined (21/10/26): stopwords and phrase exclusions added; recipes with fewer than 5 ingredient lines are matched on the title only. Details in `dev/memory/211026.md`.
- Cuisine tie-breaks confirmed (21/10/26): higher title coverage, then higher body coverage (distinct ingredient ids and techniques found in the steps), then all tied cuisines kept, up to two. "Fewer than 5 ingredients" means fewer than 5 ingredient lines. Details in `dev/memory/211026.md`.

## 221026

- Decisions (notebooks): recipes live in notebooks, one shared per kitchen and one private per member, replacing `recipe_share`. A notebook is its own entity (kitchen or member owner); ingredients and recipes point at `notebook_id`; recipes move only by copying and the copies drift apart; a kitchen capture saves to the kitchen (member as author) and to the member's notebook. `users.default_notebook_id` (ON DELETE SET NULL) and the default notebook "{alias}'s Notebook" are created on the first GET /notebooks/members/{user_id}. No category tables: recipes store category ids; any member may edit or delete a kitchen recipe.
- Decisions (S-016 capture): Discard only (storing vague amounts moves to S-019); the draft review is its own page; leaving an edited draft asks first; archived kitchens refuse capture; chip labels use the member's language; the tabs are "Notebook"; paste limit from env RECIPE_TEXT_MAX_CHARS (default 5,000); reordering lines and steps is required.
- Process: spec folders are numbered by backlog story (002→016, 003→015, 004→055); S-055 is built before S-016.
- Finished changes: PRD, AGENTS.md, backlog and specs 015/016 updated for notebooks; S-016 plan and 63 tasks; S-055 spec and tasks, then S-055 implemented (all 19 tasks, api suite green in Compose, migration round-trip checked). Open for review: signup's "My kitchen" gets its notebook on first read; the default-notebook port locks before create instead of set_if_null. Details in `dev/memory/221026.md`.

## 231026

- **Notebook model decisions (S-055):** the model moved from kitchen-owned notebooks (22/10) to people-owned ones with members, then to the snapshot model. Personal notebooks belong to people (one owner, members by invite) and never appear in a kitchen. Kitchen notebooks belong to a kitchen, and access comes only from current kitchen membership. A personal notebook reaches a kitchen only as a snapshot: an independent copy with an origin label (`source_notebook_id`, cleared when the original is deleted). Deleting a kitchen deletes its notebooks. Any kitchen member manages kitchen notebooks.
- **Capture decisions:** the first capture notebook is created when a capture is saved, never on discard, and the capture step is shared by S-016 and S-019. A created notebook is committed on its own so it survives a failed save. Archived kitchens refuse captures, even when they already have notebooks.
- **Catalog and naming decisions:** the personal catalog covers personal notebooks only, and a new notebook starts from its creator's catalog. Names are fixed at creation: "{alias}'s Notebook" for the default, "{alias}'s ({kitchen}) Notebook" for kitchen notebooks.
- **Preferences and process:** the speckit flow was used for spec 055: specify, clarify, plan, tasks, checklist. The requirements-quality checklist was regenerated for the snapshot model (36 items). T039 was marked done.
- **Project changes:** PRD, AGENTS.md and the backlog were updated. S-055 was re-scoped, S-056 (invites), S-057 (ownership passing) and S-058 (notebook management) were added, and notes were extended on S-034, S-016, S-017 and S-019. Branch renamed to `s55-notebooks`.

## 271026

- **Scope decision:** main ingredients and cuisines are out of the MVP and moved to *Later* (S-061). The PRD keeps their design in Appendix E; the draft response and `GET /recipe-vocabulary` lose their category keys; code is commented out under `MVP-OUT:`. Ingredient catalog matching (S-018) is untouched. Plan with validation checks: `dev/docs/mvp-descope-categories.md`. Details in `dev/memory/271026.md`.

## 291026

- **Finished changes:** S-022 was implemented uncommitted: shared kitchen cart with a server-held draft, single-editor locks for the cart and recipe edit (session-scoped, 5 minutes idle, cascade on lost access) and migration 0007. Its UI clarification added the cart-icon button, toasts above the tab bar and an editing bar on the Cart page only. Browser walks T052 and T064 were still to do.
- **Project fact:** the Compose test database `melos_test` must exist before the api test overlay runs.

## 301026

- **Finished changes:** S-064 (kitchen side panel) was planned, clarified and built uncommitted on branch `064-kitchen-side-panel`: `users.default_kitchen_id` resolved on read outside `/auth`, a side-panel route and a phone drawer that closes after a choice. Its browser walk was not done, as no browser was available.
- **Decisions:** the owner approved a principle 9 exception on 2026-10-30 to build S-064 before the open Must stories. On phones, kitchen actions other than cart and invite go in a more menu. S-065 (cauldron loader) was specified and planned: a CSS-only single SVG on one 2.4 s loop replaces every loading state, with no delay. Building it before the Must stories still needed owner approval.
- **Incident:** a test baseline run under a second Compose project shared the `MELOS_DATA` pgdata with the dev db, and `melos-db-1` then failed with an invalid checkpoint record. A second Compose project must never run with the main `.env`.

## 011126

- **Finished changes:** S-035 (notebook snapshots) was built and walked; S-057 (notebook invites) was built, walked with 128 checks and committed on its branch; S-058 (ownership passing) was merged through PR #30. UI work: the kitchen menu stacking fix, a 1rem phone gutter, the cauldron as browser icon and landing mark (pot 85 percent, blue 75), a trash Clear cart in the chrome with a short editing bar, empty notebooks and kitchens with a centered plus and no search bar, and Past lists as a history icon with standard chrome.
- **Decisions:** S-055 was redirected to custom units plus an admin dashboard: one unit row per name with `user_references`, a database-computed count and `is_default`; `users.is_admin` was approved by the owner; stored units never reach the model; dashboard activity is existing data plus cart created, edited and closed. Notebook sharing should match the kitchen: a share icon opening a dialog.
- **Project facts and lessons:** Playwright runs on this WSL host with libraries copied from its image. Agents share one git index, so commit from a private index when other work is staged (abbf2c8 took another agent's files by accident).
