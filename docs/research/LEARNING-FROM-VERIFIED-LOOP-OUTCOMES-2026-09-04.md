# Learning from verified Loop outcomes

Research date: 2026-09-04. Audience: Loop Engine implementers and reviewers.
Scope: information-based learning, adaptive computation, memory and skill
reuse, and the evidence needed before those mechanisms can control work.

The useful next step is to measure whether the system's predictions and
decisions are correct before letting confidence, similarity, or repetition
choose cheaper execution. This session implements prerequisites at the
existing verification, adaptive-state, model-demand, and information-evidence
boundaries. It does not complete the live paired-assistance gate.

The repository remains the authority for implementation. Papers supply
candidate mechanisms and evaluation designs. No external performance result
was independently reproduced in this session.

## Architecture and interpretation

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by,
    │                 Retrieved by, or Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when permitted
    └── Run History records
```

The four persistent intelligence layers remain Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence. Functional domains, negative experience, social context, and
the "muscle memory" analogy do not create additional runtime classes or
replace those layers. The current memory registry still has working,
episodic, semantic, and procedural types.

A cognitive mesh is a hypothesis about useful composition. Multiple roles
using the same model can share errors. The recent multi-agent comparison
examines six centralized designs and finds that costly orchestration often
fails to improve over simple sampling baselines. It also finds useful
decomposition cases, so it does not establish that every mesh is wasteful.
Loop Engine should measure the marginal contribution and complete cost of
each activated branch. [Jwalapuram et al., 2026](https://arxiv.org/html/2606.13003v1).

## Four quantities that must stay separate

| Quantity | Required definition | Invalid interpretation |
|---|---|---|
| Predictive loss | A probability distribution, declared outcome support, and independently observed outcome | Low entropy means correct |
| Information gain | A named uncertain variable, coherent prior and prospective observation model | Realized surprise is expected information gain |
| Decision value | Alternatives, consequences, horizon, probabilities, and a common utility unit | Bits can be added directly to dollars or task score |
| Economic benefit | Full generation, retrieval, training, verification, repair, and coordination costs | A smaller memory bank or fewer frontier calls proves savings |

The implemented categorical scorer computes multiclass Brier loss and
base-two log loss. Its bounded normalization divides multiclass Brier loss
by two. It refuses outcomes outside the declared support and represents a
zero-probability realized event as infinite log loss using a flag, not JSON
Infinity or arbitrary clipping. These are proper scoring rules for supplied
distributions, not proof of calibration or forecast-before-outcome ordering.
[Gneiting and Raftery, 2007](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf).

Information bottleneck objectives preserve information about a declared
relevance variable. They do not make an embedding or short summary
automatically sufficient for future tasks. Predictive-state representations
likewise need specified action-observation tests and a system model. Test a
compressed state against held-out future observations and task loss, not
only in-sample information estimates.
[Tishby, Pereira and Bialek](https://arxiv.org/abs/physics/0004057),
[Littman, Sutton and Singh, 2001](https://proceedings.neurips.cc/paper/2001/file/1e4d36177d71bbb3558e43af9577d70e-Paper.pdf).

Expected information acquisition and value of computation are different
questions. The latter concerns improvements to the eventual decision after
paying for computation. An informative observation can have no decision
value when it changes no preferred action. A cheap one-step probe can also
miss the value of complementary later probes.
[Lindley, 1956](https://projecteuclid.org/euclid.aoms/1177728069),
[Howard, 1966](https://doi.org/10.1109/TSSC.1966.300074),
[Hay et al., 2012](https://people.eecs.berkeley.edu/~russell/papers/uai12-meta.pdf).

## Primary-source findings and repository experiments

The following rows summarize focused methods and limitations review.
Adaptations and falsifiers are proposed by this review. Their maturity is
DESIGNED unless the implementation section says otherwise.

| Source | Reported evidence and transferable pattern | Assumption mismatch or failure | Existing boundary and falsifying experiment |
|---|---|---|---|
| [ToolGate, Liu et al., Jan 2026](https://arxiv.org/html/2601.04688v1) | Contract-checked tool state; ToolBench and MCP-Universe evaluation includes model judging. | Guarantees assume sound contracts. The tool-state gate is not final-answer verification; legitimate empty results can be mishandled. | `semantic_state`, `effect_approval`, response admission. Inject valid empty results, unsupported facts, and wrong final answers. Reject adaptation if any required invariant is bypassed. |
| [Agent JIT, Winston et al., May 2026](https://arxiv.org/html/2605.21470v2) | Validated tool plans and latency-aware scheduling across 37 web tasks, three trials/configuration. | Considerable synthesis/tracing setup; some tasks were curated by scheduling regime. Stale DOM and hedged effects matter. | Capability harvest/resolution and delegation. Charge cold setup, failed hedges, and verification. Reject if savings vanish or effects duplicate. |
| [λ-RLM, Roy et al., Mar 2026](https://arxiv.org/html/2603.20105v1) | Typed bounded Split/Map/Reduce composition; nine open-weight models on four task sets. | A prebuilt task menu chooses plans. Guarantees assume terminating leaves and valid combinators; some direct baselines truncate inputs. | `LoopGraphDefinition`, delegation, context artifacts. Use an external-context baseline and cross-chunk dependency tests. Reject if aggregation loses necessary relationships. |
| [AFTER, Belikova et al., Jun 2026](https://arxiv.org/html/2606.23127v1) | 382 tasks, six roles, 22 skills; executable partial/full checks expose negative transfer. | Skills are supplied rather than retrieved. In-role improvement can become cross-role regression. | Procedural controls and capability qualification. Freeze skills, split by task/role/model, and compare actual retrieval with oracle selection. Reject broad promotion on subgroup harm. |
| [SKILL-KD, Shi et al., Aug 2026 v2](https://arxiv.org/html/2607.28048v2) | Contrast student failure with teacher traces, test patches, consolidate text skills across five benchmarks. | This is textual prompt distillation, not weight training. Same-training-instance rerun success admits patches; full skill files are injected. | Exact outcome lineage and candidate harvest. Compare equal-budget teacher/student/contrast controls on unseen tasks. Reject if gains are retry luck or benchmark-format memorization. |
| [SkillGenBench, Zhou et al., May 2026](https://arxiv.org/html/2605.18693v1) | 187 repository/document tasks with fixed executor and multiple skill generators; generated skills can lose to no-skill. | Population construction favors tasks needing corpus/skills; artifact evaluation can include a model judge; pass@3 hides first-attempt cost. | Code-asset qualification and context retrieval. Use source-commit holdouts, no-skill/raw-source controls, pass@1 and hidden execution tests. Reject hindsight-only benefit. |
| [VG-Search, Chen et al., Oct 2025 v2](https://arxiv.org/html/2505.11730v2) | Math/code search experiments count generator and verifier compute; verifier frequency affects pruning efficiency. | Search-guiding scores are not effect authorization. Granularity is fixed within each problem; oracle-selected and validation-selected values differ. | Search and verification policy. Vary optional search scoring while keeping mandatory gates fixed. Reject savings that disappear with verifier cost or prune useful branches. |
| [Differentiable MoA, Wu et al., May 2026 v2](https://arxiv.org/html/2605.15706v2) | Embedding/GRU router with dense warmup and sparse later activation across nine benchmarks. | Optimization uses token confidence, not independent task utility. Pool access, logits, warmup and summarization have costs. | `model_demand`, delegation and scheduling. Match total cost and include confidently wrong specialists. Reject if confidence rises while verified quality falls. |
| [UCCI, Kotte, May 2026](https://arxiv.org/html/2605.18796v1) | Proposes calibrated uncertainty and constrained cascade thresholds on NER. | Cost equations charge one model although small-model output supplies uncertainty; exact-match calibration and micro-F1 objectives need reconciliation. | Treat as contested exploratory input. Recompute both-model and verifier cost with one consistent loss. Do not import its headline saving or optimality claim as an established guarantee. |
| [ToolLibGen, Yue et al., Oct 2025](https://arxiv.org/html/2510.07768v1) | Clusters and refactors trace-derived functions into searchable libraries; QA evaluation includes seen and unseen settings. | Refactoring review does not prove universal behavioral equivalence. Seen-question selection and bounded refinement affect evidence. | Code Intelligence harvest/admission. Test fragmented, clustered and refactored candidates with hidden property tests. Reject if consolidation loses rare correct behavior. |
| [Auto-Dreamer, Ye et al., May 2026](https://arxiv.org/html/2605.20616v1) | Learns offline consolidation using downstream return and randomized memory masking, with frozen-agent evaluation. | Memory-token reduction excludes full lifecycle cost. Masking value depends on entry granularity; task-order uncertainty remains. | Memory learning cycle and procedural controls. Retain originals; compare whole-bank regressions, poisoning and task-order shifts. Reject destructive compression or missing total-cost benefit. |
| [PACE acceptance, Shawn, Jun 2026](https://arxiv.org/html/2606.08106) | Paired betting test on Qwen prompt evolution across three small benchmarks. | The stated guarantee is per candidate under conditional fairness, not indefinitely reused holdout or run-level false-commit control. | Experiment and promotion boundaries. Freeze each candidate; use fresh paired units and an explicit cross-candidate error budget. Reject if adaptive reuse invalidates coverage. |
| [PACE two-timescale, Ling et al., May 2026](https://arxiv.org/html/2605.23019) | Separates frequent prompt changes from higher-risk control edits across three small models and four controlled benchmarks. | Dynamic validation samples reuse the training pool; limited seed coverage. Arbitrary control edits need stronger isolation here. | Self-improvement Practitioner. Compare prompt-only/control-only/two-timescale arms with untouched source-family holdouts and old-task regressions. Reject increased false acceptance. |
| [MalSkillBench, Guo et al., Jun 2026 v3](https://arxiv.org/html/2606.07131) | 3,944 malicious and 4,000 benign skills, with runtime monitoring and a model judge in construction. | Generated attacks and judge errors affect ground truth. Aggregate recall can hide prompt/control attack failures. | Skill admission, effect gates and provenance. Test code, instructions, mixed attacks and benign matches separately. Reject undeclared effects or unacceptable false positives. |

The full source matrix also records foundational scoring, confidence
sequences, information value, metareasoning, predictive state, and the
multi-agent disconfirmation study. It separates source facts from repository
proposals. The seed catalog distinguishes methods review from metadata-only
checks and inaccessible text.

Read the [machine-readable source matrix](../evidence/learning-integrity-20260904/research-matrix.json)
and [seed coverage](../evidence/learning-integrity-20260904/seed-coverage.json).
The [implementation and verification report](../verification/LEARNING-INTEGRITY-AND-RESEARCH-2026-09-04.md)
records what actually changed and what remains open.

## Repeated improvement needs a separate acceptance design

Do not accept every variant whose observed score rises. Time-uniform
confidence sequences support repeated looks only under their stated
statistical conditions. Adaptive task or route selection creates a different
problem: naive means can be biased, and small propensities can make weighted
estimates unstable. No confidence interval has been added to the current
bootstrap ladder. [Howard et al., 2021](https://www.imstat.org/publications/aos/aos_49_2/aos_49_2.pdf),
[Hadad et al.](https://arxiv.org/abs/1911.02768).

| Collection design | Permitted next claim | Required additional evidence |
|---|---|---|
| One supplied forecast and outcome | Descriptive Brier/log loss | Real forecast-before-outcome event and evaluator linkage |
| Fixed source-cluster holdout | Paired region-specific loss comparison | Preregistered population, sample size, exclusions, tolerance and interval assumptions |
| Repeated looks at one frozen candidate | Optional-stopping-safe evidence only with an appropriate method | Fresh sequential units, filtration, bounds, level and stopping rule |
| Many adaptive candidate proposals | No automatic run-level guarantee | Cross-candidate error control and an untouched audit population |
| Adaptively selected tasks/routes | Descriptive outcomes until a valid estimator exists | Decision-time propensities, support, target policy and dependence assumptions |

## Map the research to the existing components

| Component | Next experiment | Reject or narrow the adaptation when |
|---|---|---|
| Task/frontier | Small explicit action-conditional forecast before a probe | Forecast cannot be linked to its later outcome, or selection increases unresolved work |
| Context compiler | Full history versus structured state with selective rehydration | Smaller context worsens held-out loss, false acceptance, or recovery |
| Fingerprints/retrieval | Facet, n-gram, embedding and hybrid candidates with contract filters | Recall gains do not improve downstream outcomes or negative transfer rises |
| Response programs | Minimal envelope versus fixed versus negotiated structure | Schema overhead increases without consumer benefit, or fields constrain valid novel answers |
| Model allocation | Small-first and strong-first on the same frozen stage population | Savings disappear after escalation, verifier, failure and controller costs |
| Verification/state | Exact subject-bound verdict and typed accepted/candidate separation | A foreign verdict, failed artifact, or missing evidence creates success |
| Recovery | Diagnosis plus discriminating probe against bounded retry baseline | Repair destroys valid work, repeats an unchanged failure, or misses termination conditions |
| Procedural memory | Frozen skill/capability versions across source and role holdouts | In-region gain becomes cross-region harm or an interrupted procedure cannot escape |
| Distillation | Low-risk forecast/context/response ranking in shadow | Teacher agreement rises without verified utility, or OOD cases fail to abstain |
| Self-improvement | Candidate proposer separate from acceptance and promotion | Reused evaluation data creates spurious improvements or a candidate approves itself |
| Storage/replay | Rebuild measurements from intact committed history | Caller-provided identities or lost records change conclusions silently |
| Campaign | Progress through mixed-shape gates after one valid pair | Downloads or artifact presence substitute for verified task outcomes |

This is a component research map, not proof that every function has a learned
policy. The earlier whole-corpus audit remains the file and local-history
inventory; this session does not repeat or expand its semantic coverage claim.

## Official OpenAI features stay at the adapter boundary

Official documentation was checked on the research date. Documented support
does not establish account access or Loop Engine integration.

| Feature and official source | Repository-neutral meaning | Required qualification |
|---|---|---|
| [Astra model](https://developers.openai.com/api/docs/models/gpt-6-astra) and [model guidance](https://developers.openai.com/api/docs/guides/latest-model) | Versioned interpreter capability profile | Exact route/account probe, output contract, tools, settings and measured cost; keep current quarantine until qualified |
| [Async tool calling](https://developers.openai.com/api/docs/guides/async-tool-calling) | A pending owned operation with a stable call ID | The application still runs and tracks work; test cancellation, late/duplicate results, resume and isolation |
| [Programmatic tool calling](https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling) | Physical composition of authorized operations | Preserve logical calls, individual effects, accounting and observations |
| [Sandbox agents and Manifest](https://developers.openai.com/api/docs/guides/agents/sandboxes) | Execution environment and fresh-session workspace contract | Beta adapter contract, exact mounts, dependency/source identity, snapshots and effect confinement; do not introduce a second Loop runtime |
| [Compaction](https://developers.openai.com/api/docs/guides/compaction) | Opaque provider continuation material | Preserve external canonical state and exact returned context window; do not parse internal reasoning or infer state sufficiency |
| [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) | Physical prefix reuse | Pin effective instructions/settings, record actual usage and cache behavior, and prevent assistance leakage into a fresh arm |
| [Record & Replay](https://learn.chatgpt.com/docs/extend/record-and-replay) | Demonstration-derived skill candidate | The documented workflow requires macOS and Computer Use; skill replay uses available tools and does not promise deterministic zero-model execution |

The inspected official documentation does not establish that Astra uses a
particular recurrent neural architecture. Async tools, compaction, caching,
and stateful continuation must not be mistaken for neural weight updates.

## What was implemented and what still blocks the live pair

Implemented changes are recorded in the companion verification report:
subject-bound verification records and history checks; accepted-versus-attempt
state separation; exact emitted-project success checks; conservative failed
artifact invalidation; per-route bootstrap evidence thresholds; and proper
categorical forecast scoring.

These changes are prerequisites, not a substitute for the paired experiment.
The control contract remains `mechanism_only`. Immutable source/tree capture,
canonical trial allocation, realized treatment-free base-packet comparison,
complete contamination checks, independent evaluation, and projection rebuild
from committed product evidence remain open. No live assistance pair or new
Kaggle solve is claimed.

The highest-information next action is the immutable source/control boundary:
freeze authorized local bytes and directory trees, store remote inputs as
immutable artifacts, bind those snapshots to one preallocated pair, and
reject time-of-use drift. Then verify both actual base packets before making
bounded live calls. Broad campaign expansion remains gated.

## Coverage and limitations

Two independent research lanes examined 22 papers or foundational sources in
detail, including one additional skeptical multi-agent evaluation. Other
named seeds received identity/abstract checks; Logan's full primary text was
inaccessible. The complete blackboard/actor/process-calculus and every listed
vendor/evaluation workstream have not received exhaustive methods review.

The coordinator re-opened consequential sources, checked the implemented
scoring formulas, and reviewed official adapter documentation. Publisher and
benchmark-version disagreements remain explicit rather than averaged away.
InfiAgent-DABench and DAComp counts differ across versions, so a campaign must
pin the exact dataset and evaluator revision.

Research stopped after the evidence supported this bounded implementation
choice and identified the next experiments. No paper's reported quality,
cost saving, safety coverage, or generalization was reproduced here. No AGI,
universal success, million-task, calibrated router, or qualified shortcut claim
is made.
