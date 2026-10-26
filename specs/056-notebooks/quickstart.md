# Quickstart: check that notebooks work

**Feature**: [spec.md](./spec.md) | **Contract**: [contracts/notebooks-api.md](./contracts/notebooks-api.md) | **Data model**: [data-model.md](./data-model.md)

## Prerequisites

- Docker with Compose v2, `.env` filled in (AGENTS.md "Development environment").
- Branch `s55-notebooks` checked out, with the rework from [plan.md](./plan.md) in place.
- **A dev database that ran the old `0003_notebooks_ingredients`** must go back to `0002` before the new code runs (research R12). Run `alembic downgrade 0002_pgvector_kitchen_lang` on a checkout that still has the old revision file (any commit up to `3ff1601`), or recreate the dev database. Production is at `0002` and needs nothing.

## 1. Automated checks

```bash
# api suite in Compose (combine the dev overlay, or db is recreated with a 1h healthcheck and run hangs)
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.test.yml run --rm --build api

# lint
cd api && uv run ruff check .

# ui BFF routes
cd ui && npm test -- notebooks.bff && npm run lint && npm run typecheck
```

Expected: all green. The notebook tests cover SC-001 to SC-009 (SC-010 is §2):

- `api/tests/test_notebook_domain.py`: names, the `Notebook` invariants, the access rule, the capture choice.
- `api/tests/test_notebooks_application.py`: services against fake ports, including the commit after a created capture notebook.
- `api/tests/test_notebook_integration.py`: routes, the capture step, cascades and concurrency, against Postgres.
- `api/tests/test_kitchens_integration.py`: a new kitchen has no notebook until its first open; a failed creation leaves neither.

## 2. Migration (FR-023, SC-010)

On a scratch database at `0002` with a few invented users and kitchens:

```bash
docker compose exec api uv run alembic upgrade head
# expect: notebook, notebook_membership, ingredient exist and are empty;
#         users.default_notebook_id is null for everyone; users and kitchens unchanged
docker compose exec api uv run alembic downgrade 0002_pgvector_kitchen_lang
# expect: the three tables and users.default_notebook_id are gone; other data unchanged
docker compose exec api uv run alembic upgrade head
# expect: the same state as the first upgrade
```

## 3. Routes by hand (running stack)

Start the stack with `./scripts/compose-up.sh -d`. Sign up two invented users in two browser profiles, Ana and Ben, and claim the aliases "ana" and "ben". Ana creates the kitchen "Home" from the kitchen page and invites Ben, who accepts. Then, from Ana's devtools console:

```js
const j = async (p) => { const r = await fetch(p); return [r.status, await r.json()]; };
await j("/api/notebooks");
// 200 { notebooks: [] }                         (listing creates nothing)
await j("/api/notebooks/default");
// 200 { id, name: "ana's Notebook", kind: "personal", access: "owner", owner_alias: "ana",
//       kitchen_id: null, is_default: true }    call again: same id
await j("/api/notebooks");
// 200 { notebooks: [ the default notebook ] }
await j("/api/notebooks/kitchens/<Home id>");
// first call creates Home's notebook for Ana:
// 200 { notebooks: [ { name: "ana's (Home) Notebook", kind: "kitchen", access: "kitchen_member",
//       owner_alias: "ana", kitchen_id: "<Home id>", is_default: false } ] }
await j("/api/notebooks/kitchens/<Ana's My kitchen id>");
// 200 { notebooks: [ { name: "ana's (My kitchen) Notebook", ... } ] }   (signup's kitchen gets its notebook on this first call)
```

From Ben's profile:

| Call | Expected |
|---|---|
| `/api/notebooks/kitchens/<Home id>` | 200, the same "ana's (Home) Notebook", `access: "kitchen_member"` |
| `/api/notebooks/<"ana's (Home) Notebook" id>` | 200, same object |
| `/api/notebooks` | 200, no Home notebook in it (FR-014) |
| `/api/notebooks/<Ana's default id>` | 404 `notebook_not_found`, although Ben shares "Home" with Ana |
| `/api/notebooks/<random uuid>` | 404 `notebook_not_found`, same body |
| `/api/notebooks/kitchens/<Ana's My kitchen id>` | 404 `kitchen_not_found` |
| any notebook route as a user without an alias | 403 `alias_required`, no notebook row created |

## 4. Capture notebook step (FR-009 to FR-011, SC-003, SC-009)

The step has no route (FR-013), so until S-020's save lands it is checked only by the capture cases in `test_notebook_integration.py`. They check:

- **First capture in "My kitchen"** (no notebook): creates "ana's (My kitchen) Notebook" with `kitchen_id` set and no membership rows; a second call returns it with `created = false`.
- **Ana and Ben at the same moment** in a kitchen with none: one notebook.
- **"Home" with two notebooks**: no pick is refused with the candidate ids; a pick from another kitchen is refused; a valid pick is returned.
- **Archived kitchen**: refused, nothing created, even with notebooks.
- **Non-member**: the `kitchen_not_found` error, nothing created.
- **Save fails after the step created a notebook**: the session is rolled back, and the notebook is still there.
- **Personal, no notebook**: the default notebook is created and used.

## 5. Default recreated (FR-007, SC-007)

```sql
DELETE FROM notebook WHERE id = (SELECT default_notebook_id FROM users WHERE alias = 'ana');
```

The next `/api/notebooks/default` returns 200 with a new `id` and the same fields, and `users.default_notebook_id` points at it.

## 6. Kitchen deleted (FR-006, SC-008)

Delete "Home" as Ana. `SELECT count(*) FROM notebook WHERE kitchen_id = '<Home id>'` is 0, its ingredient rows are gone, and `/api/notebooks` still lists "ana's Notebook".

## 7. Leaving a kitchen (FR-017, SC-006)

No route removes a member yet, so `test_notebook_integration.py` deletes Ben's `kitchen_memberships` row for "Home". His next read of Home's notebooks, or of one of them by id, gets the 404, and the notebooks are unchanged.
