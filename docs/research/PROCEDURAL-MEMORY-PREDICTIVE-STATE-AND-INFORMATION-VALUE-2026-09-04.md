# Procedural memory, predictive state, and information value

Review date: 2026-09-04

This note defines a narrow research direction for Loop Engine. It asks whether
verified Loop history can support reusable procedures. Reuse must remain a
candidate until scope, control behavior, negative transfer, and a fresh
comparison have been tested. Information theory can define useful measurements.
It cannot turn similarity, compression, or model confidence into proof.

In this note, **AI muscle memory** means:

> Evidence-gated procedural automaticity. Repeated and verified Loop behavior
> may be represented as reusable guidance or a cheaper implementation while
> preserving the semantic contract, verification, and an exact escape to
> general reasoning.

This is an engineering term. It is not a claim that Loop Engine has a human
brain, consciousness, unconscious thought, or human procedural memory.

All numerical paper results below are author-reported and were not reproduced
in Loop Engine. The recent systems use different models, tasks, budgets, and
evaluators. Their results are design evidence, not a head-to-head comparison.

## Architecture boundary

The research does not create a new runtime or a `Node` class. The conceptual
phrase "Loop Node" still refers to an executable vertex whose runtime type is
`Loop`.

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

Role profiles remain classifications of the same runtime:

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

Procedures, memories, fingerprints, probability distributions, information
measurements, indexes, embeddings, models, policies, and assessment results are
passive records or artifacts. A classified Loop owns any work that builds,
retrieves, assesses, executes, changes, or promotes them. A retrieved record
cannot grant authority.

## Memory layers that must stay separate

"Memory" can refer to several mechanisms with different identities and update
rules. Combining them into one store would hide important trust boundaries.

```text
Loop-owned memory and procedural support
├── Procedure specification
│   └── immutable instructions, contract, version, and admission
├── Execution state
│   └── current trusted and speculative state for one activation or branch
├── Episodic memory
│   └── exact actions, observations, verification, and outcomes in Run History
├── Semantic memory
│   └── admitted facts, claims, relationships, and provenance
├── Procedural memory
│   └── candidate reusable transition, episode, or subgraph guidance
├── Compiled realization
│   └── qualified code, tool, small model, rule, or deterministic policy
└── Model-internal state
    └── provider session, recurrent activations, or parameter updates
```

Model-internal state is a property of a selected model route. It is not Run
History and does not survive a reset unless the provider contract says it does.
A `SKILL.md` file is a versioned procedure specification. It should not be
continually rewritten as execution state. Long-horizon state belongs in typed
records bound to the active Loop and source-state revision.

The distinction supports two learning rates:

1. Fast episodic capture writes exact, immutable events and artifacts as work
   happens. It retains failures, excluded attempts, and unknown outcomes.
2. Slow consolidation groups evidence, proposes abstractions, tests transfer,
   and submits a new candidate version for independent review.

This resembles the fast and slow learning separation in the
[complementary learning systems account](https://doi.org/10.1037/0033-295X.102.3.419).
The analogy suggests an experiment. It does not establish a biological
implementation or human equivalence.

## Procedural automaticity as a controlled option

The options framework represents a temporally extended action through an
initiation set, an internal policy, and a termination rule. See
[Between MDPs and Semi-MDPs](https://doi.org/10.1016/S0004-3702(99)00052-1).
A Loop Engine procedural candidate can use a similar contract:

```text
Procedural candidate
├── Initiation contract
│   └── when the procedure may be considered
├── Typed internal policy
│   └── response program, transition sequence, subgraph, tool, code, or model
├── Termination contract
│   └── what verified condition ends it
├── Interruption and checkpoint contract
├── Outcome and cost evidence
├── Applicability and exclusion region
└── Deliberative fallback
    └── return to an LLM-led Practitioner Loop
```

The candidate needs seven independent behavioral probe kinds:

| Probe | Required observation |
|---|---|
| Initiation | It starts inside the declared region and abstains outside it. |
| Termination | It stops at the exact verified condition. |
| Interruption | Cancellation or pause preserves valid state and receipts. |
| Outcome devaluation | A changed goal, reward, or cost can make the old procedure inapplicable. |
| Negative transfer | A surface-similar but incompatible case is refused or escalated. |
| Fresh control | The procedure is compared with a branch that receives no derived assistance. |
| Deliberative fallback | Failure, uncertainty, or out-of-distribution input returns control to general reasoning. |

Outcome devaluation is important because frequently successful behavior can be
wrong after the objective changes. Research on model-based and model-free
control provides the conceptual warning that cached value and current planning
can disagree. See
[Uncertainty-based competition between prefrontal and dorsolateral striatal systems](https://doi.org/10.1038/nn1560).
Loop Engine should test the observable control behavior rather than assign a
psychological label to a model.

An offline assessment may report `candidate_support_pending_resolution` only
when all seven probes are valid and pass, positive and negative episodes are
present, a fresh-control record is present, and the assessor reference differs
from the producer reference. An infrastructure-invalid probe makes the set
incomplete. This is not support: procedure, scope, assessor identity, validity,
fresh packet contents, and fallback availability still need canonical
resolution. The assessment grants no permission and authorizes no promotion.

## Predictive state instead of transcript resemblance

Let `H_t` be the available history before a Loop decision, `S_t = f(H_t)` a
state projection, and `Y_t` a declared future target. `Y_t` might be the next
observation class, verifier result, valid continuation, or termination state.

An ideal sufficient state satisfies:

```text
Y_t is conditionally independent of H_t given S_t
I(Y_t; H_t | S_t) = 0
```

No finite Loop Engine campaign can prove that relation for an open task
population. High-dimensional mutual-information estimators would add more
assumptions than the current evidence supports. The practical test is held-out
predictive regret under the same interpreter, output contract, evaluator, and
task population:

```text
predictive_regret(S) =
    E[loss(predictor(S_t), Y_t)]
  - E[loss(predictor(H_t), Y_t)]
```

Use a proper scoring rule for predictive distributions and a declared
decision loss for actions. Report false acceptance and later invalidation
separately. Near-zero measured regret means only that this state projection
matched the full-history control on the tested population within measurement
uncertainty. It is not proof of sufficiency.

[Predictive state representations](https://proceedings.neurips.cc/paper_files/paper/2001/file/1e4d36177d71bbb3558e43af9577d70e-Paper.pdf)
represent controlled state through probabilities of future action-observation
tests. A PSR-inspired Loop fingerprint can therefore include predictions for:

- the next observation category after a proposed action;
- local mechanical and semantic verification;
- likely continuation and termination conditions;
- expected effects, cost, and latency;
- later downstream consumption and invalidation.

These predictions must name a model, population, horizon, evaluator, and
version. A vector with those fields is not a formal PSR unless its controlled
tests and update process satisfy the PSR definition.

The [successor representation](https://doi.org/10.1162/neco.1993.5.4.613)
suggests a second representation. For typed future features `phi`, a successor
fingerprint can estimate discounted future occupancy:

```text
successor_fingerprint(s, a) =
    E[sum from k=0 to horizon of gamma^k * phi(event_(t+k)) | s, a]
```

This can distinguish two stages that have similar text but lead to different
tools, verification, failures, or terminal states. It can also connect
different domains whose future transition patterns are similar. The successor
fingerprint remains a similarity projection. It is not occurrence identity,
contract compatibility, causal attribution, or authority. A divergence such
as Jensen-Shannon divergence is valid only after the compared values have been
defined as compatible probability distributions.

## Rate-distortion as a state experiment

Classical rate-distortion theory asks how much information a representation
needs to keep expected distortion below a limit. The
[information bottleneck](https://arxiv.org/abs/physics/0004057) selects a
compressed representation of history that preserves information about a
declared relevant future variable.

For Loop Engine, the engineering objective is:

```text
minimize   state rate, tokens, bytes, cost, and latency
subject to predictive and decision loss <= declared tolerance
           false acceptance <= absolute safety limit
```

The true rate can be expressed through `I(H; S)` only when a joint probability
model and estimator are defined. Early experiments should report direct
proxies such as serialized bytes, model-visible tokens, and compression ratio.
Those quantities are not Shannon entropy. Distortion should be a held-out
proper loss, verifier loss, or utility regret. It should not be a model's
self-reported confidence.

If `S` is derived only from `H`, the data-processing inequality requires:

```text
I(S; Y) <= I(H; Y)
```

A retrieved artifact or new tool observation can add predictive information,
but then it is another input with its own provenance. The measurement must not
credit the state compressor for information supplied by that input.

Small discrete plug-in estimates of entropy and mutual information can be
useful for offline diagnostics. They must declare the random variables,
population, selection rule, probability model, estimator, log base, holdout,
bias correction, and evaluator. Excluded infrastructure-invalid samples remain
visible. A plug-in estimate from observed counts does not support a
generalization or causal claim.

## Information gain is not decision value

Expected information gain for a proposed observation `O` can be written as:

```text
EIG(action) =
    E_O[KL(p(theta | O, action) || p(theta))]
```

It values expected belief change. Expected value of sample information asks
whether observing `O` improves the best available decision:

```text
EVSI(action) =
    E_O[max_decision E[utility(decision, theta) | O, action]]
  - max_decision E[utility(decision, theta)]
```

Acquisition cost should be subtracted when ranking actions. A question can have
high EIG and zero EVSI if it changes beliefs without changing the selected
decision. It can have high decision value even when a simple entropy reduction
score is modest. Howard's
[Information Value Theory](https://doi.org/10.1109/TSSC.1966.300074)
explains why outcome consequences must accompany probability.

Use EIG for a declared belief-refinement objective. Use net EVSI when an
explicit utility and decision boundary exist. Otherwise label the value as a
proxy and record its assumptions. Neither quantity grants permission to run an
experiment.

## Four signals that should not share one name

| Signal | Definition | Appropriate use |
|---|---|---|
| Shannon surprisal | `-log2 p(observation given state, action)` | Flag an event assigned low probability by a declared model. |
| Bayesian surprise | `KL(posterior, prior)` | Measure change between declared prior and posterior beliefs. |
| Prediction residual | Observed value minus a declared prediction | Diagnose model fit in the units of the target. |
| Gradient surprise | Gradient of a specified neural-memory loss with respect to its memory parameters | Control an update inside that exact trained memory mechanism. |

[Bayesian Surprise Attracts Human Attention](https://papers.neurips.cc/paper/2822-bayesian-surprise-attracts-human-attention.pdf)
defines belief-update surprise. [Titans](https://arxiv.org/abs/2501.00663)
uses a gradient-based signal to update a neural long-term memory. These are not
interchangeable. An anomaly score should not be called surprise unless its
probability model or loss is recorded. Any of these signals may trigger a
candidate retrieval, diagnosis, or reorientation Loop. None verifies an
effect or commits trusted state.

## Fingerprints and retrieval

Procedural reuse needs several identities and projections:

```text
One exact Loop activation
├── occurrence identity
├── semantic situation signature
├── input and output contract signature
├── state and observation signature
├── procedural-family signature
├── graph and transition signature
├── predictive-state fingerprint
├── successor fingerprint
├── execution and tool fingerprint
└── outcome signature
```

Exact occurrence identity must include task, branch, graph version, state
revision, and activation. Embeddings, n-grams, MinHash, SimHash, LSH buckets,
and learned classifiers are rebuildable retrieval projections. They cannot
replace that identity.

A retrieval tournament should generate candidates through independent
channels:

- exact and structured facets;
- input, output, authority, effect, privacy, and tool compatibility;
- lexical terms and word or character n-grams;
- sparse and dense retrieval;
- transition, subgraph, predictive, and successor similarity;
- historical outcomes, counterexamples, late invalidation, and freshness;
- LLM-proposed cross-domain analogy.

Each result should say why it matched, where it differs, how it performed,
what negative-transfer evidence exists, and that the prior is not proof. The
owning LLM may use, modify, combine, reject, retrieve deeper, or start fresh.
Fresh controls must exclude both direct memory and derived templates, context
plans, model recommendations, and cached branch output.

The safe procedural path is:

```text
Exact episode
  -> locally verified transition
  -> candidate lesson
  -> procedural-family fingerprint
  -> advisory retrieval with a fresh control
  -> cross-task negative-transfer evaluation
  -> shadow shortcut
  -> independently qualified realization
  -> monitored use with OOD, fallback, and late invalidation
```

Frequency and a strong historical path are reasons to inspect a candidate.
They are not reasons to execute it automatically.

## What recent systems show

The most useful result across the recent literature is conditionality. Memory
can improve repeated repair and reduce redundant search. It can also propagate
errors, narrow exploration, or adapt to the evaluation sequence.

| Work | Author-reported evidence | Limit for Loop Engine |
|---|---|---|
| [Recuris](https://arxiv.org/abs/2608.24876) | Verified working state, skill selection, checked state updates, and local regression-gated repair were evaluated across four benchmarks and ten models. The paper reports improvement in 35 of 37 completed model and benchmark pairs. | The matched-budget Terminal-Bench comparison adds 2.3 points with `p = 0.774`. Repair attribution is not causal attribution, and the recent v1 study does not establish a universal controller. |
| [SkillGLoW](https://arxiv.org/abs/2609.02217) | Task-local skills are consolidated into procedural families. The paper reports a mean 17.2 percentage-point hard-score gain across 12 runs and a three-model mean increase from 73.9 to 83.9 on 60 held-out ALFWorld tasks. | Its main commit gate uses the training stream. The held-out result covers one task family. De-instantiation can remove a condition that looked local but was causal. |
| [PILOT](https://arxiv.org/abs/2608.26530) | A supervisor steers or aborts workers and distills procedures and failures. The paper reports best observed Terminal-Bench pass-rate gains of 14.6 and 12.4 points for two backbones, with lower output-token counts over its iteration windows. | Continual evaluation repeats the same 89 tasks. The worker and supervisor share a backbone. Repeated exposure, intervention cost, and harmful steering need separate controls. |
| [APEx](https://arxiv.org/abs/2609.02253) | Instance trajectories and category procedures guide test-time policy adaptation. The paper reports results on seven deep-research benchmarks, including a 14.7-point margin over a named GPT-5.4 result and 3.0 points over its strongest memory baseline. | Test-time training is transductive and sequence order matters. The comparison does not establish a matched cost or trajectory budget against the named model. It is not a ready product policy. |
| [CONTRAMEM](https://arxiv.org/abs/2608.22533) | Contrasts same-task trajectories from several models to build function and skill cards. The paper reports a three-model held-out GAIA2/ARE mean increase from 26.2 to 55.3 percent and transfer to Qwen3.7 Plus from 18.5 to 35.5 percent. | "Training-free" means no model-parameter training. Construction still uses 600 runs. The method does not by itself solve temporal initiation, interruption, devaluation, or fallback control. |
| [Demystify the Role of Memory in Machine Learning Engineering Agents](https://aclanthology.org/2026.findings-acl.525/) | On 22 MLE-Bench-lite tasks, memory helps the sequential repair agent but constrains the tree-search agent. For the tree agent, the paper reports reductions of 10.7 points on Above-Median and 11.5 points on Any-Medal; 11 tasks improve and 10 decline. | A memory policy should depend on graph topology and task state. An average benefit would hide the exploration loss and task-level reversals. |
| [Fine-Mem](https://aclanthology.org/2026.acl-long.900/) | Chunk-level question rewards and evidence-anchored attribution give local supervision for memory operations on Memalpha and MemoryAgentBench. | Chunk-local and evidence-linked credit is stronger than a final-task label, but it is still evaluator-dependent and does not establish causal stage contribution in Loop Engine. |
| [Experience-Following Behavior](https://aclanthology.org/2026.acl-long.27/) | Similar retrieved inputs often lead to similar outputs. The paper studies resulting error propagation and misaligned experience replay, and uses later evaluations as memory-quality labels. | Embedding similarity can copy the wrong behavior. Future outcomes can update evidence, but they do not retroactively make the original retrieval decision valid. |
| [Memp](https://aclanthology.org/2026.findings-acl.866/) | Past trajectories are distilled into detailed instructions and higher-level scripts, with explicit build, retrieval, and update strategies on TravelPlanner and ALFWorld. | The evidence concerns analogous tasks in two environments. A lifecycle design does not prove cross-domain applicability, safe authority, or correct initiation and termination. |

These studies support candidate procedure records, local credit, contrastive
examples, topology-aware retrieval, and regression gates. They also support a
default escape to fresh LLM reasoning when applicability is uncertain.

## Exact first experiment

The highest-information next experiment is a frozen, four-arm predictive-state
comparison. It tests whether structured state preserves the information needed
for the next bounded decision before any history is removed from a product
path.

### Population

Build 120 frozen stage situations from exact Run History and artifacts:

- 40 data and schema orientation situations;
- 40 failure-diagnosis situations;
- 40 next-experiment selection situations.

Use source, task-family, and artifact-lineage holdouts. Each situation must have
an intact causal history, a declared next-decision contract, an observed next
outcome, and an evaluator that was frozen before treatment rendering. Exclude
only typed infrastructure-invalid cases, retain them in the report, and do not
inspect their outcomes when deciding exclusion.

### Four paired arms

For every situation, render all four conditions from the same source-state
revision:

1. `FULL_HISTORY`: immutable task core plus the complete eligible causal
   history.
2. `RECENT_WINDOW`: the task core plus a fixed recent event window.
3. `STRUCTURED_STATE`: the task core plus a typed state projection and latest
   observation.
4. `REHYDRATED_STATE`: the same typed state plus evidence selected through the
   declared progressive-hydration policy.

Freeze the model and revision, provider route, system and developer resources,
response contract, tools, authority, generation settings, evaluator, outcome
labels, and source artifacts. Randomize arm order from a preregistered seed.
Use separate stateless requests so one arm cannot enter another arm's session
history. Record complete model-visible packet and provider-request digests.

### Required response

Each arm returns:

- a ranked next action from the same typed candidate set, including abstention;
- a probability distribution over declared next-observation categories;
- expected local verifier result;
- expected termination or continuation state;
- a concise decision summary and evidence references.

Do not request or store private chain of thought.

### Measures

Use cross-entropy and Brier score for the predictive distributions. Use a
predeclared decision-loss matrix for the selected action. Report false
acceptance, abstention, verifier agreement, later invalidation, serialized
bytes, model-visible tokens, latency, and provider-reported cost. Missing cost
or usage stays unknown.

For each compact arm, report paired regret against `FULL_HISTORY` and a
compression/loss proxy operating point where size is explicitly labeled as
bytes or tokens and loss is held-out decision or predictive loss. Also report
the discrete empirical plug-in information estimates as diagnostics, with
their estimator and bias limitations. Do not select a winner using the same
situations used to set the tolerance.

### Decision rule

Before execution, declare an absolute false-acceptance ceiling and a maximum
regret tolerance for each task region. A compact state becomes a candidate for
an advisory product trial only if it stays within both limits on every held-out
region, its uncertainty interval is reported, infrastructure validity is
complete, and no fresh-arm contamination is found. Cost savings cannot offset
a breach of the false-acceptance ceiling.

This experiment can reject a lossy state policy or justify a later advisory
trial. It cannot prove predictive sufficiency, causal benefit, or universal
transfer.

## Current implementation maturity

Current maturity for this work is **IMPLEMENTED_OFFLINE**.

The repository contains passive candidate contracts for:

- declared information measurements with population, target, estimator,
  holdout, evaluator, exclusion policy, minimum valid coverage, probability
  model, and digest identities;
- typed infrastructure-validity records bound to the measured source material;
- categorical entropy, surprisal, Bayesian-surprise calculations, and small discrete
  empirical predictive-information diagnostics;
- paired full-history and state-policy trials with direct quality and
  compression measurements, an absolute treatment-loss limit, and a distinct
  relative non-inferiority limit;
- procedural-control probes for initiation, termination, interruption,
  outcome devaluation, negative transfer, fresh control, and deliberative
  fallback.
- an offline public-solve assistance fixture where digest-bound hydrated prior
  material reaches the provider adapter, while the fresh arm receives none;
- direct lineage from one action-producing semantic stage through its selected
  action, execution result, and downstream verification. Other stage outcomes
  remain unknown.

The relevant implementation is in
[`information_evidence_contracts.py`](../../src/loop_engine/core/information_evidence_contracts.py),
[`information_update_evidence.py`](../../src/loop_engine/core/information_update_evidence.py),
[`information_theory_evidence.py`](../../src/loop_engine/core/information_theory_evidence.py),
[`state_policy_evidence.py`](../../src/loop_engine/core/state_policy_evidence.py),
and
[`control_assessment.py`](../../src/loop_engine/memory/procedural/control_assessment.py).
The assistance slice also uses
[`stage_assistance_material.py`](../../src/loop_engine/core/stage_assistance_material.py),
[`stage_action_lineage.py`](../../src/loop_engine/core/stage_action_lineage.py),
and the public solve adapter in
[`solve_request_adaptation.py`](../../src/loop_engine/code_nodes/solve_request_adaptation.py).
These records perform no model call, retrieval, storage, graph mutation,
execution, routing, acceptance, or promotion.
The public aggregate construction path uses local recomputation functions.
Their external source references and validity records are still
unresolved candidates until canonical Run History integration exists.

The following claims remain unproven:

- the information-theory and procedural-control candidate records are
  connected to the product solve path;
- a live model, rather than an injected provider response, uses or rejects the
  hydrated material;
- canonical Run History durably stores and later joins every measurement;
- a resolver verifies each external reference and validity record;
- any structured state matches full history on held-out tasks;
- update-level surprise calculations are issued against a resolved population,
  probability model, and evaluator;
- any information estimate is reliable in a high-dimensional task region;
- a predictive or successor fingerprint improves retrieval;
- prior procedural memory improves a valid assisted-versus-fresh comparison;
- stage contribution is causal rather than evaluator-attributed;
- any procedural shortcut is qualified to act first;
- any small model, cache, embedding, or deterministic policy can replace the
  LLM for an open-world semantic decision;
- the mechanisms reproduce across the 100-task Kaggle campaign or across
  unrelated task regions.

The next implementation step is not automatic compilation. It is to complete
offline invariants, persist these passive records through canonical Run
History, and run the exact frozen experiment above. Product exposure should
follow only if that evidence supports it.

## Primary sources

The source versions and publication pages below were checked on 2026-09-04.

- [On Information and Sufficiency](https://doi.org/10.1214/aoms/1177729694),
  Kullback and Leibler, 1951.
- [Coding Theorems for a Discrete Source With a Fidelity Criterion](https://gwern.net/doc/cs/algorithm/information/1959-shannon.pdf),
  Shannon, 1959.
- [The Information Bottleneck Method](https://arxiv.org/abs/physics/0004057),
  Tishby, Pereira, and Bialek.
- [Predictive Representations of State](https://proceedings.neurips.cc/paper_files/paper/2001/file/1e4d36177d71bbb3558e43af9577d70e-Paper.pdf),
  Littman, Sutton, and Singh.
- [Improving Generalization for Temporal Difference Learning: The Successor Representation](https://doi.org/10.1162/neco.1993.5.4.613),
  Dayan, 1993.
- [Between MDPs and Semi-MDPs: A Framework for Temporal Abstraction in Reinforcement Learning](https://doi.org/10.1016/S0004-3702(99)00052-1),
  Sutton, Precup, and Singh, 1999.
- [Bayesian Surprise Attracts Human Attention](https://papers.neurips.cc/paper/2822-bayesian-surprise-attracts-human-attention.pdf),
  Itti and Baldi, 2005.
- [Recuris](https://arxiv.org/abs/2608.24876), v1.
- [SkillGLoW](https://arxiv.org/abs/2609.02217), v1.
- [PILOT](https://arxiv.org/abs/2608.26530), v1.
- [APEx](https://arxiv.org/abs/2609.02253), v1.
- [CONTRAMEM](https://arxiv.org/abs/2608.22533), v1.
- [Demystify the Role of Memory in Machine Learning Engineering Agents](https://aclanthology.org/2026.findings-acl.525/),
  Findings of ACL 2026.
- [Fine-Mem](https://aclanthology.org/2026.acl-long.900/), ACL 2026.
- [How Memory Management Impacts LLM Agents](https://aclanthology.org/2026.acl-long.27/),
  ACL 2026.
- [Memp](https://aclanthology.org/2026.findings-acl.866/), Findings of ACL
  2026.
