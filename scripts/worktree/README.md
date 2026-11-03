# Worktrees (Melos)

Each story gets its own Claude Code worktree, with its own branch, ports and database.

```bash
claude -n 060 -w 060-short-name
```

Put the story number in the `-w` name: it becomes the folder, the branch (`worktree-060-short-name`) and the Compose project, so they line up with `specs/060-short-name`. `-n` only labels the session, for `claude --resume 060`.

On the first start, the `SessionStart` hook in `.claude/settings.json` runs `ensure.sh`. It installs the dependencies and writes the worktree's `.env`, with its own project name, ports and data folder under `~/melos-wt/`. This takes about a minute, and does nothing on later starts or in the primary checkout.

| When | Command |
|---|---|
| To run the app | `./scripts/compose-up.sh -d` |
| To run the api tests | `./scripts/compose-test.sh` |
| To stop the app | `./scripts/compose-down.sh` |
| After merging, from the primary checkout | `./scripts/worktree/worktree-done.sh 060-short-name` |

`worktree-done.sh` stops the stack, deletes that worktree's database, removes the worktree and deletes its branch if it is merged. It refuses a worktree with uncommitted work.

Choosing **remove** when Claude Code exits deletes the folder only, so the stack and data stay behind. Keep the worktree on exit and use `worktree-done.sh`.
