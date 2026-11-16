# Quickstart: Validate 076 Keep Pasted Recipe Text and Offer Personal Notebooks

## Prerequisites

- Stack running: `./scripts/compose-up.sh`
- Sign in with a seeded dev account that owns at least two personal notebooks, belongs to one personal notebook shared by someone else, and belongs to an active kitchen with two notebooks (see the fixed dev accounts from the seed, PR #44).

## Automated checks

```sh
cd ui && npm run test -- captureStore QuickAddRecipe NotebookPicker TextCaptureSheet signOut
cd ui && npm run lint && npm run typecheck
```

Expected: all pass. The new tests cover the session-storage lifecycle ([data-model.md](./data-model.md)), the side-panel candidate list, and the notebook-page and kitchen-page regressions ([contracts/ui-contract.md](./contracts/ui-contract.md)).

## Manual browser checks (constitution principle 6)

### Pasted text (User Story 1)

1. Side panel → Add recipe → Text. Paste a recipe. Tap outside the sheet. Reopen Text: the text is there.
2. Reload the page. Reopen Text: the text is there.
3. Go to another page (Cart). Open Add recipe → Text from a notebook page: the same text is there.
4. On a phone, switch to another app for a minute, come back, and reopen: the text is there.
5. Submit. On the draft, press Back: the text is there. Submit again, then Discard: reopening Text shows an empty field.
6. Paste again, submit, and Save: reopening Text shows an empty field.
7. Paste again and close the tab. Open the app in a new tab: the field is empty.
8. Paste again and sign out. Sign in as another dev account in the same tab: the field is empty.
9. In DevTools → Application → Session Storage, the `melos.capture.text` key exists only while there is text. Nothing is sent over the network until Submit.

### Notebook choice (User Story 2)

1. Outside any kitchen, side panel → Add recipe → Text. The picker lists personal notebooks (including the shared one) marked "Personal", then a divider, then the kitchen's notebooks marked with the kitchen's name. The default personal notebook is preselected.
2. Type the kitchen's name in the picker search: its notebooks are listed.
3. Archive the kitchen (owner account) and reopen: its notebooks are gone.
4. On a kitchen's page, side panel → Add recipe: that kitchen's group is first, and your own notebook there (or "My own notebook (new)") is preselected.
5. Open a personal notebook and use its add card: no picker. The sheet title is that notebook's name.
6. Open a kitchen page and use its add card: the picker lists only that kitchen's notebooks.
