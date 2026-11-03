#!/usr/bin/env bash
# Run the api tests in Compose for this checkout, creating the test database if it is missing.
# Usage: ./scripts/compose-test.sh [pytest args, e.g. pytest -q tests/test_notebook_domain.py]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=compose-lib.sh
source "$SCRIPT_DIR/compose-lib.sh"

ROOT="$(compose_repo_root)"
compose_require_docker
compose_require_env "$ROOT"

cd "$ROOT"
TEST=(docker compose -f docker-compose.yml -f docker-compose.test.yml)

# Left alone when it is running, so a dev stack's db is not recreated.
if [[ -z "$("${TEST[@]}" ps -q --status running db)" ]]; then
  compose_require_free_pgdata "$ROOT"
  "${TEST[@]}" up -d --wait db
fi

# shellcheck disable=SC2016 # expanded inside the container
"${TEST[@]}" exec -T db sh -c '
  name="${TEST_POSTGRES_DB:-melos_test}"
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select 1 from pg_database where datname = '"'"'$name'"'"'" | grep -q 1 \
    || createdb -U "$POSTGRES_USER" "$name"
'

"${TEST[@]}" run --rm --build api "$@"
