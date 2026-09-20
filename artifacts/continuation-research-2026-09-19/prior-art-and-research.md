# Prior art for harness intelligence and verified reuse

Research date: September 19, 2026. Kind: source review and proposed experiments.
This document does not change a contract, qualify an implementation, authorize
provider calls, or assert a new research contribution.

The central ideas have substantial prior art. Dynamic skill loading, executable
memory, model-created tools, feedback-based harness changes, dependency graphs,
and cost-based implementation selection have each been demonstrated in bounded
settings. The strongest useful product hypothesis for Loop Engine is that it
can deliver compatible, independently admitted material to an existing harness
and show when that material improves the customer's verified outcome. That
hypothesis still needs integrated evidence.

The immediate public product considered here is paid harness-intelligence
distribution through the Model Context Protocol and an application programming
interface. The customer runs the harness. Internal construction, decomposition,
qualification, cost measurement, and reuse still need to work through the full
engine. A narrower public interface does not remove those internal obligations.

## Scope and evidence rules

Observed local starting point: branch `main`, revision
`48cc954322691e492aad69a465ba470a112730e7`, with pre-existing changes and other
Codex processes. This research did not change their files. Local orientation
used the [recovered session review](../claude-session-review-2026-09-19/README.md),
the [session digest and research inventory](../../docs/context/AGENT-SESSION-DIGEST-AND-RESEARCH-INVENTORY-2026-09-18.md),
the [provisioning standards research](../../docs/research/HARNESS-PROVISIONING-STANDARDS-2026-09-18.md),
the [reusable capability authority map](../../docs/architecture/REUSABLE-CAPABILITY-AUTHORITY-AND-RESEARCH.md),
the configuration requirements, and the current advisory comments in
[ASTRA.md](../../ASTRA.md).

The recovered review establishes component and integration gaps. Its findings
were not independently rerun by this research assignment. External results
below are author-reported evidence, not reproduced measurements and not a
comparison against Loop Engine. A paper version is pinned where observed.
Repository links describe the pages inspected on the research date; a commit
identity was not recovered for those external repositories.

Each source entry separates resemblance, evidence, limitation, design inference,
and a discriminating test. Where exact executable versions or full populations
were not recovered, this is stated. Such entries support mechanism selection,
not a reusable numeric performance claim. All proposed experiments require
their own declared authority before execution.

## What the evidence changes

1. Qualification should measure the material's marginal benefit. A correctly
   downloaded and loaded skill can still reduce task success. A suitable
   no-additional-material treatment is necessary when the assignment permits it.
2. Executable reuse and a retrieved description are different interventions.
   Test whether a qualified implementation actually replaces repeated work.
3. Selection must consider the complete combination of task, material, harness,
   model, dependencies, and execution environment. Popularity and a broadly
   matching description do not establish compatibility or benefit.
4. Search performance and final qualification need separate populations.
   Repeatedly selecting a winner on one benchmark makes that benchmark part of
   development, even if no task answer appears in the resulting code.
5. Small graphs remain useful for independent contracts, observation, reuse,
   and repair. The physical execution plan can still batch compatible work.
   More decomposition and less decomposition are both experimental choices.
6. Distribution reliability, material quality, selection quality, native
   loading, and task acceptance need separate evidence. A digest establishes
   identity; it does not establish any of the other properties.

## Eighteen closely related research families

### 1. Anthropic Agent Skills

Barry Zhang, Keith Lazuka, and Mahesh Murag, [Equipping agents for the real
world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills),
October 16, 2025, with a December 18, 2025 open-standard update.

- Similarity: task specialization through dynamically selected instructions,
  scripts, and resources, with metadata followed by deeper material.
- Evidence: an official engineering account describes actual document skills,
  discovery, file loading, and running scripts without loading their bodies
  into model context. This is implementation evidence, not a controlled
  cross-task benefit estimate.
- Missing or contrary: the format and example do not establish independent
  capability admission, universal harness compatibility, or automatic safe
  self-promotion. Deterministic execution can consistently compute a wrong
  function.
- Design inference: distribute exact material plus compatibility and admission
  evidence; keep those stronger guarantees outside descriptive Markdown.
- Test: deliver the same admitted package to two pinned native harnesses and
  observe discovery, exact loaded files, execution, and independent output
  acceptance separately. Include an irrelevant but well-written package.

### 2. Anthropic code execution with the Model Context Protocol

Adam Jones and Conor Kelly, [Code execution with MCP: Building more efficient
agents](https://www.anthropic.com/engineering/code-execution-with-mcp),
November 4, 2025.

- Similarity: discover tool interfaces on demand, perform bulk processing in
  code, and retain useful functions as reusable skills.
- Evidence: the official article supplies concrete typed-interface and
  data-transfer examples. Its large token reduction is an illustrative
  workflow claim, not an end-to-end benchmark with a frozen task population.
- Missing or contrary: generated code needs a secure execution environment;
  discovery and tool composition add their own cost. Moving data outside the
  model does not authorize a new destination or side effect.
- Design inference: the paid server can deliver interfaces and reviewed
  reusable code while execution remains in the customer's declared workspace.
- Test: compare direct calls, client-side composed code, and a previously
  qualified procedure on identical inputs. Count discovery, generation,
  validation, transfer, and recovery. Test an effect that must execute once.

### 3. SkillsBench

Xiangyi Li and colleagues, [SkillsBench](https://arxiv.org/html/2602.12670v4),
arXiv `2602.12670v4`, June 14, 2026; first submitted February 13, 2026.

- Similarity: directly evaluates whether packaged procedural material improves
  a native harness's task completion.
- Evidence: the current study contains 87 tasks across eight domains, paired
  conditions, deterministic verifiers, and 18 model-harness configurations.
  Its fixed trial frame is three repetitions per task and condition. It reports
  overall curated-skill benefits and substantial dependence on configuration.
- Missing or contrary: task-level harm and self-generated-skill failures remain.
  Native loading does not guarantee resolution. The representative version
  table names models and harnesses but does not give numeric harness releases;
  exact reproduction would require the released run manifests. Terminal tasks
  do not establish long-running multi-agent or graphical-interface behavior.
- Design inference: make a versioned paired evaluation part of a package's
  evidence, with negative transfer visible.
- Test: repeat paired qualification on Loop Engine's admitted task families,
  then confirm on untouched tasks and a second compatible harness.

### 4. Evaluating AGENTS.md

Thibaud Gloaguen, Niels Mündler, Mark Müller, Veselin Raychev, and Martin Vechev,
[Evaluating AGENTS.md](https://arxiv.org/html/2602.11988v2), arXiv
`2602.11988v2`, June 23, 2026; first submitted February 12, 2026.

- Similarity: repository instructions are one of the resources provisioning
  would select and compose.
- Evidence: tests 300 SWE-bench Lite tasks and 138 CTXbench instances with
  generated, developer-provided, and absent context. Pairings include Claude
  Code with Sonnet-4.5, Codex with GPT-5.2 and GPT-5.1 mini, and Qwen Code with
  Qwen3-30b-coder. Task success uses execution tests; exact harness releases
  were not established in this review.
- Missing or contrary: instructions are often followed without improving
  success; repository overviews can cause unnecessary work. The study does
  not justify removing mandatory project constraints.
- Design inference: supply necessary nonstandard practices and task-relevant
  knowledge, then measure optional additions.
- Test: preserve required authority and correctness rules in every treatment;
  separately add navigation summaries, procedures, and optional process
  requirements. Measure benefit and the extra work each causes.

### 5. SWE-Skills-Bench

Tingxu Han and colleagues, [SWE-Skills-Bench](https://arxiv.org/html/2603.15401v1),
arXiv `2603.15401v1`, March 16, 2026.

- Similarity: qualification of reusable skills on repository work.
- Evidence: 49 public skills, 565 task instances in six software-engineering
  areas, pinned repositories, requirement-derived execution tests, and Claude
  Code with Claude Haiku 4.5. The report places `SKILL.md` in the project root
  and relies on autonomous discovery; no precise Claude Code release was
  recovered here.
- Missing or contrary: most skills add no pass-rate benefit, and version
  mismatches can harm performance. Many baseline tasks already pass, limiting
  possible gains. One model and one provisioning convention do not measure
  every supported skill integration.
- Design inference: qualify usefulness, dependency compatibility, and actual
  loading separately. Neither this study nor SkillsBench supplies a universal
  estimate of the value of skills.
- Test: repeat the same task with absent, compatible, stale, and deliberately
  mismatched material, while recording whether the relevant content was read.

### 6. Voyager

Guanzhi Wang and colleagues, [Voyager](https://arxiv.org/abs/2305.16291v2),
arXiv `2305.16291v2`, October 19, 2023; first submitted May 25, 2023.

- Similarity: an expanding library of executable skills, retrieval, composition,
  environmental feedback, and iterative repair with fixed model weights.
- Evidence: GPT-4 generates code for a Minecraft agent and the authors test
  acquired skills in a new world. This review uses the demonstrated mechanism;
  it did not recover an exact model snapshot and full trial denominator for
  a numerical comparison.
- Missing or contrary: Minecraft feedback and self-verification are narrower
  than independent promotion for general code with external effects. Successful
  execution is not a reusable applicability guarantee.
- Design inference: retain expected effects and preconditions with executable
  skills, using existing Code Intelligence admission.
- Test: harvest a useful procedure as a candidate, qualify it independently,
  then retrieve it for unseen inputs. Change one dependency or precondition and
  require abstention or fresh qualification.

### 7. Large Language Models as Tool Makers

Tianle Cai, Xuezhi Wang, Tengyu Ma, Xinyun Chen, and Denny Zhou,
[Large Language Models as Tool Makers](https://arxiv.org/abs/2305.17126v2),
arXiv `2305.17126v2`, March 11, 2024; first submitted May 26, 2023.

- Similarity: spend more on creating reusable functionality once, then use a
  cheaper model to invoke the resulting tool repeatedly.
- Evidence: the paper evaluates a GPT-4 tool maker and GPT-3.5 tool user on
  reasoning tasks including Big-Bench. The review establishes the functional
  cache mechanism, not a transferable cost ratio; exact model snapshots and
  all task denominators were not recovered.
- Missing or contrary: reuse only saves total cost when enough eligible
  requests occur. Tool construction, tests, maintenance, and incorrect
  invocations can consume the saving.
- Design inference: measure the break-even point before building or offering
  a specialist capability.
- Test: compare direct reasoning, an existing qualified function, and newly
  generated functionality over increasing request counts. Include construction,
  independent qualification, abstentions, and repair in cumulative cost.

### 8. Agentic Context Engineering

Qizheng Zhang and colleagues, [Agentic Context Engineering](https://arxiv.org/abs/2510.04618v3),
arXiv `2510.04618v3`, March 29, 2026; first submitted October 6, 2025.

- Similarity: develop reusable procedural context from experience without
  changing model weights.
- Evidence: the published approach separates generation, reflection, and
  curation, with incremental playbook updates. Evaluations include AppWorld
  and domain reasoning. This review does not carry forward its aggregate
  performance figures because complete matched run identities were not read.
- Missing or contrary: compressing every update into a shorter summary can
  remove useful detail. Conversely, an evolving playbook still requires
  relevance selection and protection against incorrect feedback.
- Design inference: preserve exact source evidence and proposed changes;
  prepare a selected view without overwriting the underlying record.
- Test: compare full rewriting, incremental additions, and selective retrieval
  under the same evidence budget. Inject one plausible incorrect lesson and
  measure whether independent review prevents its reuse.

### 9. GEPA

Lakshya A. Agrawal and colleagues, [GEPA: Reflective Prompt Evolution Can
Outperform Reinforcement Learning](https://arxiv.org/abs/2507.19457v2), arXiv
`2507.19457v2`, February 14, 2026; first submitted July 25, 2025. The authors
link the [original project](https://github.com/gepa-ai/gepa).

- Similarity: propose improved configurations from actual trajectories,
  evaluate candidates, and retain complementary alternatives.
- Evidence: a published prompt optimizer uses natural-language feedback and a
  Pareto frontier, with evaluation across six tasks. This review uses that
  search design and does not transfer its numeric advantage to Loop Engine.
- Missing or contrary: a useful search metric can still be incomplete or
  overfit. Prompt optimization is not permission to change enforcement,
  independent acceptance, or the customer's contract.
- Design inference: attach proposals to exact evidence and keep search
  selection separate from promotion.
- Test: compare feedback containing only scores with scores plus observed
  failure details, under equal complete search cost. Qualify selected
  candidates on a previously unused population.

### 10. Darwin Gödel Machine

Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, and Jeff Clune,
[Darwin Godel Machine](https://arxiv.org/abs/2505.22954v3), arXiv
`2505.22954v3`, March 12, 2026; first submitted May 29, 2025.

- Similarity: modify harness code, maintain an archive of candidates, and use
  measured outcomes to guide further changes.
- Evidence: the authors report evaluated coding-agent changes such as editing
  tools and context management on SWE-bench and Polyglot, with sandboxing and
  human oversight. Exact experimental identities were not recovered here for
  a reproducible numerical comparison.
- Missing or contrary: empirical improvement is not proof that arbitrary
  self-modification is beneficial. An archive can accumulate benchmark-specific
  adaptations or exploit weaknesses in the evaluator.
- Design inference: use a self-improvement Practitioner task to propose
  changes, with separate admission and review.
- Test: give candidates access to development failures while protecting the
  evaluator and final population. Include a candidate that improves the visible
  metric by violating a required invariant; promotion must refuse it.

### 11. FunSearch

Alhussein Fawzi and Bernardino Romera Paredes, [FunSearch](https://deepmind.google/blog/funsearch-making-new-discoveries-in-mathematical-sciences-using-large-language-models/),
Google DeepMind, December 14, 2023, linked to the original Nature publication.

- Similarity: use model-generated programs as candidates and retain useful
  programs through executable evaluation.
- Evidence: the work produces inspectable programs for cap-set constructions
  and bin-packing heuristics. This is stronger than asking a model to judge its
  own answer, but it is evidence in those deliberately evaluable domains.
- Missing or contrary: a well-defined executable objective is a major part of
  the method. Most open-ended customer requests do not arrive with an equally
  complete evaluator, and program search has a construction cost.
- Design inference: prioritize reusable capabilities whose obligations can be
  independently checked; qualify the evaluator too.
- Test: hold the task contract fixed while varying candidate-generation method.
  Use known-wrong programs to test the evaluator and include search cost in the
  eventual reuse calculation.

### 12. Palimpzest

Chunwei Liu and colleagues, [A Declarative System for Optimizing AI
Workloads](https://arxiv.org/abs/2405.14696v2), arXiv `2405.14696v2`, May 29,
2024; first submitted May 23, 2024. The current [official optimization
guide](https://palimpzest.org/docs/user-guide/optimization) was also inspected.

- Similarity: separate a requested semantic operation from its physical
  implementation and select plans using quality, cost, and latency.
- Evidence: the paper evaluates legal discovery, real-estate search, and
  medical schema matching. The current guide distinguishes prior-based
  execution from sample-based optimization and permits labels or a model judge.
- Missing or contrary: estimated quality is not a hard correctness guarantee.
  Sampling itself costs money, and a weak judge can favor an incorrect plan.
  No claimed paper speedup is carried forward here.
- Design inference: extend existing operation-cost and verification records;
  do not create a second execution runtime or optimization store.
- Test: compare plans selected using complete measured phase costs against
  model-call price alone. Vary cold-start cost and required accuracy so that
  the expected winning implementation changes.

### 13. NoScope

Daniel Kang, John Emmons, Firas Abuzaid, Peter Bailis, and Matei Zaharia,
[NoScope](https://arxiv.org/abs/1703.02529v3), arXiv `1703.02529v3`, August 8,
2017; first submitted March 7, 2017.

- Similarity: replace repeated expensive inference with a selected cascade
  of inexpensive operations and a more capable fallback.
- Evidence: video-specific difference detectors and specialized models are
  optimized for binary queries over fixed-angle video, using a reference
  network. This is concrete specialist substitution, not agent memory.
- Missing or contrary: agreement with the reference network is not independent
  truth. Moving cameras, new scenes, and changed questions can invalidate the
  specialization. The published speedups cannot be transferred to arbitrary
  visual reasoning or coding.
- Design inference: record a specialist's applicability and drift signals
  separately from its measured cost.
- Test: qualify a repeated bounded operation, then introduce controlled
  distribution change. Measure false acceptance among apparently confident
  cases, not only the cases the specialist chooses to escalate.

### 14. RouteLLM

Isaac Ong and colleagues, [RouteLLM](https://arxiv.org/abs/2406.18665v4),
arXiv `2406.18665v4`, February 23, 2025; first submitted June 26, 2024. The
[original laboratory page](https://sky.cs.berkeley.edu/project/routellm/)
describes the released routers.

- Similarity: learn which implementation is sufficient for a request and
  reserve a more expensive alternative for appropriate cases.
- Evidence: routers trained with preference data select between stronger and
  weaker models and are evaluated for quality-cost tradeoffs. This review
  does not reuse the laboratory's savings percentages.
- Missing or contrary: the choice set consists of models. It does not answer
  whether an exact lookup, program, index, or solver should avoid model use.
  Human preference is not independent task correctness.
- Design inference: make model routing one subordinate decision after hard
  eligibility and the availability of qualified non-model implementations.
- Test: compare a model-only choice set with an expanded implementation set.
  Keep outcomes and total cost separate, and report erroneous confident routing
  decisions and abstentions.

### 15. Cost-Aware Optimization for Agentic Query Execution

Lunyiu Nie, Yilin Xia, Yiren Liu, Christopher Jermaine, and Swarat Chaudhuri,
[Cost-Aware Optimization for Agentic Query Execution](https://arxiv.org/abs/2606.03152v1),
arXiv `2606.03152v1`, June 2, 2026.

- Similarity: choose operator type, placement, granularity, and data scope;
  retain reusable planning lessons from quality-cost feedback.
- Evidence: the abstract describes EnumGRPO and an evaluation across four
  databases in SWAN. The earlier inventory's paper title and June 2026 date
  are verified.
- Missing or contrary: the abstract's large cost-reduction headline measures
  language-model operator cost and accompanies limited execution accuracy.
  This review did not recover the complete task denominator, exact model
  identities, harness release, or full planning and training cost. It is not
  usable as a total-system savings claim.
- Design inference: separate operator savings from complete accepted-task
  cost, and enforce a quality floor before minimizing cost.
- Test: rerank identical plans first by operator cost, then by complete cost
  subject to independent acceptance. Include expensive planning and failures.

### 16. Meta-Harness and the original researcher extension

Yoonho Lee, Roshen Nair, Qizheng Zhang, Kangwook Lee, Omar Khattab, and Chelsea
Finn, [Meta-Harness](https://arxiv.org/html/2603.28052v1), arXiv
`2603.28052v1`, March 30, 2026; [original repository](https://github.com/stanford-iris-lab/meta-harness).
Joel Niklaus's [Don't Train the Model, Evolve the Harness](https://joelniklaus-harness-optimization.hf.space/)
is dated July 1, 2026 and links his [extension repository](https://github.com/JoelNiklaus/harness-optimization).

- Similarity: optimize code around fixed model weights using prior candidates,
  scores, and execution traces.
- Evidence: the paper studies classification memory, mathematical retrieval,
  and coding harnesses. Its mathematical transfer experiment separates held-out
  models and problems. The researcher extension separately uses development
  and test tasks for a legal-workflow experiment.
- Missing or contrary: section 4.3 explicitly searches and finally evaluates
  coding harnesses on the same 89 TerminalBench-2 tasks. Leakage-string audits
  cannot turn that into untouched evaluation. The original repository warns
  that its cleaned code was only checked to run. The legal report's cost chart
  excludes judge cost and other adjustments.
- Design inference: preserve detailed failures, but freeze independent final
  qualification and count the optimizer itself.
- Test: compare score-only and trace-aware optimization; use unseen tasks and
  environment changes for final acceptance.

### 17. LLMCompiler

Sehoon Kim and colleagues, [An LLM Compiler for Parallel Function
Calling](https://arxiv.org/html/2312.04511v3), arXiv `2312.04511v3`, June 5,
2024; first submitted December 7, 2023.

- Similarity: planned dependency graphs, ready-task scheduling, parallel tool
  execution, and avoiding a model call for every deterministic transition.
- Evidence: controlled function-calling patterns use GPT-3.5-turbo-1106,
  GPT-4-turbo-1106, GPT-4-0613, and LLaMA-2-70B in named experiments. The paper
  separately studies WebShop and explicitly labels differing sample sizes and
  baseline results imported from other papers.
- Missing or contrary: speed from parallel tool calls does not establish
  separately initialized harnesses per assignment, independent capability
  promotion, or safe parallel external mutations. Its WebShop behavior also
  explores more items, so that comparison changes more than scheduling.
- Design inference: maintain logical verification boundaries while scheduling
  compatible ready work efficiently.
- Test: use the same typed logical graph and inputs with serial, parallel,
  and batched physical execution. Assert identical dependency and effect
  semantics, and count every process and model call.

### 18. ADaPT

Archiki Prasad and colleagues, [ADaPT: As-Needed Decomposition and Planning
with Language Models](https://arxiv.org/html/2311.05772v2), arXiv
`2311.05772v2`, April 8, 2024; first submitted November 8, 2023.

- Similarity: recursively decompose a difficult assignment when the executor
  cannot complete it, with planning and execution as different responsibilities.
- Evidence: evaluates ALFWorld, WebShop, and TextCraft. The ALFWorld population
  includes 134 unseen games; documented executors include text-davinci-003,
  gpt-3.5-turbo, and gpt-3.5-turbo-instruct. The paper also varies executor
  strength and planning depth. No numerical advantage is transferred here.
- Missing or contrary: a model's inability or success declaration needs an
  observable check. The paper's recursion and iteration bounds are experiment
  settings, not appropriate universal Loop Engine stopping rules.
- Design inference: preserve the required small graph structure and allow a
  failed assignment to become a smaller governed subgraph when evidence
  justifies it.
- Test: compare fixed fine decomposition with adaptive refinement of the same
  initial small graph. Change executor capability and failure location; check
  whether refinement helps enough to cover planning and coordination costs.

## Corrections to carry into future research

SkillsBench search snippets still expose the first version's population and
results. The current primary paper is version 4 with 87 tasks and 18
model-harness configurations. Do not join its current results to an older
task count or self-generated-skill treatment. Evaluating AGENTS.md also has
a revised version whose conclusion is more qualified than the older abstract:
context files do not generally improve success, rather than every context file
being harmful. [SkillsBench version 4](https://arxiv.org/abs/2602.12670v4),
[Evaluating AGENTS.md version 2](https://arxiv.org/abs/2602.11988v2).

The earlier inventory associates a $49.97 search with Joël Niklaus and
Terminal-Bench. This research verified the original Meta-Harness paper, the
original Stanford repository, and Niklaus's July 1 legal-workflow extension,
but did not locate that exact amount in the inspected primary pages. Keep the
amount unresolved. Do not substitute the legal experiment's costs, outcomes,
or holdout arrangement for the original coding experiment.

The names PRAXIS, TrajAD, ProPlay, and Multi-Agent Transactive Memory from the
earlier inventory were not independently resolved in this bounded pass.
They remain research leads, not supporting citations. A name alone is not
enough to establish the intended paper, date, or result.

No inspected source proves the complete proposed Loop Engine service. That is
an evidence boundary, not a novelty claim or proof that no comparable product
exists. Packaging, measured selection, tenant policy, qualification, native
provisioning, and billing are separate obligations.

## Apply the findings at existing boundaries

The classification remains unchanged:

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

The following are proposals or refinements, not approved new fields. They
preserve all initial choices and ordered fallback requirements in the
[configuration dimension requirement](../../docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
the [flexible composition direction](../../docs/architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md),
and the [configuration grid search guide](../../docs/guides/configuration-grid-search-and-optimization.md).

| Proposed refinement | Owning boundary to extend or connect | Initial choice and ordered fallback | Discriminating observation |
|---|---|---|---|
| Evidence for each material-and-harness combination | `harness_intelligence`, `skill_registry`, `harness_selection` | Exact qualified combination; then another compatible qualified package; then an explicit no-additional-material path if permitted; otherwise unavailable | A package helps one combination but harms another, and selection preserves that distinction. |
| Server selection versus client selection | `provisioning_server`, `harness_intelligence`, `information_access` | Server supplies authorized references and compatibility facts; client selects; optional separately qualified server recommendation; client can abstain | Selection benefit is measured separately from delivery, with identical candidate scope and no hidden body disclosure. |
| Actual loading and use evidence | `instance_instructions`, `node_provisioning`, `spawned_provisioning`, harness execution records | Native observable loading signal; then adapter observation; otherwise unknown and no load claim | Disabled loader and irrelevant material remain distinguishable from successful use. |
| Executable procedure versus instructional procedure | `code_intelligence_assets`, `reusable_capability_resolution`, `reusable_capability_flywheel` | Exact qualified executable when applicable; then qualified instructional procedure; then fresh authorized work | The executable treatment eliminates repeated computation without accepting changed units, versions, or effects. |
| Decomposition and process allocation | canonical Loop definitions and graph compiler, delegation, harness execution | Declared small logical graph; refine a failing assignment into a supported subgraph; alternatively batch compatible physical work while preserving logical records | The spawning Loop and Spawned Loop outcomes remain independently attributable; budgets, cancellation, and effect protection survive each transition. |
| Complete cost of reuse and selection | `operation_cost_records`, `operation_cost_capture`, `step_efficiency_review` | Compare complete verified records; collect missing measurements; retain an explicit configured preference when evidence is incomparable | The chosen method changes when construction, verification, or cold-start cost changes, rather than always favoring a cheaper model call. |
| Feedback provenance and qualification population | `model_call_records`, `reuse_evidence`, `heuristic_adoption`, existing catalog and Run History | Server-observed delivery and client-reported outcome remain separate; independently verified outcomes can support qualification; unverified claims stay advisory | Forged or duplicated client success reports cannot promote a package or create verified cost evidence. |

This map does not create a fifth intelligence layer, a new graph vertex type,
or a parallel store. A distribution package is passive material. Work that
searches, builds, evaluates, or uses it remains owned by a classified Loop.

## A bounded sequence of experiments

First establish the serving contract without a model-quality claim: authorized
search, candidate exclusion from ordinary delivery, exact digest-bound fetch,
revocation, durable usage acknowledgment, restart behavior, and tenant
separation. This follows the recovered review's concrete blockers. Independent
offline checks can establish this boundary; they cannot establish that a real
harness benefits.

Next qualify one complete internal path and one customer-run harness path on
the same material identities. The internal path must connect decomposition,
search, selection, provisioning, execution, independent verification, and
retained Run History. The customer path must establish what was delivered and
what was actually observed at the client, preserving the distinction between
client assertions and independent outcomes.

Use a frozen population with declared task-family coverage, known failures,
and negative transfer cases. The entire task catalog remains eligible for
admission; this document does not impose a fixed 100-task sample. Keep the
native harness and model fixed when comparing absent optional material,
curated material, generated candidates, and executable reuse. Then vary the
harness separately. Preserve required instructions and permissions in all
treatments. Test additions as well as removals.

Measure accepted outcomes, unacceptable accepted outputs, abstentions, elapsed
time, physical model calls, provider-reported token completeness, total known
cost, construction and qualification cost, retries, and human work. Keep
failed deliveries, unavailable configurations, and excluded tasks in named
denominators. A returned reference, an executed script, and a successful task
are separate events.

Use development outcomes to propose selection improvements, then freeze the
selected package and policy before independent final evaluation. The existing
one-million-recorded-runs rule for learned heuristic adoption remains in
force, including its exact atomic fingerprint exception. Controlled
experiments and candidate collection do not imply authority to activate a
learned policy early.

## Unresolved questions

- Which first task family provides enough recurring work, reliable independent
  acceptance, and useful non-model alternatives to justify a paid package?
  Taxonomy coverage alone does not answer this.
- What client observations are available in each supported native harness to
  prove material loading and invocation without collecting private prompt or
  response bodies?
- Which compatibility changes invalidate qualification: model snapshot,
  harness release, dependency version, instruction precedence, execution
  environment, and package composition? The appropriate granularity needs
  evidence rather than one universal rule.
- Can client-reported results support useful recommendations without granting
  untrusted clients promotion authority or creating selection bias?
- What minimum evidence justifies calling a package qualified for a named
  population, and what revocation process handles negative transfer or drift?
- What is the realistic repeat volume and paid distribution cost at which a
  qualified procedure beats native harness work after all selection,
  provisioning, maintenance, and verification costs?

No provider experiment, outreach, deployment, untrusted-code execution, or
spending was performed. The only file written by this assignment is this
research report.
