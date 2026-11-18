# Quickstart: validate the backlog cleanup

Run from the repository root after the edits, on branch `077-backlog-cleanup`.

## 1. Both files parse, IDs are unique, statuses are valid (SC-002, SC-004)

```sh
api/.venv/bin/python -I - <<'EOF'
import yaml, collections
p = yaml.safe_load(open("dev/docs/backlog.yaml"))["stories"]
d = yaml.safe_load(open("dev/docs/backlog-done.yaml"))["stories"]
ids = collections.Counter(s["id"] for s in p + d)
print("duplicates:", [i for i, n in ids.items() if n > 1])
print("bad pending status:", [s["id"] for s in p if s["status"] not in {"backlog","in_design","in_progress","verification"}])
print("bad done status:", [s["id"] for s in d if s["status"] != "done"])
print("highest id:", max(ids))
EOF
```

Expected: no duplicates, no bad statuses, highest ID at least S-080.

## 2. Every spec folder has a story (SC-003)

```sh
api/.venv/bin/python -I - <<'EOF'
import yaml, os
ids = {s["id"] for f in ("dev/docs/backlog.yaml","dev/docs/backlog-done.yaml") for s in yaml.safe_load(open(f))["stories"]}
for n in sorted(x[:3] for x in os.listdir("specs") if x[:3].isdigit()):
    if f"S-{n}" not in ids and n not in {"001","015"}: print("no story:", n)
EOF
```

Expected: no output. (Spec 067 maps to S-078 through its `source`; check it by hand.)

## 3. Inventory references (SC-005)

```sh
grep -oE 'S-[0-9]{3}' ui/lib/featureInventory.ts | sort -u
```

Each ID printed exists in one file; the stories cited by the four `planned` features (S-028,
S-029, S-030, S-044, S-068) are all pending. Then:

```sh
cd ui && npx vitest run lib/featureInventory.test.ts
```

Expected: passes.

## 4. No pending story is already built (SC-001)

For each pending entry, read its row in `notes.md` and confirm the evidence column shows no
merged scope. Spot-check three: S-041 absent from the pending file; S-046 still pending
(the item PATCH sets `bought` only); S-048's title names only the confirmation step.

## 5. Owner review (FR-013)

The owner reads `specs/077-backlog-cleanup/notes.md` and approves before commit.
