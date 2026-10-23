# Quickstart: check that notebooks work

**Feature**: [spec.md](./spec.md) | **Contract**: [contracts/notebooks-api.md](./contracts/notebooks-api.md) | **Data model**: [data-model.md](./data-model.md)

## Prerequisites

- Docker with Compose v2, `.env` filled in (AGENTS.md "Development environment").
- Branch `s55-notebooks` checked out, with the rework from [plan.md](./plan.md) in place.
- **A dev database that ran the old `0003_notebooks_ingredients`** must go back to `0002` before the new code runs (research R10). Either run `alembic downgrade 0002_pgvector_kitchen_lang` on a checkout of commit `7031e7a` (the last one with the old revision), or recreate the dev database. Production is at `0002` and needs nothing.

## 1. Automated checks

```bash
# api suite in Compose (combine the dev overlay, or db is recreated with a 1h healthcheck and run hangs)
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.test.yml run --rm --build api

# lint
cd api && uv run ruff check .

# ui BFF routes
cd ui && npm test -- notebooks.bff && npm run lint && npm run typecheck
```

Expected: all green. The notebook tests cover SC-001 to SC-005, SC-007 and SC-008 (SC-006 is §2):

- `api/tests/test_notebook_domain.py`: names, access rule, capture choice.
- `test_notebooks_application.py`: services against fake ports.
- `test_notebook_integration.py`: routes, the capture step, cascades and concurrency, against Postgres.

## 2. Migration (FR-019, SC-006)

On a scratch database at `0002` with a few invented users and kitchens:

```bash
docker compose exec api uv run alembic upgrade head
# expect: notebook, notebook_membership, notebook_kitchen, ingredient exist and are empty;
#         users.default_notebook_id is null for everyone; users and kitchens unchanged
docker compose exec api uv run alembic downgrade 0002_pgvector_kitchen_lang
# expect: the four tables and users.default_notebook_id are gone; other data unchanged
docker compose exec api uv run alembic upgrade head
# expect: the same state as the first upgrade
```

## 3. Routes by hand (running stack)

Start the stack with `./scripts/compose-up.sh -d`. Sign up two invented users in two browser profiles, Ana and Ben, and claim aliases. Ana invites Ben to a new kitchen "Home". Then, from Ana's devtools console:

```js
const j = async (p) => { const r = await fetch(p); return [r.status, await r.json()]; };
await j("/api/notebooks/default");
// 200 { id, name: "ana's Notebook", kind: "personal", access: "owner", owner_alias: "ana", is_default: true }
// call again: same id
await j("/api/notebooks");
// 200 { notebooks: [ the default notebook ] }
await j("/api/notebooks/kitchens/<My kitchen id>");
// 200 { notebooks: [ the default notebook ] }   (linked to the signup kitchen, FR-020)
await j("/api/notebooks/kitchens/<Home id>");
// 200 { notebooks: [] }                          (no capture yet)
```

Negative cases, from Ben's profile:

| Call | Expected |
|---|---|
| `/api/notebooks/<Ana's default id>` | 404 `notebook_not_found` (Ben has not joined "My kitchen") |
| `/api/notebooks/<random uuid>` | 404 `notebook_not_found`, same body |
| `/api/notebooks/kitchens/<Ana's My kitchen id>` | 404 `kitchen_not_found` |
| any notebook route as a user without an alias | 403 `alias_required`, no notebook row created |

## 4. Capture notebook step (FR-008, SC-002, SC-008)

The step has no route (FR-021), so until S-016's save lands it is checked only by the capture cases in `test_notebook_integration.py`. They check:

- **First call for Ana in "Home"**: creates "ana's Notebook (Home)", Ana owner, linked by Ana.
- **Second call**: returns the same notebook.
- **Ben reads `/api/notebooks/kitchens/<Home id>`**: he sees it with `access: "reader"`.
- **Ben reads it by id**: same answer.

## 5. Default recreated (FR-007, SC-005)

```sql
DELETE FROM notebook WHERE id = (SELECT default_notebook_id FROM users WHERE alias = 'ana');
```

The next `/api/notebooks/default` returns 200 with a new `id`, the same fields, and `users.default_notebook_id` points at it. It is linked to "My kitchen" again, because Ana is still a member.

## 6. Kitchen deleted (FR-006, SC-007)

Delete "Home" as Ana. `/api/notebooks` still lists "ana's Notebook (Home)", and `SELECT count(*) FROM notebook_kitchen WHERE kitchen_id = '<Home id>'` is 0.
