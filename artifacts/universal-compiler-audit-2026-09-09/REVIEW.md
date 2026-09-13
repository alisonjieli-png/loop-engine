# From task to reusable solution: local capability audit

Loop Engine's intended product is a verified, reusable solution graph. The
conversation and cognitive run explain how it was built. They are not the
solution that must run again for the next input.

The local source supports that architectural direction. It does not yet prove
the complete overnight product described in the supplied mandate. Preserve the
existing capabilities and close their integration gaps before replacing them
with new abstractions.

This is an initial source-grounded audit, not a completed folder-by-folder
semantic parity review. No runtime was merged, no original implementation was
deleted, and no commit, push, deployment, or new live-model campaign was made
for this audit. The small peer experiments described below are not canonical
Loop Engine integration evidence.

## Scope and evidence

The inspected Loop Engine checkout is `main` at
`acfd826eeee3ea2c05b638031ff235b709a69eb2`, with existing dirty source and
architecture files. Their ownership remains unknown and those files were not
changed. The separate `new_overnight_build` checkout was subsequently inspected
at `ddfedccf4af205b0261941b2e0edf793864136a8`.

The [snapshot](snapshot-01/snapshot.json) records branch, revisions, dirty
paths, worktrees, authority digests, and process names without arguments or
environment values. A process name or modification time does not prove who
owns a change.

The discovery pass covered 58 roots: the canonical checkout, 52 indexed lab
projects, three new unindexed experimental peers, and two lab plans. It indexed
10,258 source files and found 1,028 byte-identical groups. These are discovery
counts, not counts of reviewed capabilities or interchangeable implementations.
Excluded dependencies, runtime data, archives, large files and symlinks are
listed explicitly. Other original repositories received a Git-metadata check,
not a new exhaustive source review. This is not a scan of every folder on the
computer, nor a transactional filesystem snapshot.

Use these evidence levels independently:

| Level | What it establishes | What it does not establish |
| --- | --- | --- |
| Declared | A current contract or catalog describes the capability | A caller uses it |
| Source inspected | A concrete implementation and boundary exist | The installed environment supports it |
| Static import reachable | A modeled import path can reach the module | The function is called, or dynamic imports are fully modeled |
| Check executed | An exact test or probe ran | General correctness or live-provider quality |
| Effect observed | An independently checked artifact or state change occurred | Generalization to other tasks |
| Qualified | An independent authority approved an exact supported region | Universal applicability or permission for a new effect |

The [preservation ledger](snapshot-01/capability-preservation-ledger.json) has
97 initial entries. Unknown fields are null, not empty capabilities. Its
dispositions preserve implementations provisionally; they do not authorize
consolidation. The [canonical component inventory](canonical-component-inventory.json)
adds the existing engine's own inventory: 430 Python files, 3,530 top-level
symbols, and 105 explicit component records. Symbol counts are not capability
counts. The [source index](snapshot-01/source-index.json) supplies file digests
and declaration locations for the wider collection.

## Governing purpose

Use bounded reasoning to compile an unfamiliar task into one or more executable
solutions. Retrieve established components before generating replacements.
Verify the composition and its actual outputs. Preserve useful novelty as a
candidate for independent qualification, so later work can use less reasoning.

The desired outputs stay separate:

| Output | Purpose |
| --- | --- |
| Task and situation record | Preserve the request, sources, amendments, constraints, unknowns and acceptance criteria |
| Cognitive Run History | Explain decisions, attempts, evidence, failures and recovery |
| Solution portfolio | Compare candidate canvases without treating every alternative as active |
| Compiled solution | Pin the selected `LoopGraphDefinition`, implementations, bindings and environment |
| Review and learning package | Carry verifications, costs, blockers, human choices and reuse candidates |

An accepted answer can still be appropriate for a question-only task. The
compiler should not generate unnecessary software. When reusable execution is
requested, a narrative answer or an unexecuted code file is insufficient.

## Complete Loop classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records

Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence: serve, search, and frame
│   ├── Code Intelligence: resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence: search, replay, and compare
│   └── User Feedback Intelligence: serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

The historical `reference_nine_step` identifier currently names ten ordered
steps. Preserve its versioned meaning rather than changing behavior to match
its name. See the [Loop guide](../../docs/components/loop-object/README.md).

Atomic means one independently governable responsibility, not one token, CPU
operation, or helper function. A separate goal, verification, retry, authority,
budget, cancellation or scheduling boundary justifies another Loop. It does
not automatically justify another operating-system process.

## Keep three graph planes distinct

```text
Architecture views
├── Descriptive intelligence graph
│   └── Source facts, syntax, resolution, static possibilities and observations
├── Logical executable graph
│   └── Exact Loop definitions, data bindings, relationships and effect policy
└── Physical execution graph
    └── Processes, isolated sessions, models, tools, sandboxes and services
```

The cognitive run graph is a historical view of work that occurred. The
Solution Canvas is a passive builder and comparison surface. Selected work
compiles into the one authoritative executable graph. An external harness is
an implementation adapter used by a Loop, not a new runtime type.

The [eight current generated views](CURRENT-GENERATED-VIEWS.md) come from the
existing typed diagram model, including C4-PlantUML output. They were not
hand-edited into an ideal-state diagram. Their [coverage record](generated-view-audit.json)
identifies missing structured protocol, delivery-timing and trust fields on
edges. They do not yet cover every requested C4 view, and visual rendering was
not tested in this audit.

## What is present, and where the complete path is missing

| Capability | Current source or boundary | Audit result and remaining proof |
| --- | --- | --- |
| One runtime and versioned profiles | `loop/recursive_loop.py`, `loop_definition.py`, profile catalogs | Established authority; preserve independent axes |
| Task intake and material questions | `templates/intake.py`, `code_nodes/solve_runtime.py` | Present; a complete unattended folder-to-answer/resume workflow needs its own demonstration |
| Cognitive procedures and horizons | `core/practitioner_context.py`, `task_frontier.py`, `adaptive_practitioner_records.py` | Present; selected profile coverage and downstream consumption must be measured |
| Four persistent intelligence layers | `core/intelligence_layers.py` | Present; fresh layers may be empty. Saved `SolutionLibrary` assets are not all loaded into the third layer |
| Temporary Runtime Memory | `core/runtime_memory.py`, `memory/working/state.py` | Separate from persistent intelligence; do not invent a fifth layer |
| Reviewed learned claims on public solve | `code_nodes/solve_learned_memory.py` | Reads an approved journal into bounded advisory context; does not select or execute a solution |
| Exact and hybrid retrieval | `core/retrieval.py`, `ngram_retrieval.py` | Hash vectors, optional learned model2vec, lexical modes and rank fusion exist. Exact n-gram search is a separate implementation |
| Fingerprints | `core/task_fingerprint.py`, `stage_fingerprint.py` | Typed compatibility and similarity identities exist; they do not qualify an artifact |
| Large-value references | `core/information_access.py`, `context_artifacts.py` | Existing identity, materialization and offloading contracts passed focused checks |
| Adaptive child reference delivery | `core/adaptive_practitioner_bindings.py:194` | Explicitly refused: the consuming adaptive path lacks its own reference-materialization capability. This is narrower than saying all pointer access is absent |
| Model packets and exposure | `core/llm_work_packet.py`, `context_pack_manifest.py`, stage-evidence records | Present; estimated bytes/4 counts are not provider token bounds. Cross-harness exact exposure still needs qualification |
| State-centric skill context | `core/skill_state_context.py` | Explicit `SKILL_STATE_PRODUCT_RENDERER_INTEGRATED = False`; tested passive mechanism, not active prompt integration |
| Small Code Intelligence cards | `core/code_intelligence_assets.py`, `loop/loop_capsule.py` | Existing lazy cards and admission contracts. Extend these before adding a competing capsule system |
| Typed Canvas compilation | `loop/canvas.py`, `code_nodes/solution_graph.py` | Graph identities and named-role connections exist. Full shapes, units, encodings and refinements are not enforced on every edge |
| All three Solution modes | Solution runner and installed-executor checks | Supported subject to compatible executors and exact model authority; no mode belongs to an entire Canvas |
| Reuse qualification and promotion | `core/reusable_capability_flywheel.py`, `reusable_capability_resolution.py` | Focused offline checks pass; resolver absent from the modeled public-solve static import closure |
| Post-solve harvesting | `core/adaptive_practitioner_reuse.py` | Optional observation port; a solved result without that binding produces no harvest observation |
| Semantic candidate-to-commit path | `core/semantic_runtime.py`, `semantic_state.py` | Focused checks pass; not in the modeled public-solve static import closure |
| External harness boundary | `core/external_harness.py`, `opencode_harness_adapter.py` | Canonical raw-host OpenCode adapter remains quarantined. Independent peer results do not remove quarantine |
| MCP and skills | Existing MCP adapters and `SkillRegistry` | Present with specific version/dependency boundaries. Core optional MCP dependency is `<2`; new peer experiments use SDK 2.2.0 |
| Reactive triggers and durable jobs | `TriggerEnvelope`, `SQLiteReactiveScheduler`, `CanonicalReactiveExecutor` | Existing mechanisms; saved-intent matching and a complete overnight product remain separate integration work |
| Recovery and supervision | `FailureDiagnosis`, `RecoveryProposal`, `SupervisionPolicy` | Present. Retry, context expansion, model escalation and provider failover must remain distinct |
| Strict model budgets | `ProviderTokenBound`, `ModelOutputAllocation`, shared model session | Focused checks pass. Qualified exact-wire bounds and durable cross-process reservations remain open |
| Managed records | `RecordOperationService`, catalog/artifact contracts | Present bounded tool; no automatic migration of historical Run History or every file writer |
| Playback and Studio | `RunHistory`, `SavedRunBundle`, diagram and viewer modules | Preserve canonical projections; live browser behavior was not retested here |
| Signature/build-backed code intelligence | Researched SCIP/LSP/CPG interfaces | No new canonical indexer integration or cross-language correctness result produced by this audit |
| Local laptop inference | Provider/model adapter options | Product target, not demonstrated by these cloud-backed development runs |
| Team/cloud intelligence | Existing storage and provider boundaries plus proposals | Distribution, tenant isolation, revocation and retention need explicit qualification; no SaaS completeness claim |

The static import report reaches 240 of 430 modules from `solve_runtime` and
290 from the CLI. All eight specifically required solve-path modules are
reachable. The remaining modules are not automatically defects: other entry
points, optional adapters and experiments own some of them. Conversely, an
import is not proof that its output influenced a real decision.

## Information transfer and the context decision

The [existing interaction catalog projection](snapshot-01/information-transfer.json)
preserves seven declared interactions: intelligence selection, prompt assembly,
model invocation, action compilation, child assignment, stall diagnosis and
recovery selection. It includes contracts, privacy, authority transfer,
delivery, retry and verification fields. Those declarations need dynamic
receipts on the chosen path.

For the target overnight path, preserve these transfers:

| Transfer | Exact information required | Failure to reject or expose |
| --- | --- | --- |
| Task folder to intake | Original bytes, digests, attachments, media, amendments and source-sharing policy | Missing attachments, traversal, symlink escape, instruction/data confusion |
| Intake to bounded responsibility | Objective, horizons, input references, acceptance, authority and budget | A subtask that loses a material constraint |
| Search to selection | Body-free identity, contract, source, eligibility and uncertainty | A relevance score presented as permission |
| Selection to context | Selected bytes, source revision, hydration level, omissions and packet digest | A reference recorded as exposed when its body was never loaded |
| Packet to harness/model | Exact adapter/model/configuration, rendered payload, limits and granted tools | Hidden configuration, uncounted retries or stale permissions |
| Model output to Canvas | Candidate code or graph delta, exact contracts and dependencies | Schema-valid output accepted without semantic checks |
| Canvas to execution | Resolved graph, exact artifacts, typed bindings and effect approvals | Changed source or an unauthorized side effect |
| Execution to verification | Immutable subject, observations, independent evaluator and exclusions | Verifier grading a different artifact or a gate edited by the producer |
| Verification to review/reuse | Scoped outcome, failures, costs, lineage and candidate lifecycle | Passing a test automatically promoting reusable intelligence |

Push and pull are compatible with addressable context. A host can resolve an
ID, verify the body and push a bounded packet before the first model call. A
model can request deeper material when needed. Test push, pull and hybrid
policies with the same evidence and authority. A pointer saves provider input
only when it reduces hydration or repetition, not merely because it is short.

## Corrections to the newly supplied overnight audit

The referenced `docs/BUILD-SPEC.md` is absent at the latest inspected revision.
Its preserved copy is `docs/superseded/BUILD-SPEC.md`; the current README points
to `docs/ENGINE.md`. Do not execute a superseded build sequence as current
repository authority.

1. **File input is not large argv content.** `poc/harness.py:153` places file
   paths in `argv`, then stores prompt bodies as files. File contents are not
   subject to the per-argument limit merely because `--file` is used. Path-list
   size, file parsing, context limits and provider payload limits remain real
   constraints. The earlier statement that no context protocol can attach to
   push delivery is unsupported.
2. **N-grams are not the whole retrieval system.** Current Loop Engine has
   `hash_vector`, `Model2VecBackend`, `simhash64` and vector/hybrid search. A
   SimHash field is not proof of a complete LSH candidate index; an optional
   embedding adapter is not proof it was used in a particular solve.
3. **A scoped memory port is not a qualified harness bootstrap.** Loop Engine
   has scoped Runtime Memory and large-value resolution. The adaptive child
   reference path still refuses. Each producer, consumer and grant must be
   tested, rather than declaring pointer support universally present or absent.
4. **The new frontier is not wired into the inspected overnight path.** Source
   search found its callers in `tests/test_frontier.py`, not `poc/overnight.py`,
   `solver.py`, `build.py` or `run.py`. Questions and horizons share a record
   structure but remain different fields and responsibilities.
5. **Evidence presence is not verification.** The [read-only frontier probes](frontier-probe.json)
   reproduce acceptance of `evidence_refs=("",)` for `VERIFIED`, an arbitrary
   unresolved string for an answered question, and undetected mutation of the
   last snapshot. These are limitations of the record mechanism, not a proven
   production exploit. Require validated evidence bindings and an independently
   anchored immutable head before treating it as trusted history.
6. **Questions are useful partial results, not completed acceptance.** A morning
   report should distinguish a productive blocker from a failed implementation
   while preserving the fact that the original task remains unfinished.
7. **An exit-zero command is evidence under an evaluator, not universal truth.**
   File-existence checks, inaccurate oracles and exploitable tests can accept
   wrong work. Preserve evaluator strength and task coverage in every outcome.

The main workspace had 486 GB available. The first full-suite attempt failed
in `/tmp`, which is a separate `tmpfs` mounted with `usrquota`. Its journal
write returned `EDQUOT`. No cleanup was performed. The retry uses this audit's
workspace `TMPDIR`. Do not attribute earlier reported failures to the same
cause without their exact logs. See [the retained failure](full-attempt-01-failure.json).

## Benefits and costs of the intended architecture

| Design | Benefit | Cost or failure mode | Required control |
| --- | --- | --- | --- |
| Small cognitive responsibilities | Easier retry, inspection, attribution and small-model use | Lost global constraints, repeated setup, coordination overhead | Horizon references, explicit handoffs and granularity experiments |
| Fresh harness sessions | Less cross-task contamination | Repeated prompt and process startup costs | Compare cold, pooled-isolated and episode-scoped sessions |
| Bounded context | Less repeated transmission and distraction | Compression can remove a delayed but important fact | Retain source references, contradictions and permissioned expansion |
| Reusable code cards | Compose without regenerating implementations | Matching names and types can hide different semantics | Units, shapes, preconditions, effects, dependencies and behavioral checks |
| Deterministic shortcuts | Avoid repeated generative reasoning | Stale dependencies, weak fingerprints and negative transfer | Exact binding, invalidation, qualification and new-input verification |
| Alternative canvases | Preserve options under uncertainty | Correlated errors and selection cost | Independent verification, common constraints and no test leakage |
| Outcome-based learning | Accumulate useful procedures and failures | Feedback bias, verifier gaming and memory poisoning | Separate proposer, evaluator and promoter; held-out populations |
| Portability adapters | Preserve useful harness and tool choices | Translation loss and unsupported control semantics | Versioned handshake plus positive and adversarial effect tests |

The linear-regression example needs more than a function signature. Its card
must distinguish fitting from prediction, feature order, missing values,
categorical encoding, leakage rules, array shape, numeric dtype, randomness,
dependency versions and allowed effects. Reuse the exact admitted artifact by
reference or reproducible packaging. Copying an anonymous snippet loses that
identity.

## Information-theory and cognitive interpretation

Context selection is a constrained compression problem: retain evidence needed
for the current decision while reducing irrelevant transmission. This is
consistent with the [information bottleneck formulation](https://arxiv.org/abs/physics/0004057),
but this audit does not estimate mutual information or prove sufficiency.
Measure task loss and false acceptance alongside bytes, actual tokens, latency,
and rework. A smaller prompt with a worse decision is not an improvement.

[SKILL.state v3](https://arxiv.org/abs/2608.26263v3) studies supplying a skill,
structured execution state and latest observation instead of replaying a growing
conversation. That is supporting research for an experiment, not proof that
every task can discard its trajectory. Loop Engine already has an offline
skill-state contract that preserves delayed-relevance and history-needed flags.
Wire and evaluate it without deleting the fuller-history option.

Reuse amortizes construction and qualification. Under equal quality and a stable
task region, a simple accounting comparison is:

`build + qualification + N × reuse_cost < N × fresh_solve_cost`

Include retrieval, validation, failures, maintenance and human review on the
reuse side. This is bookkeeping, not a measured universal savings result.
Fingerprint similarity addresses candidates; it does not establish functional
equivalence. More parallel agents likewise need evidence: the
[agent-scaling study](https://arxiv.org/abs/2512.08296v3) investigates interaction
between task structure and coordination, rather than justifying more agents for
every task.

Code evidence should be a set of typed derivations, not the supplied E0 to E8
ordering treated as a trust ladder. A static possibility and one observed trace
answer different questions. Human review and model interpretation are not
automatically stronger than compiler facts. Do not call this a mathematical
lattice without defining its partial order and join/meet operations.

## Portable tools and research implications

| Boundary | Source-supported implication for this project |
| --- | --- |
| Persisted code navigation | [SCIP](https://github.com/scip-code/scip) supplies an index interchange format, not a universal analyzer. Retain build and extraction provenance |
| Tools and resources | [MCP 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/) changes protocol continuity and extension handling. Verify the actual client/server revision; do not infer support from an MCP label |
| Portable packaging | [Agent Plugins 1.0](https://agent-plugins.org/specification) packages skills and MCP definitions. Installation, authorization and host-specific hooks remain separate obligations |
| Saved intents | [OpenSearch percolation](https://docs.opensearch.org/latest/query-dsl/specialized/percolate/) matches incoming documents against stored queries. It does not perform semantic eligibility, execution or promotion |
| Smaller-model delegation | [Shunt's benchmark definition](https://github.com/spotify/portal-ai-plugins/blob/main/plugins/shunt/evals/benchmarks.json) measures estimated main-agent context reduction. It does not establish total multi-model cost savings |
| Portable execution | [Wassette](https://github.com/microsoft/wassette) runs Wasm Components through MCP and describes itself as early development. Interface portability is not production qualification |
| Skill optimization | [SkillOpt-Sleep](https://github.com/microsoft/SkillOpt/blob/main/docs/sleep/README.md) is relevant to revisiting sessions and evaluating skill changes. Keep proposed changes behind independent promotion |
| Registry metadata | [xRegistry's specification repository](https://github.com/xregistry/spec) links the xrproxy package-registry adapters. Discovery does not establish installability or authority |
| Evaluation tasks | [Harbor](https://www.harborframework.com/docs/tasks) packages task instructions, environments and verification. Its default verifier can share the agent environment; use an explicitly separate environment when independence requires it |

The rest of the supplied project catalog remains research input. This pass
does not claim to have reverified every release, license, hosted-service term,
new paper or benchmark percentage in it. No new external service was installed
or connected for this audit.

## The small cold-to-warm experiment

Two independent peers used the same cloud model and two authored method-repair
responsibilities. A host-owned gate checked each method and the final source.
The warm file changed an unrelated comment and function while preserving the
target ASTs and declared bindings. Model use was disabled for warm runs.

| Peer | Cold result | Fresh harness instances | Cold seconds | Warm seconds | Warm model instances |
| --- | --- | ---: | ---: | ---: | ---: |
| OpenCode 1.17.9 | Passed after one failed proposal and repair | 3 | 461.16 | 1.09 | 0 |
| Pi 0.85.1 via MCPorter | Passed | 2 | 357.23 | 1.19 | 0 |

Both warm exports also replayed successfully without a model. The
[proof review](cold-warm-proof.json) retains exact record digests, failures and
known token subtotals. Physical provider-request totals and provider cost remain
unknown. The sample is one familiar source-repair task per harness, not a
controlled general performance ranking. The host supplied the decomposition.
This is not an arbitrary semantic-match proof, a full dataflow Canvas, a laptop
model benchmark, or a canonical qualification/promotion cycle.

A separate canary showed that native before-tool hooks blocked a harmless
marker in both harnesses. OpenCode's `--pure` control had not loaded that local
hook. This is why translated configuration must be tested for effect rather
than judged from file presence. The local `atomic-hook/v1` contract is not a
universal hook standard.

## Capability-preserving implementation order

1. Finish semantic review of the inventoried roots. Join each capability to
   callers, supported region, negative controls, source provenance and owner.
   Do not delete or deduplicate from the byte-overlap report.
2. Close the adaptive dependency-reference gap at the existing
   `InformationResolver` and child-grant boundary. Keep value delivery and add
   positive, denied, stale, oversized, Unicode and canceled-consumer tests.
3. Wire one harness adapter through the existing canonical boundary. Keep the
   raw-host adapter quarantined until private configuration, credentials,
   workspace, network, cancellation, exact exposure and accounting are proven.
4. Demonstrate one task-folder run that constructs alternatives, selects a
   Canvas, compiles the canonical graph and verifies exported execution.
5. Join the existing capability lifecycle to that exact live path. Cold solving,
   independent qualification, explicit promotion and warm execution must be
   distinct recorded events. Include a near-match rejection and invalidation.
6. Add the overnight operating profile over qualified pieces: bounded queue,
   per-task state, deadlines, cancellation, resume reconciliation, incumbent
   preservation, unanswered questions and morning review. No automatic merge,
   publication or failover merely because a sample policy says `allowed`.
7. Compare granularity, push/pull, session topology and model routes separately
   before evaluating combinations. Then add saved intents, indexing adapters
   and evaluated learning where the task population shows a gap.

The full architecture remains available through versioned profiles, adapters
and reviewed intelligence. A lean default does not remove those choices.
Local-only execution, all-cloud development, interactive work and unattended
work are different configurations, not different meanings of correctness.

## Acceptance and remaining work

The [delivery checklist](deliverable-status.json) accounts for every requested
audit deliverable. The broad mandate is not complete. Still required are the
full semantic parity review, a qualified canonical harness integration,
cross-harness exposure and budget accounting, general graph value checks,
live governed reuse, local-model qualification, a complete overnight path,
all requested C4 views, and broader sealed task populations.

The focused suite passed 249/249 and all 27 conformance gates plus repository
conformance passed. The [complete source-suite retry](full-workspace-tmp-checks.json)
passed 3,412/3,412 in 833.27 seconds after changing only the test temporary
directory and enforcing offline model-cache access. The first failed attempt
remains recorded. Clean-wheel, browser and CI checks were not repeated by this
audit, and no current CI success is inferred from local checks.

The useful next build is the missing connection between existing contracts,
not a replacement runtime, parallel memory system, or a new universal registry.

## Map proposed names before implementing them

| Mandate concept | Existing boundary to extend or compose | Unresolved part |
| --- | --- | --- |
| `LoopWorkPacket` | `WorkerAssignmentEnvelope`, `LLMWorkPacket`, `HarnessRunRequest` | Exact adapter bootstrap and consumer-side hydration, not three parallel packet authorities |
| `ContextNeed` | `IntelligenceQuery`, `IntelligenceSeekingStrategy`, `IntelligenceAccessPolicy` and selected context requests | Uniform cross-harness need/response mapping |
| `ContextFrame` and `ContextExposure` | `LLMContextBlock`, `ContextPackManifest`, `StageExposureManifest`, artifact references | Complete provider-wire exposure and host transformations |
| `Node Capsule` | `CodeAssetSpec`, `IntelligenceItemRef`, `IntelligenceItemPackage` | Missing applicability/refinement fields should be typed additions; no new executable Node class |
| `SourceSnapshot` and `CodeEvidenceRecord` | Intake/source admission, immutable artifacts, Code Intelligence metadata | Build target, position encoding, analyzer derivation and source-to-index invalidation |
| `SavedIntent` | Existing catalog records plus `TriggerEnvelope` and reactive scheduling | Need-to-event matching, deduplication, expiry and candidate-only notifications |
| `Record Fabric` | `CatalogStore`, `RecordOperationService`, existing artifact and Run History owners | No blanket writer migration or new parallel database |
| Horizon-aware questions | Existing task frontier and work-packet horizon fields | A passive historical projection is not the active work scheduler; the separate frontier port remains unwired |

One useful new research caveat concerns
[SkillOpt-Sleep](https://raw.githubusercontent.com/microsoft/SkillOpt/main/docs/sleep/README.md):
the current documentation calls it preview, notes that several integrations
postdate the released package, and says real backends transmit session-derived
material. Its optional per-task no-regression gate defaults off. This fits a
candidate-review experiment, not unattended adoption of private transcripts or
proof that every existing capability survives an aggregate-score improvement.
