#!/usr/bin/env bash
# Run the quick continuous integration gates before a push, all at once, and print one table.
#
# Roadmap step S-6.200. On September 25, 2026 two release pushes failed in continuous integration after twenty
# minutes on checks that nobody had run locally, and a third local run failed only because /tmp was over its
# quota. This script runs the gates of .github/workflows/ci.yml that need no browser and no container, in
# parallel, each with its own temporary folder under $HOME, and prints one table. It changes nothing in the
# tree. tools/test_ci_test_shards.py checks that every step of the workflow is either a gate here or is
# declined here with a reason, so the two cannot drift apart silently.
#
# Usage:  tools/pre_push_check.sh [--tree PATH] [--only gate,gate,...] [--list]
#   PY=/path/to/python   the interpreter with the project's extras (default: .venv/bin/python of the tree, then
#                        python3 on PATH)
#   --tree PATH          check that checkout instead of the one holding this script
#   --only a,b           run only the named gates (see --list)
# Every gate gets TMPDIR and RUNNER_TEMP under $HOME/.le-ci-tmp/pre-push/, never /tmp: on one development
# machine writes into /tmp silently produce empty files. Logs stay in that folder after the run.
# The hook template tools/git-hooks/pre-push runs this script; it explains how to install it in one checkout.
set -u

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ONLY=""
LIST=0
while [ $# -gt 0 ]; do
  case "$1" in
    --tree) ROOT="$(cd "$2" && pwd)"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --list) LIST=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
cd "$ROOT" || exit 2

PY="${PY:-$ROOT/.venv/bin/python}"
if [ ! -x "$PY" ]; then PY="$(command -v python3 || true)"; fi
if [ -z "$PY" ]; then echo "no Python found; set PY" >&2; exit 2; fi
VENV_BIN="$(cd "$(dirname "$PY")" && pwd)"
REVISION="$(git rev-parse --short HEAD 2>/dev/null || echo untracked)"
RUN="${HOME}/.le-ci-tmp/pre-push/${REVISION}-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN/tmp"
export TMPDIR="$RUN/tmp"
: > "$RUN/results.txt"
: > "$RUN/declined.txt"
STARTED=$(date +%s)

# The environment of every gate: this interpreter first on PATH, so that `python` in a step copied from the
# workflow is this one, then the caller's PATH, so that a tool found above (vale, lychee, node) is found in
# the gate too; and the tree's own source first on PYTHONPATH, so that a worktree checks itself and not the
# checkout the interpreter was installed from. A gate may put its own PYTHONPATH in front, as the workflow
# steps do. Nothing else of the caller's environment reaches a gate, so a local credential cannot turn a
# test into a live call.
GATE_PATH="$VENV_BIN:${PATH:-/usr/local/bin:/usr/bin:/bin}"

selected() { [ -z "$ONLY" ] || case ",$ONLY," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }

gate() {  # gate "local name" "workflow step name" command...
  local name="$1" step="$2"; shift 2
  if [ "$LIST" = 1 ]; then printf '  %-22s %s\n' "$name" "$step"; return 0; fi
  selected "$name" || return 0
  local tmp="$RUN/tmp-$name"; mkdir -p "$tmp"
  (
    started=$(date +%s)
    env -i PATH="$GATE_PATH" HOME="$HOME" LANG=C.UTF-8 TMPDIR="$tmp" RUNNER_TEMP="$tmp" \
        GITHUB_WORKSPACE="$ROOT" PYTHONPATH="$ROOT/src" "$@" > "$RUN/$name.log" 2>&1
    echo "$? $(( $(date +%s) - started )) $name" >> "$RUN/results.txt"
  ) &
}

skip() {  # skip "workflow step name" "reason"
  if [ "$LIST" = 1 ]; then printf '  %-22s %s (declined: %s)\n' "-" "$1" "$2"; return 0; fi
  echo "$1 | $2" >> "$RUN/declined.txt"
}

setup() {  # setup "workflow step name" command...   runs at once, before the gates, and stops the run if it fails
  local step="$1"; shift
  if [ "$LIST" = 1 ]; then printf '  %-22s %s (setup)\n' "-" "$step"; return 0; fi
  if ! "$@" > "$RUN/setup.log" 2>&1; then
    echo "setup failed: $step (log $RUN/setup.log)" >&2; exit 1
  fi
}

ci_block() {  # ci_block JOB "workflow step name": the path of a script holding that step's run text
  local job="$1" step="$2" file
  file="$RUN/step-$(printf '%s' "$step" | tr -c 'A-Za-z0-9' '-').sh"
  if ! "$PY" -c '
import sys, yaml
path, job, step = sys.argv[1:4]
with open(path, encoding="utf-8") as stream:
    data = yaml.safe_load(stream)
for item in data["jobs"][job]["steps"]:
    if item.get("name") == step:
        sys.stdout.write(item["run"])
        break
else:
    sys.exit("no step named %r in job %r" % (step, job))
' "$ROOT/.github/workflows/ci.yml" "$job" "$step" > "$file" 2> "$file.error"; then
    printf 'echo "%s"; exit 2\n' "the workflow step could not be extracted: $(cat "$file.error")" > "$file"
  elif ! "$PY" -m pip --version >/dev/null 2>&1; then
    # This interpreter has no pip module (a uv-managed environment). A step's `python -m pip install` line
    # names project dependencies that are already installed, so it is left out here rather than failing.
    sed -i 's/^\( *\)python -m pip install .*$/\1echo "pip is not available in this interpreter; the install line was left out"/' "$file"
  fi
  printf '%s' "$file"
}

# A step copied from the workflow runs the way GitHub runs it: bash with -e and pipefail, no profile.
STEP_SHELL=(bash --noprofile --norc -eo pipefail)

if [ "$LIST" = 0 ]; then
  setup "Install the report layout dependency" npm ci --prefix tools/architecture_report --ignore-scripts --no-audit --no-fund
fi

# The test-derived jobs of the workflow.
gate "self-test" "Self-test" env PYTHONPATH=src "$PY" -m loop_engine --self-test
gate "conformance" "Conformance gates" env PYTHONPATH=src "$PY" -m loop_engine --conformance
for shard in $("$PY" tools/run_test_shard.py --list | cut -d' ' -f1); do
  gate "tools-shard-$shard" "Development command and report regression checks" \
    env PYTHONPATH=src:tools "$PY" tools/run_test_shard.py --shard "$shard"
done
gate "site-map" "Served website matches its site map" env PYTHONPATH=src:tools "$PY" -m unittest tools/check_website_site_map.py
gate "component-guides" "Component guides match the source" env PYTHONPATH=src "$PY" tools/check_component_guides.py --run-documented-checks
gate "embodiment-lab" "Experimental embodiment qualification" env PYTHONPATH=src:devtools "$PY" -m unittest discover -s devtools/embodiment_lab/tests -v
gate "qualification-lab" "Independent component qualification lab" bash -c "cd devtools/qualification_lab && '$PY' -m unittest -v test_runner.py"
gate "devtools-and-hardcoding" "Self-orientation and hardcoding delta gates" bash -c "
  PYTHONPATH=src:devtools/src '$PY' -m loop_engine_devtools.cli --self-test &&
  PYTHONPATH=src:devtools/src '$PY' -m loop_engine_devtools.cli --hardcoding-audit \
    --allowlist devtools/hardcoding-allowlist.yaml --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high"
gate "examples" "Examples run" "${STEP_SHELL[@]}" "$(ci_block runtime-checks "Examples run")"
skip "Product solve acceptance" "pulls a container image and needs Docker; continuous integration runs it on every Python version"
skip "Default-install onboarding proof" "builds a wheel into a new environment; continuous integration runs it on Python 3.12"

# The documentation job.
if command -v node >/dev/null 2>&1; then
  gate "publish-guards" "Check the publication guards" "${STEP_SHELL[@]}" "$(ci_block docs "Check the publication guards")"
  gate "markdown" "Check Markdown structure" "${STEP_SHELL[@]}" "$(ci_block docs "Check Markdown structure")"
else
  skip "Check the publication guards" "node is not installed"
  skip "Check Markdown structure" "node is not installed"
fi
# Public language is checked on the Markdown files that differ from origin/main: the ones this push would
# change. The workflow's action lints its own file set, and a local vale of another version over every
# document reports dashes in dated files the action passes, which would hide a real failure in this table.
CHANGED_MARKDOWN=$( { git diff --name-only origin/main...HEAD -- '*.md'; git diff --name-only HEAD -- '*.md'; \
                      git ls-files --others --exclude-standard -- '*.md'; } 2>/dev/null | sort -u \
                    | grep -E '^(AGENTS|README|CHANGELOG|CONTRIBUTING|SECURITY|humanizer-context)\.md$|^showcase/README\.md$|^(docs|case-studies|examples)/' \
                    | while read -r path; do [ -f "$path" ] && printf '%s\n' "$path"; done | tr '\n' ' ')
if ! command -v vale >/dev/null 2>&1; then
  skip "Check public language" "vale is not installed; continuous integration runs it"
elif [ -n "$CHANGED_MARKDOWN" ]; then
  # shellcheck disable=SC2086
  gate "public-language" "Check public language" vale --config .vale.ini $CHANGED_MARKDOWN
else
  skip "Check public language" "no Markdown file differs from origin/main"
fi
if command -v rg >/dev/null 2>&1; then
  gate "retired-language" "Refuse retired public language" "${STEP_SHELL[@]}" "$(ci_block docs "Refuse retired public language")"
else
  skip "Refuse retired public language" "ripgrep is not installed; continuous integration runs it"
fi
if command -v lychee >/dev/null 2>&1; then
  gate "links" "Check local links and section anchors" lychee --offline --include-fragments --root-dir "$ROOT" \
    AGENTS.md README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md humanizer-context.md showcase/README.md 'docs/**/*.md' 'case-studies/*.md' 'examples/**/*.md'
else
  skip "Check local links and section anchors" "lychee is not installed; continuous integration runs it"
fi
gate "benchmark-registry" "Validate benchmark registry" "${STEP_SHELL[@]}" "$(ci_block docs "Validate benchmark registry")"
skip "Render current architecture diagrams" "needs a browser for the diagram renderer; continuous integration renders them"
skip "Verify interactive architecture and video" "the browser suite needs Chrome and the showcase server; run node tools/check_service_workspace.mjs on its own"

if [ "$LIST" = 1 ]; then exit 0; fi
wait

echo "Pre-push check of $REVISION in $RUN ($(( $(date +%s) - STARTED ))s wall)"
failed=0
while read -r code seconds name; do
  if [ "$code" = 0 ]; then
    printf '  pass  %5ss  %s\n' "$seconds" "$name"
  else
    printf '  FAIL  %5ss  %s  (exit %s, log %s)\n' "$seconds" "$name" "$code" "$RUN/$name.log"
    failed=1
    grep -E '^(FAILED |FAIL: |ERROR: )' "$RUN/$name.log" | head -5 | sed 's/^/          /'
  fi
done < <(sort -k3 "$RUN/results.txt")
while IFS='|' read -r step reason; do
  printf '  skip         %s: %s\n' "$(printf '%s' "$step" | sed 's/ *$//')" "$(printf '%s' "$reason" | sed 's/^ *//')"
done < "$RUN/declined.txt"
if grep -l "Disk quota exceeded\|No space left" "$RUN"/*.log >/dev/null 2>&1; then
  echo "  note  a log reports a full disk or quota: the failure may be the machine, not the change"
fi
exit "$failed"
