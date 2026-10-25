# Implementation Plan: Notebook List and Tabs in the UI

**Branch**: `059-notebook-list-tabs` (spec folder; the backlog id is S-059) | **Date**: 2026-10-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/059-notebook-list-tabs/spec.md`, with the 2026-10-25 clarifications.

## Summary

This feature is UI only. The api read routes and the ui BFF routes that it needs already exist from spec 055 (commits `187ff14` and `800b2f9`). This feature adds:

- a **Notebook** tab in the bottom tab bar, at `/notebooks`, that makes sure the person's default notebook exists, then shows their personal notebooks as cards (FR-001 to FR-003);
- a **notebooks section** on the kitchen page, under the members list, that shows the kitchen's notebooks as cards and creates the first one on first open (FR-004 to FR-006);
- a shared **notebook card** that looks like a notebook. A tap does nothing until S-020 exists (FR-014);
- labels in `en` and `es` that follow the same language rule as the kitchen page.

No new api route, BFF route, table, migration, env var or library. Nothing is written except the notebook creation that spec 055 already defines (default notebook on the tab, first notebook on the kitchen section).

## Technical Context

**Language/Version**: TypeScript with Next.js 16 (App Router) and React 19 (ui)

**Primary Dependencies**: Existing only: Next.js, React, Tailwind 4 with the soft-ledger components (`TabBar`, `SectionLabel`), `kitchensMessages`-style dictionaries under `ui/lib/i18n/`. No new library.

**Storage**: None in this feature. Reads the notebook answers from spec 055 ([`../055-notebooks/data-model.md`](../055-notebooks/data-model.md), [`../055-notebooks/contracts/notebooks-api.md`](../055-notebooks/contracts/notebooks-api.md)).

**Testing**: vitest for the card, the two lists and the BFF-to-screen mapping (component tests in the existing `*.test.tsx` style); the Compose stack and a browser check for the behavior (constitution §6: "Check UI in a browser before claiming success").

**Target Platform**: The Next.js `ui` container behind the Compose stack; phone-width layout first (the tab bar is the mobile navigation).

**Project Type**: Web application (ui BFF over the hexagonal api).

**Performance Goals**: One BFF call for the tab (default, then list) and one for the kitchen section. Meets SC-008 (2 s on a typical connection) with the same request count as the existing kitchen page.

**Constraints**:
- FR-021: every notebook call goes through a same-origin BFF route. The screens use client components that call `/api/notebooks/...`.
- FR-010: the Notebook tab page calls `requireAlias` on the server, as the kitchen page does.
- FR-011: labels follow `melos_lang_cache` (default `en`), as the kitchen page does.
- FR-008: read-only. No create, rename, delete, invite or copy control.
- FR-014: a card is inert until S-020 ships. It is rendered as a non-interactive element, not a link.

**Scale/Scope**: A household: a few notebooks per person and per kitchen; one screen per tab.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| §1 Simplicity and reuse | No service, no auth change, no new library. Reuses `TabBar`, `SectionLabel`, `requireAlias`, the BFF pattern and the kitchen page's language rule. | Pass |
| §1 Four services, external calls through ports | No new service. No external call. | Pass |
| §2 Stack stability | Next.js 16, React 19, Tailwind 4, vitest only. No dependency change. | Pass |
| §3 Hexagonal | Only the ui changes. The api already keeps non-members at 404 (spec 055 FR-016, SC-004); the ui shows that same answer as the not-found state. | Pass |
| §4 Security and privacy | The ui shows only what the api returns, and forwards the session cookie through the BFF. No new data is stored in the browser. | Pass |
| §5 No AI shortcuts | Not applicable: no AI. | Pass |
| §6 Testing | Component tests (vitest) for cards, lists and states; browser check of the tab, the kitchen section, the archived case and the alias gate. | Pass |
| §7 Deployment | Nothing new to deploy; `/health` unchanged. | Pass |
| §8 Git discipline | Small commits, no force-push, no commit made without the user's request. | Pass |

No violations, so the Complexity Tracking table is empty.

## Project Structure

### Documentation (this feature)

```text
specs/059-notebook-list-tabs/
├── spec.md
├── plan.md                  # This file
├── research.md              # Phase 0
├── data-model.md            # Phase 1: no new entities; points to spec 055
├── quickstart.md            # Phase 1: run and check guide
├── contracts/
│   └── notebook-screens.md  # Phase 1: which BFF routes each screen calls, and its states
└── checklists/requirements.md
```

### Source Code (changed or added in `ui/`)

```text
ui/
├── app/
│   ├── notebooks/                       # NEW: the Notebook tab
│   │   ├── page.tsx                     # server: requireAlias, locale, renders the screen
│   │   ├── NotebookTabScreen.tsx        # client: ensure default, list personal, states
│   │   └── notebooks.module.scss        # shared styles for the tab and the section
│   ├── kitchens/[kitchenId]/page.tsx    # CHANGED: renders the notebooks section under members
│   ├── kitchens/KitchenNotebooksSection.tsx   # NEW: client; list kitchen notebooks, states
│   └── api/notebooks/...                # unchanged (spec 055 BFF routes)
├── components/
│   ├── NotebookCard/                    # NEW: notebook-shaped, inert card
│   │   ├── NotebookCard.tsx
│   │   └── NotebookCard.module.scss
│   └── AppShell.tsx                     # CHANGED: adds the Notebook tab item
├── lib/
│   ├── appChrome.ts                     # CHANGED: "/notebooks" keeps the tab bar and highlights its tab
│   ├── notebooksClient.ts               # NEW: fetch helpers and the NotebookResponse type
│   └── i18n/notebooks.ts                # NEW: en/es strings for the tab, section, card and errors
```

**Structure Decision**: Web application. Changes stay in `ui/`. The notebook card is a shared component, because the tab and the kitchen section both use it. Both lists are client components so every call goes through the BFF (FR-021). The tab page stays a server component only for the alias gate and the locale, which matches the kitchen page.

## Phase 0: Research

Resolved in [research.md](./research.md). No NEEDS CLARIFICATION remains. The decisions are: BFF calls from client components; the language rule; tab placement; the card component; the kitchen section placement; the inert tap; and the not-found and error states.

## Phase 1: Design

- [data-model.md](./data-model.md): no new entities. The card reads the `NotebookResponse` shape from spec 055.
- [contracts/notebook-screens.md](./contracts/notebook-screens.md): which BFF routes each screen calls, in what order, and the state each response leads to.
- [quickstart.md](./quickstart.md): how to bring the stack up, seed a person and a kitchen, and check each acceptance scenario in the browser.

## Post-design Constitution Check

Re-checked after Phase 1: no change. No new service, route, table, library or env var is introduced, so every row above still passes.

## Complexity Tracking

Empty. No constitution violation to justify.
