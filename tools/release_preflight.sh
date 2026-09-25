#!/usr/bin/env bash
# Run the checks continuous integration runs, locally and at once, before a push.
#
# Why: on September 25, 2026 two release pushes failed in CI after twenty minutes on checks that were never run
# locally (the self-test and the hardcoding allowlist's own validity), and a third local run failed only because
# /tmp was over its quota. This script runs the "test" job's gates in parallel, each with its own temporary folder
# under $HOME, plus the browser suite under the shared browser lock, and prints one table. It changes nothing.
#
# Usage: tools/release_preflight.sh [--quick]    (--quick skips the browser suite)
# Needs: a Python with the project's extras (PY, default .venv/bin/python) and showcase/node_modules for Chrome.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PY:-$ROOT/.venv/bin/python}"
RUN="${HOME}/.le-ci-tmp/preflight-$(git rev-parse --short HEAD)-$(date +%H%M%S)"
mkdir -p "$RUN"
QUICK=0; [ "${1:-}" = "--quick" ] && QUICK=1

gate() {  # name, command...
  local name="$1"; shift
  local tmp="$RUN/tmp-$name"; mkdir -p "$tmp"
  ( env TMPDIR="$tmp" "$@" > "$RUN/$name.log" 2>&1; echo "$? $name" >> "$RUN/results.txt" ) &
}

gate self-test env PYTHONPATH=src "$PY" -m loop_engine --self-test
gate conformance env PYTHONPATH=src "$PY" -m loop_engine --conformance
gate tools-suite env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" LANG=C.UTF-8 TMPDIR="$RUN/tmp-tools-suite" \
     PYTHONPATH=src:tools "$PY" -m unittest discover -s tools -p 'test_*.py'
gate served-site-map env PYTHONPATH=src:tools "$PY" -m unittest tools/check_website_site_map.py
gate component-guides env PYTHONPATH=src "$PY" tools/check_component_guides.py --run-documented-checks
gate devtools-self-test env PYTHONPATH=devtools/src "$PY" -m loop_engine_devtools.cli --self-test
gate hardcoding env PYTHONPATH=devtools/src "$PY" -m loop_engine_devtools.cli --hardcoding-audit \
     --allowlist devtools/hardcoding-allowlist.yaml --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high
gate qualification-lab bash -c "cd devtools/qualification_lab && '$PY' -m unittest test_runner.py"
if [ "$QUICK" = 0 ]; then
  gate browser flock -w 5400 "$HOME/.le-ci-tmp/browser.lock" env PYTHON="$PY" timeout 3000 \
       node tools/check_service_workspace.mjs "$RUN/browser-report.json"
fi
wait

echo "Preflight of $(git rev-parse --short HEAD) in $RUN"
failed=0
while read -r code name; do
  if [ "$code" = 0 ]; then echo "  pass  $name"; else echo "  FAIL  $name (exit $code, log $RUN/$name.log)"; failed=1; fi
done < <(sort -k2 "$RUN/results.txt")
if grep -l "Disk quota exceeded\|No space left" "$RUN"/*.log >/dev/null 2>&1; then
  echo "  note  a log reports a full disk or quota: the failure may be the machine, not the change"
fi
exit "$failed"
