# Start a coding-agent session in Loop Engine

Read [START-HERE.md](START-HERE.md) first for the current requirements,
dated evidence, safe checks, and change rules. Its
two companions are [Invariants and traps](INVARIANTS-AND-TRAPS.md) and
[Ways of running](WAYS-OF-RUNNING.md). This page is the deeper orientation:
the first message for a new session, the reading order, and the component map.

This page applies to Codex and other coding agents working in the repository.

[ASTRA.md](../../ASTRA.md) is the main current advisory comments-and-suggestions
file for Claude Fable 5.1 and other development sessions. It keeps owner
requirements, proposals, acceptance criteria, and historical evidence distinct.
The repository [CLAUDE.md](../../CLAUDE.md) imports it with the shared
[AGENTS.md](../../AGENTS.md) instructions. Read the scoped instructions in
[embodiments](../../embodiments/AGENTS.md) or
[devtools](../../devtools/AGENTS.md) when working there.

The September 18 records are the
[adversarial project audit](../verification/ADVERSARIAL-PROJECT-AUDIT-2026-09-18.md)
with its ranked backlog, the
[session digest and research inventory](AGENT-SESSION-DIGEST-AND-RESEARCH-INVENTORY-2026-09-18.md),
and the [repository and session review](../verification/CLAUDE-FABLE-5-1-REVIEW-2026-09-18.md).
The boundaries that followed them are the model ontology, the model call
request, suggested outputs, the response contract registry, and the
solutions space record, listed in the [contracts index](../contracts/README.md)
and described in the changelog under September 18.

Before continuing after the September 12 account change, read the
[discrete cognitive or act step Loop node complete explanation and session handoff](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md)
in full. Preserve the full phrase and the behavioral explanation. Do not
replace either with shorthand or treat the documented design as proof that
every behavior is implemented.

For configuration, selection, fallback, and experiment work, also read the
[complete configuration dimension requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
The owner confirmed the full dimension set on September 13. Each dimension
needs an initial choice and ordered fallback priorities, not only harness
and model selection. The document separates this requirement from current
implementation and measured evidence.

The owner's subsequent clarification makes that inventory explicitly
non-exhaustive. Read the
[dimension discovery addendum](CONFIGURATION-DIMENSION-DISCOVERY-ADDENDUM-2026-09-13.md)
for the proposed refinements, additional choices, and ongoing review questions.
Protect the required baseline while continuing to discover dimensions; do not
turn either list into a fixed maximum or permit unknown runtime fields.

For additional preference engines, configuration setters, and meta-selector
work, read [configuration preferences and meta-selection](../guides/configuration-preferences-and-meta-selection.md).
The current interfaces provide sourced capability facts, atomic in-memory
setting changes, and scope-bound advisory ordering. They do not automatically
launch joint model and harness configurations or qualify autonomous live
selector portfolios. The expanded design inventory is version 1.2.0.

The subsequent [layered harness wrapper and native control proposal](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
records the owner's request to consider one or more wrapper layers and native
controls as dimensions. Wrapper composition and control ownership can vary
per assignment. Both are now typed records in
[`core.harness_layering`](../../src/loop_engine/core/harness_layering.py)
that a harness binding accepts, digests, and records on every attempt; see
[the fallback guide](../components/core-architecture/HARNESS-FALLBACK.md#declare-wrapper-layers-and-native-control-ownership).
No executor runs a wrapped composition or hands a native control to a
harness yet, and the documentation does not enable native goal controllers
or change the runtime adapters.

For the owner's request to promote broader cognitive steps, actions, prompts,
intelligence, and optimization, read
[flexible cognitive and action composition](../architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md)
and [configuration grid search](../guides/configuration-grid-search-and-optimization.md).
Expansion and simplification are both permitted design directions. The
documents preserve the research ambition without claiming an achieved
artificial general intelligence system or a general optimizer.

For the September 13 cleanup and independent review request, use the
[Claude Fable 5.1 review handoff](CLAUDE-FABLE-5.1-REVIEW-HANDOFF-2026-09-13.md).
It maps the uncommitted implementation, legacy compatibility, current versus
historical context, verification failures and corrections, and priority
review questions. It does not claim that Claude has reviewed the work.

Claude's same-day findings are in the
[Claude Fable 5.1 review](../verification/CLAUDE-FABLE-5.1-REVIEW-2026-09-13.md)
and, for the task-database campaign runner, the
[campaign runner review](../verification/TASK-DATABASE-CAMPAIGN-REVIEW-2026-09-13.md).
The configuration setter and preference modules have their own
[review](../verification/CONFIGURATION-MODULES-REVIEW-2026-09-13.md), with
what was fixed the same evening and what stays open.
The campaign review's two high findings matter before any provider answers
again: a non-outage provider failure re-runs the same cell without bound,
and a crash mid-trial leaves the campaign unresumable.
The [Ollama adapter path review](../verification/OLLAMA-ADAPTER-REVIEW-2026-09-13.md)
records what the live provider said on the evening of September 13 (the
key lists twenty models; generation is refused with a weekly usage limit
and no stated wait) and the sixteen adapter and classification defects
fixed before the campaign spends that allowance: the Ollama wire now
streams, a spent allowance is `usage_limit_reached` rather than a
throttle, a declared but unset credential refuses before any request, and
a listing is not readiness. For the storage-growth limit the preparation
report names, `RunHistory.append_checkpoint(root)` and
`load_checkpoint(root, run_id, revision)` store every event once with one
line per checkpoint and rebuild any checkpoint as the verified prefix; the
campaign runner's `RecordedSettingSession` now keeps one history per trial,
grown with `extend_from_ledger`, and checkpoints it into that store after
every invocation (`step_history` rows carry `layout`, `checkpoint`, and
`revision`; the retention test pins that every revision reloads). `ollama_client.learn_output_capability(model)`
read the output ceilings of the thirteen listed models that lacked one
when the allowance reset at 00:25 UTC on September 14, so all nineteen
Ollama Cloud models are declarable routes with source-backed maxima. The [campaign activation review](../verification/CAMPAIGN-ACTIVATION-REVIEW-2026-09-13.md)
probed `65593c7` offline before the launch: the worker's frozen snapshot
predates every fix since `dd49ca3`, a page in the provider's place drained
the queue (fixed at the ledger's usage rule), and three items are left for
this session: acknowledging an interrupted occurrence, engine identity over
the controller and package resources, and route-stop on a single generic
400. `python -m embodiment_lab.campaign_report ROOT --html page.html`
renders a campaign root as one page from its exported records, counting
the worker's access-probe calls apart from task calls.

**Urgent, 01:30 UTC September 14:** the pro worker's `CS-001` cell
(`.loop-engine-dev/fabric-readiness-20260913-N8fyhI/live-pro`) has made 320
model calls and consumed 13.8 million provider-reported tokens in fifty
minutes and is still running, with forty-nine verification rounds recorded;
the campaign builds every trial with `max_model_calls=None` and
`max_passes=None` (the runner's `ModelExecution(...)` and the Practitioner
request), so one cell can spend the whole weekly allowance. A per-cell call
ceiling and pass ceiling are configuration dimensions the grid should carry
explicitly (the owner's rule is explicit ceilings, never implicit ones), and
the worker should stop a cell that exceeds them with a recorded terminal.
The flash worker's finished cells took 44 and 69 calls. The product side is
answered on main: the kernel now applies the supervision policy's
`unaccepted_passes_before_stop` to its own passes when no pass budget is
declared, climbing the reset ladder to `stop_unprofitable` after
twenty-seven refused passes by default; the running worker's snapshot
predates it. The [first live cells record](../verification/LIVE-CAMPAIGN-FIRST-CELLS-2026-09-14.md)
tabulates every cell of both workers: seven executed flash cells cost 817
calls and 21.2 million tokens for one verified solution, the pro CS-001
cell was cancelled at 489 calls, and the allowance was spent again at
02:04 UTC. `AdaptivePractitionerRequest(..., supervision=SupervisionPolicy(...))`
now carries the per-run ceiling policy to the kernel, so the campaign grid
can declare `unaccepted_passes_before_stop` as a level per cell instead of
relying on the default of nine.

Coordination, 23:52 UTC September 13: the Claude session's changes to
campaign activation, the campaign page, provider accounting, and the
runner's step-history checkpoints are committed and pushed (`d753ed9` and
the commit that adds probe accounting to the page). That session is not
editing `task_database_campaign.py`, `campaign_activation.py`, the runner
tests, the Studio server, or the report renderers further tonight; the
launch snapshot is the Codex session's to choose. Its next work is in the
product's adapters and the evidence tooling, and it reads this file and
`ASTRA.md` for anything addressed to it. Two notes for the relaunch: the
prepared provider files declare `stream: buffer`, and a hosted service
behind a proxy read wall cuts a long generation with 504 or 524, which
`buffer` cannot answer. `stream: stream` sends every request streamed,
which the Ollama wire now speaks (newline-delimited JSON, joined with the
counts from the final line), and keeps one physical request per attempt;
`stream: auto` retries a cut request once with streaming, a second physical
request inside one attempt, which the adapter contract may refuse. And
`think: 'off'` on a model that cannot run without thinking is refused with
HTTP 400 (`invalid_request`, a route stop); `think: model` leaves that
model's default. The first live cell with `registered_alternatives`
(`BA-001` on the pro route) failed with `HarnessProcessError` before any
model call because `load_harness_binding` refuses an alternative whose
executable is not installed; the loaders now take `allow_unavailable=True`,
which registers such an alternative as unavailable so the fallback moves
on with `adapter_unavailable`. The runner's dispatch (the loop that loads
`manifest['harnesses']`) is the place to pass it for alternatives. The
evidence report's step-history check should call
`RunHistory.verified_checkpoints(store.parent, store.name)` once per store
instead of `load_checkpoint` per row: on the live FIN-001 cell (sixty-nine
checkpoints, six thousand events) that is a quarter of a second instead of
more than forty-five.

Coordination, 03:25 UTC September 14: `d511b43` changes what the
self-improvement review counts. Its population is the directories holding
a manifest, and an append-only checkpoint store now loads as its latest
checkpoint, so the campaign's `step-history` stores are reviewable
without copying them into saved runs. `RunHistory.content_digest()` names
the event content without the run id, the chain links, or the start
event's projection time; the loader excludes a later copy of an already
loaded content naming the run it repeats, and `mine_runtime` deduplicates
on that digest as well, so a re-projected ledger is one observation and a
repetition at other times stays two. The evidence tooling can use the
same digest wherever two histories must be told apart from two copies.
The experiment evidence commit `078fffc` left ten new high hardcoding
findings on `main` (the delta gate exited 1); the follow-up commit moves
those tokens to closed vocabularies and the artifact trial's instruction
texts to `strings/prompt_fragments.py`, the one module the audit treats
as prompt-resource authority, without changing the prompt bytes. The
owner asked how many solutions were generated for how many tasks: the
campaign page counts cells, calls, and tokens but not candidates per task,
so the next report change adds, per task, the candidates produced,
executed, and independently verified, with the exact denominators.

Coordination, September 14 afternoon: the owner asked a Claude Opus 5
session to reconcile all committed and uncommitted work onto `main`. The
Codex session's uncommitted tree is preserved at
`refs/backup/codex-inflight-20260914` and committed unchanged as `96fba39`.
`aca062f` makes it pass the gates and changes two behaviors. First,
`OutcomeVectorPolicy` 1.1.0 adds `after_acceptance`: an accepted,
deterministically verified result publishes and stops by default instead of
turning optional remaining work into another pass, and
`continue_while_work_remains` keeps the earlier behavior as an explicit
level; `ActionVectorRouteRequest` now takes `acceptance_established`.
Second, a resolution package is `COMPLETE` only when substantive work
completed a method: observed artifacts, inspections, provisional outputs, the
Practitioner's resolution contribution, or recovery alternatives. Orientation
restatements and the `_next_recovery` hint complete nothing,
`PROVIDER_UNAVAILABLE` and `CANCELLED` report `OPERATIONAL_INTERRUPTION`, and
`COMPLETED_PARTIAL` names only a complete package. The packaged
`src/loop_engine/data/architecture.yaml` and `terminology.yaml` must match
the root files byte for byte, and the three modules over the size cap carry
split plans in `forbidden_paths.json`. Still open from the review of this
work: vector axes are the verifier model's self-report, one unknown process
check blocks acceptance, the outcome-vector policy cannot be selected through
`SolveRequest`, and native multi-turn harness loops are not guarded between
turns. The full self-test then exposed eleven failures from a stale spawn
fixture, corrected in `aca062f`, and `89553f2` keeps generated project
refusal reasons, names excluded sources, and adds verifier comparison
policies. The [September 14 review](../verification/CLAUDE-OPUS-5-REVIEW-2026-09-14.md)
and the [intake research](../research/SELF-RESOLVING-INTAKE-SANDBOXES-AND-SHARING-2026-09-14.md)
record the rest.

Later on September 14 the owner asked for persistent general solving, a
review whenever a check fails, and a declared evaluation mode for every
contract. The direction is recorded as proposed invariants in the
[Constitution](../architecture/CONSTITUTION.md#proposed-invariants-from-owner-direction)
and designed in the
[persistent general solving decision record](../architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md).
The proposed invariants are not qualified yet. A typed supervision policy on
`SolveRequest` now reaches the Starting and Spawned Practitioner Loops, a
stalled format repair is a recoverable failure instead of the end of a run,
and a rejected orientation is repaired as a whole record, then field by field,
and then carried forward with its findings. The recovery panel's route now
passes the action vector guard, and the independent verifier repairs a
response whose format is not admitted. Supplied archives are unpacked into a
materials folder that the source inventory walks, and supplied binary files can
be selected for a project's inputs without the model reading them. New task
database campaign spaces also supply every attachment as a source file. These
are the first parts of one working folder per task.

A live rerun on `d3bda30` found correct work that was never accepted, because
the independent verifier could not produce an admitted check program. The
verifier now gives a planned file its declared path, names the field that a
refused case must repair, shows every registered criterion in its review
contract, and separates a recomputed expectation from a hardcoded
observation. An unverified run now presents its passing attempt
instead of a later failure.

`RETURN_RESULT` now submits the latest execution whose checks passed, so
passing work stays reachable for verification after a failed rewrite. A
declined recovery inside the verifier is now recorded. Recovery reasoning had
never run in campaign trials, because it required the in-process session
class while the campaign session wraps that session; it now checks the
session contract instead. The verifier can now judge a natural-language
deliverable, such as a message or a report, against one registered criterion
at a time: its probe prints the text, an isolated judge call decides, and the
judgment passes only when every quoted passage appears in that text. A refused
subject now names each undeclared file, and the oracle review treats an
expected value stated by the task as independent evidence. A failed
independent check is now reviewed before it forces repair, and a check
confirmed to be wrong is replaced only by a revision that fails on the subject
with its authored and produced files emptied. The next target is a live rerun
that qualifies these changes. The earlier targets remain: a task-owned evaluator
for campaign cells, the rest of the working folder (downloads as files, and
Spawned Loops that share the folder and return their files), and restarting
campaign cells after a provider wait.

For the subsequent September 12 configuration experiments, read the
[configuration and native initialization report](../verification/CONFIGURATION-AND-NATIVE-INITIALIZATION-2026-09-12.md).
It records 70 real Tactical calls, a forty-cell repair matrix with 159/160
case checks passing, and nine native Markdown loading controls. The report
separates engine-mediated resources from native harness loading, retains the
failed cases, and preserves the complete terminology explanation. These are
bounded component experiments, not a full-system benchmark or learning claim.

For the September 12 work on the discrete cognitive or act step Loop node, read the
[architecture and current-state checkpoint](../research/COGNITIVE-STEP-ARCHITECTURE-AND-STATE-2026-09-12.md).
It separates the design, current implementation, live Tactical failures,
verified harness handoffs, learning limits, and next proof sequence. Its dated
evidence takes precedence over earlier status summaries for that work, not
over the Constitution or typed contracts.

Use `/home/username/loop-engine` as the workspace directory for Loop Engine work.
This repository is separate from `/home/username/taedri.dev`.

## First message for a new session

```text
Work only in /home/username/loop-engine for this task.

Read AGENTS.md first. Then inspect the current branch, revision, dirty state,
active processes, and concurrent writers. Preserve all existing changes.

If a generated session_handoff/v1 packet is supplied, verify its HEAD and
worktree digest before using it. Treat missing or stale ownership as unknown.

Read README.md and docs/components/README.md. Follow only the component guides
needed for the task. Use humanizer-context.md for public writing.

Loop Engine has one universal Loop runtime. Starting, Spawned by, Queried by,
Retrieved by, and Connected from are relationships. Practitioner,
Intelligence, and Solution are roles. Run mode, step profile, thinking power,
typed contract, budget, permissions, loop condition, and exit condition are
separate settings.

Use a text or Mermaid tree when a document explains three or more architecture
branches. Start from this tree and extend one branch at a time:

Operational runtime type
└── Loop
    ├── LoopDefinition: ID, version, digest, profile, contract, modes, conditions, authority
    ├── LoopRuntimeContext: three public capability ports plus internal mechanics
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, or Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Purpose and domain categories
    ├── Selected mode: deterministic, hybrid, or non-deterministic
    ├── Budget, permissions, and effects
    ├── Model settings when model use is allowed
    └── Run History events

Authoritative static graph
└── LoopGraphDefinition
    ├── exact LoopDefinitionRef per executable vertex
    ├── typed edges
    ├── graph inputs and outputs
    └── graph version and content digest

Never use runtime type, role, profile, category, mode, or settings as
interchangeable terms.

Treat /home/username/taedri.dev only as a semantic design reference. Do not
copy files or create parallel registries. State a missing invariant, map it to
an existing Loop Engine boundary, implement the smallest typed extension, and
verify it inside Loop Engine.

Commit and push verified changes to main in the same turn, as the owner's
standing instruction requires, and keep another session's in-progress files
out of your commit. Do not call a paid provider, rerun a completed benchmark,
or perform external effects unless the current request authorizes that action.
```

## Reading order

1. [`AGENTS.md`](../../AGENTS.md)
2. [`README.md`](../../README.md)
3. [Contract index](../contracts/README.md)
4. [Taxonomy and class map](../architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
5. [Work-approach instrumentation](../architecture/WORK-APPROACH-INSTRUMENTATION.md)
   when work concerns prompt, context, memory-access, delegation, or approach
   experiments
6. [Component map](../components/README.md)
7. [Older reference-source boundaries](REFERENCE-SOURCES.md) only when older
   repository material may be relevant
8. [Loop object and profiles](../components/loop-object/README.md)
9. [Intelligence layers](../components/intelligence-layers/README.md)
10. [Core Architecture](../components/core-architecture/README.md)
11. [Solution Canvas](../components/solution-canvas/README.md)
12. [Case studies](../../case-studies/README.md) only when the task concerns
   measured full-system runs

For broad continued development, use the
[universal solver continuation brief](../prompts/LOOP-ENGINE-UNIVERSAL-SOLVER-HANDOFF.md).
It is the sole broad continuation prompt. Load one prompt for the active task.
Do not concatenate it with another file from `docs/prompts/`.

The [`session_handoff/v1` schema](../contracts/session-handoff.schema.json)
defines the optional generated packet. Do not hand-write a packet to fill an
ownership or evidence gap.

When the target model is GPT-6 Astra, also read the dated
[compatibility note](GPT-6-ASTRA-READINESS-2026-09-04.md). The architecture
remains model-neutral, and access remains unproven until an authorized probe.

For storage, structured notes, file/database queries, or memory-reference work,
read [queryable records and storage](../guides/queryable-records-and-storage.md)
and the [record-operation decision](../architecture/ADR-SCOPED-RECORD-OPERATIONS.md).
The [verification report](../verification/RECORD-ACCESS-AND-MEMORY-AUDIT-2026-09-04.md)
records the tested storage slice and open memory incidents. The
[package, harness, and memory audit](../research/STORAGE-PACKAGES-HARNESSES-AND-MEMORY-2026-09-04.md)
maps existing authorities before adding another abstraction. Its follow-up
closes the reproduced alias/snapshot defects and compares harness alternatives.
The [fresh hardening report](../verification/HARNESS-AND-MEMORY-HARDENING-2026-09-04.md)
records full source/clean-wheel results and the typed session handoff.
The later [output and mode-policy checkpoint](../verification/REASONED-OUTPUT-AND-MODE-POLICY-2026-09-05.md)
adds reasoned output allocations, shared three-mode views, conservative frontier
outcomes, and single-flight token accounting. Strict live requests still need a
qualified exact-request token bound. Do not replace missing bounds with a
character estimate or reuse archived live-run spending authority.
The legacy OpenCode raw-host execution path is quarantined; do not restore it
to make a smoke test pass. Separate brokered text-proposal adapters and the
experimental native Markdown loading controls have their own bounded evidence
in the September 12 configuration report. They do not qualify unrestricted
native tools or host execution. The [harness boundary](../components/core-architecture/MCP-AND-SKILLS.md#external-harness-boundary)
documents capability refusal, explicit registration, and post-run budget limits.
Use the host-configured record tool for managed notes. Do not directly edit its
database or immutable revisions. Existing authority Markdown and historical
evidence have not been migrated, and generated session views remain planned.

For the latest real model-training test, read the
[tabular portfolio report](../verification/TABULAR-MODEL-PORTFOLIO-2026-09-06.md)
and [reproduction guide](../../examples/25_host_runtime/TABULAR-PORTFOLIO.md).
All three requested public datasets completed: 33 real model calls and
36 fitted pipelines across three families plus a baseline per dataset.
The same host adapter handled each manifest without core changes. Candidate
selection used validation; separate containers predicted without test labels
and scored against sealed labels afterward. These are familiar datasets and
local scores, not unseen tasks or Kaggle leaderboard grades. Public downloads
were host preparation, not autonomous engine retrieval. Source rows and model
binaries remain local. Do not rerun or tune against these holdouts as though
they remain untouched.

For continued testing and publication, read the
[adaptive completion checkpoint](../verification/ADAPTIVE-COMPLETION-AND-PUBLICATION-2026-09-06.md).
The frozen package passed 3,363 source and 3,318 clean-wheel checks. Optional
host completion gates, typed serial dependency bindings, and explicit reactive
history persistence have offline coverage. Real pinned-container checks reject
known incorrect sources that smaller primary suites accepted. They do not
prove a live repair or general task quality. The exported-ticket fixture does
not connect to Jira or publish a branch.

For the unseen-task question, read the
[novel-task campaign report](../verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md).
Read its September 7 corrections before citing the original conclusions.
The campaign recorded 283 real model calls, but three prompts contradicted
their hidden cases and the later reference evaluator was inconsistent.
The original 9/10 survival and 10 percent false-acceptance claims are not
established. Separate task histories also prevented cross-task learning by
construction. Never reuse those ten tasks, their cases, or the audit seeds
as unseen evidence. Future claims need qualified prompt-and-evaluator
contracts, a pre-acceptance counterexample gate, explicit repair failure
classification, and a fresh sealed population. The
[unseen-task handoff brief](../prompts/UNSEEN-TASK-WORK-HANDOFF.md) is the
sole continuation prompt for that work.

The current capstone is the
[TrafficFlowBench native/OpenCode comparison](../benchmarks/TRAFFICFLOWBENCH-NATIVE-OPENCODE-PLAN.md).
Account entry is verified. Do not report a plan, file inventory, or unavailable
OpenCode arm as a completed comparison. The raw-host adapter remains
quarantined. Local scoring lacks official queue truth, physics boundary flows,
and most ODME terms. Preserve the queue forecast-origin information boundary.

For the preceding host embedding and source admission evidence, read the
[adaptive host generalization report](../verification/ADAPTIVE-HOST-GENERALIZATION-2026-09-06.md)
and [five-shape reproduction guide](../../examples/25_host_runtime/GENERALIZATION-PROBE.md).
This checkpoint separates spawned task contexts and verification, refuses
unsupported plan fields, repairs mixed source/output delivery, and retains
invalidated live results. Source checks passed 3,246/3,246 and clean-wheel
checks passed 3,201/3,201. That checkpoint predates typed dependency-output
bindings. Adaptive spawning remains serial; a live paired-assistance comparison
and production Overnight/Jira integration remain open. Do not treat final repaired artifacts as first-try
successes or reuse the audit cases as untouched holdouts.

Its final live artifact review passes 84/84 saved cases but independently
invalidates the latest Sales source for wrong exact totals. Keep that known
failure visible. The later completion checkpoint rejects this source with
additional source-bound counterexamples; no new live repair is claimed there.
The [history review](../verification/HISTORY-AND-OVERNIGHT-REVIEW-2026-09-06.md)
records log coverage and configured Kaggle account access separately from
task completion.

For the preceding host boundary, read the
[host adoption checkpoint](../verification/HOST-ADOPTION-AND-GENERALIZATION-2026-09-05.md),
[embedding guide](../guides/embedding-loop-engine.md), and
[host execution decision](../architecture/ADR-HOST-OWNED-EXECUTION.md).
The public host binding uses the existing Capability Directory and canonical
Loops. Host disclosure and exact effect approvals are explicit; host permission
names do not enable core file or command permissions. A seeded JavaScript
repair completed in two passes and 11 model calls after host tests exposed
the defect. The failed permission launch remains recorded. This is not an
unseen-task population or automatic persistent promotion. Final frozen checks
passed 3,120 source tests, 3,075 base-wheel tests, and 27 conformance gates in
each environment. Subsequent dataset/model evaluations need separate evidence.

For the preceding autonomous feedback work, read the
[current task-feedback report](../verification/AUTONOMOUS-TASK-FEEDBACK-2026-09-05.md)
and [architecture decision](../architecture/ADR-INDEPENDENT-TASK-FEEDBACK.md).
Generated projects require independent executable feedback by default.
One live task recovered a provider failure and passed engine-generated checks
without supplied feedback. Three canceled diagnostics remain explicit.
Task-local repair is not automatic persistent promotion or core self-modification.

For the preceding new-task attempt and generalization boundary, read the
[external-caller and code-only repair report](../verification/BRAIN-INTEGRATION-CODE-ONLY-2026-09-05.md).
It traces the actual duration-parser failure, fixes source-only artifact
delivery and captured instructions, and records real creation and repair
runs with independent checks. `solve_outcome/v5` introduced preservation of
unknown model-call totals and known subtotals. Current `solve_outcome/v6`
retains that accounting and adds stage and selected-action vector projections.
Failed-attempt tracking
and workspace visibility are repaired; broader ISO support, arbitrary harness
integration, and the separate CI audit remain outside those claims.

For the preceding campaign checkpoint, read the
[live Kaggle pilot checkpoint](../verification/KAGGLE-LIVE-PILOT-2026-09-05.md).
It records a real provider probe, explicit no-total-token-ceiling authorization,
source-integrity fixes, and a model-generated tool whose own passing tests missed
defects found by independent review. No Kaggle score exists in that checkpoint.
Its follow-up preserves the stopped repair and withdraws the agent-imposed
50-call ceiling. Call and pass limits already support `None`; do not invent a
replacement ceiling. The static path screen was corrected, but the saved
candidate still needs input bindings and independent execution checks. CI's
hardcoding audit also remains unresolved. The user's
no-monetary-ceiling instruction does not qualify strict token bounds or approve
raw competition-data export.

For the preceding diagnostic, read the
[new-task diagnostic report](../verification/UNSEEN-TASK-DIAGNOSTIC-AND-GENERALIZATION-2026-09-04.md).
Two real-provider attempts on one generated Kaggle-shaped case produced no
verified task completion. The second reproduced a post-dispatch token-budget
overshoot and left invalid, unexecuted candidate code. Live expansion stopped.
The next probe is sound pre-dispatch token reservation, not a larger budget.
Its [research note](../research/MODEL-ARCHITECTURES-COMPOSITION-AND-DEVICE-MESH-2026-09-04.md)
keeps domain knowledge in the four existing intelligence layers; device and
industry examples are test populations, never privileged runtime workflows.
The [coverage index](../research/ARCHITECTURE-COVERAGE-MATRIX-2026-09-04.json)
lists reviewed subsets and remaining research gaps.

For earlier learning work, read the
[learning-integrity implementation report](../verification/LEARNING-INTEGRITY-AND-RESEARCH-2026-09-04.md)
and its [research synthesis](../research/LEARNING-FROM-VERIFIED-LOOP-OUTCOMES-2026-09-04.md).
They record the later fixes for verifier-subject binding, adaptive accepted
state, and thin model-ladder evidence. The live paired gate remains open.

For broad architecture review, read the
[mesh and corpus audit](../verification/ARCHITECTURE-MESH-CORPUS-AUDIT-2026-09-04.md).
It records full Markdown coverage and local history inventory, separates
runtime behavior from proposals, and reproduces an unresolved verifier-subject
binding defect plus adaptive accepted/speculative state gaps. That audit
made no runtime fixes; use the later implementation report for their current
status. Other documented gaps remain open.

When the task concerns stage learning, hydrated material, action lineage, or
predictive-state evidence, including the mechanism-only control manifest and
its unresolved controls, first read the
[offline verification report](../verification/PREDICTIVE-STATE-PROCEDURAL-MEMORY-AND-STAGE-ASSISTANCE-2026-09-04.md),
with the later audit's subject-binding limitation.
Use the dated
[stage assistance integration audit](../verification/STAGE-ASSISTANCE-INTEGRATION-AUDIT-2026-09-04.md)
only as the historical defect trail; its intermediate counts are superseded.
When it concerns long-horizon skills, execution state, recursive inference,
recurrent models, or test-time memory, read the dated
[primary-source research review](../research/LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md).
When it concerns procedural reuse, predictive state, information measurements,
or the "AI muscle memory" research metaphor, read the narrower
[procedural-memory evidence note](../research/PROCEDURAL-MEMORY-PREDICTIVE-STATE-AND-INFORMATION-VALUE-2026-09-04.md).
For adaptive computation, repeated-task transfer, distillation, or cognitive
Loop templates, read the
[cognitive mesh research and design](../research/ADAPTIVE-COGNITIVE-MESH-AND-AMORTIZED-COMPUTATION-2026-09-04.md).
Its accompanying JSON catalog contains unbound design examples, not installed
profiles or qualified shortcuts.
When it concerns the Kaggle campaign, read the
[120-competition metadata report](../verification/KAGGLE-120-ACCESS-PREFLIGHT-2026-09-04.md).
Do not load these dated reports for unrelated work.

## Working-directory check

Run this before changing files:

```bash
pwd
git rev-parse --show-toplevel
git remote get-url origin
git branch --show-current
git rev-parse HEAD
git status --short --branch
git diff --name-status
git ls-files --others --exclude-standard
git worktree list --porcelain
ps -eo pid=,ppid=,etime=,stat=,comm=
```

The first two paths should both resolve to `/home/username/loop-engine`. The
remote should resolve to the Loop Engine GitHub repository. The process list
omits arguments and environment values because they may contain private data.
A matching working directory or process name does not prove ownership. Record
an owner only from an explicit claim.

## What not to include

Do not paste the full Taedri Constitution, Taedri reference manual, old Loop
Intelligence README, historical benchmark transcripts, or an entire prior chat
into a new Loop Engine session. Those sources contain project-specific or
stale details that can override the simpler Loop Engine architecture.

Bring over one verified invariant at a time. Keep its source revision and
reason visible in the resulting design note or change.
