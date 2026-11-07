# Codebase improvements: repeated code to consolidate

Survey date: 2026-11-06.

## How this was found

A small duplicate detector scanned the `ui` and `api` source files. It hashes
normalized windows of 6 lines and reports the windows that appear in more than
one file. It skipped tests, migrations, fixtures and icons. The largest
clusters were then read by hand. Line counts here are estimates, not measured
savings.

## Ranked by payoff

### 1. BFF proxy routes in `ui/app/api` (biggest win, ~1,460 lines in 28 files)

- 37 of the 65 `route.ts` files already use the shared helpers:
  `forwardRecipeRequest` in `ui/lib/recipeBff.ts`, or `ui/lib/authBff.ts`.
- The other 28 each copy the same steps by hand:
  1. forward the cookie
  2. call `fetch`
  3. on failure, return `{ detail: "Upstream unavailable.", code: "bad_gateway" }` with a 502
  4. pass the status and body through
- Five of them also redefine the same `forwardCookie()` function, for example
  `kitchens/[kitchenId]/archive`, `unarchive`, `invites` and `kitchens/[kitchenId]`.
- The largest of these routes:
  - `kitchens/[kitchenId]/route.ts` (131 lines)
  - `kitchens/route.ts` (88 lines)
  - `notebooks/default/route.ts` (74 lines)
  - `auth/me/route.ts` (72 lines)
  - `notebooks/[notebookId]/captures/url/route.ts` and `captures/text/route.ts` (69 and 63 lines)
- **Proposal:** turn `recipeBff.ts` into a general `lib/bff.ts` with
  `forward(request, { method, path, withBody, deadlineMs, timeoutError, passHeaders })`.
  The three new options cover what the custom routes need:
  - `Accept-Language` passthrough on requests (capture routes)
  - `Retry-After` passthrough on responses (capture routes)
  - an `ai_unavailable` (503) error when the request times out
- Most routes would shrink to 5–10 lines.

### 2. Client fetch wrappers in `ui/lib/*Client.ts`

- These are all the same function:
  - `cartClient.call`
  - `shoppingListClient.call`
  - `recipesClient.send`
  - `notebooksClient.requestJson` and `requestEmpty`
  - the fetch code in `places.ts`, `capture/captureClient.ts`, `capture/saveClient.ts`,
    `recipeShareClient.ts` and `sidePanelClient.ts`
- Each one:
  1. calls `fetch` with `credentials: "same-origin"`
  2. returns `{ ok: false, status: 0, code: null }` on a network failure
  3. reads the error `code` from the body
  4. parses the result and returns `{ ok: true, value }`
- There are four matching result types: `CartResult`, `ShoppingResult`,
  `RecipeResult` and `NotebookResult`.
- **Proposal:** one `lib/http.ts` that has:
  - `requestJson<T>(method, path, body, parse, readExtra?)`
  - one `ApiResult<T>` type
  - `readExtra` covers the extra error fields, such as `editor_alias` and `field` in the cart and recipe clients.
- `readMissing` and `readLineProblems` are also copied between
  `capture/captureClient.ts` and `capture/saveClient.ts`.

### 3. Recipe draft vs recipe edit

- `components/RecipeDraft/LeaveDraftGuard.tsx` and
  `components/RecipeEdit/RecipeEditLeaveGuard.tsx` are nearly identical. They
  differ only in where `edited` comes from and in the draft clearing the capture
  on leave. They should become one `LeaveGuard({ edited, messages, onLeave })`.
- `RecipeDraftEditor.tsx` (477 lines) and `RecipeEditForm.tsx` (495 lines)
  share about half their JSX: the header and Back slot, the title field, the
  ingredients section and the steps section.
- **Proposal:** pull out section components such as `RecipeTitleField`,
  `IngredientsSection` and `StepsSection`. This removes roughly 200 lines.
- This is the riskiest change, because both forms have a lot of tests.

### 4. Forms in `ui/app`

- `hooks/useFormSubmission.ts` already exists, but only `app/kitchens/InviteForm.tsx` uses it.
- These forms each manage their own pending and error state by hand:
  - `SignInForm`
  - `SignupForm`
  - `ResetPasswordForm`
  - `ForgotPasswordForm`
  - `VerifyForm`
  - `AliasSetupForm`
  - `NotebookNameDialog`
- They also miss the hook's guard against double submits, so moving them to the hook fixes that too.
- The password input with the show/hide eye toggle is repeated in sign-in,
  signup and reset password. It could become a `PasswordField` component in
  `components/soft-ledger/`.

### 5. Loading / not found / error rendering (13 screens)

- These screens repeat the same logic:
  - when loading, show `CauldronLoader`
  - when not found, show an alert message
  - on an error, show a message and a retry option
- Screens that do this:
  - `KitchenNotebooksScreen`
  - `KitchenNotebooksSection`
  - `AddNotebookSnapshot`
  - `NotebookDeleteDialog`
  - `NotebookRecipesScreen`
  - `NotebookTabScreen`
  - `ShoppingListSection`
  - `RecipeList`
  - `RecipeFromNotebookSheet`
  - `RecipeEditScreen`
  - `RecipeDetailScreen`
  - `IngredientsScreen`
  - `CartScreen`
- **Proposal:** a `<LoadState state={…} notFound={…} error={…}>{(data) => …}</LoadState>` component.

### 6. API error responses (Python)

- Five route modules each define their own private `_error()`:
  - `carts.py`
  - `shopping_list.py`
  - `recipes.py`
  - `recipe_capture.py`
  - `places.py`
- Another ~85 `JSONResponse(status_code=…, content={"detail": …, "code": …})`
  blocks are written inline in `api/api/routes/`. Most of them are in
  `auth.py`, `notebooks.py` and `kitchens.py`.
- **Proposal:** a shared `api/api/errors.py` with:
  - `error_response(status, code, detail="", **extra)`
  - `draft_problems_response(problems)`, because the `line_problems` /
    `draft_incomplete` / `ingredient_line_problem` block is copied between
    `routes/recipes.py` and `routes/recipe_capture.py`

## Lower priority

- About two-thirds of `api/adapters/persistence/email_verification.py` and
  `password_reset.py` is the same: both are one-time token stores. This is auth
  code taken from finance-dashboard, so it's probably not worth changing.
- `app/kitchens/KitchenNotebooksScreen.tsx` and `KitchenNotebooksSection.tsx`
  overlap. Item 5 would cover most of it.

## Suggested order

1. Item 1 (BFF routes) and item 2 (client fetch). Both are mechanical and
   low-risk, already have a working model to copy (`recipeBff.ts`), and save the most lines.
2. Item 4 (forms) and item 6 (API errors).
3. Item 5 (load states).
4. Item 3 (draft/edit forms). It needs the most care with tests.
