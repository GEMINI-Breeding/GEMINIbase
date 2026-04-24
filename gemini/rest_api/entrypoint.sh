#!/usr/bin/env bash
# REST API container entrypoint.
#
# When GEMINI_RUN_MIGRATIONS=1, run `alembic upgrade head` before starting the
# Litestar server. Day-0 schema is still created by init_sql/ on first-time
# Postgres volume init; Alembic handles evolution after that.
#
# For a DB bootstrapped from init_sql/ before Alembic existed, run once:
#   docker exec geminibase-rest-api alembic stamp head
# to record the baseline. Subsequent container starts with
# GEMINI_RUN_MIGRATIONS=1 will then upgrade cleanly.

set -euo pipefail

cd /geminibase

if [[ "${GEMINI_RUN_MIGRATIONS:-0}" == "1" ]]; then
    echo "[entrypoint] GEMINI_RUN_MIGRATIONS=1 — running alembic upgrade head"
    if ! alembic current >/dev/null 2>&1; then
        echo "[entrypoint] alembic_version missing; stamping baseline first"
        alembic stamp head || true
    fi
    alembic upgrade head
else
    echo "[entrypoint] GEMINI_RUN_MIGRATIONS unset; skipping alembic (day-0 schema handled by init_sql/)"
fi

# If compose/Docker passed a command, exec it (lets compose.yaml override CMD
# with the --reload dev-watcher). Otherwise fall back to the production CMD.
if [[ $# -gt 0 ]]; then
    exec "$@"
else
    exec poetry run litestar --app gemini.rest_api.app:app run --host 0.0.0.0 --port 7777
fi
