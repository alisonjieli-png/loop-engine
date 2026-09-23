#!/usr/bin/env bash
# Run the CI command set on an export of one exact revision, stages in parallel.
set -u
REV=${1:?revision}
REPO=/home/username/loop-engine
PY=${PY_OVERRIDE:-$REPO/.venv/bin/python}
OUT=/home/username/.le-ci-export/$REV
LOGS=/tmp/claude-1000/-home-username-loop-engine/81df4e9e-adbc-4fcf-9636-2fadc680611e/scratchpad/ci-$REV
git -C $REPO worktree remove --force "$OUT" 2>/dev/null; rm -rf "$OUT" "$LOGS"; mkdir -p "$LOGS"
git -C $REPO worktree add --detach "$OUT" "$REV" >/dev/null 2>&1 || exit 3
cd "$OUT"
export RUNNER_TEMP=$OUT/.runner-temp; mkdir -p "$RUNNER_TEMP"
export HOME_TMP=/home/username/.le-ci-tmp; mkdir -p "$HOME_TMP"; export TMPDIR=$HOME_TMP
[ -d $REPO/tools/architecture_report/node_modules ] && ln -s $REPO/tools/architecture_report/node_modules tools/architecture_report/node_modules 2>/dev/null
[ -d $REPO/showcase/node_modules ] && ln -s $REPO/showcase/node_modules showcase/node_modules 2>/dev/null
ln -s "$(dirname "$(dirname "$PY")")" .venv 2>/dev/null
run() { name=$1; shift; ( start=$(date +%s); "$@" > "$LOGS/$name.log" 2>&1; rc=$?; echo "$name exit=$rc seconds=$(( $(date +%s) - start ))" >> "$LOGS/SUMMARY" ) & }
run guard node tools/check_publish_guard.mjs
run mdlint npx --yes markdownlint-cli2@0.23.2 AGENTS.md README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md humanizer-context.md showcase/README.md 'docs/**/*.md' 'case-studies/*.md' 'examples/**/*.md'
run retired bash -c "! rg --hidden -n -i --glob '!src/loop_engine/forbidden_paths.json' --glob '!docs/prompts/**' --glob '!docs/evidence/**' --glob '!docs/verification/**' --glob '!showcase/node_modules/**' --glob '!**/.cache/**' '\bchronicles?\b|\breceipts?\b' README.md CHANGELOG.md humanizer-context.md docs examples case-studies benchmarks showcase && ! rg --hidden -n -i --glob '!docs/prompts/**' --glob '!docs/evidence/**' --glob '!docs/verification/**' --glob '!showcase/assets/**' --glob '!showcase/node_modules/**' --glob '!**/.cache/**' '\bchild(?:ren)?\b|\broot[[:space:]_-]+loop\b|what[[:space:]_-]*is[[:space:]_-]*next|what[[:space:]_-]+next|whats[[:space:]_-]*next|whatnext' README.md CHANGELOG.md humanizer-context.md docs examples case-studies showcase"
run selftest env PYTHONPATH=src $PY -m loop_engine --self-test
run conformance env PYTHONPATH=src $PY -m loop_engine --conformance
run embodiment env PYTHONPATH=src:devtools $PY -m unittest discover -s devtools/embodiment_lab/tests
run tools env PYTHONPATH=src:tools $PY -m unittest discover -s tools -p 'test_*.py'
run guides env PYTHONPATH=src $PY tools/check_component_guides.py --run-documented-checks
run hardcoding bash -c "PYTHONPATH=devtools/src $PY -m loop_engine_devtools.cli --self-test && PYTHONPATH=devtools/src $PY -m loop_engine_devtools.cli --hardcoding-audit --allowlist devtools/hardcoding-allowlist.yaml --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high"
run qualification bash -c "cd devtools/qualification_lab && PYTHONPATH=$OUT/src $PY -m unittest test_runner.py"
run examples bash -c 'set -e; export PYTHONPATH=src; for e in 01_prioritize_support_queue 02_predict_customer_renewal 03_connect_a_model 04_read_run_reports 06_reconcile_invoices 08_play_back_a_saved_run 09_search_the_intelligence_layers 10_validate_customer_import 11_seed_space_context 12_wrap_a_large_codebase 13_brave_search_plugin 14_five_problem_campaign 15_verify_a_deployment_profile 16_compare_complex_harnesses 17_classify_harness_files 18_three_model_ensemble 19_four_memory_demonstration 20_compile_text_tasks 21_schema_org_data_standardization 23_drop_in_extensions 26_export_a_standalone_solution 27_optimize_a_node_grid 28_containerized_worker 30_overnight_local_run; do echo "== $e"; '"$PY"' examples/$e/run.py > /dev/null || { echo "FAILED $e"; exit 1; }; done'
run browser bash -c "PYTHON='$PY' node tools/check_service_workspace.mjs /home/username/.le-ci-tmp/browser-$REV-$$.json"
wait
echo "ALL DONE" >> "$LOGS/SUMMARY"
