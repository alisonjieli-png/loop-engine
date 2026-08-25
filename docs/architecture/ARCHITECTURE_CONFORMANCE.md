# Architecture Conformance — final proof (2026-08-23)

The maximal-conformance reset's acceptance surface, each gate marked exactly
**PASS / FAIL / NOT RUN / BLOCKED** — a NOT RUN is never presented as a pass.
Machine manifest: `architecture_conformance.json` (regenerate:
`PYTHONPATH=. python3 -m loop_engine --conformance`,
exit 0 = all zero-tolerance gates hold; identical from the installed
wheel: `python -m loop_engine --conformance`). Suite: **683/683, 0 skips**
(baseline at reset start: 573, 0 skips) — the suite grew, never shrank, and
the scanner fails on any skip/xfail marker in the conformance suites.

## Gate table

| Gate | Verdict | Evidence |
|---|---|---|
| One canonical recursive runtime (`PractitionerLoop is Loop`; `run_to_completion is run`) | **PASS** | `_conformance_test` in suite |
| 12 zero-tolerance gates (unclassified files, legacy runtimes, legacy imports, network/subprocess bypass, eval/exec, secrets incl. receipts, dynamic-import bypass, kimi-k3, placeholders, stale docs, skip markers) | **PASS** | `architecture_conformance.json`; `--conformance` exit 0 |
| Scanner detectors canary-proven (each fires on a planted invalid fixture) | **PASS** | `_conformance_scan.self_test` in suite |
| Nine-step is a template, not a mandate; a custom loop runs a materially different order | **PASS** | build_test_repair (8 steps, act-first) in suite |
| Candidate templates cannot run until admitted | **PASS** | `loop_templates` tests |
| LoopSpec initialize fail-closed + digest; pause→JSON→resume; cancel; honest partials | **PASS** | `recursive_loop` tests 15–19 |
| §12: ≤1 semantic call/iteration; semantic fallback defers as a visible model boundary | **PASS** | suite + smoke receipts |
| Child permission clamp; MAX adds no permissions; recursion bomb bounded; budget not evadable | **PASS** | adversarial tests |
| Closure audit: orphaned children flagged; every terminal transition recorded | **PASS** | adversarial test |
| Parent → child → grandchild spawn, return, integrate (lineage + depths on one ledger) | **PASS** | `_conformance_test` |
| Facet search: require / prefer / exclude incl. locality + job_position lens | **PASS** | directory tests 10b–10e |
| Smoke stage 0 (deterministic fixture, zero calls, in-suite) | **PASS** | `smoke_ladder.self_test` |
| Smoke Titanic: real cloud call (provider tokens), real submission | **PASS** | `evidence/smoke-titanic-loop-20260823.json` (public 0.76794) |
| Warm-run growth gates (fewer calls / not worse / more code-served) | **PASS** | same receipt |
| Flywheel full cycle: mine real ledgers → stage → gate refuses evidence-free → promote through gate → later run retrieves the REGISTERED resource | **PASS** | `evidence/flywheel-promotion-20260823.json` |
| Improvement lane self-promotion refused (SafeguardError, exercised live) | **PASS** | same receipt |
| Legacy assimilation (body-free inventory → wrap candidates, never executed) | **PASS** | `evidence/loop-canary-C-20260823.json` |
| Mode canaries: code_only / hybrid / model_led all exercised on real runs | **PASS** | stage 0 / Titanic cold / canary A |
| Loop emits its artifact as a SolutionSpec (searchable String next to the receipt) | **PASS** | smoke lane `act` step; `mode-portfolio` receipt carries each arm's spec |
| Mode portfolio (deterministic-only / hybrid / model-led on the same task + oracle) | **PASS** | `evidence/mode-portfolio-titanic-20260823.json` — CV 0.8294@0 calls / 0.8294@1 / 0.8339@1 (one run each; smoke, not statistics) |
| In-graph ModelActionRequest pause inside composite code nodes (§12 full protocol) | **NOT RUN** | loop-iteration-level deferral only |
| Smoke stage 2 (current Playground Series episode) | **PASS** | `evidence/smoke-playground-s6e8-20260823.json` — 691K rows; cold 1 call / 77s, REAL submission public **0.95663** (beats the prior zero-model route 0.93098; under the old from-scratch control 0.96094); warm 0 calls; CORRECTED: the template's constant-0.7094 float column had ALREADY steered the lane to probabilities — the resubmission was byte-identical (0.95663 again), falsifying the hard-labels hypothesis and proving end-to-end determinism; the lane now quotes OOF ROC-AUC (0.9559) instead of a proxy |
| Smoke stage 3 (advanced active competition through child-loop decomposition) | **NOT RUN** | — |
| Full CodeNodeManifest on every live code node (§6.1) | **NOT RUN** | facets slice only |
| Guidance Ledger full state vocabulary + skip receipts (§11) | **NOT RUN** | `bias_checklist` is the seed |
| Loop-tree rich HTML/JSON report (§7.6) | **NOT RUN** | `LoopLedger.tree()` + receipts exist; the rendered report does not |
| Action ontology axes (§8.2) as search keys | **NOT RUN** | — |
| The 13-document authoring-guide set (§22) | **NOT RUN** | report/ledger/conformance docs exist; authoring guides do not |
| **Clean-wheel canary** (Canary A of the companion): `pip install loop_engine*.whl` in a clean venv → `python -m loop_engine --self-test` 683/683 + `--conformance` exit 0, cwd outside the repo; CLI `loop-engine` works | **PASS** | pyproject.toml; the canary EXPOSED + fixed 8 cross-component imports (five stdlib leaves vendored with provenance); new scanner rule `cross_component_import` keeps the boundary closed |
| **Canary C** file/DuckDB catalog equivalence — same top identities, identical bodies, digest-refused tampering; DB holds references+digests, files stay authoritative | **PASS** | `static_architecture/duckdb_catalog.py` (in suite; `database` extra) |
| Solution compiler: fail-closed compile, content-addressed plan digest, select_best + gating_router, Canvas rendered (Mermaid+JSON) from one canonical dict | **PASS** | `code_nodes/solution_compiler.py` (in suite) |
| Builder/solution separation (Canary D): model-led builder shipped a deterministic SolutionSpec | **PASS** | smoke lane act step + mode-portfolio receipt |
| PyPI publication / Trusted Publishing / entry-point plugin packs (Canary B) / OCI packs | **NOT RUN** | release workflows deliberately not created; never publish without authorization |
| Function-length / parameter-count / catch-all-name detectors (§21 remainder) | **NOT RUN** | module-size + docstring detectors exist; the rest specified for next session |

## Honest quality statement

The live smoke's public score (0.76794) is BELOW the repository's 0.778
zero-model lane and far below its own 0.8316 CV — the small-data overfit gap.
The flywheel's measurable improvement is **model-call substitution (1 → 0) at
equal local quality**; no quality gain is claimed. Playground smoke is never
benchmark evidence; real active competitions remain the evidence bar.

## Next (ranked by expected downstream impact)

1. §21 remainder detectors (function length, parameter count, catch-all
   names) + the entry-point plugin canary (Canary B).
3. In-graph ModelActionRequest pause (extend §12 into composite code nodes).
4. CodeNodeManifest slice for the ten most-used code nodes, scanner-enforced.
5. The loop-tree rendered report + Guidance Ledger state vocabulary.

## Dated addendum (2026-08-24)

Counts above are the 2026-08-23 reset snapshot; the count below rots
by design — always recompute. At the 2026-08-24 hygiene sweep:
**765/765** (recompute with the command in the header). Gates added
since, all PASS in-suite: retrieval engine backends (FTS5 default +
model2vec semantic canary with measured margins;
`evidence/retrieval-engine-tournament-20260823.json`), Chronicle native
emission from the root Loop (`enable_chronicle`), and universal
encapsulation (`loop/encapsulate.py` — deterministic checks run as
PractitionerLoops; positive, child-spawn, raising-evidence, and
settings-pin tests). Design authority docs registered:
DESIGN-LANGUAGE.md, CLAUDE-DESIGN-PROMPT.md.
