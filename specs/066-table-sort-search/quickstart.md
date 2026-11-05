# Quickstart: validate Sort and Search for Tables

## Prerequisites

- Worktree stack running: `./scripts/compose-up.sh -d` (UI on the worktree port, e.g. 3370).
- An admin account (`users.is_admin`, spec 055): on a dev stack the seeded owner (`SEED_DEV_USER_EMAIL`) is one, via `SEED_DEV_USER_ADMIN` (default `1` under the dev overlay). Seed data with invented names, including accented ones (for example "Sopa de maíz", "Ñoquis").

## Automated

```sh
cd ui && npm run test -- DataTable AdminDashboard && npm run lint && npm run typecheck
```

Expected: helper tests cover text/number/date, empties last both ways, stability, accent/case folding; component tests cover aria-sort, toggle, search, no-matches, no fetch on sort/search.

## Browser walk (360px and 1280px, en and es, keyboard only once)

1. Open `/admin`, Recipes tab. Click "Added to carts": ascending, heading shows direction. Click again: descending.
2. Sort Title: "Ñoquis" sits with N, "sopa" and "Sopa" together.
3. Type "MAIZ": "Sopa de maíz" remains. Sort a column: only filtered rows reorder.
4. Type "zzz": the no-matches text shows; clear: all rows return.
5. Units and Ingredients: same search checks. Users: no search bar, every data column sorts; empty dates last both ways.
6. Switch tab and back: default order, empty search.
7. Network panel: no request on any sort or search.
8. Tab to a heading, press Enter: sort changes; a screen reader reads the direction.
