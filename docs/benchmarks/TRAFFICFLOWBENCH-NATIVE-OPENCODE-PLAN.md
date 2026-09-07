# TrafficFlowBench: native and OpenCode executor comparison

Status: proposed capstone, not an executed comparison. The configured Kaggle
account is already entered. OpenCode 1.17.9 is installed, but Loop Engine's
raw-host OpenCode execution profile remains quarantined. No data download,
competition submission, or harness comparison is authorized by this document.

The experiment tests whether a full coding harness improves the work performed
inside a bounded Loop. It does not replace the Loop runtime or require a new
harness instance for every helper function.

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Exact versioned role profile
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contracts
    ├── Loop and exit conditions
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when authorized
    └── Run History
```

## Compare two questions separately

| Arm | Execution | Question |
|---|---|---|
| A: native | Existing model/tool execution inside canonical Loops | Current baseline. |
| B: per-Loop OpenCode | The same bounded assignments use an approved OpenCode harness adapter | Does the execution harness help when model, inputs, and capability access are matched? |
| C: whole-task OpenCode, optional | One harness receives the same complete task and external gates | Is outer decomposition helping, or adding overhead? |

Run the controlled A/B first. Keep the model/provider route, input snapshots,
tool capabilities, approved skill catalog, verification, data visibility, and
resource authority equivalent. Count startup, context loading, retries,
internal model calls, tool calls, and verification cost.

A second product-configuration comparison may give each system its preferred
tools and context strategy. Label that as a bundled-system comparison. It
cannot isolate the effect of OpenCode when the available capabilities differ.

OpenCode discovers skill descriptions and loads bodies on demand. Availability
is not proof that a model consumed a skill. Record exact selected versions,
loaded bodies, effective configuration, and model-visible packet digests.
[OpenCode skill documentation](https://opencode.ai/docs/skills/).

## Qualification before OpenCode execution

Use the existing `HarnessRegistry`, `HarnessExecutionRequirements`, host
operations, and workspace adapters. The installed binary alone is not a
qualified executor.

Freeze the binary/package identity, configuration, plugins, skills, and tool
schemas. Use an isolated home/configuration and workspace, with no inherited
personal sessions or caches. Broker credentials and effects through the
approved interfaces. Protect evaluator code, held-out labels, and unrelated
files. Refuse undeclared network access, publication, and hidden subagent
spawning. Test cancellation and descendant cleanup, tool denials, output
capture, nullable usage, and restart without effect replay.

OpenCode's configuration has permissive defaults, and auto mode changes
approval behavior. Inspect the effective merged permissions, not only one
configuration file. Permission settings complement containment; they are not
proof of an operating-system sandbox.
[OpenCode permission documentation](https://opencode.ai/docs/permissions/).

Keep the existing quarantine until those checks pass. An unavailable B arm is
an infrastructure result, not evidence that A solves tasks better.

## Frozen organizer reference and scoring limits

Reference inspected: `jacky850/trafficflowbench-public` at
`205faf1b78d6f73a5e55e1168d161dcbbdb86a58`.
The code is MIT licensed; competition data and participation rules require
their own review. The package is approximately 13 GB unpacked, so it belongs
in a separate data workspace, not model context or this Git repository.
[Organizer repository](https://github.com/jacky850/trafficflowbench-public/tree/205faf1b78d6f73a5e55e1168d161dcbbdb86a58).

| Task | Available local evidence | Limit |
|---|---|---|
| State reconstruction | Released training answers support state-error evaluation. | Seal evaluation answers from both executors; training availability is not permission to expose holdout labels. |
| Queue forecasting | Input, horizon, and binary-output validation. | Official queue labels are withheld for every split, including train. |
| Physics | Submission and physical diagnostic checks. | Public fallback calculations lack organizer boundary flows and must not be reported as official physics scores. |
| ODME | Link-count consistency. | Local `S_link` is only part of ODME. Do not grade against a reference generated from the same prior/count inputs. |

These limits are stated in the organizer's
[local evaluation guide](https://github.com/jacky850/trafficflowbench-public/blob/205faf1b78d6f73a5e55e1168d161dcbbdb86a58/docs/RUN_LOCAL.md).
Do not construct a purported official composite from unavailable components.

The score weights are state 0.35, queue 0.30, physics 0.15, and ODME 0.20.
Directions are averaged within corridor families before equal family
aggregation. Task 3 uses the Task 1 submission rather than separate rows.
[Scoring specification](https://github.com/jacky850/trafficflowbench-public/blob/205faf1b78d6f73a5e55e1168d161dcbbdb86a58/docs/SCORING_SPEC.md).

The supplied Kaggle description and repository documents differ on handling
missing task rows. Use strict complete-task validation for submissions and
resolve the competition-level rule before official scoring. The CLI returned
a deadline string of `2026-11-07T06:55:00`; the supplied page says November 6.
Do not silently choose a timezone or deadline. Confirm the authoritative
Kaggle page, current rules, and submission limits before submitting.

## Temporal and information boundaries

Tasks 1, 3, and 4 permit offline estimation. Queue forecasting must see only
the allowed history through origin `T`; its horizon is after `T`. A state
estimate smoothed using later observations must not enter the queue arm, even
when its reported timestamp is at or before `T`.

Bind each data reference to its split, source lineage, available columns,
permitted timestamp range, and snapshot. Include tests that deliberately try
to access future observations or sealed answers. Unavailable low-quality ramp
readings remain missing evidence, not zero flow. All traffic-specific rules
belong in task contracts, data adapters, and verifier capabilities, not core
task-name branches.

## Execution sequence

1. Inventory the release, rules, evaluator files, data sizes, and access grants.
   Freeze exact bytes and hashes before an experiment.
2. Qualify the OpenCode adapter on small source-repair and tool-denial fixtures.
   Run unchanged native controls and account for every physical call.
3. Establish a Task 1 baseline on a predeclared real-data subset. Separate
   fitting data from evaluation answers. Check any subset adapter against the
   frozen scorer; a changed population is a local subset score, not a leaderboard score.
4. Run paired A/B assignments with randomized order and fresh, isolated state.
   Preserve failed, canceled, and unstarted attempts. Repeat before claiming a benefit.
5. Expand to coupled state/physics work, ODME, and causal queue windows. Keep
   unscoreable components explicit and validate the complete output row set.
6. Only after separate approval, produce and submit a fully validated combined
   file. Record official scores separately from local results.

For each pair, retain quality, false acceptance, completeness, latency, model
calls, token-accounting coverage, cost state, source/skill exposure, revisions,
human interventions, and negative transfer. Unknown usage is not zero.

Start with keep-versus-split decisions and observation-driven replanning. A
logical Loop can use code, a model, or a qualified harness; it need not create
another physical model call. Compare eager versus selective skill hydration
only as a declared later treatment. Do not claim causal assistance until the
existing canonical assignment, packet-comparison, and fresh-arm gates pass.
