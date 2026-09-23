#!/usr/bin/env bash
# Run the main plan unattended.
#
#   runner/overnight.sh RUN_FOLDER [extra runner options]
#
# The supervisor restarts the runner after a crash and stops when the runner
# reports that the plan is complete (0), that the budget cannot hold another
# step (3), that a provider outage outlasted the declared wait (4), or that
# the provider key is missing (5). Every start and stop is written to
# RUN_FOLDER/supervisor.log. It never asks for input.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
run_folder="$1"
shift
restart_wait_seconds="${OVERNIGHT_RESTART_WAIT_SECONDS:-30}"
max_restarts=5
restarts=0
mkdir -p "$run_folder"
log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$run_folder/supervisor.log"
}
log "supervisor $$ started"
while true; do
  log "starting the runner (restart $restarts of at most $max_restarts)"
  python3 "$here/run_trials.py" main --run-folder "$run_folder" "$@"
  code=$?
  case "$code" in
    0|3|4|5)
      log "runner ended with code $code; supervisor stops"
      exit "$code"
      ;;
  esac
  restarts=$((restarts + 1))
  log "runner ended with code $code"
  if [ "$restarts" -gt "$max_restarts" ]; then
    log "too many restarts; supervisor stops"
    exit 1
  fi
  sleep "$restart_wait_seconds"
done
