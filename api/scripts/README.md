# api/scripts

Nothing here runs in production except `entrypoint.py` (the container's
`CMD`, launched via `python -m scripts.entrypoint` — not meant to be run by
hand). It runs `alembic upgrade head`, optionally seeds a dev user, then
serves the API.

## seed_dev_user.py — dev/worktree account

When `SEED_DEV_USER=1` (the default in `docker-compose.dev.yml`), the
entrypoint creates a pre-verified account so the stack is usable without
going through sign up:

| Variable | Purpose |
|---|---|
| `SEED_DEV_USER_EMAIL`, `SEED_DEV_USER_PASSWORD` | Account credentials (required; invent them) |
| `SEED_DEV_USER_ALIAS` | Alias claimed on the account (optional) |
| `SEED_DEV_USER_ADMIN` | `1` makes the owner an admin (`/admin`); default `1` under the dev overlay, `0` otherwise. Applied on every boot |
| `SEED_DEV_USER_KITCHEN` | Shared kitchen created next to "My kitchen" (optional; `docker-compose.dev.yml` defaults it to "Dev's Kitchen") |
| `SEED_DEV_MEMBER_EMAIL`, `SEED_DEV_MEMBER_PASSWORD`, `SEED_DEV_MEMBER_ALIAS` | The second account, added to the shared kitchen as a member (optional; the email is derived from the owner's when unset) |

With a shared kitchen the seed also saves two recipes there, one authored by the owner
and one by the member, each in its author's own notebook of that kitchen.

### Real recipes (optional, never committed)

`seed_source_recipes.py` reads recipes from a running Melos app (production) over its
public API. The seed spreads them evenly over every shared-kitchen member's personal
(default) notebook and own kitchen notebook: each goes to the one holding the fewest
recipes, authored by that notebook's user.

| Variable | Purpose |
|---|---|
| `SEED_RECIPES_SOURCE_URL` | The app's base URL, e.g. `https://melos.example.com`. Unset = skipped |
| `SEED_RECIPES_SOURCE_EMAIL`, `SEED_RECIPES_SOURCE_PASSWORD` | An account on that app that can read the notebooks |
| `SEED_RECIPES_SOURCE_NOTEBOOKS` | Comma-separated notebook names (case and accents ignored); empty = every notebook the account reads |

It signs in, lists the account's notebooks (`/api/notebooks`), pages through each chosen
notebook's recipes and reads each one (`/api/recipes/{id}`), then signs out. Only content
is kept (title, servings, ingredient lines, steps), one copy per title; no author, alias,
notebook or id, and nothing is written to disk. Custom units each recipe uses are added
to its author. Any failure logs a warning and the seed goes on without them. This part runs on
every api boot, also when the owner already exists: recipes are keyed by title, so ones
already seeded are not added again and a plain restart picks up new ones.

The seed is idempotent: an existing account with the same email is left
untouched. A seed failure is logged and never blocks boot. Never use real
personal data here.

## recipe_languages.py — one-time language proposal (spec 043)

Run once after deploying migration `0020_catalog_other_names`:

    docker compose exec api uv run python -m scripts.recipe_languages detect [--limit N]
    docker compose exec api uv run python -m scripts.recipe_languages status

`detect` sends each recipe not read yet (title, ingredient names and steps only) to the model.
When the answer differs from the stored fallback language, it stores the answer as
`proposed_language`, and the recipe page offers "Apply" or "Dismiss". It never writes
`language` itself. Every recipe it reads gets `language_detected_at`, so a second run reads
only new rows. It commits every 50 recipes, prints counts, and exits 0, or 1 on a database
error. Uses `GEMINI_API_KEY` and `GEMINI_CHAT_MODEL`.
