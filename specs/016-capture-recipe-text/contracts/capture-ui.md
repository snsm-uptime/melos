# Contract: Capture UI

Normative for routes, the shared component's props and behaviour, and the
member-facing strings. Strings are English in this feature, kept in `ui/lib/i18n/capture.ts`
so that internationalization can follow after MVP, chosen by the account language
setting (FR-034).

## Routes

| Route | Shows | Tab marked |
|-------|-------|------------|
| `/notebooks` | Header "Notebook" (the tab from spec 060). Reads the default notebook through `/api/notebooks/default` and the list through `/api/notebooks` (spec 056). `AddRecipeCallToAction` above the list, preselecting the default notebook. No recipe list (S-021). | `notebook` |
| `/notebooks/draft` | Draft review for the notebook the capture is for, whichever page opened it. Redirects to that page (the store's return path) when there is no draft. | `notebook` |
| `/kitchens/[kitchenId]` | Members, and the notebooks section (spec 060). `AddRecipeCallToAction` above the notebook cards, **only when not archived** (FR-033). No separate Notebook tab: the section is the kitchen's notebook view. | `home` |

## `AddRecipeCallToAction` (`ui/components/AddRecipeCallToAction/`)

```ts
type AddRecipeCallToActionProps = {
  notebook: { id: string; kind: "personal" | "kitchen"; name: string };
  locale: Locale;
};
```

- Renders a placeholder rectangle with standard rounded corners and a centred
  `PlusIcon`, as a `<button>` with the accessible name "Add a recipe".
- Activating it opens `AddRecipeOptionsDialog`, built on `ActionDialog` with no
  `confirmLabel`/`cancelLabel` (footer hidden). The dialog is titled "Add a
  recipe" and has a vertical list separated by dividers:
  1. **URL**: `aria-disabled`, with the secondary text "Not available yet".
  2. **Picture**: `aria-disabled`, with the secondary text "Coming soon".
  3. **Text**: enabled. Closes the dialog and opens `TextCaptureSheet`.
  Escape or a backdrop click closes the dialog and changes nothing.
- On mount, if the store holds `sheetOpen` for this same notebook (Back from
  the draft page), the sheet opens again with the stored text.

### `TextCaptureSheet`

- `Sheet` titled with the notebook's label (FR-001a). A **notebook picker** sits under the title. Outside a kitchen it lists the member's personal notebooks they own or belong to (from spec 056's list route), with the default preselected; with one, there is no picker. In a kitchen it lists that kitchen's notebooks; with several, the member picks one. A kitchen's notebook exists from the first open of its Notebook page (spec 056 FR-008a).
- A multi-line paste input labelled "Recipe text". A live counter appears once
  the text is over 90% of `max_text_chars`.
- The submit control is disabled when the text is empty or whitespace, when it
  is over `max_text_chars` after trimming (with the message "That text is too
  long. Paste up to {max_text_chars} characters."), the configured limit., or while submitting.
- While submitting, it shows a progress state ("Reading your recipe…") and
  the input is read-only (FR-004).
- On 200, the store moves to `draft` and the app navigates to the notebook's
  draft route.
- On any other answer, the message for its `code` appears inside the sheet
  (role `alert`) and the text stays unchanged and editable (FR-014 to FR-018,
  FR-028).

## `ActionDialog` (edit)

`confirmLabel`, `cancelLabel` and `onConfirm` become optional. When both labels
are absent, the footer is not rendered and focus goes to the first focusable
child. Existing callers pass all three and render exactly as before.

## Draft review page (`RecipeDraftEditor`)

Full screen inside the notebook route, with chrome header "Review recipe" and
a Back control.

| Area | Behaviour |
|------|-----------|
| Notebook line | "For: " + `notebook.label` (FR-001a). |
| Title | Editable text. Errors: "Add a title." / "Keep the title under 200 characters." |
| Servings | Editable integer and an "estimated" badge while `servingsEstimated` is true. Error: "Servings must be a whole number of at least 1." |
| Categories | Chips in `language` (the member's configured language). Main ingredients and cuisines in two groups. Variant chips read "Variant · Tag". Each group has an add picker (`ChipPicker`) fed by `/api/recipe-vocabulary`, hidden at 2. A chip has a remove control. |
| Ingredients | One row per line: name, quantity, unit (select from the allowed set), size (select, only when unit is `unit`), preparation, note. A "vague amount" toggle clears quantity and unit. Rows can be added, removed, moved up and moved down. Line errors appear under the row: "Add an amount and a unit, or mark it as vague." / "A vague amount has no number or unit." / "Size is only for counted items." |
| Steps | Ordered, editable list. Steps can be added, removed, moved up and moved down. Error: "Add at least one step." |
| Discard | Always enabled (FR-020). Clears the draft and the text, then returns to the Notebook page with the text sheet open and empty. |
| Back | Returns to the Notebook page with the text sheet open and the text unchanged (FR-031). No prompt. |
| Save | **Not shown** (S-020). |

### Leave guard (`LeaveDraftGuard`)

Active only while `edited`. Any same-origin link that leads away from the draft
route opens an `ActionDialog`:

- Title: "Leave without saving?"
- Body: "Your changes to this draft will be lost."
- Buttons: "Stay" (cancel; keeps the draft) and "Leave" (confirm; clears the
  store and follows the link).

Reloading or closing the tab uses the browser's `beforeunload` warning.

## Bottom tab bar

The Notebook tab already exists (spec 060) at `/notebooks`; this feature does not add a tab. The items, in order, are: Home (`/home`), **Notebook** (`/notebooks`), then the existing items.
label "Notebook"), then the existing items. Cart and chat tabs come with their
own stories.
