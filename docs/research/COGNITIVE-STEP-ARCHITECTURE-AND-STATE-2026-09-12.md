# Loop Engine: Cognitive-step architecture and current state

## Current assessment

Loop Engine is intended to turn unfamiliar tasks into verified, reusable
programs by distributing the work across small cognitive assignments. Each
independently governed assignment runs as a Loop. A Loop can use a native
implementation, a custom registered harness, or a separate external harness
process. The durable deliverable is a Solution graph that runs on new inputs
without repeating the original investigation.

The architecture has working parts. Separate harness processes can make real
model calls through the governed gateway. A live Pi-to-OpenCode handoff
recovered a rejected structured response. The adaptive Practitioner can detect
repeated work, request diagnosis, compare proposed recovery strategies, and
assess whether a lesson is reusable. These are narrower achievements than a
reliable autonomous solver.[^1][^2]

The latest Tactical diagnostics completed no tasks successfully: all six runs
failed development and sealed evaluation. They used one previously attempted
task, not six unseen tasks. Nine recovery rounds produced eight task-local
learning dispositions and one failed assessment. They produced no reusable
learning candidates and no promotions. Effective recovery and cross-task
learning remain unproven.[^2][^3]

| Question | Current answer |
|---|---|
| Have different harnesses reached Tactical? | Yes. Saved older task campaigns include nine harness families. |
| Can one cognitive assignment switch harnesses? | Yes, through an explicit finite policy. One live structured-response recovery completed. |
| Does switching harnesses solve the current task? | Not in the retained diagnostic population. |
| Can the runtime retain multiple outputs? | Yes, in bounded component paths. A live continued-production solution matrix is not yet qualified. |
| Have all combinations been tested? | No. The initial catalog contains 51,840 configurations per task; most factor levels remain planned. |
| How many task-folder tasks have been attempted? | Nine distinct task identities in the scoped Tactical evidence: eight older adapted tasks and one newer task. |
| Are the current package checks green? | The saved clean installation passed 3,839 checks and 27 conformance gates. This is not a current GitHub CI result. |
| Has the engine demonstrated self-learning AGI? | No. It has demonstrated some task-local monitoring and recovery operations, not broad generality or verified retained improvement. |

The next useful proof is small and concrete: a failed cognitive assignment
receives the exact failed contract, chooses an executable repair, applies that
repair under the existing authority, and improves an independently checked
outcome. Repeated diagnosis without an applied change is still a stall.

## Snapshot, authority, and review coverage

This checkpoint records the repository on September 12, 2026, on `main` at
`0cb7b86cb7f5b1f6a6b1b798da4e0a4a1469e00f`, with substantial uncommitted work.
The commit alone does not identify the tested implementation. The accompanying
checkpoint records source digests, dirty paths, saved result summaries, and
the observation time. All 472 current production Python files match the
source snapshot used for the final checked wheel.[^4]

Other coding sessions and background jobs share this machine. A process name
or working directory does not establish ownership. The checkpoint found no
process matching the scoped systematic or legacy task campaigns. That is a
bounded process observation, not a claim that the machine is idle.

The earlier inventory enumerated 3,577,616 file entries and 358,986 directories,
without following directory symlinks. It read and hashed all 1,721 then-tracked
files, scanned 90,186 text files, and indexed 466 production Python modules.
Its logical file-size sum was 486,220,465,118 bytes. The later 472-module count
reflects a different source snapshot.[^5]

This was broad inventory plus focused semantic review, not a human-equivalent
line-by-line reading of every dependency, dataset, binary, and transcript.
The review explicitly records that exhaustive semantic coverage is false.
Deleted, inaccessible, or externally retained sessions remain outside the
denominator. These limits matter because the folder contains large reference
repositories as well as the active product.

This report is a dated synthesis. It does not replace the Constitution,
structured architecture contracts, component contracts, or exact runtime
authority. It does not authorize a campaign, provider switch, promotion,
commit, or publication. Historical reports remain intact, including their
failures and later corrections.

## The architecture and its purpose

The research hypothesis is that task decomposition, selected context,
executable checks, search, and reusable procedures can reduce the reasoning
burden placed on one model invocation. Smaller models may then complete work
that they handle poorly in a large, undifferentiated prompt. The repository
does not yet establish superiority over frontier models, a particular model
size advantage, or local overnight task quality.[^6]

The progression in the design is specific. Prompt engineering puts expertise
into one request. Iterative prompting distributes that expertise across
follow-up requests. Loop and graph engineering makes continuation, branching,
and checking explicit. Cognitive-step engineering adds a separately configured
execution boundary for each assignment that needs independent governance.
Useful decisions and implementations can then become candidates for reuse.

The stable classification is:

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

Every executable graph vertex is a Loop. Harnesses are adapters used by
Loops. Contracts, candidates, artifacts, references, stores, and graph edges
are passive objects or internal mechanics. There is no additional operational
agent or Node class. A mode never grants model, file, network, or spending
authority.[^7]

Role-specific behavior remains organized under the same runtime:

```text
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
│   ├── Context Intelligence
│   │   └── serve, search, and frame
│   ├── Code Intelligence
│   │   └── resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence
│   │   └── search, replay, and compare
│   └── User Feedback Intelligence
│       └── serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

A Starting Practitioner can spawn a subproblem Practitioner and query an
Intelligence Query Loop. The Query Loop retrieves selected Intelligence Item
Loops. A Starting Solution runs a pipeline through Connected Solution Loops.
Spawned Solution Loops are appropriate for actual dynamic branches, repairs,
fallbacks, or ensemble members. These relationships are not interchangeable.

The shared Core Architecture exposes only three public capability groups:

```text
Public capabilities available to authorized Loops
├── Intelligence Search and Retrieval
├── Web Research
└── Custom Plugins
```

Shared browsing, retrieval, and custom tools belong behind these existing
ports. Providers, settings, workspaces, approvals, stores, Runtime Memory,
Run History, reports, and playback remain internal mechanics. A capability is
not a graph vertex, but the work that uses it must belong to a classified
Loop. A harness's own browser or tool implementation is an adapter choice,
subject to the same authority and qualification requirements.

### Two different graphs

The Practitioner graph records how the work was discovered: interpretation,
retrieval, alternatives, experiments, failures, and verification. The Solution
Canvas records what executes for a new input. Both use the same Loop runtime,
but they answer different questions.

For a data task, the investigation might compare feature transformations and
candidate algorithms. The delivered Solution should identify the accepted
preparation, training or model-loading, and prediction work, with exact
dependencies and typed interfaces. Test-label scoring remains outside the
candidate's training and prediction boundary.

Reusable does not mean that every Solution must be deterministic. An accepted
Solution may still contain a model-using Loop where semantic work is needed.
Mode belongs to each Loop; the Canvas can restrict permitted member modes but
does not have one execution mode of its own. The in-process Solution runner
supports all three modes with compatible executors and the required model
authority. Unsupported combinations return a typed failure.[^8]

`LoopGraphDefinition` already supplies versioned, digest-bound graph identity,
and rendering supports JSON and Mermaid views. A dependency-wave executor
also exists. The ordinary adaptive path has narrower per-action Solution
compilation and serial governed delegation; these components do not establish
general autonomous multi-part graph construction. Portable execution on a
fresh machine, a DAG scheduler, or Kubernetes remains a separate export and
replay proof.[^5][^6]

## The discrete cognitive assignment

A useful assignment asks one inspectable question or performs one bounded
act: identify missing evidence, choose a capability, interpret a failed
command, propose a small implementation, or compare a result with an expected
contract. Its output must be useful to a specific consumer. A long explanation
without a checkable decision is not sufficient.

An independently governed assignment needs an exact identity, objective,
profile, typed inputs and outputs, authority, loop and exit conditions, and a
return destination. Ordinary calculations remain inside their owning Loop.
Launching another Loop for every string comparison would add overhead and
recursive configuration without adding useful governance.[^7][^9]

Logical granularity and process lifetime are separate. One small semantic
assignment can involve several model or tool calls inside its harness. The
current external path starts a fresh confined process per semantic attempt.
Future process pooling would require evidence that state, instructions, and
permissions reset correctly between assignments.

Atomic, compact, reference nine-step, and custom step profiles remain possible
choices. The number of procedure steps is not a new role, run mode, or level
of model intelligence. The appropriate granularity is an experimental
question: too much work in one response can overload its contract, while
excessive splitting can lose context and increase handoff cost.

The intended cognitive-act cycle is a workflow, not a second runtime:

```text
Bind the assignment and expected observation
  -> inspect the current evidence
  -> select an eligible method or harness
  -> perform the authorized act
  -> admit and interpret the observation
  -> compare it with the expectation
  -> accept, repair, reorient, or stop under the owning Loop's contract
```

Cheap controls should be deterministic where their meaning is known. Schema,
path, permission, deadline, digest, and required-field checks do not need a
model to restate them. Semantic uncertainty can require a separate
model-using assignment. Neither kind of check should impersonate independent
task acceptance.

Current response, method, and recovery boundaries implement parts of this
cycle. Universal before-and-after semantic checking of every directory scan,
API action, or mutation is not yet wired. Phase names in a log do not establish
meaningful calibration. Some kernel phases execute inside an outer Loop's
`act`; counting only outer phase labels can also miss real inner work.[^5][^10]

The default kernel forecast reports `forecast_made: false`, and its default
calibration reports `compared: false` when no forecast was supplied. Meaningful
expectation checks therefore need actual bound observations or an installed
implementation, not just the presence of a forecast/calibration phase.
See the [kernel defaults](../../src/loop_engine/loop/kernel.py).

## Expectation checks and reorientation

The question "Is this what I expected?" should bind a prediction or contract
before an operation and assess the actual observation afterward. It should
not become a generic model request to approve whatever just happened.

| Boundary | Expectation to bind | Useful response to a mismatch |
|---|---|---|
| Directory inspection | Approved root, listing scope, completeness, and required evidence | Distinguish an empty directory, denied access, truncation, missing mount, and wrong path. |
| Model response | Exact operation and prompt identity, schema, normalization policy | Reject malformed structure; return safe diagnostics to a repair assignment. |
| Capability selection | Capabilities compatible with the chosen action and grant | Refuse an impossible method before spending calls trying to describe it. |
| Reference resolution | Scope, revision, schema, content digest, and access decision | Report missing, stale, changed, incompatible, and denied material separately. |
| Tool or API action | Exact effect request and expected state transition | Reconcile uncertain effects before retrying; inspect changed state before continuing. |
| Verification | Exact candidate identity, evaluator identity, metric and acceptance rule | Preserve a failed or inconclusive result; do not substitute model confidence. |

The directory, reference, and tool examples describe the target coverage, not
a claim that every such boundary already has this complete check. The model
path has an implemented `ObservationExpectation` and `ModelResponseContract`.
They bind the expected structure before dispatch and retain the response
identity when admission fails.[^10]

Permitted presentation repair can remove an exact JSON fence, an approved
preamble, or one JSON-string encoding layer. It cannot invent a missing
field, alter a value, accept duplicate keys, or infer authority from text.
Required field names are disclosed only under the response policy. Schema
admission proves that the consumer can inspect the response, not that the
response is true.

The progress comparison now ignores changing occurrence IDs, pass numbers,
confidence, estimates, and rewritten explanations. It compares material
evidence and executable action inputs, including non-adjacent repetitions.
An optional unchanged-evidence diagnosis can run even when the action changes.
That signal is advisory: a different action with no new evidence can be
legitimate exploration. The signal does not itself choose a terminal route.

One live failure exposed why these checks belong before the handoff. Both
arms selected `COMPOSE_SOLUTION` with an empty capability list. The installed
planner could not construct a valid execution method for that choice.
Repeatedly trying a different harness could not satisfy an impossible shared
contract. The prerequisite is now enforced at action admission. This is a
constraint of the current planner, not a universal prohibition on other
Loop bodies composing Solutions.[^2]

## Harness processes and information handoff

The minimum launch packet should make the assignment and its limits clear.
It should carry the essential facts inline and make additional material
discoverable through small, typed references.

| Packet field | Required meaning |
|---|---|
| Assignment identity | Definition, activation, responsibility, semantic-call identity, and return destination |
| Contracts | Input/output schemas, invariants, explicit uncertainty or refusal states, and normalization policy |
| Critical context | Necessary task constraints, current evidence, unresolved question, and relevant prior failure |
| Reference manifest | Content identities, descriptions, revisions, digests, schemas, sizes, provenance, and scope |
| Resources | Exact selected skills, instructions, tools, plugins, and staged files |
| Authority | File, tool, model, network, effect, and spending decisions, separately bound |
| Lifecycle | Continue/exit conditions, remaining work authority, deadline, cancellation, and emission policy |
| Observability | Output references, safe decisions, physical usage, failures, and effect state |

These are contract responsibilities, not a proposed universal dictionary that
bypasses existing types. Current authorities include `HarnessRunRequest`,
`DelegationSpec`, `ContextVisibilityPolicy`, `InformationResolver`, and
context artifacts. Extend an existing boundary when it already owns the
meaning.[^8][^11]

Inline, reference-based, and mixed delivery are legitimate experimental arms.
Inline delivery minimizes retrieval dependencies for a small assignment.
References keep large optional bodies out of the initial context. Mixed
delivery can provide the objective and schema immediately while letting the
worker select supporting material. None has been established as the universal
winner.

A pointer is not sufficient by itself. The recipient needs to know what it
refers to, whether it is relevant, which revision is intended, and whether
access is permitted. Possession of a reference does not grant access. The
central catalog can retain metadata while immutable bodies remain in the
existing artifact store. This does not require a new memory database.

The current qualified harness profile is narrower than the full vision.
External harnesses receive brokered text-proposal work. Native harness tools
are disabled. The confined process has no provider credential or general
external network access; private IPC reaches the canonical gateway. The
engine verifies the original semantic packet against the actual harness
envelope and binds responses to real broker results.[^12]

This proves process-backed semantic execution. It does not yet prove a
tool-rich harness that independently browses, loads skills, retrieves code,
and exchanges durable artifacts with another harness across process death.
That producer/consumer proof still needs explicit positive and negative
controls for missing objects, stale revisions, changed digests, denied scope,
and schema mismatch.

Measure actual material loaded and the complete harness prompt envelope.
Starting with a short pointer and then loading the entire archive does not
demonstrate context savings. Process startup, resolver traffic, failed loads,
and provider-reported usage belong in the comparison.

## Harness choice, fallback, and forks

There is no qualified universal winner among Pi, OpenCode, Codex, native
gateway execution, or other harnesses. A harness that handles one response
shape well may add unnecessary cost to another assignment. Comparing them
requires the same task information, model route, evaluator, and declared
effort, while retaining each harness's actual prompt overhead and behavior.

The implemented `HarnessFallbackPolicy` uses an explicit finite order of
registered alternatives. Each attempted harness gets a fresh canonical
Spawned Practitioner Loop, request identity, and workspace. The original
semantic packet, system context, model route, and output allocation remain
bound. Later attempts receive bounded failure observations, not an inherited
conversation or arbitrary working tree.[^13]

Used calls and tokens remain charged to the shared authority. The deadline
does not reset. Unknown accounting, possible external effects, shared provider
failures, exhausted authority, and unclassified failures do not authorize
another attempt. The current fallback path concerns text proposals; it does
not silently replay a file write or API mutation.

Several different behaviors must remain distinct:

```text
Changing the way work proceeds
├── Transport retry: retry an eligible failed request
├── Formatting repair: recover the required response representation
├── Harness fallback: another registered adapter tries the same assignment
├── Provider failover: a separately authorized provider route changes
├── Semantic repair: change a proposal after meaningful feedback
├── Task replanning: change the work decomposition or strategy
└── Portfolio generation: deliberately retain additional valid candidates
```

The present fallback policy stops after the first admitted response. It does
not generate a portfolio or learn which harness should be first. Forks can be
separately registered, with their own identities and pinned configurations.
Installation or an upstream feature list is not integration qualification.
No automatic installation occurs during discovery.

The current campaign route remains Tactical Engineering with
`gemma-4-coding-abliterated`. Ollama failover is disabled. The reported
roughly 30-hour Ollama reset is an estimate, not a verified reset time or a
scheduled provider switch.[^2]

## Multiple outputs and a matrix of Solutions

The design requires a Loop to be able to publish an early candidate and
continue exploring. Later outputs may be better, worse, equivalent, or useful
under different constraints. A consumer can act on an available candidate
without pretending the producer has finished every authorized investigation.

Five dimensions need independent definitions:

| Dimension | Example |
|---|---|
| Response schema | One proposed transformation with a named typed contract |
| Consumer input cardinality | One selected candidate or a portfolio snapshot |
| Producer lifecycle | Produce once or continue while authorized |
| Emission policy | Publish provisional candidates or independently verified candidates |
| Serving/selection policy | Exact candidate, first verified candidate, current best under a stated metric, or several alternatives |

One response schema can have many candidate instances over time. A response
containing a list is a separate choice. A consumer's number of outputs does
not determine its permitted inputs.

The runtime has bounded multiple-output support, and `Loop.result()` can
expose admitted outputs while a multiple-output Loop remains active. Reactive
candidate, evaluation, lease, and output-store components also exist.
Two contract issues remain before treating the combined path as qualified:
consumer output cardinality is used in an input-compatibility decision, and
new output fields affect historical definition digests without a matching
encoding version change.[^5][^14]

An emitted candidate should bind its producing activation, exact input
revision, definition, payload digest, and evaluation state. A consumer records
the exact candidate it used. A later output must not silently rewrite a
completed branch. A new branch or activation can compare the alternative;
committed effects still require explicit reconciliation.

For example, three candidate feature transformations and two candidate
estimators yield six proposed compositions before compatibility checks:

| Transformation | Estimator A | Estimator B |
|---|---|---|
| Candidate 1 | Composition 1A | Composition 1B |
| Candidate 2 | Composition 2A | Composition 2B |
| Candidate 3 | Composition 3A | Composition 3B |

This table is a design example, not a saved campaign result. A composition
must pass type, dependency, data-leakage, authority, and evaluation checks.
Five alternatives at ten positions would produce 9,765,625 combinations.
The search therefore needs an explicit strategy for scheduling, deduplication,
pruning, diversity, and stopping. Exhaustive branching is not automatically
useful learning.

The current evidence does not establish a live end-to-end harness workflow
that emits early candidates, keeps producing alternatives, evaluates their
combinations, and updates a consumer graph correctly. That remains a central
proof obligation, not a feature to infer from the word `multiple`.

## Intelligence, fingerprints, and retained learning

The persistent intelligence structure stays fixed:

```text
Persistent intelligence
├── Context Intelligence
│   └── Procedures, question sets, response templates, and failure guidance
├── Code Intelligence
│   └── Qualified functions, validators, adapters, and Solution components
├── Runtime History and Solution Intelligence
│   └── Reviewed attempts, failures, comparisons, graphs, and reuse outcomes
└── User Feedback Intelligence
    └── Scoped preferences, corrections, constraints, and explicit decisions

Run-local working state
└── Runtime Memory
```

Markdown, skills, repositories, transcripts, vectors, and packages are source
or distribution formats, not additional intelligence layers. Harness binaries,
provider credentials, stores, and process supervisors remain runtime
mechanics. A usage procedure can become Context Intelligence; a qualified
executable asset can become Code Intelligence.

Code admission requires immutable source identity, provenance, license state,
version, dependencies, typed contracts, effects, tests, independent
verification, and a digest. Generated or imported material remains candidate
only until the separate approval process permits active use.[^7][^15]

Fingerprints also have different meanings. An occurrence ID identifies one
event. A progress projection detects repeated observable work. An exact
computation identity must cover all result-relevant inputs, state,
implementation, environment, contracts, and effect constraints. Embeddings,
SimHash, or other locality signatures retrieve related candidates; similarity
does not prove equivalent answers.

Lexical/vector retrieval, optional model2vec support, SimHash metadata, and
governed deterministic reuse already exist. The reuse fixture includes a
promoted capability used by an adaptive Practitioner with zero model calls.
That is offline mechanism evidence, not a measured live transfer benefit or
economic saving. Some stage signatures deliberately omit values and
provenance, so they are unsuitable as sole exact-result cache keys.[^5][^15]

Millions of prior runs are not necessary to invoke a known, verified pure
function under an exact contract. Broader learned applicability and routing
do need evidence. Effects, freshness, and changed dependencies can invalidate
reuse even when the visible question looks identical.

The implemented optional recovery-learning assignment uses
`practitioner.self_improvement@1.0.0`. It receives a small recovery packet and
chooses `ephemeral_task_only` or `requires_validation`. The existing
`LearningCandidate` and `LearningBundle` records retain proposed learning in
run-local artifact staging. No new persistent store or self-promotion path
was introduced.[^10][^16]

A recovery proposal can itself be wrong. Capturing a lesson before its repair
has succeeded requires that uncertainty to remain visible. In the latest
diagnostics, the model did not produce any reusable candidate. Eight
assessments explicitly kept the observation task-local; one assessment
failed.

Task-local monitoring is therefore observed. Retained cross-task improvement
is not. The engineering fixes made during development are also not evidence
that Loop Engine autonomously changed its own architecture.

A useful learning experiment would expose an enabled arm to task family A,
independently review any resulting candidates, freeze them, and compare that
arm with memory-disabled or frozen-memory controls on fresh family B. It
would verify that the selected material actually affected the new assignment,
measure quality and effort, and retain negative transfer. No such qualified
live result is established by this checkpoint.

## Experiment history and denominators

### Repository and session review

The earlier review indexed 715 scoped transcript/session records: 63 Codex,
618 Claude Code, and 34 OpenCode. These include subordinate sessions and
related probes, not 715 independent human conversations. The direct sets
contain 50 Codex rollout files, 36 Claude transcript files, and 21 OpenCode
database sessions. A separate Codex history index contributed 166 relevant
entries across eight session IDs.[^5]

The recurring direction was consistent: small cognitive assignments,
selective context, interchangeable harnesses, visible failures, independently
verified work, and reusable Solutions. Copied projects supplied possible
mechanisms, not authority to merge those projects into the product. Private
transcript bodies are not reproduced here.

### Earlier component and task studies

| Study | Retained observation | Limit |
|---|---|---|
| September 9 harness expansion | Eleven projects completed real-inference component phases; 33 calls; 30 verified task/harness pairs of 34 attempted and 36 planned, over three function tasks. | Ollama Cloud, not Tactical. Component population, not a general harness ranking. |
| Earlier T1 transport qualification | 17/19 transport passes. | Transport success is not task quality. |
| September 10 full-solve qualification note | 14/17 passes with fixture replies. | Exercises local integration; does not prove provider or model performance. |
| Older Tactical snapshot | 66 surviving cells, 73 saved event files, 3,362 model-invocation records. | Frozen at 08:53:19 UTC; not the later total or an exhaustive provider ledger. |
| Refreshed older Tactical files | 80 surviving cells across eight task identities and nine harness families. | Repeated attempts, historical overwrite risk, and unqualified old evaluators prevent a valid aggregate success rate. |
| Newer systematic task baseline | Native, OpenCode, and Codex: 0/3 development and sealed passes. | One density-normalized-neighbor task; interrupted diagnostic arms. |
| Cognitive-act recovery studies | Six further runs on that same task: 0/6 development and sealed passes. | Three changing source snapshots, not a matched six-run performance study. |

The historical component counts above come from the dated reports and their
reviewed correction trail. They must not be pooled across providers, tasks,
versions, or evaluator types.[^5]

The old 3,362 invocation records include 3,356 explicitly recorded Tactical
`gemma-4-coding-abliterated` identities and six unknown identities. Known token
subtotals were 67,629,533 input and 1,831,776 output. These are saved-event
subtotals, not billing totals. Model identity means the integration's recorded
route, not independently verified server weights or hardware.

Three positive old gate records remain in the history: two OpenCode scores
of 1.0000 and one Codex score of 0.7438. All retained
`BLOCKED_MATERIAL_INPUT` as the engine terminal. More importantly, all eight
adapted evaluators exposed target labels to `predict(dict(row))`. A synthetic
label-copying control passed all eight. The two perfect-scoring saved
implementations also trained on the full CSV that the evaluator later sampled
as a holdout. Those results do not establish held-out generalization.[^5]

The September 6 novel-task report is a separate population and provider.
Its opening 10/10 account and later 9/10 account were subsequently corrected:
three prompts contradicted their cases, and the claimed 10 percent
false-acceptance rate was not supported by the retained audit. The correction
section governs interpretation. That campaign also separated run stores, so
it did not measure cross-task learning.[^17]

### The current task-folder count

The refreshed legacy projection contains these eight task identities:

| Task | Surviving legacy cell records |
|---|---:|
| `1-c-qualification-data-analysis` | 10 |
| `20-newsgroups-ciphertext-challenge` | 9 |
| `2022-ucs654-Lab-2-Exam` | 12 |
| `3-d-cn-ns-on-geometric-shapes` | 9 |
| `4-day-ioai-prepration-challenge-series-1` | 13 |
| `Kannada-MNIST` | 9 |
| `aaiv-2026-ii-taller-cnn-miaa-mcd` | 9 |
| `ai-assignment-2-summer-2026` | 9 |
| Total | 80 |

The additional task is `1-c-qualification-machine-learning`, adapted as
`density_normalized_neighbors_v1`. It raises the scoped distinct count to
nine, regardless of how many times it was retried. This count excludes
unrelated function tasks, other-provider campaigns, and unknown missing
attempts. It is not a count of successfully solved Kaggle competitions.[^4]

### Tactical capacity and initialization probes

The configured endpoint is
`https://ai.tacticalengineering.net:6969/v1`. A saved boundary probe reported
a shared sequence limit of 262,144 tokens when presented with 300,001 input
token IDs. The server's calculation was
`262144 - 300001 = -37857`. This is evidence for that deployment's shared
input-plus-output limit, not a separate 262,144-token output allowance.[^18]

Earlier acceptance of `max_tokens=1048576` with a short completion did not
establish that output capacity. Current diagnostics used an explicit
65,536-token response allocation, with call and pass totals unset, a
1,200-second invocation timeout, endpoint pacing, and cancellation. Capacity,
per-request allocation, exact context fit, and total-run authority remain
different facts. A character-based fit estimate is not a qualified exact
tokenizer bound.

Setup failures are retained separately from model failures. These included
missing host directories, preflight settings failures, and an interrupted
full-capacity diagnostic whose server completion remained unknown. An older
Pi preflight's reported zero calls was corrected to unknown accounting in a
derived record; the original artifact was retained. Unknown does not mean
zero.

### Per-step fallback diagnostics

| Attempt | Observed result | Physical calls |
|---|---|---:|
| `pi-36eebc5872` | Pi response rejected; no fallback configured. | 1 |
| `live-chain-c7412f7174` | Pi rejected, OpenCode admitted; outer wrapper then violated an accounting invariant. Overall failure. | 2 |
| `live-chain-70c28bc6ee` | Pi rejected, OpenCode admitted; enclosing cognitive assignment completed. | 2 |
| `preflight-opencode-d48cefa4f0` | OpenCode, Pi, and Codex all rejected; order exhausted. | 3 |

The successful handoff used Pi 0.85.1 and OpenCode 1.17.9. Codex 0.153.4 was
the unused third alternative. It took 67.298 seconds for the invocation and
reported 963 input plus 64 output tokens. Its 70-event history chain verified,
and playback produced 37 lines. Cost is unknown.[^1]

The failed wrapper counted delegated physical calls as the outer Loop's own
calls. The canonical runtime correctly refused that accounting. The wrapper
was corrected, and a regression control checks that two actual gateway calls
produce exactly two invocation records. Different markers, response
requirements, and the intervening fix prevent treating these four attempts as
one frozen success-rate experiment.

### Cognitive-act diagnostics

All three studies used the original 3,500 training points, eight development
queries, and 48 fresh sealed queries per study. Independent scalar and vector
references agreed. Real isolated positive and negative evaluator controls
passed. The task is density-normalized nearest-neighbor selection, not a
complete general Kaggle workflow. Fresh queries on this previously attempted
task do not make the task unseen.[^2][^3]

Each study compared native execution with an OpenCode-first fallback policy
permitting Pi and Codex. The policy's presence does not mean every alternative
ran on every semantic assignment. Candidate files were frozen before sealed
results were released. A frozen candidate can still be an unchanged failing
placeholder; freezing is not proof that source generation succeeded.

| Study | Arm | Saved terminal | Known calls | Total known? | Elapsed seconds | Recovery rounds |
|---|---|---|---:|---|---:|---:|
| `4dvatL` | Native | `CANCELLED` | 69 | No | 1,376.697 | 1 |
| `4dvatL` | OpenCode-first | `NO_PROGRESS` | 21 | Yes | 421.142 | 0 |
| `y2dvqH` | Native | `NO_PROGRESS` | 11 | Yes | 206.452 | 0 |
| `y2dvqH` | OpenCode-first | `NO_PROGRESS` | 19 | Yes | 386.341 | 0 |
| `lRaw69` | Native | `CANCELLED` | 51 | No | 1,025.567 | 6 |
| `lRaw69` | OpenCode-first | `BLOCKED_MATERIAL_INPUT` | 31 | No | 629.378 | 2 |

Every row failed development and sealed evaluation. The known physical-call
subtotal is 202. Three totals are complete; the three interrupted totals
remain unknown. Cost is unknown in every row. Per-arm elapsed values include
their diagnostic conditions and are not a fair harness speed ranking.

The last OpenCode-first arm was interrupted after repeated recovery; it saved
`BLOCKED_MATERIAL_INPUT`. Operator intent and the reported terminal are
preserved separately. No terminal was rewritten to improve consistency.
All six saved event chains verified in the recovery summary.[^3]

The first study lacked the later method contract. The second exposed the
impossible empty-capability composition. The third included capability
prerequisites and recovery before an action could execute. The studies also
changed query instances. They explain defects and mechanisms, but they cannot
support a pooled treatment effect.

## Changes made and verification

The recent implementation changes follow the existing cognitive-act
architecture. They add checks and optional assignments rather than replacing
the runtime or removing native and custom execution choices.[^2][^10]

| Area | Implemented change | Remaining limit |
|---|---|---|
| Response admission | Versioned schema and explicit meaning-preserving normalization before consumption | A structural pass is not semantic correctness. |
| Method planning | Bind methods to the selected action and permitted capabilities; refuse impossible prerequisites | The combined action record may still demand too much at once. |
| Progress detection | Ignore volatile metadata; detect repeated actions and unchanged material evidence | Detecting a stall does not select a useful repair. |
| Recovery | Diagnose, propose, and adjudicate; optionally enter before action execution after response repair is exhausted | The selected change is not yet proven to be applied effectively. |
| Recovery learning | Optional small self-improvement assignment; candidate-only existing artifacts | No reusable candidate or promotion in the latest live studies. |
| Harness fallback | Fresh registered attempts with preserved packet identity and shared accounting | Configured order, text-only proposal profile, no learned ranking. |
| Accounting and effects | Preserve gateway errors and physical usage; unresolved effects block later invocations | Interrupted server work can leave totals unknown. |
| Package integrity | Regenerate the six-entry ontology index through DuckDB; correct a string-valued test result to Boolean | These repairs do not validate broader model quality. |

`diagnose_unchanged_evidence` and `capture_recovery_learning` are separate
public request settings. Both default to false. Enabling them supplies no
additional model, tool, file, spending, or promotion authority.

The latest qualification is:

| Check | Saved result |
|---|---:|
| Focused source checks | 242/242 |
| Embodiment application checks | 21/21 |
| Clean installed full suite | 3,839/3,839 |
| Clean installed conformance | 27/27 |
| Current Python source versus checked package source | 472/472 files match |

The clean installation used Python 3.10, base dependencies, and DuckDB.
Optional suites requiring MCP, model2vec, NumPy, OpenTelemetry SDK, pandas,
or scikit-learn were not exercised. This is neither a complete optional
integration qualification nor a GitHub CI verdict.[^2][^4]

Earlier full-suite attempts exposed a stale catalog index, a non-Boolean test
result, temporary-filesystem quota exhaustion, and a Unix-socket path-length
limit. Those failures remain in their historical reports. The final suite
used a short dedicated temporary path on the main filesystem. The final wheel
also includes an import-only consolidation that reduced an 801-line live
module to the 800-line source limit; it did not change the live algorithm.

Passing the suite means the checked assertions passed. It does not close
known behavioral gaps that those assertions do not yet cover.

## Open defects and evidence limits

| Issue | Evidence and consequence | Required next proof |
|---|---|---|
| Legacy evaluator leakage | All eight old adapters exposed targets; saved perfect-score implementations trained on evaluator source rows. | Freeze splits before training, expose features only, and score sealed labels separately. |
| Host verifier containment | A finite canary's descendant wrote after the parent timeout; output capture was not truly byte-bounded. The relevant source shape remains. | Process-tree cancellation, bounded capture, exact candidate binding, and qualified isolation. The new diagnostics use a separate qualified Docker path. |
| Historical definition compatibility | The new reader rejected an unchanged old `loop_definition/v1` digest after output fields were added. | An explicit versioned encoding or migration that validates the original digest. |
| Port cardinality | Producer/consumer compatibility uses the consumer's output setting to judge incoming multiplicity. | Separate input cardinality, response schema, lifecycle, and selection. |
| Reward validity | Empty trajectories received credit; structural markers could score highly despite missing artifacts; unknown score could be treated as zero. | Outcome-bound, evaluator-bound labels and explicit unknown handling before learning or promotion. |
| Attempt identity | The legacy campaign can replace a task/arm directory and merge away prior rows. | Immutable attempt IDs and explicit selection or regrading records. |
| Recovery execution | Diagnosis and proposed strategies recur without a verified implementation. | Bind exact failure and legal repair choices; prove the selected change reached execution and helped. |
| Context and tool integration | Brokered text-only harnesses do not exercise the full tool-rich vision. | Separate process/reference handoff and authorized tool/skill loading tests. |
| Generalization and reuse | No qualified cross-task transfer or smaller-versus-frontier comparison. | Fresh task-family controls, attribution, negative-transfer checks, and complete accounting. |
| Solution delivery | Serialization and execution components exist; general clean-workspace graph export/replay is unproven here. | Run the delivered graph without the original investigative state or undeclared paths. |

The first six findings retain their original reproduction details in the
review appendix. The later cognitive-act changes did not fix all of them.
The checkpoint source manifest makes the inspected versions recoverable.
No failure is removed because a different path or later unit test passed.[^5]

The next-action response-failure recovery path still needs the exact failed
contract in its model-state packet, alongside a small executable set of
repair choices. The method-planning path supplies more of that context.
Repair selection should be followed by an application record and an
independent observation of the changed outcome. This is a proposed next
extension, not completed behavior.

## Systematic comparisons and the next proof sequence

The initial task catalog contains 318 raw directories: eight previously
attempted tasks, 47 missing data, 188 requiring metadata recovery, and 75
requiring task/evaluator admission. The initial 310 fresh candidates were
catalog candidates, not 310 executable held-out tasks. The subsequently used
neighbor task must no longer be treated as fresh.[^4][^18]

The 188 malformed descriptions were primarily saved Kaggle rate-limit error
content. One metadata-recovery probe succeeded, but bulk recovery and
admission were not completed. Folder presence is not a task contract. Each
admitted task needs its source, files, ambiguity decisions, leakage boundary,
metric direction, evaluator, sandbox policy, and frozen identity.

The initial comparison catalog is:

| Factor | Levels | Catalog maturity |
|---|---:|---|
| Harness | 20 | Native plus 19 manifests; qualification is separate from installation |
| Context | 3 | Planned |
| Skills | 2 | Planned |
| Tools | 3 | Planned |
| Intelligence | 3 | Planned |
| Default first steps | 3 | Planned |
| Initialization | 2 | Planned |
| Output behavior | 2 | Planned |
| Temperature | 2 | Planned |
| Expectation policy | 2 | Planned |

The product is 51,840 configurations per task, or 16,070,400 theoretical cells
for the initial 310 candidates before admission. These are catalogued cells,
not executed trials. The later fallback and recovery controls also require
exact versioned representation in any new experiment manifest.

The program should preserve the broad search objective while advancing through
proof gates. It does not need to assume that every invalid combination is
executable or invent a replacement total-call ceiling.

| Order | Experiment or correction | Completion evidence |
|---|---|---|
| 1 | Applied recovery on a small failing assignment | Exact expected/observed difference, chosen legal repair, applied change, independent improvement, and retained failures |
| 2 | Separate producer/consumer harness handoff | Producer exits; independently launched consumer resolves the correct immutable reference; negative controls refuse correctly |
| 3 | Small cognitive-step decomposition | Compare combined action selection with smaller capability, method, and verification assignments under the same information and authority |
| 4 | Continued candidate production | Early usable candidate, later alternatives, exact consumer bindings, no hidden overwrite, correct cancellation and terminal behavior |
| 5 | Controlled harness/resource comparisons | Fixed task and provider; single-factor ablations and declared interaction tests; all attempts and uncertain usage retained |
| 6 | Reusable Solution delivery | Accepted typed graph executes in a fresh workspace with declared dependencies and independent evaluation |
| 7 | Reviewed learning transfer | Experience on one population improves fresh tasks relative to frozen or memory-disabled controls, without hidden holdout exposure |
| 8 | Broader admitted task campaign | Frozen denominator and selection rule; real full-system path; failure, time, usage, cost state, and evaluator evidence for every cell |

The harness comparison should include fixed Pi, fixed OpenCode, fixed Codex,
native execution, and explicit fallback as separate treatments. A fallback
policy is not a fourth independent model. Record which harness actually ran
at each assignment and how much work preceded a usable response.

Context, tools, skills, plugins, initialization files, intelligence exposure,
model settings, first-step procedures, and cognitive granularity should have
versioned identities. Initial ablations can isolate contribution; later
interaction studies can test combinations. A learned runtime selector should
rank only eligible implementations using reviewed evidence relevant to the
assignment, not names, filenames, or unqualified confidence.

Useful metrics include independently verified task quality, response-admission
rate, time to first verified candidate, later-candidate improvement, physical
model calls, actual context loaded, tool effects, cancellation, accounting
completeness, human intervention, and negative transfer. Cost stays unknown
when it cannot be reconciled. A best-of-many result must state how many
attempts were made and how selection occurred.

The full-system benchmark boundary remains:

```text
Frozen real task population
  -> Starting Practitioner
  -> reviewed Context and executable Code Intelligence
  -> bounded Spawned Loops
  -> candidate comparison and verification
  -> compiled and executed Solution Canvas
  -> independent evaluator
  -> verified Run History, playback, and report
```

Transport probes, fixture tests, partial paths, and deterministic replays
remain useful. They must retain those labels.[^7][^9]

## Folder map and continuation record

| Location | Current role |
|---|---|
| `src/loop_engine/` | Active Python runtime, contracts, intelligence boundaries, adapters, and public solving |
| `architecture.yaml`, `terminology.yaml`, `docs/contracts/` | Structured architecture and contract authority |
| `docs/components/` | Current component behavior and limits |
| `docs/research/`, `docs/verification/` | Dated design synthesis and measured checkpoints; later corrections matter |
| `embodiments/`, `devtools/embodiment_lab/`, `devtools/embodiment_axes/` | Registered configurations, qualification applications, and experimental variations |
| `overnight/`, `new_overnight_build/`, `speculative_prompting/`, `vigil/`, copied Taedri material | Reference designs, not automatically active product components |
| `artifacts/`, `.loop-engine-dev/`, external task-run directories | Evidence and generated study output with distinct ownership and populations |
| `/home/username/task_database/` | Raw task collection and existing adapters; admission remains necessary |

No copied reference folder was moved or deleted for this checkpoint. Cleanup
should first label active code, experiments, references, and historical
evidence by provenance. Physical moves require an ownership check and a
review of absolute paths used by active processes. Unique source and failed
attempts should remain recoverable. The separate `/home/username/taedri.dev`
repository remains a design reference, not a merge source.[^19]

The source locations most relevant to the next implementation are:

| Responsibility | Authoritative source |
|---|---|
| Public request and terminal outcome | [solve_runtime.py](../../src/loop_engine/code_nodes/solve_runtime.py) |
| Adaptive assignments and response contracts | [adaptive_practitioner_records.py](../../src/loop_engine/core/adaptive_practitioner_records.py) |
| Capability-bound method planning | [adaptive_practitioner_planning.py](../../src/loop_engine/core/adaptive_practitioner_planning.py) |
| Material progress comparison | [adaptive_practitioner_supervision.py](../../src/loop_engine/core/adaptive_practitioner_supervision.py) |
| Recovery diagnosis, proposal, and adjudication | [adaptive_practitioner_recovery.py](../../src/loop_engine/core/adaptive_practitioner_recovery.py) |
| Candidate learning capture | [recovery_learning.py](../../src/loop_engine/core/recovery_learning.py) |
| Observation and admission contracts | [observation_expectations.py](../../src/loop_engine/core/observation_expectations.py), [model_response_admission.py](../../src/loop_engine/core/model_response_admission.py) |
| Shared model authority and accounting | [solution_model_port.py](../../src/loop_engine/code_nodes/solution_model_port.py) |
| Harness selection, attempt isolation, and recovery | [harness_configuration.py](../../src/loop_engine/core/harness_configuration.py), [harness_semantic.py](../../src/loop_engine/core/harness_semantic.py), [harness_fallback.py](../../src/loop_engine/core/harness_fallback.py) |
| Reference materialization | [information_access.py](../../src/loop_engine/core/information_access.py), [context_artifacts.py](../../src/loop_engine/core/context_artifacts.py) |
| Output lifecycle | [reactive_contracts.py](../../src/loop_engine/loop/reactive_contracts.py), [reactive_outputs.py](../../src/loop_engine/loop/reactive_outputs.py), [reactive_output_store.py](../../src/loop_engine/core/reactive_output_store.py) |
| Experiment launch and evidence | [systematic_runtime.py](../../devtools/embodiment_lab/systematic_runtime.py) |

The accompanying [checkpoint evidence directory](../../artifacts/state-checkpoint-20260912-OtPgn5/README.md)
contains a derived DuckDB database, JSON exports, and a reproducible snapshot
script. JSON is exported through DuckDB, not hand-authored. This projection
does not replace Run History, the artifact store, the intelligence catalog, or
managed records. Managed notes still use `RecordOperationService` or
`loop-engine records`, with exact approval and expected revision.[^20]

The immediate continuation target is applied, verifiable recovery. Preserve
the cognitive-act architecture, keep harness and model choices independent,
and require evidence that the next changed action did something useful before
expanding the campaign.

## Sources

The following are Loop Engine repository documents and local saved records.
They are not independent publications. Source identities for the principal
documents and all current Python modules are retained in the checkpoint
database. Local paths require access to this checkout and its retained study
directories.

[^1]: Loop Engine, [Per-step harness recovery, September 12, 2026](../verification/HARNESS-STEP-RECOVERY-2026-09-12.md), sections "Live attempts, including failures" and "Implemented behavior." Exact attempt directories are listed in that report.

[^2]: Loop Engine, [Cognitive-act recovery checkpoint, September 12, 2026](../verification/COGNITIVE-ACT-RECOVERY-2026-09-12.md), changes, verification, live diagnostics, and open work.

[^3]: Loop Engine, [Cognitive-act saved-run summary](../../artifacts/cognitive-act-recovery-20260912-05JQhk/summary.json), September 12, 2026; [summary builder](../../artifacts/cognitive-act-recovery-20260912-05JQhk/summarize.py). Six event-chain checks, exact run identities, source digests, outcomes, call accounting, and learning dispositions. Local generated evidence.

[^4]: Loop Engine, [Current-state checkpoint](../../artifacts/state-checkpoint-20260912-OtPgn5/README.md), September 12, 2026. `checkpoint.duckdb` and DuckDB-generated `checkpoint.json`: refreshed 80-cell legacy projection, source comparison, factor counts, saved QA projection, and scoped process observation.

[^5]: Loop Engine, [Review and saved-run evidence](../../artifacts/review-2026-09-12-JAXVkn/REVIEW.md), September 12, 2026. Coverage, session history, the frozen 08:53:19 UTC Tactical snapshot, findings F01 through F08, and historical corrections. Supporting read-only queries and source metadata are in that directory's review database.

[^6]: Loop Engine, [Cognitive steps, harness processes, and reusable Solutions](COGNITIVE-STEP-HARNESS-DIRECTION-2026-09-12.md), September 12, 2026. Earlier design synthesis; its review-only work status is historical, not the authority for later runs.

[^7]: Loop Engine, [Architecture Constitution](../architecture/CONSTITUTION.md), [repository instructions](../../AGENTS.md), and [architecture.yaml](../../architecture.yaml), versions identified in the checkpoint manifest. Runtime identity, authority, intelligence, promotion, and benchmark invariants.

[^8]: Loop Engine, [Contract index](../contracts/README.md), current inspected version. Loop definitions, graph identity, modes, port limits, model authority, public solving, and verification boundaries.

[^9]: Loop Engine, [Work-approach instrumentation and optimization](../architecture/WORK-APPROACH-INSTRUMENTATION.md), current inspected version. Accepted direction, governed granularity, approach experiments, contribution evidence, and the explicitly unproven checkpoint.

[^10]: Loop Engine, [Cognitive-act recovery and candidate learning](../components/practitioner/COGNITIVE-ACT-RECOVERY.md), current inspected version, plus the corresponding source modules linked in the continuation map.

[^11]: Loop Engine, [Information access](../../src/loop_engine/core/information_access.py), [delegation runtime](../../src/loop_engine/loop/delegation_runtime.py), and [context artifacts](../../src/loop_engine/core/context_artifacts.py), source identities in the checkpoint database. Existing mechanisms do not by themselves prove the proposed cross-process reference experiment.

[^12]: Loop Engine, [Harness integration guide](../../embodiments/HARNESS-GUIDE.md), inspected version. Brokered text-only profile, process isolation, envelope binding, and qualification limits. Its Ollama example belongs to an earlier campaign and is not the current provider instruction.

[^13]: Loop Engine, [Per-step harness recovery contract](../components/core-architecture/HARNESS-FALLBACK.md), current inspected version. Ordered registrations, shared authority, uncertainty/effect refusal, and first-admitted-response semantics.

[^14]: Loop Engine, [Loop contract](../../src/loop_engine/loop/loop_contract.py), [Loop definition](../../src/loop_engine/loop/loop_definition.py), and [Loop runtime](../../src/loop_engine/loop/recursive_loop.py), source identities in the checkpoint database; reproduction details in review findings F03 and F04.

[^15]: Loop Engine, [Reusable Capability Flywheel](../components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md) and review finding F08. Governed reuse and explicit offline-fixture limits.

[^16]: Loop Engine, [Self-improvement as a Practitioner task](../components/self-improvement/README.md) and [recovery_learning.py](../../src/loop_engine/core/recovery_learning.py), current inspected versions. Candidate staging is separate from active intelligence and independent promotion.

[^17]: Loop Engine, [Unseen novel-task campaign](../verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md), specifically "Corrections recorded on 2026-09-07." Earlier headline figures are not used as current performance claims.

[^18]: Loop Engine, local systematic study in the git-ignored development directory `.loop-engine-dev/systematic-20260912-Ly6MoT/` on the owner's machine (not part of the repository), September 12, 2026. `campaign.duckdb`: `task_catalog`, `factor_levels`, `configurations`, `endpoint_probes` entry `context_boundary_300001`, and evaluator qualification records. The checkpoint copies only bounded aggregate projections.

[^19]: Loop Engine, [Reference-source boundaries](../context/REFERENCE-SOURCES.md) and the review's folder map. Copied projects supply design provenance, not product authority.

[^20]: Loop Engine, [Queryable records and storage](../guides/queryable-records-and-storage.md), current repository guidance. Derived report projections do not replace the host-managed record service or canonical runtime writers.
