# Recurrent models and system-level improvement

Loop Engine can test improvements to procedures, configurations, tools, and
Loop graphs using existing inference endpoints. It does not need a new model
architecture to start that work. Persistent improvement still requires a
measured benefit on later tasks, independent review, and explicit promotion.
Repeated generation on one task establishes none of those by itself.

This September 14 research synthesis maps published work to the existing
architecture. Proposed experiments below are not implemented settings or
claims of artificial general intelligence. The
[current experiment report](../verification/EXPERIMENT-FABRIC-READINESS-2026-09-14.md)
records the separate implementation and live-evidence limits.

## Architectural placement

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

An improvement experiment uses this classification without adding a runtime
type. Harnesses and model endpoints remain adapters. Optimizers, memory
stores, and evaluation services remain internal mechanics owned by classified
Loops. Read the [complete behavioral explanation](../context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md)
for narrow assignments, separate harness initialization, continued candidate
production, declared completion, and protection against repeated effects.

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

A Starting Practitioner can propose an experiment and spawn a bounded solver
or verifier. It queries an Intelligence Query Loop, which retrieves selected
Intelligence Item Loops. A resulting Solution Canvas connects executable
Solution Loops through typed ports. Dynamic repair and ensemble branches may
spawn additional Loops under the remaining authority. The Canvas itself has
no single execution mode.

## What the research establishes

| Work | Mechanism | Limit and relevance |
|---|---|---|
| Recurrent Looped Transformer, Yifan Zhang, September 12, 2026 | A recurrent decoder carries its hidden state and layer-specific sliding-window attention state across prompt and response tokens. A causal encoder supplies global attention memory. | Temporal recurrence is not unlimited computation per token or constant total memory. The paper does not establish large-model reasoning gains. It is a possible future model route, not an available Loop Engine setting. [Author project and paper](https://yifanzhang-pro.github.io/recurrent-looped-tranformer/). |
| Scaling up Test-Time Compute with Latent Reasoning, February 2025 | The Huginn model repeats an internal latent reasoning core. The authors trained a 3.5-billion-parameter model and released artifacts. | This provides empirical recurrent-depth work, but availability through an installed inference endpoint must be checked separately. [Paper](https://arxiv.org/abs/2502.05171). |
| Scaling Latent Reasoning via Looped Language Models, October 2025, revised July 2026 | Ouro studies shared layers and learned allocation of recurrent depth. | Internal depth is distinct from a harness making additional model calls. Published model comparisons are not Loop Engine benchmark results. [Paper](https://arxiv.org/abs/2510.25741). |
| Darwin Gödel Machine, May 2025 | An evolutionary archive retains coding agents whose implementation changes are tested empirically. | This directly informs harness and procedure experiments without requiring foundation-model weight updates. Its benchmark results do not transfer to this repository. [Paper](https://arxiv.org/abs/2505.22954), [official code](https://github.com/jennyzzt/dgm). |
| Metaⁿ, August 25, 2026 | A fixed meta-operation consumes code and traces from the current agent stack and proposes strategic context or callable helpers. An archive retains alternative layer chains. | The official repository calls the work a research prototype. Some experiments lack held-out splits, and archive-best selection differs from a deployable selector. Deeper layers can cause negative transfer. [Paper](https://arxiv.org/abs/2608.24735), [official code](https://github.com/minnesotanlp/meta-n). |
| Self-Adapting Language Models, 2025 | The system generates adaptation data and update instructions, then learns from downstream performance after weight updates. | Persistent parameter adaptation needs training access. It is not automatically available from an ordinary completion endpoint. [Official code](https://github.com/Continual-Intelligence/SEAL). |
| The Last AI Built by Humans, September 10, 2026 | A roadmap separates executing improvements, choosing strategies, gathering experience, adapting environments, and improving the improvement process. | This is not evidence of a completed general self-improving system. Its Headroom Closed Index measures historical benchmark progress, not recursive improvement directly. [Paper](https://arxiv.org/abs/2609.11873). |
| Recursive Self-Improvement in AI, revised September 6, 2026 | A survey separates changes to deployment behavior, trained policy, evaluators, and research processes. | Use these distinctions to identify what an experiment changes and who verifies it. They do not establish that repeated self-judgment is reliable. [Survey](https://arxiv.org/abs/2607.07663). |

The Recurrent Looped Transformer repository also reports small synthetic
experiments, so describing it as having no experiments would be inaccurate.
Those tests do not match computation budgets and are not evidence of a
general-purpose production model. Full state replay matters after weight
updates: replaying only text or the final hidden state is not equivalent to
reconstructing all recurrent attention state. These constraints come from the
[author's repository](https://github.com/yifanzhang-pro/recurrent-looped-tranformer).

Our inference from this literature is practical: first test changes to the
system around the model, where Loop Engine controls the experiment and can
save exact evidence. Treat latent recurrence and model training as additional
capabilities only when an exact provider or installed implementation supports
them. A model family name does not prove support.

## Fixed-weight harness optimization

The owner supplied a report attributed to Joël Niklaus: an optimized OpenCode
v1.18.13 harness with GPT-OSS-20B at high reasoning increased held-out
Terminal-Bench 2.1 success from 4.8% to 14.8% after 23 search iterations and
about 2,400 development attempts, using $49.97 of application programming
interface credits. Those are the supplied report's claims, not results
reproduced in Loop Engine. The arithmetic is a 10-percentage-point increase
and approximately 3.08 times the original success rate. It is not a claim of
three times the model's general intelligence; 85.2% of attempts still failed
under the reported measure.

The original social-post address is
[Joël Niklaus's post](https://x.com/joelniklaus/status/2098064253404225640).
The browser could not read its full text directly. The official public embed
endpoint confirmed the author, post identity, and opening text, but returned
only a truncated view of the long post. A search result reproduced the supplied
text; that is not independent technical verification. The author's public
[harness-optimization repository](https://github.com/JoelNiklaus/harness-optimization/tree/c98a168014412c2333fca635cdcc0c6c901c0ade)
was inspected at `c98a168014412c2333fca635cdcc0c6c901c0ade`. Its available main
branch describes related work, including a different SWE-bench Pro
comparison. It did not establish the exact task split, patch history, or cost
accounting for the reported $49.97 experiment. Do not merge those two studies.

Further source tracing found the author's separate
[harness-optimization-results archive](https://huggingface.co/buckets/joelniklaus/harness-optimization-results).
Its published baseline search summary contains 39 tasks with three attempts
each, six successes in 117 attempts, and a 5.1282% success rate. The inspected
held-out task configuration names Gemma 4 26B-A4B, not GPT-OSS-20B. These
records do not verify the supplied post's exact experiment. Matching an
OpenCode version or a folder name is insufficient.
[Inspected summary](https://huggingface.co/buckets/joelniklaus/harness-optimization-results/tree/search/iter00-upstream-v1-18-13/summary.json),
[inspected task configuration](https://huggingface.co/buckets/joelniklaus/harness-optimization-results/tree/heldout/heldout-baseline-upstream-v1-18-13/break-filter-js-from-html/a1/harbor-job-config.json).

Before citing the numerical result as qualified external evidence, resolve
the exact development and held-out task identifiers, repetitions, seeds,
serving configuration, immutable harness revisions, evaluator, validation
margin, rejected candidates, and cost records. The development baseline of
8.5% is not the held-out baseline of 4.8%. Whether the reported budget includes
the proposing model, build and sandbox compute, repeated validation, and
final evaluation remains unverified.

### Related primary research

| Study | Relevant evidence | Experiment implication for Loop Engine |
|---|---|---|
| [Meta-Harness, March 2026](https://arxiv.org/abs/2603.28052) | Searches code around a fixed model using prior source, scores, and execution traces. It studies context management, retrieval, and coding. | Treat harness code and information presentation as searchable candidates. Preserve drill-down access to exact failure evidence rather than only aggregate scores. |
| [Agentic Harness Engineering, April 2026](https://arxiv.org/abs/2604.25850) | Exposes editable components, structured experience, and predictions associated with proposed edits. | Record the changed component, predicted behavioral effect, relevant task population, observed effect, and regressions separately. |
| [Rethinking the Evaluation of Harness Evolution for Agents, July 2026](https://arxiv.org/abs/2607.12227) | Under comparable feedback and inference budgets, harness evolution did not consistently outperform simpler search; transfer was limited in the tested setups. | Compare against parallel sampling and sequential task repair. Measure protected later-task performance before claiming reusable improvement. |
| [HarnessLens, August 2026](https://arxiv.org/abs/2608.27311) | Selects behavior-relevant tasks for candidate checks and uses additional confirmation to distinguish attributable gains from regressions. | Target development checks by affected behavior, then validate on a separate confirmation population. A higher aggregate can hide a broken task family. |
| [HarnessDev, September 2026](https://arxiv.org/abs/2609.01437) | Evaluates harness creation and evolution across multiple domains. Generated harnesses have uneven performance and limited transfer between runtime models. | Optimize model-harness combinations, not a universal harness ranking. Keep creation, improvement, and cross-model transfer as distinct evaluations. |
| [Harness-of-Harness, September 2026](https://arxiv.org/abs/2609.01481) | Organizes existing coding harnesses into planning, coding, and testing iterations with versioned project histories and independent evaluation. | Study outer control, progressive resource exposure, and reusable work while preserving the existing Loop runtime and authority. Longer operation alone does not prove persistent harness improvement. |

These studies support experimentation, not a guaranteed improvement factor.
Their different task populations, models, budgets, and evaluators prevent an
uncontrolled ranking of the reported scores.

### Turn the reported fixes into governed treatments

| Reported treatment | Loop Engine interpretation | Required negative controls |
|---|---|---|
| Verify before stopping | A candidate completion request must resolve typed verification obligations bound to the exact delivered artifact. If continuation is permitted, the owner can assign verification work. | Changed artifact after testing; missing evaluator; unverifiable output; exhausted authority; already terminal activation. No automatic acceptance from merely running a command. |
| Continue announced actions | A native harness finishing its turn need not complete its owning Loop. Typed unmet obligations can justify another permitted turn or assignment. | Do not extract a command from prose and execute it. A statement such as "now run X" is not tool authority. Refuse repeated committed effects, cancellation bypass, and unbounded continuation. |
| Repair malformed tool calls | A versioned formatting-repair policy may propose an unambiguous syntactic correction, then revalidate the complete typed tool call and its exact effects. | Multiple plausible repairs; changed tool identity; altered paths or arguments; invalid schema after repair; embedded instructions in tool output. Preserve original and repaired identities. Never use repair to widen permissions. |

These treatments are candidate dimensions, not universal defaults. They must
be independently selectable and have explicit fallbacks. A matched experiment
needs the original harness, each treatment alone, combinations, and controls
that spend the same extra work without changing the harness. A failed
compatibility check is an exclusion with a reason, not a model failure.

Use an isolated candidate workspace for a proposed harness patch. Compile and
test the exact patch before a task rollout; do not edit a shared installed
harness or the running parent. Bind the candidate to its parent version,
source digest, declared effects, and build environment. The independent
validator controls held-out tasks and promotion. The proposing Practitioner
can nominate a new parent, but cannot approve it or rewrite its evaluator.

Retain the complete search history, including declined patches and failed
builds. Report proposer calls, candidate execution calls, validation calls,
physical provider requests, tokens, unknown cost, elapsed time, and compute
separately. Compare improvement per total search budget and later-task reuse,
not only the final harness's inference cost.

## Four intelligence layers, with separate Runtime Memory

| Existing layer | Material from an improvement experiment | Admission and use |
|---|---|---|
| Context Intelligence | Source-backed research summaries, reusable methods, questions, prompt templates, failure conditions, and context-selection guidance. | Stage proposed guidance as candidate material. Review scope, evidence, contradictory results, and later-task performance before active reuse. |
| Code Intelligence | Reusable implementations, harness adapters, evaluators, configuration procedures, and deterministic realizations of useful semantic work. | Bind exact source, version, digest, provenance, license, dependencies, typed contracts, effects, tests, and independent qualification. A retrieved card does not authorize execution. |
| Runtime History and Solution Intelligence | Exact trial occurrences, observed settings, output identities, verified histories, failures, comparisons, and compiled Solution references. | Preserve failures and exclusions. Separate mechanical execution, development evaluation, task acceptance, and reusable suitability. Historical success is a prior, not proof for a new task. |
| User Feedback Intelligence | The owner's requirements, corrections, scope choices, and explicitly attributed feedback. | Preserve authorship, target, timing, conflicts, and strength. An automated evaluator's finding belongs in experimental history, not in a record pretending to be human advice. |

Runtime Memory holds temporary hypotheses, selected references, and working
observations for one run. It is not a fifth persistent intelligence layer.
Moving a useful observation out of Runtime Memory requires a candidate record
and the destination layer's admission process.

Use the existing [intelligence components](../components/intelligence-layers/README.md),
[self-improvement Practitioner](../components/self-improvement/README.md), and
[reusable capability process](../components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md).
Do not create a second learning database or promote an item through a legacy
convenience registry. The ordinary search path excludes candidates and
inactive lifecycle declarations even when a record claims the core tier.
Explicit candidate review does not grant access to a gated collection.

## Search dimensions to extend and qualify

The [owner's dimension inventory](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
remains the required baseline. The following experiments extend that design;
they do not add accepted runtime fields by naming them in this document.

| Experiment family | Choices to represent separately |
|---|---|
| Procedure and graph composition | Step order, added cognitive work, action boundaries, branch topology, alternative output production, comparison, and stopping conditions. Compare both larger and compact procedures. |
| Harness composition | Initial harness, ordered compatible alternatives, wrapper layers, native control ownership, fresh or resumed sessions, state transfer, and cancellation semantics. |
| Intelligence use | Which layer is queried, retrieval method, exact or similar fingerprints, selection policy, context allocation, source freshness, candidate-review scope, and negative-transfer controls. |
| Optimizer and meta-selector | Grid traversal, random controls, Bayesian proposals, evolutionary proposals, vector similarity, portfolios, exploration priorities, multi-objective ranking, and confidence calibration. |
| Experimental design | Task-family stratification, repetitions, seeds, evaluator version, training and development separation, protected final tests, fidelity, delayed feedback, and duplicate-occurrence handling. |
| Resource allocation | Per-cell and cumulative authority, call and pass budgets, wall time, concurrency, model output allocations, thinking settings, retrieval expense, and optimizer overhead. Unknown cost stays unknown. |
| Optional model recurrence | Exposed internal depth controls, stopping rules, recurrent-state lifetime, cache identity, replay requirements, and training access. Record unavailable or unknown when no exact implementation declares them. |

Every admitted choice needs an initial value and ordered fallback policy.
Discovery, support, installed availability, qualification, permissions,
eligibility, ranking, selection, execution, evaluation, acceptance, and
promotion remain distinct. An unavailable harness should exclude that route,
not silently remove the task or install software with new authority.

An optimizer proposes only within the currently declared typed space. A
proposal to add an unknown dimension is design work for independent review.
It cannot mutate the running contract. The design space can remain open while
each measured campaign has a finite, versioned denominator.

## Proof sequence for reusable improvement

Freeze tasks, source identities, configurations, and evaluator versions.
Compare a fixed baseline with context retrieval, independently qualified code
reuse, adaptive configuration selection, and reviewed procedure changes.
Use matched task splits and resource accounting. Keep a deployable selector's
choice separate from retrospectively choosing the best archived answer.

For every comparison, retain exact configurations, alternative rankings and
reasons, model and tool attempts, declared and effective settings, exclusions,
unknown usage, artifacts, and independent verdicts. Evaluate the next version
on different tasks before claiming transfer. Measure regressions and the cost
of finding the improvement, not only the cost of its final successful run.

An improvement Practitioner may propose a better optimizer or evaluator. It
cannot replace the evaluator judging that same proposal, approve its own
candidate, expand its permissions, or bypass rollback. A successful task
repair, a useful reusable procedure, and an improved discovery process are
three different claims with different evidence requirements.

## Current limits

The reference campaign and compact artifact experiment do not yet prove the
complete improvement cycle. The compact route composes and executes a
candidate project; it does not compile and independently qualify the complete
Solution Canvas or materialize dataset directories. Unsupported materializers
produce an explicit eligibility result before a model call. Its direct model
gateway composition is recorded separately from an external harness wrapper.

The live reference workers exhausted the available Ollama allowance or were
cancelled for repeated unaccepted work. No future reset time is inferred.
The next live qualification needs a checked runtime snapshot, explicit
supervision and resource policies, reconciled interrupted effects, and usable
task evaluators. Large queues and repeated model calls are not evidence of
recursive self-improvement.
