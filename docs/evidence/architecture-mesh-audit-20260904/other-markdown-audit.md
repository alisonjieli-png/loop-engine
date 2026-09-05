# Loop Engine Markdown audit outside docs

Read-only semantic review of every Markdown file outside `docs/` in the exact corpus recorded at `/tmp/loop-engine-architecture-audit.UBvdFH/files.jsonl`.

Coverage: **109 files, 6942 lines, fully read**. This includes the ignored `example-output/incident-report/report.md` because the supplied corpus included it. The core README and the first part of the root README had already been read in earlier audit work; their full reading is included here.

At completion, SHA-256 checks of all 109 paths matched the supplied corpus manifest (exit status 0). This binds the covered Markdown bytes to that manifest. It does not establish behavioral correctness, preserve a complete dirty source snapshot, or qualify the runtime. No repository files were edited and no historical instructions, demonstrations, provider calls, downloads, or benchmark reruns were executed. Only this temporary report was written.

## Material findings

| ID | Exact evidence | Finding and implication |
|---|---|---|
| O01 | `SECURITY.md:20`, `:26` | Security guidance says the only outbound requests are chat and model-catalog reads, and no provider configuration means no network calls. Current Web Research, Brave, MCP transport setup, Kaggle and explicitly authorized network capabilities make those statements too broad. Security documentation should enumerate authority-controlled network boundaries rather than equate network availability with provider credentials. |
| O02 | `CONTRIBUTING.md:54` | Claims identical model-arm and zero-model-arm artifacts mean the model never reached the result. This is an invalid causal inference: different executed paths can produce identical correct output. Artifact identity alone cannot prove treatment exposure or contribution; trace and action lineage are required. |
| O03 | `CONTRIBUTING.md:21`, `:24`, `:27` | Current contributor guidance names retired `static_architecture/*_client.py` paths and hand-copies event-family and module-size figures. The adapter path is definitely stale. Counts and caps must resolve from current machine authority; this sub-audit did not re-run those gate populations, so it does not independently declare the numeric figures wrong. |
| O04 | `examples/README.md:3`, `examples/02_predict_customer_renewal/README.md:6`, `pyproject.toml:27`, `examples/02_predict_customer_renewal/run.py:13` | Examples describe a bare main-archive install as the complete package and use it for data examples. Base dependencies are PyYAML/jsonschema/tomli; NumPy, pandas and sklearn are in extras. Customer-renewal imports NumPy/pandas directly. A fresh base installation does not provide that example's declared environment. The current root README correctly explains lightweight base versus data/all extras. |
| O05 | `checkpoints/README.md:3`, `:27`; `tools/make_checkpoint.py:27`, `:45`, `:81`, `:99` | The checkpoint guide claims exact reconstruction of entire system state. The script records branch, HEAD and status without dirty contents or a full worktree digest; its tree is tracked filenames, and conformance output is truncated to its last 2,000 characters. It advertises `conformance.json` in the generated SNAPSHOT but never writes that file. Its exit status depends only on self-test success, not conformance. These are concrete source/documentation mismatches; the script was inspected, not run. |
| O06 | `src/loop_engine/runtime/README.md:26`, `runtime/artifacts/README.md:27`, `runtime/runs/README.md:27`, `runtime/runtime_memory/README.md:27` | Local README contracts under the installed source tree permit "Run output written by the runtime." This conflicts with current policy placing mutable run state outside installed package roots. The contracts should describe conceptual ownership/reference locations; this audit did not observe runtime files being written there. |
| O07 | `src/loop_engine/kernel/resolver/README.md:9` | Names `loop.builtin_resolvers` as a current owner. That module is absent from the current Loop package. The README is a stale ownership map, even though it correctly says the folder adds no executor. |
| O08 | `src/loop_engine/node/README.md:98` | Lists `core.loop_profile.configuration_provider@1.0.0`, record_lookup, validator, transform and composite as common versioned profiles. Those exact IDs are absent from the current executable profile catalog and source/structured registrations searched. They should be labeled illustrative historical presets or mapped to exact registered profiles. |
| O09 | `kaggle/README.md:103`, `:104` | Inspection commands use `/kaggle/working/loop-engine-logs/run-history`, while the current layout documented in the same file is `/kaggle/working/loop-engine/logs/run-history`. Commands point at the retired layout. |
| O10 | `kaggle/README.md:30` | Says the cell runs against any attached competition/dataset regardless of layout. Open intake of arbitrary paths is not support for arbitrary modalities or submission contracts. Current qualification and narrow executor documents explicitly defer/refuse unsupported archives, modalities, multi-output and table shapes. Reword as path-layout-independent intake with bounded execution support. |
| O11 | `examples/21_schema_org_data_standardization/README.md:27`; `run.py:300`, `:330`, `:385` | Claims validation with SHACL shapes. `_shacl_shapes()` emits a Turtle string, but the actual path calls hand-written `_validate_shacl()` checks that do not consume the shapes. The declared name datatype constraint is not checked. This demonstrates a narrow Python validation approximation, not an executed SHACL validation engine or standards conformance. |
| O12 | `CHANGELOG.md:415` | One unreleased entry says it maps all 28 transitions, then reports 18 realized plus 13 unrealized. The census is internally inconsistent. This does not establish the current transition count; use the live registry plus a dated result. |
| O13 | `CHANGELOG.md:636`, `:642`; `src/loop_engine/core/model_gateway.py:740`, `:761` | Changelog explicitly endorses shrinking an implicitly selected model output maximum to fit a route window. This is in tension with the current AGENTS requirement to request the exact source-backed maximum. Source contains that implicit-ceiling adjustment. Root should reconcile the authoritative policy and implementation rather than merely edit the historical explanation. This audit did not make a provider call. |
| O14 | `src/loop_engine/strings/SEED-DIMENSIONS.md:9` | Says generated strings remain candidates until they win on real tasks. A useful outcome is evidence for independent review, not sufficient promotion authority. This incomplete description should retain the explicit independent qualification/promotion boundary. It is not proof that code currently auto-promotes candidates. |

## Important distinctions preserved by these files

- The root README separates open task intake from supported physical capabilities and says unsupported work returns typed blockers. It labels current stage assistance as an injected, mechanism-only fixture with unresolved controls.
- Benchmark and case-study documents preserve the invalidated DS-1000 2/4 score and distinguish a zero-new-call regrade of exact saved outputs from a fresh live provider run.
- OpenML case-study accounting preserves unknown usage for failed calls and distinguishes valid artifacts/scores from quality acceptance. Its three-task denominator does not establish broad performance.
- Historical case studies may correctly describe a nine-step run from their own frozen revision. Those records must not be mechanically rewritten to ten steps simply because the current reference profile grew.
- SciFact explicitly excludes its deterministic diagnostic from selected model-led campaign evidence. Candidate methods and final evaluation all use the same 300 judged test queries, so these results do not establish held-out method-selection generalization.
- N-gram and model-routing benchmarks explicitly label synthetic populations and refuse live quality/cost interpretations. The n-gram report preserves its false split.
- The 120-competition Kaggle report carefully distinguishes metadata access, source qualification and task scoring. It states that no source in the three-candidate source-qualification canary became QUALIFIED.
- Example 12 uses fixture bodies for its million-line/9-GB representation; its README says no repository clone or dataset load occurred. It proves reference handling, not actual large-corpus performance.
- The four-memory demonstration is a scripted deterministic two-run scenario. Its existence does not demonstrate general learned transfer, automatic public-product memory integration, or model-quality gain.
- Integration skill files are thin CLI instructions. Their names and presence do not establish automatic installation, an extra runtime, or authority to run a provider.
- Development Assurance is described as an application on the same engine. Its README explicitly distinguishes warning-only three-parameter migration findings from strict mode.
- Packaged SKILL.md files were read as repository data for this audit. They were not adopted as instructions governing the audit.
- Product-proof Markdown files contain tiny fixture outputs and source documents. Their presence alone does not prove the associated run succeeded; valid claims need the exact saved result and event evidence.
- Showcase documentation distinguishes editable source from generated exports and says media is incomplete until matching exports succeed. No browser/media verification was performed here.

## Coverage method and limits

All Markdown in the supplied outside-docs subset was read in full, including repeated generated folder contracts, changelog, fixture outputs and SKILL.md files. Source checks were targeted and read-only: `tools/make_checkpoint.py` and the customer-renewal example were read fully; `pyproject.toml`, profile catalog/ontology, Schema.org example, and model gateway were sampled or text-searched. This is not a full semantic audit of those Python modules. Referenced external pages, standard specifications and benchmark datasets were not fetched.

The exact per-file hashes remain in the supplied corpus manifest. The following coverage table lists every path and the manifest's line count. Core README was fully read in the prior component pass and is included without double-counting it as new work.

## Exact full-reading coverage

| Path | Lines | Coverage |
|---|---:|---|
| `AGENTS.md` | 367 | full |
| `CHANGELOG.md` | 1204 | full |
| `CONTRIBUTING.md` | 66 | full |
| `README.md` | 352 | full |
| `SECURITY.md` | 35 | full |
| `artifacts/product-proof/acceptance/task-a-workspace/attempt-1/report.md` | 4 | full |
| `artifacts/product-proof/acceptance/task-b-workspace/attempt-1/summary.md` | 5 | full |
| `artifacts/product-proof/acceptance/task-c-workspace/attempt-1/index.md` | 17 | full |
| `artifacts/product-proof/acceptance/task-c-workspace/attempt-1/inputs/docs/alpha.md` | 7 | full |
| `artifacts/product-proof/acceptance/task-c-workspace/attempt-1/inputs/docs/beta.md` | 7 | full |
| `artifacts/product-proof/cli/dataset-workspace/attempt-1/summary.md` | 5 | full |
| `artifacts/product-proof/cli/workspace-from-file/attempt-1/report.md` | 4 | full |
| `artifacts/product-proof/cli/workspace/attempt-1/report.md` | 4 | full |
| `benchmarks/beir_scifact/README.md` | 126 | full |
| `benchmarks/capability-scenarios/README.md` | 66 | full |
| `benchmarks/ds1000/README.md` | 95 | full |
| `benchmarks/kaggle_competitions/README.md` | 196 | full |
| `benchmarks/model-routing/README.md` | 52 | full |
| `benchmarks/ngram-retrieval/README.md` | 97 | full |
| `benchmarks/openml_cc18/README.md` | 41 | full |
| `case-studies/README.md` | 44 | full |
| `case-studies/TEMPLATE.md` | 40 | full |
| `case-studies/ds1000-four-task-recorded-output-correction.md` | 147 | full |
| `case-studies/openml-cc18-three-task-run.md` | 126 | full |
| `checkpoints/2026-08-26-pre-five-step/SNAPSHOT.md` | 14 | full |
| `checkpoints/README.md` | 28 | full |
| `devtools/README.md` | 83 | full |
| `devtools/qualification_lab/README.md` | 63 | full |
| `devtools/src/loop_engine_devtools/intelligence/core/README.md` | 16 | full |
| `example-output/incident-report/report.md` | 43 | full |
| `examples/01_prioritize_support_queue/README.md` | 20 | full |
| `examples/02_predict_customer_renewal/README.md` | 19 | full |
| `examples/03_connect_a_model/README.md` | 20 | full |
| `examples/04_read_run_reports/README.md` | 19 | full |
| `examples/05_kaggle_competition/README.md` | 29 | full |
| `examples/06_reconcile_invoices/README.md` | 19 | full |
| `examples/07_watch_a_run_live/README.md` | 23 | full |
| `examples/08_play_back_a_saved_run/README.md` | 22 | full |
| `examples/09_search_the_intelligence_layers/README.md` | 23 | full |
| `examples/10_validate_customer_import/README.md` | 33 | full |
| `examples/11_seed_space_context/README.md` | 58 | full |
| `examples/12_wrap_a_large_codebase/README.md` | 27 | full |
| `examples/13_brave_search_plugin/README.md` | 37 | full |
| `examples/14_five_problem_campaign/README.md` | 29 | full |
| `examples/15_verify_a_deployment_profile/README.md` | 64 | full |
| `examples/16_compare_complex_harnesses/README.md` | 70 | full |
| `examples/17_classify_harness_files/README.md` | 38 | full |
| `examples/18_three_model_ensemble/README.md` | 22 | full |
| `examples/19_four_memory_demonstration/README.md` | 20 | full |
| `examples/20_compile_text_tasks/README.md` | 64 | full |
| `examples/21_schema_org_data_standardization/README.md` | 31 | full |
| `examples/22_product_quickstart/README.md` | 18 | full |
| `examples/22_product_quickstart/fixtures/docs/alpha.md` | 7 | full |
| `examples/22_product_quickstart/fixtures/docs/beta.md` | 7 | full |
| `examples/23_drop_in_extensions/README.md` | 48 | full |
| `examples/23_drop_in_extensions/example_extension/skills/summary-skill/SKILL.md` | 10 | full |
| `examples/23_drop_in_extensions/provider_templates/README.md` | 22 | full |
| `examples/README.md` | 69 | full |
| `examples/tasks/README.md` | 100 | full |
| `humanizer-context.md` | 112 | full |
| `integrations/README.md` | 15 | full |
| `integrations/claude-code/skills/loop-engine-inspect/SKILL.md` | 10 | full |
| `integrations/claude-code/skills/loop-engine-run/SKILL.md` | 12 | full |
| `integrations/claude-code/skills/loop-engine-setup/SKILL.md` | 12 | full |
| `integrations/codex/plugins/loop-engine/skills/loop-engine-inspect/SKILL.md` | 15 | full |
| `integrations/codex/plugins/loop-engine/skills/loop-engine-run/SKILL.md` | 18 | full |
| `integrations/codex/plugins/loop-engine/skills/loop-engine-setup/SKILL.md` | 19 | full |
| `kaggle/README.md` | 252 | full |
| `showcase/README.md` | 106 | full |
| `src/loop_engine/ARCHITECTURE-MAP.md` | 44 | full |
| `src/loop_engine/catalog/README.md` | 27 | full |
| `src/loop_engine/core/README.md` | 22 | full |
| `src/loop_engine/governance/README.md` | 40 | full |
| `src/loop_engine/governance/approval/README.md` | 41 | full |
| `src/loop_engine/governance/candidates/README.md` | 41 | full |
| `src/loop_engine/governance/promotion/README.md` | 41 | full |
| `src/loop_engine/governance/review/README.md` | 41 | full |
| `src/loop_engine/intelligence/README.md` | 40 | full |
| `src/loop_engine/intelligence/code/README.md` | 41 | full |
| `src/loop_engine/intelligence/code/core/README.md` | 44 | full |
| `src/loop_engine/intelligence/code/learned/README.md` | 44 | full |
| `src/loop_engine/intelligence/code/plugin/README.md` | 44 | full |
| `src/loop_engine/intelligence/context/README.md` | 41 | full |
| `src/loop_engine/intelligence/context/core/README.md` | 49 | full |
| `src/loop_engine/intelligence/context/learned/README.md` | 44 | full |
| `src/loop_engine/intelligence/context/plugin/README.md` | 44 | full |
| `src/loop_engine/intelligence/runtime_history_solution/README.md` | 41 | full |
| `src/loop_engine/intelligence/runtime_history_solution/core/README.md` | 44 | full |
| `src/loop_engine/intelligence/runtime_history_solution/learned/README.md` | 44 | full |
| `src/loop_engine/intelligence/runtime_history_solution/plugin/README.md` | 44 | full |
| `src/loop_engine/intelligence/user_feedback/README.md` | 41 | full |
| `src/loop_engine/intelligence/user_feedback/core/README.md` | 44 | full |
| `src/loop_engine/intelligence/user_feedback/learned/README.md` | 44 | full |
| `src/loop_engine/intelligence/user_feedback/plugin/README.md` | 44 | full |
| `src/loop_engine/kernel/README.md` | 40 | full |
| `src/loop_engine/kernel/enforcement/README.md` | 41 | full |
| `src/loop_engine/kernel/executor/README.md` | 41 | full |
| `src/loop_engine/kernel/loader/README.md` | 41 | full |
| `src/loop_engine/kernel/resolver/README.md` | 41 | full |
| `src/loop_engine/node/README.md` | 115 | full |
| `src/loop_engine/node/loop_node/README.md` | 14 | full |
| `src/loop_engine/ontology/README.md` | 104 | full |
| `src/loop_engine/runtime/README.md` | 40 | full |
| `src/loop_engine/runtime/artifacts/README.md` | 41 | full |
| `src/loop_engine/runtime/runs/README.md` | 41 | full |
| `src/loop_engine/runtime/runtime_memory/README.md` | 41 | full |
| `src/loop_engine/skills/README.md` | 5 | full |
| `src/loop_engine/skills/software-tdd-red-green-refactor/SKILL.md` | 27 | full |
| `src/loop_engine/strings/SEED-DIMENSIONS.md` | 383 | full |
