# Data Model: Notebooks That Belong to People and Are Linked to Kitchens

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md) | **Date**: 2026-10-23

Source of truth: PRD §1.6. Alembic revision `0003_notebooks_people` (replaces the unmerged `0003_notebooks_ingredients`, research R10). No backfill.

## Tables

### `notebook` (new)

| Column | Type | Rules |
|---|---|---|
| `id` | uuid, pk | `gen_random_uuid()` default |
| `name` | text, null | Set on every notebook except a kitchen notebook. Fixed at creation in this feature |
| `kitchen_id` | uuid, null, unique | FK `kitchens.id` `ON DELETE CASCADE`. Set only on a kitchen notebook (created by S-057) |
| `created_at` | timestamptz | `now()` default |

- Check `ck_notebook_name_or_kitchen`: `(kitchen_id IS NULL) = (name IS NOT NULL)`.
- A notebook with `kitchen_id` set has no owner and is never anyone's default or capture notebook (FR-002, spec Assumptions).

### `notebook_membership` (new)

| Column | Type | Rules |
|---|---|---|
| `notebook_id` | uuid | FK `notebook.id` `ON DELETE CASCADE` |
| `user_id` | uuid | FK `users.id` `ON DELETE CASCADE`; index `ix_notebook_membership_user_id` |
| `role` | text | Check `role IN ('owner', 'member')` |
| `created_at` | timestamptz | `now()` default. "Longest-standing member" in S-057 orders by this |

- Primary key `(notebook_id, user_id)`: a person appears once per notebook.
- Partial unique index `uq_notebook_one_owner` on `(notebook_id) WHERE role = 'owner'`: at most one owner.
- "Exactly one owner" for every notebook other than a kitchen notebook is kept by the application: the notebook and its owner row are inserted in the same transaction (R1).

### `notebook_kitchen` (new)

| Column | Type | Rules |
|---|---|---|
| `notebook_id` | uuid | FK `notebook.id` `ON DELETE CASCADE` |
| `kitchen_id` | uuid | FK `kitchens.id` `ON DELETE CASCADE`; index `ix_notebook_kitchen_kitchen_id` |
| `linked_by` | uuid, null | FK `users.id` `ON DELETE SET NULL`. The person who made the link |
| `created_at` | timestamptz | `now()` default |

- Primary key `(notebook_id, kitchen_id)`: a notebook is linked to a kitchen at most once. Inserts use `ON CONFLICT DO NOTHING`.
- A kitchen notebook is never linked (application rule; it already belongs to its kitchen).

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
| `default_notebook_id` | uuid, null | FK `notebook.id` `ON DELETE SET NULL` (`use_alter`, the two tables reference each other) |

No other change to `users`, and no change to signup, sign-in, alias claim or sessions (FR-005). Approved constitution exception, see [plan.md](./plan.md) Complexity Tracking.

## Cascades (FR-006)

| Deleted | Goes with it | Stays |
|---|---|---|
| Kitchen | its `notebook_kitchen` rows, its kitchen notebook (and that notebook's memberships and catalog) | every notebook that was linked to it, with its catalog (SC-007) |
| Notebook | its memberships, links and catalog; `users.default_notebook_id` set to null where it pointed at it | everything else |
| User | their `notebook_membership` rows; `notebook_kitchen.linked_by` set to null (shown as "unknown") | the notebooks and the links they made (ownership passing, ending links and kept copies are S-057, built before any route that deletes a user or a kitchen membership) |

## Domain (`api/domain/notebook.py`, pure)

```text
NotebookKind   = "personal" | "kitchen"
NotebookRole   = "owner" | "member"
NotebookAccess = "owner" | "member" | "reader"

Notebook(id, name: str | None, kitchen_id: UUID | None)
  invariant: kitchen_id is None  ⇔  name is not None   (else InvalidNotebookError)
  kind: "kitchen" when kitchen_id is set, else "personal"

default_notebook_name(alias)                      → "{alias}'s Notebook"
kitchen_capture_notebook_name(alias, kitchen)     → "{alias}'s Notebook ({kitchen})"
notebook_access(role, via_kitchen, is_kitchen_nb) → strongest of owner > member > reader, or None
    is_kitchen_nb and via_kitchen  → "member"   (its members are the kitchen's members, R2)
choose_capture_notebook(candidate_ids, picked)    → UUID | None (None = create)
    picked not in candidates       → NotebookNotFoundError
    several and no pick            → NotebookChoiceRequiredError(candidate_ids)
```

The name and kitchen invariant replaces the 2026-10-22 rule "exactly one of `kitchen_id`, `user_id`", which is removed with `notebook.user_id`.

## Read model (application)

`NotebookView`: the shape of every answer (contract in [contracts/notebooks-api.md](./contracts/notebooks-api.md)).

| Field | Source |
|---|---|
| `id` | `notebook.id` |
| `name` | `notebook.name`, or the kitchen's current name for a kitchen notebook |
| `kind` | `Notebook.kind` |
| `access` | `notebook_access(…)` for the caller; never `None` in an answer |
| `owner_alias` | alias of the `owner` membership's user; `null` for a kitchen notebook or when no owner remains |
| `is_default` | `users.default_notebook_id = notebook.id` for the caller |

The repository returns raw facts (the caller's role, whether the notebook can be reached through a kitchen, the owner's alias, whether it is the default). The application applies `notebook_access` and turns `None` into `NotebookNotFoundError` (research R8).

## Lifecycle in this feature

```text
first GET /notebooks/default  ──►  notebook(name="{alias}'s Notebook")
                                   + membership(owner) + catalog seed
                                   + link to the signup kitchen (if still a member)
                                   + users.default_notebook_id
capture step, no candidate     ──►  signup kitchen and no default → the default notebook as above
                                   otherwise notebook(name="{alias}'s Notebook ({kitchen})")
                                   + membership(owner) + catalog seed + link(linked_by = member)
default notebook deleted       ──►  users.default_notebook_id = null → recreated on next GET
```

Not in this feature: adding or removing members (S-056), linking or unlinking by hand (S-034), kitchen notebooks and kept copies (S-057), renaming and deleting notebooks from the UI.
