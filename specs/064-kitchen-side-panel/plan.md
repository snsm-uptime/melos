# Implementation Plan: Kitchen Side Panel

**Branch**: `064-kitchen-side-panel` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/064-kitchen-side-panel/spec.md`, backlog S-064

## Summary

Replace the bottom tab bar and the kitchens list on `/home` with one left panel in `AppShell`: avatar, alias with recipe count, Home, other kitchens, Notebooks, log out. It shows icons only when closed on larger screens, and is a drawer over the content on phones. Kitchen management moves to icon buttons in the kitchen header row and a "+" in the panel. The api gains a nullable `users.default_kitchen_id` and a small `side-panel` read and set route. The default is resolved on read, so signup and the auth routes are not changed.

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript with Next.js 16 and React 19 (ui)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Tailwind 4. No new library.

**Storage**: PostgreSQL 16, one new column (migration `0009_default_kitchen`). Open or closed state in `localStorage`.

**Testing**: pytest in the Compose test overlay, fake repositories for the use case, vitest for the panel, browser walk in [quickstart.md](quickstart.md)

**Target Platform**: Phone and desktop browsers, breakpoint `md` (768px)

**Project Type**: Web application (`api/`, `ui/`)

**Performance Goals**: The side-panel read uses at most 4 SQL statements (1 for the user, 2 for the kitchens, 1 count), plus one write when the default changes

**Constraints**: Authentication layer unchanged. Non-members get `404`. All text in English and Spanish (parity test). 44px touch targets (`size-11`).

**Scale/Scope**: About 20 kitchens per person (SC-007). Removes `TabBar`, `KitchensPanel`, `HomeKitchensSection`, `HomeChrome` and `ChromeAvatarLink`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| 1 Simplicity and Reuse | Pass | No service added. The auth layer is untouched: the default lives outside `/auth/*`, and the panel only calls the existing sign-out route. |
| 2 Tech Stack | Pass | No library added. |
| 3 Hexagonal | Pass | Resolution rule in `domain/`, use cases in `application/`, membership checked there. |
| 4 Security and Privacy | Pass | The route answers for the caller only. The count is one integer about the caller. |
| 5 No AI Shortcuts | N/A | No AI. |
| 6 Testing | Pass | All layers covered. The browser walk stays a required step. |
| 7 Deployment | Pass | No infrastructure change. |
| 8 Git Discipline | Pass | Schema change through Alembic. |
| 9 Scope and Schedule | **Exception approved by the owner, 2026-10-30** | Not in PRD Appendix C "Must", and 16 Must stories remain open before 02/11. Written approval given at `/speckit-implement`. See Complexity Tracking. |

Post-design re-check: same result. The design added no violation.

## Project Structure

### Documentation (this feature)

```text
specs/064-kitchen-side-panel/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── side-panel-api.md
│   └── side-panel-ui.md
└── tasks.md             # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
api/
├── domain/default_kitchen.py                       # new: pure resolution rule
├── application/side_panel.py                       # new: read and set use cases
├── adapters/persistence/side_panel.py              # new: repository
├── adapters/persistence/models.py                  # default_kitchen_id
├── adapters/persistence/migrations/versions/0009_default_kitchen.py
├── api/routes/side_panel.py, api/schemas/side_panel.py
└── tests/                                          # domain, application, HTTP

ui/
├── components/SidePanel/                           # new: panel, entries, create dialog, state hook
├── components/AppShell.tsx                         # panel replaces TabBar; phone menu button
├── components/AccountMenu.tsx                      # sign out removed
├── lib/appChrome.ts                                # panelEntryFromPath replaces tabKeyFromPath
├── lib/signOut.ts, lib/sidePanelClient.ts          # new
├── lib/i18n/sidePanel.ts                           # new
├── app/api/side-panel/                             # new BFF routes
├── app/home/page.tsx                               # redirect, or the no-kitchens view
├── app/kitchens/KitchenDetailChrome.tsx            # management icon buttons
└── app/kitchens/kitchensClient.ts                  # unarchive updates the store
```

**Structure Decision**: Existing `api/` and `ui/` layout. `ui/components/SidePanel/` follows the one-folder-per-component pattern already used there.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle 9: story outside Appendix C "Must", planned while Must stories are open | Direct owner request; the spec is already on `main` | Waiting for Must to finish is the alternative. It is the owner's call before `/speckit-implement`, not one this plan can make. |
