# Adaptive questions, compilation, and capability research

Research date: 2026-09-05. Status: research and proposed experiments, not a
runtime implementation or a claim of AGI. This follow-up asks how a Loop can
choose useful questions, create and revise subtasks, select computation, and
turn verified experience into reusable capabilities. More questions, smaller
prompts, more agents, and shorter programs are not success criteria by themselves.

This extends the [adaptive computation review](ADAPTIVE-COGNITIVE-MESH-AND-AMORTIZED-COMPUTATION-2026-09-04.md)
without replacing its source map, existing contracts, or the
[current product proof gate](../verification/UNSEEN-TASK-DIAGNOSTIC-AND-GENERALIZATION-2026-09-04.md).
All proposed experiments below remain unrun. External results are author-reported;
none was reproduced here. Publication dates below distinguish original work
from later revisions, not implementation qualification.

## Repository evidence and boundaries

Read-only inspection used `main` at
`d121379773e46a1255fd3e86436d907dc2a0b4d0` with the existing dirty record/harness
work preserved. No runtime source, provider configuration, dependency, or
generated architecture authority was changed in this research pass. No model
experiment, deployment, commit, or push occurred. The earlier 2,680-check result
belongs to its saved verification checkout; it was not rerun for this report.

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
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the mode permits a model
    └── Run History records
```

The existing [contract index](../contracts/README.md) remains the interface map.
Research roles do not require new runtime classes. Domain-specific questions,
rules, examples, code, and verifiers belong in the four existing intelligence
layers and qualified capabilities. They must not select an industry controller
through a label or filename.

Two distinctions matter before learning new policies:

| Inspected boundary | Current behavior | Research consequence |
|---|---|---|
| `core.task_frontier` | `FrontierItem` and `FrontierSnapshot` are digest-chained projections of adaptive results | This is not an active general work-queue controller. Do not infer policy execution from its presence. |
| `frontier_from_adaptive_result` | A question absent from a later nonempty orientation becomes `ANSWERED`; selected work with unknown verdict can become `COMPLETED` | These statuses are not independently verified labels for training question or stopping policies. |
| `LoopGraphDefinition` | One typed executable DAG authority | Feedback uses later activations/revisions; arbitrary cyclic graphs are not an installed execution feature. |
| `loop.loop_capsule` | `LoopCapsule` is a compatibility alias for `IntelligenceItemPackage` | Extend current package/semantic contracts instead of creating a competing capsule registry. |
| Information evidence | Existing measurements and paired state-policy records have documented reference-resolution gaps | A numerical diagnostic does not establish causal benefit or authorize promotion. |

Two small in-memory probes confirmed the frontier behavior without any model
call or file mutation. Input A had two orientations: first one unknown question,
then an empty unknown list, with no answer or verification record. Its status
changed `READY` to `ANSWERED`. Input B had a selected `GENERATE_CODE` action and
no verdict across two passes. Its status changed `SELECTED` to `COMPLETED`.
These observations do not show that the product falsely accepted a task; they
show why the projection is an unsafe substitute for verified outcome labels.

Inspected source SHA-256:

- `core/task_frontier.py`: `5b02ff8cdb4ed8faf654286f4acc51979d8aeac941ff7d52b03e9bb682343c1f`
- `code_nodes/solution_graph.py`: `07d1a690b994c1b4d6ec04ed6837cec49aee43ecf01f979537369d10b95d4174`

## 1. Questions as decision-support actions

The solver should maintain candidate questions without asking the user all of
them. A question may be answered by a file, tool, experiment, verifier, or human.
First distinguish an unclear goal from missing environmental evidence and from
the model's own uncertainty. Only the first necessarily requires user input.

[Structured Uncertainty Guided Clarification](https://aclanthology.org/2026.findings-acl.2028/)
(Findings ACL, July 2026) makes this distinction over tool parameters and models
question value and cost. Its evaluated parameter domains do not supply a
universal value estimator for open-ended research or planning.

Research questions:

1. Which answer could change the next action, its authority, or acceptance?
2. Can the engine inspect an available source instead of interrupting the user?
3. When should independent questions be batched, and when would the first answer
   make later questions unnecessary?
4. Can redundant questions be merged without merging distinct constraints?
5. What exact answer/evidence resolves a question, and what later event reopens it?

Candidate records should identify the affected decision, alternative hypotheses,
answer source, predicted observations, dependencies, burden, and unresolved
status. A vanished question is not an answer. Question generation, selection,
asking, interpretation, and resolution need separate outcome events.

## 2. Adaptive decomposition and subtask generation

[Least-to-Most Prompting](https://arxiv.org/abs/2205.10625) (2022; ICLR 2023)
decomposes before sequential solution. [Decomposed Prompting](https://arxiv.org/abs/2210.02406)
(2022; ICLR 2023) delegates to modular handlers. Both demonstrate useful
mechanisms but use task-designed examples or handlers. Importing their evaluated
task taxonomy would conflict with open-world intake.

[ADaPT](https://aclanthology.org/2024.findings-naacl.264/) (NAACL Findings 2024)
instead decomposes when execution cannot complete a subtask. That makes the
failure detector part of the effective policy: false success blocks necessary
decomposition, while false failure creates unnecessary work.

Research questions:

6. Is this responsibility coherent enough to solve directly?
7. Which boundary needs a separate observation, verifier, authority, or checkpoint?
8. Are subtasks independent, conditional, or coupled by shared constraints?
9. Can a failed subtask be replaced while preserving verified neighboring work?
10. Can decomposition discover a missing capability rather than silently assume it?

Generate several possible decompositions as candidates, not several mandatory
executions. Each selected subtask needs a goal, typed inputs/outputs, exact
dependency references, acceptance conditions, authority, and a contribution to
the parent objective. Local completion must not imply parent completion.

## 3. Small iterative prompts with sufficient state

Compare coherent calls with bounded iterations that carry the original task
constraints, current responsibility, exact dependency outputs, relevant evidence,
uncertainties, and a response contract. Shorter prompts can lose facts needed to
maintain global consistency. Repeating a full transcript can also add cost and
irrelevant material. The useful size is a measured property of the responsibility.

Research questions:

11. Which facts must remain exact across every iteration?
12. Does an iteration obtain evidence, test a hypothesis, repair a failure, or only
    restate the preceding answer?
13. When can compatible logical steps share one physical call without hiding
    their outputs, verification, or attribution?
14. Can a verified incumbent survive a misleading critique or new speculative branch?

[Intrinsic self-correction experiments](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html)
(ICLR 2024) found failures and degradation without external feedback on the
studied models/tasks. This is a reason to compare evidence-backed repair with
intrinsic reflection, not a claim that all current models cannot self-correct.
Store concise decisions, observations and tests, not private hidden reasoning.

## 4. Compilation as distinct transformations

Compilation can mean task-to-contract, contract-to-graph, graph-to-placement,
graph-to-code, or prompt/program optimization. These transformations have
different proof obligations. An optimized prompt still calling an LLM is not a
zero-model compiled capability.

[LLMCompiler](https://icml.cc/virtual/2024/poster/32829) (ICML 2024) separates
planning dependencies, dispatch and function execution. Its reported parallel
gains do not authorize reordering effectful operations or duplicating commands.
[WIT](https://component-model.bytecodealliance.org/design/wit.html) defines
interfaces rather than behavior; behavioral obligations remain necessary.

Research questions:

15. What observable behavior must each compiler preserve, including units and errors?
16. Can capsules support useful composition without full source hydration?
17. Which reads can run concurrently without changing snapshot semantics?
18. Does fusion or compilation preserve exact effects, failure boundaries,
    cancellation, budget accounting, and treatment isolation?
19. Can deployment change through capability/environment bindings rather than core edits?

Use differential and metamorphic checks between interpreted and compiled
realizations. A type-correct graph can still compute the wrong thing. Generated
adapters and glue remain candidates until independently checked. Keep one
`LoopGraphDefinition`; physical scheduling is a separate plan, not another
semantic graph authority.

## 5. Information theory and the value of computation

These are proposed decision models, not measurements already supplied by the
runtime. A useful question-value model is:

```text
VOI(q | h) = E_y[max_a E[U(a, theta) | h, q, y]]
             - max_a E[U(a, theta) | h] - cost(q)
```

Here `h` is admitted information, `theta` is the unknown task state, `q` is a
question/probe, `y` its possible answer, and `a` an authorized downstream action.
Utility and cost need comparable units or an explicit multi-objective policy.
Hard safety and authority constraints must not become soft utility penalties.
Question bundles need their joint value; summing individual values double-counts
redundancy and misses complementary questions.

[Selecting Computations](https://arxiv.org/pdf/1207.5879) (UAI 2012) models
computation as a decision with cost. Its examples show why a myopic stopping
rule can miss sequences of computations that are useful together. An LLM
writing a confidence number does not supply its probabilistic assumptions.

Expected information gain concerns a specified unknown variable:

```text
EIG(q | h) = E_y[KL(p(theta | h, q, y) || p(theta | h))]
```

It need not maximize task utility. Learning an unpredictable nuisance field can
yield information without helping the decision. A diagnostic metric needs its
population, variables, estimator, units, calibration and computation cost.

[Information bottleneck](https://arxiv.org/pdf/physics/0004057) (1999 manuscript;
2000 preprint) defines compression relative to a relevance variable. If `Z`
is derived only from history `H`, data processing does not let it create more
information about target `Y` than `H` contains. A bounded model may nevertheless
use `Z` more effectively. Test downstream loss and recoverability, not token
compression alone.

Research questions:

20. Which unknowns affect the decision, rather than merely having high entropy?
21. Do question pairs have value that a one-step score misses?
22. Does compressed state retain late-relevant facts, counterevidence, and source identity?
23. Is the cost of selecting a computation greater than the computation it saves?
24. Does estimated progress predict independent verified progress on held-out work?

## 6. Capability theory with explicit meanings

There is no single capability score that establishes general intelligence.
Keep these meanings separate:

| Meaning | Operational question | Required evidence |
|---|---|---|
| Representational capacity | Can this language, model or interface express the needed behavior? | Type/expressiveness arguments with explicit assumptions |
| Available affordance | Can this environment expose the observation or action? | Runtime discovery and verified environment compatibility |
| Demonstrated competence | How reliably does this exact realization satisfy this contract in this region? | Independent outcomes, distribution, budget, calibration and failure regions |
| Granted authority | May this activation perform this effect now? | Current scope, permission, effect approval and revocation checks |

[Horton](https://www.usenix.org/legacy/event/hotsec07/tech/full_papers/miller/miller_html/index.html)
(HotSec 2007) concerns delegating and attributing narrow authority through
object capabilities. A plain locator in Loop Engine is not an unforgeable
grant. Neither permission nor an installed tool proves competence.

[Selective classification](https://arxiv.org/pdf/1705.08500) (2017) motivates
measuring accepted risk together with coverage. [Uncertainty under dataset shift](https://arxiv.org/html/1906.02530v2)
(NeurIPS 2019) warns against carrying familiar-population calibration into a
changed environment. OOD signals, calibration, ranking and abstention are
separate properties.

Research questions:

25. What input region, environment, budget and verifier qualify this capability?
26. Do composition errors share causes, making independent-success products invalid?
27. Can a failed composition reveal a missing adapter, observation, permission, or skill?
28. Does a capability detect changed goals, units, tools or data distributions and abstain?

[Successor features and generalized policy improvement](https://papers.nips.cc/paper/2017/hash/350db081a661525235354dd3e19b8c05-Abstract.html)
(NeurIPS 2017) offer a transfer mechanism that separates dynamics from rewards.
The stated same-dynamics setting is a material limitation: topic similarity does
not establish compatible transition behavior. Treat cross-domain reuse as a
tested mapping, not a vocabulary match.

## 7. Reuse, abstraction and distillation

The following primary-paper versions were reviewed for this follow-up. Their
implementations and licenses are not automatically admitted into Loop Engine.

| Source version | Transferable mechanism | Condition that narrows the claim |
|---|---|---|
| [DSPy v1](https://arxiv.org/html/2310.03714v1), 2023-10-05 | Optimize declared model-call programs and demonstrations | An end-to-end metric can accept traces with incorrect intermediate steps; compilation is not semantic equivalence. |
| [GEPA v2](https://arxiv.org/pdf/2507.19457v2), 2026-02-14 | Reflective prompt mutation and Pareto candidate selection | Weights remain frozen; reflective credit assignment is not causal attribution. Include selection/evaluation cost, not just rollout count. |
| [Darwin Godel Machine v3](https://arxiv.org/html/2505.22954v3), 2026-03-12 | Archive-based search over coding-agent changes | Reused evolutionary subsets are not untouched audit populations; the paper documents objective hacking. |
| [DreamCoder v1](https://arxiv.org/html/2006.08381v1), 2020-06-15 | Alternate program search, library abstraction and search-guide learning | The typed language and task likelihood constrain the problem; arbitrary effectful Python does not inherit those conditions. |
| [LATM v2](https://arxiv.org/html/2305.17126v2), 2024-03-11 | Stronger tool maker and cheaper tool user | Tiny per-family validation populations cannot qualify broad applicability. Charge tool construction and failed dispatches to reuse economics. |
| [CRAFT v2](https://arxiv.org/html/2309.17428v2), 2024-03-13 | Create, abstract, validate, deduplicate and retrieve tools | Post-abstraction validation uses original tasks; name/arity grouping is not behavioral equivalence. |

Look for repeated verified transformations, dependencies and failure-recovery
patterns. A whole successful task is not automatically the best reuse unit.
Extract a smaller parameterized capability only when its contract survives
changes in values, names, context and environment.

Research questions:

29. Which repeated structure is stable, and which detail was accidental?
30. Should experience become an example, context policy, response program, code,
    subgraph, ranker or tuned model?
31. Are teacher labels independently supported, or is the student learning errors?
32. Does the shortcut preserve abstention, failure detection, and a qualified escape?
33. How many uses repay creation, qualification and maintenance costs?

For equal verified quality, a simple accounting check is:

```text
reuse is cheaper when
N * (cost_fresh - cost_reuse) > cost_build + cost_qualify + cost_maintain
```

Include retrieval, verification, repairs, storage, and model calls in those
costs. If the per-use saving is nonpositive there is no positive break-even
count under this model. Quality and authority are gates, not exchangeable savings.

Start distilled models on bounded support decisions such as ranking context or
predicting verifier risk. Keep teacher proposals, admitted decisions, exact
actions, observations, independent outcomes, failures and later invalidations
distinct. Compare simpler supervision with elaborate teacher explanations;
private hidden chain of thought is not required training data.

## 8. Self-evolution with independent acceptance

Candidate search may change prompt wording, response topology, context policy,
decomposition, model allocation, or a reusable capability. Begin with one
bounded surface so the experiment can attribute the effect. Archive rejected
candidates and negative transfer as well as successful candidates.

Research questions:

34. Does a diverse archive improve search at matched total experiment cost?
35. Can a candidate change the evaluator, its permissions, or the acceptance population?
36. Does repeated testing accumulate false promotions?
37. Can a regression be invalidated and rolled back without erasing its history?

Separate proposer, evaluator and promoter. Untouched holdouts are not tuning
data, even when only aggregate scores are returned. Evidence from different
models, task lineages and time periods needs explicit grouping. Statistical
acceptance guarantees apply only under their assumptions, not to an arbitrary
sequence of self-modifications. Core permission and verifier changes require
stronger governance than run-scoped response-program experiments.

## Experiment program

The treatments below are proposed. First use small offline fixtures to validate
the mechanism. Choose live sample sizes from a declared effect/precision target
and budget; pilot counts do not establish statistical sufficiency. Avoid one
large factorial search that exhausts the holdout or compute allowance.

| ID | Treatment and controls | Primary falsifier |
|---|---|---|
| Q1 | Decision-value question selection versus never-ask, ask-all and ordinary LLM selection; include complete requests, ambiguities, redundant and complementary questions | No utility gain after question cost, unnecessary user interruptions, missed material questions, or unsupported resolution labels |
| D1 | Coherent execution versus fixed decomposition and failure-triggered splitting; hold out dependency shapes and operator combinations | Added steps propagate errors or add total cost without improving independently verified completion |
| P1 | Full authorized history versus bounded task-aware state and length-matched generic summaries; introduce late-relevant constraints | Lost critical facts/authority, lower verified quality, or retrieval/repair cost erases the saving |
| C1 | Interpreted graph versus capsule composition, safe parallel scheduling and a compiled realization | Changed units, semantics, effects, ordering, treatment exposure, cancellation or independent verdict |
| I1 | Entropy-greedy versus task VOI, bounded lookahead and fixed-budget probes in an enumerable environment | Nuisance entropy wins over useful evidence, complementary probes are missed, or estimation overhead erases utility gain |
| R1 | Fresh solve versus retrieved episode, parameterized capability and distilled support policy; use changed-goal and misleading-similarity cases | Reuse increases false acceptance, fails novel compositions, lacks an escape, or misses quality-adjusted break-even |
| E1 | Fixed incumbent versus greedy replacement and controlled candidate acceptance; keep audit data inaccessible to search | Accepted candidates degrade untouched audit tasks or false promotions exceed the declared allowance |
| M1 | Exact values/revision refs across existing information backends; mutate source, expire/revoke access and pause before commit | Stale ref silently returns new bytes, revoked authority allows a new read/effect, or a transaction stays open during reasoning |

Every experiment records source/implementation digests, realized model-visible
packets, assignment, evaluator identity, exclusions, unknown usage, physical
calls, cost, latency, verified outcomes, coverage and later invalidation. A
template-free/fresh control is necessary when evaluating reusable prompting.
Wrong but structurally valid outputs must remain visible.

## Small implementation sequence after research

The subsequent [reasoned output and mode-policy report](../verification/REASONED-OUTPUT-AND-MODE-POLICY-2026-09-05.md)
records the implemented repair subset. The frontier observations above retain
their original inspected source digests; they are not claims about the repaired
checkout. The broader experiments remain unrun.

1. Prove pre-dispatch resource reservation and refusal, including retries,
   uncertain usage, parallel reservations and cancellation. Do not lower the
   provider's source-backed output maximum silently to fit a budget.
2. Finish the current canonical assisted/fresh product pair with independent
   evaluation and exact packet/control evidence. Research does not replace it.
3. Replace inferred question/work resolution labels with evidence-linked
   outcomes before using frontier projections for learning. This is a proposed
   correction, not a change implemented by this report.
4. Implement one bounded Q1/D1 comparison through current Practitioner decisions
   and `LoopGraphDefinition`. Do not introduce a second planner runtime.
5. Test one reusable subgraph and one support-model candidate in shadow using
   R1/E1. Expand only where independent evidence supports the next region.

The intended progress is better decisions about what to ask, which work to
create, how much computation to spend, and what can be reused safely. Universal
task success, full automatic deployment, million-task generalization and
autonomous core evolution remain unproven.
