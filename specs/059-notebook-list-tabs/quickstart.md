# Quickstart: check the Notebook tab and the kitchen notebooks section

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Screens contract**: [contracts/notebook-screens.md](./contracts/notebook-screens.md)

## Prerequisites

- Docker with Compose v2 and `.env` filled in (AGENTS.md "Development environment").
- The spec 055 notebook API and BFF routes are present on the branch (commits `187ff14` and `800b2f9`).
- Two invented users, Ana and Ben, with the aliases "ana" and "ben" (see spec 055 quickstart §3 for the sign-up steps).

## 1. Automated checks

```bash
cd ui && npm test && npm run lint && npm run typecheck
```

Expected: all green. The new tests cover:

- `NotebookCard`: inert (no link, no button), "Default" marker only on the default, "unknown" for a null owner.
- Notebook tab: calls `default` before `list`; an alias error redirects; a failure shows retry and no list.
- Kitchen section: 404 shows the not-found message; an empty list shows the empty state; no add-recipe action.

## 2. Start the stack

```bash
./scripts/compose-up.sh -d
```

Open the ui in two browser profiles, one for Ana and one for Ben.

## 3. Notebook tab (User Story 1)

| Step | Action | Expected |
|---|---|---|
| 1 | Ana opens the Notebook tab for the first time | The tab shows one card, "ana's Notebook", owner "ana", access "owner", marked "Default" |
| 2 | Ana reloads the tab | The same card, no second default |
| 3 | Ana, a member of Ben's personal notebook "Family" | "Family" shows owner "ben", access "member", no default marker |
| 4 | Ana belongs to kitchen "Home" | Home's notebook is not on the tab |
| 5 | Tap any card | Nothing happens (FR-014, until S-020) |
| 6 | Open the tab with no alias | Redirected to the alias step; no notebook created |

## 4. Kitchen notebooks section (User Story 2)

| Step | Action | Expected |
|---|---|---|
| 1 | Ana creates kitchen "Home" and opens its page | The notebooks section shows one card, "ana's (Home) Notebook", owner "ana" |
| 2 | Ben, a member, opens Home's page | Ben sees the same card; no second notebook |
| 3 | Ana and Ben open Home's page at the same moment (first time on a new kitchen) | One notebook exists, and both see it |
| 4 | Archive Home, then open its page as a member | Its notebooks are still listed; no add-recipe action appears |
| 5 | Archive a kitchen with no notebook, open its page | Empty state; no notebook created |
| 6 | Carl, not a member, opens Home's page | The not-found message; no cards |

## 5. Failures (User Story 3)

| Step | Action | Expected |
|---|---|---|
| 1 | Stop the api container, reload the tab | The error message with retry; no list |
| 2 | Start the api again, press retry | The default and the list appear |
| 3 | Remove Ben from Home (or use a test membership change), reload Home | The not-found message; no cards |

## 6. Language (FR-011)

| Step | Action | Expected |
|---|---|---|
| 1 | Clear the language cookie and open the tab | English labels |
| 2 | Set the `melos_lang_cache` cookie to `es` and reload | Spanish labels; names unchanged |

## 7. Browser check (constitution §6)

Check the phone width first: the tab bar stays at the bottom, the cards do not overflow, and there is no horizontal page scroll.
