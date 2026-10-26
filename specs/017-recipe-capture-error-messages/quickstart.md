# Quickstart: Clear Recipe Capture Error Messages

**Date**: 2026-10-25 | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/capture-messages.md](./contracts/capture-messages.md)

A validation guide: run it after the phases in plan.md are done. It does not restate the implementation.

## Prerequisites

- Docker with Compose v2, `uv`, Node/`npm`.
- `.env` filled in from `.env.example` (a valid `GEMINI_API_KEY` for the browser steps; the test overlay uses the fake extractor).
- Data directory created: `mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata"`.
- A signed-in member with a notebook (spec 056).

## 1. Automated checks

```bash
# api, in Compose (canonical)
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api

# ui
cd ui && npm test && npm run lint && npm run typecheck
```

Expected: all pass. The new cases are the domain problem kinds, the application pass-through, the adapter reason enum, the integration codes, and the sheet messages.

## 2. Browser walkthrough

Start the stack with `./scripts/compose-up.sh`, open <http://localhost:3000>, go to the Notebook tab, open the add-recipe call to action, choose Text, paste a text, and submit. After each case, confirm the text is still in the box (SC-004).

| # | Paste | Expected message (contract wording) | Check |
|---|-------|-------------------------------------|-------|
| 1 | A recipe with ingredients and steps, no title | "Add a title for the recipe." | Title named; text kept |
| 2 | Ingredients with a title, no steps | "Add the steps of the recipe." | Steps named; text kept |
| 3 | No title and no steps | Both sentences, title first | Every missing part named (US1 AS3) |
| 4 | Full recipe, with the line "1/4 butter" (no unit) | "Add a unit to butter, such as grams, cups or units." | Ingredient named (FR-012) |
| 5 | Full recipe, with "salt" (no quantity and no unit) | "Add a quantity to salt." and "Add a unit to salt…" | Both kinds named for one ingredient |
| 6 | "What's the weather tomorrow?" | "That doesn't look like a recipe. It reads as a question or request. Clarify the text: paste the full recipe…" | Reason from fixed wording; no assistant text |
| 7 | "What's the total grams of a bar of butter?" | "That reads as a question about butter, not a recipe…" | Question names its ingredient (FR-013) |
| 8 | A short story about a holiday | "…It reads as a story or article…" | Story reason |
| 9 | Two complete recipes, one after the other | "Only one recipe can be added at a time. Paste them one by one." | Multi-recipe wording |
| 10 | Any refusal above | Message contains no quoted assistant sentence, code or stack; the only assistant-derived text is the ingredient name | FR-007, SC-003 |
| 11 | An ingredient name with digits or symbols, for example a line the model names "2 x butter!" | The ingredient part reads "this ingredient" | Name cleaning fallback |

Case 6 and 7 depend on the model's choice; confirm the reason with the AI evaluation fixtures (`api/tests/fixtures/ai_eval/`) before judging the wording.

## 3. Unreadable answer

Make the assistant's answer unreadable in a test run (the fake extractor returns `InvalidOutput`). Expected: "The app could not build a recipe from this text. Try again, or shorten the text to one recipe." Text kept. No technical detail.

## 4. Unchanged messages (FR-011)

- A text over `RECIPE_TEXT_MAX_CHARS` shows the spec 016 limit message, and the length message appears before any missing-part message.
- Stop the assistant service or hit its usage limit: the availability and limit messages match spec 016.

## Done when

- Section 1 is green.
- Section 2 rows 1 to 9 match, with the text kept in the box each time.
- Section 3 and 4 match.
- Each message string exists once in `ui/lib/i18n/capture.ts`.
