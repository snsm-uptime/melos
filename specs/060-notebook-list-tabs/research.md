# Research: Notebook List and Tabs in the UI

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Every decision below was checked against the code on 2026-10-25. Nothing here was left as NEEDS CLARIFICATION.

## R1: Client components call the BFF; the tab page keeps the alias gate on the server

- **Decision**: The Notebook tab and the kitchen notebooks section are client components that fetch `/api/notebooks/...` (the same-origin BFF). The `/notebooks` page is a server component that only runs `requireAlias("/notebooks")` and resolves the locale, as `app/kitchens/[kitchenId]/page.tsx` does.
- **Rationale**: FR-021 says every notebook call goes through a same-origin BFF route. The kitchen page calls the api directly from the server for its members list, but spec 056 made the notebook BFF routes the contract for the ui, so the new screens use them. The server-side alias gate keeps FR-010 and matches the kitchen page.
- **Alternatives considered**: Server components calling the api internal URL, as the kitchen page does for members. Rejected: it would bypass the BFF that FR-021 names, and the notebook screens would then be the only ones with a different path.

## R2: Language follows the `melos_lang_cache` cookie, default English

- **Decision**: The page resolves the locale from the `melos_lang_cache` cookie, accepting only `es` or `en` and falling back to `en`, the same rule as `resolvePageLocale` in the kitchen page. Strings live in `ui/lib/i18n/notebooks.ts` with `en` and `es` entries, following `kitchensMessages`.
- **Rationale**: This is what the kitchen page does today, so the new screens match it. It also matches Clarification 2026-10-25 (English until the account language setting, Story 1.6, exists). Until that setting writes the cookie, every person sees English.
- **Correction to the spec**: The first draft of the spec said the UI picks the language from the browser. The code does not do that on these pages. The spec's Assumptions now describe the cookie rule.
- **Alternatives considered**: Reading `Accept-Language` through `detectLocale` in `ui/lib/i18n/locale.ts`. Rejected: the kitchen page does not use it, so these screens would disagree with the rest of the app.

## R3: Notebook tab placement and highlight

- **Decision**: Add an item to the `tabs` array in `AppShell.tsx`, with key `notebook`, href `/notebooks`, and an icon. Add `/notebooks` to `APP_CHROME_PREFIXES` in `ui/lib/appChrome.ts` so the tab bar stays mounted, and return `"notebook"` from `tabKeyFromPath` for `/notebooks` paths.
- **Rationale**: `TabBar` was written so that a new tab is one array entry (its comment says "a new tab is just a new item"). `showsAppChrome` and `tabKeyFromPath` decide whether the bar shows and which tab is current.
- **Alternatives considered**: Putting notebooks under `/home`. Rejected: Home is the kitchens list; a separate tab matches the backlog's "personal Notebook tab".

## R4: One shared notebook card

- **Decision**: A new `NotebookCard` component renders a notebook-shaped card: a rectangle with a spine or cover edge and the name, owner line and, on the tab, access and default marker. It is a plain element (`article` or `li`), not a link, so FR-014 holds. Its props are the `NotebookResponse` fields it shows, plus a `showAccess` flag for the tab.
- **Rationale**: Both screens show cards, and the spec requires one shape (FR-003, FR-004). The default marker is text ("Default"), not only a color, so screen readers announce it.
- **Alternatives considered**: Reusing a generic list row. Rejected: the user asked for cards shaped like notebooks, not rows.

## R5: Kitchen section placement

- **Decision**: The kitchen page renders `KitchenNotebooksSection` in the `detailPrimary` column, under the members list, with a `SectionLabel`. It receives `kitchenId` and the archive state. It does not render an add-recipe action (FR-006 and the assumption in the spec).
- **Rationale**: The page already has a primary column (members) and a sidebar (`TemporalNavigation`). Notebooks belong with the kitchen's content, not with its invite and time controls. Archive state comes from the kitchen detail payload already fetched by the page.
- **Alternatives considered**: Adding a third tab inside the kitchen page. Rejected: the spec does not call for one, and the page has no tab component for kitchens.

## R6: The tap is inert until S-021

- **Decision**: `NotebookCard` has no click handler and no link. It is marked `aria-disabled` only if a visible disabled style is needed; otherwise it is not interactive. S-021 will add the link.
- **Rationale**: Clarification 2026-10-25 (option A): cards do nothing until S-021 ships. FR-013 keeps recipe lists out of this feature.
- **Alternatives considered**: A placeholder page per notebook. Rejected: it would be a new route the spec does not ask for.

## R7: Ensuring the default notebook on the tab

- **Decision**: The tab calls `GET /api/notebooks/default` first, then `GET /api/notebooks`. If the first call fails, the tab shows the error state and does not list.
- **Rationale**: Spec 056 says the default is created on its first call and that listing creates nothing. Calling the default first makes the first visit show the default (FR-001, SC-001), and an error there must not look like an empty list (FR-009).
- **Alternatives considered**: Listing only. Rejected: a person who has never opened the tab would see an empty list, which contradicts SC-001.

## R8: Not-found and error states

- **Decision**:
  - Kitchen section: a `404` from `GET /api/notebooks/kitchens/{id}` shows the same message the kitchen page shows for a missing kitchen (`detailNotFound`), and no cards. Any other failure shows `loadError` with a retry button.
  - Tab: a `403` with `code: alias_required` redirects to the existing alias step, as the rest of the app does. Other failures show `loadError` with retry.
- **Rationale**: FR-007 and FR-009. The kitchen page already maps 404 to "unavailable", so the section agrees with it.
- **Alternatives considered**: A separate "no access" message for non-members. Rejected: spec 056 SC-004 requires non-members and missing kitchens to get the same answer.

## R9: Archived kitchens

- **Decision**: The section lists notebooks for members of an archived kitchen (spec 056 returns them), and shows an empty state when the list is empty. It shows no add-recipe action in either case.
- **Rationale**: FR-006 and spec 056 FR-016.
- **Alternatives considered**: Hiding the section for archived kitchens. Rejected: FR-006 requires the list to stay visible to members.

## R10: Tests

- **Decision**: vitest component tests for `NotebookCard` (inert, default marker, unknown owner), for the tab screen (default-then-list order, alias redirect, error with retry), and for the section (404, empty, archived, list). Browser checks follow [quickstart.md](./quickstart.md).
- **Rationale**: Constitution §6: vitest for components, browser for feature correctness.
- **Alternatives considered**: End-to-end test framework. Rejected: not in the stack (constitution §2).
