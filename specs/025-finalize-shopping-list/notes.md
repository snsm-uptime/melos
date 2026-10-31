# Notes: S-025

## T001: transaction (2026-10-30)

`api.deps.get_db` gives one session per request and commits when the request ends, and FastAPI caches the dependency, so every repository of a request shares it. The repositories never commit. The cart write and the list refresh are therefore atomic. `CartRepository.get_or_create_for_update` holds the cart row lock, which also serializes every list write of a kitchen; the partial unique index is the backstop.

## Changes from the plan

- Writes in an archived kitchen answer 403 `kitchen_archived`, the existing convention, not 409.
- Hand names are trimmed, space-collapsed and lower-cased, not passed through `normalize_name`, which drops accents ("jabón" would read "jabon").
- The read response also carries `kitchen_is_archived`, as the ui's cart data has no such field.

## Results (2026-10-30)

- api in Compose (test overlay): 938 passed, 4 failed. The 4 are in capture and notebook tests this story does not touch (the text limit, vocabulary, and two kitchen-capture notebook tests). ruff clean.
- ui: 975 vitest tests, lint and typecheck clean.
- Migration 0009: upgrade, downgrade and upgrade tested. Applied to the worktree's dev database.
- HTTP walk through the BFF on the worktree stack, one account in a throwaway kitchen, deleted afterwards: hand item on an empty cart, draft, save, refused item, Done, second Done, cart kept, history, the three pages answer 200, outsider 404.

## Open

- T037, the browser walk with two accounts at phone and desktop width, in both languages, is not done.
- The closing date is the UTC day (R7). The HTTP walk recorded 2026-10-31 on the local evening of 2026-10-30, so Done in the evening in the Americas records tomorrow.
- SC-002 and the timed 100-recipe read on the dev stack are unmeasured; the test harness read is under 1 s.
