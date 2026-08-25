> **HISTORICAL NOTE (2026-08-23):** written before the loop-of-loops reset. The executable authority is now `architecture_map.py` (four top-level abstractions; `--map`) and `loop/recursive_loop.py`. Kept for the kernel narrative; where they disagree, the code and `ARCHITECTURE_CONFORMANCE.md` win.

# Loop Engine architecture

**One sentence:** the practitioner understands the current problem, decides what to
do next, determines how to do it, executes or delegates the work, verifies the
result, and preserves what it learned before deciding what should happen next.

This file is the single reference for the whole architecture: names, contracts,
what is static versus generated, memory, the model-call plane, search, and the
question-variation engine. Code lives beside it in
`src/loop_engine/` (package self-test:
`PYTHONPATH=. python3 -m loop_engine --self-test`).

> Labels used honestly: **BUILT+TESTED** = in this package with passing tests.
> **CANDIDATE** = an off-the-shelf option identified for evaluation — an untested
> choice requiring Loop Engine testing, never a measured finding.

---

## 1. The Practitioner Kernel — the six-node universal solver

The kernel contains **no domain workflow**. It is a meta-DAG whose only job is to
discover, build, run, evaluate, and remember whatever DAG is needed. Node names
are full sentences (single verbs proved too abstract); short keys are code
identifiers only, and every run receipt embeds the full names.

| # | Node (canonical full-sentence name) | Output contract |
|---|---|---|
| 1 | **Reconstruct the current problem state and assemble the verified context already available** | `Situation` |
| 2 | **Assess whether the current problem state is sufficient and prepare any additional evidence, questions, perspectives, and reasoning resources needed for the next decision** | `DecisionSupportPortfolio` |
| 3 | **Generate, challenge, and select the most valuable next action** | `CandidateAction[]` |
| 4 | **Find, adapt, compose, or design the most appropriate method for carrying out the selected action** | `ExecutionPlan` |
| 5 | **Execute the method, build or run the required task graph, or delegate bounded subproblems to child practitioners** | `ResultPacket[]` |
| 6 | **Independently test the results, compare alternatives, and identify remaining gaps or failures** | `EvaluationPacket` |
| 7 | **Integrate accepted results and commit validated evidence, artifacts, and reusable learning to shared memory** | committed state |
| 8 | **Choose whether to continue, branch, retry, reset, distill, escalate, or finish** | new versioned state + `RouteDecision` |

**Node 2** is the sufficiency + reasoning-resource step (owner spec 2026-08-23),
with four progressively-more-expensive outcomes (`SUFFICIENCY_OUTCOMES`):
`sufficient_no_expansion` (proceed) → `retrieved_resources` (reuse stored
questions/perspectives/context policies) → `generated_resources` (generate
provisional questions/perspectives/analogies — NOT trusted knowledge) →
`research_spawned` (a child practitioner reduces an evidence gap). Its default
never forces an LLM/research call, so a standardized pass stays cheap. It keeps
**three things separate that must never collapse**: PROBLEM STATE & EVIDENCE
(what we know) vs REASONING RESOURCES (things used to improve thinking —
provisional) vs the MODEL-READY PROMPT (the exact ordered model input).

The kernel is 8 nodes (was 6); `what_is_next`→`decide_next` and
`learn_route`→`route` alias for back-compat.

Structural rules (BUILT+TESTED, `kernel.py`, 12/12):

- **Each pass is acyclic.** Node 6 never loops backward; it commits, then launches
  another pass over a **new versioned state** (`derive()`, never mutate). Every
  iteration is independently reproducible, inspectable, restartable.
- **Candidate actions carry decision metadata**: expected value, confidence,
  information gain, estimated cost, risk, dependencies, reversibility,
  parallelizability. Node 2 proposes candidates; it never executes the first idea.
- **Node 3 is reuse-first**: *"do we already have this coded, retrievable,
  ready?"* is answered before anything is generated. Its eight implementation
  modes: `use, configure, compose, modify, mutate, research, generate, delegate`.
- **Research outranks blind attempts** when the situation signals missing
  information, and research is executed by **spawning a child practitioner**
  running this same kernel; its `learned:` facts flow up to the parent.
- **Node 5's verdicts**: accept, accept provisionally, repair, research more, try
  another candidate, expand the swarm, tune, reset, stop.
- **Node 6's routes**: stop-success, continue, retry, repair, explore branch,
  expand swarm, distill, reframe, soft reset, cold restart, stop-unprofitable.
  Resets are **documented** (the failure log is append-only); a **cold restart**
  keeps only the objective, constraints, success criteria, and the failure log —
  the organizational "bring in a whole new person."
- **Every pass appends one event** to the run's `events.jsonl` — document, share,
  and learn from every run.
- A **swarm** is a portfolio of parameterized child specs of the same kernel
  (`run_swarm`) — not a separate architecture. An **experiment** is a kind of
  `ExecutionPlan`. **Distillation** is a task node 6 spawns. None of these add
  kernel nodes.

## 2. Final nomenclature

| Term | Exact meaning |
|---|---|
| practitioner | One run of the six-node kernel against a `ProblemSpec`. |
| practitioner kernel | The six-node meta-DAG above — the only solver shape. |
| pass | One acyclic traversal of the six nodes; the unit of reproducibility. |
| versioned state | The `PractitionerState` a pass derives; old versions stay intact for replay. |
| problem spec | Objective, constraints, success criteria, budgets — the only thing a cold restart keeps. |
| sub-practitioner | A child practitioner spawned for a narrower objective (research, a missing tool, a critique); same kernel, own exploration canvas, findings feed the parent. Depth-guarded. |
| solution canvas | Where the actual answer's graph is assembled. |
| exploration canvas | Where side work runs — note-taking, testing, side research. |
| matrix of solutions | A canvas where every step is a **slot**: a preferred node plus **type-compatible fallbacks**; execution waterfalls per slot, so one broken node cannot collapse the solution. |
| slot | One step of the matrix: a required type contract and its ordered candidates. |
| strict core service DAG | A hand-owned pipeline the practitioner uses but never rebuilds: the model-call DAG, the search/serve DAG, memory commit. |
| task DAG | A reusable or generated solution for actual work (research, scraping, ML, ...). Practitioner-buildable. |
| resource | Anything stored and searchable: question forms, personas, context policies, nodes, graphs, tools, knowledge, artifacts, failures, run summaries. |
| tier | `core` (ships, always on) / `experimental` (off by default) / `gated` (needs an explicit grant — licensed or trade-secret sets). |
| question form | A stored, generalized template of one way of asking (authored once, multiplied forever). |
| ask variant | One deterministic point in the multiplication (form × persona × context policy × seed). |
| ask strategy | A scripted flow of asks (blueprint → detail → detail → most discrete step; are-you-sure-intermediary). |
| shortcut | A learned zero-model route: problem signature → verified artifact; the self-improvement memory. |
| logjam reset | The documented stuck-recovery ladder (soft retry → reframe → context reset → persona/model reset → branch reset → cold restart → capability escalation). |

## 3. Three DAG categories — and what is static versus generated

```
                    SHARED RESOURCE LAYER
   question forms · personas · context policies · nodes · graphs
   tools · knowledge · artifacts · failures · performance history
                             ↕
              SIX-NODE PRACTITIONER KERNEL  (static)
                             │
        ┌────────────────────┼─────────────────────┐
        ▼                    ▼                     ▼
  Strict core service   Existing task DAG    Generated task DAG
  DAGs (static)         (resource, reused)   (practitioner-built)
```

**Static — we own these, the practitioner never rebuilds them** (it may only
propose experimental alternatives, clearly tiered):

1. The **practitioner kernel** itself.
2. The **model-call DAG** (`model_call.py`) — every model call, one contract.
3. The **search/serve DAG** (`store_serve.py`) — finding and serving what exists.
4. The **question-variation engine** (`question_engine.py`) — ways of asking.
5. **Memory commit** — append-only, versioned, provenance-linked writes
   (`self_improve.py` shortcuts, `events.jsonl`, run log; unified client below).

**Practitioner-generated — searchable resources for the next solve:** task DAGs,
new nodes (authored via OpenCode workers, compile-verified), adapters, question
forms (registered once with `llm_generated_once` provenance, experimental tier),
distilled rules/models.

## 4. The strict model-call DAG (BUILT+TESTED, `model_call.py`, 7/7)

```
prepare_context → render → call (+ model fallbacks) → validate
```

One standardized question-in object, `AskSpec`: question, knowledge + **which
context view** to show (the 14 context policies: fully informed, task only,
blind, goal only, memory-blind, contradiction-focused, counterfactual, ...),
persona, output contract, language, details, temperature, and a
preference-ordered **model chain**. A model that is down, empty, or fails
validation **falls through to the next model** — an ask never dies with one
provider. `chat_maxout` requests each model's full output ceiling (kimi 256K,
mistral 262K, deepseek-pro/glm/Ox-Alpha 128–131K) and backs off 10% only on
failure. Provider-reported token counts are the only admissible usage evidence.

**Cheapest-route doctrine** (enforced structurally by `reuse_first_guard` in the
methodical layer): cache → deterministic rule → retrieval → micro-model → small
model → tool call → one hosted model → deliberation → research. An expensive rung
is unreachable until the cheaper rungs are recorded as ruled out.

**Off-the-shelf, evaluated honestly:**

- **LiteLLM** — CANDIDATE. Multi-provider routing, retries, fallbacks behind one
  interface. Strongest candidate if provider breadth beyond Ollama Cloud +
  Mistral is needed. Adoption cost: verifying it preserves provider-reported
  token counts and per-model output ceilings; our four-stage contract and context
  policies stay ours either way.
- **OpenRouter** — CANDIDATE hosted router; conflicts with the current sanctioned
  provider policy (its key is dead here); revisit only with an owner decision.
- **LangChain / instructor** — CANDIDATES for structured output; our
  contract-first `AskSpec` + validators already cover the need at about 200
  lines without another orchestration framework, so the bar for adoption is high.

**Decision:** the call DAG **contract** is permanently ours; a library may one
day be an internal transport inside stage 3, only after winning a paired Loop Engine
test.

## 5. The strict search/serve DAG (BUILT+TESTED, `store_serve.py`, 7/7)

```
parse_query → filter_eligible (kind + tier gates) → score (idf × field) → rank → serve
```

Deterministic (no model call to find what we already own), rarity-weighted so
discriminating terms beat ubiquitous ones, and tier gates are **visible
exclusions** — a disabled gated record cannot leak even by direct id fetch. JSONL
files are the MVP database; the core set ships with the package and each
organization overlays its own files. Direction of travel: every stored thing
converges on one **resource envelope** (id, type, version, namespace,
capabilities, contracts, provenance, quality history, cost history, access
policy, relationships) and **capability-based requests** ("train a
gradient-boosted tree classifier" — never "XGBoostNodeV4"). *(Envelope +
capability request: the top open build item.)*

## 6. Memory — model, current state, and off-the-shelf options

Seven memory types behind one conceptual interface:

| Type | Holds | Current implementation (BUILT) |
|---|---|---|
| Working | current practitioner state | `PractitionerState` (versioned) |
| Episodic | what happened in prior runs | `events.jsonl` per run + `.solver_runs.jsonl` |
| Semantic | facts, evidence, knowledge | store records (kind `context`/`knowledge`) |
| Procedural | nodes, DAGs, recipes | node files + store records + question forms |
| Failure | dead ends, resets, causes | append-only failure log in state + logjam log |
| Performance | what works where | `ShortcutStore` (signature → verified route) |
| Artifact | code, models, reports | artifact **references** in packets (never blobs) |

Rules: read broadly, **write carefully** — append-only, versioned, provisional
until verified, provenance-linked; one model output never overwrites trusted
knowledge; learn **only from verified outcomes** (an unverified step is never
distilled).

**MVP storage layout** (target):

```
practitioner_data/
├── registry.sqlite        # metadata, relationships, FTS5 search
├── resources/             # content-addressed files
├── runs/<run_id>/events.jsonl
├── artifacts/
└── organization_config/
```

**Off-the-shelf, evaluated honestly (all CANDIDATES pending Loop Engine testing):**

- **SQLite (FTS5)** — recommended MVP registry: stdlib, local-first, zero new
  dependencies, full-text search built in. Aligns with the repo's data-lives-in-
  stores doctrine.
- **DuckDB** — CANDIDATE for analytical queries over run histories at scale.
- **LanceDB / Chroma / FAISS** — CANDIDATE local vector indexes when semantic
  retrieval is added; embeddings remain LOCAL per standing policy.
- **mem0, Letta (MemGPT), Zep** — CANDIDATE agent-memory frameworks; they bundle
  opinions about context injection that overlap our context-policy plane, so the
  fit test is whether they can act as *storage adapters* beneath our seven-type
  interface rather than replacing it.
- **Git/GitHub as memory** — already partially in use (this repo); content-
  addressed, versioned, reviewable; right for node/DAG/form definitions, wrong
  for high-frequency run events.

**Decision:** the seven-type interface and write rules are ours; storage engines
plug in beneath as adapters, starting with JSONL (today) → SQLite FTS5 (next).

## 7. The question-variation engine (BUILT+TESTED, `question_engine.py`, 7/7)

The secret sauce is asking many ways — and generating those ways must not be a
live model job. **A model may author a new form once; from then on it is a
stored, generalized template.**

- 16 core **forms** ship, including: best way, worst way, rank 1–10, rank
  options, **rank by analogy**, **eliminate**, verify/check, **generate the
  completely new**, pairwise, devil's advocate, premortem, decompose,
  prerequisites, what's missing, calibrate probabilities, check-then-extend.
  Each declares its **answer shape** (ranking, elimination, verdict, proposals,
  score, ...) so parsing is contract-first.
- **Deterministic multiplication**: forms × personas × context policies × seed
  salts → an `AskVariant` stream (stride mode covers every form before any
  repeats; identical inputs give identical streams; no randomness source).
  16 forms × 1,000 personas × 14 policies × 8 seeds = **1.79M distinct asks**,
  each one reproducible, zero generation calls.
- Every variant compiles to an `AskSpec` and runs through the strict model-call
  DAG. Model-authored forms register with `llm_generated_once` provenance at
  experimental tier — core tier is earned only by outcome history.

## 7b. Context enrichment — growing the banks (BUILT+TESTED, `enrichment.py`, 7/7)

Not a seventh kernel node. When node 1's deterministic **coverage probe** finds
the persona/question banks do not cover the problem's domain (a heart-disease
task with no cardiology personas), node 2 proposes one high-bias `enrich`
candidate — **optional** (`EnrichmentPolicy` defaults OFF) and **tunable** (how
many domain personas, diametric-field personas, question templates, key
phrases). One structured generation parses into STANDARD records —
`llm_generated_once` provenance, experimental tier — written through the normal
stores, so everything generated is immediately searchable, multiplies like any
shipped form, and is never regenerated for the next similar problem. A malformed
generation stores nothing. Deep needs (latest publications, real-time search)
remain research actions that spawn child practitioners.

**Prompt assembly is standardized**: every prompt integrates its elements in the
declared order (`PROMPT_ASSEMBLY_ORDER`): persona → context view → details →
question → seed salt → output contract → language. Two asks differ only by the
dimensions that changed, never by accidental arrangement.

## 8. Learning and self-improvement (BUILT+TESTED)

- After every cycle: **"could this be done deterministically or cheaper?"** —
  answered deterministically. A verified, model-built step with a concrete
  artifact distills into a **shortcut** (signature → handle); the learning probe
  IS node 3's "do we already have this?", so a very similar problem replays at
  the reuse rung with **zero model calls**.
- The distillation ladder: large model → smaller model → micro-model →
  deterministic rule → cached result, always keeping an escalation path.
- Tuning is **multi-place and toggleable** (`tuning.py`): step / graph / executor
  switches, grid or coordinate-descent within a hard reported budget, incumbent
  kept unless beaten.

## 8b. Global configuration — five core settings, enforced (BUILT+TESTED, `config.py`, 7/7)

**Owner-facing surface: the OperatingProfile** (`operating_profile.py`, 8/8) —
five ENUM modes: `access_mode`, `reasoning_and_model_mode`,
`construction_and_execution_mode` (authority, ordered least→most), `effort_mode`,
`optimization_mode` (preferences) + a `Limits` block. `resolve_chain(Platform →
Organization → Project → Run → Child)` clamps a child to the MINIMUM authority and
tightest limits seen — a child may only narrow, never broaden — while preferences
take the most-specific profile. `to_solver_config()` derives the enforced
SolverConfig below, so the guards bite unchanged. Beneath it:

A run's permissions are a handful of clear buckets, not a wall of knobs — and
they are **enforced at the how/act/ask boundaries**, never decorative:

1. **internet_access** (default: NOT allowed) — online research/downloads are
   refused with the reason when off.
2. **allowed_models** — `None` = the sanctioned roster; an explicit tuple
   restricts the chain; `()` = **no model calls** (the pure-deterministic
   profile solves with zero asks, proven end-to-end). A policy-forbidden model
   can never be configured in.
3. **code_authoring** (default: allowed) — off forces use/configure/compose of
   existing nodes; a generate plan is refused with a documented reason.
4. **budgets** — passes/tokens/seconds ceilings, **uncapped by default** (a
   budget is an explicit owner choice, never a silent default). A set token
   ceiling stops further asks loudly; the run finishes deterministically.
5. **optimize_for** — accuracy / runtime / cost / reliability; rides every
   prompt's details so decisions actually weigh it.

Advanced (defaulted, out of the way): deterministic_first, reuse_sources
(internal / github / pypi). `SolverConfig.summary()` is the plain-English
receipt of what a run may and may not do. **Defaults are FULL POWER** — internet
allowed, all reuse sources, uncapped budgets; the config exists to RESTRICT when
the owner chooses, never to hobble by default.

### Standing decision biases (BUILT+TESTED, `biases.py`, 7/7)

The practitioner's instincts, each deterministic and visibly tagged
(`bias:<name>` in the rationale): **generate-context-first** (build the domain persona/question/key-phrase bank as the biased FIRST move); **research-first** on missing info;
**enrich-first** on weak domain coverage; **adversarial-on-perfection** (a ≥0.99
score outranks everything until audited); **diagnose-after-repeated-failure**
(work the cause, not the retry); **pilot-before-full** (an expensive unproven
run gets a cheap pilot twin ranked ahead); **distill-after-repetition** (stop
paying for a known decision); and the **simplicity tie-break** (equal value and
confidence → the cheaper candidate wins).

**Biases are not dogma — they must earn their keep.** Every registry entry names
its ADVERSARIAL ALTERNATIVE, and learning/training runs validate a bias by
running `paired_trial` arms — one following it, one suppressing exactly it — on
the same problem, recording outcomes to the append-only `BiasLedger`. The
evidence verdict is three-valued: *earns its keep*, *demote* (the alternative
wins a clear majority of enough trials — `apply_biases` then auto-suppresses
it), or *insufficient evidence* (the instinct stays active until evidence
retires it). Retirement by evidence, never by argument.

## 9. What ships in the package versus organization databases

**Package (static):** the kernel, the strict service DAGs, the question engine,
schemas/contracts, core question forms, core personas, core context policies,
core validators, local storage adapters.

**Organization databases:** proprietary question packs (industry/trade-secret,
gated tier), personas, context policies, private knowledge, reusable nodes and
DAGs, tool integrations, prior runs, failure patterns, benchmarks, performance
histories. Namespaces: core → marketplace/licensed → organization → team →
project → run.

## 10. Where the moat is

Not the raw prompt count — versioned **outcome history**: *this question form +
this context policy + this persona + this model + this resource set worked for
this problem type, at this quality, cost, and failure profile.* Plus failure
knowledge, credit assignment, search quality, and cost compression. Raw prompts
are copyable; receipts are not.

## 11. Current status (2026-08-23)

| Layer | Module | Tests |
|---|---|---|
| Six-node kernel (versioned passes, resets, swarm, events) | `kernel.py` | 11/11 |
| Practitioner loop machinery (5-node state machine, logjam) | `practitioner_loop.py` | 10/10 |
| Methodical guards (reuse-first ladder, one-shot block) | `methodical.py` | 8/8 |
| Canvases + matrix of solutions | `canvas.py` | 7/7 |
| Sub-practitioners + non-linear orchestration | `sub_practitioner.py` | 7/7 |
| Self-improvement shortcuts | `self_improve.py` | 8/8 |
| Universal front door + run documentation | `solver.py` | 6/6 |
| Multi-place toggleable tuning | `tuning.py` | 8/8 |
| Strict model-call DAG | `model_call.py` | 7/7 |
| Strict search/serve DAG | `store_serve.py` | 7/7 |
| Ask strategies (compound flows) | `ask_strategies.py` | 6/6 |
| Question-variation engine | `question_engine.py` | 7/7 |
| Ollama Cloud client (maxout, no caps) | `ollama_client.py` | live-verified |
| OpenCode worker layer (+ Ox Alpha) | `opencode_client.py` | 5/5 + live |
| Kaggle tabular executor (real submissions) | `kaggle_executor.py` | 6/6 + submitted |

**Open build items (honest):** unified resource envelope + capability-based
request; `ReasoningRequest` fields (budget, evidence requirements, privacy) on
`AskSpec`; the one memory client over the seven types + SQLite FTS5 registry;
`UniversalSolver.solve()` re-based onto the kernel; model-backed kernel
implementations wired to the live roster end-to-end.

**Live campaigns:** ARC-AGI-2 solver improvement (baseline 54/1000 training,
ensemble 68/1000; worker iterating). Kaggle entries verified working for
Pokémon-strategy and RSNA; ARC-AGI-2/3 joins still pending on the website.
