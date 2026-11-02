# Quickstart: validate ownership passing

Nothing in the running app triggers this rule until S-054, so validation is automated.

## Prerequisites

While working, run the api tests the way CI does: `uv run pytest` against a throwaway tmpfs `pgvector/pgvector:pg16` container on its own port.

The final check is the Compose test overlay, the canonical command in AGENTS.md. It uses the `melos_test` database, which must exist, and that database sits in the same `pgdata` as dev. So run it in this checkout's usual Compose project, never in a second project with the main `.env`, because `-p` does not separate the data directory.

## Commands

While working:

```bash
cd api
uv run pytest -q tests/test_notebook_domain.py tests/test_notebook_ownership_application.py \
  tests/test_notebook_ownership_integration.py tests/test_notebook_members_application.py \
  tests/test_notebook_members_integration.py tests/test_notebook_invites_application.py \
  tests/test_notebook_invites_integration.py
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```

Final check, from the repository root:

```bash
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" "${TEST_POSTGRES_DB:-melos_test}"'  # first time only
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --no-deps --build \
  -e RECIPE_TEXT_MAX_CHARS=5000 api
```

`--no-deps` leaves a running dev `db` alone. `RECIPE_TEXT_MAX_CHARS=5000` is there because two capture tests pin the default, and this checkout's environment sets another value. `--build` retags `melos-api`.

## What must be shown

The integration tests call the service, then delete the user row themselves, as S-054 will.

| Scenario | Expected |
|----------|----------|
| Owner with members who joined on different dates | Earliest joiner owns it; others unchanged; joining times unchanged |
| Two members with the same joining time, on two identical notebooks | The same person inherits both |
| Member who left and rejoined | Counts from the rejoining |
| Recipes by owner and members | All kept; owner's read "unknown" |
| Several notebooks | Each settled on its own, possibly with different heirs |
| Notebook with no members | Gone, with recipes, catalog, invites and source text |
| Snapshot and open invite, notebook passes | Both unchanged; invite still joins; no sender's name shown; new owner can resend |
| Snapshot, notebook deleted | Stays with its recipes; origin label cleared |
| Person is only a member elsewhere, or in a kitchen | Those notebooks keep their owners |
| User deletion fails after the rule ran | After rollback, every notebook is as it was, passed or deleted |
| Heir leaves while the rule runs (two sessions) | One owner remains; leave is refused or happens first |
| Someone joins while the rule runs (two sessions) | One owner remains; the join is counted or comes after |
| Invite accepted while the notebook is deleted (two sessions) | Invalid-link answer, no 500 |
| After the rule, the new owner invites and removes someone | Works through the existing routes |

## Left for S-054

The browser walk of an account deletion, and seeing the new owner's view in the ui.
