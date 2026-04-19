#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="$ROOT_DIR/data/results/pipeline-run"
LOG_FILE="$RUN_DIR/pipeline.log"
STATUS_FILE="$RUN_DIR/status.env"
PID_FILE="$RUN_DIR/pipeline.pid"

MODE="foreground"
BACKEND="hybrid"
INPUT_CSV="data/input/test_skus.csv"

usage() {
  cat <<'EOF'
Usage: scripts/run_backend_full_pipeline.sh [--background] [--backend BACKEND] [--input CSV]

Runs the backend pipeline end to end:
1. Non-live pytest suite
2. Live retrieval smoke tests
3. Live evaluation on the assignment SKU CSV

Artifacts:
- data/results/pipeline-run/pipeline.log
- data/results/pipeline-run/status.env
- data/results/live-evaluation.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --background)
      MODE="background"
      shift
      ;;
    --backend)
      BACKEND="${2:-}"
      shift 2
      ;;
    --input)
      INPUT_CSV="${2:-}"
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

mkdir -p "$RUN_DIR"

write_status() {
  local stage="$1"
  local state="$2"
  local message="$3"
  {
    printf 'STAGE=%q\n' "$stage"
    printf 'STATE=%q\n' "$state"
    printf 'MESSAGE=%q\n' "$message"
    printf 'UPDATED_AT=%q\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    printf 'BACKEND=%q\n' "$BACKEND"
    printf 'INPUT_CSV=%q\n' "$INPUT_CSV"
    printf 'LOG_FILE=%q\n' "$LOG_FILE"
    printf 'PID_FILE=%q\n' "$PID_FILE"
  } >"$STATUS_FILE"
}

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "Missing $label: $path" >&2
    exit 1
  fi
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Required command not found: $cmd" >&2
    exit 1
  fi
}

run_stage() {
  local stage="$1"
  shift
  write_status "$stage" "running" "Running $stage"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] START $stage"
  "$@"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] DONE  $stage"
}

run_live_stage() {
  local stage="$1"
  shift
  write_status "$stage" "running" "Running $stage"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] START $stage"
  /bin/zsh -lc "set -a; source .env >/dev/null 2>&1; set +a; $*"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] DONE  $stage"
}

pipeline_main() {
  trap 'write_status "${CURRENT_STAGE:-bootstrap}" "failed" "Pipeline failed at ${CURRENT_STAGE:-bootstrap}"' ERR

  export PYTHONUNBUFFERED=1

  require_file ".venv/bin/python" "virtualenv python"
  require_file "$INPUT_CSV" "input CSV"
  require_file ".env" "environment file"
  require_command /bin/zsh

  : >"$LOG_FILE"
  echo "$$" >"$PID_FILE"
  write_status "bootstrap" "running" "Initialized backend pipeline run"

  CURRENT_STAGE="pytest_non_live"
  run_stage "$CURRENT_STAGE" /bin/zsh -lc ".venv/bin/python -m pytest backend/tests -q -m 'not live'"

  CURRENT_STAGE="pytest_live_retrieval"
  run_live_stage "$CURRENT_STAGE" ".venv/bin/python -m pytest backend/tests/test_live_retrieval.py -q"

  CURRENT_STAGE="evaluate_live_${BACKEND}"
  run_live_stage "$CURRENT_STAGE" ".venv/bin/python -m backend.app.cli evaluate-live --input '$INPUT_CSV' --backend '$BACKEND' --output data/results/live-evaluation.json"

  CURRENT_STAGE="completed"
  write_status "$CURRENT_STAGE" "completed" "Backend pipeline completed successfully"
  rm -f "$PID_FILE"
}

if [[ "$MODE" == "background" ]]; then
  nohup bash "$0" --backend "$BACKEND" --input "$INPUT_CSV" >"$LOG_FILE" 2>&1 < /dev/null &
  bg_pid=$!
  echo "Started background pipeline PID $bg_pid"
  echo "Log: $LOG_FILE"
  echo "Status: $STATUS_FILE"
  exit 0
fi

pipeline_main 2>&1 | tee -a "$LOG_FILE"
