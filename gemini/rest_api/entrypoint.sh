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
#   # Legacy volume bootstrapped from main's pre-Alembic init_sql/:
#   docker exec geminibase-rest-api alembic stamp 0001_baseline
#   #   then re-start the container so `upgrade head` applies the rest.
#   #   (0002 carries an idempotent bridge that creates the five tables
#   #   main's init_sql lacked: users, user_experiments,
#   #   reference_datasets, reference_plots, plot_geometry_versions.)
#
#   # Volume bootstrapped from some intermediate branch init_sql/:
#   docker exec geminibase-rest-api alembic stamp <last-revision-in-DB>

set -euo pipefail

cd /geminibase

if [[ "${GEMINI_RUN_MIGRATIONS:-0}" == "1" ]]; then
    echo "[entrypoint] GEMINI_RUN_MIGRATIONS=1 — checking alembic state"
    # `alembic current` exits 0 with empty stdout when the version table
    # is missing OR present-but-empty. INFO log lines go to stderr, so
    # plain stdout content == "DB has a stamped revision."
    # Bounded, with its messages kept: a check that never answers (database
    # unreachable, slow storage) used to hang the start with nothing logged.
    t0=$(date +%s)
    alembic_out="$(mktemp)"
    alembic_err="$(mktemp)"
    PYTHONFAULTHANDLER=1 alembic current >"$alembic_out" 2>"$alembic_err" &
    apid=$!
    for _ in $(seq 1 12); do
        kill -0 "$apid" 2>/dev/null || break
        sleep 5
    done
    if kill -0 "$apid" 2>/dev/null; then
        # Still waiting after a minute: say on what, then ask Python where.
        echo "[entrypoint] alembic current still running after 60 s:"
        grep -E '^(State|Name)' "/proc/$apid/status" 2>/dev/null
        echo "[entrypoint] kernel wait: $(cat /proc/$apid/wchan 2>/dev/null)"
        for c in $(pgrep -P "$apid" 2>/dev/null); do
            echo "[entrypoint] child $c: $(grep -E '^State' /proc/$c/status 2>/dev/null) wait=$(cat /proc/$c/wchan 2>/dev/null)"
        done
        ls -l "/proc/$apid/fd" 2>/dev/null | tail -8
        kill -ABRT "$apid" 2>/dev/null
        sleep 5
        tail -60 "$alembic_err"
    fi
    wait "$apid"
    rc=$?
    current_rev="$(tr -d '[:space:]' <"$alembic_out")"
    echo "[entrypoint] alembic current took $(( $(date +%s) - t0 )) s (exit $rc)"
    if [[ "$rc" -ne 0 ]]; then
        echo "[entrypoint] alembic current failed or timed out; its messages:" >&2
        tail -40 "$alembic_err" >&2
    fi
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

  # Legacy volume bootstrapped from main's pre-Alembic init_sql/:
  docker exec <this-container> alembic stamp 0001_baseline

  # Volume bootstrapped from an intermediate init_sql/: pick the last
  #   migration whose effects are already in your DB (see
  #   alembic/versions/) and stamp there instead.

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

# The install's own account (the desktop app signs in with it; workers use
# it to reach the API). Idempotent: an existing account is left untouched.
if [[ -n "${GEMINI_FIRST_SUPERUSER_EMAIL:-}" && -n "${GEMINI_FIRST_SUPERUSER_PASSWORD:-}" ]]; then
    python -m gemini.cli bootstrap-superuser
else
    echo "[entrypoint] GEMINI_FIRST_SUPERUSER_EMAIL/PASSWORD unset; not creating a superuser"
fi

# If compose/Docker passed a command, exec it (lets compose.yaml override CMD
# with the --reload dev-watcher). Otherwise fall back to the production CMD.
if [[ $# -gt 0 ]]; then
    exec "$@"
else
    exec poetry run litestar --app gemini.rest_api.app:app run --host 0.0.0.0 --port 7777
fi
