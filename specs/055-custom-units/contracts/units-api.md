# Contract: units in the recipe routes

All routes need a signed-in person with an alias. The ui reaches them through the same-origin BFF.

## `GET /recipe-vocabulary` (changed)

Now per person. `units` holds the ten defaults in today's order, then the caller's other units, sorted.

```json
{ "units": ["g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit", "lata"],
  "sizes": ["small", "medium", "large"],
  "max_text_chars": 10000 }
```

## `POST /recipe-vocabulary/unit-check` (new)

Body: `{ "word": "Latas" }`, at most 200 characters. Stores nothing. 200 in every case below.

| Answer | When |
|--------|------|
| `{ "outcome": "known", "unit": "lata" }` | The word is, or maps to, a unit the caller has. `unit` is the value to put on the line |
| `{ "outcome": "new", "unit": "lata" }` | The word can be offered. `unit` is its normalized form. Ask the question |
| `{ "outcome": "not_a_unit", "unit": null }` | Too long, empty, only digits or symbols, or close to two units |

## `POST /notebooks/{id}/captures/text` (changed)

A successful answer gains `draft.unknown_units`:

```json
{ "unknown_units": [{ "word": "lata", "lines": [0, 3] }] }
```

- Each listed line has `unit` set to `word`, so "latas" on line 3 reads "lata".
- The list is empty when every word is known.
- A word that can't be offered keeps today's 422 `ingredient_line_problem`.
- Every other outcome is unchanged.

## `POST /recipes` and `PUT /recipes/{id}` (changed)

Both bodies gain `keep_units: list[str]`, default `[]`, at most one entry per allowed line count.

| Input | Result |
|-------|--------|
| A line's unit is available to the caller | Saved as before |
| A line's unit is in `keep_units` and can be offered | Saved, and the word joins the caller's list |
| On update only, a line's unit is already on the stored recipe | Saved, and the caller's list doesn't change |
| Anything else | The existing 422 with `line_problems` kind `unit_not_recognized`. Nothing is stored |
| A `keep_units` word that no saved line uses | Ignored |
| A `keep_units` word already covered | Ignored |
| A repeated Save with the same key | Returns the stored recipe and adds nothing |

The word joins in the transaction that writes the recipe, after every check has passed.

## Read routes (unchanged shape)

`unit` on a recipe line, and on a shopping list amount, is any string. The shopping list's `kind` gains one value:

```json
{ "name": "frijoles", "kind": "custom", "size": null,
  "amounts": [{ "quantity": "3", "unit": "lata" }], "recipes": [] }
```

- `custom` quantities are whole numbers, rounded up per unit after the sum.
- Amounts in different custom units of one ingredient share one line.
- A mass, volume or count amount of the same ingredient stays on its own line.

## `POST /kitchens/{id}/shopping-list/items` (unchanged)

Hand items keep the ten units. Any other unit is the existing refusal (FR-016).

## Service with no route: `RemoveUserFromUnitsService`

Module: `api/application/units.py`. For S-054 to call, alongside `PassOwnedNotebooksService`.

```python
RemoveUserFromUnitsCommand(user_id: UUID)
RemoveUserFromUnitsService(units: UnitRepository).execute(command) -> None
```

**The caller must** call it in the transaction that deletes the user row and commit once after that row is gone. It can run before or after the row is deleted, since nothing references it.

**The service promises** to:

- Never commit or roll back.
- Take row locks in name order.
- Do nothing on a second run.
- Delete a non-default row left with no references.
- Never touch a recipe line.
