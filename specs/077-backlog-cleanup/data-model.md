# Data model: Backlog cleanup

No database change. The "data" is the two YAML files and the feature inventory.

## Story entry

Fields as used today in `dev/docs/backlog.yaml` and `dev/docs/backlog-done.yaml`:

| Field | Required | Rule |
|-------|----------|------|
| `id` | yes | `S-NNN`, unique across both files (FR-005) |
| `title` | yes | Names only the scope of this entry; narrowed after a split (FR-004) |
| `epic` | yes | Existing epics: Bootstrap, Kitchens, Capture, Recipes, Cart, Ask, MCP, Account, Platform, Quality, Deployment |
| `priority` | yes | `must`, `should`, `later` |
| `status` | yes | Pending file: `backlog`, `in_design`, `in_progress`, `verification`. Done file: `done` |
| `journey` | no | PRD journey, e.g. `J3` |
| `source` | yes | PRD section, owner request, and the spec folder when one exists |
| `acceptance` | no | PRD acceptance IDs |
| `notes` | no | Scope and history; corrected where it contradicts the code (FR-008) |
| `verification` | done only | Date, tests run, open checks by task ID (FR-002) |

## State transitions

```text
backlog --spec written--> in_design --build starts--> in_progress --built, not merged--> verification
   any pending status --scope merged on main--> done (entry moves to the end of backlog-done.yaml)
   pending, partly merged --split (R3)--> done (original ID) + pending (new ID)
   duplicate ID --renumber (R2)--> new ID; note "was S-NNN"
```

An entry never moves from done back to pending; missing scope found later becomes a new
pending story.

## Change list row

The review record for the owner (FR-013), kept in `specs/077-backlog-cleanup/notes.md`; format
in [contracts/change-list.md](contracts/change-list.md).

## Feature inventory reference

`ui/lib/featureInventory.ts` entries carry `stories: string[]` and `status: available |
planned`. Rules after cleanup: every cited ID exists in one file; a `planned` feature cites only
pending stories (SC-005).
