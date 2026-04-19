#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

BACKEND_PID=""

cd "$SCRIPT_DIR"

# Configurable ports (override via VINO_BACKEND_PORT / VINO_FRONTEND_PORT)
BASE_BACKEND_PORT="${VINO_BACKEND_PORT:-18000}"
BASE_FRONTEND_PORT="${VINO_FRONTEND_PORT:-15173}"

# Find first available ports starting from base
find_free_port() {
  local port=$1
  while lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do
    port=$((port + 1))
  done
  echo "$port"
}

BACKEND_PORT=$(find_free_port "$BASE_BACKEND_PORT")
FRONTEND_PORT=$(find_free_port "$BASE_FRONTEND_PORT")

# Load .env so OPENROUTER_API_KEY and other secrets are available
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.env"
  set +a
fi

# Default to Playwright retrieval for live data (overridable via env)
export VINO_RETRIEVAL_BACKEND="${VINO_RETRIEVAL_BACKEND:-playwright}"
# Ensure local dev uses in-process Playwright, not the docker microservice
export VINO_PLAYWRIGHT_SERVICE_URL="${VINO_PLAYWRIGHT_SERVICE_URL:-}"

echo "==> Starting native backend on http://127.0.0.1:$BACKEND_PORT (retrieval=$VINO_RETRIEVAL_BACKEND)"
source .venv/bin/activate 2>/dev/null || true
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!

# Start frontend (Vite dev) with dynamic port
echo "==> Starting frontend on http://localhost:$FRONTEND_PORT"
cd "$SCRIPT_DIR/frontend"
VITE_PORT="$FRONTEND_PORT" pnpm dev -- --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

cleanup() {
  kill "$FRONTEND_PID" 2>/dev/null || true
  kill "$BACKEND_PID" 2>/dev/null || true
  exit
}

trap cleanup INT TERM

echo ""
echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  Press Ctrl+C to stop both."
echo ""

# Export for potential subprocess use
export VINO_BACKEND_URL="http://127.0.0.1:$BACKEND_PORT"

wait
