#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

BACKEND_PID=""

cd "$SCRIPT_DIR"

# Local development - no containers
echo "==> Starting native backend on http://127.0.0.1:8000"
source .venv/bin/activate 2>/dev/null || true
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Start frontend (Vite dev)
echo "==> Starting frontend on http://localhost:5173"
cd "$SCRIPT_DIR/frontend"
pnpm dev &
FRONTEND_PID=$!

cleanup() {
  kill "$FRONTEND_PID" 2>/dev/null || true
  kill "$BACKEND_PID" 2>/dev/null || true
  exit
}

trap cleanup INT TERM

echo ""
echo "  Backend:  http://127.0.0.1:8000"
echo "  Frontend: http://localhost:5173"
echo "  Press Ctrl+C to stop both."
echo ""

wait
