# Contract: change list for the owner's review

Written to `specs/077-backlog-cleanup/notes.md` before the backlog files are committed
(FR-013). One row per story touched; stories not touched are not listed.

```markdown
| Story | Action | Before | After | Evidence |
|-------|--------|--------|-------|----------|
| S-041 | move to done | pending, in_progress | done; open: T003, T035, ... | merged #42 (120a09d); tasks 67/86 |
| S-069 (registry) | renumber | S-069, done | S-078, done; note "was S-069" | spec 067; clashes with spec 069 |
```

`Action` is one of: `move to done`, `split`, `renumber`, `add`, `status`, `narrow`,
`note fix`. Evidence names a commit, PR, task count or file path.

Below the table, two short lists:

- **Owner decisions**: items left open for the owner (S-034, the S-041 T065 pop-up, approval of
  new numbers S-078 to S-080).
- **Follow-ups not done here**: PRD updates found, a possible backlog lint.

## Contract: entry text added to the done file

```yaml
  - id: S-076
    title: Keep the pasted recipe text with the recipe, and offer every writable notebook in quick add
    epic: Capture
    priority: must
    status: done
    journey: J2
    source: owner request (post-MVP); specs/076-keep-pasted-recipe-text
    verification: >
      Recorded by S-077 on 2026-11-18 from main (merged #46, #47). Tasks 19/20; open: T018
      (manual quickstart walk at desktop and phone width). Feature inventory: <checked or updated>.
```

Titles and sources of added entries are taken from the spec folder's `spec.md`, not invented.
