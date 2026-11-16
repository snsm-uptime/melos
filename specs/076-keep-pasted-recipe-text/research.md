# Research: Keep Pasted Recipe Text and Offer Personal Notebooks

**Feature**: 076-keep-pasted-recipe-text | **Date**: 2026-11-16

## R1 — Where the pasted text lives today

- **Finding**: `ui/lib/capture/captureStore.ts` holds `text` in a module-level object. `closeSheet()` keeps it, `backToSheet()` keeps it, and `markSaved()`, `discardDraft()` and `startManualDraft()` set it to `""`. A reload, or the browser dropping the tab while the app is in the background, loses it.
- **Decision**: Keep the store as the single source of truth and mirror `text` into the browser's per-tab session storage. Every `update()` that changes `text` writes it, and an empty string removes the key. On first client read, the store starts from the stored value.
- **Rationale**: This follows the store's existing lifecycle, so Back from the draft still shows the text (spec 016 FR-031), and save or discard still clears it (FR-006 as corrected). Session storage is per tab and is cleared when the tab or window closes. That matches "only during the current session" and the edge case that a second tab starts empty.
- **Alternatives considered**:
  - *localStorage*: survives closing the browser, which breaks FR-003.
  - *Server-side draft*: sends the text before submit, which breaks FR-005 and adds an API and a table for no gain.
  - *Persist the whole capture state (draft, notebook, link, picture)*: out of scope. A `File` can't be serialized, and the spec covers only the text.

## R2 — Hydration safety

- **Finding**: `useCaptureState` uses `useSyncExternalStore` with `EMPTY` as the server snapshot.
- **Decision**: Read session storage lazily the first time `getCaptureState()` runs in the browser, not when the module is imported on the server. Wrap every read and write in `try/catch`: storage can be blocked in private mode or full, and then the app works as it does today.
- **Rationale**: The server snapshot stays `EMPTY`, so the server-rendered HTML matches the first client render. React then switches to the client snapshot after hydration, so no hydration-mismatch warning appears.

## R3 — Not leaking text to another member (FR-004)

- **Finding**: `ui/lib/signOut.ts` already clears per-person client caches (`clearPrefsCache`, `resetMembershipKitchensStore`) before and after the sign-out call.
- **Decision**: Add `clearKeptCaptureText()`, which removes the storage key and resets the in-memory `text`, to `signOut()`. Also call it when sign-in succeeds (`app/sign-in/SignInForm.tsx`). That covers a session that expired without a sign-out, followed by another person signing in on the same tab.
- **Alternatives considered**: Key the stored text by user id. The client doesn't hold the user id everywhere it would need it. Clearing at both sign-in and sign-out gives the same guarantee with less code.

## R4 — Notebooks for the side panel (FR-008)

- **Finding**: `GET /api/notebooks` (`ListMyNotebooksService` → `visible_facts_for`) already returns the personal notebooks the caller owns or belongs to, and every notebook of every kitchen they belong to. Each row carries `kind`, `kitchen_id`, `kitchen_is_archived`, `is_default` and `is_own_capture_notebook`. Today `QuickAddRecipe` throws away everything that isn't `kind === "personal"` outside a kitchen, and calls only `fetchKitchenNotebooks(kitchenId)` inside one.
- **Decision**: The side panel uses `fetchPersonalNotebooks()` (the same endpoint) and keeps:
  - personal notebooks: all of them
  - kitchen notebooks: those whose kitchen isn't archived (`kitchen_is_archived !== true`)
  On a kitchen's pages, it adds the current kitchen's "new notebook" row when `is_own_capture_notebook` is false for every one of that kitchen's notebooks, as today. If there are no personal notebooks, it still calls `fetchDefaultNotebook()` first, as today.
- **Preselection**: On a kitchen's pages, the member's own notebook in that kitchen, or the "new" row (as today). Elsewhere, the default personal notebook, then the first personal notebook, then the first row.
- **Rationale**: No API change, no new endpoint, one request instead of one per kitchen.
- **Alternatives considered**: One `fetchKitchenNotebooks` call per kitchen. That's N requests, and it duplicates what the list endpoint already returns.

## R5 — Telling notebooks apart in the picker (FR-012)

- **Finding**: `NotebookPicker` passes `{ id, name }` to `SearchableSelect`. `SearchableSelectOption` already supports `dividerBefore`, which draws a divider above a row to start a group.
- **Decision**: Add an optional `detail` to `NotebookPickerOption`, rendered in the label as `"{name} · {detail}"`, and an optional `dividerBefore` passed straight through. The side panel puts personal notebooks first (detail: the localized "Personal"), then each kitchen's notebooks (detail: the kitchen's name, from `useMembershipKitchens()`), with a divider before each group. `CaptureCandidate` gets the same two optional fields. Captures from a notebook's page or a kitchen's page don't set them, so those pickers look exactly as they do today.
- **Rationale**: Search keeps working on the full label, so typing a kitchen name finds its notebooks. The sheet title and the draft still use the plain notebook name.
- **Alternatives considered**: Real group headers in `SearchableSelect`. That's a bigger change to a shared component for no extra clarity.

## R6 — "Inside a notebook" and "on a kitchen's page" (FR-009, FR-010)

- **Finding**: `NotebookRecipesScreen` passes a single candidate, the notebook itself. The text, link and picture sheets show the picker only when `candidates.length > 1`, so a notebook's page already captures into itself with no choice. `KitchenNotebooksSection` passes only that kitchen's notebooks, plus the "new" row.
- **Decision**: No change. Regression tests are added so the behaviour stays this way.

## R7 — Multiple "new notebook" rows

- **Finding**: `OWN_NEW_NOTEBOOK_ID` is one fixed id. `pickerOptions` and `captureTarget` assume at most one "new" row per picker.
- **Decision**: The side panel offers the "new" row only for the kitchen whose pages are open. Outside a kitchen it offers existing kitchen notebooks only, so there is never more than one "new" row. The spec's edge case was updated to match.
