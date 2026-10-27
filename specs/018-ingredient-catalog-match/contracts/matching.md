# Contract: Ingredient Matching (S-018)

Describes the changes to the S-016 capture contract. Everything not listed here is unchanged.

## 1. Extraction result (model → api)

Each `ingredient_lines[]` entry gains two optional fields. The response schema marks neither as required, so an older response without them still validates and yields lines with no proposal.

| Field | Type | Required | Rule |
|---|---|---|---|
| `text_name` | string | no | The ingredient's name as written in the pasted text, in the text's language. |
| `catalog_match` | string or null | no | One entry of the `<<<CATALOG_NAMES … CATALOG_NAMES>>>` block, spelled exactly as in that block, or null when no entry fits. |

Prompt change: the system instruction states both fields. The catalog block and the text block remain data (spec 016 security rule).

Invalid proposals are not errors: a `catalog_match` that is not in the catalog block is ignored by the rule (treated as no proposal) and does not refuse the draft.

## 2. Capture response (api → ui)

`POST /notebooks/{notebook_id}/captures/text` returns the S-016 draft shape with two additions. Existing fields keep their meaning; `ingredient_lines[].name` is the displayed name (the catalog entry for a matched line).

```json
{
  "catalog": ["flour", "onion"],
  "draft": {
    "...": "unchanged S-016 fields",
    "ingredient_lines": [
      {
        "name": "onion",
        "text_name": "onions",
        "quantity": 2,
        "unit": "unit",
        "size": "large",
        "preparation": null,
        "vague": false,
        "match": { "kind": "matched", "entry": "onion" }
      },
      {
        "name": "flour",
        "text_name": "flour",
        "quantity": 200,
        "unit": "g",
        "size": null,
        "preparation": null,
        "vague": false,
        "match": { "kind": "new", "entry": null }
      }
    ],
    "changes": [
      { "line": 0, "from": "onions", "to": "onion" }
    ]
  }
}
```

Rules:
- `catalog` is present at the top level: the capture notebook's catalog entries, sorted. The match control (FR-005) lists them. It is read by the capture, not by a new route.
- `text_name` is present on every line: the name as the text writes it, or the assistant's name when the text gives none. Undo returns a line to this name (FR-004).
- `match` is present on every line; `kind` is `"matched"` (with `entry`) or `"new"` (with `entry: null`).
- `changes` is present (possibly empty). It lists one item per matched line whose `from` (`text_name`, or `name` when absent) and `to` (the entry) differ after case folding and space collapsing. A singular-form difference ("onions" → "onion") is listed; a case-only difference ("Onion" → "onion") is not.
- No new HTTP status codes. Matching failures are not errors: the line is "new".
- Errors are unchanged from S-016 and S-017.

## 3. UI behaviour (ui)

| Element | Behaviour |
|---|---|
| Ingredient line label | Shows "matched: <entry>" or "new ingredient" (English). Every line shows one label (FR-001). |
| Change list | Above the ingredient table when `changes` is non-empty. Each item reads "<from> → <to>" with an Undo action. |
| Undo | Sets the line to `new` with its `name` before the match; removes only that item from the list (FR-004). |
| Change match | Each line has a control that lists the notebook's catalog entries and "new ingredient". Choosing an entry shows "matched: <entry>"; choosing "new ingredient" shows that label; the change list updates at once (FR-005). |
| Empty catalog | No change list; every line "new ingredient" (FR-007). |

Labels live in `ui/lib/i18n/capture.ts`. English only; Spanish comes with the account-language story.

## 4. Domain rule (api internal, for the tests)

```text
normalize_name(s)   -> trim, NFKD minus combining marks, casefold, collapse spaces
singular_forms(n)   -> {n} ∪ singular candidates (fixed EN and ES rules)
match_line(line, catalog, proposal):
    if proposal is None or proposal not in catalog: new
    key = normalize_name(line.text_name or line.name)
    if key ∈ singular_forms(normalize_name(proposal)) or normalize_name(proposal) ∈ singular_forms(key):
        matched(proposal)
    else: new
```

Duplicates: two catalog entries that normalize equal; the proposal wins if it is one of them. Otherwise the line is new (FR-008).
