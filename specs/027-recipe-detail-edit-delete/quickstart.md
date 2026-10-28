# Quickstart: validate S-027 end to end

Prerequisites: the stack runs through Compose (`./scripts/compose-up.sh`); a signed-in user with an alias; one kitchen with another member. Use invented data only.

## 1. Automated checks

```sh
# api: pure + application tests (no database), then integration in the Compose test overlay
cd api && uv run pytest -q tests/test_recipe_write_domain.py tests/test_recipe_manage_application.py
# integration: see AGENTS.md for the Compose test overlay command; run tests/test_recipe_manage_integration.py
uv run ruff check .
# ui
cd ui && npm test && npm run lint && npm run typecheck
```
Expected: all new tests pass; baseline failures noted in `specs/021-recipe-lists/notes.md` are unchanged.

## 2. Browser walk (constitution §6)

1. Capture and save "Tomato rice" (rice, tomato, salt to taste; 3 steps) into a personal notebook. Open the notebook; tap the card. **Expect** the detail with all lines and steps (US1).
2. Tap **Edit**. Change "1 cup" to "2 cups", add "onions" (a notebook that has "onion" in its catalog), delete one step, **Save**. **Expect** "onions → onion" shown with Undo before saving; after Save, the detail shows the new content and the list card still reads the same title (US2, AC3.4-style).
3. Edit again: clear the title and **Save**. **Expect** a plain message naming the title, nothing saved, other edits kept.
4. Open the same recipe in two tabs as two members of a kitchen notebook. Save in tab A, then save in tab B. **Expect** tab B is told the recipe changed and keeps its edits (US2-8, SC-007).
5. As a member of an archived kitchen (or a user with read access only), open the recipe. **Expect** no Edit or Delete.
6. Tap **Delete**, choose **Cancel**. **Expect** nothing changes. Tap **Delete** again and confirm. **Expect** the list without the recipe; reopen the old link, **Expect** "That recipe isn't available." (US3).
7. With a copy of the recipe in another notebook (insert it through the test fixture), delete the original. **Expect** the copy is unchanged (AC3.2).

## 3. Data checks (psql in the test database)

- After a delete: no `recipe`, `recipe_ingredient`, `step` or `source` row for the id; the notebook's `ingredient` names are unchanged.
- After an edit: `author_id`, `notebook_id`, `source_id`, `created_at` unchanged; `updated_at` newer; positions run 0..n-1.
