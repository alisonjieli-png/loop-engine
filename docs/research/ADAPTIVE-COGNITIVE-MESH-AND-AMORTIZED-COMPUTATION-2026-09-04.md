# Adaptive cognitive Loops and amortized computation

Research date: 2026-09-04. Repository inspected: `main` at
`22ee44052b027ba96ce50c37e4cc6a659e1b91c8`, with existing uncommitted work.

Status: research synthesis and proposed design. The templates accompanying
this note are passive design examples. They are not installed Loop profiles,
learned policies, training jobs, or evidence of improved task performance.

Loop Engine can be framed as a cognitive mesh: a changing arrangement of
Loops that orient, investigate, compute, communicate, verify, repair, and
learn. Each responsibility can have several realizations. The research
question is which realization, context, and amount of computation should be
used for this responsibility, given the information currently available and
the consequences of an error.

This framing gives the user's AGI Loop Node Framework ambition an engineering
target: open task intake, compositional problem solving, selective use of
experience, and measured improvement across task populations. It does not
establish that any implementation can solve every representable problem.

## Reading map

Read this page for computation selection, distillation economics, and the
proposed cognitive mesh. Use the
[template catalog](COGNITIVE-LOOP-TEMPLATE-CANDIDATES-2026-09-04.json) for
concrete response and responsibility examples. The earlier
[long-horizon review](LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md)
covers neural recurrence and skill state in more detail. The
[procedural-memory review](PROCEDURAL-MEMORY-PREDICTIVE-STATE-AND-INFORMATION-VALUE-2026-09-04.md)
defines the existing measurement candidates. The
[verification report](../verification/PREDICTIVE-STATE-PROCEDURAL-MEMORY-AND-STAGE-ASSISTANCE-2026-09-04.md)
states what the implementation currently demonstrates.

Sources were selected for a concrete mechanism, a relevant evaluation, or a
formal assumption that affects this design. Recent preprints and older
foundational work are identified separately. Paper results are reported by
their authors and have not been reproduced here. Proposed equations and
experiments below are Loop Engine design synthesis unless attributed otherwise.

## One stable runtime, flexible cognitive responsibilities

The complete classification remains:

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

The reusable role profiles remain:

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
│   ├── Context Intelligence: serve, search, and frame
│   ├── Code Intelligence: resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence: search, replay, and compare
│   └── User Feedback Intelligence: serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

The stable architecture consists of definitions, typed ports, authority,
state revisions, effect handling, model and tool adapters, and event history.
The task-specific structure chooses responsibilities, dependencies,
information exchanges, realization portfolios, and verification boundaries.

Here, *mesh* describes those relationships. It does not imply all-to-all
communication or a new runtime. Every displayed executable vertex is a Loop.
Records and indexes describe or support the work. A reusable
`LoopGraphDefinition` remains a DAG; recurrent work uses later activations and
new state revisions, while recursive work creates bounded delegated Loops.

Useful cognitive responsibilities can be expressed through existing profiles:

| Responsibility | Consumes | Produces | Natural owner |
|---|---|---|---|
| Orientation | Task, authority, observations | Interpretation, unknowns, acceptance questions | Practitioner |
| Attention and sufficiency | Evidence candidates, decision to support | Context request, missing facts, proposed compression | Practitioner with Intelligence queries |
| Analogy | Current responsibility, prior episodes | Mappings, differences, counterexamples | Intelligence comparison plus Practitioner judgment |
| Computation allocation | Contract, candidate realizations, measured risk and cost | One plan or portfolio, escalation and stopping proposal | Practitioner |
| Hypothesis and experiment | Incident, competing causes | Discriminating probe and predicted observations | Practitioner research |
| Execution | Admitted plan and typed inputs | Result, artifacts, observed effects | Solution |
| Critique and verification | Candidate and acceptance contract | Evidence-linked verdict, gaps | Practitioner verifier or Solution validator |
| Repair and integration | Divergence, checkpoint, valid work | Small changed plan and proposed state delta | Practitioner |
| Consolidation and distillation | Outcome-linked historical population | Reusable artifact or policy candidate | Self-improvement Practitioner task |

These are optional responsibilities. A simple transformation can invoke one
reviewed Solution Loop. An unfamiliar task may need orientation, several
probes, multiple branches, and independent verification. A responsibility can
be fused with another when its contract remains observable. A separate Loop is
useful when the work needs its own goal, authority, scheduling, cancellation,
verification, or history identity.

## What the research adds

### Computation is itself a decision

[Selecting Computations](https://arxiv.org/html/1207.5879v1), UAI 2012, studies
the value of computations that improve a later action. Its distinction between
simulation selection and ordinary cumulative-reward bandits matters here. A
Loop choosing another diagnostic computation is optimizing the eventual
decision, including the cost of thinking. One-step estimates can miss useful
sequences of probes; the paper also gives counterexamples to naive stopping
assumptions. Its formal results do not establish an optimal LLM controller.

[FrugalGPT](https://arxiv.org/html/2305.05176v1), 2023, demonstrates learned
model cascades on related training and deployment distributions.
[RouteLLM](https://arxiv.org/html/2406.18665v4), revised February 2025, learns
strong-versus-weak routing from preferences and augmentation. The latter's
Arena-only routers behave near random on some reasoning benchmarks before
relevant augmentation. These results support measuring routing in the actual
task region. Preference wins and verified task success require separate labels.

[BEST-Route](https://proceedings.mlr.press/v267/ding25d.html), ICML 2025,
selects both a model and a sample count. Its proxy reward model selects among
responses. This is a useful precursor to joint allocation, but its scorer is
not an independent task verifier. Its accounting assumptions about shared
input charges and excluded network latency must be replaced with observed
provider behavior in a product experiment.

[Scaling LLM Test-Time Compute Optimally](https://arxiv.org/html/2408.03314v1),
2024, evaluates difficulty-dependent search and revision on MATH. A relevant
limitation is that its expensive difficulty estimation is excluded from the
reported inference comparison. The engineering lesson is to measure the cost
of deciding how much to think, and to test whether another small-model sample
is more useful than escalation. More computation can also exploit an imperfect
verifier.

### Enough context depends on the task and the solver

[Sufficient Context](https://arxiv.org/html/2411.06037), ICLR 2025, separates
retrieval relevance from whether the supplied material supports an answer.
Its results distinguish failures to obtain evidence from failures to use
available evidence. A smaller model can fail even with sufficient context;
a larger model can sometimes answer from prior knowledge with insufficient
retrieved context. Sufficiency should therefore be measured separately from
realization capability. Google's
[June 2026 Agentic RAG account](https://research.google/blog/unlocking-dependable-responses-with-gemini-enterprise-agent-platforms-agentic-rag/)
describes iterative retrieval across sources; that is a deployed design
example, not evidence of Loop Engine performance.

[SKILL.state v3](https://arxiv.org/html/2608.26263v3), revised September 2,
2026, has Google and Purdue affiliations. It carries an immutable skill
specification, current structured state, and latest observation into each
step. This supports explicit state and bounded context experiments. The bound
depends on what the state must retain: an expanding set of entities, unresolved
obligations, or exact artifacts still consumes space. A schema designed for a
known skill can omit information needed after an unforeseen task change.

### Repetition can teach a reusable representation

There is no single established theory called *repeat task theory* that
guarantees universal transfer. Several bodies of work answer different parts
of the question.

[Logan's instance-theory experiment](https://pubmed.ncbi.nlm.nih.gov/1402715/),
1992, models automatic performance as retrieval of prior solutions and tests
reaction-time predictions. This suggests a useful analogy: repeated stable
work can increasingly be served by memory. Its human laboratory results do
not prescribe a power-law learning curve for Loop Engine or establish
transfer to new task families.

[Baxter's inductive-bias model](https://aima.eecs.berkeley.edu/~russell/classes/cs294/f05/papers/baxter-2000.pdf),
2000, gives a learning-to-learn account in which experience across tasks can
improve the bias used on new tasks from the same environment. That environment
assumption is central. A million related instances do not demonstrate
generalization to arbitrary distributions.

[DreamCoder](https://arxiv.org/abs/2006.08381), 2020 preprint and later PLDI
work, alternates program search, reusable library abstraction, and training a
neural search guide. It motivates a direct path from repeated successful
programs to smaller reusable functions. It relies on a suitable language and
executable specifications; arbitrary natural-language tasks do not inherit
those properties automatically.

[Skill Reuse as Compression in Agentic RL](https://arxiv.org/html/2605.31509v1),
May 2026 preprint, shapes successful trajectories using a learned dictionary
of reusable sequences. Its description-length result applies under a fixed
successful-trajectory policy distribution. It does not prove that repeatedly
updating the policy preserves success or transfer. Use compression as one
candidate-discovery signal alongside held-out behavior.

[Break It Down, Pass It On](https://arxiv.org/html/2608.20274v1), August 2026
preprint, compares skill granularity and representation across eleven models
and three environments. Subtask skills help on average while whole-task
skills often hurt; text frequently transfers better than code, with
exceptions. This supports experiments on reusable boundaries rather than
automatically caching whole workflows.
The study induces skills after failed as well as successful tasks; it does
not reproduce Loop Engine's independent qualification process.

### Distillation has several destinations

[Hinton et al.](https://arxiv.org/abs/1503.02531), 2015, establish the use of
teacher distributions to train a student. This can transfer distinctions
beyond hard labels. It requires access to appropriate teacher outputs; an API
that exposes text alone does not supply arbitrary teacher logits.

[Distilling Step-by-Step](https://aclanthology.org/2023.findings-acl.507/),
ACL 2023, uses teacher explanations as supervision for smaller task models.
[Small Models Struggle to Learn from Strong Reasoners](https://aclanthology.org/2025.findings-acl.1301/),
ACL 2025, provides counterevidence to simply using the largest teacher and
longest trace: tested small students can benefit from simpler supervision.
Loop Engine should compare concise decisions, intermediate observable targets,
and verified outputs. Private hidden chain of thought is not a required asset.

[LLM on a Budget](https://arxiv.org/html/2511.11574v1), 2025 preprint,
uses teacher labels and embeddings to train classical classifiers and a small
transformer on two text corpora. This gives a direct route from LLM judgments
to bounded classification. The teacher acts as the oracle, and embedding
inference still costs resources. Independent labels are needed to establish
correctness beyond teacher agreement.

[EVAPORATE](https://arxiv.org/html/2304.09433v1), 2023, compares repeated direct
extraction with generated extraction functions and an ensemble using weak
supervision. Plain synthesized code loses quality in its evaluation. The
combined approach improves the tradeoff. This supports direct LLM-to-code
experiments for repeated extraction, with the original examples and unseen
formats retained as tests.

[DSPy](https://arxiv.org/abs/2310.03714) and
[GEPA v2](https://arxiv.org/abs/2507.19457v2), revised February 2026, optimize
LM programs or prompts against feedback. They offer alternatives to changing
weights. Compilation in this context can still produce a program that calls
an LLM. Candidate search cost, metric quality, and holdout reuse affect the
meaning of any improvement.

[SKALD](https://arxiv.org/html/2608.09826v1), August 2026 preprint, trains a
question-only student from a skill-conditioned teacher view on student
prefixes. Its skill card is absent at deployment. The reported comparison
with contextual exposure also removes that baseline's skill at test time, so
it does not establish superiority over optimized retrieval during inference.
Offline skill construction and teacher scoring belong in the cost ledger.

[Self-Distillation Enables Continual Learning](https://arxiv.org/html/2601.19897v1),
January 2026 preprint, studies demonstration-conditioned self-distillation.
It reports reduced forgetting in its tested sequence, with residual forgetting
and higher training cost than SFT. Continuous improvement should use immutable
candidate versions and measured retention, rather than assuming each update
improves the whole solver.

[On Teacher Hacking](https://arxiv.org/html/2502.02671v1), 2025, constructs a
controlled setting where agreement with a teacher improves while agreement
with its oracle deteriorates. The oracle is another model, which limits the
claim, but the mechanism matters: optimizing teacher imitation can optimize
the wrong target even on held-out prompts.

### Coordination and certainty also consume computation

[Towards a Science of Scaling Agent Systems v3](https://arxiv.org/html/2512.08296v3),
April 2026 revision, evaluates 260 configurations across six benchmarks. It
finds task-dependent benefits and losses from coordination. Its regression
uses measurements obtained from execution, and held-out configurations are
not universal unseen domains. Use it to motivate topology experiments and
coordination accounting, not to install a fixed agent-count threshold.

[Semantic entropy](https://www.nature.com/articles/s41586-024-07421-0),
Nature 2024, groups sampled responses by meaning to detect a subset of
hallucinations. Sampling and semantic grouping have costs. Repeated confident
wrong answers can have low disagreement. This is a diagnostic feature, not a
correctness gate by itself.

[Learn then Test](https://arxiv.org/html/2110.01052v5), revised 2022,
provides finite-sample risk-control machinery for selecting policies with
multiple testing accounted for. Its basic setup uses independent, identically
distributed calibration examples from the target population, with risk and
confidence levels specified in advance. Correlated activations and changed
policies or environments require additional treatment. The guarantee concerns
a population, not certainty about the next answer.

[Conformal LLM Routing](https://aclanthology.org/2026.acl-srw.70/), ACL Student
Research Workshop 2026, is a useful recent routing example. Its harm target is
the cheap model being wrong when the expensive model is correct; both models
being wrong is not that harm event. Our assessment is that pointwise
confidence bounds plus empirically near-monotone risk do not by themselves
justify adaptive threshold selection. Use valid simultaneous testing or a
fixed-sequence procedure before claiming a bound. Evaluate absolute accepted
errors separately from comparative degradation.

## A task has an information state, not a universal difficulty score

For a Loop at time `t`, represent available decision information as:

```text
Decision information
├── Task and output contract, with unresolved interpretation choices
├── Trusted facts and exact source references
├── Speculative hypotheses and their evidence
├── Current observations and execution environment
├── Comparable historical cases, failures, and invalidations
├── Available realizations and verifier capabilities
└── Remaining authority, time, cost, and computation allowances
```

The proposed residual uncertainty is about specific obligations: an unknown
column meaning, a disputed causal explanation, a missing constraint, or an
unverified artifact. Counting tokens or facts is not a measure of how much of
the task is solved. The same evidence can be sufficient for a lookup, but
insufficient for a causal claim.

Let `H` be relevant history, `Z` a compressed working representation, and `Y`
an outcome variable defined for one downstream decision. The
[information bottleneck](https://arxiv.org/abs/physics/0004057) motivates
balancing compression of `H` against predictive information about `Y`.
If `Z` is computed solely from `H`, with no additional informative input,
data processing prevents it from increasing information about `Y` beyond
that contained in `H`. This does not imply that
the compact representation is less useful to a bounded model: it can be
easier to consume and can exclude distracting material.

The deployment test should use task loss:

```text
Task-loss difference(compressed state, fuller history)
  = expected loss using Z
    - expected loss using the authorized fuller-history comparator
```

This signed difference can be negative when compression helps the consumer.
Specify the consumer, data population, estimator, unit, and evaluator. Measure
late-relevant facts, counterevidence loss, extra retrievals, and repair. The
fuller-history comparator also needs verification; it is not an oracle.
Store a recoverable reference to exact material when compacting it. Retrieval
can repair an omission only while the original evidence remains available.

Predictive information measures dependence between selected past and future
variables. It does not measure general intelligence. Shannon surprisal,
Bayesian belief-update surprise, prediction error, and model disagreement
answer different questions. Keep their estimators and meanings distinct.
The [predictive-information paper](https://arxiv.org/abs/cond-mat/9902341)
supplies the theoretical basis, not a universal score for arbitrary transcripts.

## Choose the computation portfolio at the Loop boundary

The proposed selection unit is:

```text
Computation portfolio
├── Semantic contract and required output topology
├── Realization: code, tool, retrieved program, statistical model, or LLM
├── Context strategy and response-program candidate
├── Compute allocation: samples, search, revision, and provider controls
├── Verifier and candidate-selection method
├── Escalation, interruption, and stopping conditions
└── Evidence region and exact version bindings
```

A strong model with concise evidence can cost less than a weak model with a
large context, repeated failed calls, and an expensive verifier. A small model
plus a reliable mechanical check can be the best choice for a narrow stage.
Exact code may be best immediately when the required computation is already
known. Hybrid execution can use a model only for the ambiguous portion and
exact code for the settled transformation.

For a frozen task population `D`, a proposed objective is:

```text
minimize expected total monetary cost of policy pi on D
subject to:
  accepted-error risk on each declared critical task region <= its limit
  service coverage or task utility meets its declared requirement
  required artifact and effect contracts are satisfied
  latency and resource constraints are satisfied
```

Here accepted-error risk is `P(failure | accepted, task region)`. Also report
`P(failure and accepted | task region)` and `P(accepted | task region)`.
A region with no accepted cases has no estimated conditional error rate;
it is not certified safe. Insufficient independent accepted samples leave
the bound unknown. Coverage or task utility must appear in the objective so
rejecting every task cannot qualify as a useful low-cost solver.

Preserve cost, latency, quality, and human effort as separate dimensions unless
the task supplies conversion weights. Include discovery, feature extraction,
embedding computation, routing, failed attempts, verification, repairs,
network delay, and amortized learning. An unpriced provider yields unknown
monetary cost. A hindsight oracle choosing the best observed result is a
diagnostic upper bound, not an available routing baseline.

For an optional computation `c`, one useful approximation is:

```text
VOC_1(c | h)
  = E over its observation [best expected terminal utility after c]
    - best expected terminal utility now
    - expected cost of c expressed in the same utility units
```

The first term includes how the observation changes the eventual choice.
If no conversion weights are available, use the constrained cost formulation
above instead of subtracting unlike quantities.
Information gain alone can reward irrelevant novelty. A short additional
check can have high decision value even when its entropy reduction is small.
Compare a one-step policy with bounded lookahead because two complementary
probes can be valuable together. The controller's own computation must be
budgeted; exact bootstrap settings make starting it finite.

Initially an authorized Practitioner reasons over these proposals. Later a
Loop can first consult a qualified classifier for a bounded region while
retaining an observable escalation path. A low-cost exact computation with a
complete contract need not wait for an LLM to rediscover its algorithm.

### How one task changes its computation

Consider a hypothetical ingestion repair. The user supplies a changed table
and asks to restore a pipeline. Orientation finds that the table structure is
familiar, but two field meanings are uncertain. An Intelligence Query Loop
retrieves earlier schema repairs. Contract comparison accepts a row-accounting
procedure but rejects an old timestamp assumption.

The Practitioner uses exact code to inspect missingness and row identities,
and spends one semantic call resolving the field meanings from current source
documentation. A small structured-output model can propose the mapping once
that evidence is available. A reviewed transform performs the conversion;
an independent check tests the result. If the timestamp meaning remains
ambiguous, the model cannot compensate merely by sounding more certain.

Across later related tasks, a ranker can learn which context sources helped
resolve those ambiguities. A parameterized transform can bypass model
generation for already specified mappings. Changed source semantics return the
work to orientation while preserving verified row inspection. The reusable
part is a bounded capability with applicability evidence, not the original
task's entire graph.

This example illustrates the intended learning target: lower computation
where knowledge is sufficient, additional investigation where it is useful,
and continued flexibility when a familiar input hides a new problem.

## Muscle memory is a selective reusable option

Procedural automaticity means that the system can recognize when a verified
procedure applies, execute it cheaply, notice when it stops applying, and
resume general problem solving. The essential learned object contains more
than the procedure body:

```text
Reusable procedure candidate
├── Initiation conditions and required evidence
├── Typed arguments and parameter invariants
├── Action or computation policy
├── Expected intermediate observations
├── Termination and output contract
├── Interruption and compensation boundaries
├── Known counterexamples, drift, and invalidation
└── General-reasoning continuation when applicability fails
```

The [options framework](https://doi.org/10.1016/S0004-3702(99)00052-1)
provides the initiation, policy, and termination abstraction. The extra
verification and authority fields above are engineering requirements for
Loop Engine. An approved code function is one realization of an option; a
small model or a bounded subgraph can be another.

Test changed reward and changed constraints. A familiar procedure that
continues after the desired outcome changes is a habit failure. Keep fast
episodic capture separate from slower consolidation and qualification. A
failure can teach where an option should abstain even when it teaches no new
successful action.

Pheromone-like path memory can be a projection of observed route utility,
failure frequency, cost, and freshness in an explicit task region. Popularity
alone is not useful credit. Repeated uses inherited from the same solution
lineage are correlated; keep source clusters and effective sample counts.
Decay the relevance of stale evidence, not the historical record itself.

## Fingerprints should predict transfer

Use several representations for different questions:

| Projection | Useful question | Important failure |
|---|---|---|
| Exact occurrence and content digest | Which activation or bytes were used? | Similar inputs must not collapse identities |
| Contract and structured facets | Are inputs, outputs, effects, and assumptions compatible? | Same shape can have different semantics |
| Word and character n-grams | Which error strings, schemas, or procedures overlap? | Surface overlap misses negation and causal differences |
| MinHash, SimHash, LSH | Which candidates are worth inspecting cheaply? | Approximate neighbors and collisions are not equivalence |
| Semantic embeddings | Which responsibilities are analogous? | Similar meaning can require opposite actions |
| Task or behavior probes | Which realizations work on this kind of data? | Probes cost compute and may use unavailable labels |
| Transition or subgraph signature | Which interaction pattern has recurred? | Topology similarity does not preserve environment assumptions |
| Outcome projection | Where has reuse helped or failed? | This activation's future outcomes cannot be decision-time inputs; historical summaries can |

[Task2Vec](https://arxiv.org/abs/1902.03545), ICCV 2019, uses labeled visual
tasks and a probe network's Fisher information to select feature extractors.
It motivates data- and behavior-based task representations. It is not a
label-free universal embedding for all cognitive operations.

Train candidate similarity on transfer utility: did using this artifact
improve this later task after verification? Include hard negatives such as the
same stack trace with a different cause, equivalent table shapes with temporal
leakage, and identical output formats with changed permissions. Keep all
features available before the allocation decision separate from labels
learned afterward. Version the encoder, normalization, vocabulary, index, and
training population; reindex rather than mixing incompatible vector spaces.

## Distillation is a graph of alternatives

The following is an artifact derivation tree, not an executable graph:

```text
Contract + representative inputs + independent outcome evidence
├── Better context and response programs
│   ├── Retrieved examples and compact skill material
│   └── Optimized prompts that still invoke an LLM
├── Smaller learned realizations
│   ├── Prompted small LLM
│   ├── Fine-tuned or adapted small LLM
│   ├── Embedding model plus classifier or ranker
│   └── Classical domain model
├── Compiled realizations
│   ├── Parameterized function, query, or tool
│   ├── Reusable Solution DAG
│   └── Exact algorithm with explicit applicability
└── Allocation and verification support
    ├── Context or response-program ranker
    ├── Escalation-benefit and failure-risk predictors
    └── Selective verification and stopping candidates
```

Any branch can be useful without passing through the others. A new failure can
send work back to a more expressive realization. Learned models implemented
with reproducible inference remain empirical approximations; reproducibility
does not prove that their semantic output is correct. Compiling an exact
algorithm requires a specification and tests or a proof appropriate to it.

For each training example, bind the decision-time features, candidate options,
teacher output, admitted choice, action, observation, independent check,
downstream use, cost, and later corrections. A teacher preference is a
preference target. A route choice is an imitation target. Verified task loss
is an outcome target. Keep these distinct when training or comparing models.

Teach extraction, context ranking, route benefit, and error classification
before attempting to distill the universal semantic answer. For a domain
model, targets can instead be classification, regression, forecasting,
ranking, anomaly detection, or calibrated uncertainty, with task-appropriate
splits and metrics. Data preparation and hyperparameter search are themselves
Loop-owned experiments with costs and provenance.

### When training pays for itself

For a horizon ending at the next requalification, use this proposed
constant-average-cost approximation:

```text
C_candidate(N) = F + M + N * [g + (1-a)*b + a*(s + v + f*b)]

N_break_even = (F + M) / [a*(b - s - v - f*b) - g]
```

`F` is data, teacher generation, training or synthesis, search, qualification,
and deployment cost. `M` is maintenance across the horizon. `g` is gating and
shared feature cost per request. `a` is the fraction routed to the candidate.
`N` counts incoming requests; expected candidate executions are `a*N`.
`b` is baseline cost including its verification and repair at matched service
quality, `s` candidate execution, `v` candidate verification, and
`f` escalation probability after candidate execution. Use conditional costs
when escalated tasks differ from the baseline average. If the denominator is
nonpositive, this candidate does not amortize under the assumed traffic.
It may still be worth testing for a separately declared quality, latency, or
locality objective; that is a different optimization claim.

Illustration only: with `F + M = $60`, `g = $0.001`, `a = 0.6`,
`b = $0.10`, `s + v = $0.01`, and `f = 0.1`, savings are `$0.047` per
incoming request. Break-even is about 1,277 requests. These invented values
are not model prices or Loop Engine results. Qualification still has to meet
the declared quality requirement.

### Training adapters must remain replaceable

OpenAI's current
[SFT documentation](https://developers.openai.com/api/docs/guides/supervised-fine-tuning)
describes distilling suitable larger-model responses into a smaller model and
requires evaluation first. It also says its self-serve fine-tuning platform is
winding down. The
[deprecation schedule](https://developers.openai.com/api/docs/deprecations)
limits new training by account history and lists January 6, 2027 as the end of
new jobs for active existing customers. It separately schedules changes to
the Evals platform. Availability was checked on this note's date; account
access was not probed.

Keep dataset manifests, local evaluation, model artifacts, and qualification
inside Loop Engine's provider-neutral contracts. An open-weight training
backend or another qualified service can supply a realization. Training
availability is a capability fact, not an architectural constant.

## Continuous improvement needs multiple clocks

```text
Improvement timescales
├── Within an activation: observe, revise, verify, and stop
├── Across activations: checkpoint state and update scoped episode memory
├── Across tasks: identify transfer, counterexamples, and reuse candidates
├── Across training rounds: fit, calibrate, qualify, and version realizations
└── Across deployment periods: monitor drift, invalidate, and requalify
```

Each clock produces finite work. The faster clock may propose changes to the
slower one, but cannot approve its own candidate. Neural test-time learning,
external memory updates, prompt evolution, and persistent state revisions
must remain distinct operations with different rollback behavior.

Freeze deployed policy versions during an evaluation epoch. Record candidate
sets, selection probabilities where applicable, and rejected options. Random
exploration can provide counterfactual evidence only within its authorized
scope. Importance weighting requires support and correct propensities; it
cannot reconstruct the result of an action the behavior policy never tried.
Routing that changes later states needs trajectory-level evaluation, beyond
a one-step contextual-bandit approximation.

Use chronological streams, held-out sources, held-out task families, and
retained old capabilities to measure transfer and forgetting. Separate
beneficial reuse from reduced exploration. The ACL 2026 study
[Demystify the Role of Memory in Machine Learning Engineering Agents](https://aclanthology.org/2026.findings-acl.525/)
reports different effects for sequential repair and tree-search agents.
Memory policy and graph structure must therefore be tested together.

Measure coverage alongside accuracy: abstaining on almost everything can
make accepted answers look excellent while making the solver unhelpful.
Report risk on selected traffic, unconditional harmful outcomes, task utility,
and group-specific performance. Fixed-sample bounds must not be reused after
repeated threshold search or continuous peeking without valid corrections.

## Templates and response formats should make decisions easier

The accompanying catalog provides twelve proposed cards. Each has a cognitive
responsibility, existing profile suggestion, required input meanings,
suggested payload schema, completion condition, interruption conditions, and
measurable outcome. The catalog is outside runtime registries. Its schemas
validate shape only and its profile references remain unbound to exact
definition digests until a future integration.

Use one small envelope plus a selected payload. Keep invocation identity,
evidence references, and disposition stable. Permit additional semantic
fields and template replacement. Negotiate a changed consumer contract before
executing downstream work; a model cannot silently remove a required output.

```text
Proposed template families
├── Understand: orient, assess sufficiency, map analogy
├── Decide: allocate computation, compare candidate solutions
├── Perform: execute a typed transform with an artifact result
├── Check: verify and diagnose a discrepancy
└── Improve: design an experiment, consolidate a procedure, train a candidate,
    and assess qualification
```

Use records for bounded decisions, hypothesis tables for diagnosis, matrices
for alternatives, DAGs for dependencies, patches for state changes, and
artifact manifests for exact bytes. A useful output-format selector is trained
against downstream consumption and repair cost. It should not reward verbose
JSON merely because it is syntactically valid.

## Quality of life should reduce cognitive and operational work

| Product improvement | Concrete behavior | Measure |
|---|---|---|
| Decision explanation | Show why a route was eligible, what evidence supports it, and the next escalation | Unnecessary reruns and operator corrections |
| Context inspection | Show included sources, omissions, unresolved facts, and exact hydration links | Lost-evidence repairs and context cost |
| Incumbent preservation | Keep the last verified artifact visible while challengers run | Time to first usable result |
| Local repair | Retry publication or one failed transform from its checkpoint | Preserved verified work and duplicate effects |
| Memory correction | Mark a prior invalid, identify dependent candidates, rebuild affected projections | Time to quarantine stale advice |
| Experiment replay | Reconstruct one stage's inputs, treatment, evaluator, and outcome | Reproduction rate and comparison validity |
| Template preview | Show payload fields and the consumer contract before use | Admission and downstream formatting failures |
| Resource view | Separate spent, estimated, reserved, and unknown cost; show queues and critical path | Budget surprises and idle compute |
| Session continuity | Open a compact current-state map with links to exact evidence | Reorientation time and repeated investigation |

An unattended monitor can raise a typed event when repeated state, contradictory
evidence, or budget pressure appears. The owning Loop decides whether to
change granularity, retrieve, replan, repair, ask a material question, or stop.
The operator should be able to inspect that decision at the stage where it
occurred.

## Mapping to the repository

These are integration targets, not new architectural planes:

| Existing boundary | Relevant current asset | Next extension to test |
|---|---|---|
| `loop.loop_definition`, `loop.loop_profile_catalog` | One runtime and versioned profiles | Bind selected cognitive cards to exact existing definitions |
| `core.choice`, `core.semantic_decision` | Proposed options, adjustments, new options, decision records | Joint realization/context/verifier allocation payload |
| `core.model_demand`, `core.model_routing_selector` | Advisory route histogram and deterministic bootstrap selection | Measured escalation benefit and total-cost proposals |
| `core.template_negotiation`, `core.llm_work_packet` | Negotiable shapes and model packet | Outcome-linked response-program selection |
| `core.skill_state_context`, `core.context_budget` | State and context mechanics | Sufficiency probes and adaptive evidence hydration |
| `core.ngram_retrieval`, `core.task_similarity_engine` | Candidate retrieval representations | Compare lexical, embedding, contract, and behavior features |
| `core.information_theory_evidence`, `core.state_policy_evidence` | Offline measurement candidates | Resolve real populations and outcomes through Run History |
| `memory.procedural.control_assessment` | Candidate procedural control probes | Measured initiation, interruption, devaluation, and fallback |
| `core.stage_action_lineage`, `core.solve_control_manifest` | Mechanism-only product assistance evidence | Canonical stage pair with realized controls and independent evaluator |
| `core.self_tuning`, `core.prompt_experiment` | Versioned setting experiments | Calibrated policies with complete cost and outcome targets |
| `core.reusable_capability_flywheel` | Governed capability lifecycle | Direct text-to-code and small-model realization comparisons |
| `core.reactive_scheduler`, `core.reactive_worker` | Finite reactive activations and leases | Scheduled consolidation and drift checks as ordinary Loop work |

Source inspection found a specific assumption to retire during the allocation
work: `model_demand.py` describes starting too cheaply as only causing a slower
correct answer. An incorrect result can pass a weak verifier. The current
histogram also uses fixed observation and success-share thresholds and a
lossy `helped` projection. These are bootstrap heuristics, not an estimate of
minimum sufficient computation or a bound on false acceptance.

## Experiments that can decide the design

| Experiment | Intervention and control | Evidence needed before adoption |
|---|---|---|
| E0: valid assistance | One frozen semantic checkpoint, relevant prior versus fresh | Actual packets, canonical assignment, executed action, independent evaluation, rebuilt projection |
| E1: realization portfolio | Strong baseline, small model, cascade, exact code where applicable, and joint allocator | Matched acceptance requirements; include router, verifier, and failed-attempt costs |
| E2: information sufficiency | Full authorized evidence, compressed state, retrieval-on-demand, sufficiency-guided retrieval | Missing-fact recovery, answer loss, call count, and late-relevance stress cases |
| E3: procedural transfer | Whole-task versus subtask skills; text versus code; no memory control | New sources and families, changed constraints, interruption, and negative transfer |
| E4: distillation destination | Direct teacher-to-small-model, teacher-to-classifier, and teacher-to-code | Independent labels, training cost, lifetime traffic, and break-even interval |
| E5: skill placement | Retrieval at inference, optimized prompt, weights only, and weights plus retrieval | Equal teacher-data and compute accounting; no training-only advantage in one baseline |
| E6: controller value | Fixed budget, one-step VOC, bounded lookahead | Controller overhead and complementary-probe cases |
| E7: mesh topology | One Loop, delegated parallel work, critic, and ensemble | Task decomposition, correlation, communication cost, selected-result quality |
| E8: continual change | Frozen candidate versus scheduled updates | Forward transfer, retained old tasks, drift, coverage, and requalification cost |

E0 remains the prerequisite for claiming benefit from prior-stage assistance.
Dataset preparation, template design, and offline research can proceed in
parallel. Broader Kaggle experiments should follow the existing five-task
pilot and staged campaign gates once E0 is valid. A memory or compute policy
should earn adoption in a declared region, with its exceptions documented.

For each experiment, save a population manifest, exact artifact and model
versions, decision-time features, treatment assignment, verifier contract,
failure accounting, and full cost record. Separate policy training,
calibration, and final testing. Use a predeclared comparison rule or a valid
sequential design. Report confidence intervals over independent source or task
clusters, not duplicated activations treated as independent tasks.

The first useful deliverable is a measured choice between several realizations
of one contract. That result can support a small allocation model. Repeating
this process across varied responsibilities creates a growing library of
scoped capabilities while the Practitioner retains an open path for unfamiliar
work.
