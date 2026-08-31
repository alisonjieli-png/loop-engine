# Reusable Capability Flywheel implementation ledger

Date: 2026-08-31

This ledger covers every path changed in the working tree for this
implementation turn. The final source full suite passed 1,617 of 1,617 checks.
The corrected Python 3.10 wheel passed 1,588 of 1,588 installed checks. Both
runs made zero provider calls. The focused flywheel slice passed 33 of 33
checks. The transactional semantic runtime slice passed 16 of 16 checks.

## Flywheel, fallback, and public integration

| Path | Purpose and key symbols | Why it belongs there | Verification |
|---|---|---|---|
| `src/loop_engine/core/reusable_capability_records.py` | Adds `CapabilityNeed`, `ReuseOpportunityObserved`, complete `ReuseAssessment`, `CapabilityGeneralizationRecord`, hybrid profiles, resolution plans, and invocation records. | Passive cross-stage contracts belong in Core, not in a new runtime. | Flywheel 33/33; source and wheel full suites. |
| `src/loop_engine/core/reusable_capability_flywheel.py` | Adds catalog-backed `CapabilityAuthority`, candidate registration, exact qualification, promotion, rejection, rollback, and lifecycle transitions. | It extends the existing catalog and Code Intelligence authorities. | Flywheel 33/33; boundary and conformance checks. |
| `src/loop_engine/core/reusable_capability_harvest.py` | Adds observation, reactive dispatch, the shared async/inline assessment and generalization pipeline, and source-to-candidate lineage. | Harvest execution is separate from lifecycle authority and every stage remains a Loop. | Async worker and inline parity checks. |
| `src/loop_engine/core/reusable_capability_resolution.py` | Rebuilds projections, enforces hard eligibility, resolves exact capabilities, invokes them, and verifies outputs. | Resolution and invocation are separate from lifecycle mutation. | Warm zero-model proof; projection rebuild proof; full suites. |
| `src/loop_engine/core/reusable_capability_hybrid.py` | Loads named profiles and runs one bounded structured hybrid operation. | Hybrid variations remain data under the existing hybrid mode. | Normalization, adapter, repair, and reranker checks. |
| `src/loop_engine/core/reusable_capability_checks.py` | Runs the cold-to-warm, source-to-generalized, async, inline, trust, restart, Practitioner integration, duplicate, repair, rejection, rollback, and quarantine fixture. | Focused verification is separate from production contracts. | 33/33 focused checks; collected by the full suite. |
| `src/loop_engine/core/adaptive_practitioner_reuse.py` | Adds `observe_generated_project_reuse()` for verified generated-project completion. | Public solve integration stays a small post-completion helper. | Public observation port and observer-failure checks. |
| `src/loop_engine/core/code_intelligence_assets.py` | Adds `CodeAssetAdmissionRecord`, exact proof digests, serialization, lifecycle states, and `admit_code_asset()`. | Code Intelligence already owns executable asset identity. | 8/8 Code Intelligence checks; full suites. |
| `src/loop_engine/core/adaptive_practitioner.py` | Calls the optional reuse observation helper after verified generated-project completion. | The source Practitioner owns the accepted result and artifact references. | Adaptive Practitioner 29/29; full suites. |
| `src/loop_engine/core/adaptive_practitioner_records.py` | Adds the typed optional `ReuseObservationPort` dependency. | Runtime dependencies are declared in the existing cohesive dependency contract. | Adaptive Practitioner 29/29; parameter and conformance gates. |
| `src/loop_engine/data/reusable_capability_hybrid_profiles.yaml` | Stores seven versioned hybrid assistance presets. | Semantic policy stays in package data rather than Python branches. | Profile load and exact stage checks; clean-wheel resource check. |
| `src/loop_engine/data/practitioner_context_fallback.yaml` | Stores the minimum outage question and guidance portfolio. | Basic degraded behavior stays separate from active Context Intelligence. | Practitioner context 10/10; clean-wheel resource check. |
| `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | Stores the full Practitioner question, persona, guidance, and prompt portfolio. | The main semantic portfolio belongs in Context Intelligence. | Practitioner context 10/10; ontology and clean-wheel checks. |
| `src/loop_engine/data/practitioner_context_intelligence.yaml` | Removed after moving its content to Context Intelligence. | Prevents two authoritative copies of the same portfolio. | Ontology index and clean-wheel resource checks. |
| `src/loop_engine/core/practitioner_context.py` | Adds explicit availability and fallback policy, a source-and-degradation load record, and model-candidate portfolio access. | Loading and validation remain at the existing Practitioner context boundary. | 10/10 focused checks; full suites. |
| `src/loop_engine/intelligence/context/core/manifest.yaml` | Registers the moved full Practitioner portfolio and exact digest. | The existing Core Context collection owns its manifest. | Ontology checks; clean-wheel checks. |
| `src/loop_engine/intelligence/context/core/README.md` | Explains the active portfolio and separate fallback. | The semantic folder contract documents its own contents. | Ontology README checks; public prose review. |
| `src/loop_engine/core/boundary_registry.py` | Registers nine new operational boundaries with exact role profiles. | Every new operation must remain inside the canonical Loop ontology. | Boundary 8/8; zero unregistered boundaries. |
| `src/loop_engine/__init__.py` | Exports the curated flywheel, admission, resolution, and hybrid contracts. | Public contracts use the existing lazy API surface. | Import smoke; clean-wheel focused and full suites. |
| `src/loop_engine/_self_test.py` | Collects `reusable_capability_checks`. | The full suite must not silently omit a new self-test. | Uncollected-test conformance gate passed. |
| `architecture.yaml` | Adds the normative flywheel authorities and invariants. | Root architecture remains the repository authority. | Architecture contract and conformance passed. |
| `src/loop_engine/data/architecture.yaml` | Mirrors the install-time architecture projection. | Installed checks need the same authority without a checkout. | Root and package files match; clean-wheel conformance passed. |
| `src/loop_engine/architecture_map.py` | Registers the flywheel, semantic runtime, evidence, state, fixture, and check modules under Core. | The architecture map is the module ownership authority. | Architecture map checks passed. |
| `src/loop_engine/ARCHITECTURE-MAP.md` | Regenerates the reader-facing module map. | Generated current architecture must match code. | Architecture freshness gate passed. |
| `src/loop_engine/ontology/index.json` | Regenerates the catalog ontology after the Context manifest change. | It is a disposable generated index over authoritative manifests. | Ontology live-tree check passed. |
| `src/loop_engine/architecture_conformance.json` | Stores the fresh zero-tolerance conformance result. | The package ships the current machine-readable gate result. | Every listed gate passed. |
| `artifacts/verification/reusable_capability_flywheel_results.json` | Stores exact local metrics, promoted digests, projection identity, build hashes, and limitations. | Machine-readable verification belongs under artifacts. | Parsed as JSON; values copied from fresh runs. |

## Transactional semantic runtime

| Path | Purpose and key symbols | Why it belongs there | Verification |
|---|---|---|---|
| `src/loop_engine/core/semantic_runtime_records.py` | Adds `SemanticLoopContract`, `SemanticInterpreterProfile`, realization bindings, candidates, proposed deltas, verification, authorization, ProgramID, commit, and execution records. | The Semantic ABI is passive data bound to the canonical Loop definition. | Round-trip, identity, trust-transition, and full-suite checks. |
| `src/loop_engine/core/semantic_runtime_evidence.py` | Adds fixture-scoped reliability envelopes and five-strategy benchmark records. | Measured evidence remains separate from runtime authority and model confidence. | Semantic 16/16. |
| `src/loop_engine/core/semantic_state.py` | Adds issued verifier and effect records plus catalog-backed compare-and-swap trusted state. | Existing `CatalogStore` remains the physical state authority; the model never writes it. | Idempotency, stale-state, abstention, and unsafe-effect checks. |
| `src/loop_engine/core/semantic_runtime.py` | Binds semantic specifications into exact `LoopDefinition` facts, selects qualified realizations, and executes the candidate-to-commit transaction through canonical Loops. | It extends the one runtime instead of adding a semantic function kernel. | Semantic 16/16; boundary and architecture gates. |
| `src/loop_engine/core/semantic_runtime_fixture.py` | Defines the implementationless policy-routing contract, reviewed context, two interpreter fixtures, deterministic realization, and independent verifier. | Test-specific semantics stay outside the generic runtime. | Routing, missing-fact, injection, requalification, and materialization checks. |
| `src/loop_engine/core/semantic_runtime_checks.py` | Runs implementationless execution, trust-state, ProgramID, requalification, materialization, fallback, reliability, and five-strategy proofs. | Focused evidence is separate from production contracts. | 16/16 focused checks; collected by the full suite. |
| `artifacts/verification/semantic_runtime_results.json` | Stores exact contract, ProgramID, execution record, reliability, materialization, strategy, and Run History results. | Machine-readable local evidence belongs under artifacts. | Parsed as JSON and generated from the focused suite. |
| `docs/architecture/ADR-TRANSACTIONAL-SEMANTIC-RUNTIME.md` | Records canonical binding, trust transition, ProgramID, realization, and materialization decisions. | The change extends several architecture authorities and needs one decision record. | Compared with live symbols and focused results. |
| `docs/components/loop-object/SEMANTIC-RUNTIME.md` | Explains the current semantic contract, transaction, context, routing fixture, materialization, and evidence limits. | Semantic execution is a Loop behavior, not another Intelligence layer or runtime. | Public prose and link review. |
| `docs/verification/SEMANTIC-RUNTIME-EVALUATION.md` | Reports exact focused, strategy, source, wheel, and limitation evidence. | Measured results remain separate from design. | Values copied from final machine-readable runs. |

## Architecture, research, and operating documentation

| Path | Purpose and key sections | Why it belongs there | Verification |
|---|---|---|---|
| `docs/architecture/ADR-REUSABLE-CAPABILITY-FLYWHEEL.md` | Records the lifecycle, authority, storage, mode, fallback, and rejected alternatives. | The change joins several existing architectural boundaries. | Compared with live symbols; public prose review. |
| `docs/architecture/REUSABLE-CAPABILITY-AUTHORITY-AND-RESEARCH.md` | Maps repository authority and synthesizes ten primary research sources. | The mandate requires repository and prior-art reconciliation. | Source links verified; path and symbol audit. |
| `docs/components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md` | Documents contracts, search, async flow, hybrid profiles, trust, and limits. | Reusable capabilities connect Code Intelligence and Runtime History. | Compared with the 20-check vertical slice. |
| `docs/verification/REUSABLE-CAPABILITY-FLYWHEEL-EVALUATION.md` | Reports commands, totals, exact trace IDs, metrics, clean wheel, and limits. | Verification evidence is separate from design. | Values copied from final source and wheel runs. |
| `docs/verification/REUSABLE-CAPABILITY-FLYWHEEL-IMPLEMENTATION-LEDGER.md` | Lists every changed path, purpose, ownership, and test. | The mandate requires a complete handoff ledger. | Checked against `git status --short`. |
| `docs/components/intelligence-layers/README.md` | Links the new flywheel guide. | The intelligence-layer index should expose the feature. | Link and Markdown check through full suite packaging. |
| `docs/contracts/README.md` | Adds Code admission, lifecycle, resolution, invocation, and hybrid rows. | The contract map points to current Python authorities. | Link and symbol review. |
| `README.md` | Adds the async candidate and warm zero-model reuse behavior. | First-time users need a short current-behavior summary. | Humanizer guidance; clean-wheel metadata build. |
| `CHANGELOG.md` | Adds flywheel and Context outage fallback entries. | Both are release-visible behavior changes. | Public prose review. |
| `pyproject.toml` | Adds the Python 3.10 `tomli` fallback to base dependencies. | The base full suite imports the fallback module on Python versions without `tomllib`. | Clean Python 3.10 wheel full suite passed after rebuild. |

## Semantic-selection and implicit-limit cleanup completed in the same turn

| Path | Purpose | Verification |
|---|---|---|
| `docs/guides/llm-first-universal-solver.md` | Explains that models select semantic candidates while code enforces contracts. | Full suite; public prose review. |
| `docs/architecture/SEMANTIC-IDENTITY-DICTIONARY.md` | Regenerates the semantic dictionary view. | Semantic projection freshness passed. |
| `terminology.yaml` | Adds the model-selected intelligence candidate concept. | Semantic conformance passed. |
| `src/loop_engine/data/terminology.yaml` | Mirrors terminology for installations. | Architecture contract passed. |
| `src/loop_engine/data/semantic_data_dictionary.yaml` | Regenerates the install-time semantic projection. | Semantic projection passed. |
| `src/loop_engine/forbidden_paths.json` | Expands semantic-default and module-size enforcement fields. | Zero-tolerance conformance passed. |
| `src/loop_engine/semantic_freedom_conformance.py` | Scans task-literal branches and semantic numeric defaults across the package. | Live tree returned zero findings. |
| `src/loop_engine/core/intelligence_portfolio.py` | Separates discovery from explicit model selection and removes heuristic winner authority. | Intelligence portfolio 11/11; full suites. |
| `src/loop_engine/core/intelligence_portfolio_checks.py` | Adds positive and adversarial model-selection checks. | Focused checks passed. |
| `src/loop_engine/core/adaptive_practitioner_orientation.py` | Removes deterministic semantic rewriting and reports contradictions for model repair. | Adaptive Practitioner 29/29. |
| `src/loop_engine/core/adaptive_practitioner_acceptance_checks.py` | Proves conflicting semantic output is rejected and repaired by the model path. | Adaptive Practitioner 29/29. |
| `src/loop_engine/core/adaptive_practitioner_recovery.py` | Validates model-produced recovery routes instead of mapping them in code. | Adaptive recovery checks in full suite. |
| `src/loop_engine/core/adaptive_practitioner_verification.py` | Preserves model route decisions while blocking unsafe success. | Adaptive verification checks passed. |
| `src/loop_engine/core/adaptive_practitioner_records.py` | Supplies complete persona, guidance, and question candidate sets to the model. | Adaptive and context checks passed. |
| `src/loop_engine/core/adaptive_practitioner.py` | Removes preselected semantic defaults and uses the model-selected path. | Adaptive Practitioner 29/29. |
| `src/loop_engine/code_nodes/solution_records.py` | Requires explicit semantic candidate selection after deterministic eligibility. | Solution record checks passed. |
| `src/loop_engine/core/asset_class.py` | Requires an explicit implementation handle instead of choosing one by fallback order. | Asset-class checks in full suite. |
| `src/loop_engine/generation/model/campaign.py` | Makes campaign ceilings optional and requires an installed exact-enumeration strategy. | Generation model checks passed. |
| `src/loop_engine/generation/operators.py` | Updates generation operator verification for the explicit strategy. | Generation operator checks passed. |
| `src/loop_engine/code_nodes/context_seed.py` | Removes invented project, task, source, and depth defaults. | Context seed checks passed. |
| `src/loop_engine/code_nodes/housekeeping.py` | Removes an implicit improvement-pass ceiling. | Housekeeping checks passed. |
| `src/loop_engine/code_nodes/self_improvement_loop.py` | Makes history and review bounds optional policy inputs. | Self-improvement checks passed. |
| `src/loop_engine/strings/question_engine.py` | Makes question multiplication unbounded unless a caller supplies a limit. | Question engine checks passed. |
| `src/loop_engine/loop/encapsulate.py` | Stops forcing a fixed top-five Intelligence result window. | Encapsulation checks passed. |
| `src/loop_engine/loop/intelligence_loops.py` | Propagates optional search limits through Intelligence Loops. | Intelligence Loop checks passed. |
| `src/loop_engine/core/capability_directory.py` | Makes capability search size optional. | Capability directory checks passed. |
| `src/loop_engine/core/duckdb_catalog.py` | Removes an implicit query result window. | DuckDB checks passed when adapter was installed. |
| `src/loop_engine/core/intelligence_layers.py` | Preserves an unset Intelligence search limit. | Intelligence layer checks passed. |
| `src/loop_engine/core/ngram_retrieval.py` | Makes n-gram result limits explicit and optional. | N-gram checks passed. |
| `src/loop_engine/core/retrieval.py` | Propagates optional result limits through the retrieval interface. | Retrieval checks passed. |
| `src/loop_engine/core/runtime_settings.py` | Changes retrieval and history ceilings to optional values. | Runtime settings checks passed. |
| `src/loop_engine/core/settings_loader.py` | Preserves absent optional limits instead of inventing them. | Settings loader checks passed. |
| `src/loop_engine/core/skill_registry.py` | Makes skill search size optional. | Skill registry checks passed. |
| `src/loop_engine/core/store_serve.py` | Makes store search size optional. | Store checks passed. |
| `src/loop_engine/catalog/query.py` | Makes catalog query limit optional. | Catalog query checks passed. |
| `src/loop_engine/catalog/composite.py` | Preserves optional limits when merging stores. | Composite catalog checks passed. |
| `src/loop_engine/catalog/stores/in_memory.py` | Supports an unset limit in the reference store. | Catalog conformance passed. |
| `src/loop_engine/catalog/stores/package_jsonl.py` | Supports an unset limit in packaged JSONL search. | Catalog conformance passed. |
| `src/loop_engine/catalog/stores/sqlite_store.py` | Omits SQL limit clauses when no limit is supplied. | Catalog conformance passed. |
| `src/loop_engine/catalog/stores/duckdb_files.py` | Omits DuckDB limit clauses when no limit is supplied. | Catalog conformance passed. |
| `src/loop_engine/catalog/stores/duckdb_store.py` | Omits DuckDB store limit clauses when no limit is supplied. | Catalog conformance passed. |

## Final commands

```bash
.venv/bin/python -m loop_engine --self-test
.venv/bin/python -m loop_engine --conformance
.venv/bin/python -m loop_engine --repo-conformance --format json
git diff --check
```

Clean-wheel verification built both archives in a temporary directory,
installed the wheel outside the repository, checked four required package
resources, ran the 33-check flywheel slice and 16-check semantic slice, ran the
1,588-check installed suite, and ran installed conformance. The final wheel
SHA-256 is
`958af7ede3c4e76700f640ddd9de9435a4f75bf5cab757c0480cfc188bd96c31`.
