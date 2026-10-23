# Data Model: Personal and Kitchen Notebooks

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md) | **Date**: 2026-10-23 (snapshot model)

Source of truth: PRD §1.6. Alembic revision `0003_personal_kitchen_notebooks` (replaces the unmerged `0003_notebooks_ingredients`, research R12). No backfill.

## Tables

### `notebook` (new)

| Column | Type | Rules |
|---|---|---|
| `id` | uuid, pk | `gen_random_uuid()` default |
| `name` | text, not null | Check `ck_notebook_name_not_blank`: `btrim(name) <> ''`. Fixed at creation in this feature |
| `kitchen_id` | uuid, null | FK `kitchens.id` `ON DELETE CASCADE`; index `ix_notebook_kitchen_id`. Set: a kitchen notebook. Null: a personal notebook. Not unique: a kitchen can have several |
| `source_notebook_id` | uuid, null | FK `notebook.id` `ON DELETE SET NULL`; index `ix_notebook_source_notebook_id`. The origin label of a snapshot. Never set by this feature (S-034) |
| `created_at` | timestamptz | `now()` default. Lists are ordered by `created_at, id` |

- Check `ck_notebook_source_is_kitchen`: `source_notebook_id IS NULL OR kitchen_id IS NOT NULL`.
- Check `ck_notebook_source_not_self`: `source_notebook_id <> id` (a null passes).

### `notebook_membership` (new, personal notebooks only)

| Column | Type | Rules |
|---|---|---|
| `notebook_id` | uuid | FK `notebook.id` `ON DELETE CASCADE` |
| `user_id` | uuid | FK `users.id` `ON DELETE CASCADE`; index `ix_notebook_membership_user_id` |
| `role` | text | Check `ck_notebook_membership_role`: `role IN ('owner', 'member')` |
| `created_at` | timestamptz | `now()` default. S-057 orders "longest-standing member" by this |

- Primary key `(notebook_id, user_id)`: a person appears once per notebook.
- Partial unique index `uq_notebook_one_owner` on `(notebook_id) WHERE role = 'owner'`: at most one owner.
- Application rules (research R2): every personal notebook is inserted with its owner row in the same transaction (exactly one owner); no row ever points at a kitchen notebook.

### `ingredient` (new, unchanged from the 2026-10-22 design)

| Column | Type | Rules |
|---|---|---|
| `id` | uuid, pk | `gen_random_uuid()` default |
| `notebook_id` | uuid | FK `notebook.id` `ON DELETE CASCADE` |
| `name` | text | A normalized name (trimmed, lower-case, singular) |
| `created_at` | timestamptz | `now()` default |

- Unique `uq_ingredient_notebook_name` on `(notebook_id, name)`: a catalog is a set.

### `users` (changed)

| Column | Type | Rules |
|---|---|---|
| `default_notebook_id` | uuid, null | FK `notebook.id` `ON DELETE SET NULL` (`use_alter`, the two tables reference each other). Application rule: only ever set to a personal notebook the person owns |

No other change to `users`, and no change to signup, sign-in, alias claim or sessions (FR-005). Approved constitution exception, see [plan.md](./plan.md) Complexity Tracking.

### Not created here

`notebook_invite` (S-056). No `notebook_kitchen` table and no kitchen-notebook membership: both belonged to the withdrawn kitchen-link model.

## Cascades (FR-006)

| Deleted | Goes with it | Stays |
|---|---|---|
| Kitchen | its kitchen notebooks, their catalogs; `source_notebook_id` set to null on any notebook that came from one of them | every personal notebook (SC-008) |
| Notebook | its memberships and catalog; `users.default_notebook_id` set to null where it pointed at it; `source_notebook_id` set to null on snapshots made from it | the snapshots themselves, and everything else |
| User | their `notebook_membership` rows | every notebook. Passing ownership is S-057, built before or with any route that deletes a user (S-053) |

Leaving a kitchen, or being removed from one, changes no notebook row: access is computed from `kitchen_memberships` on each request (research R10).

## Domain (`api/domain/notebook.py`, pure)

```text
NotebookKind   = "personal" | "kitchen"
NotebookRole   = "owner" | "member"
NotebookAccess = "owner" | "member" | "kitchen_member"

Notebook(id, name: str, kitchen_id: UUID | None = None, source_notebook_id: UUID | None = None)
  invariants (else InvalidNotebookError):
    name.strip() != ""
    source_notebook_id is None or kitchen_id is not None
    source_notebook_id != id
  kind: "kitchen" when kitchen_id is set, else "personal"

default_notebook_name(alias)                    → "{alias}'s Notebook"
kitchen_notebook_name(alias, kitchen_name)      → "{alias}'s ({kitchen_name}) Notebook"

notebook_access(kind, role, in_kitchen)         → NotebookAccess | None
    personal → role (owner | member) or None; in_kitchen is ignored
    kitchen  → "kitchen_member" when in_kitchen, else None; role is ignored

choose_capture_notebook(candidates, picked)     → UUID | None   (None = create one)
    none                             → None (any pick ignored)
    exactly one                      → that one (any pick ignored)
    several, pick in candidates      → picked
    several, pick not in them        → NotebookNotFoundError
    several, no pick                 → NotebookChoiceRequiredError(candidates)
```

The name invariant replaces the 2026-10-22 rule "exactly one of `kitchen_id`, `user_id`", removed with `notebook.user_id`.

## Read model (application)

`NotebookView` is the shape of every answer (wire form in [contracts/notebooks-api.md](./contracts/notebooks-api.md)).

| Field | Personal notebook | Kitchen notebook |
|---|---|---|
| `id` | `notebook.id` | `notebook.id` |
| `name` | `notebook.name` | `notebook.name` |
| `kind` | `personal` | `kitchen` |
| `access` | the caller's role: `owner` or `member` | `kitchen_member` |
| `owner_alias` | alias of the owner membership's user; null if none remains | null |
| `kitchen_id` | null | `notebook.kitchen_id` |
| `kitchen_is_archived` | null | the kitchen's archived state, read with the notebook |
| `is_default` | `users.default_notebook_id = notebook.id` for the caller | false |

The repository returns facts (the notebook, the caller's role, whether the caller belongs to its kitchen, the owner's alias, whether it is the default, the kitchen's archived state). The application applies `notebook_access` and turns `None` into `NotebookNotFoundError` (research R10).

`CaptureNotebook(notebook_id, created: bool)` is the result of the capture step (research R6, R7).

## Lifecycle in this feature

```text
first GET /notebooks/default      ──►  notebook(name="{alias}'s Notebook") + catalog seed
                                       + membership(owner) + users.default_notebook_id
create a kitchen (kitchen service) ──►  kitchen + kitchen membership
                                       + notebook(name="{alias}'s ({kitchen}) Notebook", kitchen_id)
                                       + catalog seed           (one transaction)
capture step, kitchen, none       ──►  lock kitchen row, re-check
                                       + notebook(name="{alias}'s ({kitchen}) Notebook", kitchen_id)
                                       + catalog seed + commit
capture step, personal, none      ──►  the default notebook as above + commit
personal notebook deleted         ──►  users.default_notebook_id = null → recreated on next GET
kitchen deleted                   ──►  its notebooks and catalogs deleted; personal notebooks stay
```

Not in this feature: notebook invites and members (S-056), snapshots and setting `source_notebook_id` (S-034), ownership passing (S-057), creating, renaming and deleting notebooks by hand (S-058).
