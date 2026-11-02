# Quickstart: validate notebook management

## Automated checks

- api, canonical: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`
- api lint: `cd api && uv run ruff check .`
- ui: `cd ui && npm test && npm run lint && npm run typecheck`

Do not start a second Compose project with the main `.env`: `-p` does not isolate the data directory. A worktree has no `.env` of its own, so run `worktree-bootstrap.sh` first (see `scripts/worktree/README.md`), which gives it its own project, ports and data directory. The test database must exist: `docker compose exec db createdb -U "$POSTGRES_USER" "${TEST_POSTGRES_DB:-melos_test}"`. Use an isolated stack for the browser walk.

## Setup

Three invented accounts: Ana, Ben and Carl. Ana and Ben share kitchen Home, and Carl is in neither. Ana owns "Soups" with 2 recipes. Ben is a member of it. There is one pending invite on it. Home has a snapshot of "Soups" and a second, archived kitchen.

## Walk

Run at 360px and 1280px, in English and Spanish, and once by keyboard only.

1. **Rename as owner**: Ana renames "Soups" to "Winter soups". The page title, Ana's and Ben's lists, and the snapshot's label show it. The snapshot's own name does not change.
2. **Rename refused**: Ben sees no options button on it. A direct PATCH answers 403. Carl's answers 404.
3. **Name rules**: spaces only shows the message and keeps the text. The box stops at 200 characters. A direct PATCH with 201 answers 422 `invalid_notebook_name`.
4. **Kitchen rename**: Ben renames a Home notebook. Ana sees it.
5. **Add kitchen notebook**: Ben adds "Holidays" to Home. It opens empty, Ana sees it, and a capture there saves.
6. **Delete a personal notebook**: Ana opens Delete on "Winter soups". The dialog states 2 recipes and 1 person. Cancel changes nothing. Confirm lands on Ana's list. Ben gets redirected away, the pending invite shows the invalid-link message, and the snapshot keeps its recipes with no label.
7. **Delete a kitchen notebook**: with one of its recipes in the cart and on the active list, Ben deletes it. The recipe leaves the cart, other cart entries stay, the shopping list line stays, and the side panel count drops.
8. **Delete the default**: the dialog says a new one takes its place, and a new, empty default shows on landing.
9. **Delete the last kitchen notebook**: the next open of the kitchen's notebooks creates a new one.
10. **Archived kitchen**: no options button, no add tile, and direct calls answer 403.
11. **Gone while open**: Ana and Ben both have a kitchen notebook open. Ana deletes it. Ben tries Rename, sees the gone message, and closing it lands on the kitchen's notebooks.
12. **Draft open**: open a capture draft, delete its notebook in another tab, then save. The message shows and the draft stays.

## Expected test coverage

SC-003 and SC-004 are covered by integration tests over every role. SC-006 and SC-007 need real concurrent requests against Postgres: two deletes, rename against delete, snapshot against delete, invite against delete, capture against delete, and archive against rename, delete and add.
