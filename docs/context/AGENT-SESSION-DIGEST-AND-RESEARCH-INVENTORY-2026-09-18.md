# Agent session digest and research inventory, September 12 to 18, 2026

This document summarizes the recent Codex, Claude Code, and OpenCode sessions
that worked on Loop Engine, the research and comparison items the owner asked
those sessions to consider, and the research notes the owner supplied on
September 16 to 18 about efficient discrete reasoning and building steps. It
is a digest for orientation. It grants no authority, changes no contract, and
claims no implementation beyond what the linked records establish.

How to read the labels:

- Observed: taken from a session record, a campaign record, or a repository
  file that this session read.
- Owner requirement: a direction the owner gave in a session prompt.
- Proposal: a design direction that is not implemented.
- External claim: a statement from an article, a paper, a repository README,
  or the owner's research notes that this session did not reproduce. Links
  are given only where they were supplied or verified; a name without a link
  was not located.

Session records were read from the Codex rollout files under
`~/.codex/sessions`, the Claude Code session files under
`~/.claude/projects`, and the OpenCode session database under
`~/.local/share/opencode`. The companion review of the repository state is
[the September 18 review](../verification/CLAUDE-FABLE-5-1-REVIEW-2026-09-18.md).

## 1. The sessions at a glance

```text
Agent sessions on Loop Engine, September 12 to 18
├── Codex (gpt-5.6-sol, --yolo), September 12 to 14
│   ├── September 12: full review, the discrete cognitive or act step Loop
│   │   node nomenclature, Kaggle and task database expansion, Tactical runs
│   ├── September 13: dimension set, layered harness wrappers, ASTRA.md,
│   │   wide search, meta-selectors, Ollama Cloud preparation, disk cleanup
│   └── September 14: best-available resolution, action vectors, human-like
│       steps for every harness, then an unanswered summary request
├── Claude Code (Opus 5, then Fable 5.1), September 13 to 18
│   ├── September 13: review of Codex work, fixes, merge to main
│   ├── September 14: pipeline review, north star, live reruns, verifier
│   │   batches 8 to 13, persistence direction
│   └── September 18: repository and session review, this digest
└── OpenCode (glm-5.3-flash through opencode-go), September 15 to 16
    ├── frontier radar, DeepSeek harness, ten architectural variations
    ├── budget-phase routing, fast-path allowance, probe binding refusal
    ├── atomic harness instances, stub experiments, reasoned fallback
    └── constitution, adaptable policies, reuse tiers, the two spaces
```

Observed state on September 18: `main` is at `646b46d` with continuous
integration green through `1108218` and two newer runs in progress. The
working tree still holds this session's failed-check review (batch 13) and
the OpenCode session's runtime mechanisms, documents, and 718 MB of
experiment output, none of it committed. The Codex terminal has been idle
since September 14 and the OpenCode terminal since September 16; both
processes are still alive.

## 2. What each session was asked and what it delivered

### 2.1 Codex, September 12 to 14

Observed from 150 distinct owner prompts across the rollouts. Several prompts
concerned other projects in the same terminal (a Kaggle notebook, an entity
monitoring product, a trading scanner, social media content, disk cleanup);
only the Loop Engine items are listed.

| Owner asked for | What happened | Where it is recorded |
|---|---|---|
| A review of every file, idea, and prior Codex, Claude Code, and OpenCode session for this folder | Review and handoff documents | [Codex start here](CODEX-START-HERE.md), [everything learned](EVERYTHING-LEARNED-2026-09-08.md) |
| "Is this what I expected" cognitive steps before and after small actions and model calls, to catch corner cases | Became the action intent and outcome vector work on September 14 | [ASTRA.md](../../ASTRA.md), `core/outcome_vector.py` |
| Each node able to try several harnesses (start with OpenCode, fall back to Pi), forks of open harnesses, Hermes | Harness recipes and the harness semantic binding; a multi-harness proof of concept ran on September 16 in the stub folder | [harness guide](../../embodiments/HARNESS-GUIDE.md), [harness trials](../verification/HARNESS-EMBODIMENT-TRIALS-2026-09-10.md) |
| The full phrase "discrete cognitive or act step Loop node" with its complete explanation, and no shorthand anywhere | Recorded and enforced in the instruction files | [the phrase handoff](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md), [AGENTS.md](../../AGENTS.md) |
| The dimension set for every step (starting harness and fallbacks, model and fallbacks, tools, skills, context files, and more) with fallback priorities | The configuration dimension requirement and its addendum | [dimensions](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md), [addendum](CONFIGURATION-DIMENSION-DISCOVERY-ADDENDUM-2026-09-13.md) |
| Native loop and goal commands of Codex, OpenCode, and Pi; wrapping harnesses in layers; an outer Loop around a harness loop | Recorded as a design direction | [layered harness wrappers](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md) |
| Hyperlambda, and a wide search over millions of configurations with grid, Bayesian, genetic, and vector methods, plus meta-selectors | Research record, guides, and the generation component | [Hyperlambda and wide search](../research/HYPERLAMBDA-AND-WIDE-SEARCH-2026-09-13.md), [grid search guide](../guides/configuration-grid-search-and-optimization.md), [meta-selection guide](../guides/configuration-preferences-and-meta-selection.md) |
| An advisory file for Claude Fable 5.1 | `ASTRA.md` | [ASTRA.md](../../ASTRA.md) |
| Recurrent looped Transformers and recursive self-improvement, with the owner's view that improvement belongs in the harness fabric rather than in model weights | Research record | [recurrent models and system improvement](../research/RECURRENT-MODELS-AND-SYSTEM-IMPROVEMENT-2026-09-14.md) |
| The reported $49.97 OpenCode harness search on Terminal-Bench (Joël Niklaus) | Recorded with the unresolved source details | [fixed-weight harness section](../research/RECURRENT-MODELS-AND-SYSTEM-IMPROVEMENT-2026-09-14.md#fixed-weight-harness-optimization), [reference code](https://github.com/JoelNiklaus/harness-optimization) (64 stars, MIT, observed September 18) |
| An artificial general intelligence fabric: readiness, visualizers, fingerprints, token accounting, step logging | Readiness checklist | [experiment fabric readiness](../verification/EXPERIMENT-FABRIC-READINESS-2026-09-14.md) |
| Never a blocked or empty result; do what a capable person would do with missing material | The best-available resolution package | [ASTRA.md](../../ASTRA.md), `code_nodes/solve_terminal.py` |
| Every action as a vector that is checked, so a successful model response is not confused with correct reasoning or the requested output | Action intent vector, action vector assessment, route guard | [ASTRA.md](../../ASTRA.md) |
| The same human-like behavior in the custom Practitioner and in OpenCode, Codex, and Pi | The canonical semantic packet for every harness | `core/harness_semantic.py` |
| A file-by-file review with sub-agents into a "Luna Max summary folder" (September 14, 12:04) | Not done: the session recorded completion two seconds later with no output, and no such folder exists | none |

Observed: every Codex edit through September 14 was backed up as
`refs/backup/codex-inflight-20260914` and reconciled into `main` by the
Claude Code session (`96fba39`, `aca062f`, and later commits).

### 2.2 Claude Code, September 13 to 18

| Owner asked for | What happened | Where it is recorded |
|---|---|---|
| September 13: review the project and the Codex sessions, then fix, align, merge, and push | Review, 19001d1 fixes, branches merged, gates green | [review handoff](CLAUDE-FABLE-5.1-REVIEW-HANDOFF-2026-09-13.md), [September 13 review](../verification/CLAUDE-FABLE-5.1-REVIEW-2026-09-13.md) |
| September 14: review the full pipeline, the north star, and the recent Codex sessions | Review at `e089f60` with five verified control defects | [September 14 review](../verification/CLAUDE-OPUS-5-REVIEW-2026-09-14.md) |
| Can the system solve tasks; ignore deleted datasets; missing material must be self-resolved | Archive unpacking, binary inputs, attachment files as sources, best-available result selection | `core/task_materials.py`, commits `78e0dfa`, `e079c37`, `2aaa5d5` |
| Clean runs, fully working, fully cognitive; no stopping | Orientation repair, verifier format repair, recovery route guard, verifier contract fixes, returned results reaching passing work, recovery for every session, criterion judgment, undeclared file naming, failed-check review | commits `336e39c` to `c4def81`; batch 13 in the working tree |
| Persistent general solving, a review of every failed check, contracts that declare how they are evaluated | Proposed invariants and decision record | [Constitution](../architecture/CONSTITUTION.md), [decision record](../architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md) |
| Frontier research on harnesses, agent loops, harness-based self-improvement, and harness as a human worker (September 14) | Not done: the six-topic research workflow failed on the weekly usage limit, which resets on September 20 | none |
| September 18: review the project and the latest sessions | Review record and this digest | [September 18 review](../verification/CLAUDE-FABLE-5-1-REVIEW-2026-09-18.md) |

### 2.3 OpenCode, September 15 to 16

Session `ses_f5a30539effeYcS8lchNC4VXPp`, 45 owner prompts, 28.4 million
input tokens. The prompts often pasted long research notes from other
assistants; the items in those notes are listed in section 4.

| Owner asked for | What happened | Where it is recorded |
|---|---|---|
| Review the project, the recent Claude Code and Codex sessions, and the DeepSeek harness | Session read this repository's session transcript and the harness trial records; no separate DeepSeek harness record was written | [harness trials](../verification/HARNESS-EMBODIMENT-TRIALS-2026-09-10.md) |
| Consider a frontier radar (autonomous discovery companies, harness optimization companies, environment and evaluation vendors, durable runtimes, evidence and policy graph control) and ten architectural variations of the intelligence layers | Considered in conversation; not recorded as a repository document | none |
| Which previous runtimes and entry points actually solved tasks in the task database, and why a gate failed | Found the campaign gates leaked their holdout | [ASTRA.md](../../ASTRA.md) (working tree), `stub-experiments-20260916/atomic-kaggle-pipeline/README.md` |
| Launch more variations proactively and implement generalized fixes | Budget-phase routing, the fast-path allowance, the probe subject-binding refusal, campaign wiring | [CHANGELOG.md](../../CHANGELOG.md) "Added on 2026-09-15" (working tree) |
| Atomic components, each reasoning or action step as its own harness instance, with only the context, tools, and resources it needs | Design direction document and a stub experiment (one OpenCode instance per component) | adaptive cognition and atomic harness instances (`docs/architecture/ADAPTIVE-COGNITION-AND-ATOMIC-HARNESS-INSTANCES.md`, untracked in the working tree) (untracked), `stub-experiments-20260916/` |
| A constitution file that encapsulates every aspect of the project | 739-line synthesis with an explicit authority order | complete project constitution (`docs/COMPLETE-PROJECT-CONSTITUTION.md`, untracked in the working tree) (untracked) |
| Twenty rules for what happens between atomic steps (meaning across handoffs, dependencies, reusable results, learning without corrupting evidence) | Considered in conversation; partly reflected in the adaptive cognition document | see above |
| Actually solve Kaggle tasks; formalize the stub with memory, fingerprinting, tools, model variations, grid dimensions, more steps, Solution Canvas export | The atomic Kaggle pipeline stub ran; honest scores 0.6065 on 20-newsgroups and 0.9804 on Kannada-MNIST after the gate correction (session's measurement) | `stub-experiments-20260916/atomic-kaggle-pipeline/` |
| Adaptable rules: development versus production, adjusting rules that are too tight | Design direction document | adaptable policies (`docs/architecture/ADAPTABLE-POLICIES-AND-LIFECYCLE-APPLICABILITY.md`, untracked in the working tree) (untracked) |
| Exact, locality sensitive hashing, retrieval, and similarity fingerprints; reuse tiers; suggested output formats; micro models for search; embeddings and low rank adapters as memory | Design direction document | reuse tiers and cost routing (`docs/architecture/REUSE-TIERS-AND-COST-ROUTING.md`, untracked in the working tree) (untracked) |
| Solution graphs rather than one-off solutions; per-node provenance (harness, tools, files, context size, inputs, outputs) and whether solutions were tested end to end outside the build loop | Partly answered from records; the per-node provenance question is not answered by a single report today | open |
| A proof of concept that rotates harnesses and models across nodes and selects the best result, with the practitioner space writing into the deliverable space | Multi-harness proof of concept in the stub folder; cross-endpoint run on Tactical passed the stub's gate (session's report) | `stub-experiments-20260916/multi-harness-practitioner-poc/` |
| Prepackaged intelligence layers and holdout hygiene; an ontology of skills, instruction files, tools, contracts, supervisors, and plugins that standard harnesses can adopt | Considered; no record written | open |
| A universal reasoned fallback: before any deterministic fallback, one reasoning call receives the context and the candidate list and selects | Implemented only in the stub (`reasoned_fallback.py`), not in the engine | `stub-experiments-20260916/multi-harness-practitioner-poc/reasoned_fallback.py` |
| Research NVIDIA labs-OO-Agents | Research note | external NOOA note (`docs/research/EXTERNAL-NOOA-OO-AGENTS-2026-09-16.md`, untracked in the working tree) (untracked) |
| Stronger separation and nomenclature for the solutioning space and the Solution Canvas | The two-space document | the two spaces (`docs/architecture/PRACTITIONER-SOLUTIONING-AND-SOLUTION-CANVAS-SPACES.md`, untracked in the working tree) (untracked) |
| Clean up dirty files and branches into one branch; review the recent actions | Not done; the session went idle after the last prompt | [September 18 review](../verification/CLAUDE-FABLE-5-1-REVIEW-2026-09-18.md) |

## 3. The efficiency thesis

Owner requirement, stated across the OpenCode session and the research notes:
the quickest, lowest-overhead solution to each atomic step should be
preferred. Reusability, search, and model size are choices to be made per
step, "given what we have". Loop Engine should ask the question an engineer
asks first: is a language model really the most efficient way to solve this?

The owner's assessment of the frontier models is blunt: they are strikingly
inefficient at discrete reasoning and building steps. The example is GPT-6
Astra in the Vals AI Minecraft test. Instead of building a cheap image
detector as a tool and reusing it, the model interpreted the screen inside
the general model on every step, with large overhead and poor results.
External claim, from the article the owner cited: the model played for 141
hours, built a blaze farm, lost its valuables and its bed to a creeper, then
farmed potatoes for hours, and confused sugarcane with pigs
([Tom's Hardware, September 16](https://www.tomshardware.com/tech-industry/artificial-intelligence/defeated-gpt-6-astra-model-spent-several-hours-just-farming-potatoes-after-being-blown-up-by-a-creeper-in-minecraft-openai-offering-gets-further-than-any-other-ai-system-in-141-hour-test)).
The owner's research note adds the qualification that the run's tool
permissions and the full trace were not available, so it cannot be shown that
the agent was permitted to train a detector and refused to; the criticism that
stands is that the agent never reconsidered its method.

Observed: Loop Engine's own runs show the same pattern in a different form.

| Observed cost in the September 14 rerun on `2aaa5d5` | Value |
|---|---|
| General model calls per Practitioner pass before any work | about four (orient, decide, verify, route) |
| Model calls per independent verification attempt | three to ten (design, file, review, and now judgment) |
| Trials verified at the 60-call ceiling | 0 of 9 |
| Trials verified at 150 calls and at no ceiling | 3 of 19 |
| PM-001 at 60 calls | 43 calls spent returning a result that never existed |
| CS-001 pro at no ceiling | 256 calls, 22 verifier refusals at zero calls after the file set changed |
| DA-001 flash at no ceiling | 206 calls, 21 refused oracle reviews of keyword probes |

The general model performed orientation, decision, verification, and routing
on every pass, and the verifier performed design, review, and comparison with
model calls even for checks that a small judge, an exact comparison, or a
cached result could have made. The September 16 qualification lane shows the
other side: with per-criterion judgment cases, DA-001 was verified in 23
calls and SCM-001 in 60.

The rule the owner asked Loop Engine to make central, stated as a proposal:

```text
For every recurring operation, before paying for general reasoning, ask
├── can the result be read from an authorized structured source
├── can it be reused from a verified earlier result or procedure
├── can it be computed by ordinary code or a solver
├── can it be found by an index or a search
├── can it be classified or extracted by a small model
├── can it be controlled by a practiced procedure with observation
└── only then: which model, with which minimal packet, at which effort
```

Select the least-cost validated implementation, give it only the inputs its
contract needs, record why the alternative was retained or replaced, and
reconsider when evidence or conditions change. The rule applies to the
harness itself: no unnecessary supervisor call, sub-agent, graph traversal,
or training job.

## 4. Requested research and consideration inventory

Everything the owner asked to be researched, considered, or compared this
week, with what the repository already records. Items marked "not recorded"
have no repository document yet.

### 4.1 Frontier landscape named in the September 15 radar

Owner-supplied list, from an external research note pasted on September 15.
No links were supplied and none were verified here.

| Layer | Names as supplied |
|---|---|
| Autonomous discovery | Discovery Loop, rekursiv.ai, hiloop, Lila Sciences, FutureHouse |
| Harness optimization | Synth, Belvedir, Lemma |
| Environments and evaluations | OpenAI Frontier Evals, Anthropic Managed Agents, METR, Apollo, Neo Research, Snorkel, Meta ARE |
| Durable runtime | ego, Tasklet, Maritime, Archal, Herdr |
| Evidence, policy, and graph control | Ambral, Salus, Mirrors, Skillsync, Hyperspell, Graphify Labs |
| Runtimes and frameworks named in the same note | LangGraph, Strands, Mastra, Microsoft Agent Framework, Google ADK, OpenAI Agents SDK, Pydantic Graph, LlamaIndex Workflows, Temporal, Prefect, Dapr, DSPy, GEPA, AlphaEvolve, Darwin Gödel Machine, AI Scientist, DynTaskMAS, AgentSpawn, Autoresearch, OpenProse, Cordis |
| Evaluations named | Terminal-Bench 2 and Harbor, SWE-bench Pro, tau-bench, RE-Bench |

The note's central idea, recorded as a proposal: a harness should become
three linked graphs, a specification graph of intended nodes, contracts,
policies, and budgets; a runtime graph of actual execution and recovery; and
an evidence graph of traces, artifacts, graders, tests, judgments, and
promotion decisions. Loop Engine's boundary register, Run History, and
Solution Canvas already separate these three, but no document says so in
those words. Discovery Loop is compared in
[the Discovery Loop record](../research/DISCOVERY-LOOP-COMPARISON-2026-09-14.md);
the other names are not recorded.

### 4.2 Harnesses, runtimes, and protocols

| Item | Requested by | Repository record |
|---|---|---|
| DeepSeek harness capabilities and loop | OpenCode session, September 15 | [harness trials](../verification/HARNESS-EMBODIMENT-TRIALS-2026-09-10.md); no dedicated record |
| OpenCode, Codex, Pi, Hermes, and forks as per-step practitioners | Codex, September 12 | [harness guide](../../embodiments/HARNESS-GUIDE.md), [harnesses as optional executors](../research/HARNESSES-AS-OPTIONAL-LOOP-EXECUTORS-2026-09-06.md) |
| Native loop and goal commands, layered wrappers | Codex and Claude Code, September 13 | [layered harness wrappers](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md) |
| Hyperlambda (app.ainiro.io/hyperlambda) | Codex, September 13 | [Hyperlambda and wide search](../research/HYPERLAMBDA-AND-WIDE-SEARCH-2026-09-13.md) |
| NVIDIA labs-OO-Agents ([repository](https://github.com/NVIDIA-NeMo/labs-OO-Agents), 2,202 stars, license not asserted on GitHub, observed September 18) | OpenCode, September 16 | external NOOA note (`docs/research/EXTERNAL-NOOA-OO-AGENTS-2026-09-16.md`, untracked in the working tree) (untracked) |
| The harness engineering article (Substack, with the Dario Amodei quotation on harnesses) | OpenCode, September 16 | not recorded; the same direction is in [ASTRA.md](../../ASTRA.md) |
| The $49.97 OpenCode harness search (Meta-Harness) | Codex, September 14 | [fixed-weight harness section](../research/RECURRENT-MODELS-AND-SYSTEM-IMPROVEMENT-2026-09-14.md#fixed-weight-harness-optimization) |
| Agent harness, runtime, protocol, and ontology landscape | Claude Code, September 14 | [landscape record](../research/AGENT-HARNESS-RUNTIME-PROTOCOL-ONTOLOGY-LANDSCAPE-2026-09-14.md) |

### 4.3 Repositories and tools named this week

Observed on September 18 through the GitHub interface; stars, license, and
last push are as reported that day.

| Project | Repository | Stars | License | Last push | What it is (external claim) |
|---|---|---|---|---|---|
| Slayer | [MotleyAI/slayer](https://github.com/MotleyAI/slayer) | 210 | MIT | 2026-09-18 | Embeddable semantic layer over databases: typed queries, join planning, SQL generation, row-level security |
| Oxigraph | [oxigraph/oxigraph](https://github.com/oxigraph/oxigraph) | 1,916 | Apache-2.0 | 2026-09-18 | Rust SPARQL and RDF engine as a library with Python and JavaScript bindings; RDF dataset canonicalization |
| Cartography | [cartography-cncf/cartography](https://github.com/cartography-cncf/cartography) | 4,084 | Apache-2.0 | 2026-09-18 | Cloud and identity assets and relationships in a Neo4j graph, including model provider interface keys as nodes |
| LPG Modeler | [Volland/lpg-modeler](https://github.com/Volland/lpg-modeler) | 28 | MIT | 2026-09-17 | One labeled property graph model generating LadybugDB DDL, Neo4j constraints, SHACL shapes, and an OWL ontology |
| SSTorytime | [markburgess/SSTorytime](https://github.com/markburgess/SSTorytime) | 244 | Apache-2.0 | 2026-09-18 | Semantic Spacetime graph library over PostgreSQL, loaded through the N4L notes language, reached by agents through a separate MCP proxy |
| MemOS | [MemTensor/MemOS](https://github.com/MemTensor/MemOS) | 11,452 | Apache-2.0 | 2026-09-18 | Persistent hybrid-retrieval memory whose local plugin scores attempts and packages a working pattern as a skill; integrations listed for OpenClaw, Hermes Agent, and DeepSeek Harness |
| tgrep | [microsoft/tgrep](https://github.com/microsoft/tgrep) | 3,231 | MIT | 2026-09-18 | Trigram-indexed search with a background server; the quoted 33 seconds to 643 milliseconds is an average query on gecko-dev with the index built |
| forkd | [deeplethe/forkd](https://github.com/deeplethe/forkd) | 2,891 | Apache-2.0 | 2026-09-14 | Fork and branch of live Firecracker microVMs for agents; the 56 millisecond figure is the source pause, not snapshot readiness |
| LeJEPA | [galilai-group/lejepa](https://github.com/galilai-group/lejepa) | 1,354 | other | 2026-01-25 | Self-supervised embeddings regularized toward an isotropic Gaussian (SIGReg); vision representation research |
| Meta-Harness reference code | [JoelNiklaus/harness-optimization](https://github.com/JoelNiklaus/harness-optimization) | 64 | MIT | 2026-08-12 | Reference code for the meta-harness paper behind the $49.97 search |
| Codex Minecraft toolkit | [wz1119/Codex-Minecraft-Gameplay](https://github.com/wz1119/Codex-Minecraft-Gameplay) | 161 | Apache-2.0 | 2026-09-07 | Keyboard, mouse, and screenshot toolkit for Minecraft with GPT-6 Astra computer use; not shown to be the toolkit of the Vals run |
| Video PreTraining | [openai/Video-Pre-Training](https://github.com/openai/Video-Pre-Training) | 1,743 | MIT | 2025-09-03 | Minecraft behavior learned from video, acting through mouse and keyboard |
| STEVE-1 | [Shalev-Lifshitz/STEVE-1](https://github.com/Shalev-Lifshitz/STEVE-1) | 221 | not stated | 2024-06-04 | Text-to-behavior Minecraft controller built on Video PreTraining and MineCLIP |
| MineDojo | [MineDojo/MineDojo](https://github.com/MineDojo/MineDojo) | 2,257 | MIT | 2024-03-18 | Minecraft environment with structured observations beside pixels |
| Palimpzest | [mitdbg/palimpzest](https://github.com/mitdbg/palimpzest) | 238 | MIT | 2026-09-17 | Optimized semantic computation; the Abacus optimizer separates the logical operation from its physical implementation |
| NoScope | [stanford-futuredata/noscope](https://github.com/stanford-futuredata/noscope) | 436 | not stated | 2020-03-06 | Cascades of frame-difference detectors and specialized models in front of an expensive reference model |
| jev-ultrafast | [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) | 4,618 | MIT | 2026-09-18 | Browser Use flight-search example driven by Jev over an indexed element table; it searches, it does not book |

### 4.4 Decision and compact models

| Item | Observed on September 18 | External claims as supplied |
|---|---|---|
| Jev (TypeSafe) | [The Rundown article](https://www.therundown.ai/news/typesafe-jev-ai-decisions-software), published September 16: three output types (yes or no probability, choice with distribution and confidence, rubric score), $0.042 per million input tokens with no output charge, 70 to 500 millisecond responses, a "238 times cheaper" comparison against Claude Fable 5.1 input pricing, and the caveat that confident answers must be verified per use case | Text only, hosted; confidence summarizes the distribution's shape and is not a verified probability of correctness; evaluations use averaged GPT-6 Astra and Claude Fable 5.1 judgments as references; a third-party test on 12 synthetic passages found 6 of 7 defects at about 25 times lower latency |
| Bonsai 2 27B (PrismML) | Model card observed: derived from Qwen3.8-27B, Apache 2.0, 84.78 versus 86.32 average across 14 thinking-mode benchmarks (stated as 98.2 percent retention), language weights 5.95 GB (PTQ1_0) or 7.21 GB (PQ2_0) against 53.8 GB in FP16, optional 0.63 GB vision pack, and the warning that stock llama.cpp will not run the files | A 55 tokens per second browser demonstration; that rate would need about 18 seconds to generate 1,000 tokens |
| FunctionGemma (Google), SetFit, GLiNER, GLiClass, Distilling Step-by-Step, Agent Distillation, Minitron, AWQ, low rank adaptation, DAgger, SelectiveNet | Not fetched | Named in the owner's note on custom small models as candidate implementations for bounded classification, extraction, action selection, and rejection |
| Qwen3.8-Flash-Next N-gram memory, mixture of experts routing, and multi-token prediction | Not fetched | Named in the owner's note on output-conditioned computation; the note reports 512 experts with 10 routed plus 1 shared per token |

### 4.5 Research papers and concepts named in the owner's notes

Links were not supplied for these; they are listed by theme so that a later
research pass can locate and verify them. The arXiv preprint below was
verified by identifier.

| Theme | Named work |
|---|---|
| Ontology-constrained data access | [Symbolic Separation: Grounding Deep Agents in Knowledge Graphs for Trustworthy Operational Data Analytics](https://arxiv.org/abs/2609.17107), Davletiyarov, Khan, and Bartolini, September 15, 2026 (verified title and abstract); the owner's note reports a 14-task evaluation in which the graph-grounded agent completed 12 of 14 with one model and 3 of 14 with another, so the widely quoted "43 to 86 percent" compares different models |
| Skills, procedural memory, and trajectory monitoring | Voyager (2023), PRAXIS (2025), TrajAD (2026), ProPlay (2026), Multi-Agent Transactive Memory (June 2026), Buffer of Thoughts, LLMCompiler, Large Language Models as Tool Makers, Automated Design of Agentic Systems, FunSearch, AlphaGeometry |
| Test-time and latent computation | Coconut, System-1.5 Reasoning, Rational Metareasoning for Large Language Models (June 2025 version), RouteLLM, MetaNet (August 2026), Pre-Attention Expert Prediction and Prefetching, task-level mixture of experts (2021), a cache-friendly routing study (August 2026), SGLang jump-forward decoding, Grappler, Ray, SmolVLA |
| Context and evidence | Sufficient Context, The Complexity Trap (observation masking), Agentic Context Engineering, Anthropic's context engineering and code-execution notes, OpenAI's latency guide and structured outputs, Agent Skills progressive disclosure |
| Cost-based execution | Palimpzest and Abacus, Cost-Aware Optimization for Agentic Query Execution (June 2026; the note reports a 317-fold reduction in model operator cost at 35.4 percent execution accuracy), NoScope |
| Human skill and teamwork | Wolpert and Kawato (1998) paired forward and inverse models (MOSAIC), Wolpert, Ghahramani, and Jordan (1995), Heald, Lengyel, and Wolpert (2021) COIN, Sadtler and colleagues (2014), Wymbs and colleagues on chunking, Johansson and colleagues on gaze, Lieder and Griffiths on rational metareasoning, Buch and colleagues on replay, Liang, Moreland, and Argote (1995) transactive memory, Hutchins on distributed cognition, Bahrami and colleagues, Lorenz and colleagues, Navajas and colleagues, NIST on control charts and the exponentially weighted moving average |
| Minecraft agents | Video PreTraining, STEVE-1, MineCLIP, MineDojo, MrSteve |

### 4.6 Repository records that already cover parts of this direction

These predate the week and should be read before any new research pass:
[procedural memory, predictive state, and information value](../research/PROCEDURAL-MEMORY-PREDICTIVE-STATE-AND-INFORMATION-VALUE-2026-09-04.md),
[adaptive cognitive Loops and amortized computation](../research/ADAPTIVE-COGNITIVE-MESH-AND-AMORTIZED-COMPUTATION-2026-09-04.md),
[skill state execution and cache economics](../research/SKILL-STATE-EXECUTION-AND-CACHE-ECONOMICS.md),
[long-horizon recurrence, skills, and state](../research/LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md),
[model routing and gateway options](../research/MODEL-ROUTING-AND-GATEWAY-OPTIONS.md),
[scaffolds, skills, and search](../research/SCAFFOLDS-SKILLS-SEARCH-2026-09-11.md),
[tool-use training landscape](../research/TOOL-USE-TRAINING-LANDSCAPE-2026-09-11.md),
[cognitive steps, harness processes, and reusable Solutions](../research/COGNITIVE-STEP-HARNESS-DIRECTION-2026-09-12.md),
[the reusable capability flywheel](../architecture/REUSABLE-CAPABILITY-AUTHORITY-AND-RESEARCH.md),
and [flexible cognitive steps and actions](../architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md).

## 5. The research notes supplied by the owner, September 16 to 18

The owner pasted a long research conversation with another assistant. The
sections below keep its claims, its own evidence qualifications, and the
mapping to Loop Engine. Everything here is an external claim or a proposal
unless marked observed.

### 5.1 Jev: bounded semantic judgments as a software component

Claims: Jev answers narrow questions about supplied information and returns
typed judgments (a probability, a choice with a distribution, a rubric score)
instead of prose; the intended architecture is code that asks several narrow
questions, applies thresholds, and routes; parallel questions over one
document can share a request. Qualifications in the note: "cannot
hallucinate" concerns the permitted output structure, not correctness; the
confidence field summarizes distribution shape; the published evaluations
compare Jev to averaged frontier-model judgments rather than to verified
outcomes; the pricing comparison to a frontier model's input rate is 238
times, but against a small model's input rate about 24 times; escalating one
percent of a million requests to a human reviewer costs more than inference.

Mapping: Loop Engine's independent verifier now makes exactly this kind of
bounded judgment (the criterion judgment case, one criterion per call,
grounded in verbatim quotes). A typed judgment model is a candidate
implementation of that judge role and of the oracle review, and of the
recovery panel's option selection, as one more registered model route. It
would need the same grounding, the same refusal to accept an ungrounded
answer, and a text-only, hosted-service boundary declared in the route. It
must never replace an exact comparison, a permission check, or arithmetic.

### 5.2 The execution envelope: muscle memory, the vector cone, and the control chart

The owner's idea: when repeating similar but slightly different tasks, a
person has muscle memory, a learned sense of what competent execution looks
like, and a continuous signal for whether the current action is still in the
right region. The note's refinement:

```text
Four separate signals, never averaged into one score
├── familiarity: have similar situations and actions occurred in verified runs
├── progress: is the requested outcome becoming more complete
├── prediction error: did the action produce the expected observable change
└── constraint status: are the mandatory requirements still satisfied
```

Warm and progressing continues the practiced path; familiar but not
progressing suspects a loop; unfamiliar but progressing inspects without
rejecting; a constraint violation stops regardless of familiarity. The unit
of reuse is a predictive skill: when it applies, what it needs to observe,
what it does, what should change, what must stay unchanged, how success is
checked, and when it must stop. A control chart over residuals (repeated
actions without state change, growing expectation gaps, unresolved
requirements past their stage) shortens the automatic segment as deviations
grow, with baselines per task family and stage and thresholds estimated on
held-out sequences rather than textbook limits. Promotion into trusted memory
requires independent verification, not the agent saying "done".

Mapping, observed: the action intent vector and action vector assessment
implement prediction before action and comparison after it on one pass; the
supervision policy's stall detection and escalation ladder are a coarse
progress monitor; the task and stage fingerprints (`core/task_fingerprint.py`,
`core/stage_fingerprint.py`) and the tiered fingerprint index are the
familiarity signal; the reusable capability flywheel keeps tools as
candidates until qualified. Missing: a per-skill applicability record with
expected consequences, the four signals kept separate at the route step, a
residual chart with per-family baselines, and procedure memory as
executable, parameterized artifacts rather than retrieved examples.

### 5.3 Using the cone to shorten reasoning

Claims: inside a validated region execute a stored procedure; near the
boundary reason only about the differences (difference-directed reasoning
with explicit dependency tracking so a changed metric definition invalidates
dependent calculations but not parsing); outside it plan from scratch. An
"agreement horizon" lets the controller run the shared prefix of several
applicable procedures without a planning call until they branch. Separate
savings must be measured separately: procedure reuse (fewer planning calls),
difference reasoning (smaller unresolved problem), a compact execution state
(less input), model and effort routing, and prompt caching. Internal
shortcuts (distilling a skill into a small model; latent shortcut paths as in
Coconut or System-1.5) come later. An illustrative calculation: if 70 percent
of tasks reuse a procedure, the decision portion is about 6.4 times faster,
but an unchanged 20 second external operation reduces the end-to-end gain to
about 1.3 times.

Mapping: the fast-path allowance (working tree) runs exact resolvers before
the first model call, which is the hot path in its simplest form. The
deterministic mode and the deterministic attempt trace exist. Missing: a
learned or declared applicability gate per procedure, dependency tracking
between plan stages, and the agreement horizon.

### 5.4 Output-conditioned computation

Claims: Qwen3.8-Flash-Next's N-gram memory injects learned vectors for local
token sequences into the residual stream, separately from its mixture of
experts routing and its multi-token prediction; none of these uses the
required output's type, domain, or stage to allocate computation. The
proposal is an explicit output contract (structure, semantic domain,
evidence restriction, current stage) that biases expert routing, drives
expert prefetching, reduces the active expert budget where validated, and
conditions a draft model for speculative decoding. Qualifications: selecting
different experts does not save work unless activated work, sequential steps,
or data movement fall (the note cites MetaNet's 62 percent fewer activated
experts for a 4.9 percent latency reduction); a small output space does not
make a task easy; a predicted answer must remain a hypothesis.

Mapping: this is model-internal research beyond Loop Engine's boundary. The
part that applies today is the output contract itself: the verifier's
registered criteria and the typed response contracts are output contracts,
and a context compiler could work backward from them (section 5.6).

### 5.5 Human skill and teamwork mechanisms

Claims and translations from the note:

| Research connection | Proposed translation |
|---|---|
| Paired forward and inverse models (MOSAIC): select an action for a desired result and predict its consequences | Pair each skill with expected observable effects; revise selection when predictions fail |
| Chunking of practiced sequences | Execute validated multi-step procedures without a planning call per transition; allow a chunk to split when the environment changes |
| Context inference (COIN): adapt, switch, or create a memory | Keep procedures per interface version; do not overwrite one global skill on every failure |
| Active sensing: gaze leads the hand to task-relevant landmarks | Retrieve only the evidence that could change the next action; keep omitted evidence retrievable |
| State estimation from prediction plus sensation | Keep attempted, observed, and believed state distinct, with freshness |
| Rational metareasoning | Spend more computation only where it is likely to change the decision |
| Replay during rest | Compile verified traces into candidate procedures offline; test before promotion |
| Transactive memory and distributed cognition | A measured expertise directory and a shared structured workspace instead of broadcasting everything to every agent; agreement is not verification |

Mapping: the four intelligence layers, Runtime Memory, and the Solution
Canvas are the shared workspace; the harness capability matrix is a partial
expertise directory without measured reliability per operation. The other
mechanisms are proposals.

### 5.6 Minimal sufficient information: the context compiler

Claims: keep what the system knows separate from what a model call sees;
build each call a decision packet (objective, current decision, constraints,
evidence, unresolved questions, expected output) by working backward from the
output contract; let the model answer DECISION, NEED_INFO with a specific
missing fact, or BLOCKED; keep bulk data and routine control flow out of the
model (tools return result envelopes with scope and completeness fields);
maintain structured operational state instead of summaries of summaries;
diagnose the bottleneck (missing fact, hard inference, tool failure, wrong
procedure, missing permission) before adding computation; give multiple
agents narrow contracts; learn what can be omitted through controlled context
ablation; and require that building a shortcut pays for itself over expected
reuse.

Mapping, observed: the Practitioner already assembles a work packet with a
context budget (`llm_work_packet_assembled`, `context_pack_compiled`,
`context_budget_applied` events), keeps typed state, answers its own
capability questions, and distinguishes material questions from runtime
facts. Missing: sufficiency checks driven by the output contract, a typed
NEED_INFO response from every step, result envelopes with scope and
completeness on every capability, and ablation experiments that learn an
evidence-selection policy per task family.

### 5.7 Custom small models and heuristics

Claims: a frontier model "knows too much" is the right intuition but the cost
comes from running the whole network, so shrink the required behavior, not
the encyclopedia; pick the smallest machine per operation (ordinary code,
statistical model, encoder plus classification head, span extractor, compact
task-tuned language model, learned heuristic guiding a solver, and only then
a general model); let the frontier model propose heuristics and programs that
an evaluator keeps (FunSearch); distill the transformation, not the subject;
pair every specialist with an applicability and abstention mechanism; train
boundary cases and the specialist's own error states (DAgger); sample
confident acceptances, not only escalations; and apply a break-even rule
before building.

Mapping: Code Intelligence admission and the reusable capability flywheel
already make a produced tool a candidate until a different process qualifies
it, which is the promotion rule the note asks for. Missing: an operation
registry with per-implementation cost, quality, and applicability records,
and an engineering loop that proposes replacements from measured repetition.

### 5.8 The project set: relationships in the graph, not the prompt

The owner's list and the note's assessment:

| Project | What to borrow | Qualification in the note |
|---|---|---|
| Symbolic Separation (paper) | Reject unsupported data-access operations before execution; validated, ontology-mediated access | The headline compares different models; zero hallucinated answers was observed on 14 tasks, not guaranteed |
| Slayer | A small typed intermediate language between the model and execution; the database does the bulk work | Unproven join cardinalities produce warnings; strict tasks should turn them into refusals |
| Oxigraph | Embedded relationship queries and stable fingerprints of unchanged graph content | Canonicalization proves structural equality, not semantic equality or truth |
| LPG Modeler | One reviewed model with a target-capability matrix; unsupported constraints become diagnostics | OWL is open-world, SHACL validates data; an OWL statement is not a database constraint |
| Cartography | Source-specific collectors into one relationship model with observation timestamps | Timestamps record synchronization, not when exposure began or whether coverage was complete |
| SSTorytime | Time, context, and relationships as first-class information; a separate proxy | A different graph model from RDF; authorization and isolation still need verification |
| MemOS | The trace, candidate skill, feedback, revision lifecycle | Its skill packager injects an invocation guide into the prompt; stored procedure fields do not execute without model interpretation; its verifier checks tool coverage above 50 percent and textual overlap, not outcomes |
| tgrep | Durable indexes updated incrementally | Profile first; the speedup is repository search, not the agent |
| forkd | Preserve expensive local setup when testing alternatives | External effects are not rolled back with local memory; bound permissions on branches |
| LeJEPA | Possibly stable representations for comparing situations | Distance is not calibrated correctness; task-conditioned representations may fit better than one isotropic geometry |

The note's architectural principle, recorded as a proposal: keep four kinds
of knowledge distinct (schema and contracts; observed facts with provenance;
procedures and dependencies; execution experience), treat a relation absent
from the schema differently from an allowed relation whose instance is
absent (open-world absence is not falsity), and keep model-proposed
relationships in a candidate area until corroborated.

Mapping: Loop Engine's ontology package, boundary register, typed contracts,
Context Intelligence with candidate-only admission, and Run History already
separate these four kinds. No graph engine is integrated, and the
NOOA note (`docs/research/EXTERNAL-NOOA-OO-AGENTS-2026-09-16.md`, untracked in the working tree) records the
same conclusion for object-oriented agents: the separation exists here; the
gaps are measured reliability records and the engineering loop.

### 5.9 Loop Engine should optimize the computation, not default to a model

Claims: an execution compiler accepts an operation description (inputs,
required output, requirements) independent of its implementation and chooses
among available implementations from a capability inventory (types,
prerequisites, permissions, measured quality, runtime cost, cold-start cost,
whether the model is loaded and the index exists); the plan is optimized as a
whole (setup, execution, data movement, verification, expected recovery)
under quality, latency, permission, and resource requirements; "atomic"
means independently checkable, not maximally fragmented, so operations fuse
when they share inputs and have no unresolved semantic decision between
them; three loops run at different rates (execution, deliberation on events,
engineering under its own budget); and "obtain or build a better capability"
is a first-class action triggered by measured repetition with a break-even
rule and promotion of versioned artifacts.

Mapping: the Solution Canvas compiler and the deterministic mode exist; the
model routing selector and output capacity records exist for model routes;
the stage assistance experiment runs shadow and advisory arms. Missing: an
operation registry across code, index, classifier, controller, and model
implementations with recorded costs; a compiler that selects among them; the
engineering loop; and a selection record per operation.

### 5.10 The smallest useful loop node

The owner's question: should Loop Engine break tasks into their smallest
possible loop nodes? The note's answer, recorded as a proposal: the smallest
useful, independently testable node, with a logical graph that exposes
substitution and verification boundaries and an execution plan that fuses,
batches, or specializes nodes to minimize total work while preserving checks,
permissions, and interruption points. A node needs its own model call,
conversation history, supervisor, or model-based verifier only when the
operation requires it, and looping only where feedback is required. Stop
decomposing when another split adds no better executor, no smaller
information need, no reuse, no isolated failure, and no scheduling benefit.

Mapping: this is consistent with the discrete cognitive or act step Loop
node definition and with the one-runtime rule; the
adaptive cognition document (`docs/architecture/ADAPTIVE-COGNITION-AND-ATOMIC-HARNESS-INSTANCES.md`, untracked in the working tree)
(untracked) records the decomposition and provisioning rules; the stub
experiment ran one OpenCode instance per component. Missing: node fusion in
the execution plan and cost-aware decomposition.

### 5.11 GPT-6 Astra in Minecraft

The note's findings: the run was conducted by Vals AI; 141 hours is not a
measure of inference overhead; the public Codex Minecraft toolkit already
contains checked action sequences with visual preconditions, postconditions,
and pixel-change monitoring, but no learned perception or detector training;
Minecraft controllers that do not deliberate over every action exist (Video
PreTraining, STEVE-1, MrSteve); NoScope shows automatic replacement of
expensive vision with cheaper cascades; tool making by language models is
established. The sharpened criticism: failing to train a detector is not the
mistake, failing to evaluate a cheaper adequate method is. The expected
behavior is a method-improvement decision after measured repetition:
profile the bottleneck, test the cheapest plausible replacement, promote a
verified implementation, and stop invoking the frontier model for solved
perception. The experiment that would settle it compares a direct
computer-use agent, an engineered specialist system, and a self-engineering
Loop Engine that must pay for its own search, training, and validation.

### 5.12 Bonsai 2 and Jev for decisions in games

The note's conclusions: Bonsai reduces the resources to host a capable
generative model; Jev reduces the work of bounded semantic questions; neither
replaces a detector, a pathfinder, or a practiced controller. Jev is text
only and hosted, so screenshot to Jev to object locations is not a supported
pipeline; its own documentation reportedly warns about counting, arithmetic,
date comparison, indirection, and adversarial content and recommends doing
arithmetic in code and filtering state before submission. Real-time control
needs different decision rates (a 70 to 500 millisecond call spans 4 to 30
frames at 60 frames per second), so typed judgments belong at the event level
and compact generative models at the planning level. The browser-use example
gained its seven seconds by changing the representation (an indexed element
table) and dividing the work, not only by a faster model.

## 6. Consolidated mapping to Loop Engine boundaries

| Mechanism from the notes | Owning boundary today | Status |
|---|---|---|
| Bounded typed judgments as a verifier role | `core/independent_judgment.py`, model routes | Implemented offline and qualified live in two trials; a typed-judgment model would be one more route |
| Prediction before action, comparison after | `core/outcome_vector.py`, action vector assessment, route guard | Implemented offline; live models' assessment quality not qualified |
| Familiarity and reuse | `core/task_fingerprint.py`, `core/stage_fingerprint.py`, tiered fingerprint index, reuse tiers document | Fingerprints exist; locality sensitive hashing, hybrid retrieval, and output-side tiers are proposals |
| Practiced procedures with observation | fast-path allowance (working tree), deterministic resolvers, Solution Canvas | Simplest hot path exists; parameterized procedure memory with applicability records is missing |
| Progress and residual monitoring | supervision policy, stall detection, budget-phase thresholds (working tree) | Coarse; no residual chart with per-family baselines |
| Failed check review before repair | `core/independent_failure_review.py` (working tree) | Implemented offline; not exercised live |
| Reasoned choice before deterministic fallback | `core/recovery.py`, recovery panel | Exists for model failures and stalls; the universal rule exists only in the stub |
| Context compiled from the output contract | work packet assembly, context budget, registered criteria | Partial; sufficiency and NEED_INFO responses missing |
| Operation registry and execution compiler | model routing selector, output capacity records, capability registry | Model-level only; no cross-implementation cost model |
| Tool and model making as candidates | Code Intelligence admission, reusable capability flywheel | Promotion rule exists; the engineering loop that proposes replacements is missing |
| Four kinds of knowledge kept distinct | ontology package, boundary register, Context Intelligence, Run History | Exists; no graph engine and no measured reliability directory |
| Atomic harness instances per step | `core/harness_semantic.py`, harness recipes, the stub experiment | Binding exists; per-step rotation and best-of selection exist only in the stub |
| Evaluation hygiene | campaign gates in `devtools` | Holdout leak found; gate not yet corrected in `devtools` |

## 7. Proposed next experiments, in the order the efficiency rule suggests

Each is a proposal with a discriminating test and an owning boundary.

1. Operation cost records. Record per operation the implementation used,
   input size and representation, setup, execution, verification, outcome,
   and recovery, starting from the existing Run History events. Test: a
   report over one campaign names the three most expensive recurring
   operations with their counts. Owner: Run History projections.
2. A judge route comparison. Run the criterion judgment step on a second
   registered route (a compact local model or a typed-judgment service) in
   shadow mode beside the current route. Test: grounded agreement rate and
   cost per grounded judgment on the September 16 qualification tasks.
   Owner: model routes and `core/independent_judgment.py`.
3. Retained-check re-planning and the resolution package guard (findings 4
   and 5 of the September 18 review). Test: the pro CS-001 and PM-001 records
   replayed offline no longer dead-end. Owner: `core/independent_verification.py`,
   `core/adaptive_practitioner_verification.py`.
4. Applicability records on the fast path. Give each deterministic resolver
   and each qualified procedure a record of supported contexts, expected
   consequences, and measured error among accepted cases. Test: a changed
   unit, authorization, or version makes the procedure abstain. Owner: the
   reusable capability flywheel.
5. Node fusion in the execution plan. Test: a logical plan with several
   nodes sharing one input executes as one process without losing the
   per-node checks in Run History. Owner: Solution Canvas compiler.
6. The engineering loop. After a campaign, propose a replacement for the
   most expensive recurring operation with a break-even estimate, build it
   as a candidate, and qualify it independently. Test: one recurring
   operation replaced with measured savings on held-out tasks. Owner:
   self-improvement Practitioner profile and Code Intelligence admission.
7. Campaign gate correction. Test: the corrected gate scores a known leaked
   solution lower than the leaked gate did. Owner: `devtools` task campaign.

## 8. Open questions for the owner

- Which of the untracked OpenCode documents should become normative, and in
  which order: the constitution, the adaptive cognition direction, the
  adaptable policies, the reuse tiers, the two spaces.
- Whether the frontier radar and the ten architectural variations should be
  recorded as repository research records with sources, or remain
  conversation material.
- Which provider routes may be used for the judge route comparison, given the
  Ollama allowance and the Tactical endpoint.
- Whether a typed-judgment service (hosted, text only) is acceptable under the
  privacy rules for task material, or whether only local models qualify.

## 9. Source map

- Session records: `~/.codex/sessions/2026/09/12` to `14`,
  `~/.claude/projects/-home-username-loop-engine/`,
  `~/.local/share/opencode/opencode.db` (session
  `ses_f5a30539effeYcS8lchNC4VXPp`).
- Campaign records: `.loop-engine-dev/live-rerun-v3-20260914.ShZN`,
  `.loop-engine-dev/proactive-20260915-kR7wQm`,
  `.loop-engine-dev/qualification-20260916-mQ9vXk`.
- Articles the owner cited: [The Rundown on Jev](https://www.therundown.ai/news/typesafe-jev-ai-decisions-software),
  [Tom's Hardware on the Astra Minecraft test](https://www.tomshardware.com/tech-industry/artificial-intelligence/defeated-gpt-6-astra-model-spent-several-hours-just-farming-potatoes-after-being-blown-up-by-a-creeper-in-minecraft-openai-offering-gets-further-than-any-other-ai-system-in-141-hour-test).
- Paper the owner cited: [Symbolic Separation](https://arxiv.org/abs/2609.17107).
- Repositories: listed with links in section 4.3.
- Model listings: `prism-ml/Ternary-Bonsai-2-27B-gguf` on Hugging Face.
