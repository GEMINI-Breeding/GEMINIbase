#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PIPELINE_DIR="$(cd "$PROJECT_ROOT/../gemini/pipeline" && pwd)"
COMPOSE_FILE="$PIPELINE_DIR/docker-compose.yaml"
ENV_FILE="$PIPELINE_DIR/.env"
ENV_EXAMPLE="$PIPELINE_DIR/.env.example"
API_URL="http://localhost:7777"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[gemini-ui]${NC} $1"; }
ok()   { echo -e "${GREEN}[gemini-ui]${NC} $1"; }
warn() { echo -e "${YELLOW}[gemini-ui]${NC} $1"; }
err()  { echo -e "${RED}[gemini-ui]${NC} $1"; }

# ── 1. Check Docker is available ──────────────────────────────────────
if ! command -v docker &>/dev/null; then
  err "Docker not found. Install Docker Desktop to run the GEMINI backend."
  exit 1
fi

if ! docker info &>/dev/null; then
  err "Docker daemon is not running. Start Docker Desktop first."
  exit 1
fi

# ── 2. Ensure .env exists ────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$ENV_EXAMPLE" ]; then
    log "No .env found — copying from .env.example"
    cp "$ENV_EXAMPLE" "$ENV_FILE"
  else
    err "No .env or .env.example in $PIPELINE_DIR"
    exit 1
  fi
fi

# ── 3. Start backend services if REST API is not reachable ───────────
check_api() {
  curl -sf "${API_URL}/schema" >/dev/null 2>&1
}

if check_api; then
  ok "Backend already running at ${API_URL}"
else
  log "Backend not reachable — starting Docker services..."
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build 2>&1 | tail -5

  log "Waiting for REST API to be healthy..."
  for i in $(seq 1 60); do
    if check_api; then
      break
    fi
    if [ "$i" -eq 60 ]; then
      err "REST API did not become healthy after 60s."
      err "Check logs: docker compose -f $COMPOSE_FILE logs rest-api"
      exit 1
    fi
    printf "."
    sleep 2
  done
  echo
  ok "Backend ready at ${API_URL}"
fi

# ── 4. Install UI dependencies if needed ─────────────────────────────
if [ ! -d "$PROJECT_ROOT/node_modules" ]; then
  log "Installing dependencies..."
  cd "$PROJECT_ROOT" && npm install
fi

# ── 5. Set CORS on backend (wildcard for dev) ────────────────────────
# The Vite proxy handles this, so no CORS config needed.

# ── 6. Start Vite dev server ─────────────────────────────────────────
ok "Starting GEMINI UI at http://localhost:5173"
echo
cd "$PROJECT_ROOT" && exec npx vite --host
