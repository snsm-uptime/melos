# Data Model: Match Captured Ingredient Names to the Notebook's Catalog

No table, column or migration is added. The catalog is read-only here (spec FR-006, FR-013). The entities below live in memory during a capture and in the browser draft.

## Catalog entry (existing, read-only)

- **Source**: `ingredient` table, through `IngredientCatalog.names_for_notebook(notebook_id)` (spec 056).
- **Fields used**: `name`, a normalized string (lower-case, singular) unique per notebook.
- **Rules**: Read once per capture. Never written by matching.

## IngredientLine (domain, extended)

| Field | Type | Source | Notes |
|---|---|---|---|
| `name` | str | Extraction (`name`) | The assistant's name, lower-case singular. Kept for undo. |
| `text_name` | str | Extraction (`text_name`, new), set after the check | The name as written in the pasted text. Falls back to the assistant's `name` when the model omits it. Undo returns the line to this name. |
| `catalog_match` | str or None | Extraction (`catalog_match`, new) | The catalog entry the model proposes. None when it proposes none. |
| `preparation`, `quantity`, `unit`, `size`, `vague`, `note` | as today | Extraction | Unchanged. |

Validation: `text_name` and `catalog_match` are optional. A missing `text_name` means no change can be listed for the line; the line still gets a match from the rule only if `name` normalizes to the proposal (see research §3). Rule input is `name` when `text_name` is absent.

## LineMatch (domain, new)

| Field | Type | Meaning |
|---|---|---|
| `kind` | `"matched"` or `"new"` | Label on the line (FR-001). |
| `entry` | str or None | Catalog entry when `kind` is `"matched"`. |

Invariant: `entry` is set exactly when `kind == "matched"`, and it is an entry of the notebook's catalog.

## NameChange (domain, new)

| Field | Type | Meaning |
|---|---|---|
| `line` | int | Index of the ingredient line in the draft. |
| `from` | str | Text name (`text_name`, or `name` when absent). |
| `to` | str | Catalog entry (`LineMatch.entry`). |

Invariant: a change exists only for a `matched` line whose displayed name differs from its entry under case-only comparison, in which case no change is listed (spec edge case: "Onion" and "onion").

## DraftRecipe (domain, extended)

- Adds `matches: tuple[LineMatch, ...]` (one per line, in line order) and `changes: tuple[NameChange, ...]`.
- Each matched line's displayed `name` is its catalog entry.

## Member choices (browser only, captureStore)

| Field | Type | Meaning |
|---|---|---|
| `lines[i].match` | `LineMatch` | Current label; starts from the server result. |
| `lines[i].undone` | bool | True after the member undoes that line's change; the line shows "new ingredient" with `name`. |
| `lines[i].chosen` | str or None | Catalog entry the member picked from the notebook's catalog, or `"new"` for "new ingredient". |

Not sent to the api in this feature. Discarded with the draft.

## State transitions (per line)

```text
server match: matched(E) ──undo──▶ new (shows name)
server match: matched(E) ──choose other entry E2──▶ matched(E2)
server match: matched(E) ──choose "new"──▶ new (shows name)
server match: new ──choose entry E2──▶ matched(E2)
```

Each change is undone or chosen per line; no transition touches other lines (spec US2 scenario 4).
