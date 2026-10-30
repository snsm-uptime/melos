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
| `SEED_DEV_USER_KITCHEN` | Shared kitchen created next to "My kitchen" (optional; `docker-compose.dev.yml` defaults it to "Dev's Kitchen") |
| `SEED_DEV_MEMBER_EMAIL`, `SEED_DEV_MEMBER_PASSWORD`, `SEED_DEV_MEMBER_ALIAS` | The second account, added to the shared kitchen as a member (optional; the email is derived from the owner's when unset) |

With a shared kitchen the seed also saves two recipes there, one authored by the owner
and one by the member, each in its author's own notebook of that kitchen.

The seed is idempotent: an existing account with the same email is left
untouched. A seed failure is logged and never blocks boot. Never use real
personal data here.
