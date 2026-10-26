# Contract: Capture refusal codes and messages

**Date**: 2026-10-25 | **Plan**: [../plan.md](../plan.md) | **Builds on**: [spec 016 capture-api](../../016-capture-recipe-text/contracts/capture-api.md), [capture-ui](../../016-capture-recipe-text/contracts/capture-ui.md)

This file is the delta for spec 016's capture contract. Every other code in spec 016 keeps its status and wording.

## HTTP (api, `POST /notebooks/{notebook_id}/captures/text`, through the BFF)

All refusals keep the body `{ "detail": string, "code": string }`. Extra list fields are added where noted. `detail` is a fixed token or empty, never assistant prose.

| Code | Status | When | Body additions | Changed? |
|------|--------|------|----------------|----------|
| `not_a_recipe` | 422 | Text is not a recipe | `detail` = reason enum value (`question_or_request` \| `not_food` \| `story_or_article`); `ingredient` = cleaned name or `null` | Yes: detail was free text |
| `one_recipe_at_a_time` | 422 | Text holds more than one recipe | none | Wording only (ui) |
| `draft_incomplete` | 422 | Title and/or steps missing | `missing`: `["title"]`, `["steps"]` or both | New |
| `ingredient_line_problem` | 422 | Only ingredient-line problems | `line_problems`: list of `{ "name": string \| null, "kind": "quantity_missing" \| "unit_missing" \| "unit_not_recognized" }`, one entry per problem; a line with neither quantity nor unit gives two entries | New |
| `ai_invalid_output` | 422 | Answer cannot be turned into a recipe for any other reason | none | Wording only (ui) |
| `text_empty` | 422 | Empty after trimming | none | Unchanged |
| `text_too_long` | 422 | Over `RECIPE_TEXT_MAX_CHARS` | `detail` has the limit | Unchanged |
| `ai_unavailable`, `ai_limit_reached`, `ai_misconfigured` | 503, 429, 503 | Service states | none | Unchanged (spec 016 FR-011) |
| `kitchen_archived` | 409 | Archived kitchen | none | Unchanged |
| `notebook_not_found` | 404 | No access | none | Unchanged |

`name` is the cleaned ingredient name (plan.md Design Decision 5); `null` when the cleaning check fails, and the ui then writes "this ingredient". The ui shows at most five line sentences, then "and more ingredients need a change."

If both `missing` and `line_problems` apply, the api returns `draft_incomplete` with both lists filled. The ui shows the `missing` sentence(s) first, then the line-problem sentence(s).

## Fixed English messages (ui, `ui/lib/i18n/capture.ts`)

Each row is one string in the file. Keys are suggestions; the file is the source of truth. Wording follows the spec; "Your text is kept" style is avoided because the text is already visible in the box.

| Trigger | Message |
|---------|---------|
| `not_a_recipe`, `question_or_request`, no ingredient | That doesn't look like a recipe. It reads as a question or request. Clarify the text: paste the full recipe, with its ingredients and steps. |
| `not_a_recipe`, `question_or_request`, `ingredient` = {name} | That reads as a question about {name}, not a recipe. Clarify the text: paste the full recipe, with the amount and unit of {name} and its steps. |
| `not_a_recipe`, `question_or_request`, `ingredient` = null | Same as the row above without the name: "…the amount and unit of this ingredient…". |
| `not_a_recipe`, `not_food` | That doesn't look like a recipe. It is not about food. Paste the full recipe, with its ingredients and steps. |
| `not_a_recipe`, `story_or_article` | That doesn't look like a recipe. It reads as a story or article. Paste only the recipe, with its ingredients and steps. |
| `one_recipe_at_a_time` | Only one recipe can be added at a time. Paste them one by one. |
| `draft_incomplete`, `title` | Add a title for the recipe. |
| `draft_incomplete`, `steps` | Add the steps of the recipe. |
| `ingredient_line_problem`, `quantity_missing`, `name` = {name} | Add a quantity to {name}. |
| `ingredient_line_problem`, `unit_missing`, `name` = {name} | Add a unit to {name}, such as grams, cups or units. |
| `ingredient_line_problem`, `unit_not_recognized`, `name` = {name} | {name} uses a unit the app does not know. Use a common unit, such as grams, cups or spoons. |

With `name` = null, the same sentences use "this ingredient" in place of {name}. "1/4 butter" with no unit gives "Add a unit to butter, such as grams, cups or units."
| `ai_invalid_output` | The app could not build a recipe from this text. Try again, or shorten the text to one recipe. |
| `text_too_long` | That text is too long. Paste up to {limit} characters. (spec 016, unchanged) |
| `ai_unavailable`, `ai_limit_reached`, `ai_misconfigured`, `kitchen_archived`, `notebook_not_found` | Spec 016 wording, unchanged. |

Units named in the messages (grams, cups, spoons) are examples; the unit list comes from the domain. Check them against the unit list before merging.

## Reason values sent by the assistant (adapter)

| Value | Used when |
|-------|-----------|
| `question_or_request` | The text asks a question or gives an instruction, not a recipe |
| `not_food` | The text is about something other than food or cooking |
| `story_or_article` | The text is prose (a story, article, list of links), not a recipe |

Any other value, or a missing value, is treated as an unreadable answer (`ai_invalid_output`).

## Rules for reviewers

- A message must name the reason and, where the member can act, one next step (SC-001).
- No message interpolates assistant text, a title or a service error (FR-007, SC-003). The only interpolated assistant-derived value is an ingredient name, and only after `clean_display_name` accepts it.
- Each string appears once in `ui/lib/i18n/capture.ts` (FR-010).
