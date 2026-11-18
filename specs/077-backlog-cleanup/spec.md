# Feature Specification: Backlog cleanup against what is built

**Feature Branch**: `077-backlog-cleanup`

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "I want to clean up the @dev/docs/backlog and @dev/docs/backlog-done.yaml based on what has been already implemented to avoid doing double work"

## User Scenarios & Testing *(mandatory)*

The people served are the project owner, who picks the next story by priority (constitution
principle 9), and anyone (person or agent) who starts a story from the backlog. Both read
`dev/docs/backlog.yaml` to decide what to build and `dev/docs/backlog-done.yaml` to see what
already exists. Today the two files disagree with the code and with each other (see the
audit at the end), so a reader can pick work that is already built.

### User Story 1 - The pending backlog lists only work not yet built (Priority: P1)

The owner opens the pending backlog and every entry in it is work that is not merged on
`main`. Stories that are built and merged, even with a browser walk still open, are in the
done file with a verification note that names the checks still open.

**Why this priority**: This is the double work the owner wants to avoid. A story such as
S-041 (photo capture), listed `in_progress` though merged in #42, invites someone to build it
again.

**Independent Test**: For every entry left in the pending backlog, look for its merged code or
spec tasks on `main`; none is found complete. For every entry moved, its merge is found.

**Acceptance Scenarios**:

1. **Given** a story whose spec tasks are complete except manual walks and whose code is merged
   on `main`, **When** the cleanup runs, **Then** the story is in the done file with
   `status: done` and a verification note listing each open check by task ID.
2. **Given** a story with no merged code, **When** the cleanup runs, **Then** it stays in the
   pending backlog.
3. **Given** a story with part of its scope merged (for example a user story of its spec not
   built), **When** the cleanup runs, **Then** the built part is recorded as done and the
   remaining part stays pending with a title and notes that name only what is left.

---

### User Story 2 - Every story number points to one story (Priority: P1)

A reader who sees a story number in a spec, a commit, the feature inventory or a backlog note
finds exactly one entry for it across both files, and its spec folder number matches.

**Why this priority**: Duplicate numbers hide work. S-066 is both "table sort and search" (done
work, spec 066) and "render browser-only recipe pages" (later). S-069 is both "quick add"
(spec 069) and "refused site registry" (spec 067), while S-067 is "recipe image". A reader who
looks up one of these numbers can read the wrong story and skip or repeat work.

**Independent Test**: List every `id` across both files; each appears once. Each story that names
a spec folder has the folder's number equal to its own, or a note that says why not.

**Acceptance Scenarios**:

1. **Given** two entries share an ID, **When** the cleanup runs, **Then** the entry whose spec
   folder matches the number keeps it, and the other gets the next free number with a note
   naming its old number.
2. **Given** a story was renumbered, **When** a reader searches the repository for the old
   number in the feature inventory or another backlog note, **Then** every reference that meant
   the renumbered story uses the new number.

---

### User Story 3 - Built work with no entry gets one (Priority: P2)

Work merged on `main` from a spec but never given a backlog entry (spec 073 ingredient
translation job, spec 076 kept recipe text) has an entry, so the story numbers it uses are
taken and the record of what is built is complete.

**Why this priority**: Without an entry, the next free number can collide with a spec folder
already used, and the done file does not show the feature exists.

**Independent Test**: Every folder under `specs/` maps to a story in one of the two files, or to
the bootstrap or extractor note already in the done file (001, 015).

**Acceptance Scenarios**:

1. **Given** a spec folder with merged code and no backlog entry, **When** the cleanup runs,
   **Then** a done entry exists with its title, epic, source, and verification note.
2. **Given** a spec folder with no merged code and no entry, **When** the cleanup runs, **Then**
   a pending entry exists with status `in_design`.

---

### User Story 4 - Pending entries describe the code as it is today (Priority: P3)

The notes of each remaining pending story say what already exists and what is left, so the
person who picks it starts from the right place.

**Why this priority**: Stale notes cost time but do not by themselves cause double work.

**Independent Test**: Read each pending entry's notes against the code; no note claims a part
exists that was removed, or that a part is missing that is built.

**Acceptance Scenarios**:

1. **Given** S-032 says the MCP container exists from the bootstrap, **When** the cleanup runs,
   **Then** its note says the service was removed in spec 073 and the story starts from none.
2. **Given** S-048 says the single-recipe copy is built under S-071, and spec 069 also built a
   copy from any readable notebook, **When** the cleanup runs, **Then** its title and notes
   name only the remaining step.
3. **Given** the backlog header comments describe a focus that is finished, **When** the
   cleanup runs, **Then** they describe the current state and order.

### Edge Cases

- A story marked done whose verification note says it is still in progress (S-071 "Stays
  in_progress until T034 passes"): the AGENTS.md rule is that done means merged with open
  checks recorded, so it stays done and the note is reworded to list T034 as open.
- A done entry whose verification says "pending implementation" though the feature is built
  (S-060): the note is corrected from the merged code.
- A story whose evidence is unclear (S-034 evaluation set, where capture evaluation fixtures
  exist but the PRD's set is not confirmed): it stays pending, and its note records what exists
  and that the owner decides whether it is met.
- A pending story already in the feature inventory as planned: if moved to done, the inventory
  entry becomes available in the same change (AGENTS.md, spec 075 FR-017).
- A spec folder whose number differs from its story (S-069 entry for spec 067): handled by
  User Story 2; the spec folder is never renamed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each story in either file MUST be checked against `main`: its spec folder's
  `tasks.md`, its merged commits and the code it names.
- **FR-002**: A story whose scope is merged on `main` MUST be in `backlog-done.yaml` with
  `status: done`, appended at the end, with a verification note dated 2026-11-18 that lists the
  tasks still open by ID (browser walks, timings, owner reviews).
- **FR-003**: A story with no merged scope MUST stay in `backlog.yaml` with a status from the
  defined set (`backlog`, `in_design`, `in_progress`, `verification`); `in_design` when a spec
  folder exists and no code is merged.
- **FR-004**: A story with part of its scope merged MUST be split: the built part recorded as
  done, the rest kept pending under a title that names only what is left. The split keeps the
  original number on the done part, because commits and the feature inventory already cite it
  for what shipped; the remaining part takes the next free number and names the open tasks of
  the original spec folder (research R3).
- **FR-005**: Story IDs MUST be unique across both files. On a clash, the entry whose spec
  folder number matches keeps the ID; the other takes the next free number, and its note
  records the old number.
- **FR-006**: Every reference to a renumbered story in `ui/lib/featureInventory.ts`, both
  backlog files and AGENTS.md MUST be updated to the new number. Spec folders and past commits
  are not changed.
- **FR-007**: Every spec folder under `specs/` MUST map to a story entry, except 001 and 015,
  which the done file already cites as sources.
- **FR-008**: Pending entries' notes MUST be corrected where they contradict the code
  (removed services, parts built by other stories, superseded dependencies).
- **FR-009**: Done entries are not otherwise edited (header rule of `backlog-done.yaml`), except
  to correct a verification note that contradicts the merged code or to record checks still
  open; each such edit says so in the note.
- **FR-010**: The header comments of `backlog.yaml` MUST describe the current focus and order,
  and the "next free number" MUST be derivable as one more than the highest ID across both
  files and all spec folders.
- **FR-011**: A story moved to done that adds a feature a person can use MUST have its feature
  inventory entry set to available in the same change.
- **FR-012**: No story MUST be deleted. A story found to be fully covered by another story is
  moved to done with a note naming the story that built it.
- **FR-013**: The cleanup MUST produce a change list (story, before, after, evidence) the owner
  reviews before the change is committed.

### Key Entities

- **Story entry**: an item in either backlog file: ID, title, epic, priority, status, journey,
  source, acceptance, notes, verification.
- **Spec folder**: `specs/NNN-short-name`, with its `tasks.md` showing which tasks are complete.
- **Evidence**: a merged commit or PR, completed tasks, or code on `main` that shows a story's
  scope is built.
- **Feature inventory entry**: an item in `ui/lib/featureInventory.ts` that cites stories and is
  `available` or `planned`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 entries in the pending backlog whose full scope is merged on `main`.
- **SC-002**: 0 story IDs that appear more than once across both files.
- **SC-003**: 100% of spec folders map to a story entry (001 and 015 excepted).
- **SC-004**: 0 entries in the pending backlog with a status outside the defined set.
- **SC-005**: Every story ID cited in the feature inventory exists, and every `planned`
  inventory feature cites only pending stories.
- **SC-006**: A reader picking the top pending story can tell what is left to build from its
  entry alone in under 2 minutes, without opening the code.

## Assumptions

- "Implemented" follows AGENTS.md "Backlog files": merged on `main`, with open manual checks
  recorded in the verification note, not blocking done.
- The evidence base is `main` at e4b2bb8 (2026-11-18); work in `.claude/worktrees/` that is not
  merged does not count.
- The PRD is not changed by this story; PRD follow-ups found are listed in the change list.
- The owner reviews the change list before commit (FR-013), and approves new numbers.
- No code changes beyond story numbers in the feature inventory.

## Audit at specification time (2026-11-18)

Findings that drive the requirements; the plan verifies each one again.

| Story | Today | Evidence | Expected after cleanup |
|-------|-------|----------|------------------------|
| S-041 photo capture | pending, `in_progress` | merged #42; tasks 67/86, open are tests, PRD, calibration, walk | done; open tasks listed (FR-002) |
| S-066 table sort and search | pending, `verification` | tasks 25/25; only the Spanish review open | done |
| S-066 render browser-only pages | pending, later | duplicate ID | new number (FR-005) |
| S-072 acrylic chrome, palette | pending, `in_design` | commits c99d0c6, e1806b8 on `main`; tasks 34/40, open are walks and perf | done |
| S-074 ingredients table | pending, `backlog` | spec 074 draft, no tasks, no code | `in_design` |
| S-075 landing tour | pending, `verification` | merged #45; tasks 57/59 | done |
| spec 073 translation job | no entry | merged #43; tasks 46/58, US3 review list not built | split: done part, pending review-list part (FR-004) |
| spec 076 kept recipe text | no entry | merged #46, #47; tasks 19/20 | done entry S-076 |
| S-069 refused site registry | done | spec 067; clashes with S-069 quick add | new number (FR-005); inventory updated |
| S-067 recipe image | done | no spec folder of its own; spec 067 is the registry | keeps S-067; note says no spec folder |
| S-060 notebook tabs | done | note says "pending implementation" | note corrected (FR-009) |
| S-071 share recipe | done | note says it stays `in_progress` | note lists T034 open |
| S-043 catalog rename and merge | done | tasks 61/64, open walk, evaluation, T060 | note lists T058, T059 |
| S-046 edit shopping list items | pending | PATCH item only sets bought | stays; note says so |
| S-047 recipe cards | pending | cards with image exist; no cart-frequency sort, author filter | narrowed (FR-004) |
| S-048 copy recipe | pending | copy built in S-069 and S-071; confirmation of name changes not built | narrowed to the confirmation step |
| S-032 MCP | pending | MCP service removed in spec 073 | note corrected |
| S-034 AI evaluation set | pending | capture fixtures in `api/tests/fixtures/ai_eval` | stays; owner decides |
| S-028, S-029, S-030, S-031, S-042, S-044, S-045, S-054, S-068 | pending | no matching routes or screens found | stay |
| S-033, S-051, S-052, S-053, S-061 | pending | not built | stay |
