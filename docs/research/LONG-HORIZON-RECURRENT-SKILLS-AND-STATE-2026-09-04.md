# Long-horizon recurrence, skills, and state

Review date: 2026-09-04

This review reaches one practical conclusion. Loop Engine should test a compact,
verified execution-state projection inside the existing Loop runtime. It should
not create another runtime, infer a neural architecture from an API feature, or
let a mutable state summary replace Run History.

The paper at the center of this review is
[SKILL.state v3](https://arxiv.org/abs/2608.26263v3), revised on 2026-09-02.
Its author block lists two Google LLC authors and one Purdue University author.
SKILL.state is an agent execution architecture. It is not a
file format and does not define the meaning of `SKILL.md`. The shared word
"skill" hides two different layers:

- SKILL.state defines what an agent receives at each execution step and what
  state survives to the following step.
- A `SKILL.md` file is the instruction manifest inside a skill bundle. The
  Agent Skills standard does not require a version field in that file.
  OpenAI's official [Build skills](https://learn.chatgpt.com/docs/build-skills)
  page and [Skills API guide](https://developers.openai.com/api/docs/guides/tools-skills)
  describe that packaging contract.

All numerical research results in this document are author-reported and were
not reproduced in Loop Engine. This review made no model or provider calls and
ran no paper code. It compares reported mechanisms, study designs, and limits.
The earlier [cache-economics review](SKILL-STATE-EXECUTION-AND-CACHE-ECONOMICS.md)
contains a worked cost model for transcript-prefix caching. That model is an
assumption-driven estimate, not a provider bill or benchmark result.
The narrower
[procedural-memory and predictive-state note](PROCEDURAL-MEMORY-PREDICTIVE-STATE-AND-INFORMATION-VALUE-2026-09-04.md)
defines the implemented offline evidence contracts and their seven control
probes.

## Architecture boundary

The research does not change the repository's runtime classification.

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

An execution-state snapshot is passive data owned by a Loop. A state compiler,
state updater, verifier, retriever, or recovery process is work and therefore
must be owned by a classified Loop. An embedding index, recurrent model,
provider conversation, skill bundle, state schema, or cache remains a passive
record or an internal runtime mechanic.

## Six meanings that must stay separate

| Term | Where state lives | Update mechanism | What it does not establish |
|---|---|---|---|
| Execution state | Typed records outside the model | Validated state transitions | Model learning or neural recurrence |
| Persistent agent memory | Run History, artifacts, and admitted intelligence | Retrieval, consolidation, review, and promotion | Current truth or automatic authority |
| Recursive inference | A model or harness calls bounded subproblems | Programmatic decomposition and joining | Cross-run learning |
| Neural recurrent state | Hidden activations or state-space variables | Token-level recurrent equations | Durable task memory after reset |
| Test-time learning | Selected model or memory parameters | An inference-time optimization rule | Safe self-improvement of the whole system |
| Skill bundle | Instructions, resources, and optional scripts | Versioned file publication and admission | Live execution state |

Recurrence means that a transition is applied repeatedly. Recursion means that
work invokes another bounded instance of related work. Learning means that a
future policy or model changes because of evidence. A system can have any one
of these properties without the other two.

## Scalable `SKILL.md` packaging

OpenAI's current Build skills documentation and the open Agent Skills
specification use progressive disclosure:

```text
Skill context
├── Startup metadata
│   ├── Shared standard: name and description
│   └── Codex host behavior: skill file path too
├── Activated procedure
│   └── Full SKILL.md instructions for one selected skill
└── Selected resources
    ├── scripts
    ├── references
    └── assets
```

OpenAI documents an initial Codex skill-list budget of at most 2 percent of
the context window, or 8,000 characters when the context window is unknown.
Descriptions are shortened before complete skills are omitted. The open
specification recommends fewer than 5,000 tokens and fewer than 500 lines for
the activated `SKILL.md`, with detailed material moved into shallow referenced
files. These are packaging and loading rules. They do not define execution
state, verification, or learning.

Loop Engine's current startup card omits local file paths as well as complete
instructions and requested tools. This is an intentional private discovery
projection, not an exact reproduction of the Codex host's initial list.

The standard frontmatter contains `name`, `description`, and optional
`license`, `compatibility`, `metadata`, and experimental `allowed-tools`.
Loop Engine must treat `allowed-tools` as a request, not permission. A skill
cannot grant the model, network, file, shell, spending, or external-effect
authority needed to run a tool.

This separation suggests three cost controls with different maturity:

1. The passive registry can return compact discovery cards without including
   complete instructions, paths, or tool requests in that projection. The
   cards are not yet integrated with the product prompt.
2. The registry loads one procedure only after selection and digest
   verification. Task use also requires an exact admission record.
3. A future resource materializer should load supporting files only when the
   owning Loop states the need, authority, byte budget, and consumer. The
   current loader returns file references but does not enforce this complete
   per-resource policy.

Long-horizon state belongs beside the activated procedure, not inside a
continually rewritten `SKILL.md`. Cross-run learning should create a candidate
new skill version, state schema, retrieval policy, or verifier. It should not
silently mutate the admitted procedure used by the active run.

## Close reading of SKILL.state

### Execution contract

SKILL.state replaces a growing transcript with three inputs at step `t`:

```text
A_t = (P, Sigma_t, O_t)

P       immutable procedural specification
Sigma_t current structured execution state
O_t     latest environment observation
```

The model produces transient reasoning, a state patch, and an action. The
runtime validates the patch, merges it into the current state, performs the
action, and supplies the resulting observation to the following step. Prior
actions, observations, and reasoning are not replayed to the model. The paper
uses dictionary merge with null-deletion semantics. It also reports one static
five-field schema for all 100 InterCode CTF tasks. The fields track discovered
flags, tested hypotheses, active files, working directory, and a command
summary. See the paper's
[method and schema description](https://arxiv.org/html/2608.26263v3#S3).

This is an execution policy over context. The immutable procedural
specification could come from a `SKILL.md` bundle, a Loop profile, a task
contract, or another admitted source. SKILL.state does not require any one of
those formats.

### Reported evidence

The following figures are author-reported and unreproduced here. On the
synthetic warehouse benchmark with Gemini-3-Flash and five generator seeds,
the paper reports this comparison at a 100-step horizon:

| Runtime | Accuracy | Cumulative tokens | Mean prompt size |
|---|---:|---:|---:|
| Transcript plus structured state | 0.91 | 1,062,387 | 31,354 characters |
| SKILL.state | 0.94 | 65,408 | 1,905 characters |

The stateful baseline used 16.2 times as many cumulative tokens.
At 200 steps, they report 0.94 accuracy and 122,384 tokens for SKILL.state,
compared with 0.88 and 5,041,164 tokens for the stateful baseline. A
budget-matched 100-step comparison reports 0.94 for structured state, 0.52 for
a capped natural-language summary, 0.22 for LLMLingua compression, and 0.18
for a sliding window. These results support the claim that field semantics can
matter more than equal prompt length. They do not prove that one schema works
for open-world tasks.

On public tasks, the authors report 54.2 percent pass@1 on 100 InterCode CTF
tasks, compared with 46.4 percent for the strongest listed baseline. They
report 58.3 percent on the retail portion of Sierra tau-Bench and 32.4 percent
on its airline portion. The paper's
[result tables](https://arxiv.org/html/2608.26263v3#S5) contain the complete
runtime and token comparisons.

The open-weight error analysis is directly relevant to cheap-model routing.
For Gemma-4-31B-it at a 100-step horizon, the authors classify 68 percent of
errors as premature state overwrite or deletion, 20 percent as schema or type
errors, and 12 percent as JSON syntax errors. A smaller state updater is not a
safe shortcut merely because its output parses.

### The bounded-state claim is conditional

The paper writes the per-step prompt size as:

```text
|P_t| = O(|P| + |Sigma| + |O|)
```

It then calls the prompt footprint `O(1)` in execution horizon `T`. That result
requires `P`, `Sigma`, and the latest observation to stay bounded as `T` grows.
An open-world task can violate that condition. A changing question frontier,
growing set of unresolved dependencies, or large latest observation can make
the state grow. Loop Engine should measure state size against horizon and task
complexity rather than record `O(1)` as an invariant.

### Limits stated by the authors

The paper names three cases where its sufficient-state assumption can fail:

1. No fixed schema is known and the state structure must be discovered during
   execution.
2. An earlier observation becomes relevant after it was discarded.
3. The historical trajectory is itself the requested output, as in audit,
   provenance, or explanation work.

It also evaluates a single-agent execution design. Concurrent state writes
would need deterministic conflict resolution. These limits appear in the
paper's [limitations section](https://arxiv.org/html/2608.26263v3#S7).

Loop Engine has one additional constraint. A mutable current-state view must
not erase the immutable evidence needed to audit, replay, diagnose, or assign
stage outcomes. The practical design is an immutable sequence of snapshots and
verified deltas that presents a mutable logical state to the next Loop.

## Agent execution and memory research

The closest related work changes the harness around a frozen model. These
approaches can inform Loop Engine directly because they operate at the same
systems layer.

### ReasoningBank

[ReasoningBank v2](https://arxiv.org/abs/2509.25140v2), revised on 2026-03-16
and accepted at ICLR 2026, distills strategy-level memories from successful
and failed trajectories. At test time it retrieves memories and later adds new
ones. Its memory-aware test-time scaling method generates several experiences
per task so that contrastive evidence can improve memory extraction.

The useful idea is outcome-linked strategy memory, including failures. The
main caution is attribution. The implementation uses an LLM judge for
success and failure labels, simple embedding retrieval, and simple
consolidation. The authors identify judge noise and limited retrieval and
composition as limitations. A final task label is too coarse to train
Loop-level route or skill decisions without stage evidence.

### Recuris

[Recuris v1](https://arxiv.org/abs/2608.24876) separates working memory from
experiential memory. Working memory tracks verified progress and unresolved
goals. That state selects relevant skills. After an action, checkers decide
which proposed state changes the observation supports. The resulting trace
links state, selected skill, action, observation, proposed update, checker
decision, committed update, and task outcome.

Across tasks, a fixed meta-agent selects one or more parts of the memory-control
layer for repair: experiential skills, working-state specification, invocation
policy, or checker. The authors describe this as a repair attribution, not
causal identification; several mechanisms may contribute. The system proposes
a local patch. A fixed gate admits the patch only if it repairs the source
failure and passes regression criteria on held-out tasks. The model and outer
procedure remain fixed.

Author-reported, unreproduced results cover four benchmarks and ten models.
The paper reports improvement in 35 of 37 completed model and benchmark pairs,
including gains of 17.8 points for GPT-5.6 Sol and 15.6 points for Claude Opus
5 on τ²-Bench. The incomplete pair count, differing task populations,
and very recent v1 status limit any general claim. The verified state update
and local, regression-gated patch are still strong design candidates.

### SkillGLoW

[SkillGLoW v1](https://arxiv.org/abs/2609.02217), submitted on 2026-09-02,
argues that a reusable unit should be a procedure shared by a family of tasks.
It groups task-local skills into procedural families, removes instance detail
from the shared prior, and regenerates local detail for a new task. A commit
gate checks that a proposed prior does not reduce performance in the deployed
library.

Author-reported, unreproduced results span four benchmarks and three models.
The paper reports a mean 17.2 percentage-point gain on its hard-score metric
across 12 runs. At the last round, its family library has 0.309 times as many
entries and 0.278 times as many words as the task-specific pool. The paper
reports the reciprocal word ratio as 3.6 to 1. On 60 unseen
held-out ALFWorld tasks, the three-model mean rises from 73.9 to 83.9 percent
without modifying the learned prior. The central risk is false
de-instantiation: a procedure can lose a condition that looked task-specific
but was causal. Family discovery, negative transfer, and the commit gate all
need independent holdouts.

### PILOT

[PILOT v1](https://arxiv.org/abs/2608.26530) combines a worker with a separate
supervisor. The supervisor can steer or abort an active run. It also converts
procedures and failure modes observed during supervision into persistent
skills and memory.

Author-reported, unreproduced results cover two frozen open-weight backbones
and three benchmarks. In its one-shot comparison, the paper reports first
place among the evaluated counterpart harnesses in five of six configurations.
Across self-improvement iterations on Terminal-Bench 2.0, each backbone's best
observed pass rate rises by 14.6 and 12.4 percentage points, while mean output
tokens fall by 42.9 and 47.4 percent over the reported iteration windows. Its
own limitations state that repeated
evaluation is expensive, the benchmark and backbone set is small, and the
supervisor and worker use the same backbone. Live steering therefore needs a
control for harmful intervention, not only a count of recovered runs.

### Recursive Language Models and Prime Agent

[Recursive Language Models v3](https://arxiv.org/abs/2512.24601v3) treats a
long prompt as an external environment. The model writes code to inspect and
split it, calls language models on selected parts, and recursively joins the
results. This is inference-time context processing. It does not update the
base model or create durable learning by itself.

The paper reports processing inputs more than an order of magnitude beyond the
base context window, with median gains over several named scaffolds on four
long-context tasks. It also reports that a post-trained 8B RLM model improves
by a median 28.3 percent over its base model across four tasks. Those comparisons are
author-reported and unreproduced. Recursive calls can increase cost, branch
count, and attack surface. The fair comparison for Loop Engine is against its
Context Intelligence compiler, progressive artifact loading, and compaction,
under the same model-call and token budget.

[Prime Agent v1](https://arxiv.org/abs/2608.23552) combines the RLM idea with a
persistent IPython process, recursive sessions, direct session communication,
retained histories, revisable memories, and reusable skills. It separates
active model context from program state and disk-backed state. The paper
describes an 85.5-hour nanoGPT run and reports a change from 30 to 95.5 percent
on its ARC-AGI-3 RHAE Best@1 setup, plus results across coding and simulation
tasks. This is a technical report and the results are not reproduced here.
Cross-harness comparisons need exact task, model, budget, evaluator, and tool
controls before they support a Loop Engine claim.

### Scaling agent systems

The current v3 of
[Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296v3)
evaluates 260 configurations across six benchmarks, five coordination
architectures, and three model families. The authors report relative changes
from plus 80.8 percent on decomposable financial reasoning to minus 70.0
percent on sequential planning. They also report that their predictor selects
the best architecture for 87 percent of held-out configurations, with a
cross-validated `R^2` of 0.373, or 0.413 with a task-grounded capability
measure.

These author-reported results argue against unconditional delegation. Parallel
work can help when branches are independent. Coordination can hurt sequential
work or tool-heavy tasks. Loop Engine should treat branch count, join policy,
verifier topology, and communication budget as experiment variables selected
from task state. The model that chooses a graph still cannot broaden authority.

## Neural recurrence and test-time memory

The following papers change the sequence model itself. They are relevant to
future model routes and custom-model experiments. They do not justify a change
to the Loop runtime.

| Work | Recurrent state | State update | Reported scope |
|---|---|---|---|
| [Mamba](https://arxiv.org/abs/2312.00752v2) | Fixed-size selective state-space state | Input-dependent propagation and forgetting | Language, audio, and genomics |
| [Mamba-2](https://arxiv.org/abs/2405.21060) | Fixed-size selective state-space state | Structured state-space duality connects recurrent and quadratic forms | Language modeling and associative recall |
| [Griffin](https://arxiv.org/abs/2402.19427) | Gated linear recurrence plus local attention | Learned recurrent gates | Language modeling through 14B parameters |
| [RecurrentGemma](https://arxiv.org/abs/2404.07839v2) | Griffin fixed-size state | Linear recurrence plus local attention | Open 2B and 9B language models |
| [TTT](https://arxiv.org/abs/2407.04620v4) | A linear model or MLP acts as hidden state | Self-supervised gradient update on the test sequence | Models from 125M to 1.3B parameters |
| [Titans](https://arxiv.org/abs/2501.00663) | Deep neural long-term memory plus attention | Gradient surprise, momentum, and forgetting | Language, reasoning, genomics, and time series |
| [Miras](https://arxiv.org/abs/2504.13173) | Configurable associative memory | Chosen objective, retention rule, and optimizer | Moneta, Yaad, and Memora sequence models |
| [Nested Learning and Hope](https://arxiv.org/abs/2512.24695) | Several nested memory and optimization levels | Distinct context flows and update frequencies; Hope learns a self-referential update rule | Proof-of-concept continual and long-context learning |

Mamba makes state-space parameters depend on the input so the model can select
what to propagate or forget. Its authors report linear sequence scaling,
5 times the Transformer inference throughput in their setup, and
Mamba-3B performance that matches a Transformer twice its size. Mamba-2 uses
state-space duality and reports a core layer two to eight times faster than
Mamba. Griffin mixes gated recurrence with local attention. RecurrentGemma
packages that architecture in open models and reports performance comparable
to similarly sized Gemma baselines with fewer training tokens. All of these
are author comparisons under their own training and evaluation conditions.

TTT makes the hidden state a model and updates it with a self-supervised
learning step on the test sequence. Titans extends that line with a deep
neural memory. Its "surprise" is the gradient of an associative memory loss,
carried with a momentum-like state and controlled by learned decay and
forgetting terms. The authors report context tests beyond two million tokens.
Miras generalizes these designs along four choices: memory architecture,
attentional-bias objective, retention gate, and memory learning algorithm.

Nested Learning treats model components and optimizers as nested learning
problems with different context flows and update rates. Hope is a
proof-of-concept self-modifying recurrent architecture with a continuum memory
system. The authors report gains in language modeling, knowledge incorporation,
continual learning, and long-context tasks. The paper itself calls the results
promising. It does not establish safe, unrestricted, online self-modification.

The official Astra API documents reviewed below expose none of the
parameter-update controls that TTT, Titans, Miras, or Hope require. A future
compatible implementation can enter Loop Engine through an exact model route,
capability record, and evaluator. The semantic Loop contract stays the same
while the model realization changes.

## The OpenAI and GPT-6 Astra boundary

Only official OpenAI documentation supports this section.

The official [GPT-6 Astra model page](https://developers.openai.com/api/docs/models/gpt-6-astra)
documents a 1,050,000-token context window, 128,000 maximum output, reasoning
efforts, supported endpoints, tools, and prices. The official documents
reviewed on 2026-09-04 do not disclose a recurrent neural architecture for
GPT-6 Astra. This is an observation about public documentation, not evidence
about undisclosed implementation details.

The documented continuity features live at the API or harness layer:

| Official feature | What persists or changes | Correct interpretation |
|---|---|---|
| [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) | Response items linked by a conversation or `previous_response_id` | Server-managed or caller-managed request history |
| [Persisted reasoning](https://developers.openai.com/api/docs/guides/reasoning#preserve-reasoning-across-calls) | Opaque compatible reasoning items can enter later calls | Reasoning continuity, not exposed reasoning text or model-weight learning |
| [Compaction](https://developers.openai.com/api/docs/guides/compaction) | Retained items and an opaque compaction item carry forward prior state and reasoning so older prefixes can be dropped | Context compression at the API layer |
| [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) | Matching prompt prefixes receive cache treatment | Provider compute and billing optimization, not semantic memory |
| [Async tool calling](https://developers.openai.com/api/docs/guides/async-tool-calling) | The model continues while the application runs a tool | Execution concurrency managed by the application |
| [Mid-turn steering](https://developers.openai.com/api/docs/guides/steering) | A user update queues a continuation on the same WebSocket workflow | Runtime control; it does not undo effects or cancel tools already started |
| [Build skills](https://learn.chatgpt.com/docs/build-skills) | Instructions and optional resources load progressively | Reusable instruction packaging |

The Responses reasoning guide says persisted reasoning remains opaque and can
be reused only when compatible response items are available. The conversation
state guide says prior input tokens in a `previous_response_id` chain are still
billed as input. The compaction guide says the compacted item is not intended
for human interpretation. The prompt-caching guide asks developers to measure
cached tokens, cache-write tokens, latency, and realized cost. None of these
features alone proves that a model updates recurrent hidden state across API
requests.

Async tools and steering are useful for PILOT-like supervision experiments.
They are not complete supervision. Loop Engine still needs exact correlation,
effect authority, cancellation semantics, state revision checks, and Run
History before a steering message can support a recovery claim.

The current text-only Astra adapter passes 21 of 21 injected offline checks.
The route-policy prototype passes 38 of 38 offline checks, but a source-visible
hard gate prevents it from constructing an executable route. The policy keeps
only global, Standard, text-only planning in scope and rejects other locality
and service-tier workflows. Issued one-use spending authority, trusted-clock
availability, exact adapter and credential binding, invocation-budget
enforcement, and per-call reasoning-effort correlation remain unimplemented.
No live OpenAI call was made.

## Information-theory model for execution state

Let `H_t` be the full history available before decision `t`. Let `S_t` be a
state projection made from that history, and let `Y_t` contain future facts
that matter to the decision, such as the valid next action, the next
observation distribution, verifier result, or final task contribution.

### Sufficient statistics

An exact sufficient state satisfies the conditional-independence relation
`Y_t` independent of `H_t` given `S_t`:

```text
p(Y_t | H_t, S_t) = p(Y_t | S_t)
```

When `S_t` is a deterministic function of `H_t`, this reduces to
`p(Y_t | H_t) = p(Y_t | S_t)`. The state then retains all history information
needed to predict the selected future variable. This definition depends on
`Y_t`. A state sufficient for choosing a shell command may be insufficient for
explaining why that command was chosen. Without a specified future variable
and task distribution, no smaller sufficient statistic is guaranteed. Full
history is a safe information upper bound, although often an impractical one.

SKILL.state assumes its schema is sufficient for future execution. Loop Engine
should treat sufficiency as a tested hypothesis per task region, response
contract, and verifier, never as a property inferred from schema validity.

### Information bottleneck and rate-distortion

The [information bottleneck method](https://arxiv.org/abs/physics/0004057)
asks for a compact representation of one variable that preserves information
about another. Applied here, a state compiler seeks low `I(H_t; S_t)` while
retaining high `I(S_t; Y_t)`. A rate-distortion form asks for the smallest
state rate that keeps expected decision loss below a declared bound.

```text
minimize   I(H_t; S_t)
subject to E[decision_loss(H_t, S_t)] <= D
```

`D` must be task-specific. It can include wrong actions, missed blockers,
false completion, verification failures, recovery work, cost, and latency.
Reducing tokens while increasing false acceptance is a bad point on the
rate-distortion curve.

If `S_t` is computed only from `H_t`, the data-processing inequality gives
`I(S_t; Y_t) <= I(H_t; Y_t)`. Compression cannot create predictive
information that was absent from its source. A retrieved artifact, tool
observation, or external memory can add information, but its provenance then
belongs in the state transition. The conditional quantity
`I(Y_t; H_t | S_t)` is residual predictive information in history after the
state is known. Translating it into task loss requires a declared policy and
loss function. Early Loop Engine experiments should measure paired verifier
loss directly, not claim a reliable mutual-information estimate from a small
run set.

### Causal states and predictive information

Computational mechanics groups two histories into the same causal state when
they imply the same probability distribution over futures. Shalizi and
Crutchfield show that this construction is a minimal sufficient predictive
representation in their setting. See
[Computational Mechanics: Pattern and Prediction, Structure and Simplicity](https://arxiv.org/abs/cond-mat/9907176).

[Predictive information](https://arxiv.org/abs/cond-mat/9902341) measures mutual
information between past and future. For Loop Engine, these ideas suggest a
practical test: two histories may share a state fingerprint only when their
future verifier and action distributions remain equivalent within measured
tolerance. Text similarity is candidate evidence, not predictive equivalence.

### Three different forms of surprise

Shannon surprisal for an observation is:

```text
surprisal(o_t) = -log2 p(o_t | S_t)
```

It measures how unlikely the observation was under a declared predictive
distribution. It does not measure belief change.

Bayesian surprise is the divergence between posterior and prior beliefs after
an observation. In this sequential notation it is
`KL(p(theta | S_t, o_t) || p(theta | S_t))`. It can be high when an observation
changes a belief even if raw event rarity is not high. See Itti and Baldi's
[Bayesian Surprise Attracts Human Attention](https://papers.neurips.cc/paper/2822-bayesian-surprise-attracts-human-attention.pdf).

Titans gradient surprise is different again. It uses the gradient of the
associative memory loss with respect to the memory parameters, with momentum
and learned decay. Its magnitude depends on the chosen model, loss,
parameterization, and scale. Calling any anomaly score "surprise" does not make
these quantities interchangeable.

Loop Engine can use each as a signal:

- Shannon surprisal can flag an observation that the current transition model
  assigned low probability.
- Bayesian surprise can trigger belief revision or deeper evidence retrieval.
- Gradient surprise can govern writes inside a qualified neural-memory model.

None can grant permission, verify an effect, or commit trusted state.

### State entropy and decision-relevant loss

State entropy `H(S_t)` is defined only when an empirical or modeled
distribution over states exists. Serialized token count, number of populated
fields, compressed bytes, and schema width are useful size measures. They are
not Shannon entropy.

A directly measurable loss is more useful early in development:

```text
decision_relevant_loss =
    loss(action selected from S_t, observed outcome)
  - loss(action selected from H_t, observed outcome)
```

Estimate it with paired branches from the same frozen task and environment
state. Record local verification, information gain, later invalidation,
downstream use, task contribution, tokens, cost, and latency. Do not infer this
loss from a model's confidence.

### Algorithmic-complexity approximations

Kolmogorov complexity is not computable in general. Description length,
compressed byte length, normalized compression distance, and grammar size are
explicit approximations. An encoded model can also supply a description length
only when parameter precision, encoding, and decoder are stated. Cilibrasi and Vitanyi's
[Clustering by Compression](https://arxiv.org/abs/cs/0312044) explains how
real compressors approximate an uncomputable information distance for string
objects.

A shorter state is not automatically simpler in the useful sense. A compact
opaque summary can require more decoder knowledge and lose a rare identifier.
Report the compressor, version, dictionary, and reconstruction or decision
loss whenever a compression proxy enters an experiment.

## Mapping into current Loop Engine authority

The repository already has most of the control boundaries required for a safe
state-centric experiment. It now also has an offline passive context candidate
that composes an admitted skill, an exact state schema, trusted state, a latest
observation, selected history material, and an execution binding. That
candidate is intentionally absent from the product prompt renderer.

| Research concept | Current Loop Engine authority | Current use or proposed fit |
|---|---|---|
| Immutable procedure | [`SkillManifest` and `SkillAdmissionRecord`](../../src/loop_engine/core/skill_registry.py) | Standard-compatible discovery, bounded startup cards, and a digest-bound admission record that names an external reviewer |
| Passive state context candidate | [`skill_state_context.py`](../../src/loop_engine/core/skill_state_context.py) | Offline schema, scope, privacy, byte-budget, and state-sufficiency checks; not rendered or executed by the product |
| Current run notes | [`RunNoteBoard`](../../src/loop_engine/core/runtime_memory.py) | Run-scoped Runtime Memory; not yet a typed execution-state snapshot |
| Candidate state update | [`ProposedStateDelta`](../../src/loop_engine/core/semantic_runtime_records.py) | Exact base state, writes, effects, evidence, and idempotency |
| Independent state verification | [`SemanticVerificationRecord`](../../src/loop_engine/core/semantic_runtime_records.py) | Candidate checks before trusted-state admission |
| Trusted state commit | [`CatalogTrustedSemanticState`](../../src/loop_engine/core/semantic_state.py) | Compare-and-swap commit through semantic runtime authority |
| Immutable trajectory | [`RunHistory`](../../src/loop_engine/core/run_history.py) | Audit, replay, lineage, and evidence source |
| Exact large material | [`ContextArtifactManager`](../../src/loop_engine/core/context_artifacts.py) | Digest-addressed raw artifacts, policy-based offloading, and separate compaction; selected and authorized hydration remains integration work |
| Prior skill or episode search | [`intelligence_portfolio.py`](../../src/loop_engine/core/intelligence_portfolio.py) | Candidate search across existing intelligence layers |
| Stage identity and outcomes | [`stage_evidence_records.py`](../../src/loop_engine/core/stage_evidence_records.py) | Occurrence, retrieval, exposure, decision, and trial records |
| Model capability and availability | [`model_routing_records.py`](../../src/loop_engine/core/model_routing_records.py) | Passive capability, suitability, demand, and availability records |
| Parallel or recursive work | [`delegation_runtime.py`](../../src/loop_engine/loop/delegation_runtime.py) | Bounded Spawned Loops with typed inputs and outputs |
| Executable topology | [`LoopGraphDefinition`](../../src/loop_engine/code_nodes/solution_graph.py) | One versioned graph authority with typed edges |

The proposed design composes the contracts in this table. The current passive
compiler directly composes `LoadedSkill`, `TrustedStateSnapshot`, and
`LLMContextBlock`; the other identities are validated references. It adds no
parallel store, event vocabulary, skill registry, executor, graph, or runtime
class. A later integration must resolve those references through the existing
Run History, artifact, graph, routing, and authorization services. It must also
connect through the current context-manifest and prompt-assembly boundaries
without flattening mixed trust and privacy classes.

## Current implementation after review

Two offline foundations were implemented during this review.

The skill registry now follows the standard Agent Skills frontmatter for new
manifests, moves Loop Engine version, title, and tag values into namespaced
metadata, recognizes exactly one case-insensitive `SKILL.md`, and labels known
legacy frontmatter rather than calling it standard. It produces byte-bounded
startup cards that omit instructions, file paths, and requested tools from the
returned projection. Discovery still reads the skill files to establish exact
digests. Full instructions require selection, digest verification, and a
matching admission record for task use. The record names an external reviewer;
the registry does not perform or prove that review. Its current suite passes 21
of 21 checks.

The passive state-context candidate deep-seals observation and selected-history
JSON, validates trusted state against a self-contained exact JSON Schema,
binds task, run, branch, graph, Loop, tenant, state revision, observation,
privacy, destination, profile, and materialization references, and preserves
trust and privacy for each part. State-sufficiency flags cannot compile without
selected evidence-backed history material. A fixed-shape 200-step fixture
stayed between 3,759 and 3,767 serialized bytes. This is a narrow boundedness
test, not a general constant-space result. Its current suite passes 17 of 17
checks.

Both suites are offline. The state candidate does not enter the product prompt,
read Run History, update state, call a model, invoke a tool, or grant authority.
Its history and materialization references still need resolution against the
existing authoritative services during product integration. No current result
shows that compact state preserves task quality or reduces realized cost.

## Proposed state-centric skill design

Keep the skill body immutable during a run. Store evolving execution state in
a separate, typed, run-scoped sidecar. Present the latest verified snapshot to
the model, while Run History retains every transition and observation.

```text
State-centric skill execution
├── Immutable skill package
│   ├── SKILL.md instructions and metadata
│   ├── optional state-schema artifact
│   ├── exact version and manifest digest
│   └── digest-bound external-review admission record
├── Run-scoped execution binding
│   ├── run, branch, graph, and Loop activation identity
│   ├── exact skill and schema references
│   ├── authority and budget references
│   └── source state revision
├── Immutable state snapshot
│   ├── trusted values and evidence references
│   ├── speculative values and uncertainty
│   ├── active goals, blockers, and frontier
│   ├── selected history and artifact references
│   └── state digest and revision
├── Candidate transition
│   ├── latest observation reference
│   ├── proposed patch and action
│   ├── expected observation
│   └── invalidation and rollback conditions
└── Admission
    ├── structural validation
    ├── semantic and evidence verification
    ├── authority and effect check
    ├── compare-and-swap commit
    └── Run History event
```

The logical state changes. The stored records do not. One transition should
produce a new snapshot with a new revision and digest. This gives the next
Loop a small current view while preserving concurrency checks and exact replay.

### Proposed sidecar snapshot

A future `skill_execution_state/v1` record should contain or reference:

- exact skill ID, version, manifest digest, admission record, and state schema;
- run, branch, graph version, Loop activation, and semantic-call identity;
- source state ID, revision, and digest;
- trusted values with evidence and freshness;
- speculative values with uncertainty and explicit invalidation conditions;
- active goals, unresolved questions, blockers, and completion criteria;
- selected model, tool, context, artifact, and prior-state references;
- permissions, effects, privacy, retention, and budget references;
- previous snapshot and transition references;
- current state size, token size, compressed size, and optional entropy-estimate
  method;
- schema extension requests and a free-form escape reference for facts that do
  not yet fit.

Do not place raw credentials, private hidden reasoning, a copied full
transcript, or executable authority in the sidecar. Preserve concise decision
summaries, alternatives, actions, observations, verification, and exact
artifact references in Run History.

### Proposed transition record

A future `skill_state_transition/v1` should bind:

```text
base snapshot and revision
latest observation and evidence
candidate patch
candidate action
schema changes requested
structural admission
semantic verifier decision
effect authorization
committed snapshot or refusal
observed state and decision loss
```

When an observation may matter later but does not belong in current state,
retain a small evidence reference and retrieval key. A Practitioner can request
progressive hydration from Run History or an artifact. This is the escape path
for the second SKILL.state limitation, where relevance becomes visible late.

### Skill learning across runs

Do not edit an admitted `SKILL.md` in place. A self-improvement Practitioner
task may produce one of four candidates:

1. A revised skill version.
2. A revised state schema or field bundle.
3. A revised retrieval or invocation policy.
4. A revised verifier or state-update realization.

Each candidate keeps source trajectories, negative examples, attribution
confidence, and held-out results. Another process reviews and promotes it. A
popular path, embedding cluster, high model confidence, or successful source
run cannot approve the change.

## Prioritized falsifiable experiments

Each experiment must freeze the task population, model route, provider state,
tool versions, budgets, evaluator, and starting environment. Count state
construction, verification, repair, retrieval, cache writes, and failed calls.

### E0. State-transition safety

Hypothesis: immutable snapshots, typed deltas, evidence checks, and
compare-and-swap commits reject stale, malformed, unsupported, or
authority-expanding patches before trusted state changes.

Use deterministic fixtures for omitted keys, null deletion, type coercion,
duplicate updates, stale revisions, concurrent writes, forged evidence,
permission broadening, and replay. The experiment fails if any invalid patch
commits or an accepted transition lacks an exact Run History record.

### E1. Fixed-schema state against transcript history

Hypothesis: on a bounded procedural task with a known schema, state-only
context matches or improves verified task success while lowering total input,
output, cache-write, and repair cost.

Run paired branches from the same frozen state:

```text
Arm A: immutable procedure + append-only history + latest observation
Arm B: immutable procedure + verified current state + latest observation
Arm C: immutable procedure + verified state + selected evidence references
```

Measure accepted success, false acceptance, prompt and output tokens, actual
cached and cache-write tokens, realized cost, latency, state-patch failures,
and recovery work. Reject the hypothesis if the state arm exceeds the declared
quality-loss tolerance or if total cost per verified completion does not
improve. A token-count reduction alone is insufficient.

### E2. Late relevance and state sufficiency

Hypothesis: a compact state plus evidence-reference retrieval preserves facts
whose relevance appears late better than a state-only arm and at lower cost
than full-history replay.

Inject delayed dependencies, corrected facts, contradictory observations,
rare identifiers, and requests where provenance is the output. Compare
state-only, state plus retrieval, and full history. Measure retrieval recall,
wrong-state persistence, decision-relevant loss, and explanation completeness.
The hypothesis fails if selected retrieval cannot recover the needed evidence
or repeatedly hydrates most of the history.

### E3. Dynamic schema discovery on unseen task families

Hypothesis: a minimal universal envelope with run-scoped schema extension
retains open-world task quality better than fixed domain schemas without
unbounded field growth.

Use source, task-family, output-contract, and tool-path holdouts. Compare a
fixed schema, an LLM-proposed run schema, composable field bundles, and a
minimal envelope with artifact references. Track schema churn, unknown-field
use, state size by horizon, invalid patches, quality, and transfer. The
bounded-state claim fails if median or tail state size grows materially with
horizon after controlling for task complexity.

### E4. Outcome-linked strategy memory

Hypothesis: retrieved prior strategies improve a later Loop only when the
owning model can use, modify, combine, ignore, or reject them and stage-local
outcomes support the retrieval.

Run shadow, advisory, and paired fresh controls. Record exact exposure and the
model's disposition. Include negative-transfer and late-invalidation cases.
The hypothesis fails if advisory retrieval raises false acceptance, hurts a
holdout population, or receives only run-level credit.

### E5. Procedural-family skill consolidation

Hypothesis: a family-level procedure plus task-local regeneration transfers
better and uses less context than a flat pool of task-specific skills.

Compare no skill, nearest task skill, flat task pool, family procedure, and
family procedure plus local regeneration. Hold out complete task clusters and
solution lineages. The hypothesis fails if family skills lose rare causal
conditions, create negative transfer, or pass only when evaluated on their
source family.

### E6. Live supervision and steering

Hypothesis: a separate supervisor can reduce stalls and recover the active run
without increasing harmful interventions or duplicating work.

Start with a shadow supervisor that predicts steer, cancel, wait, or no-action
decisions. Then run paired advisory trials. An Astra trial must use the
Responses WebSocket steering contract and exact effect cancellation semantics.
Measure precision and recall of interventions, recovered verified tasks,
wasted tokens, already-committed effects, and supervisor cost. The hypothesis
fails if false interventions erase the quality or cost gain.

### E7. Recursive context processing

Hypothesis: bounded RLM-style programmatic inspection solves selected
long-context tasks more cheaply than full hydration or provider compaction.

Compare the current context compiler, provider compaction, a non-recursive
external-context program, and bounded recursive calls. Use the same model
portfolio and total call budget. Record branch width, depth, inspected bytes,
missed evidence, generated code failures, total cost, and task result. The
hypothesis fails if recursion wins only by spending more or by seeing evidence
withheld from a control.

### E8. Coordination topology selection

Hypothesis: task-state features can select between coherent single-Loop work,
parallel Spawned Loops, a centralized verifier, and an ensemble better than one
fixed topology.

Test independent, sequential, tool-heavy, and join-sensitive tasks. Keep model
and tool budgets equal. Use task-family holdouts and report the selector's
calibration, not only top-one accuracy. The hypothesis fails if the learned
selector does not beat a simple fixed baseline or if communication overhead
removes its quality gain.

### E9. Cheap state updater and verifier

Hypothesis: a small structured-output model can propose state patches for a
narrow region while a deterministic gate and independent verifier keep false
commits within a declared bound.

Train on admitted state transitions with local outcomes, including overwrite,
type, formatting, stale-state, and negative-transfer examples. Run in shadow
with out-of-distribution detection and abstention. Promote only a narrow region
after untouched holdouts. The hypothesis fails on excess false commits,
miscalibration, unexplained coverage growth, or failure to abstain outside its
qualified region.

Neural recurrent model comparisons come later. A TTT, Mamba, Titans-like, or
RecurrentGemma route should satisfy the same semantic contract and evaluator as
an attention model. It does not receive architectural authority because its
hidden state is recurrent.

## Recommended implementation order

1. Define passive state snapshot and state-transition candidates by composing
   existing semantic-state, skill, artifact, and Run History identities.
2. Prove stale-state, evidence, authority, rollback, and concurrency behavior
   with deterministic tests.
3. Instrument state size, selected-history size, patch failures, cache details,
   decision-relevant loss, and later invalidation.
4. Run E1 on one frozen bounded task population with a real authorized model.
5. Run E2 before discarding history from any open-world product path.
6. Add dynamic schema extension and progressive evidence hydration.
7. Expose learned strategy and skill candidates in shadow, then advisory, then
   paired trials.
8. Test supervisor steering, recursion, and topology selection under equal
   budgets.
9. Distill a small state updater only after stage outcomes and holdouts are
   reliable.

This order tests the hardest assumption first: whether the proposed state
retains the information needed for the following decision. Storage scale and
small-model speed do not repair a lossy state definition.

## Primary source register

The versions below were checked on 2026-09-04. Paper results remain
author-reported and unreproduced in this repository.

| Source | Version or date used | Scope in this review |
|---|---|---|
| [SKILL.state](https://arxiv.org/abs/2608.26263v3) | v3, 2026-09-02 | Explicit execution state and bounded-context claim |
| [ReasoningBank](https://arxiv.org/abs/2509.25140v2) | v2, 2026-03-16 | Outcome-derived reasoning memory |
| [Titans](https://arxiv.org/abs/2501.00663) | v1, 2024-12-31 | Neural long-term memory and gradient surprise |
| [Miras](https://arxiv.org/abs/2504.13173) | v1, 2025-04-17 | Memory architecture design dimensions |
| [Nested Learning and Hope](https://arxiv.org/abs/2512.24695) | v1, 2025-12-31 | Nested optimization and continuum memory |
| [Scaling Agent Systems](https://arxiv.org/abs/2512.08296v3) | v3, 2026-04-08 | Coordination scaling and topology selection |
| [Recursive Language Models](https://arxiv.org/abs/2512.24601v3) | v3, 2026-05-11 | Recursive external-context inference |
| [Prime Agent](https://arxiv.org/abs/2608.23552) | v1, 2026-08-24 | Persistent REPL and recursive harness |
| [Recuris](https://arxiv.org/abs/2608.24876) | v1, 2026-08-25 | Verified working memory and local evolution |
| [PILOT](https://arxiv.org/abs/2608.26530) | v1, 2026-08-27 | Live supervisor steering and evolution |
| [SkillGLoW](https://arxiv.org/abs/2609.02217) | v1, 2026-09-02 | Procedural-family consolidation |
| [TTT](https://arxiv.org/abs/2407.04620v4) | v4, 2025-08-31 | Model-valued recurrent hidden state |
| [Mamba](https://arxiv.org/abs/2312.00752v2) | v2, 2024-05-31 | Selective state-space model |
| [Mamba-2](https://arxiv.org/abs/2405.21060) | v1, 2024-05-31 | State-space duality and revised recurrent layer |
| [Griffin](https://arxiv.org/abs/2402.19427) | v1, 2024-02-29 | Gated recurrence with local attention |
| [RecurrentGemma](https://arxiv.org/abs/2404.07839v2) | v2, 2024-08-28 | Open Griffin-based model family |
| [Information Bottleneck](https://arxiv.org/abs/physics/0004057) | arXiv record checked 2026-09-04 | Relevant-information compression |
| [Computational Mechanics](https://arxiv.org/abs/cond-mat/9907176) | journal and arXiv record | Minimal predictive causal states |
| [Predictive Information](https://arxiv.org/abs/cond-mat/9902341) | arXiv record checked 2026-09-04 | Mutual information between past and future |
| [Bayesian Surprise](https://papers.neurips.cc/paper/2822-bayesian-surprise-attracts-human-attention.pdf) | NIPS 2005 paper | Belief-update surprise |
| [Clustering by Compression](https://arxiv.org/abs/cs/0312044) | arXiv record checked 2026-09-04 | Compression proxy for uncomputable complexity |
| [Agent Skills specification](https://agentskills.io/specification) | checked 2026-09-04 | Skill manifest fields and progressive-disclosure guidance |

Official OpenAI sources checked on 2026-09-04:

- [GPT-6 Astra model page](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Current GPT-6 Astra guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
- [Reasoning and persisted reasoning](https://developers.openai.com/api/docs/guides/reasoning)
- [Compaction](https://developers.openai.com/api/docs/guides/compaction)
- [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Async tool calling](https://developers.openai.com/api/docs/guides/async-tool-calling)
- [Mid-turn steering](https://developers.openai.com/api/docs/guides/steering)
- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Skills API guide](https://developers.openai.com/api/docs/guides/tools-skills)

## Limits of this review

Most 2026 agent papers above are recent preprints. Several are v1 reports.
Their code, task populations, models, inference budgets, and evaluators differ,
so their percentages are not head-to-head comparisons. No result supports a
universal policy.

The information-theory section defines measurement targets. It does not claim
that mutual information, causal states, or entropy can already be estimated
reliably from Loop Engine's current run volume. Early experiments should use
direct task loss, verifier results, tokens, bytes, latency, and cost.

The absence of a disclosed Astra neural architecture in the official sources
reviewed is not evidence about OpenAI's private design. It is a boundary on
what Loop Engine can claim. API conversation state is runtime state until an
official source establishes something more.
