# api/scripts

Nothing here runs in production except `entrypoint.py` (the container's
`CMD`, launched via `python -m scripts.entrypoint` — not meant to be run by
hand). It runs `alembic upgrade head`, optionally seeds a dev user, then
serves the API.

## seed_dev_user.py — dev/worktree accounts

When `SEED_DEV_USER=1` (the default in `docker-compose.dev.yml`), the entrypoint creates
three fixed, pre-verified accounts so the stack is usable without going through sign up.
They are dev-only and live in the script, not in `.env`. All share the password
`DEV_PASSWORD` (`pass12word34`), and none has a photo. Aliases are stored lowercase.

| Email | Alias | Language | Role |
|---|---|---|---|
| `owner@dev.com` | `DevOwner` | en | Owns the shared kitchen; admin when `SEED_DEV_USER_ADMIN` is on |
| `member@dev.com` | `DevMember` | en | Member of the shared kitchen |
| `invitado@dev.com` | `DevInvitado` | es | Outside the kitchen, ready to be invited |

| Variable | Purpose |
|---|---|
| `SEED_DEV_USER_ADMIN` | `1` makes the owner an admin (`/admin`); default `1` under the dev overlay, `0` otherwise. Applied on every boot |
| `SEED_DEV_USER_KITCHEN` | Name of the shared kitchen, next to each account's own first kitchen (default "Dev's Kitchen") |

Fixed recipes, saved in the owner's and the member's kitchen notebooks:

- One invented recipe each: "Arepas de queso" (owner) and "Ensalada de tomate y aguacate" (member).
- A pair to try the catalog language setup, both in the owner's notebook: "Roasted carrots"
  (en: `carrot`, `olive oil`) and "Zanahorias asadas" (es: `zanahoria`, `aceite de oliva`).
  The catalog keeps the four names apart until you merge them (spec 043).
- Oil in both languages: "Pollo al horno" (es: `aceite`), "Oven chicken" (en: `oil`) and
  "Ensalada de lechuga" (es: `aceites`). The seed then merges `oil` into `aceite` as its English
  name, and `aceites` into `aceite` by the singular rule (spec 043, FR-005).

### Rotating recipes

Two built-in recipes, "Cajetas de Tita Marielos" (es) and "JUICY Pesto Pasta!" (en), and the
real ones below are spread evenly over five notebooks: the personal notebook of all three
accounts and the kitchen notebook of the owner and the member. Each goes to the notebook
holding the fewest recipes (ties in that order), authored by its user.

### Real recipes (optional, never committed)

`seed_source_recipes.py` reads recipes from a running Melos app (production) over its
public API. They join the rotation above; a real recipe with a built-in title is dropped.

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
every api boot, also when the accounts already exist: recipes are keyed by title, so ones
already seeded are not added again and a plain restart picks up new ones.

The seed is idempotent: an existing account with the same email is left
untouched. A seed failure is logged and never blocks boot. Never use real
personal data here.

## recipe_languages.py — one-time language proposal (spec 043)

Run once after deploying migration `0021_catalog_other_names`:

    docker compose exec api uv run python -m scripts.recipe_languages detect [--limit N]
    docker compose exec api uv run python -m scripts.recipe_languages status

`detect` reads each recipe not read yet (title, ingredient names and steps only) and detects
its language offline with lingua (`adapters/language/lingua_detector.py`). When the result
differs from the stored fallback language, it stores it as
`proposed_language`, and the recipe page offers "Apply" or "Dismiss". It never writes
`language` itself. Every recipe it reads gets `language_detected_at`, so a second run reads
only new rows. It commits every 50 recipes, prints counts, and exits 0, or 1 on a database
error. It needs no API key and makes no network call.
