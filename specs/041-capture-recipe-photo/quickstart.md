# Quickstart: validating picture capture

Run from the worktree root. Use invented images only (spec 041 Assumptions, `api/tests/fixtures/ai_eval/pictures/`). Contracts: [capture-picture-api.md](contracts/capture-picture-api.md), [ports.md](contracts/ports.md), [disclaimers-preference.md](contracts/disclaimers-preference.md). Entities: [data-model.md](data-model.md).

## Prerequisites

- `./scripts/compose-up.sh -d` (UI on port 3180 for this worktree), the migration applied (`0022_user_disclaimers`).
- `GEMINI_API_KEY` and `GEMINI_CHAT_MODEL` set in `.env` for the real-assistant steps (5 to 8). Steps 1 to 4 and the automated suites need no key.
- Two accounts, one in a personal notebook and one in a kitchen notebook; a phone or a 360 px window for the phone steps.

## Automated

```sh
cd api && uv run pytest tests/test_recipe_picture_domain.py tests/test_recipe_capture_picture_application.py tests/test_user_disclaimers_migration.py
cd api && uv run pytest -m "not live"            # whole suite, no network
cd api && uv run ruff check .
cd ui && npm test -- PictureCaptureSheet pictureRules captureClient Toast SidePanelSettings
cd ui && npm run lint && npm run typecheck
```

Compose integration (route, membership, archived kitchen, save as `photo`, disclaimers round trip): the test overlay as for specs 026 and 063.

## Manual walk (browser, English then Spanish, 360 px and 1280 px)

1. **Picture option.** Open the add-recipe options from a notebook and from the quick add button: Picture is enabled, no "coming soon". It opens a sheet with a dashed inner border and "Upload file or drag and drop"; the submit control is disabled. (US1.1, FR-001, FR-002, FR-004)
2. **Refusals in the sheet.** Choose a PDF renamed `.jpg`, a text file, a damaged PNG (the fixture with a broken tail), and a file over 10 MB: each shows its message and nothing is sent (watch the network panel); a picture already chosen stays chosen. Drop two files: "Choose one picture at a time." (US2.1, US2.2, FR-016, FR-017, SC-003)
3. **HEIC and preview.** Choose the small HEIC fixture: it is accepted; in a browser that cannot show it, the sheet shows a file placeholder with the name. Choose a JPEG: a preview shows with a remove control. (FR-002, Edge Cases)
4. **Archived and removed.** With the kitchen archived (or the member removed) while the sheet is open, submit: the archived message or not found, and the call is not made (api log shows no assistant request). (FR-003)
5. **Happy path.** Submit the clear English page fixture: within 32 s a draft opens with title, servings, lines and steps matching the expected draft; the toast shows and is gone after 10 s; Save works and the recipe is in the notebook. Repeat with the Spanish page (accents and fractions: "½ cucharadita", "crème fraîche"). (US1.2 to US1.5, FR-009, SC-001, SC-002)
6. **Orientation and layout.** The sideways, upside-down, angled and two-column fixtures each give the expected draft. (FR-010, SC-001; if sideways or upside-down fails, see research R4 fallback)
7. **Partial draft.** Submit the fixture with title and ingredients but no steps: the draft opens, steps flagged, Save disabled; add a step and Save becomes available. The fixture with a line "butter" and no amount or unit: that line is flagged, Save disabled until fixed. No absent part is filled in. (US1.8, US1.9, FR-013a, SC-008)
8. **Refusals from the assistant.** The no-recipe fixture (a landscape): "That doesn't look like a recipe." with a reason. The two-recipe fixture: "Upload only one recipe at a time". The blurred fixture: "We couldn't read that recipe. Try a clearer photo." In each the picture is still chosen. Stop the assistant (wrong key): "Assistant misconfigured. Your picture is kept". (US2.3 to US2.6, FR-018, FR-019, FR-020, SC-004)
9. **Injection.** Submit the fixture whose printed text says "ignore previous instructions…": the draft equals the expected one. (US3.3, SC-006)
10. **Back and Discard.** From a draft press Back: the sheet has the same picture; press Discard from another draft: an empty sheet. Edit a draft and reload: the leave prompt appears. (US1.6, FR-014)
11. **Nothing stored.** After steps 5 to 10, query the database: no `recipe`, `source`, `recipe_ingredient` or `step` row exists for captures that were not saved; after a Save, one `source` row has `type='photo'`, `url` and `raw_text` null, and the recipe has no `preview_image_base64`. Search the api log for the image's base64 prefix or file name: none. (US3.1, US3.2, SC-005, FR-015)
12. **Disclaimers option.** In the account settings, turn "Show disclaimers" off: the next picture draft opens with no toast; turn it on: the toast returns. Sign out and in, and on a second browser: the choice holds. Text and link drafts never show the toast. (US1.10, US1.11, FR-013b, FR-013c, SC-009)
13. **Language.** Switch the account to Spanish: sheet, messages and toast are in Spanish; all of steps 2, 7, 8 and 12 use the Spanish strings. (FR-029, US2.7)

## Evaluation (manual, real assistant)

`cd api && uv run python scripts/eval_picture_capture.py` runs every fixture in `api/tests/fixtures/ai_eval/pictures/` and prints, per image, title, servings and lines against the expected draft and the overall rate. Pass: at least 90% correct (SC-001). Record the run in `specs/041-capture-recipe-photo/notes.md` as spec 026 did.

## Done when

All automated suites pass; steps 1 to 13 pass at both widths and both languages; the evaluation rate is recorded; the backlog entry moves to `done` with its verification note; the PRD updates listed in plan.md Follow-ups are made.
