# Codex 5.6 Max execution ledger

This is the durable resume point for the current Loop Engine completion
campaign. It records observed evidence, accepted work, exact blockers, and
checkpoint state. A file being present does not make its checkpoint complete.

## Campaign identity

| Field | Value |
|---|---|
| Repository | `alisonjieli-png/loop-engine` |
| Local path | `/home/username/loop-engine` |
| Canonical branch | `main` |
| Starting SHA | `6a26978c5e6cd2e3852818c4bb4b2dac23b0da76` |
| Starting `origin/main` | `6a26978c5e6cd2e3852818c4bb4b2dac23b0da76` |
| Started | `2026-08-27` |
| Current campaign state | `NOT YET PROVEN` |
| Current workflow | `CI` run `33081066312` |
| Workflow result | `failure` in public documentation |
| Commit made by this ledger task | none |
| Push made by this ledger task | none |

## Resume protocol

At the start of a resumed session:

1. Read this ledger and the two architecture registers.
2. Fetch `main` and tags when network access is authorized.
3. Inspect branch, revision, status, active work, and concurrent ownership.
4. Read the latest GitHub Actions run and failed logs.
5. Resume the earliest incomplete hard checkpoint.
6. Update the machine-readable checkpoint and command records with exact
   evidence.

Do not restart architecture design from zero. Do not assume a concurrent edit
is accepted merely because it exists.

## Starting repository evidence

The first repository check found:

- top level: `/home/username/loop-engine`;
- branch: `main`;
- `HEAD`: `6a26978c5e6cd2e3852818c4bb4b2dac23b0da76`;
- `origin/main`: the same SHA;
- remote: `https://github.com/alisonjieli-png/loop-engine.git`;
- one architecture tag: `v0.9.0-architecture`; and
- an inherited non-clean worktree.

The initial read-only diff summary observed 44 tracked modified paths and two
untracked source paths. A later refresh at `2026-08-27T13:28:13-04:00`
observed 46 tracked modified paths and the same two untracked paths. That
increase is concurrent work. None of these paths was attributed to this ledger
task.

### Inherited and concurrent paths at the refresh

```text
.github/workflows/ci.yml
.vale.ini
AGENTS.md
architecture.yaml
benchmarks/capability-scenarios/README.md
benchmarks/capability-scenarios/catalog.json
docs/architecture/CONSTITUTION.md
docs/architecture/CURRENT-ARCHITECTURE-MAP.md
docs/architecture/GLOSSARY.md
examples/18_three_model_ensemble/README.md
examples/18_three_model_ensemble/run.py
examples/README.md
src/loop_engine/__main__.py
src/loop_engine/_self_test.py
src/loop_engine/architecture_conformance.json
src/loop_engine/architecture_contract.py
src/loop_engine/architecture_map.py
src/loop_engine/code_nodes/solution_canvas.py
src/loop_engine/code_nodes/solution_canvas_checks.py
src/loop_engine/code_nodes/solution_compiler.py
src/loop_engine/code_nodes/solution_graph.py
src/loop_engine/code_nodes/solution_graph_builder.py
src/loop_engine/code_nodes/solution_graph_checks.py
src/loop_engine/core/custom_endpoint.py
src/loop_engine/core/event_vocabulary.py
src/loop_engine/core/model_gateway.py
src/loop_engine/core/model_routes.py
src/loop_engine/core/run_history.py
src/loop_engine/core/runtime_settings.py
src/loop_engine/loop/loop_profile_catalog.py
src/loop_engine/loop/loop_profile_ontology.py
src/loop_engine/memory/query/query.py
src/loop_engine/memory/semantic/record.py
src/loop_engine/memory/storage/repository.py
src/loop_engine/memory/storage/store.py
src/loop_engine/node/README.md
src/loop_engine/node/__init__.py
src/loop_engine/node/loop_node/README.md
src/loop_engine/node/loop_node/__init__.py
src/loop_engine/ontology/README.md
src/loop_engine/ontology/loop_node.py
src/loop_engine/repository_conformance.py
src/loop_engine/runtime_ontology_check.py
src/loop_engine/templates/compiler.py
src/loop_engine/templates/model.py
terminology.yaml
src/loop_engine/code_nodes/solution_model_port.py [untracked]
src/loop_engine/core/model_response_text.py [untracked]
```

## Current GitHub evidence

Run `33081066312` at the starting SHA completed with:

| Job | Result | Evidence |
|---|---|---|
| suite and conformance, Python 3.10 | success | job `98548104892` |
| suite and conformance, Python 3.11 | success | job `98548105063` |
| suite and conformance, Python 3.12 | success | job `98548105119` |
| distribution build | success | job `98548105023` |
| public documentation | failure | job `98548105014` |

The failed step was `Refuse retired public language`. Its log shows the scan
crossed the intended public-prose boundary and reported historical prompt text
and source text. This must be fixed at the scanner and vocabulary ownership
boundaries. A broad unverified allowlist is not an acceptable fix.

## Accepted architecture baseline

```text
One concrete runtime
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, Solution
    ├── Mode: deterministic, hybrid, non-deterministic
    ├── Profile and step procedure
    ├── Typed input and output contracts
    ├── Loop and exit conditions
    ├── Authority, effects, and budget
    └── Run History

One authoritative reusable graph
└── LoopGraphDefinition

Passive solution construction
└── Solution Canvas

Four persistent intelligence layers
├── Context Intelligence
├── Code Intelligence
├── Runtime History and Solution Intelligence
└── User Feedback Intelligence

Three public capability groups
├── Intelligence Search and Retrieval
├── Web Research
└── Custom Plugins
```

`LoopNode` is accepted only as qualified passive, ontology, graph-concept, or
compatibility vocabulary. It is not another runtime. Passive records and
configuration are not Loops.

## Source reconciliation status

The initial source pass completed these evidence tasks:

- read current repository authority and core public documentation;
- compared the committed and dirty versions of the Constitution,
  `architecture.yaml`, and `terminology.yaml`;
- listed repository prompt-history files with Git provenance;
- located four distinct downloaded Loop Engine mandate files plus one exact
  duplicate;
- queried OpenCode's database by workspace and by Loop Engine content across
  all session directories;
- included eight materially relevant workspace sessions;
- included three exact message fragments from two sessions rooted elsewhere;
- excluded unrelated newsletter, Taedri harness, and OpenCode configuration
  material;
- recorded prompt digests instead of copying large prompt bodies; and
- preserved seven named standalone sources as `SOURCE_UNAVAILABLE`.

The decision register is
[`GUIDANCE-RECONCILIATION-REGISTER.yaml`](../architecture/GUIDANCE-RECONCILIATION-REGISTER.yaml).
The conflict register is
[`ARCHITECTURE-CONFLICT-REGISTER.md`](../architecture/ARCHITECTURE-CONFLICT-REGISTER.md).

## Work items

### LE-WORK-000: baseline and reconciliation evidence

| Field | Value |
|---|---|
| Goal | Establish a resumable, provenance-preserving starting point. |
| Source requirement | Current execution-first mandate, section 0 through section 3. |
| Affected invariant or product path | Repository truth and checkpoint order. |
| Baseline | Main at `6a26978`; dirty concurrent worktree; GitHub workflow red. |
| Implementation | Added initial guidance, conflict, ledger, and machine evidence files. |
| Files changed | Only the nine paths assigned to this ledger task. |
| Commands run | Git state, Git history, GitHub run readback, source hashes, OpenCode read-only database queries. |
| Tests | YAML, JSON, JSONL, public-language, and Markdown validation passed. |
| Measurement | Eight workspace sessions, three cross-directory fragments, unrelated session material excluded, seven unavailable standalone sources. |
| Result | Initial evidence baseline created and syntax-validated. |
| Remaining uncertainty | Concurrent implementation is still changing and has not passed a full accepted gate. |
| Commit | none |
| GitHub Actions run | baseline run `33081066312` only |
| Publication state | not published |

### LE-WORK-001: architecture coherence and main green

| Field | Value |
|---|---|
| Goal | Leave one runtime name, one graph authority, one vocabulary, and a green current workflow. |
| Source requirement | Current mandate checkpoint 1. |
| Affected invariant or product path | `Loop`, qualified `LoopNode`, Run History, public documentation. |
| Baseline | Normative and machine files contradicted the concrete runtime; public documentation job failed. |
| Implementation | Concurrent edits exist in contracts, terminology, conformance, docs, and workflow. |
| Files changed | Owned by the main implementation agent, not this ledger task. |
| Commands run | Read-only comparison and GitHub log inspection. |
| Tests | Not yet accepted on the dirty worktree. |
| Measurement | Baseline has four successful jobs and one failed job. |
| Result | `NOT YET PROVEN`. |
| Remaining uncertainty | Compatibility, serialized records, current conformance, and current CI. |
| Commit | none |
| GitHub Actions run | no post-change run yet |
| Publication state | not published |

### LE-WORK-002: core solve and role-mode proof

| Field | Value |
|---|---|
| Goal | Prove one real solve path and all role-mode combinations or typed unavailable results. |
| Source requirement | Current mandate checkpoint 2. |
| Affected invariant or product path | CLI intake, task compilation, runtime execution, graph, verification, Run History. |
| Baseline | CLI delegates to `universal_solve`; README discloses deterministic-only Solution execution. |
| Implementation | Concurrent task-compiler and Solution model-port edits exist. |
| Files changed | Owned by the main implementation agent. |
| Commands run | Read-only code and documentation inspection. |
| Tests | No accepted dirty-worktree role-mode matrix or clean-wheel proof yet. |
| Measurement | Nine role-mode cells required. |
| Result | `NOT YET PROVEN`. |
| Remaining uncertainty | Text, file, task-pack convergence and model-led Solution execution. |
| Commit | none |
| GitHub Actions run | none |
| Publication state | not published |

### LE-WORK-003: governed learning cycle

| Field | Value |
|---|---|
| Goal | Prove staging, independent review, promotion, later use, measured improvement, and negative-transfer protection. |
| Source requirement | Current mandate checkpoint 3. |
| Affected invariant or product path | Memory lifecycle and Learned intelligence. |
| Baseline | Public fifth step stages only. |
| Implementation | Concurrent local journal review and promotion methods exist. |
| Files changed | Owned by the main implementation agent. |
| Commands run | Read-only lifecycle and storage inspection. |
| Tests | Local lifecycle checks exist; two-run installed proof not recorded. |
| Measurement | One treatment run, one no-memory control, one incompatible-scope case. |
| Result | `NOT YET PROVEN`. |
| Remaining uncertainty | Active collection indexing, later-use evidence, rollback, and scope enforcement. |
| Commit | none |
| GitHub Actions run | none |
| Publication state | not published |

### LE-WORK-004: unified model routing

| Field | Value |
|---|---|
| Goal | Prove deterministic-first selection and local, custom, organization, and cloud route parity. |
| Source requirement | Current mandate checkpoint 4. |
| Affected invariant or product path | `ModelGateway`, provider adapters, routing intelligence, privacy. |
| Baseline | Gateway and built-in provider contracts exist; no accepted local Qwen run or holdout routing result. |
| Implementation | Concurrent gateway, route, endpoint, and settings edits exist. |
| Files changed | Owned by the main implementation agent. |
| Commands run | Read-only gateway and settings inspection. |
| Tests | Existing component checks only. |
| Measurement | Ten routing scenarios and routing-regret controls required. |
| Result | `NOT YET PROVEN`. |
| Remaining uncertainty | Exact deployment identity, local-only zero-cloud proof, suitability learning, live availability. |
| Commit | none |
| GitHub Actions run | none |
| Publication state | not published |

### LE-WORK-005: later capability checkpoints

| Field | Value |
|---|---|
| Goal | Research-to-Intelligence, focused Solution Factory, benchmarks, retrieval, Kaggle RSI, and release. |
| Source requirement | Current mandate checkpoints 5 through 9. |
| Affected invariant or product path | All later capability and publication surfaces. |
| Baseline | Partial adapters, scenarios, benchmark registry, and showcase exist. |
| Implementation | Preserve but do not treat as core proof. |
| Files changed | none by this ledger task beyond evidence files. |
| Commands run | Inventory only. |
| Tests | Not run in this work item. |
| Measurement | Not measured in this work item. |
| Result | `NOT YET PROVEN`. |
| Remaining uncertainty | All checkpoint-specific gates. |
| Commit | none |
| GitHub Actions run | none |
| Publication state | not published |

## Checkpoint state

| Checkpoint | State | Exact next proof |
|---|---|---|
| 0. Baseline and reconciliation | in progress | Read back concurrent implementation state and run current conformance. |
| 1. Architecture coherence and main green | in progress | Run current conformance and public documentation gates, then current GitHub CI. |
| 2. Core solve and role-mode execution | pending | Run five core proofs from a clean wheel. |
| 3. Complete memory and learning governance | pending | Run the two-run treatment and control proof plus incompatible scope. |
| 4. Unified model routing | pending | Run routing scenarios, including local-only zero-cloud evidence. |
| 5. External Evidence | pending | Run source-grounded research through typed ports. |
| 6. Solution Factory and Studio | pending | Complete the focused flagship portfolio and playback. |
| 7. Benchmark and retrieval evidence | pending | Run matched benchmark and frozen retrieval tournaments. |
| 8. Bounded Kaggle RSI | pending | Prove KRSI-1 through KRSI-3 on held-out tasks. |
| 9. Release and publication | pending | Build, install, hash, tag, publish, and read back supported artifacts. |

## Evidence files

```text
Human-readable
├── docs/architecture/GUIDANCE-RECONCILIATION-REGISTER.yaml
├── docs/architecture/ARCHITECTURE-CONFLICT-REGISTER.md
└── docs/implementation/CODEX-5.6-MAX-EXECUTION-LEDGER.md

Machine-readable
├── artifacts/checkpoints/checkpoint_ledger.jsonl
├── artifacts/checkpoints/command_receipts.jsonl
├── artifacts/checkpoints/test_results.jsonl
├── artifacts/checkpoints/live_integration_matrix.json
├── artifacts/verification/architecture_facts.jsonl
└── artifacts/verification/conflicts.jsonl
```

## Current exact blocker

Main cannot be described as green because GitHub Actions run `33081066312`
failed its public-documentation job. The dirty worktree contains a proposed
boundary correction, but no post-change commit or GitHub run exists yet.

The next command belongs to the main implementation owner after resolving
concurrent edits:

```bash
python3 -m loop_engine --conformance
```

Then reproduce the public-language command from `.github/workflows/ci.yml`
against the exact intended public paths before committing.

## Resumed execution: semantic recovery

### LE-WORK-M1: Checkpoint -1 semantic recovery

| Field | Value |
|---|---|
| Work item ID | `LE-WORK-M1` |
| Goal | Restore `Loop` as the sole concrete and public runtime while preserving useful independent implementation. |
| Source requirement | Stop-the-line canonical semantic constitution, 2026-08-27. |
| Affected invariant or product path | Runtime identity, public API, definitions, legacy records, architecture contracts, wheel installation. |
| Baseline | Starting SHA `6a26978c5e6cd2e3852818c4bb4b2dac23b0da76`; the shared worktree temporarily renamed the runtime to `LoopNode`. |
| Implementation | Preserved the full pre-repair diff; restored the `Loop` class and exports; removed active/public `LoopNode`; retained `LoopDefinitionRecord`; added exact legacy `kind: loop_node` migration; made `terminology.yaml` the semantic authority; added mutation gates. |
| Files changed | Runtime, ontology compatibility reader, architecture and terminology contracts, semantic conformance, generated dictionary, recovery and verification artifacts. |
| Commands run | Source self-test and conformance; wheel/sdist build; Twine checks; clean Python 3.10 wheel install; installed self-test and conformance; saved Run History readback. |
| Tests | Source `1337/1337`; source conformance `28/28`; clean wheel `1337/1337`; clean wheel conformance `28/28`; legacy record migration `4/4`; saved canonical histories `11/11`. |
| Measurement | One runtime class; zero subclasses; zero active `LoopNode` classes; zero `LoopNode` package-root exports; zero semantic conformance violations. |
| Result | `VERIFIED WORKING`; pushed main is green. |
| Remaining uncertainty | Required GitHub Actions result and external publication state. |
| Commit | `dc2b3f27d347cd17a8de423e54df7efe5cf7ce40` |
| GitHub Actions run | `33108407104`, success on Python 3.10, 3.11, and 3.12, distribution build, examples, and public documentation |
| Publication state | published to `origin/main` through commit `571d533a550d4254a6064bc672c0ca6189da5eb6` |

### LE-WORK-M2: Checkpoint -0.5 universal parameterization and repository alignment

| Field | Value |
|---|---|
| Work item ID | `LE-WORK-M2` |
| Goal | Represent varied behavior through typed definitions, profiles, procedures, portfolios, strategies, adapters, and Loop instances; assess every first-party file, symbol, and folder. |
| Source requirement | Universal Parameterized Loop Architecture and File-by-File Alignment Mandate, 2026-08-27. |
| Affected invariant or product path | Procedure model, Practitioner profiles, repository assurance, folder ontology, strings and serialized contracts. |
| Baseline | Static audit found 175 call-boundary violations and high-value duplicated vocabularies, unstable IDs, and string-encoded behavior. |
| Implementation | Repository-assurance request/profile and initial file records exist; full inventories and twenty-behavior proof remain. Cohesive configuration and data classes are explicitly protected from unjustified deletion. |
| Files changed | Initial devtools assurance and semantic decision rules only. |
| Commands run | AST parameter and semantic audits. |
| Tests | Not yet a completed checkpoint proof. |
| Measurement | Full file/symbol/folder denominator will be regenerated from the pushed Checkpoint -1 state. |
| Result | `NOT YET PROVEN`. |
| Remaining uncertainty | Generic ProcedureDefinition and ProcedureStepSpec integration, complete inventories, first repaired batch, twenty-behavior matrix. |
| Commit | none |
| GitHub Actions run | none |
| Publication state | backlog for the next Codex audit session |

### LE-WORK-M3: Work-Approach Instrumentation and Optimization

| Field | Value |
|---|---|
| Work item ID | `LE-WORK-M3` |
| Goal | Make work strategy, prompt assembly, context selection, memory access, delegation, confidence, response shape, and verification experimentally traceable without creating another runtime. |
| Source requirement | Current owner guidance on instrumenting observable human work strategies, 2026-08-27. |
| Affected invariant or product path | Loop profiles, procedures, prompt assembly, intelligence selection, delegation, Run History, benchmarks, and governed learning. |
| Baseline | `ReasoningRequest`, `PromptAssemblySpec`, named blocks, layout policies, seeds, prompt digests, intelligence portfolios, and typed delegation already cover part of the boundary. Exact approach snapshots, contribution tests, and suitability learning are not complete. |
| Implementation | Added the accepted architecture and checkpoint contract in `docs/architecture/WORK-APPROACH-INSTRUMENTATION.md`. Existing typed configuration and data classes remain protected. No new runtime or competing authority was added. |
| Files changed | Architecture direction, Codex start context, guidance register, and this ledger. |
| Commands run | Compiler checks; source self-test and conformance; complete Markdown lint; retired-language scans; YAML and JSONL parsing; package build; Twine validation. |
| Tests | Compiler `9/9`; template library `5/5`; source `1341/1341`; conformance `28/28`; Markdown `132` files with zero issues; retired-language matches `0`; Twine passed for wheel and sdist. |
| Measurement | Requires matched trials, exact denominators, ablations, held-out task families, uncertainty, and negative-transfer tests. |
| Result | `NOT YET PROVEN`. The architecture direction is recorded; implementation and experiments remain a later hard checkpoint. |
| Remaining uncertainty | Exact reuse map for candidate passive records, implementation batch order, frozen task populations, and independent evaluator contracts. |
| Commit | pending |
| GitHub Actions run | pending |
| Publication state | pending main push |
