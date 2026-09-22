# Model-call strategy and disagreement research

Kind: dated primary-source research and proposed boundary decision. Reviewed
September 22, 2026. This record is input for Claude Code's S-6.30,
S-6.31, S-6.58 and newly proposed S-6.60 work. It changes no runtime
contract or model authority.
The [configuration dimension requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
already names model-call strategy separately from model, route, output
allocation, run mode and effect permission. The owner clarified that “JAB”
means **TypeSafe Jev**.

## Complete runtime classification

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

The proposed strategy is a typed component behind an existing Loop-owned
model-call edge, with swappable engines. It is not another runtime or graph
vertex. A process or container boundary may be an engine placement choice;
placing the strategy in a container would not itself grant model, network,
file or spending authority. Read the [layered harness direction](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
before assigning overlapping native controls.

## Which decisions already have owners

| Question | Current owner and status |
|---|---|
| Given a typed deterministic-sufficiency finding, is a model unnecessary; otherwise, which one eligible route is preferred? | [Model routing selector](../../src/loop_engine/core/model_routing_selector.py) and configuration preferences. The caller supplies the sufficiency finding; the selector does not infer it from task prose. This is route eligibility and choice, not an ensemble. |
| Which provider executes an authorized attempt? | [ModelGateway](../../src/loop_engine/core/model_gateway.py) invokes a named provider route, handles typed failures and records physical attempts. Provider failover tries another route after failure; it is not voting among successful answers. |
| Can a fast bounded model answer a typed decision? | [Typed decisions](../components/typed-decisions/README.md) admit Jev, Circuit and System One profiles behind a versioned request and capability check. No live Jev quality route was qualified in this audit. |
| How much may a route return? | [Model output allocation](../../src/loop_engine/core/model_capabilities.py) binds an allowance to source-backed exact capacity and route evidence. Unknown capacity remains unknown. |
| Is the step result acceptable? | The owning Loop and independent verifier. A provider's successful response, Jev probability, model agreement or syntactically valid output cannot approve the task. |

The missing choice is **call topology** for one semantic assignment: no
model, one model, a sequential cascade, several independent candidates, or
a targeted deliberation and adjudication procedure. The current
[ModelExecutionSession](../../src/loop_engine/code_nodes/solution_model_port.py)
is single-flight. Parallel fanout therefore needs a shared atomic allowance
reservation and unknown-outcome reconciliation before it can be qualified.
This is an inference from the current source and owner's requested behavior,
not a claim that a new component already runs.

```text
Loop-owned model work
├── Typed task and accepted-output contract
├── Eligibility and authority: effects, recipients, model routes, budget
├── Model-call strategy choice: no model, one, cascade, candidates, adjudication
│   ├── Optional Jev or other bounded decision evidence
│   └── Exact initial choice and ordered fallback triggers
├── Per-member exact route and output allocation
├── ModelGateway physical provider attempts
└── Independent evaluation and acceptance by the owning Loop
```

## Candidate versioned strategy record

This is a research proposal, not an approved schema. A first engine should
pass through the existing single-call path, so a new edge can be tested
without changing its result. A second engine may return `no_model` when
typed deterministic evidence is sufficient. Additional engines need
separate qualification.

| Field or decision | Required content and refusal |
|---|---|
| Semantic request | Exact assignment, task input digest, typed output contract, step profile and evaluator reference. A strategy cannot infer authority from prose or tags. |
| Strategy | `no_model`, `single`, `sequential_cascade`, `independent_candidates`, or an explicitly experimental deliberation profile, with version and selected engine. Unknown strategy refuses before a call. |
| Member eligibility | Exact configured provider, model, route, capabilities, context and output capacity for each call; named exclusions and reasons. A requested cross-provider member needs its own grant. |
| Total authority | Remaining physical calls, tokens, time and spending, plus file/network/secret/external-effect scope and permitted data recipients. Every member and auxiliary judge draws from the same cumulative allowance. |
| Selection evidence | Initial choice, alternatives, confidence or unknown state, decision method, expected cost and quality assumptions, source of estimates, and ordered fallback triggers. A model score does not grant permission. |
| Execution identity | One occurrence for every physical primary, failed, retry, compaction, judge and losing-candidate call; provider-reported usage, cache reads/writes and unknown cost stay distinct. |
| Disagreement policy | Which questions can be resolved by tests or facts, which need an independent verifier, which may use calibrated vote or ranking, and when to return an inconclusive result or ask the owner. Candidate outputs and dissenting evidence remain addressable by exact digest. |
| Effect reconciliation | Candidate generation does not replay a committed external effect. Cancellation and unknown provider completion cannot be reported as clean success or silently retried. |

The initial strategy and fallback order are part of the host and Loop
configuration within their authority. A deterministic no-model path may be
the first choice for a task with a qualified exact component. A generative
task may begin with one pinned model. A verifier rejection can permit repair
or another member only if the remaining allowance and declared policy do.
A provider outage triggers its own same-provider or authorized cross-provider
path, not a quality escalation. A missing credential, unqualified route or
exhausted budget cannot become an ensemble by fallback. The owner-specified
[dimension record](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md#recorded-baseline-dimensions)
requires each dimension's exact initial and ordered fallback choices.

## TypeSafe Jev's proper role

[TypeSafe's documentation](https://docs.typesafe.ai/introduction) sends a
shared state and typed questions to Jev. Choice and Score return
probability distributions and confidence; Noul returns a probability for a
truth-valued statement. The vendor says the questions can be evaluated in
parallel. [Its announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
describes fast structured decisions, not generation of code or arbitrary
task completion. The published speed, price and calibration results are
vendor claims on their evaluated populations.

A bounded Jev call could advise which **eligible** strategy or route to
try, or whether a specific check needs further evidence. The deterministic
eligibility rule must first remove disallowed models, recipients and
effects. Jev's probability is evidence to calibrate against later accepted
outcomes, not a permission, a fallback grant or independent acceptance.
Batching many questions can save decision overhead when they share a valid
state; it can also add an unnecessary model call to a step whose method is
already exact. Compare both.

## The proposed million-task learning loop

The owner wants to record many step decisions, then inspect where logic,
decision methods, intelligence or retrieval failed. The proposed
[Constitution learning rule](../architecture/CONSTITUTION.md#le-data-001-proposed)
sets a declared minimum initially at one million runs before a learned
heuristic affects routing, apart from an exact atomic fingerprint. That is
a threshold proposal, not a claim that one million representative task
outcomes have been collected or that any model becomes calibrated at that
count. Failed and excluded attempts need the same identity as successes.

For each consenting run, a training candidate can name the step contract,
eligible strategy and routes, exact selection method and probability when
an experiment randomizes, chosen configuration, supplied context references,
physical attempts, later independent outcome, and cost completeness. Keep
raw customer prompts and code out of hosted telemetry by default. The
record's version and digest must bind the decision to the exact outcome;
provider-reported missing usage remains unknown. Self-generated records
stay candidate-only until independent qualification.

The [doubly robust policy evaluation work](https://arxiv.org/abs/1103.4601)
explains a crucial inference limit: ordinary run history observes the
outcome of the strategy actually chosen, not what another model set would
have done. A million single-route runs cannot by count alone prove a
counterfactual ensemble would improve them. Authorize a bounded, frozen,
paired or randomized comparison; record its assignment probabilities and
eligible alternatives; use the same independent evaluator; retain task
regions without overlap as unknown. Change a serving policy only after
its quality floor, cost and privacy effects pass held-out work. The
[OpenSquilla data-flywheel paper](https://arxiv.org/html/2607.11399#S5)
is direct prior art for trajectory-linked routing records, while its
environment labels and judged steps need the same independence audit as any
local proposal.

## Primary research and code to compare

| Source | Relevant mechanism | Limit before reuse |
|---|---|---|
| [RouteLLM](https://github.com/lm-sys/RouteLLM/tree/0b64fdafe049e596a3f5657c219329f24af24198), Apache 2.0 | Learned strong-versus-weak routing from preference data. | Workload-specific calibration is required; its leading router recipes use an external embedding key. It selects a route, not a multi-model executor. |
| [FrugalGPT](https://arxiv.org/abs/2305.05176) and [BEST-Route](https://arxiv.org/abs/2506.22716) | Learned cascades and joint model/sample-count choice. | Their reported gains belong to their tasks and model pool. Recreate with exact Loop Engine route, authority and acceptance controls before adopting a policy. |
| [Together Mixture-of-Agents](https://github.com/togethercomputer/MoA/tree/1b5cab0f0905d9da821e37322ac6df96ba65e1a7), Apache 2.0 | Parallel candidate models feed an aggregator in layers. | Its example fixes a provider and generation settings and cannot be copied into the typed authority path. Aggregation is not independent verification. |
| [OpenSquilla](https://github.com/TokenRhythm/opensquilla/tree/9bcdf25d3265bf360166deff50af7fc3952a8029), Apache 2.0, and [Agentic Routing](https://arxiv.org/html/2607.11399) | The paper proposes harness-state-conditioned choice of one model or a complementary set, with trajectory, outcome and cost records to improve the router. Its repository has an open LightGBM cold-start ranker. | This is direct prior art for the owner's idea. Author-reported results use their harness, model pool and evaluators; some step rewards use model judgment. They do not establish independent Loop Engine task acceptance. Review exact code and rights before considering an engine adapter. |
| [LLM-Blender](https://github.com/yuchenlin/LLM-Blender), Apache 2.0 | Pairwise ranking and generative fusion of outputs. | Preference ranking is distinct from task correctness and effect safety. |
| [LiteLLM routing](https://docs.litellm.ai/docs/routing) and [DSPy](https://github.com/stanfordnlp/dspy) | External load balancing or offline prompt and program optimization. | Treat a proxy as a provider adapter and assign one owner to retries. Offline tuning does not grant runtime permissions. |
| [Devin Fusion](https://cognition.com/blog/local-fusion) and [Augment Prism](https://www.augmentcode.com/blog/augment-prism-model-routing-to-reduce-cost-and-maintain-quality) | Persistent lead/sidekick and cache-aware per-turn model routing. | Both challenge nominal cheap-model savings. Count bootstrap, cache eviction, corrections, review and cost per accepted task. Their published results are not local qualifications. |

## When several models help and when they fail

[Self-consistency](https://arxiv.org/abs/2203.11171) improved selected
reasoning benchmarks by sampling and choosing a common answer. A
[NeurIPS 2025 comparison](https://proceedings.neurips.cc/paper_files/paper/2025/hash/934252acd87f254d5d4672fbde283bd2-Abstract-Conference.html)
found majority voting explained most debate gains in its seven tasks.
An [ICML 2024 study](https://proceedings.mlr.press/v235/smit24a.html)
did not find a reliable debate advantage over simpler sampling without
careful tuning. [LLM judge research](https://arxiv.org/abs/2306.05685)
documents position, verbosity and self-enhancement biases. These results
make voting, debate and model judgment experiment arms, not default truth
rules. Agreement among correlated models can still be wrong; disagreement
may reveal a missing requirement rather than an answer to average.

[Anthropic's research-system account](https://www.anthropic.com/engineering/multi-agent-research-system)
reports gains for breadth-first research with a frontier lead and focused
subagents, alongside much higher token use than chat and weaker fit for
tightly dependent coding work. That makes decomposability and total
coordination cost explicit inputs to the strategy decision.

The [OpenSquilla PinchBench comparison](https://arxiv.org/html/2607.11399#S4.SS3.SSS2)
illustrates the multiple objectives. Its selected multi-model configuration
reports lower average dollar cost than a fixed Opus 4.8 comparison but more
total tokens and longer median elapsed time, with nearly equal benchmark
quality. That is an author-reported selected configuration, not a general
proof that a model set is cheaper or better. It shows why one efficiency
percentage hides cost, latency and accepted-result trade-offs.
Its [formal selection set](https://arxiv.org/html/2607.11399#S3.SS1)
has at least one model; Loop Engine's existing typed no-model routing branch
is a separate candidate worth preserving when code or deterministic evidence
already satisfies the step. That branch alone does not prove task acceptance.

Preserve every candidate, its exact model and route, and its dissenting
evidence. Resolve with programmatic tests, external facts or a qualified
independent evaluator when one exists. When no check can decide, return an
inconclusive result or a scoped question rather than silently selecting a
majority. A model that produced a candidate cannot approve it solely by
judging its own output. The best policy can differ by task, risk, model pool
and permission boundary.

## Matched experiment and known-wrong cases

Use frozen tasks from coding, research and data work, including ambiguous
requirements, a fully deterministic subtask, an answer with a known-wrong
majority, an external effect that must never repeat, and a task that needs
new evidence after disagreement. Keep the same task inputs, model routes,
total physical-call and spending allowance, tools, evaluator and output
contract for every eligible arm:

1. Qualified deterministic path with zero model calls.
2. One pinned model and current gateway behavior.
3. Sequential cascade after a declared substantive failure.
4. Repeated independent candidates from one model.
5. Heterogeneous models with a declared comparison or adjudicator.
6. A persistent lead and sidekick where the same routes can be configured.

Report task acceptance, false acceptance, abstention, all physical calls,
input/output/cache usage, elapsed time, monetary cost or unknown cost,
cross-provider disclosure, disagreement and repair cost. Compare a quality
floor before cost. A parallel strategy must reserve the combined allowance
before any dispatch and reconcile unknown completion. A fresh-per-step arm
must include start-up and cache-write overhead. Preserve candidates that
lost and calls that failed.

The named future checks should reject: a Jev result that broadens a route
or budget; an ensemble member with an unsupported output capacity; a
cross-provider call without its grant; a known-wrong majority accepted
without independent evaluation; a cancelled branch charged as zero despite
unknown usage; missing candidate digests; and a repeated external effect.
Removing each guard must fail its owning check. No real provider comparison
was run for this research. The new model-call strategy layer is tracked as
proposed S-6.60 in the [roadmap](../roadmap/roadmap.yaml); no implementation
or model-call authority is established by that entry.
