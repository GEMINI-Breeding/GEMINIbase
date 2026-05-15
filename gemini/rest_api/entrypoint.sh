#!/usr/bin/env bash
# REST API container entrypoint.
#
# When GEMINI_RUN_MIGRATIONS=1, run `alembic upgrade head` before starting the
# Litestar server. Day-0 schema is still created by init_sql/ on first-time
# Postgres volume init; Alembic handles evolution after that.
#
# First-time stamping is a manual step — the entrypoint cannot auto-stamp
# safely. A DB with no `gemini.alembic_version` row could be either:
#
#   (a) a fresh volume just bootstrapped from current init_sql/ — schema is at
#       head, so stamping head is correct, OR
#   (b) a legacy volume bootstrapped from an older init_sql/ (whose DDL did
#       NOT yet include the columns introduced by later migrations) — stamping
#       head silently records "fully migrated" and `upgrade head` then no-ops,
#       leaving the DB schema permanently drifted from what the ORM expects.
#
# Case (b) is exactly what 0006_trait_records_accession + 0007 was added to
# bridge; auto-stamping in this path masks that drift. So this script bails
# with an actionable error instead, and the operator chooses:
#
#   # Fresh volume (init_sql/ just ran with current code):
#   docker exec geminibase-rest-api alembic stamp head
#
#   # Legacy volume (init_sql/ ran before some migration was added):
#   docker exec geminibase-rest-api alembic stamp <last-revision-in-DB>
#   #   then re-start the container so `upgrade head` applies the rest.

set -euo pipefail

cd /geminibase

if [[ "${GEMINI_RUN_MIGRATIONS:-0}" == "1" ]]; then
    echo "[entrypoint] GEMINI_RUN_MIGRATIONS=1 — checking alembic state"
    # `alembic current` exits 0 with empty stdout when the version table
    # is missing OR present-but-empty. INFO log lines go to stderr, so
    # plain stdout content == "DB has a stamped revision."
    current_rev="$(alembic current 2>/dev/null | tr -d '[:space:]')"
    if [[ -z "$current_rev" ]]; then
        cat >&2 <<'ERR'
[entrypoint] ERROR: gemini.alembic_version is empty or missing.

This DB has not been stamped with an Alembic revision, so the entrypoint
cannot tell whether init_sql/ ran with the current schema (in which case
stamping `head` would be correct) or an older schema (in which case
stamping `head` would silently skip needed migrations).

Stamp manually, then restart this container:

  # Fresh volume bootstrapped from CURRENT init_sql/:
  docker exec <this-container> alembic stamp head

  # Legacy volume bootstrapped from an older init_sql/:
  #   pick the last migration whose effects are already in your DB
  #   (see backend/alembic/versions/) and stamp there, e.g.:
  docker exec <this-container> alembic stamp 0005_experiment_files_metadata

Then a subsequent start with GEMINI_RUN_MIGRATIONS=1 will `upgrade head`
the rest of the way.
ERR
        exit 1
    fi
    echo "[entrypoint] alembic current: $current_rev — running upgrade head"
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
