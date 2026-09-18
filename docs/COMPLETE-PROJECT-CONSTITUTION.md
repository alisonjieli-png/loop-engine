# Loop Engine complete project constitution

This document is a consolidated map of the whole Loop Engine project. It
restates, in one place, what every governing document, contract index,
component guide, and runtime module establishes. It encodes every aspect of
the project: identity, the one runtime, roles, modes, contracts, intelligence,
permissions, verification, solving behavior, evidence, harnesses, memory,
configuration, documentation rules, and current limits.

This document is a synthesis. It does not grant execution authority and it
does not replace the normative sources. Where this document and those
authorities disagree, the normative authorities win. The authority order is:

1. The [Architecture Constitution](architecture/CONSTITUTION.md) with its
   stable invariants.
2. Machine-readable contracts
   ([architecture.yaml](../architecture.yaml),
   [terminology.yaml](../terminology.yaml), schemas, manifests).
3. Contract tests.
4. [Architecture Decision Records](architecture/).
5. Folder README files.
6. Public API docstrings.
7. Inline comments and generated documentation.

A statement in this synthesis is only as strong as its source. Where the
source says a behavior is proposed, unqualified, or not implemented, this
document repeats that state rather than upgrading it.

## Part 1. Project identity

- Repository: `/home/username/loop-engine`, remote
  `https://github.com/alisonjieli-png/loop-engine.git`.
- Product and repository name: Loop Engine.
- Python distribution and command: `loop-engine`.
- Python import: `loop_engine`.
- Public README title: Building with Loops.
- Loop Engine is a standalone repository. `/home/username/taedri.dev` is a
  separate design reference only. Loop Engine never imports it, depends on
  it at runtime, or copies registries, naming systems, governance documents,
  or whole files from it.
- The repository ships one installable package containing the runtime, its
  contracts, its tests, examples, benchmarks, case studies, and presentation
  assets in separate directories with declared ownership.

### The product in one paragraph

Loop Engine coordinates tasks through one shared Loop runtime. Given
configured capabilities and authority, it attempts work, checks the results,
and saves completed work and failures in an inspectable Run History. It takes
small steps and selects the next concrete action itself. It records typed
model decisions and material actions, then checks its work before claiming
success. Verified code, context, and solutions can become candidates for
governed reuse. This interface is not a claim that arbitrary unseen tasks are
already solved.

## Part 2. The one operational runtime

### The absolute rule

`Loop` is the only concrete operational runtime and the only executable graph
vertex (Constitution LE-NODE-001). The canonical class refuses subclassing at
class-creation time. The repository MUST NOT define a concrete generic Node
class, role-specific node classes, mode-specific node classes, or any second
operational runtime (LE-NODE-002 through LE-NODE-004).

Common behaviors are versioned passive Loop presets, never runtime subclasses
(LE-NODE-005). Typed objects contained by a Loop, including contracts,
policies, configurations, references, results, and reports, are not
executable vertices (LE-NODE-006). A semantic step needing independent
governance executes as a Loop Spawned by its parent (LE-NODE-007). A
low-level primitive is not promoted into a Loop unless it needs an independent
goal, contract, budget, permission boundary, retry, verification, scheduling
decision, or Run History identity (LE-NODE-008).

### The complete classification tree

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

### The words used precisely

- Runtime type answers what operational object runs. The answer is always
  `Loop`.
- Relationship answers how this Loop entered the active structure: Starting,
  Spawned by, Queried by, Retrieved by, or Connected from.
- Role answers what broad responsibility it has: Practitioner, Intelligence,
  or Solution.
- Profile answers which reusable versioned behavior preset it uses.
- Category answers how work is classified for search and organization. A
  category never creates a class or runtime.
- Mode answers how the Loop is allowed to resolve its work.
- Step profile answers which ordered steps it can run.
- Settings answer which contracts, budgets, permissions, provider routes,
  thinking power, and conditions apply.
- Loop and exit conditions answer when it may continue and when it finishes.
- Graph relationships answer how this Loop relates to other Loops.

### Three run modes, no more

| Mode | Meaning |
|---|---|
| deterministic | Code, rules, calculations, retrieval, or execution lead. No language model is called. |
| hybrid | Code leads. A language model may resolve one bounded semantic step. |
| non-deterministic | A language model leads semantic work while the Loop controls tools, permissions, budgets, events, and verification. |

A mode never grants file, network, secret, model, spending, or
external-effect authority. The in-process Solution runner supports all three
modes when a compatible executor and exact model authority are supplied;
without them it returns a typed unavailable-executor failure. Thinking power
and model routing apply only when a hybrid or non-deterministic Loop is
authorized to call a model. They are not additional run modes.

A graph, pipeline, or Canvas does not inherit one mode. It may declare only a
policy for the modes permitted on its member Loops.

### The Loop definition

`LoopDefinition` is immutable. It carries definition ID, semantic version,
content digest, registered role profile and version, the typed input and
output contract, supported modes, installed executor modes, step profile,
loop condition, exit condition, canonical configuration facts, permissions,
effects, and required capabilities. A definition reference is
`definition_id + version + content_digest`. Loading a changed record with an
old digest fails.

`LoopStartRequest` carries five fields: the goal, the complete definition, the
relationship, the least-authority `LoopRuntimeContext`, and the event log. A
Loop refuses to start when the profile is unregistered, the contract role
conflicts with the profile, a selected mode is unsupported, or the runtime
context lacks a required capability, permission, or executor.

`LoopGraphDefinition` is the authoritative static directed acyclic graph. Every graph vertex
contains an exact definition reference. Every edge names typed source and
target roles. Every graph carries its own version and digest. `SolutionSpec`
and `Canvas` build or project this graph. They are not parallel graph
authorities.

### Relationships and roles in practice

A Starting Loop has no incoming Loop relationship. A Spawned Loop records one
spawning Loop ID. A spawning Loop and a Loop it spawns may use different
modes. A Starting Practitioner may spawn a Practitioner subproblem Loop and
query an Intelligence Query Loop. That Query Loop retrieves Intelligence Item
Loops and returns typed references or material. A Starting Solution runs
deterministic pipelines through Connected Solution Loops and uses Spawned
Solution Loops only for a real dynamic branch, fallback, repair, or ensemble
member. Passive records, services, ports, slots, and edges are not graph
vertices.

### Historical compatibility

Historical serialized `kind: loop_node` records may be read only through the
exact migration into `LoopDefinitionRecord`. Retired topology fields appear
only inside explicit readers for immutable legacy records. New records do not
emit them.

## Part 3. The canonical descriptive term

The full phrase "discrete cognitive or act step Loop node" and its complete
behavioral explanation are required language. The complete explanation states
that such a node is an independently governed instance of the Loop runtime
responsible for one clearly defined cognitive step or action; that it
receives the context, instructions, skills, plugins, tools, and working files
relevant to its assignment; that a separately initialized harness process may
perform the assignment and, when explicitly permitted, another harness may
attempt the same assignment after a failure while contracts, permissions,
history, and remaining authority persist; that discrete describes the scope
of the assignment, not one attempt, one model call, or one output; that it
can iterate until declared completion conditions are satisfied or publish
candidate outputs and continue while continuation conditions and authority
permit; and that continued operation never authorizes repeated external
effects, which require their own authorization and duplicate-delivery
protection.

This phrase does not introduce a runtime class, role, or mode. The canonical
runtime identifier remains `Loop`. The full phrase and full explanation must
be preserved in explanations, documentation, prompts, and handoffs without
shortening, acronym, or label substitution.

## Part 4. The configuration dimension requirement

The recorded configuration dimensions are a required baseline, not an
exhaustive list or a maximum. Every dimension needs an explicit initial
choice and ordered fallback priorities. The baseline dimensions are:

harness implementation and process initialization; role profile; step
profile; model; provider and route; tools; skills; context Markdown files;
harness native instruction Markdown files; prompt injected Markdown and
prompt construction; plugins; hooks; input contract; output contract;
supervisors and independent verifiers; thinking power; model call strategy;
model generation settings; model output allocation; Loop usage and
orchestration; run mode; intelligence and runtime memory; workspace and
execution environment; budgets, permissions, and effect policy; and Loop exit
and output publication conditions.

Additional dimensions are being discovered and added deliberately. Every
proposal maps to an existing owning boundary, states its initial and fallback
choices, and defines a discriminating test. Do not reduce the requirement to
harness and model choice, and do not mistake a documented requirement for
implemented and qualified behavior. Support additional cognitive steps,
prompts, questions, intelligence, actions, and resource combinations as well
as compact procedures. Do not make minimal step count, prompt count, context,
or model use the universal objective.

## Part 5. The three roles

### Practitioner

The Practitioner builds and verifies solutions. Registered profiles include
reference nine step, compact five step, research, solver, verifier,
self-improvement, and code execution. The Practitioner reconstructs the task
and accepted state, searches the four intelligence layers, selects a mode
with an installed executor, performs bounded work or spawns another Loop,
verifies output against the task contract, integrates accepted work, and
evaluates loop and exit conditions.

Every selected action produces an `action_intent_vector/v1` recording intended
direction, expected state change, check, dependencies, fallback, and decision
coordinates, and an `outcome_vector/v2` recording what was actually observed.
A successful model response, observable process alignment, capability
execution, expected action output, requested task output, verification,
material progress, and safe continuation are separate axes. An unchecked
axis remains unknown. Private model reasoning is not recorded. A pure guard
rejects a normal stop while the current action vector says safe authorized
work remains. This policy belongs to the owning Practitioner Loop and applies
identically when the semantic work uses the custom implementation or a
registered OpenCode, Codex, Pi, or other harness realization. A harness
completion event cannot accept the task or grade its own vector.

Self-improvement is a Practitioner task, not a separate component. It stages
candidates for independent review and cannot approve its own work
(LE-GOV-001). A tool written during a run remains a candidate until a
different process qualifies it.

### Intelligence

Intelligence is organized as four persistent layers:

1. Context Intelligence.
2. Code Intelligence.
3. Runtime History and Solution Intelligence.
4. User Feedback Intelligence.

Runtime Memory is separate, temporary, and scoped to one run. Source formats
such as Markdown, skills, repositories, packages, transcripts, and vectors do
not define new intelligence layers. Searching, selecting, materializing,
framing, invoking, replaying, and interpreting intelligence are Loop
operations. Search returns small typed references. A large body loads only
after selection and permission checks. Imported and self-generated
intelligence remains candidate-only until an independent process approves it.
Never infer promotion from retrieval, execution, a good score, or model
confidence. Code Intelligence requires an immutable source identity,
provenance, license state, version, dependency information, typed contract,
effects, tests, independent verification, and a digest before it is active.

In the ordinary flow a Practitioner queries an Intelligence Query Loop,
which retrieves Intelligence Item Loops. Query and retrieval do not change
role, profile, or selected mode into a spawning relationship.

### Solution

A Solution Canvas organizes candidate Solution Loops for a finished solution.
Every executable vertex in the Canvas resolves to a Solution Loop with a
complete versioned definition. Execution projects selected candidates into one
authoritative graph before any operation runs. Connected Solution Loops carry
typed values through declared ports for deterministic pipeline steps. Spawned
Solution Loops are reserved for real dynamic branches: selected fallbacks,
repairs, and dynamic ensemble members.

## Part 6. Core Architecture and capabilities

Core Architecture has exactly three public capability groups:

1. Intelligence Search and Retrieval.
2. Web Research.
3. Custom Plugins.

These are reusable capabilities, not executable graph vertices. The work that
searches, researches, or invokes a plugin belongs to a classified Loop.
`LoopRuntimeContext` carries these groups as three typed ports plus internal
runtime mechanics. Providers, settings, workspaces, approvals, stores,
Runtime Memory, Run History, reports, playback, and provider adapters are
internal runtime mechanics, not additional public capability groups.

Every operational boundary appears in the existing `core.boundary_registry`
with runtime type `Loop` and either an exact registered role profile or a
validated typed profile source. Missing, extra, unknown, unversioned, or
role-incompatible boundaries fail conformance.

## Part 7. Permissions, authority, and effects

- A descendant Loop may narrow inherited permissions but must not broaden
  them without an explicit delegated grant (LE-PERM-001).
- Discovery is effect-free. File writes, shell commands, network access,
  model calls, spending, and external mutations require explicit typed
  authority.
- Approvals bind to the exact requested effect. A changed effect needs a new
  decision. Effect approval state is durable and one-use; replay or argument
  drift refuses.
- Path-confined workspaces are mandatory. Path traversal, symlink escape,
  and unsafe overwrite are refused. Untrusted code runs in a declared sandbox
  with bounded resources and a network policy.
- A mode never grants file, network, secret, model, spending, or
  external-effect authority.
- External effect uncertainty requires reconciliation before further mutation.
  Committed external effects are never replayed silently.
- Host-owned execution registers explicit capabilities with frozen schemas and
  handshake identities; permission declarations are scoped to the selected
  host operations; observed progress and task completion remain separate; and
  final success requires issued, current-state-bound host verification.
- Keys are read and never written. Endpoint records carry posture, not
  credentials. Secret-shaped literals fail the build. No telemetry exists.
  With no provider configured the library makes no network calls at all.

## Part 8. The model boundary

- The model proposes semantic decisions. Deterministic supervisors retain
  permissions, tool execution, evidence gates, liveness, and terminal
  authority.
- Use real configured providers for provider integration and performance
  claims. A stub may test a local contract but proves no integration.
- Never silently replace a failed model call with canned or synthetic output.
- Output capacity resolves from a source-backed record for the exact provider
  and model. Without an explicit allocation, request the full capacity, not
  an invented smaller default. A typed `ModelOutputAllocation` binds to the
  route and decision evidence within known capacity. Capacity, selected
  allowance, and total-run authority are separate. Unknown capacity is an
  explicit unknown result; a total budget or semantic size estimate never
  becomes a provider limit.
- Retry, same-provider fallback, cross-provider failover, formatting repair,
  evaluator-triggered repair, and task replanning remain distinct. Failover
  runs only when the run contract explicitly permits it. An explicitly
  selected model remains pinned.
- Provider-reported token usage is preserved. Missing usage and cost remain
  unknown, not zero.
- Private prompts, raw outputs, authorization headers, and credentials never
  enter source files, events, reports, or exported traces.
- DeepSeek-style provider reasoning fields are protocol state, not verified
  evidence. The evidence layer is observable actions, artifacts, tests,
  sources, and verifier outputs.

## Part 9. Verification and acceptance

### Independent verification

Generated projects require independent executable checks by default. A
separate verifier Loop proposes checks from the original task, reviews its
own proposals as an oracle, runs them in a read-only, network-disabled Docker
workspace, and returns observed failures to the existing repair loop. The
frozen subject binds the original task and exact criteria to immutable bytes.
Verifier packets exclude producer plan and event history. Expected-value
comparisons execute outside the candidate process. An unavailable or failed
check cannot be overridden by producer acceptance. Retained regression code
and expectations cannot change silently. Physical verifier calls share the
run's session accounting. Task acceptance grants no persistent promotion or
core modification.

The independent verifier can also judge a natural-language deliverable
against one registered criterion at a time: its probe prints the text, an
isolated judge call decides, and deterministic grounding passes the judgment
only when every quoted passage appears in the printed deliverable.

### Failure review

A failed independent check is reviewed before it forces repair. An isolated
call classifies the failure with quoted evidence as a correct failure, a
wrong expectation, a check stricter than the task, an environment defect, an
ambiguous requirement, or unknown. A claim that the check is wrong needs a
second isolated confirming call. A revised check is designed with the
disputed check and both reviews as untrusted feedback, passes the normal
oracle review, and must fail on the same subject with its authored and
produced files emptied before it runs on the real subject. Otherwise the
original check and its failure stand. The disputed check, failed report, and
both reviews stay recorded. A correct failure names the part of the work to
repair. Confirmation on a different model route is not implemented yet.

### Resolution packages

An unverified task-level outcome returns a complete resolution package. Every
registered safe resolution method appears exactly once as completed, not
applicable, unavailable, authority-required, or resource-exhausted. A
completed method carries its mapped material. At least one useful method must
complete. Resolution completion, requested-outcome verification, and
operational interruption are separate axes. A best-available resolution
preserves provisional outputs, assumptions, gaps, alternatives, and next
actions, and never invents facts, authority, verification, or external
effects. A run may return earlier passing work for verification instead of
rewriting after a later failed attempt. An incomplete task source enters a
separate best-available lane that never enters original task success
denominators.

### Evidence and benchmarks

Observed, inferred, assumed, missing, and disputed facts are stated
separately. Failures and excluded attempts are preserved with the same
prominence as successes. A full-system benchmark requires a frozen real task
population, a Starting Practitioner, reviewed Context and executable Code
Intelligence, bounded Spawned Loops, candidate comparison and verification, a
compiled and executed Solution Canvas, an independent evaluator, and verified
Run History, playback, and report. A component test, provider probe,
deterministic replay, or partial path is not a full-system benchmark. Reports
state the exact denominator, selection rule, metric direction, evaluator,
failures, physical model calls, token-accounting completeness, elapsed time,
cost state, artifacts, and limitations. Published results from another
harness are external evidence only, cited with exact task population, model,
harness version, evaluator, source, and limitations. Benchmark claims never
exceed saved evidence.

For the current first benchmark campaign, selected solutioning runs are
non-deterministic. Deterministic Spawned Loops may retrieve, execute,
validate, and grade. That campaign choice is not a universal product rule.

## Part 10. Persistent general solving

The owner's September 14 direction is recorded as proposed invariants
(LE-SOLVE-001 through LE-SOLVE-005, LE-CONTRACT-001 through LE-CONTRACT-003)
and designed in the persistent general solving decision record. Its
principles, applied to engine behavior and development work alike:

- Build general mechanisms. No control flow, prompts, or checks written for
  one task, dataset, or benchmark.
- Persist within declared authority. Turn a failure into a typed next action.
  A run ends only for a verified result, exhausted declared authority, a
  question only the owner can answer, a cancellation, or a provider outage
  recorded for resumption, and records which reason ended it.
- When a check fails, first decide whether the work, the check, or the
  environment is wrong, and record why. Do not weaken a check to make it
  pass. A revised check must still reject a known-wrong answer.
- Never let a review waive a permission, secret, network, spending, sandbox,
  or external-effect contract.
- Treat a tool written during a run as a candidate until a different process
  qualifies it.
- Never end work on a fixed attempt count. When the same failure repeats,
  change the approach: quote the failure, narrow the request, try another
  registered method, or carry the best result forward as provisional with its
  findings recorded.
- The task working folder gathers supplied files, unpacked archives,
  downloads, generated work, and outputs, persists across attempts, and
  shares scoped views with Spawned Loops. It grants no write, command,
  network, or spending authority.
- Run live experiments only under explicit owner authority. Record every
  trial including failures and outages, keep runners waiting through a
  provider outage within a declared wait, and stop before an allowance is
  drained.

Implemented against this direction: task materials unpacking, binary file
selection, best-available result selection, re-presentation of earlier
passing work, reasoned recovery for every admitted model session, declared
supervision policies, budget-phase routing thresholds, a declared fast-path
allowance for model-led runs, verifier failure review, criterion judgment for
natural-language deliverables, and undeclared-file naming in verifier
refusals. No live rerun has qualified all of these together yet.

## Part 11. Harnesses as bounded substrates

A harness is an internal execution substrate that one Loop binds for a
bounded stretch of semantic work, the way the Model Gateway is a substrate for
model calls. External coding harnesses such as OpenCode, Codex, Pi, aider,
Cline, and their peers become swappable capability units inside a Loop without
becoming a second runtime. No harness owns task authority, acceptance,
promotion, history, or the intelligence flywheel.

Every harness request carries the same versioned outcome policy. A harness
adapter can report mechanical execution but cannot award semantic success or
grade its own outcome vector. A harness completion event sets only the
mechanical execution axis. Harness selection reads reviewed evidence bound to
an exact contract, population, and evaluator; eligibility precedes ranking;
insufficient evidence preserves the configured order; and missing measurements
remain unknown. Per-step recovery runs through explicit ordered alternatives
under shared authority and accounting, stops at an admitted proposal rather
than task acceptance, and never replays uncertain effects.

A discrete cognitive or act step Loop node may bind a separately initialized
harness process for its assignment. Composed instances give exact tool grants
structurally rather than by prompt: a per-step instance is built from a core
layer identical on every step, carrying the response contract, refusal rules,
and safety posture, and a step layer chosen from a registered catalogue keyed
by step id, carrying the tools, skills, and permissions that step should
have. Selection is engine authority; a model never names files into its own
instance, because a model that could compose its own instance could grant
itself tools. Read-only steps deny write-capable tools outright, including
delegation tools whose subagents could reintroduce them.

Layered wrapper composition and native control ownership are configuration
dimensions, not a fixed stack. Wrappers remain internal mechanics unless
their work needs a separately governed canonical Loop. Native controls never
grant broader authority or replace independent task acceptance. An outer Loop
Engine Loop may govern a native harness's inner loop; cumulative authority,
retry ownership, cancellation, and independent acceptance stay explicit
across both.

MCP connects an application to tools, data, and workflows as a capability and
data edge. Agent Skills package reusable procedures as a context subgraph.
ACP standardizes communication between coding agents and clients as a
harness-hosting boundary. None of them is the authority system, the evidence
ledger, or a graph vertex.

## Part 12. Memory and records

Memory kinds are distinct: Runtime Memory is temporary and run-scoped;
episodic, semantic, and procedural records are persistent with lifecycle
governance; Run History is the immutable event record. Candidate generation
and promotion are separate. A Loop that generates a candidate may not approve
its own candidate. Consolidation is non-destructive. Legal lifecycle
transitions are recorded and enforced; rejected and tombstoned are terminal.

Procedural memory carries applicability conditions, typed contracts,
permissions, verification, and evidence. Retrieving a procedure never bypasses
runtime checks: a remembered procedure still passes current contracts,
permissions, effect approvals, and compatibility validation.

For managed notes and report collections, use `loop-engine records` or
`RecordOperationService`. Do not directly rewrite database rows,
current-reference metadata, immutable revision artifacts, or generated views.
Preserve schema, namespace, expected revision, and exact write approval.
Unknown commits are not successes. Ordinary source, schema, test, and
hand-authored documentation edits remain permitted within the task.

## Part 13. Run History and evidence integrity

Every run preserves Run History: ordered events, definition references,
relationship records, distinct positive, missing, partial, and real-zero model
usage, a digest-bound product outcome, saved playback, and hash chain
checking. One corrupt run cannot break verified sibling runs. A saved run
manifest binds the exact product outcome digest. Reports, playback, and
Studio project the bound product outcome.

Semantic stage evidence separates activation identity, semantic-call identity,
and similarity signatures. Physical retries do not change the semantic call
occurrence. Selected action, execution, and verification join by exact
occurrence references. Rejected, provisional, or unbound attempts cannot
replace the accepted incumbent. Foreign, stale, duplicate, or changed
lineage cannot create stage credit.

## Part 14. Reactive execution

Reactive series carry stable identities, finite trigger-bound activations,
fenced work leases, and append-only candidate, evaluation, and portfolio
records. Every activation is finite, budgeted, and terminal, and starts the
exact Loop definition. Reference possession never grants access. Inline values
are owned snapshots, not shared mutable aliases. Rank belongs to one policy
version, not the candidate. Portfolio reads never reactivate the producer.
Stale fencing tokens cannot commit. Unchanged input does not create duplicate
work. The candidate producer cannot be its sole verifier. Installed execution
placements are inline, async IO, and thread. Process, container, remote
worker, and Kubernetes placements are unproven.

## Part 15. Configuration and parameters

- Omitted, null, empty, false, and zero remain distinct. Invalid explicit
  values do not fall back. Explicit values precede profiles, policies,
  defaults, derivation, and intelligence. Intelligence proposals cannot
  override explicit values or invariants.
- Supervision policy is typed and versioned. It carries non-progress limits,
  the escalation ladder (soft reset, cold restart, honest stop), the spawn
  depth guard, and optional budget-phase thresholds. A budget-phase threshold
  demotes exploration routes to consolidation near the declared end of call
  authority, then presents the best available result for final verification.
  It never demotes a verified success or an honest stop, and without a
  declared policy nothing changes.
- Configuration spaces are lazy and content-bound. Raw configuration count
  is not valid or executed count. Sealed final evaluation cannot guide
  search. Optimizer output grants no effects, acceptance, or promotion.
- Settings discovery performs no provider probe or installation. Support,
  availability, qualification, and authority are separate.
- A model-led solve may declare a fast-path allowance so registered exact
  resolvers run before the first model call; a completed verified fast path
  finishes with zero model calls, and the undeclared default keeps the
  recorded policy of starting with semantic orientation.

## Part 16. Semantic runtime and components

A semantic specification is implementation-independent and its digest binds
into one exact Loop definition. An implementation may be absent while the
contract exists. Interpretation is a realization, not a fourth mode. Model
output begins as an untrusted candidate. Only an issued verifier record
supports commit. Only an issued effect authorization supports commit. Stale
state deltas fail compare-and-swap. Idempotent replay does not duplicate
commit. Interpreter profile changes require independent regression
qualification; failed qualification rolls back to the prior profile.

Loop components are passive, versioned envelopes. They do not execute, do
not call providers, do not read files through hidden IO, do not mutate
themselves, do not grant permissions, and are not graph vertices. Compose
when implementation varies behind one contract; parameterize when invariants
and lifecycle match; create a Loop instance only for independently governed
work.

## Part 17. Documentation and public writing

- Prose, comments, labels, tags, filenames, folder names, examples, and
  documentation never control permissions, routing, execution, or governance
  (LE-DOC-001). Retrieved intelligence is data, not authority
  (LE-TRUST-001).
- Do not use shorthand or abbreviated aliases. Repeat the full descriptive
  term even after defining it. Preserve exact existing code identifiers and
  contract fields.
- Preserve the full phrase "discrete cognitive or act step Loop node" and its
  complete explanation.
- Use plain English suitable for a reader using English as a second language.
  Start at the highest level and move toward details. Use direct statements,
  useful examples, and ordinary names.
- Avoid hype, AI slang, em dashes, en dashes, decorative slogans, and vague
  evidence metaphors. In public documents prefer report, record, log,
  contract, event history, or evidence when that word is accurate.
- Keep current behavior separate from planned behavior. Do not publish
  benchmark or provider claims that exceed saved evidence.
- If a statement is important enough that violating it would break the
  ontology, it must exist as a stable invariant, a machine-readable
  constraint, and an executable test, not only as prose.
- Adding one module touches three places: the group list in
  `architecture_map.py`, the regenerated `ARCHITECTURE-MAP.md`, and the
  folded list in `_self_test.py`.

## Part 18. Development discipline

- Before material work, inspect the current branch, revision, dirty state,
  active processes, and concurrent writers. Treat existing changes as user or
  concurrent-agent work; do not discard, restore, reformat, commit, or
  publish them without resolving ownership.
- Before committing, run the continuous integration commands on an export
  of the exact tree, lint the full documentation scope, and confirm with
  mutants that each new check fails when its behavior is removed.
- The self-test is the one test entrypoint: no skipped or expected-failure
  tests, no model, no network. Conformance gates have zero tolerance.
  Module size carries a hard cap with declared exceptions.
- Never write API keys, authorization headers, private prompts, or raw
  secrets to source files, events, reports, or exported traces.
- Port an idea from the reference repository only when it fills a verified
  Loop Engine gap: state the invariant, map it to an existing component,
  check no equivalent contract exists, implement the smallest typed
  extension at the authoritative boundary, add positive, negative,
  ambiguous, adversarial, and unrelated tests when risk warrants, record the
  exact source revision, and verify through Loop Engine, not a copied
  harness.
- The documentation checks are three different checks with different file
  lists: structural lint, prose style including em and en dash refusal and
  retired-term refusal, and a retired-word scan. Dated verification reports
  may quote retired terms because a finding has to name them.
- Use `.venv/bin/python` with `PYTHONPATH=src`. The system Python does not
  have the package installed.

## Part 19. Verified scope and unproven claims

This synthesis distinguishes implemented, offline-verified, and unproven
behavior. The strongest documentation rule requires the same distinction in
every claim:

- Implemented and offline-verified: the one-runtime ontology and its
  conformance gates; typed contracts across solve, verification, harness,
  reactive, plugin, records, and parameter boundaries; independent executable
  verification with frozen subjects and read-only Docker execution; failure
  review, criterion judgment, and undeclared-file naming; resolution
  packages; budget-phase routing and the fast-path allowance (offline;
  live qualification pending); supervision and recovery; Run History with
  hash chains; the four intelligence layers with candidate-only admission;
  the reactive execution foundation; per-step harness composition with core
  and step layers; managed records; the semantic runtime vertical slice.
- Live-qualified in bounded scope: the DS-1000 four-task smoke benchmark on
  the pinned deepseek flash route; the first task-database campaign cells and
  the matched reruns; provider probes.
- Explicitly unproven, never claimed: universal oracle correctness;
  adversarial independence of same-model reasoning; fully automatic
  requalification of changed interfaces; autonomous cross-process resume;
  live provider quality for the reusable flywheel; distributed placements;
  arbitrary unseen task quality; achieved general intelligence. Artificial
  general intelligence is a research ambition, not a runtime, role, mode, or
  achieved capability claim.

A mechanism that exists in code with passing offline checks but without a
live qualifying rerun is stated exactly that way, everywhere.

## Part 20. The map to normative sources

| Topic in this document | Normative source |
|---|---|
| One runtime, roles, modes, presets | [Architecture Constitution](architecture/CONSTITUTION.md) LE-NODE-001 through LE-NODE-009 |
| Configuration bootstrap | LE-CONFIG-001, LE-CONFIG-002 |
| Intelligence layer rules | LE-INTEL-001 through LE-INTEL-003 |
| Permission narrowing | LE-PERM-001 |
| Prose is non-executable | LE-DOC-001, LE-TRUST-001 |
| Version pinning | LE-VERSION-001 |
| Distinct memory concepts | LE-RUNTIME-001 |
| Plugins add no runtime | LE-PLUGIN-001 |
| No self-approval | LE-GOV-001 |
| Persistent solving proposals | LE-SOLVE-001 through LE-SOLVE-005, LE-CONTRACT-001 through LE-CONTRACT-003 |
| Every machine boundary | [architecture.yaml](../architecture.yaml) |
| Every canonical term | [terminology.yaml](../terminology.yaml) |
| Harness constitution | [HARNESS-AS-LOOP-NODE-CONSTITUTION.md](architecture/HARNESS-AS-LOOP-NODE-CONSTITUTION.md) |
| Configuration dimensions | [DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md](architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md) |
| Full term explanation | [DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md](context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md) |
| Flexible composition | [FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md](architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md) |
| Layered wrappers | [LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md](architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md) |
| Adaptive cognition and atomic instances | [ADAPTIVE-COGNITION-AND-ATOMIC-HARNESS-INSTANCES.md](architecture/ADAPTIVE-COGNITION-AND-ATOMIC-HARNESS-INSTANCES.md) |
| Adaptable policies and lifecycle applicability | [ADAPTABLE-POLICIES-AND-LIFECYCLE-APPLICABILITY.md](architecture/ADAPTABLE-POLICIES-AND-LIFECYCLE-APPLICABILITY.md) |
| Reuse tiers and cost routing | [REUSE-TIERS-AND-COST-ROUTING.md](architecture/REUSE-TIERS-AND-COST-ROUTING.md) |
| Persistent solving design | [ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md](architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md) |
| Contract index | [contracts/README.md](contracts/README.md) |
| Component guides | [components/README.md](components/README.md) and subfolders |
| Writing rules | [humanizer-context.md](../humanizer-context.md) |
| Conformance traps | [context/INVARIANTS-AND-TRAPS.md](context/INVARIANTS-AND-TRAPS.md) |
| Repository layout | [REPOSITORY-ORGANIZATION.md](REPOSITORY-ORGANIZATION.md) |
| Security posture | [SECURITY.md](../SECURITY.md) |
| Ways of running | [context/WAYS-OF-RUNNING.md](context/WAYS-OF-RUNNING.md) |
| Current work state | [context/CODEX-START-HERE.md](context/CODEX-START-HERE.md), [ASTRA.md](../ASTRA.md) |

## Maintenance rule

This synthesis is regenerated or updated whenever a governing document
changes. It never introduces a new invariant, term, runtime, role, mode, or
capability claim. When a new stable rule is needed, add it to the
Architecture Constitution with its enforcement test and machine-readable
entry first, then reflect it here.
