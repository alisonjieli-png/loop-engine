# SoL-Pi and the Loop Engine harness boundary

Kind: primary-source review and proposed qualification plan. Reviewed September
19, 2026. The owner supplied the project-page text and paper image. This review
also inspected arXiv version 1 and the public implementation at
`bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1`. No SoL-Pi package was installed,
model called, or published result reproduced here.

## Decision

Support Pi with SoL-Pi as a candidate, configurable harness profile. Do not
replace Loop Engine, fork Pi, or enable every mechanism by default. Keep plain
Pi and other harness profiles available for comparison and fallback.

The current public release is an MIT-licensed Pi extension, not a separate
model server or a new operational runtime. Its package is version 0.1.0 and
marked private; the documented installation uses Git. It builds on public Pi
extension interfaces. This makes an extension-set profile a better initial
integration than a separate first-party harness implementation.
[Repository](https://github.com/NVlabs/SoL-Pi/tree/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1),
[package](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/package.json).

The reusable research method may matter more than the four initial features:
use trajectory evidence to propose a narrow change, keep its evaluation
independent, and preserve rejected attempts. This complements our architecture;
it does not establish that our current implementation already does it.

## Keep the runtime classification intact

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
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

```text
Loop-owned execution choices
├── Harness configuration
│   ├── Plain Pi
│   ├── Pi plus a pinned SoL-Pi extension set
│   └── Other admitted native or custom harnesses
├── Model configuration
│   ├── Existing text-generation endpoint
│   ├── Optional Jev, Circuit or compatible decision endpoint
│   └── Separately authorized auxiliary summarization endpoint
└── Outer Loop obligations
    ├── Exact assignment, permissions and cumulative allowance
    ├── Cancellation, effects, identity and Run History
    └── Independent task acceptance and candidate promotion
```

Users or their providers operate model endpoints. Launching a selected local
harness process does not make Loop Engine responsible for downloading,
launching or managing that harness's models.

## What the research establishes, and what it does not

The supplied project account describes 152 ideas and 535 development
environments. Independent lineages screened candidates before the final
evaluation. Humans supplied initial direction and refactored surviving work.
The released extension is the result, not evidence of a complete packaged
auto-research service or automatic learning from each customer's sessions.

The paper distinguishes 11 one-way acceptance tasks from 40 final tasks within
EdgeBench's 51 public tasks. Its displayed totals should not be described as
51 untouched final-test tasks. The highest-scoring single-feature configuration
is selected separately for each backend, unlike the frozen complete stack.
[Paper, sections 2.5 and 3.1](https://arxiv.org/html/2609.20519v1#S2.SS5).

Reported results, not Loop Engine measurements:

| Population and configuration | Baseline | SoL-Pi | Interpretation |
|---|---|---|---|
| EdgeBench, GPT-5.6 Sol, complete stack | Pi score 44.833; cost $1,339 | Score 42.003; cost $894 | Lower cost and lower aggregate score |
| EdgeBench, Opus 5, complete stack | Pi score 44.756; cost $1,741 | Score 42.224; cost $1,158 | Similar trade-off on another backend |
| Terminal-Bench 4, 63 CPU-only tasks | Pi solves 18; cost $286.45 | Solves 15; cost $211.12 | Three fewer tasks solved, despite lower cost per success |

Costs use the paper's August 17 price schedule. They are not present-day
invoices, infrastructure costs, or projected Loop Engine savings.
[Paper, tables 1 to 3](https://arxiv.org/html/2609.20519v1#S3).

The supplied project page is explicit that recursive efficiency compounding
and harness scaling laws remain research directions. Its swarm comparison has
one two-hour trial per condition; the single agent remains the cheapest. These
observations warrant experiments, not a universal preference for swarms.

## Four mechanisms, four different responsibilities

| Mechanism | Relevant idea from the supplied project description | Existing Loop Engine owner | Discriminating test before adoption |
|---|---|---|---|
| Action Fusion | Combine a known edit and its follow-up check without another model decision | Harness tool adapter, capability invocation and effect approval | Failed edit never runs the command; failed command never silently repeats a committed edit; combined effects need exact authority |
| ObservationPack | Keep original output available by reference instead of replaying its full body | Context artifacts, context packing and scoped materialization | A needed middle-of-file detail remains retrievable after packing, restart and permitted resume; another scope cannot recall it |
| Evidence-Preserving Reducer | A cheaper model extracts selected diagnostic evidence that code checks | Harness observation adapter, response admission and model-call accounting | Altered quote, wrong source digest, wrong exit status, omitted decisive failure and unavailable reducer all retain a usable original |
| Online Context Compact | Consider compaction at meaningful progress boundaries and charge for cache disruption | Native context control and explicit wrapper ownership | Compaction preserves unfinished obligations, never creates an unauthorized continuation and is cheaper including its own calls |

These are separate settings. There is no reason to make one feature flag own
all four. Mechanism ordering is also configuration with a contract: a verified
reduced observation must not then lose its evidence through another packing
stage. Test the actual composed stack, not just each component in isolation.

The implementation registers enabled features at session start and puts
compaction after the other context transformers. ObservationPack uses fixed
thresholds in source: output above 10 KiB, two full deliveries, then a 1 KiB
excerpt with recall. Its token estimate uses four characters per token; that
estimate is not provider-reported billing usage.
[Entrypoint](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/src/sol-pi/index.ts),
[observation implementation](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/src/sol-pi/extensions/observation-pack/observation.ts).

## Concrete integration findings

1. Our existing Pi manifest names version 0.85.1, which matches the release's
   tested version. However, our current text-only process recipe passes
   `--no-extensions`, `--no-tools` and `--no-session`. It will not load or
   exercise SoL-Pi. Removing those restrictions globally would be an authority
   expansion, not an integration fix. Add an explicitly governed extension-capable
   profile and qualify it separately.
   [Current recipe](../../src/loop_engine/core/harness_process_relay.py).
2. Upstream reports 140 offline tests on Pi 0.85.1 and 0.84.2. Its peer ranges
   are broad, but that is not qualification of every Pi release. Pin the exact
   runtime, extension commit, effective settings and extension order. Compaction
   continuation depends on particular session and event behavior, especially
   alongside other extensions.
   [Compatibility](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/docs/compatibility.md).
3. All four mechanisms default off. A trusted project configuration replaces,
   rather than merges with, the personal configuration. Record which file was
   effective. Do not equate a file placed in a workspace with a loaded feature.
   The cache write/read ratio is configurable and remains fixed when the
   session's model changes. Re-evaluate that policy on a provider switch.
   [Configuration](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/docs/configuration.md).
4. The reducer calls another model using Pi-managed authentication. Our outer
   budget and trace must observe that call, cancellation and usage, or the
   profile must keep reduction disabled. A key's availability does not grant
   permission to send diagnostic logs to that provider.
   [Reducer provider boundary](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/src/sol-pi/extensions/evidence-preserving-reducer/provider.ts).
5. Archives persist under the Pi session directory, and SoL-Pi is not a sandbox.
   Its likely-secret detector is a precaution, not a complete privacy control.
   We need session confinement, retention and deletion rules, and independent
   permission for remote reduction. No automatic upload into shared intelligence.
   [Security](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/SECURITY.md).
6. Action Fusion serializes its own fused operations by file and checks the
   file hash before the command. It is not a filesystem transaction or global
   lock against other processes. A file mutation can succeed before its command
   fails; preserve that partial effect and refuse an unsafe replay.
   [Fused execution](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/src/sol-pi/extensions/action-fusion/then-run.ts).
7. The compaction economics code contains declared heuristic constants for
   horizon, reserve and margins. Treat them as a candidate policy. Do not turn
   their defaults into universal model capacities or replace exact provider
   accounting with an estimate.
   [Economics](https://github.com/NVlabs/SoL-Pi/blob/bd005888b9b8a3fcdb511feb91fc27d3dfa8f2b1/src/sol-pi/extensions/online-context-compact/economics.ts).

## Comparison with our other choices

| Choice | Primary responsibility | Relationship to SoL-Pi |
|---|---|---|
| Loop Engine | Own typed work, authority, intelligence identities and independent acceptance | Outer owner; do not replace these responsibilities with extension behavior |
| Plain Pi | Execute a task using its selected models and tools | Required matched baseline and supported fallback |
| Pi with SoL-Pi | Change tool execution and context handling inside Pi | Optional harness profile, not another runtime type |
| Jev or Circuit | Return bounded typed judgments | Optional decision provider, not a substitute for generating diagnostic excerpts or executing tools |
| Retrieval engines | Find and rank intelligence | Complementary; observation recall during execution is not a complete cross-run retrieval service |
| Deferred optimization | Propose tested changes from permitted history | Can use the paper's research method without putting online self-modification in the serving path |

Keeping these choices independent lets the same task compare plain Pi against
an admitted extension set while holding the model, material and authority fixed.
It also avoids attributing a better model, extra context or more attempts to a
harness optimization.

## Proposed experiments and initial settings

Begin with all mechanisms off. Establish the plain Pi baseline through Loop
Engine's actual adapter. Then test ObservationPack alone and Action Fusion
alone on assignments where their mechanisms can actually fire. Keep original
observations and independent outcome checks available.

The reducer starts disabled until nested calls, log-sharing permission and
accounting are connected. Compaction starts disabled until stop, cancel,
resume, headless completion and extension ordering have passed. Each feature
needs an explicit fallback to the baseline behavior. Changed workspaces and
uncertain external effects require reconciliation before switching harnesses.

Use both short atomic assignments and long research/build assignments. Include
small outputs where packing should stay dormant, huge logs, multilingual text,
contradictory diagnostics, repeated failures, concurrent writes, missing
archives, malicious handles, model unavailability and exhausted authority.
Test failure preservation as well as successful completion.

For four binary features, the full grid has sixteen combinations. Start with
the baseline and four single-feature comparisons, then selected combinations
where interactions are plausible. Call that a screening design, not exhaustive
coverage. Evaluate the full grid only under a declared budget.

Freeze tasks, checks, model route and effort, source revisions, settings,
workspace snapshot and comparison rules before evaluation. Keep development,
candidate acceptance and final evaluation separate. Match paired tasks and
repeat enough trials to report uncertainty; retain non-triggered and failed
attempts in the denominator. Do not select a winning profile on the final test
set and reuse that same set as fresh proof.

Measure accepted task outcomes first. Then include uncached input, cache reads,
cache writes, generated output, reducer and compaction calls, retries, recall,
startup, elapsed time, memory and storage. Missing usage stays unknown. Useful
quoted evidence is not proof that every important fact was retained.

## Further ideas for Loop Engine

### Adversarial review of the supplied discussion

The supplied comments are prompts for investigation, not additional experiment
results. The following distinctions affect our adoption decision.

| Claim in the discussion | Assessment | Consequence for our comparison |
|---|---|---|
| The full stack has no capability loss | Not supported by the displayed averages or Terminal-Bench counts | Report the loss and its distribution; do not substitute a slogan for our acceptance contract |
| Every headline is one run with no variance | The swarm explicitly has one trial per condition. Main result tables do not provide uncertainty, but that alone does not establish every underlying repetition count | Request run manifests and repeat matched tasks; keep the broader accusation unconfirmed |
| The strongest performance point is selected on evaluation results | The reported Performance point chooses the best single mechanism separately for each backend | Treat it as a selected comparison, not a universally frozen winning profile; use a fresh final set for our selection |
| The numbers do not reconcile | The headline cost reductions reconcile with the displayed totals; no specific contradictory raw record was supplied | Name the exact denominator and record before asserting a numerical defect |
| Search cost is missing from the economic case | Complete research, integration and upkeep costs are not established by the reported serving-cost table | Measure adoption cost and break-even use; unknown search cost is not zero |
| This already proves compounding recursive improvement | The authors explicitly describe that as future work | Call the current mechanism discovery automated search; test a second generation before claiming compounding |
| Exact quotes make reduction safe | Exactness checks do not establish that all decisive evidence was selected | Include omitted failure lines, exceptions, negation and contradictory evidence in adversarial tests |
| The lesson is to build another harness from scratch | Not required by the released extension architecture | Reuse Pi and admitted extensions; keep our outer authority and acceptance contracts |
| Less output replay proves reasoning limits were only buffering flaws | The experiment does not isolate or establish that universal cause | Treat context handling as one optimization dimension alongside model capability and task design |

Recomputed from the supplied project totals: cost reductions against Pi are
33.23% for GPT-5.6 Sol and 33.49% for Opus 5. Aggregate score retention is
93.69% and 94.34%. The native-harness cost comparisons are 49.97% and 54.32%.
Those agree with the rounded headlines. The hourly ranges also reproduce when
the dollar differences are divided by 102 task-hours. That is a denominator
inference, not verification of actual elapsed utilization or a portable hourly
price promise.

Our break-even calculation should include research, integration, qualification
and maintenance, divided by the measured saving per accepted task when that
saving is positive. An unacceptable task-quality loss disqualifies the candidate
before that economic calculation. Aggregate tolerance must not hide a failure
on a required task family or a protected permission boundary.

### Candidate directions

An observation's useful lifetime can be a measured configuration dimension:
when should it stay inline, become a reference, be reduced, or be recalled?
Keep content identities and original bytes independent from these projections.
Use outcomes to propose changes, not to promote a generated summary as truth.

Try artifact-level learning before model training: repair an ambiguous tool
contract, improve a reusable instruction, or change a context-packing policy.
Attribute success and cost to the exact policy and actual triggering point.
Existing self-improvement Practitioner tasks may stage those candidates;
independent acceptance and the heuristic-adoption policy remain in force.

Disposable experiment workspaces are useful. Disposable authority and evidence
are not. A copied experiment template must still name its owner, input/output
contracts, budgets, effects, cleanup, cancellation and artifact destinations.
Keep a small stable controller while allowing bounded experiment-specific
composition. The project's criticism of one growing coordinator is a warning
against task-specific branches, not evidence that typed contracts are unnecessary.

These are proposals mapped to existing components. No source was ported, no
SoL-Pi profile was enabled, and no gain is claimed for Loop Engine.
