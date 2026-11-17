# UI Contract: Keep Pasted Recipe Text and Offer Personal Notebooks

No HTTP contract changes. The side panel reads the existing `GET /api/notebooks` (through the `/api/notebooks` route handler) and uses fields that are already there: `kind`, `kitchen_id`, `kitchen_is_archived`, `is_default`, `is_own_capture_notebook`.

## Capture store (`ui/lib/capture/captureStore.ts`)

```ts
/** Removes the kept text from this tab and from memory. Called on sign-in and sign-out. */
export function clearKeptCaptureText(): void;
```

Existing functions keep their signatures. The only behaviour change is that `text` is now mirrored to session storage, following the lifecycle in [data-model.md](../data-model.md#kept-capture-text-browser-session-storage).

## Sign-in and sign-out

- `ui/lib/signOut.ts → signOut()` calls `clearKeptCaptureText()` alongside the existing cache resets.
- `ui/app/sign-in/SignInForm.tsx` calls `clearKeptCaptureText()` after a successful sign-in, before navigating.

## Notebook picker (`ui/components/NotebookPicker`)

```ts
export type NotebookPickerOption = {
  id: string;
  name: string;
  /** Shown after the name ("Dinners · Casa Soto"); searched like the name. */
  detail?: string;
  /** Draws a divider above this row (a new group). */
  dividerBefore?: boolean;
};
```

Existing callers that pass `{ id, name }` render as they do today.

## Add-recipe entry points

| Entry point | Candidates | Picker shown | Default |
|-------------|------------|--------------|---------|
| Side panel (`QuickAddRecipe`), outside a kitchen | All personal notebooks plus notebooks of every active kitchen, grouped | When there is more than one | Default personal notebook |
| Side panel, on a kitchen's pages | The same, with the current kitchen's group first, plus its "new" row when needed | When there is more than one | Own notebook in that kitchen, or the "new" row |
| Notebook page (`NotebookRecipesScreen`) | That notebook only | Never | That notebook |
| Kitchen page (`KitchenNotebooksSection`) | That kitchen's notebooks plus "new" row when needed | When there is more than one | Own notebook, or the "new" row |

Rows 3 and 4 are unchanged (regression-tested only).
