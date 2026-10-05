#!/usr/bin/env bash
# One scheduled pass of the query multiplier, from the pinned checkout this file sits in.
#
# The systemd user unit that install_schedule.py writes runs this script; it caps the pass at MemoryMax=4G. The
# pass writes only under its private root (default ~/baltor-library/query-runs) and keeps its live status in
# <root>/state/status.json. A file <root>/state/pause makes every pass exit at once without disabling the timer;
# a file <root>/state/stop ends a running pass after its current requests.
set -euo pipefail
here="$(cd "$(dirname "$0")/../.." && pwd)"
root="${QUERY_MULTIPLIER_ROOT:-$HOME/baltor-library/query-runs}"
if [ "${1:-}" = "--finish" ]; then
  # ExecStopPost: systemd's own verdict, which a pass cannot write itself when a timeout or the memory cap
  # killed it. One record in state/last-unit-result.json and one line appended to state/unit-history.jsonl.
  mkdir -p "$root/state"
  revision="$(cat "$here/REVISION" 2>/dev/null || echo unknown)"
  line="$(printf '{"record_type": "research_query_unit_result/v1", "finished_at": "%s", "service_result": "%s", "exit_code": "%s", "exit_status": "%s", "revision": "%s"}' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${SERVICE_RESULT:-unknown}" "${EXIT_CODE:-unknown}" "${EXIT_STATUS:-unknown}" "$revision")"
  printf '%s\n' "$line" > "$root/state/last-unit-result.json"
  printf '%s\n' "$line" >> "$root/state/unit-history.jsonl"
  exit 0
fi
minutes="${QUERY_MULTIPLIER_MINUTES:-20}"
python="${QUERY_MULTIPLIER_PYTHON:-$HOME/loop-engine/.venv/bin/python}"
if [ -z "${OLLAMA_API_KEY:-}" ] && [ -f "$HOME/.bashrc" ]; then
  # The owner's existing Ollama key is exported in ~/.bashrc, which returns early for shells that are not
  # interactive. Read that one export line only, never the rest of the file, and never print it. Without it the
  # web search lane refuses with key_not_in_environment and every other lane runs.
  line="$(grep -E '^export OLLAMA_API_KEY=' "$HOME/.bashrc" | tail -n 1 || true)"
  if [ -n "$line" ]; then eval "$line"; fi
fi
if [ -e "$root/state/pause" ]; then
  printf '{"status": "paused", "pause_file": "%s"}\n' "$root/state/pause"
  exit 0
fi
cd "$here"
export PYTHONPATH=src:tools PYTHONDONTWRITEBYTECODE=1
exec "$python" tools/run_query_multiplier.py run --root "$root" --minutes "$minutes" \
  --authorize-network-reads --authorize-local-writes
