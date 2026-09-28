#!/usr/bin/env bash
# Run the quick continuous integration gates before a push, all at once, and print one table.
#
# Roadmap step S-6.200. On September 25, 2026 two release pushes failed in continuous integration after twenty
# minutes on checks that nobody had run locally, and a third local run failed only because /tmp was over its
# quota. This script runs the gates of .github/workflows/ci.yml that need no browser and no container, in
# parallel, each with its own temporary folder under $HOME, and prints one table. The conformance gate rewrites
# src/loop_engine/architecture_conformance.json; when the tree was clean at the start, HEAD's copy is put back after
# the gates, so a run leaves a clean tree clean.
# tools/test_ci_test_shards.py checks that every step of the workflow is either a gate here or is declined here with a
# reason, so the two cannot drift apart silently. One local gate checks what the workflow cannot: the pristine check
# exports HEAD and regenerates every generated view there (tools/regenerate_all.py --pristine), because the working
# tree is not what is pushed. The last line says NOT EQUIVALENT TO CI whenever anything the workflow runs did not run
# here (tools/pre_push_summary.py), and a gate that exits 127 is reported as a missing command, not a code failure.
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

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
only=""
listing=0
while [ $# -gt 0 ]; do
  case "$1" in
    --tree) root="$(cd "$2" && pwd)"; shift 2 ;;
    --only) only="$2"; shift 2 ;;
    --list) listing=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
cd "$root" || exit 2

# The interpreter: PY when set, else the tree's .venv, else the .venv of the checkout that holds the tree's
# repository (a worktree has none of its own; this is how a worktree finds the project's dependencies), else python3
# on PATH, which may lack them. That last case is reported as a gap of the run, because a step can then fail on a
# missing module, which is the machine and not the change.
PY="${PY:-$root/.venv/bin/python}"
python_fallback=""
if [ ! -x "$PY" ]; then
  common="$(git -C "$root" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  if [ -n "$common" ] && [ -x "$(dirname "$common")/.venv/bin/python" ]; then
    PY="$(dirname "$common")/.venv/bin/python"
  else
    PY="$(command -v python3 || true)"
    python_fallback="$PY"
  fi
fi
if [ -z "$PY" ]; then echo "no Python found; set PY" >&2; exit 2; fi
venv_bin="$(cd "$(dirname "$PY")" && pwd)"
revision="$(git rev-parse --short HEAD 2>/dev/null || echo untracked)"
run_folder="${HOME}/.le-ci-tmp/pre-push/${revision}-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$run_folder/tmp"
export TMPDIR="$run_folder/tmp"
: > "$run_folder/results.txt"
: > "$run_folder/environment.txt"
if [ -n "$python_fallback" ]; then
  echo "PY is not set and no .venv was found, so the gates ran on $python_fallback, which may lack the project's dependencies" \
    >> "$run_folder/environment.txt"
fi
: > "$run_folder/declined.txt"
: > "$run_folder/local.txt"
run_started=$(date +%s)
# Whether the tree differs from HEAD when the run starts: the gates then check files a push would not send.
dirty=0
if [ -n "$(git -C "$root" status --porcelain 2>/dev/null)" ]; then dirty=1; fi
python_version="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo unknown)"

# The steps copied from the workflow call `python`, as the workflow's runner provides it. A machine may have only
# python3, and a tree without .venv falls back to it, so every copied step failed with exit 127 there (train 4,
# September 27, 2026). A small folder of this run holds `python` and `python3` that run this interpreter, and it comes
# first on every gate's path. Each is a script that runs the interpreter by its full path rather than a link, so a
# virtual environment still finds its own packages.
shim="$run_folder/bin"
mkdir -p "$shim"
for name in python python3; do
  printf '#!/bin/sh\nexec "%s" "$@"\n' "$PY" > "$shim/$name"
  chmod +x "$shim/$name"
done

# The environment of every gate: the shim folder and this interpreter's folder first on PATH, so that `python` in a
# step copied from the workflow is this one, then the caller's PATH, so that a tool found above (vale, lychee, node) is
# found in
# the gate too; and the tree's own source first on PYTHONPATH, so that a worktree checks itself and not the
# checkout the interpreter was installed from. A gate may put its own PYTHONPATH in front, as the workflow
# steps do. Nothing else of the caller's environment reaches a gate, so a local credential cannot turn a
# test into a live call.
gate_path="$shim:$venv_bin:${PATH:-/usr/local/bin:/usr/bin:/bin}"

selected() { [ -z "$only" ] || case ",$only," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }

gate() {  # gate "local name" "workflow step name" command...
  local name="$1" step="$2"; shift 2
  if [ "$listing" = 1 ]; then printf '  %-22s %s\n' "$name" "$step"; return 0; fi
  selected "$name" || return 0
  start_gate "$name" "$@"
}

start_gate() {  # start_gate "local name" command...: run it in the background and record one result row
  local name="$1"; shift
  local tmp="$run_folder/tmp-$name"; mkdir -p "$tmp"
  (
    started=$(date +%s)
    env -i PATH="$gate_path" HOME="$HOME" LANG=C.UTF-8 TMPDIR="$tmp" RUNNER_TEMP="$tmp" \
        GITHUB_WORKSPACE="$root" PYTHONPATH="$root/src" "$@" > "$run_folder/$name.log" 2>&1
    echo "$? $(( $(date +%s) - started )) $name" >> "$run_folder/results.txt"
  ) &
}

local_gate() {  # local_gate "local name" "what it checks" command...: a gate the workflow does not run
  local name="$1" what="$2"; shift 2
  if [ "$listing" = 1 ]; then printf '  %-22s %s (local only)\n' "$name" "$what"; return 0; fi
  selected "$name" || return 0
  echo "$name" >> "$run_folder/local.txt"
  start_gate "$name" "$@"
}

skip() {  # skip "workflow step name" "reason"
  if [ "$listing" = 1 ]; then printf '  %-22s %s (declined: %s)\n' "-" "$1" "$2"; return 0; fi
  echo "$1 | $2" >> "$run_folder/declined.txt"
}

setup() {  # setup "workflow step name" command...   runs at once, before the gates, and stops the run if it fails
  local step="$1"; shift
  if [ "$listing" = 1 ]; then printf '  %-22s %s (setup)\n' "-" "$step"; return 0; fi
  if ! "$@" > "$run_folder/setup.log" 2>&1; then
    echo "setup failed: $step (log $run_folder/setup.log)" >&2; exit 1
  fi
}

system_managed() {  # the interpreter is the system's own, which refuses pip installs (PEP 668)
  "$PY" -c 'import os, sys, sysconfig
sys.exit(0 if sys.prefix == sys.base_prefix and os.path.isfile(os.path.join(sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED")) else 1)' \
    2>/dev/null
}

ci_block() {  # ci_block JOB "workflow step name": the path of a script holding that step's run text
  local job="$1" step="$2" file
  file="$run_folder/step-$(printf '%s' "$step" | tr -c 'A-Za-z0-9' '-').sh"
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
' "$root/.github/workflows/ci.yml" "$job" "$step" > "$file" 2> "$file.error"; then
    printf 'echo "%s"; exit 2\n' "the workflow step could not be extracted: $(cat "$file.error")" > "$file"
  elif ! "$PY" -m pip --version >/dev/null 2>&1 || system_managed; then
    # This interpreter has no pip module (a uv-managed environment), or the system manages it and refuses installs
    # (PEP 668). A step's `python -m pip install` line names project dependencies the workflow's runner installs;
    # a pre-push check does not install into the interpreter it was given, so the line is left out here.
    sed -i 's/^\( *\)python -m pip install .*$/\1echo "the install line was left out: this interpreter has no pip or the system manages it"/' "$file"
  fi
  printf '%s' "$file"
}

# A step copied from the workflow runs the way GitHub runs it: bash with -e and pipefail, no profile.
step_shell=(bash --noprofile --norc -eo pipefail)

# Only the tools shards need the report layout dependency; the workflow installs it in their job alone.
shard_selected() { [ -z "$only" ] || case ",$only," in *",tools-shard-"*) return 0 ;; *) return 1 ;; esac; }
if [ "$listing" = 1 ] || shard_selected; then
  setup "Install the report layout dependency" npm ci --prefix tools/architecture_report --ignore-scripts --no-audit --no-fund
fi

# The test-derived jobs of the workflow.
gate "self-test" "Self-test" env PYTHONPATH=src "$PY" -m loop_engine --self-test
gate "conformance" "Conformance gates" env PYTHONPATH=src "$PY" -m loop_engine --conformance
# The pristine check: HEAD exported into .le-ci-tmp/pristine in the home folder (git archive, never the working tree),
# every generated view regenerated there by the export's own builders, and a failure when anything differs from the
# commit.
# Release train 2 of September 27, 2026 passed here and failed in continuous integration: the status pages were current
# in the working tree only. When the tree is clean and the conformance gate runs, that gate writes the conformance
# manifest from the same bytes, so the export leaves out its slowest view and the manifest is compared with HEAD after
# the gates (the pristine-manifest row).
manifest_path="src/loop_engine/architecture_conformance.json"
pristine_arguments=(--pristine)
manifest_by_conformance=0
if [ "$listing" = 0 ] && [ "$dirty" = 0 ] && selected conformance && selected pristine-tree; then
  pristine_arguments+=(--skip conformance-manifest)
  manifest_by_conformance=1
fi
local_gate "pristine-tree" "HEAD exported, every generated view regenerated there, nothing differs from the commit" \
  env PYTHONPATH=src:tools "$PY" tools/regenerate_all.py "${pristine_arguments[@]}"
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
gate "examples" "Examples run" "${step_shell[@]}" "$(ci_block runtime-checks "Examples run")"
skip "Product solve acceptance" "continuous integration only: pulls a container image and needs Docker, on every Python version"
skip "Default-install onboarding proof" "continuous integration only: builds a wheel into a new environment on Python 3.12"

# The documentation job.
if command -v node >/dev/null 2>&1; then
  gate "publish-guards" "Check the publication guards" "${step_shell[@]}" "$(ci_block docs "Check the publication guards")"
  gate "markdown" "Check Markdown structure" "${step_shell[@]}" "$(ci_block docs "Check Markdown structure")"
else
  skip "Check the publication guards" "node is not installed"
  skip "Check Markdown structure" "node is not installed"
fi
# Public language is checked on the Markdown files that differ from origin/main: the ones this push would
# change. The workflow's action lints its own file set, and a local vale of another version over every
# document reports dashes in dated files the action passes, which would hide a real failure in this table.
changed_markdown=$( { git diff --name-only origin/main...HEAD -- '*.md'; git diff --name-only HEAD -- '*.md'; \
                      git ls-files --others --exclude-standard -- '*.md'; } 2>/dev/null | sort -u \
                    | grep -E '^(AGENTS|README|CHANGELOG|CONTRIBUTING|SECURITY|humanizer-context)\.md$|^showcase/README\.md$|^(docs|case-studies|examples)/' \
                    | while read -r path; do [ -f "$path" ] && printf '%s\n' "$path"; done | tr '\n' ' ')
if ! command -v vale >/dev/null 2>&1; then
  skip "Check public language" "vale is not installed; continuous integration runs it"
elif [ -n "$changed_markdown" ]; then
  # shellcheck disable=SC2086
  gate "public-language" "Check public language" vale --config .vale.ini $changed_markdown
else
  skip "Check public language" "nothing to check: no Markdown file differs from origin/main"
fi
if command -v rg >/dev/null 2>&1; then
  gate "retired-language" "Refuse retired public language" "${step_shell[@]}" "$(ci_block docs "Refuse retired public language")"
else
  skip "Refuse retired public language" "ripgrep is not installed; continuous integration runs it"
fi
if command -v lychee >/dev/null 2>&1; then
  gate "links" "Check local links and section anchors" lychee --offline --include-fragments --root-dir "$root" \
    AGENTS.md README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md humanizer-context.md showcase/README.md 'docs/**/*.md' 'case-studies/*.md' 'examples/**/*.md'
else
  skip "Check local links and section anchors" "lychee is not installed; continuous integration runs it"
fi
gate "benchmark-registry" "Validate benchmark registry" "${step_shell[@]}" "$(ci_block docs "Validate benchmark registry")"
skip "Render current architecture diagrams" "continuous integration only: the diagram renderer needs a browser"
skip "Verify interactive architecture and video" "continuous integration only: the browser suite needs Chrome and the showcase server; run node tools/check_service_workspace.mjs on its own"

if [ "$listing" = 1 ]; then
  printf '  %-22s %s (local only)\n' "pristine-manifest" \
    "the conformance manifest the conformance gate wrote from a clean tree equals HEAD's"
  exit 0
fi
wait

if [ "$manifest_by_conformance" = 1 ]; then
  echo "pristine-manifest" >> "$run_folder/local.txt"
  if git diff --quiet HEAD -- "$manifest_path" > "$run_folder/pristine-manifest.log" 2>&1; then
    echo "0 0 pristine-manifest" >> "$run_folder/results.txt"
  else
    { echo "The conformance gate wrote a manifest that differs from HEAD's: the committed $manifest_path is stale."
      echo "Continuous integration does not compare it. Regenerate it with: python tools/regenerate_all.py"
      git diff --stat HEAD -- "$manifest_path"; } >> "$run_folder/pristine-manifest.log" 2>&1
    echo "1 0 pristine-manifest" >> "$run_folder/results.txt"
  fi
  # The tree was clean when the run started: leave it clean.
  git show "HEAD:$manifest_path" > "$manifest_path"
fi

echo "Pre-push check of $revision in $run_folder ($(( $(date +%s) - run_started ))s wall)"
summary_options=(--only "$only" --python "$python_version" --workflow "$root/.github/workflows/ci.yml")
if [ "$dirty" = 1 ]; then summary_options+=(--dirty); fi
"$PY" "$root/tools/pre_push_summary.py" "$run_folder" "${summary_options[@]}"
status=$?
if grep -l "Disk quota exceeded\|No space left" "$run_folder"/*.log >/dev/null 2>&1; then
  echo "  note  a log reports a full disk or quota: the failure may be the machine, not the change"
fi
exit "$status"
