# Research: Backlog cleanup against what is built

Evidence base: `main` at e4b2bb8 (2026-11-18). Spec: [spec.md](spec.md).

## R1. What counts as done

- **Decision**: A story is done when its scope is merged on `main`. Open manual checks (browser
  walks, timings, owner wording reviews, PRD follow-ups) are listed by task ID in the
  verification note and do not keep the story pending.
- **Rationale**: This is the existing rule in AGENTS.md "Backlog files" and the header of
  `backlog-done.yaml` ("manual verification may still be open"). Most done entries already
  carry open walks (S-027, S-035, S-069).
- **Alternatives considered**: Keep built stories in `verification` until every walk passes.
  Rejected: it is the state that let S-041 look unbuilt; the `verification` status stays
  available for stories whose code is built but not merged.

## R2. Clashing IDs: which entry keeps the number

- **Decision**: The entry whose spec folder number equals the ID keeps it. Numbers assigned:

  | Old | Story | New |
  |-----|-------|-----|
  | S-069 (done, second entry) | Refused site registry, spec 067 | S-078 |
  | S-066 (pending, later) | Render browser-only recipe pages | S-079 |

  S-069 quick add (spec 069) and S-066 table sort (spec 066) keep theirs. S-067 recipe image
  keeps its number; its note says it has no spec folder and that spec 067 is the registry.
- **Rationale**: The folder number is the rule in the backlog header ("NNN is the story
  number"), so the match is the least surprising owner.
- **Alternatives considered**: Renumber the registry to S-067 and move recipe image. Rejected:
  S-067 recipe image is cited in the feature inventory and recipe commits.
- **Next free number**: the highest across both files and `specs/` is 077 (this story), so new
  numbers start at 078.

## R3. Splitting a partly built story

- **Decision**: The original number stays with the done part; the remainder gets a new number
  and points at the open tasks of the original spec folder. Applied to spec 073: S-073 done
  (scheduled translation job, merged #43); S-080 pending `in_design`, "Admin review of
  AI-made standard ingredient names" (spec 073 US3, tasks T031–T040, plus T055–T056).
- **Rationale**: The inventory already cites S-073 for an available feature, and #43 shipped
  under it. Moving the number to the pending part would make an available feature cite a
  pending story.
- **Alternatives considered**: Keep S-073 pending until US3 ships. Rejected: hides a merged
  service (the `jobs` Compose service) from the done record.
- **Narrowing without split**: S-047 and S-048 have nothing built under their own numbers; the
  built parts came from S-067, S-069 and S-071. They stay pending with narrowed titles and a
  note naming those stories (FR-008), not split.

## R4. How each story is checked

- **Decision**: Three checks per story, recorded in the change list: (a) merge evidence,
  `git log --oneline main` for the spec number or story ID; (b) `tasks.md` completion,
  `- [x]` against `- [ ]`, and which open tasks are manual; (c) a code search for the routes or
  components the story names when there is no spec folder.
- **Rationale**: Sufficient for the 21 pending entries and 3 unlisted folders; no tooling to add.
- **Alternatives considered**: A permanent backlog lint in CI. Rejected for now (constitution
  1, simplicity); listed as a possible follow-up in the change list.

## R5. Evidence per open story (summary)

| Story | Finding | Outcome |
|-------|---------|---------|
| S-041 | merged #42; 19 open tasks: tests T035, T046, T053, T060, T062, T065, T067, T069, T070, data T003, calibration T077, PRD T079, walks | done; open tasks listed. T065 (picture pop-up) is a feature task, so the note flags it as unbuilt scope for the owner |
| S-066 | 25/25 tasks; Spanish review open | done |
| S-072 | palette and frosted bar on `main` (c99d0c6, e1806b8 and follow-ups); open T002, T017, T030, T035, T037, T040 are measurements and walks | done |
| S-074 | spec draft, no tasks, no code | `in_design` |
| S-075 | merged #45; open T041, T042 | done |
| spec 076 | merged #46, #47; open T018 | S-076 done |
| S-046 | PATCH item sets `bought` only | stays `backlog` |
| S-047 | `RecipeCard` shows image; no `cart_add_count`, no author filter | stays, narrowed |
| S-048 | copy from any readable notebook (spec 069) and share copy with name matching (spec 071); no confirmation of name changes | stays, narrowed |
| S-032 | `mcp` service removed in spec 073 | stays, note corrected |
| S-034 | capture fixtures in `api/tests/fixtures/ai_eval` (15 entries) | stays; owner decides |
| S-028, S-029–S-031, S-042, S-044, S-045, S-054, S-068 | no route, screen or service found | stay |

## R6. References that change and those that do not

- **Decision**: Update `ui/lib/featureInventory.ts` (link capture cites S-069 for the registry,
  becomes S-078; the quick-add feature keeps S-069), both backlog files and AGENTS.md if it
  cites a renumbered ID. Do not edit `specs/`, `dev/memory/` logs or commit history; they are
  records of their time, and the new entries' notes give the old number so a search finds both.
- **Rationale**: FR-006. `dev/memory/041126.md` and `history.md` cite S-066 for page rendering;
  the S-079 note naming "was S-066" keeps them traceable.

## R7. Validation

- **Decision**: One-off checks run from the shell with the api venv's PyYAML (6.0.3), plus the
  existing `ui/lib/featureInventory.test.ts`. Commands are in [quickstart.md](quickstart.md).
  Nothing is added to the repository for validation.
- **Alternatives considered**: A committed lint script. Deferred, see R4.

## R8. Branch

- **Decision**: Work on branch `077-backlog-cleanup`, created before the first edit. The setup
  script reported it but did not create it; `main` is checked out.

## R2 confirmed (owner review, 2026-11-18)

Merged stories keep their numbers; only pending work is renumbered. Table sort keeps S-066 and
page rendering becomes S-079. Both S-069 entries are merged; quick add keeps S-069 and the
refused site registry becomes S-078, as decided above. The spec 041 picture pop-up became S-081.
