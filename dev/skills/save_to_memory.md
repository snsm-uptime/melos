# Save to memory

Append one line to today's memory file (`docs/memory/ddMMYY.md`). Run from the repo root.

## 1. New daily file: summarize the previous day into history

Check whether today's file exists. If it does not, the append in step 2 creates a new daily file, so first:

```bash
today="docs/memory/$(date +%d%m%y).md"
if [ ! -e "$today" ]; then
  find docs/memory -maxdepth 1 -name '[0-9][0-9][0-9][0-9][0-9][0-9].md' | awk -F/ '{n=$NF; sub(/\.md$/,"",n); print substr(n,5,2) substr(n,3,2) substr(n,1,2), $0}' | sort | tail -1 | cut -d' ' -f2
fi
```

The path printed (if any) is the file before today's. Then:

1. Read that whole file.
2. Append to `docs/memory/history.md` one section that summarizes **all** of its lines, grouped by theme (decisions, preferences/corrections, project facts, finished changes). Do not copy the lines; summarize them. Use this heading:

   ```markdown
   ## ddMMYY

   - <summary bullet>
   ```

   The heading uses the previous file's name (`ddMMYY`).
3. If the previous file is empty or no daily file exists yet, skip this step.

`history.md` is append-only, like the daily files.

## 2. Append the memory line

```bash
printf '%s\t%s\n' "$(date +%H:%M)" 'content' >> "docs/memory/$(date +%d%m%y).md"
```

Replace `'content'` with the fact to keep.
