# Research: Ingredients Table Layout (spec 074)

No NEEDS CLARIFICATION items remain: the owner decided rows 3, 5 and 8 of the spec's review table on 2026-11-08.

## R1. Join key between admin names and the standard table

- **Decision**: map each admin name with `discovery_key(name)` (domain, `api/domain/ingredient_catalog.py:212`) before matching `standard_ingredient.normalized_name`.
- **Rationale**: the standard table stores the discovery key, the shortest singular form of the normalized name (spec 073, R5). The admin query groups by the raw name, so a direct equality join would miss plurals and accents (for example "tomates" against "tomate").
- **Alternatives considered**: join on `normalize_name` (rejected: the standard table never stores it, so plurals would not match); store the key on the admin row in SQL (rejected: the singular rule lives in the domain, and principle 3 keeps rules out of SQL).
- **Consequence**: the mapping runs in the application layer, one pass over the admin rows. Its test is pure (domain).

## R2. Notebooks count

- **Decision**: `COUNT(DISTINCT ingredient.notebook_id)` over `ingredient` rows whose `name` equals the admin name.
- **Rationale**: `ingredient` has one row per `(notebook_id, name)` (`uq_ingredient_notebook_name`), so the distinct count is the number of notebooks holding the name. Spec 055 requires "whichever notebooks hold it".
- **Alternatives considered**: count from `recipe_ingredient` via `recipe.notebook_id` (rejected: an ingredient can be in a notebook before any recipe uses it).

## R3. Standard status and Source

- **Decision**: Standard status comes from `standard_ingredient.ai_checked_at` and the presence of an AI-made name:
  - **Checked**: `ai_checked_at` set and a name in some language with `source = 'ai'` or `'admin'`, or a valid check with no saved name.
  - **Pending**: `ai_checked_at` is null.
  - **Rejected**: `ai_checked_at` set and no name beyond the discovery name.
- **Source**: the `source` values of `standard_ingredient_name` for the row, shown as the set of values (for example "discovery, ai"). The constraint allows `discovery`, `ai` and `admin` (`ck_standard_ingredient_name_source`).
- **Rationale**: these are the states the spec 073 job writes (`mark_checked`, `save_translation`).
- **Alternatives considered**: a stored status column (rejected: a new column needs a migration and duplicates `ai_checked_at`).

## R4. Admin review list

- **Decision**: a separate admin section, listing `standard_ingredient_review` rows with `status = 'pending'`, newest first. Each item shows the replaced name, the proposed name, the language, who proposed it, and the date.
- **Rationale**: spec 073 FR-022 requires the list on the admin dashboard, and the owner decided it is a section, not a column (spec 074 row 8).
- **Alternatives considered**: a column on the Ingredients table (rejected by owner decision); a separate screen (out of scope: spec 073 excludes a UI beyond the admin dashboard list).
- **Open**: the accept and reject actions are spec 073 scope. This plan lists only; the buttons are not built here unless spec 073 has landed them.

## R5. Place picker order

- **Decision**: custom places first, then defaults, in the Place picker only (owner decision, row 3). Place tabs keep spec 070 FR-014 (defaults first).
- **Rationale**: the owner chose the picker order from the outline; the tabs follow their own rule.
- **Alternatives considered**: align the picker with the tabs (rejected by owner).

## R6. Language column

- **Decision**: always shown in the catalog view (owner decision, row 5).
- **Rationale**: the column already exists and is always shown in `CatalogManager.tsx`. The change is to keep it so, with no new rule.

## R7. Name shown in the table

- **Decision**: the main name follows the viewer's interface language when a name exists in it, else `ingredient.name` (spec 043 FR-007). Other names appear underneath.
- **Rationale**: the same rule already governs the shopping list; using it in the tables keeps the views consistent.
