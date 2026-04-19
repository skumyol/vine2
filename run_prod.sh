#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --check flag: just verify if services are running
if [[ "${1:-}" == "--check" ]]; then
  if curl -sf http://127.0.0.1:8042/api/health > /dev/null 2>&1; then
    echo "Backend is running on http://127.0.0.1:8042"
    exit 0
  else
    echo "Backend is NOT running."
    exit 1
  fi
fi

# Production deployment with Docker
echo "==> Starting production services with Docker..."
cd "$SCRIPT_DIR"
"$SCRIPT_DIR/run_docker.sh" up -d

echo ""
echo "  Backend:   http://127.0.0.1:8042"
echo "  Frontend:  http://127.0.0.1:3042"
echo "  Playwright: http://127.0.0.1:8043"
echo ""
echo "  Logs: ./run_docker.sh logs"
echo "  Stop: ./run_docker.sh down"
