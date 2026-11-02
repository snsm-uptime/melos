# Implementation Plan: Custom Units and Admin Dashboard

**Branch**: `055-custom-units` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/055-custom-units/spec.md`

## Summary

A measure word the app doesn't know now opens a draft with a question, instead of refusing the capture. If the person says yes, the word joins their list when the recipe saves. A new `unit` table holds one row per name, with a native list of people and a count computed by the database. Recipe lines keep plain text, so the table check on the ten units goes, and any stored unit works for every reader. The shopping list gains a `custom` kind that adds up and rounds up.

The app compares words in code, so stored units never reach the model. The in-flight key for extraction must now cover the caller's lists, or two people pasting the same text would share one person's units.

An `is_admin` column, shown through the side panel and not the auth routes, opens a read-only dashboard of four sections. A new `cart_activity` table records cart actions for it. See [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript with Next.js 16 and React 19 (ui).

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, google-genai, Tailwind 4. No new libraries.

**Storage**: PostgreSQL 16. One migration, `0013_custom_units`: two new tables, one new `users` column, two changed checks. See [data-model.md](data-model.md).

**Testing**: pytest (domain, application with fake ports, integration in the Compose overlay), vitest, a browser walk, and one manual AI fixture.

**Target Platform**: The existing Compose stack. The `mcp` service is not touched, as it has no capture tool yet.

**Project Type**: Web application (`api` + `ui`).

**Performance Goals**: A person's list adds one small query to capture, save, edit and vocabulary reads. Reading a recipe adds none (FR-011). Dashboard sections are rare reads, with no target.

**Constraints**: The auth layer changes by one column only. No unit conversion. A cart or recipe flow must not depend on who holds a unit. Removal from a unit is a rule with no route until S-054.

**Scale/Scope**: Household scale: tens of unit names and a few accounts. The dashboard has no paging.

No item needs clarification.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| §1 Simplicity and Reuse | Pass, with approval | `users.is_admin` touches the auth table. The owner approved it on 2026-11-01 (spec Clarifications). Routes, sessions and passwords don't change (R16). Still four services. |
| §2 Tech Stack | Pass | No new library. Model names are untouched. |
| §3 Hexagonal | Pass | Normalizing, lookup and the cart action are pure domain rules. Admin access is checked in `application/`. New ports: `UnitRepository`, `CartActivityLog`, `AdminReportRepository`. |
| §4 Security and Privacy | Pass | Stored units are never sent to the model (R4). Pasted text keeps its delimiters. The in-flight key stops one person's units reaching another (R5). |
| §5 No AI Shortcuts | Pass | Nothing saves without the person's confirmation. A word joins only at Save. No unit is converted (R13). |
| §6 Testing | Pass | All layers are covered. See [quickstart.md](quickstart.md). |
| §7 Deployment | Pass | One migration, and one SQL line for the owner, documented in the README. |
| §8 Git Discipline | Pass | The schema change goes through Alembic. |
| §9 Scope and Schedule | **Exception approved by the owner, 2026-11-02** | S-055 is priority `later`. Must stories are still open, and the v1 deadline is 2026-11-02. See Approvals under Complexity Tracking. |
| AGENTS.md "Every recipe query checks..." | Exception approved by the owner, 2026-11-02 | The dashboard reads titles across notebooks. See Approvals under Complexity Tracking. |

### Post-design re-check

The design adds no violation. The two rows below still stand. The dashboard exception is limited further by design: the key test in `contracts/admin-api.md` keeps ingredients, steps and conversations out.

## Project Structure

### Documentation (this feature)

```text
specs/055-custom-units/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── units-api.md
│   └── admin-api.md
└── tasks.md             # /speckit-tasks, not made here
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── recipe_draft.py          # custom_unit_name, lookup_unit(extra), UnknownUnit, draft rules
│   ├── cart.py                  # custom kind, cart_save_action
│   └── errors.py                # admin not found
├── application/
│   ├── units.py                 # new: available units, keep rule, unit check, removal service
│   ├── admin.py                 # new: dashboard reads and the access check
│   ├── ports.py                 # UnitRepository, CartActivityLog, AdminReportRepository
│   ├── recipe_extraction.py     # in-flight key, units passed to check_draft
│   ├── recipe_capture.py        # reads the person's units
│   ├── recipe_save.py           # keep_units
│   ├── recipe_manage.py         # keep_units, units on the stored recipe
│   ├── recipe_vocabulary.py     # per-person list
│   ├── carts.py                 # records created and edited
│   ├── shopping_list.py         # records closed
│   └── side_panel.py            # is_admin
├── adapters/
│   ├── llm/prompts/recipe_extraction_system.md   # rule against folding a measure word
│   └── persistence/
│       ├── units.py             # new
│       ├── admin.py             # new
│       ├── cart_activity.py     # new
│       ├── models.py
│       └── migrations/versions/0013_custom_units.py   # new
├── api/
│   ├── routes/                  # recipe_capture, recipes, side_panel, admin (new)
│   ├── schemas/                 # recipes, shopping_list, side_panel, admin (new)
│   └── deps.py
└── tests/
    └── fixtures/                # ai_eval/canned_beans.txt, prompt golden file

ui/
├── app/
│   ├── admin/                   # new: page and sections
│   └── api/
│       ├── admin/[section]/     # new BFF route
│       └── recipe-vocabulary/   # unit-check BFF route
├── components/
│   ├── RecipeDraft/             # IngredientLineRow picker, UnknownUnitQuestion (new)
│   ├── RecipeEdit/              # vocabulary, not the fixed list
│   └── SidePanel/               # admin entry
└── lib/
    ├── capture/                 # draftRules, captureStore, captureClient, saveClient
    ├── recipeEdit.ts
    ├── recipesClient.ts
    ├── shoppingListClient.ts    # custom kind
    └── i18n/                    # question and dashboard text, en and es

dev/docs/prd.md, AGENTS.md, README.md   # texts the spec says must change
```

**Structure Decision**: The existing `api` and `ui` layout. `ui/app/admin/` and `ui/app/api/admin/` are new route folders under `app/`, which AGENTS.md already lists for pages and BFF routes.

## Build order and cut-lines

1. **Foundation**: the migration, domain rules, `UnitRepository`.
2. **US1 and US2 together**: one has no value without the other.
3. **US3 ships in the same release as US1**. It's P2 by value, but without it a saved `lata` silently drops off a shopping list and blocks other members' edits, so it is not a cut-line.
4. **US4 is the cut-line.** Everything from `is_admin` on, `cart_activity` included, can move to a later release with no effect on cooking flows.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| §9: a `later` story built while Must stories are open, one day before the v1 deadline | The owner redirected S-055 on 2026-11-01 and specified it. **Exception approved by the owner on 2026-11-02**, see Approvals below | Deferring it is the rule's default, and it's the owner's call. Planning changes no code, so the plan goes ahead |
| AGENTS.md and PRD §3: dashboard reads recipe titles and figures across notebooks the admin doesn't belong to | FR-017d asks for it, and the spec records the exception. Scope: the `/admin/recipes` route only. Document it at the top of `application/admin.py` | A dashboard limited to the admin's own notebooks can't show how the app is used. AGENTS.md and PRD text change with this feature, which AGENTS.md says needs explicit approval. **Approved by the owner on 2026-11-02**, see Approvals below |

### Approvals

- Approved by: Sebastian Soto M (project owner), on 2026-11-02, in the Claude Code session that produced `tasks.md` ("approved, record both in plan.md").
- **§9 exception.** Scope: S-055 as specified in `spec.md`, built while Must stories are open. It covers no other `later` story.
- **AGENTS.md edits.** Scope: task T072 only: the text on the fixed list of units, and the "every recipe query" rule for the `/admin/recipes` route. It covers no other change to AGENTS.md or the constitution.
