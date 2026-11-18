# Change list: backlog cleanup (S-077)

Evidence base: `main` at e4b2bb8, checked 2026-11-18 on branch `077-backlog-cleanup`. Format:
[contracts/change-list.md](contracts/change-list.md). Stories not touched are not listed.

| Story | Action | Before | After | Evidence |
|-------|--------|--------|-------|----------|
| S-077 | add | none | pending `in_progress`, Housekeeping section; moves to done after owner review | this spec |
| S-069 (registry) | renumber | S-069, done | S-078, done; note "renumbered from S-069" | spec 067; clashes with S-069 quick add (spec 069), which keeps the number (owner) |
| S-067 | note fix | done; no folder note | done; note: no spec folder, spec 067 is S-078 | `specs/067-refused-site-registry` source line |
| S-066 (page rendering) | renumber | S-066, pending `backlog` | S-079, pending `backlog`; note "renumbered from S-066" | clashes with S-066 table sort (spec 066, merged), which keeps the number |
| S-041 | move to done | pending `in_progress` | done; open checks listed; T065 and its test T062 split to S-081 | merged #42 (120a09d); tasks 67/86 |
| S-066 (table sort) | move to done | pending `verification` | done; open: Spanish string review | tasks 25/25; walk 70/70 (cd0b5ba) |
| S-072 | move to done | pending `in_design` | done; open T002, T017, T030, T035, T037 | c99d0c6, e1806b8, 8aa92a5, b5a519e, d85f3e1; tasks 34/40 |
| S-075 | move to done | pending `verification` | done; open T041, T042 | merged #45 (5f42942); tasks 57/59 |
| S-047 | narrow | cards with image, author chips, filters, sort | author and notebook filters, ingredient filter, cart-frequency sort | `ui/components/RecipeCard` shows image or pot and the author chip; `RecipeList` has a text filter only; `recipe.cart_add_count` is counted (`api/application/ports.py`) and read only by the admin dashboard |
| S-048 | narrow | copy with name normalization and confirmation | confirmation of name changes only | spec 069 (copy from any readable notebook), spec 071 (`ShareRecipeService`, name matching) |
| S-046 | note fix | pending `backlog` | pending `backlog`; note: PATCH sets `bought` only | `api/api/routes/shopping_list.py:152`, `SetBoughtBody` |
| S-073 | split | no entry | done (scheduled translation job); review list split to S-080 | merged #43 (bd5f790); tasks 46/58 |
| S-080 | add | none | pending `in_design`, admin review of AI-made standard names | spec 073 US3, T031–T040 open |
| S-076 | add | no entry | done; open T018 | merged #46 (b9c4fe3), #47 (3c9094e); tasks 19/20 |
| S-074 | status | pending `backlog` | pending `in_design` | `specs/074-ingredients-table/spec.md` (draft, no tasks, no code) |
| S-032 | note fix | "Container ... exist from the bootstrap" | `mcp` service removed in spec 073 | no `mcp` service in `docker-compose*.yml` on main |
| S-034 | move to done | pending `backlog` | done; owner accepted the fixtures | `api/tests/fixtures/ai_eval/` (11 text cases; language, matching, pages, pairs sets) |
| S-081 | add | none | pending `in_design`, picture pop-up from the author's avatar | spec 041 FR-027, T062 and T065 open |
| S-060 | note fix | done; `verification: pending implementation` | done; verification names the code | `ui/app/kitchens/[kitchenId]/notebooks/page.tsx` (60b7178, S-035), `ui/app/notebooks/NotebookTabScreen.tsx` (b166b56, S-059) |
| S-071 | note fix | done; "Stays in_progress until T034 passes." | done; T004 answered (archived kitchens included); open T034 | `specs/071-share-recipe-to-user/tasks.md` (T004 done with the default), research.md "Owner to confirm" |
| S-043 | note fix | done; no verification | done; verification added: open T058, T059 | merged #40 (c0c1721); tasks 61/64 |
| header | note fix | focus text of 2026-11-05 | current order and the cleanup note | — |

Stories checked and left unchanged (no route, screen or service found on main): S-028, S-029,
S-030, S-031, S-042, S-044, S-045, S-054, S-068, S-033, S-061, S-051, S-052, S-053. S-079 (page rendering) is unchanged apart from its number.

## Findings that differ from research R5

- S-041 open tasks are T003, T035, T046, T053, T060, T062, T065, T067, T069, T070, T077, T079,
  T080 (spec alignment), T081 (full automated run), T082 (timing), T083 (walk), T084
  (evaluation), T085 (security pass) and T086 (the move itself, done by this story). T062 is the
  test for T065, so both are unbuilt scope.
- S-047: the author chip on cards is already built (`RecipeCard.tsx` shows `author_alias` as a
  `Chip`), so it is dropped from the narrowed title too.
- S-071: T004 is marked done with the default (archived kitchens included); the owner's answer
  is still open.
- T010 found one more reference: `dev/docs/prd.md` Appendix C calls the registry "S-069, spec
  067". It is changed to S-078. In `ui/lib/featureInventory.ts` the link-capture feature cites
  S-078; quick add keeps S-069 and the table feature keeps S-066. AGENTS.md and README.md cite neither.

## Owner decisions

Answered by the owner on 2026-11-18:

- **New numbers**: merged stories keep their numbers; only pending work is renumbered. Table
  sort keeps S-066 and page rendering (pending) becomes S-079. Both S-069 entries are merged, so
  the owner chose: quick add keeps S-069 (its spec folder and commits say 069) and the refused
  site registry becomes S-078. S-080 and S-081 are new pending stories. This matches research R2.
- **S-041 T065 (and T062)**: becomes its own story, S-081 (`in_design`, spec 041 FR-027).
- **S-034**: done; the fixtures in `api/tests/fixtures/ai_eval` meet the story.
- **S-071 T004**: members of archived kitchens are included, as built.
- **S-074**: not confirmed in this review; its source still says "ID proposed, owner to confirm".

## Follow-ups not done here

- PRD follow-ups still open in their specs: spec 041 T079, spec 070 T043.
- A backlog lint (unique IDs, valid statuses, every spec folder mapped) could run in CI;
  deferred (research R4).

## Validation (quickstart 1–3)

Run 2026-11-18 on `077-backlog-cleanup` after the edits.

1. Parse, IDs, statuses: `duplicates: []`, `bad pending status: []`, `bad done status: []`,
   `highest id: S-081`; 22 pending entries, 51 done (re-run after the owner's answers and S-077 moved to done).
2. Spec coverage: no output. Checked by hand:
   S-078's source is `specs/067-refused-site-registry`.
3. Inventory: every cited ID exists; the planned features cite S-028, S-029, S-030, S-044 and
   S-068, all pending. `npx vitest run lib/featureInventory.test.ts`: 8 passed.
