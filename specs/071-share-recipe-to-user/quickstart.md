# Quickstart: Share a recipe with a person from the recipe page

How to run and check the feature end to end. Use the Compose dev stack. Do not start a second
Compose project against the main `.env` (its dev data directory is shared; see project memory).
Use an isolated stack for any browser walk.

## Prerequisites

- Two test accounts that share a kitchen, and a third that shares only a notebook with the first.
  Invent the aliases; no real personal data (constitution principle 4).
- A recipe in the first account's notebook.
- Stack running with the feature's migrations (none expected; see research R-2).

## Automated checks

```bash
# api: domain, application (fakes), integration (Postgres via the test overlay)
cd api && uv run pytest tests/application/test_recipe_share.py
docker compose -f docker-compose.test.yml up --abort-on-container-exit   # integration suite

# ui: popup component
cd ui && npx vitest run components/ShareRecipeDialog
npx eslint components/ShareRecipeDialog
```

Expected: all pass. Integration cases must cover co-member listing and order, 404 for a non-member
recipient, 404 for an unreadable recipe, refusal with no default notebook, and no change to the
source recipe.

## Manual walk

1. Log in as the first account and open a recipe.
2. Press the share icon in the page header (FR-001). Expect a popup with a search field and the send
   icon, which is disabled.
3. Expect the kitchen and notebook co-members at the top of the list, then nothing else from the
   account list (FR-003, FR-004). A stranger's alias must not appear, even when typed in full.
4. Type part of an alias. Expect narrowing with the same order (FR-005).
5. Choose the co-member. Expect the send icon to enable (FR-007). Press it once.
6. Expect a success message naming the person, and the list gone (FR-009; SC-004 within 2 s).
7. Log in as the recipient. Open the default notebook. Expect the copy, with the recipient as author
   (FR-008). Edit the copy; reopen the original; expect it unchanged (FR-011, US2).
8. Repeat step 2 in Spanish. Expect Spanish strings for every popup message (FR-012).

## Edge checks

- No co-members: empty-result message, send disabled (edge case).
- Recipient with no default notebook: refusal message, no copy created.
- Send failure (for example the recipient was deleted): error message, popup stays open with the
  recipient selected (FR-010).
- Double-click send: exactly one copy appears in the recipient's notebook (R-4). This is the known
  gap if the client guard is bypassed; record any duplicate in the feature notes.

## Known gaps

- The "most recent" order depends on membership timestamps (R-1). If they are absent, the order is
  alphabetical and this must be stated in the story notes.
- No server-side dedupe of repeated identical sends (R-4).
