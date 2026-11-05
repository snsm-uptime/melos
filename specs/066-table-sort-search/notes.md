# Notes: Sort and Search for Tables

## Browser walk (T024), 2026-11-04

Headless Chromium (Playwright 1.64.1) on the WSL host against the worktree stack
(`http://localhost:3370`, its own Postgres), signed in as the seeded admin. Quickstart steps
1 to 8 at 1280px and 360px, in English and Spanish (account language set per pass, reset to
empty afterwards); keyboard only once per language. Read-only apart from the language and a
temporary spread of `cart_add_count` (1 to 11, reset to 0 afterwards) so step 1 sorts real
numbers.

Data: 9 recipes (7 read from production by the dev seed, 2 invented), including the accented
"Galletas Clásicas con Chispas de Chocolate".

Result: **70/70 checks passed.**

| Step | Check | Result |
|---|---|---|
| 1 | "Added to carts" ascending then descending, `aria-sort` follows | 1,2,3,4,6,7,8,9,11 then reversed |
| 2 | Title order equals `Intl.Collator(base, numeric)` | pass, en and es |
| 3 | "CLASICAS" finds "Galletas Clásicas…"; sorting keeps the filter | pass |
| 4 | "zzz": no-matches text, no table, input editable; clearing restores 9 rows | pass |
| 5 | Search bar on Units and Ingredients; none on Users; all 10 Users columns sort; empty "Newest session" values last both ways | pass |
| 6 | Leaving Recipes and coming back: loaded order, empty search, no `aria-sort` | pass |
| 7 | No request on any sort or search (only the two tab loads) | pass |
| 8 | Tab to a heading, Enter: `aria-sort="ascending"`, label "Title, sort level 1, ascending" / "Título, nivel de orden 1, ascendente" | pass |
| Layout | Page width equals the viewport at 360px; the table scrolls inside its box | 360px |

Timings (all four passes):

- SC-001, open the Recipes tab and sort, under 2 s: 828 to 873 ms (includes the tab's
  first load and the loader's minimum time).
- SC-002, search result, under 1 s: 8 to 23 ms.

Not covered: a real screen reader (the walk reads the accessible label and `aria-sort`
instead), and the Network panel by hand (the walk records every request instead).
