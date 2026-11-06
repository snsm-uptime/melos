# Implementation Plan: Share a recipe with a person from the recipe page

**Branch**: `071-share-recipe-to-user` | **Date**: 2026-11-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/071-share-recipe-to-user/spec.md`

## Summary

A recipe reader presses a share icon in the recipe page header. A popup opens with a
`SearchableSelect` of aliases. Only people who share a kitchen or a notebook with the caller are
listed, co-members first. Pressing the send icon copies the recipe into the chosen person's default
notebook, authored by that person, and the popup swaps the list for a success message.

Technical approach: one read endpoint returns the caller's co-members in display order; one write
endpoint copies a readable recipe into the recipient's default notebook. The copy reuses
`RecipeRepository.copy_one` and `IngredientCatalog.add_names` from the existing kitchen copy path
(spec 069). It also adds the name normalization that S-048 needs, so this feature builds the shared
copy step that S-048 is waiting on, scoped to a single recipe and a personal target notebook. The
UI is a new popup component built on the existing `SearchableSelect` `action` prop and the same
send icon as the invite-by-email form.

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript / React 19 (ui, Next.js 16)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (api); Next.js 16, Tailwind 4, vitest (ui).
No new libraries.

**Storage**: PostgreSQL 16 + pgvector. No schema change expected: the copy uses existing `recipes`,
`notebooks`, `notebook_members`, `kitchen_memberships` rows. Confirm in Phase 0 (research R-2).

**Testing**: pytest (domain pure; application against fake ports; integration against Postgres via
the Compose test overlay); vitest for the popup component; browser check per quickstart.

**Target Platform**: Linux containers (Compose); web browser (desktop and mobile widths).

**Project Type**: web application (ui BFF proxying to api).

**Performance Goals**: Success message within 2 s of pressing send under normal load (SC-004).
Candidate list loads with the popup; no pagination (co-member lists are small).

**Constraints**: The ui talks only to `ui`, which proxies `/api/*` to `api`. Kitchen- and
notebook-scoped access checks return 404 for non-members. Strings in English and Spanish (FR-012).
Recipient email is never sent (spec assumption). The auth layer is not touched.

**Scale/Scope**: A user has a handful of kitchens and notebooks, so the co-member list is tens of
people at most. Scope is one recipe at a time, to one recipient, into one default notebook.

## Constitution Check

*Gate evaluation before Phase 0 and re-check after Phase 1.*

| Principle | Check | Result |
|-----------|-------|--------|
| 1. Simplicity and Reuse | Reuses `copy_one`, `add_names`, `SearchableSelect`, the send icon; no new service, no queue, no auth change | PASS |
| 2. Tech stack stability | Python 3.12 / uv, FastAPI, SQLAlchemy, Next.js 16; no new dependency; no model names involved | PASS |
| 3. Hexagonal architecture | Co-member query and copy go through `application/` use cases and ports in `application/ports.py`; SQLAlchemy stays in `adapters/persistence/`; `domain/` gains only error types | PASS, if the query is a port method (see Phase 1) |
| 3. Kitchen-scoped queries check membership | Read and send check the caller can read the recipe; the recipient must be a co-member at send time; non-members get 404 | PASS (designed in) |
| 4. Security and privacy | Aliases of strangers are not exposed: the list is co-members only and the send endpoint rejects any other user id with 404. No email; no real data in tests | PASS |
| 5. No AI shortcuts | No AI involved; the copy is made directly (no draft step) | N/A |
| 6. Testing and quality | Domain pytest, application tests on fakes, integration on Postgres, vitest for the popup, browser check | PASS (planned) |
| 9. Post-MVP scope by backlog priority | S-071 is `must` and is the owner's next story | PASS |

**Result**: No violations. Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/071-share-recipe-to-user/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── share-api.md     # Phase 1
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
api/
├── domain/
│   └── errors.py                       # + ShareRecipientNotFoundError, ShareRecipientNoDefaultNotebookError
├── application/
│   ├── recipe_share.py                 # NEW: ListShareCandidatesService, ShareRecipeService
│   └── ports.py                        # + CoMemberDirectory port (list co-members), + default-notebook lookup if missing
├── adapters/persistence/
│   ├── co_members.py                   # NEW: SQL for co-members (kitchen + notebook memberships)
│   └── recipes.py / notebooks.py       # reuse copy_one, default notebook lookup
├── api/
│   ├── routes/recipes.py               # + GET /recipes/share-candidates, + POST /recipes/{id}/share
│   └── schemas/recipes.py              # + ShareCandidate, ShareRequest, ShareResponse
└── tests/
    ├── application/test_recipe_share.py        # fakes
    └── integration/test_recipe_share_routes.py # Postgres, membership and 404 cases

ui/
├── app/api/ (or existing BFF proxy)        # proxy the two new routes unchanged
├── components/ShareRecipeDialog/
│   ├── ShareRecipeDialog.tsx           # NEW: popup; SearchableSelect + send action; success state
│   ├── ShareRecipeDialog.test.tsx      # vitest
│   └── index.ts
├── components/RecipeHeader/ (existing) # + share IconButton (FR-001)
└── lib/i18n/ (existing messages)       # EN + ES strings (FR-012)
```

**Structure Decision**: Web application, the existing api hexagonal layout and ui component
folders. The feature lives beside the recipe copy code (spec 069) in the api and beside the recipe
page header in the ui. The share popup is its own component folder, following
`ui/COMPONENT_PATTERNS.md`; icons come from `ui/app/icons/` only.

## Phase 0: Research

See [research.md](./research.md). Open unknowns, all resolved there:

- R-1 Ordering data: is there a timestamp on memberships for "most recent shared activity"?
- R-2 Schema: does the existing data support co-member lookup without a migration?
- R-3 Name normalization: which matcher (S-018) to reuse for the S-048 step.
- R-4 Double send: how to make one copy per press.
- R-5 Recipient default notebook: the lookup and the "no default notebook" failure.

## Phase 1: Design

- [data-model.md](./data-model.md): share candidate, share copy, the rules that link them.
- [contracts/share-api.md](./contracts/share-api.md): the two HTTP routes and error codes.
- [quickstart.md](./quickstart.md): how to run and verify the feature end to end.

## Post-design Constitution Check

Re-checked after Phase 1. The co-member query is a port method, the copy goes through an
application service, and the send route enforces co-membership server-side. All gates still PASS.
