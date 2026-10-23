# Feature Specification: Notebooks for Kitchens and Members

**Feature Branch**: TBD
**Created**: 2026-10-22
**Status**: Draft
**Input**: Prerequisite for `specs/002-capture-recipe-text`. Backlog story: S-055. Build order: this spec first, then spec 002 (S-016). Spec numbers follow creation order, not build order.

## Summary

Recipes are kept in notebooks. Each kitchen has one shared notebook. Each member has a notebook of their own. This feature creates the notebooks, stores the ingredient catalog that belongs to each notebook, and provides the two read routes that capture needs. It does not capture, save or show recipes.

## Clarifications

### Session 2026-10-22

- The database must allow many notebooks per member, for later use. The schema has no unique constraint on the member side. Each kitchen still has exactly one notebook (unique on `kitchen_id`).
- In this release the application creates one notebook per member, on first use. This is the current product rule; PRD §1.6 and AGENTS.md say "one for now" and were updated on 2026-10-22.
- The auth routes (signup, alias claim, sign-in) are not changed (AGENTS.md).
- The user has a nullable `default_notebook_id` (foreign key to `notebook`). `GET /notebooks/members/{user_id}` returns the member's default notebook. When the value is null, the call creates a notebook and stores its id there. The create-and-set step locks the user row and re-checks, so two simultaneous first calls make one notebook. A member's notebooks are the `notebook` rows with their `user_id`; there is no join table. Adding the column to the user model is approved by the owner's instruction of 2026-10-22 (AGENTS.md: the auth layer is otherwise unchanged). This also answers spec 002's question of how the member's page learns its notebook id: it calls the default route.
- Naming: a notebook has a `name`. A member's default notebook is named "{alias}'s Notebook", using the alias at creation time; the name does not follow later alias changes. A kitchen's notebook has no stored name; it shows the kitchen's name.
- Deleting the default notebook sets `default_notebook_id` back to null (foreign key `ON DELETE SET NULL`). The next default call creates a new default notebook silently.
- The creation is invisible to the UI: the default route answers with the same shape and status whether the notebook was just created or already existed. There is no "created" flag and no 201.

## User Scenarios & Testing

### User Story 1 - Every kitchen has its notebook (Priority: P1)

When a member creates a kitchen, the kitchen gets exactly one notebook in the same step. Members of the kitchen can read the notebook; other people cannot.

**Independent Test**: Create a kitchen. Read its notebook as an owner and as a member, and check that a non-member gets the not-found answer.

### User Story 2 - Every member has a notebook on first use (Priority: P1)

A signed-in member with an alias gets their own notebook the first time they ask for their default notebook. Asking again returns the same notebook.

**Independent Test**: As a member with no default notebook, call the default-notebook route twice and check that one notebook exists and the user's `default_notebook_id` is set to it.

### User Story 3 - Existing data has notebooks (Priority: P1)

The migration gives every existing kitchen a notebook and every existing user with an alias a notebook. Downgrading removes the tables cleanly.

**Independent Test**: Upgrade a database with existing kitchens and users, and check the notebook counts. Downgrade and upgrade again.

## Requirements

### Functional Requirements

- **FR-001**: Creating a kitchen MUST create its notebook in the same transaction as the kitchen and its owner membership.
- **FR-002**: The user MUST have a nullable `default_notebook_id`. `GET /notebooks/members/{user_id}` MUST return the member's default notebook; when `default_notebook_id` is null it MUST create a notebook named "{alias}'s Notebook", store its id as the default, and return it. Repeating the call, including simultaneous first calls, MUST NOT create a second notebook. The response MUST be the same, in shape and status, whether the notebook was just created or already existed.
- **FR-003**: The `notebook` table MUST have exactly one owner per row (a kitchen or a member), unique on `kitchen_id`, and MUST NOT have a unique constraint on `user_id`. The `notebook` table MUST have `name` (set for member notebooks, null for kitchen notebooks). The user table MUST have `default_notebook_id`, a nullable foreign key to `notebook` with `ON DELETE SET NULL`. A member's notebooks are the `notebook` rows with their `user_id`; there is no join table.
- **FR-004**: `GET /notebooks/kitchens/{kitchen_id}` MUST return `{ id, kind: "kitchen", kitchen_id, name, is_archived }` to any member of the kitchen. A missing kitchen and a non-member MUST get the same 404 `kitchen_not_found`.
- **FR-005**: `GET /notebooks/members/{user_id}/{notebook_id}` MUST return `{ id, kind: "member", user_id }` only when `user_id` is the caller and the notebook belongs to that member. Any other caller, and a missing notebook, MUST get the same 404 `notebook_not_found`. `GET /notebooks/members/{user_id}` (FR-002) MUST return the same shape and apply the same access rule.
- **FR-006**: The `ingredient` table MUST have `(id, notebook_id, name)` with unique `(notebook_id, name)`. This feature exposes a read-only catalog reader; nothing writes ingredients yet.
- **FR-007**: The migration MUST create both tables and backfill one kitchen notebook per existing kitchen and one member notebook (named "{alias}'s Notebook") per existing user that has an alias, MUST add `default_notebook_id` to the user table and set each existing user's value to that notebook, and MUST have a working downgrade.
- **FR-010**: When the default notebook no longer exists, `default_notebook_id` MUST be null and the next default call MUST create a new default notebook, with no error shown to the member.
- **FR-008**: No code in this feature MUST write recipe, step, category, source or share data.
- **FR-009**: Signup, sign-in, alias claim and session code MUST NOT change. The only change to the user is the new `default_notebook_id` column.

### Key Entities

- **Notebook**: id, `kitchen_id` or `user_id` (exactly one set), `name` (member notebooks only), created_at.
- **Ingredient**: id, `notebook_id`, name. Read-only here.
- **User (changed)**: gains `default_notebook_id`, null until the member first asks for their default notebook.

## Success Criteria

- **SC-001**: Creating a kitchen leaves exactly one notebook for it, in 100% of automated runs.
- **SC-002**: Repeated and simultaneous first calls leave exactly one notebook for the member, and `default_notebook_id` equals its id, in 100% of automated runs.
- **SC-003**: The migration backfill gives each existing kitchen, and each existing user with an alias, one notebook, and downgrade and upgrade both succeed.
- **SC-005**: After the default notebook is deleted, the next default call creates a new one named "{alias}'s Notebook" and sets it as the default, with the same response shape, in 100% of automated runs.
- **SC-004**: A non-member and a non-owner each get the documented 404 for the two read routes, in 100% of automated runs.

## Assumptions

- The PRD (§1.6, Appendix A) and AGENTS.md already describe the notebook model (decided 2026-10-22).
- Unit and integration tests run in Compose against Postgres, as in spec 002.
- This feature adds no env var and no library.
