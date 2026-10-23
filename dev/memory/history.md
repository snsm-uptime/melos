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
