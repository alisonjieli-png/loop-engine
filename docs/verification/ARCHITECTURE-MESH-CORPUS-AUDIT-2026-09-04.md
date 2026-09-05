# Loop mesh architecture and repository audit

Audit date: 2026-09-04. Repository: `/home/username/loop-engine`.
Source HEAD: `22ee44052b027ba96ce50c37e4cc6a659e1b91c8`, branch `main`.
The findings describe the inspected dirty checkout, not HEAD alone.

Loop Engine has one executable runtime and substantial support for typed,
governed work. Its main solver currently behaves like a coordinator-led team.
It is not yet an independently learning society of solvers, and it has not
demonstrated that it can solve every unfamiliar problem.

The most urgent new finding concerns evidence, not terminology. An offline
probe attached a genuine verifier record for result B to the execution of
result A. The attribution boundary accepted it. A separate probe showed that
the adaptive integrator retains rejected artifacts without a per-artifact
trust classification. These gaps need attention before stage records train
routers or qualify shortcuts.

This is a review. No runtime fixes, commits, pushes, releases, Kaggle
submissions, or live model calls were made for this audit. The report and
its evidence bundle are new outputs. The writing pass uses the repository's
neutral technical voice and preserves exact names and uncertainty.

## 1. The architecture that exists

The complete classification is:

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
```

`Loop` is the operational type. "Loop node" can describe its position in a
graph, but does not establish another runtime class. The live conformance
check found 69 registered operational boundaries bound to this ontology:
62 exact profile bindings and seven validated dynamic profile sources.
That checks the registered boundary population, not every possible hidden
operation in arbitrary source code.

Role profiles specialize the same runtime:

```text
Loop role profiles
├── Practitioner
│   ├── reference nine-step and compact profiles
│   ├── research and solver
│   ├── verifier and code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence: serve, search, frame
│   ├── Code Intelligence: resolve, invoke, load
│   ├── Runtime History and Solution Intelligence: search, replay, compare
│   └── User Feedback Intelligence: serve, scope, interpret
└── Solution
    ├── atomic component and pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

Profile names are versioned identifiers. A historical name such as
`reference_nine_step` is not sufficient evidence of the number of currently
executed steps. Inspect the selected profile and its executor.

### Not every object is an executable Loop

The useful rule is: every independently governed operational responsibility
has a Loop owner. A fingerprint, schema, model artifact, stored row, prompt,
edge, configuration object, or receipt remains passive. A database adapter
does not become another graph vertex merely because a Loop uses it.

Create a separate activation when work needs an independent contract, goal,
budget, authority, retry, verification, scheduling, cancellation, checkpoint,
or history identity. Keep ordinary hashing, formatting, arithmetic, and
serialization inside their owning Loop unless such a boundary is needed.
This follows the current Constitution and avoids recursive wrapper growth.

### The society analogy

A Practitioner resembles a coordinator or specialist assigned a bounded
problem. Intelligence Loops resemble researchers and librarians. Solution
Loops resemble workers executing an approved procedure. Verifiers check
results. Run History provides records of what actually happened.

The analogy has limits. Two profiles may use the same model and session.
Different role names do not imply independent knowledge, independent model
weights, or independent verification. A repeated execution is not itself
learning. A reviewed reusable procedure is closer to "muscle memory" than
a frequently repeated prompt.

The public adaptive path remains a staged, coordinator-led implementation.
`adaptive_practitioner.py` executes spawned specifications sequentially with
shared services. Generic asynchronous delegation and local reactive workers
exist elsewhere, but their existence does not prove that the main solver
uses a peer mesh or dynamically allocates a different model to each stage.

The compiled `LoopGraphDefinition` is an immutable DAG and refuses cycles.
Recurrence can occur through bounded iterations and later activations with
new state. Recursive decomposition can occur through spawning. Neither
requires a literal cycle in one committed Solution graph.

## 2. Intelligence, memory, and static infrastructure

These are different architectural dimensions:

```text
Loop Engine resources used by Loops
├── Persistent intelligence layers
│   ├── Context Intelligence
│   ├── Code Intelligence
│   ├── Runtime History and Solution Intelligence
│   └── User Feedback Intelligence
├── Core Architecture public capability groups
│   ├── Intelligence Search and Retrieval
│   ├── Web Research
│   └── Custom Plugins
└── Internal runtime mechanics
    ├── providers, model gateways, settings, and capability records
    ├── permissions, approvals, workspaces, and effect enforcement
    ├── stores, artifacts, indexes, and scoped Runtime Memory
    └── Run History, reports, playback, and scheduling
```

| Persistent layer | What belongs there | Present limitation |
|---|---|---|
| Context Intelligence | Reviewed instructions, domain context, response guidance, and selected source material | A Markdown file or retrieved skill is not automatically active or trustworthy. Selection, permission, materialization, and framing remain separate. |
| Code Intelligence | Exact executable capabilities, dependencies, contracts, effects, tests, provenance, and qualification | Optional reuse services can qualify exact capabilities. This is not automatic generalization of every generated code artifact. |
| Runtime History and Solution Intelligence | Prior runs, decisions, solutions, failures, and comparison/replay references | General catalog summaries do not automatically join every Solution Library record or establish intact causal evidence. Strict history resolution is still necessary. |
| User Feedback Intelligence | Scoped feedback, preferences, corrections, and their provenance | The local feedback store is not an authenticated multi-tenant feedback service or an automatic learning pipeline. |

`core`, `learned`, and `plugin` describe provenance or placement within the
intelligence organization. They do not add three intelligence layers.
Registration and promotion are separate lifecycle decisions. Runtime Memory
is temporary and scoped to a run. The current memory-type registry contains
working, episodic, semantic, and procedural memory. Functional memory is a
useful research description of reusable capabilities, not a fifth registered
memory type. These categories do not replace the four intelligence layers.

Core Architecture is not a synonym for Core Code Intelligence. The former
provides capability ports and internal mechanics. The latter is executable
intelligence content with a particular provenance. Some current documents
still confuse these terms.

## 3. Maturity of the cognitive mesh

The labels below apply to the named behavior and inspected path. They are
not a single maturity score for the whole product.

| Area | Current evidence | What is not established |
|---|---|---|
| One canonical runtime | Implemented and checked against registered operational boundaries | Exhaustive proof that every possible hidden responsibility is correctly classified |
| Open task intake | Generic task contracts, Practitioner interpretation, typed capability refusal | Successful resolution of arbitrary unfamiliar tasks |
| Delegation and recurrence | Bounded spawning, async delegation services, local reactive scheduling, iteration | Main-product peer mesh with independently allocated cognition and live shared frontier |
| Solution execution | Typed graph contracts; deterministic, hybrid, and non-deterministic execution when the exact compatible executor and authority exist | Universal availability of every executor or modality |
| Trusted state | Narrow semantic-runtime candidate, verification, and compare-and-swap commit boundaries | Uniform accepted/speculative state separation across the adaptive solver |
| Retrieval and fingerprints | Exact identities, semantic/shape records, lexical/vector/hybrid retrieval components, n-gram experiments | Similarity as correctness, complete multi-scale composition, or proven broad transfer |
| Prior-stage assistance | `IMPLEMENTED_OFFLINE` public-solve fixture with injected provider and hydrated material; explicitly `mechanism_only` | Live product assistance, a fully frozen uncontaminated pair, canonical projection bridge, or causal benefit |
| Stage credit | Action/execution/verifier records and explicit unknown fields | Exact evaluation-subject enforcement, complete outcome vector, independently verified downstream/task contribution |
| Information diagnostics | Passive entropy, surprisal, predictive-information and paired compression/loss calculations | A live optimizer of context, compute, or memory; population-level state sufficiency |
| Procedural memory | Passive applicability/control assessments and governed capability lifecycle pieces | Qualified automatic "muscle memory" in the main solver |
| Model allocation | Mechanical eligibility, route capabilities, bootstrap rankings and advisory/shadow evidence | Per-stage semantic choice of model, context, effort, verifier, and stopping policy in one integrated allocator |
| Self-improvement | Practitioner-owned candidate/review boundaries and isolated reuse mechanisms | An autonomous continuously improving ecosystem or automatic safe self-promotion |
| Cognitive templates | Twelve unbound design cards plus existing installed profiles | A catalog of installed, qualified new cognitive executors merely because cards exist |
| Kaggle campaign | Saved metadata and source-qualification work, with explicit attrition | 100 verified task completions, one million unseen tasks, or broad AGI performance |

The model ladder is still a bootstrap recommendation. Its fixed observation
and success-share thresholds are not a learned model-demand function.
Repeated-task familiarity can justify a cheaper realization only when
contract compatibility, risk, outcome quality, negative transfer, and
verification cost support that choice. No current record makes familiarity
alone sufficient.

The newer research documents keep these boundaries reasonably clear. Their
LLM-to-small-model-to-code ladder, cognitive templates, information-value
experiments, and recurrence proposals are research inputs and candidates.
They should not be reported as installed architecture.

## 4. Findings that change the next implementation order

### F01. High: verifier evidence is not bound to its exact subject

The actual `verify_adaptive_results` producer receives a plan and results,
but its persisted `adaptive_verification/v1` record lacks the exact evaluated
plan, action, execution, and result identities. `record_action_verification`
validates the latest evaluation and separately validates the caller-supplied
execution/result pair. It does not validate a link between those two facts.

The saved offline reproduction evaluates B through the real verification
function using an injected response. It then supplies A's execution and
result to the lineage boundary alongside that genuine stored evaluation.
The boundary records `local_verification=true` and `credit=helped` for A,
although the A and B result digests differ.

This is a reproduced boundary-integrity failure. The normal sequential
wrapper supplies consistent arguments; the probe does not show that an
ordinary single-threaded solve spontaneously swaps results. Delayed
verification of an older result can be valid. The correction must bind the
evaluated subject explicitly, not merely forbid all cross-pass verification.

Source: `src/loop_engine/core/stage_action_lineage.py:355`,
`src/loop_engine/core/adaptive_practitioner_verification.py:222`.
The [probe and observed result](../evidence/architecture-mesh-audit-20260904/README.md)
are preserved with the audit.

### F02. High: adaptive integration mixes rejected and accepted artifacts

The adaptive `integrate_commit` writes `facts.last_result` and adds artifact
references for every verdict. A rejected result therefore replaces the last
result and enters the shared artifact map. A later accepted result leaves
the rejected artifact present while the last-verification field describes
the newer accepted result.

The original input state remained unchanged in this probe. Error fields
and prior history survive; the state type itself is not deeply immutable.
This is not evidence of independent Intelligence promotion or bypass of a
semantic-runtime commit token. It is evidence that the adaptive state lacks
a per-artifact accepted/speculative partition and a distinct accepted
incumbent. The same probe also reproduces an unchecked `best_index` causing
`IndexError` at integration.

Source: `src/loop_engine/core/adaptive_practitioner.py:550` and
`src/loop_engine/core/adaptive_practitioner_verification.py:202`.

### F03. High: apparently current guidance still demands retired behavior

The Constitution permits internal primitives. Several active prompt files
still demand a Loop for every constant, value, formatting operation, and
path operation. The suite index retires that strict interpretation, but
its children retain it. A glossary that calls itself normative repeats the
same conflict.

Examples: `docs/prompts/UNIVERSAL-COMPONENT-IMPLEMENTATION-MANDATE.md:149`,
`ADVERSARIAL-COMPONENT-ARCHITECTURE-REVIEW.md:75`,
`CONTINUOUS-COMPONENT-CONFORMANCE.md:63`,
`docs/architecture/GLOSSARY.md:13`, and
`docs/architecture/COMPONENT-GLOSSARY.md:39`.

This creates a practical self-improvement risk: a future agent can follow a
plausible "current" document and undo the intended architecture. Reconcile
the conflicting sources and their authority, not just the onboarding index.
Keep historical prompts available as history rather than executable mandates.

The four registered external master prompts were also fully reviewed. They
contain competing precedence rules, proposals to replace the four layers,
retired folder migrations, and a separate task-question engine design.
Translate useful responsibilities into existing Loop records and profiles;
do not instantiate a second engine. A complete comparison also found an old
instruction to retire "Static Architecture" rewritten as retiring "Core
Architecture" in the repository copy. That textual change is not current
authorization to remove Core Architecture.

### F04. High integration priority: assistance remains a mechanism fixture

The current control manifest permits only `mechanism_only`. Candidate
assistance is injected into a public solve fixture; this does not establish
autonomous retrieval from intact prior Run History. The SQLite projection
expects canonical projection-source events that the product fixture does
not yet emit through a complete bridge. Frozen metadata also does not prove
all referenced bytes or external state were frozen.

There is no valid live assisted-versus-fresh benefit claim here. The new
subject-binding defect further limits stage-credit claims. Preserve the
offline evidence, but do not promote it to learning data with exact causal
credit or expand the campaign on that assumption.

Source: `architecture.yaml:213`,
`src/loop_engine/core/solve_control_manifest.py:31`, and the dated
[public-solve verification report](PREDICTIVE-STATE-PROCEDURAL-MEMORY-AND-STAGE-ASSISTANCE-2026-09-04.md).

### F05. Medium: the main path is less dynamic than the architectural vocabulary

The adaptive `act` path iterates spawned tasks sequentially and shares its
services. The recorded frontier is constructed from completed results, not
used as a living frontier controlling execution. An omitted later question
can be marked answered by that projection; omission alone is not evidence
of a verified answer. Generic async and reactive services are useful
components, but their presence does not establish integration.

Source: `adaptive_practitioner.py:494`,
`adaptive_practitioner_records.py:2214`,
`core/task_frontier.py:290`, `loop/delegation_runtime.py:424`, and
`core/reactive_worker.py:159` under `src/loop_engine/`.

### F06. Medium: duplicated architecture descriptions disagree

| Conflict | Examples | Required interpretation |
|---|---|---|
| Core infrastructure called Core Code Intelligence | `src/loop_engine/core/README.md:3`; `docs/architecture/GLOSSARY.md:139` | Keep runtime capabilities, intelligence layer, provenance, and lifecycle separate. |
| Solution execution described as deterministic-only | `docs/components/solution-canvas/README.md:92`; `docs/contracts/README.md:103`; `docs/architecture/ARCHITECTURE-VISUAL-GUIDANCE.md:103` | All three modes require a compatible installed executor and exact authority. Unsupported execution returns a typed failure. |
| Universal doctrine says every computation is a PractitionerLoop and always tries deterministic first | `src/loop_engine/loop/loop_doctrine.py:3`, `:52`, `:69` | Roles and mode policy are explicit; a preset cannot become a universal runtime law. Some compatibility paths still consume this doctrine. |
| Intelligence portfolio examples omit model-selected references and describe rotating deterministic selection | `docs/components/intelligence-layers/INTELLIGENCE-PORTFOLIOS.md:36`, `:59` | Current selection requires explicit selected references; the example is incomplete. |
| Provenance and acceptance aliases collapse into registration | `src/loop_engine/core/context_ontology.py:229`; `docs/components/intelligence-layers/CONTEXT-HIERARCHY.md:57` | Scope legacy aliases explicitly; provenance or a commit is not independent promotion. No activation bypass was demonstrated. |
| Old maps describe a fifth social memory and one-to-one layer/memory mapping | `docs/architecture/CURRENT-ARCHITECTURE-MAP.md:426` | Do not derive current memory ontology from an older map. |

### F07. Medium: handoff and public examples overstate their guarantees

The checkpoint README promises exact full-state reconstruction, while its
script stores HEAD and status without dirty file contents or a full worktree
digest. It truncates conformance output, advertises a conformance file it
does not write, and bases its exit status only on self-test. Do not use that
checkpoint as an exact dirty-worktree handoff.

Other examples include stale security statements that omit Web Research and
MCP network effects, outdated Kaggle log paths, data examples missing their
installation extras, illustrative profile IDs absent from the live catalog,
and a Schema.org example that calls handwritten Python checks "SHACL
validation" without executing its generated SHACL shapes.

These are source/documentation mismatches, not evidence that every associated
runtime feature is broken. The
[outside-docs review](../evidence/architecture-mesh-audit-20260904/other-markdown-audit.md)
records exact paths, limits, and per-file coverage.

### F08. Medium: passing architecture gates do not certify the whole corpus

The fresh conformance run passed 27 zero-tolerance gates over 405 source
files. The broader assurance run returned `PASS_WITH_DOCUMENTED_WARNINGS`:
zero hard findings and 225 API-shape warnings over 411 files and 3,295
callables. The warnings use a three-parameter migration policy, while the
strict public-interface gate uses another configured cap and exceptions.
They are not 225 demonstrated runtime correctness defects.

The assurance inventory also labels files without matching findings
`VERIFIED_BY_CURRENT_GATES`. That label is not a full semantic review or an
ownership claim for every file. Its file denominator differs from this
audit's explicit corpus exclusions. The stale-document conformance check
does not evaluate every assertion across all Markdown files.

All 518 Python files in the corpus parsed structurally. One saved historical
evidence file failed JSON parsing with extra data:
`artifacts/verification/self_orienting_abstraction_results.json`, line 181.
That is an evidence-integrity finding, not a demonstrated live solver failure.

### F09. Medium: output-limit policy and gateway behavior disagree

The current agent instructions require the exact source-backed provider
maximum output. The gateway first resolves that maximum, then reduces an
implicitly chosen ceiling to fit the declared context window. Explicit
caller limits are treated differently and refused when they do not fit.

This is an actual policy/implementation mismatch, not just stale prose.
Reconcile which behavior is authoritative and record any permitted
adjustment explicitly. Do not silently change either policy during an
architecture review. No provider call was made to assess provider behavior.

Source: `src/loop_engine/core/model_gateway.py:740`, `:761`, and
`AGENTS.md` under Models and providers.

### F10. Medium: one known success can make a model ladder "proven"

The ladder counts all rows toward its 12-observation threshold. A local
probe supplies one successful cheap-route observation and eleven unknown
strong-route outcomes. The ladder's `proven` property becomes true and it
recommends the cheap route. This contradicts the source comment that a
single good run cannot promote a rarely used route.

The ladder remains advisory and does not itself select a live route. The
finding is about evidence sufficiency and reporting. Per-route decided
sample requirements, diversity, uncertainty, and independently checked
quality are missing. Its ranking also prefers success share before cost;
it is not an estimator of the minimum sufficient computation.

Source: `src/loop_engine/core/model_demand.py:86`, `:120`.
The [offline probe](../evidence/architecture-mesh-audit-20260904/model-ladder-probe.py)
makes no provider calls.

## 5. What the commit history establishes

The local repository contains 158 commit objects: 131 reachable from current
refs, 18 additional reflog-only commits, and nine additional unreachable
objects. The audit inspected metadata and changed paths for all 158 and
automatically read and hashed their full patches. Selected architectural
diffs received detailed semantic review. No remote fetch or object recovery
was performed.

The history records real architectural correction, including:

- `903d453`: replacing an earlier fabricated fallback success path with
  actual execution and failure preservation.
- `9dc646b`: refusing model-authored expected-output claims as artifact proof.
- `d5519a4`: preserving an omitted failed Kaggle attempt alongside success.
- `dc2b3f2`: consolidating executable identity on `Loop` and passive
  `LoopDefinitionRecord`, following earlier `LoopNode` naming confusion.
- `b43d76d`: retracting the stronger "learning loop closed" wording.
- `22ee440`: adding local outcome boundaries, followed by uncommitted
  production-path work that must not be attributed to HEAD alone.

Reflog and unreachable snapshots include abandoned experiments and duplicate
working/index states. One abandoned stage path treated schema admission as
local verification. Such code is historical evidence, not something to
restore merely because it appears in a prior prompt or commit.

The [history review](../evidence/architecture-mesh-audit-20260904/commit-history-audit.md)
records selected diffs, retractions, CI limitations, and all-commit metadata
coverage. A green local historical run does not establish current hosted CI
or current product behavior.

## 6. Review coverage and limits

The input snapshot was read between `2026-09-04T21:16:53Z` and
`2026-09-04T21:17:39Z`. Earlier and later semantic reads were checked against
its per-file hashes. The repository had concurrent agent processes and
pre-existing edits. Process names and working directories were not treated
as ownership claims.

| Corpus | Coverage |
|---|---|
| Current repository files | 1,502 files, 128,007,629 bytes read and hashed, including all 1,095 tracked files and in-scope untracked/generated material |
| Current text | 1,494 UTF-8 text files, 694,276 lines; full automated content scan, with targeted source and record review |
| Current Markdown | 280 files, 50,106 lines; full text read across the review team, including prompts, references, components, guides, examples, fixture outputs, and SKILL.md files |
| Python | All 518 files parsed for structural inventory; detailed semantic review concentrated on runtime, intelligence, evidence, verification, state, retrieval, and campaign boundaries |
| Local commits | All 158 metadata/path inventories and automated full-patch reads; detailed semantic review of selected changes, not every historical line |
| External historical prompts | Four explicitly registered files, 34,367 lines, fully semantically reviewed through direct reading and verified identical-text/base-plus-diff coverage; exact methods are recorded separately |
| Registered conversations | Only the eight named sessions and three named fragments were selected; available user-text parts were counted and hashed, not exported or treated as fully semantically reviewed |
| Binary assets | Eight assets hashed; no image, presentation, PDF, or video content inspection claimed |

The inventory reports no file read errors, no mid-read changes, and no
tracked files missing from the walk. Seventy dependency, cache, build,
distribution, or Git-internal directories were excluded explicitly. The
other worktree's current files, deleted unavailable external prompts,
unregistered chats, inaccessible remote history, dependencies, and all
historical binary contents are not part of this complete-file claim.

This is not a claim that every source line, historical patch line, external
conversation, or binary was semantically reviewed. The broad automated scan,
full Markdown reading, targeted source review, and executable probes are
different evidence levels. The requested literal "every bit of history"
review remains incomplete for source-code semantics, historical patch
semantics, and unreviewed or unavailable conversation and binary content.

The [evidence index](../evidence/architecture-mesh-audit-20260904/README.md)
contains per-file and per-commit manifests, reading coverage, exclusions,
source hashes, assurance results, and reproductions. Audit outputs created
after the snapshot are not retroactively counted among the 1,502 inputs.

## 7. Next work

The next code change should bind each verification to the exact evaluated
plan and execution/result set, reject a genuine verdict for a different
subject, and test legitimate delayed verification. Then separate the
adaptive accepted incumbent from rejected/speculative artifacts and validate
model-selected result indexes.

In parallel, reconcile the conflicting active guidance without deleting
history. Preserve the four intelligence layers and three public Core
capability groups. Generate or validate repeated mode/profile descriptions
against their structured authority.

Only after those corrections should the product-path assistance experiment
advance: retrieve real prior evidence, freeze control inputs and bytes,
capture exact requests, execute both isolated arms, independently verify
the same declared subject, and rebuild projections from canonical history.
One such pair proves the mechanism, not general benefit.

The broader cognitive mesh can then add a live frontier and bounded graph
changes, per-stage computation allocation, and qualified procedural reuse.
The five-task mixed-shape pilot remains the next campaign gate. A 100-task
count cannot repair ambiguous credit or a contaminated control.
