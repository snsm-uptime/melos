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
| `SEED_DEV_USER_KITCHEN` | Extra kitchen created next to "My kitchen" (optional) |

The seed is idempotent: an existing account with the same email is left
untouched. A seed failure is logged and never blocks boot. Never use real
personal data here.
