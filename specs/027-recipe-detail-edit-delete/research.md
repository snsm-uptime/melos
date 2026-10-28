# Research: Recipe Detail, Edit and Delete (S-027)

No `NEEDS CLARIFICATION` remained after the 2026-10-28 clarify session. These are the design decisions the plan rests on.

## R1. Version token for the stale-save check (FR-011)

- **Decision**: Use `recipe.updated_at` as the version. The detail route returns it as `version`; the update route requires it back. The update runs `SELECT ... FOR UPDATE` on the recipe row, compares, and writes only on a match; a mismatch raises `StaleRecipeError` (409 `recipe_changed`). A missing row raises not-found (404).
- **Rationale**: The column exists, is set on insert, and needs no migration. Locking the row serializes two concurrent saves, so the second sees the first's new `updated_at`.
- **Alternatives**: an integer `version` column (needs a migration, no gain here); ETag/If-Match headers (the BFF would have to forward them; a body field is simpler and matches how spec 020 passes `save_key`).

## R2. Name matching in edit (FR-009, clarification Q1 = matched, undoable)

- **Decision**: A read-only route `POST /recipes/{id}/name-matches` takes the typed names and returns, per name, the catalog entry it matches or `null`. The pure rule `propose_entry(name, catalog)` in `domain/ingredient_catalog.py` picks the first catalog entry for which `match_line(...)` confirms (same normalized name, singular forms included). The ui calls it when a member leaves a name field, shows the change with the existing `NameChangeNotice` and its undo, and sends the final names on save. The update route then only resolves case/spacing with `resolve_line_names` and adds the new names, exactly as spec 020 does for a confirmed draft.
- **Rationale**: Reuses the S-018 rule without a model call and without copying the singularization rules into TypeScript. Undo is a ui state; the server trusts the confirmed names, as it does at first save.
- **Alternatives**: match in the ui with a TypeScript copy of `singular_forms` (two copies of one rule drift); match inside the update route and return the changes after the fact (the member could not undo before saving, contradicting the clarification).

## R3. Write permission (FR-005, FR-006)

- **Decision**: A pure `can_write_recipes(access, kitchen_is_archived)` in `domain/notebook.py` built on the existing `NotebookView.access`: personal owner or member → true; kitchen member → true unless the kitchen is archived. Every use case loads `facts_for(actor, recipe.notebook_id)`; no access → 404 `recipe_not_found`; access but no write → 403 `recipe_read_only`. The detail response carries `can_write` so the ui can hide the actions.
- **Rationale**: One rule, one place, enforced in `application/` (constitution §3) and reused later by S-022/S-048.
- **Alternatives**: return 409 `kitchen_archived` as spec 020 does (the member of an archived kitchen can still read, so 403 read-only is the clearer answer for edit/delete).

## R4. Delete and the source record (FR-014, clarification Q2 = delete with recipe)

- **Decision**: In one transaction, read `source_id`, delete the recipe row (lines and steps cascade), then delete the source row. A repeated delete finds no recipe and returns 404 `recipe_not_found`; the ui treats a 404 on delete as done and returns to the list (FR-017).
- **Rationale**: Each save creates its own source row (spec 020), so no other recipe shares it. `recipe.source_id` is `ON DELETE SET NULL`, so the order is also safe if a source were ever shared.
- **Alternatives**: keep the pasted text (privacy cost, rejected in clarify); a soft delete (adds a state every list and later story must filter).

## R5. Replacing lines and steps (FR-007, FR-010)

- **Decision**: In the same locked transaction, delete the recipe's `recipe_ingredient` and `step` rows, flush, insert the new ones with positions 0..n-1, update title, servings, `servings_estimated` and `updated_at`. Author, notebook, source, `save_key` and `created_at` are not touched. New catalog names go through `IngredientCatalog.add_names`; nothing is removed from the catalog.
- **Rationale**: Positions are unique per recipe; delete-then-insert avoids transient collisions and keeps reorder trivial. No ingredient or step ids are exposed, so nothing depends on row identity.
- **Alternatives**: diff and update rows in place (more code, no user-visible gain).

## R6. Validation and error mapping (FR-008, FR-019)

- **Decision**: Run `check_edited_draft` on the incoming content, then the 100-line/100-step limits, exactly as `SaveRecipeDraft`. In `api/routes/recipes.py` the update route reuses `_problems` and `_error`, so `draft_incomplete`, `ingredient_line_problem` and `invalid_recipe` keep their spec 020 shapes and the ui reuses its message mapping.
- **Rationale**: One rule set for first save and edit (spec FR-008) and one error vocabulary for the ui.

## R7. Source on the detail (FR-003)

- **Decision**: The detail returns `source: {type, url}` or `null`, never `raw_text`. Today every source is `type=text` with no url (URL capture is S-026), so no link shows yet; the ui renders it when `url` is set.
- **Rationale**: The pasted text can be long and private and is not part of the recipe the member reads.

## R8. Where Back and the post-save landing go (FR-004, FR-011a)

- **Decision**: Cards link to `/recipes/{id}?from=<path>`. `from` is accepted only if it starts with `/notebooks/` or `/kitchens/`; otherwise Back goes to `/notebooks/{recipe.notebook_id}`. Edit opens `/recipes/{id}/edit?from=…`; after a save it goes to `/recipes/{id}?from=…`; after a delete it goes to `from`.
- **Rationale**: The same recipe is reachable from a notebook list and from a kitchen list, so the list cannot be derived from the recipe alone. The allow-list prevents an open redirect.

## R9. Edit form and the draft components (FR-007, FR-012)

- **Decision**: New `RecipeEdit` form with its own local state. Reuse `IngredientLineRow`, `RowControls`, `NameChangeNotice` and `LeaveDraftGuard` after checking each is free of `captureStore`; where one is not, pass its data and callbacks through props instead of copying it.
- **Rationale**: The draft editor is tied to the capture flow and its store (a reload clears it); an edit must start from the stored recipe. Reusing the rows keeps the two screens looking the same.

## R10. Future references (FR-016)

- **Decision**: `DeleteRecipe` is the single place a recipe is removed. It does nothing for cart, embeddings or chat citations because those tables do not exist. S-022, S-019 and S-030 each add their cleanup there (or by `ON DELETE CASCADE` on their own foreign key to `recipe.id`), and `UpdateRecipe` is the single place S-019 will re-embed.
- **Rationale**: Satisfies "no reference of its own outlives the recipe" with no speculative code.
