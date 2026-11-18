# Tasks: Backlog cleanup against what is built

**Input**: Design documents from `specs/077-backlog-cleanup/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/change-list.md, quickstart.md

**Tests**: No test tasks are requested. Validation is the quickstart checks and the existing
`ui/lib/featureInventory.test.ts`.

**Organization**: Tasks are grouped by user story. Almost every task edits
`dev/docs/backlog.yaml` or `dev/docs/backlog-done.yaml`, so few run in parallel.

**Rules for every edit** (from spec and data-model):
- Pending statuses are only `backlog`, `in_design`, `in_progress`, `verification`; done entries have `status: done`.
- Entries moved to done go to the end of `dev/docs/backlog-done.yaml`, unchanged except `status: done` and a `verification` note "Recorded by S-077 on 2026-11-18 from main (e4b2bb8)" that lists open tasks by ID (FR-002).
- No story is deleted (FR-012). Done entries are edited only to correct a note that contradicts the code or to record open checks, and the note says so (FR-009).
- Do not edit `specs/` (other than this folder), `dev/memory/`, or history (research R6).
- Titles and sources of added entries come from the spec folder's `spec.md`, not invented (contract).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Create and switch to branch `077-backlog-cleanup` from `main` (research R8); confirm `git status` is clean apart from `specs/077-backlog-cleanup/` and `.specify/feature.json`.
- [X] T002 Add story S-077 to `dev/docs/backlog.yaml` under a new "Housekeeping" section at the top of `stories:`: title "Backlog cleanup against what is built", epic Platform, priority should, status `in_progress`, source "owner request 2026-11-18; specs/077-backlog-cleanup".

---

## Phase 2: Foundational (blocks all stories)

**Purpose**: Re-verify the evidence and write the change list the owner reviews (FR-001, FR-013).

- [X] T003 For each row of research R5 and the spec's audit table, re-run the three checks of research R4 against `main`: `git log --oneline main | grep -E '<spec number>|S-<id>'`; `grep -ciE '^\s*- \[x\]'` and `grep -cE '^\s*- \[ \]'` on `specs/<NNN>-*/tasks.md`, listing open task IDs; and a code search under `api/` and `ui/` for stories with no spec folder (S-028, S-029, S-030, S-031, S-042, S-044, S-045, S-054, S-068). Note any finding that differs from research R5.
- [X] T004 For each open task found in T003 on a story about to move to done, classify it as a check (walk, timing, review, PRD, calibration, tests-only) or unbuilt scope. Expected unbuilt scope: S-041 T065 (picture pop-up, FR-027 of spec 041) and spec 073 T031–T040; anything else found is added to "Owner decisions".
- [X] T005 Write `specs/077-backlog-cleanup/notes.md` in the format of `contracts/change-list.md`: one row per story touched with Action (`move to done`, `split`, `renumber`, `add`, `status`, `narrow`, `note fix`), Before, After, Evidence; then "Owner decisions" (S-034, S-041 T065, approval of S-078, S-079, S-080) and "Follow-ups not done here" (PRD follow-ups found, a possible backlog lint).

**Checkpoint**: the change list is complete; the story phases apply it.

---

## Phase 3: User Story 2 - Every story number points to one story (Priority: P1)

Done before US1 so entries moved in US1 are not confused with the duplicates.

**Goal**: Each ID appears once across both files (FR-005, FR-006).

**Independent Test**: quickstart section 1 reports no duplicates; `grep -oE 'S-[0-9]{3}' ui/lib/featureInventory.ts` IDs all exist.

- [X] T006 [US2] In `dev/docs/backlog-done.yaml`, change the entry "S-069 Refused site registry" (source `specs/067-refused-site-registry`) to `id: S-078`; append to its notes: "Renumbered from S-069 by S-077 on 2026-11-18: S-069 is the quick add story (spec 069). Its spec folder is 067." Leave the quick add entry as S-069.
- [X] T007 [US2] In `dev/docs/backlog-done.yaml`, append to the S-067 "Recipe image" notes: "No spec folder of its own; specs/067-refused-site-registry belongs to S-078 (noted by S-077, 2026-11-18)."
- [X] T008 [US2] In `dev/docs/backlog.yaml`, change the later entry "S-066 Render recipe pages that build their content only in the browser" to `id: S-079`; append to its notes: "Renumbered from S-066 by S-077 on 2026-11-18: S-066 is table sort and search (spec 066). dev/memory logs cite it as S-066."
- [X] T009 [P] [US2] In `ui/lib/featureInventory.ts` line 113, change the link-capture feature's `stories: ["S-026", "S-069"]` to `["S-026", "S-078"]`; leave the quick-add feature (line 168, `["S-069"]`) unchanged. Then run `cd ui && npx vitest run lib/featureInventory.test.ts` and confirm it passes.
- [X] T010 [US2] `grep -rn 'S-069\|S-066' AGENTS.md README.md dev/docs/*.md ui/lib api --include='*.md' --include='*.ts' --include='*.py'` and update any reference that means the registry or the page-rendering story; record what was found in `notes.md`.

**Checkpoint**: no duplicate IDs.

---

## Phase 4: User Story 1 - The pending backlog lists only work not yet built (Priority: P1) 🎯 MVP

**Goal**: No entry in `dev/docs/backlog.yaml` has its full scope merged on `main` (FR-002, FR-003, FR-004).

**Independent Test**: quickstart section 4; S-041, S-066, S-072, S-075 are absent from `dev/docs/backlog.yaml` and present at the end of `dev/docs/backlog-done.yaml`.

- [X] T011 [US1] Move S-041 from `dev/docs/backlog.yaml` to the end of `dev/docs/backlog-done.yaml` with `status: done` and a verification note: merged #42 (120a09d); tasks 67/86; open checks T003, T035, T046, T053, T060, T062, T067, T069, T070, T077 (calibration, release gate), T079 (PRD) and the browser walk; unbuilt scope T065 (picture pop-up from the author's avatar), owner to decide whether it becomes its own story. Feature inventory: "Capture from a photo" already available.
- [X] T012 [US1] Move S-066 (table sort and search) to the end of `dev/docs/backlog-done.yaml` with `status: done`; verification note: tasks 25/25; walk 70/70 on 2026-11-04 (keep the existing notes); open: the owner's review of the Spanish strings in `ui/lib/i18n/table.ts`.
- [X] T013 [US1] Move S-072 to the end of `dev/docs/backlog-done.yaml` with `status: done`; verification note: on `main` in c99d0c6 (palette), e1806b8 (frosted top bar) and follow-ups (8aa92a5, b5a519e, d85f3e1); tasks 34/40; open T002, T017, T030, T035 (walks and measurements), T037 (performance), T040 (superseded by this move).
- [X] T014 [US1] Move S-075 to the end of `dev/docs/backlog-done.yaml` with `status: done`; verification note: merged #45 (5f42942); tasks 57/59; open T041 (browser walk), T042 (loop timings).
- [X] T015 [US1] Narrow S-047 in `dev/docs/backlog.yaml`: title "Kitchen recipe cards: author chips and author and notebook filters, ingredient filter, cart-frequency sort"; append to notes: "Cards with the recipe image or default pot are built (S-067, `ui/components/RecipeCard`). Not built: sort by `recipe.cart_add_count`, author and notebook filters (checked by S-077, 2026-11-18)." Adjust the listed parts to what T003 found.
- [X] T016 [US1] Narrow S-048 in `dev/docs/backlog.yaml`: title "Confirm ingredient name changes when copying a recipe into another notebook"; replace the note's build history with: "Copy from any readable notebook is built (S-069, spec 069) and copy to a co-member's default notebook with name matching (S-071). What is left: show each name change from the target catalog and let the person confirm before the copy is saved (AC3.3, AC3.4)."
- [X] T017 [US1] Confirm S-046 stays `backlog`; append to its notes: "The item PATCH route only sets `bought` (spec 070); quantity and name edits are not built (checked by S-077, 2026-11-18)."

**Checkpoint**: the MVP of this cleanup; a reader can no longer pick built work.

---

## Phase 5: User Story 3 - Built work with no entry gets one (Priority: P2)

**Goal**: Every spec folder maps to a story (FR-007, FR-004 split).

**Independent Test**: quickstart section 2 prints nothing.

- [X] T018 [US3] Append S-073 to the end of `dev/docs/backlog-done.yaml`: title from `specs/073-ingredient-translation-cron/spec.md` (the scheduled translation job), epic Capture, priority should, `status: done`, source "specs/073-ingredient-translation-cron"; notes: the `jobs` Compose service and removal of the `mcp` service; verification: merged #43 (bd5f790); tasks 46/58; the review list (US3, T031–T040) is split into S-080; open T055 (quickstart walk), T056 (EXPLAIN ANALYZE). Feature inventory already cites S-073 as available.
- [X] T019 [US3] Add S-080 to `dev/docs/backlog.yaml` in the Recipes or Platform section: title "Admin review of AI-made standard ingredient names (accept or reject a person's proposed value)", epic Platform, priority should, `status: in_design`, source "specs/073-ingredient-translation-cron (US3, FR-022)"; notes: "Split from S-073 by S-077 on 2026-11-18. Remaining tasks in specs/073-ingredient-translation-cron/tasks.md: T031–T040. S-074 places this list in its own section."
- [X] T020 [US3] Append S-076 to the end of `dev/docs/backlog-done.yaml` following the contract example in `contracts/change-list.md`; take the title and source from `specs/076-keep-pasted-recipe-text/spec.md`; verification: merged #46 (b9c4fe3) and #47 (3c9094e); tasks 19/20; open T018; feature inventory checked (update an entry if the spec adds a feature a person can use, FR-011).
- [X] T021 [US3] Set S-074 to `status: in_design` in `dev/docs/backlog.yaml`; replace "ID proposed, owner to confirm" in its source with "ID confirmed by S-077 on 2026-11-18" only if the owner approves in T029, else leave it.

**Checkpoint**: every spec folder has a story.

---

## Phase 6: User Story 4 - Pending entries describe the code as it is today (Priority: P3)

**Goal**: No note contradicts the code (FR-008, FR-009, FR-010).

**Independent Test**: reading each changed note against the code finds no contradiction.

- [X] T022 [P] [US4] In `dev/docs/backlog.yaml`, replace the first sentence of S-032's notes with: "The `mcp` Compose service was removed in spec 073 (#43); the story starts from no service." Keep the rest.
- [X] T023 [P] [US4] In `dev/docs/backlog.yaml`, append to S-034's notes: "Capture evaluation fixtures exist in `api/tests/fixtures/ai_eval` (specs 015, 026, 041, 043); the owner decides whether they meet this story (S-077, 2026-11-18)."
- [X] T024 [US4] In `dev/docs/backlog-done.yaml`, replace S-060's `verification: pending implementation` with a note naming the notebook list and tab code on `main` found in T003, and "Corrected by S-077 on 2026-11-18".
- [X] T025 [US4] In `dev/docs/backlog-done.yaml`, replace "Stays in_progress until T034 passes." in S-071's verification with "Open: T034 (quickstart browser walk) and T004 (owner answer on archived-kitchen co-members). Corrected by S-077 on 2026-11-18."
- [X] T026 [US4] In `dev/docs/backlog-done.yaml`, add a `verification` field to S-043: merged #40 (c0c1721); tasks 61/64; open T058 (browser walk), T059 (AI evaluation); T060 done by this entry. Recorded by S-077 on 2026-11-18.
- [X] T027 [US4] Rewrite the header comments of `dev/docs/backlog.yaml` (lines 1–33) and the section comments: keep the status definitions and spec-folder rule; replace the 2026-11-05 focus text with the current order (open shopping work S-046, S-068; then Recipes, Capture, Ask, MCP, Look and feel, Quality and deployment, Later); add "Cleaned up 2026-11-18 (S-077): built stories moved to done, duplicate IDs renumbered (S-069 → S-078, S-066 → S-079), spec 073 split (S-080). Next free number: one more than the highest across both files and specs/." Remove section headers left empty (for example "Next: open Platform work... waiting for its browser walk" if nothing remains under it).

**Checkpoint**: all stories complete.

---

## Phase 7: Polish & cross-cutting

- [X] T028 Run quickstart sections 1–3 from `specs/077-backlog-cleanup/quickstart.md`; record the output in `specs/077-backlog-cleanup/notes.md`. Fix and re-run until: no duplicates, no bad statuses, no spec folder without a story (spec 067 maps to S-078), inventory test passes.
- [X] T029 Ask the owner to review `specs/077-backlog-cleanup/notes.md` (FR-013), including the "Owner decisions" list; apply their answers.
- [X] T030 After approval, move S-077 to the end of `dev/docs/backlog-done.yaml` with `status: done` and a verification note (quickstart results, owner approval date; no feature inventory change beyond the S-078 reference).
- [X] T031 Commit in two commits on `077-backlog-cleanup`: (1) `docs(backlog): clean up backlog against main (S-077)` with both YAML files and `specs/077-backlog-cleanup/`; (2) `fix(ui): feature inventory cites S-078 for the refused site registry` with `ui/lib/featureInventory.ts`. Push and open a PR only if the owner asks.

---

## Dependencies & execution order

- Phase 1 → Phase 2 → US2 (Phase 3) → US1 (Phase 4) → US3 (Phase 5) → US4 (Phase 6) → Polish.
- US2 goes first because US1 and US3 append entries and cite new IDs (S-078, S-080).
- US3's T018–T019 (split) depend on T003's open-task list for spec 073.
- T021 depends on T029 (owner approval) for its source wording; its status change does not.
- T030 depends on T029.

## Parallel opportunities

- T009 (inventory file) runs alongside T006–T008 (YAML files).
- T022 and T023 touch different entries of the same file but no shared lines; run them together or in sequence.
- Everything else edits the same two YAML files and runs in order.

### Parallel example: User Story 2

```text
T006–T008 (dev/docs/backlog*.yaml)   |   T009 (ui/lib/featureInventory.ts + vitest)
```

## Implementation strategy

1. **MVP**: Phases 1–4 (setup, change list, unique IDs, built stories moved). After this the
   backlog no longer invites double work.
2. **Increment**: Phase 5 records unlisted work; Phase 6 corrects notes and the header.
3. **Close**: quickstart checks, owner review, commits.
