#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="$ROOT_DIR/data/results/pipeline-run"
LOG_FILE="$RUN_DIR/pipeline.log"
STATUS_FILE="$RUN_DIR/status.env"
PID_FILE="$RUN_DIR/pipeline.pid"
LINES=40
FOLLOW=0

usage() {
  cat <<'EOF'
Usage: scripts/watch_backend_full_pipeline.sh [--follow] [--lines N]

Shows the current pipeline status, whether the PID is alive, and recent log lines.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --follow)
      FOLLOW=1
      shift
      ;;
    --lines)
      LINES="${2:-40}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -f "$STATUS_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$STATUS_FILE"
  echo "Stage: ${STAGE:-unknown}"
  echo "State: ${STATE:-unknown}"
  echo "Message: ${MESSAGE:-}"
  echo "Updated: ${UPDATED_AT:-unknown}"
  echo "Backend: ${BACKEND:-unknown}"
  echo "Input: ${INPUT_CSV:-unknown}"
else
  echo "Status file not found: $STATUS_FILE"
fi

if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE")"
  if ps -p "$pid" -o pid= 2>/dev/null | grep -q "[0-9]"; then
    echo "Process: running (pid=$pid)"
  else
    echo "Process: not running (stale pid=$pid)"
  fi
else
  echo "Process: no pid file"
fi

if [[ -f "$LOG_FILE" ]]; then
  echo
  echo "Recent log output:"
  tail -n "$LINES" "$LOG_FILE"
  if [[ "$FOLLOW" -eq 1 ]]; then
    echo
    echo "Following log. Press Ctrl+C to stop."
    tail -n "$LINES" -f "$LOG_FILE"
  fi
else
  echo "Log file not found: $LOG_FILE"
fi
