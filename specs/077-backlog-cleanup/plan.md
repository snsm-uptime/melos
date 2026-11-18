# Implementation Plan: Backlog cleanup against what is built

**Branch**: `077-backlog-cleanup` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/077-backlog-cleanup/spec.md`

## Summary

Bring `dev/docs/backlog.yaml` and `dev/docs/backlog-done.yaml` in line with `main` at e4b2bb8:
move merged stories to the done file with their open checks (S-041, S-066, S-072, S-075), add
entries for merged work that has none (S-073, S-076), split spec 073's unbuilt review list
into S-080, give the clashing IDs new numbers (registry S-069 → S-078, page rendering S-066 →
S-079), narrow S-047 and S-048, correct stale notes (S-032, S-060, S-071, S-043) and the
backlog header, and update the feature inventory's story references. A change list in
`notes.md` goes to the owner before commit. Decisions are in [research.md](research.md).

## Technical Context

**Language/Version**: YAML documents; one TypeScript file (`ui/lib/featureInventory.ts`) for ID
references only

**Primary Dependencies**: none added; PyYAML 6.0.3 from the api venv for one-off checks

**Storage**: files in the repository, no database change

**Testing**: quickstart checks (YAML parse, unique IDs, statuses, spec coverage) and the
existing `ui/lib/featureInventory.test.ts`

**Target Platform**: repository documentation

**Project Type**: web application (api + ui); this story touches docs and one ui data module

**Performance Goals**: n/a

**Constraints**: no story deleted; done entries edited only to correct notes or record open
checks; `specs/`, `dev/memory/` and history not rewritten

**Scale/Scope**: 21 pending entries, 31 done entries, 31 spec folders, 1 inventory file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|-----------|-------|--------|
| 1. Simplicity and reuse | No new tool or file format; checks are one-off commands | Pass |
| 2. Tech stack stability | No dependency added | Pass |
| 3. Hexagonal architecture | No code layers touched | Pass |
| 4. Security and privacy | No data, secrets or personal details in entries | Pass |
| 5. No AI shortcuts | No AI feature | Pass |
| 6. Testing and quality | Inventory test run after the ID change; quickstart validates the files | Pass |
| 7. Deployment and operations | No runtime change | Pass |
| 8. Code review and git discipline | Own branch, owner reviews the change list, small commits (files, then inventory) | Pass |
| 9. Product scope | The story has a spec; the owner keeps choosing priorities, and new numbers need the owner's approval | Pass |

Re-check after design: unchanged, all pass. No exceptions needed.

## Project Structure

### Documentation (this feature)

```text
specs/077-backlog-cleanup/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R8
├── data-model.md        # Phase 1: story entry, transitions, change list row
├── quickstart.md        # Phase 1: validation commands
├── contracts/
│   └── change-list.md   # Phase 1: the owner's review record and added-entry format
├── notes.md             # Created during implementation: the change list
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Files changed by this story

```text
dev/docs/backlog.yaml          # pending entries: removals, narrowing, notes, header, new S-079, S-080, S-077
dev/docs/backlog-done.yaml     # appended: S-041, S-066, S-072, S-075, S-073, S-076, S-077; S-078 renumbered; notes fixed
ui/lib/featureInventory.ts     # S-069 → S-078 on the link-capture feature
AGENTS.md                      # only if it cites a renumbered ID (none found at planning time)
```

**Structure Decision**: Edits in place in the existing files; no new source directories.

## Implementation order

1. Create branch `077-backlog-cleanup`; add S-077 to the pending file as `in_progress`.
2. Re-verify every row of research R5 against `main` and write `notes.md` (contract).
3. Renumber (R2) and update the inventory reference (R6).
4. Move merged stories to the done file; add S-073 and S-076; add S-080 and S-079 pending (R3).
5. Narrow S-047, S-048; correct S-032, S-074 status, done-file notes S-060, S-071, S-043.
6. Rewrite the backlog header comments for the current state.
7. Run quickstart 1–3; record results in `notes.md`.
8. Owner review; then move S-077 to done with its verification note.

## Complexity Tracking

No violations.
