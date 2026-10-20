## 171026

- Decisions (AI/search): embeddings are always TOON-based behind an `EmbedTextStrategy` (Strategy pattern, A/B-testable, tracks strategy and input tokens); pgvector searches are always pre-filtered by `kitchen_id`, plus optional creator, date range, ingredients, categories and exclusions.
- Decisions (MCP): separate `mcp` container (port 9000 in dev, nginx in prod) with per-user Bearer API keys scoped to the user's own kitchens; exposes kitchen/member ops, `capture_recipe` (capture + save), cart edits, shopping-list read/edit and chat `ask`. MCP is Must scope; the API-key UI on Account is Should.
- Decisions (shopping lists and chat): finalized shopping lists are stored as snapshots (`shopping_list` + `shopping_list_item`, `closing_date`); the kitchen assistant queries them via a `shopping_list_history` tool and returns TOON that the UI renders as clickable cards.
- Finished changes: PRD appendices A, B.2, B.3 and C updated to match the above.
