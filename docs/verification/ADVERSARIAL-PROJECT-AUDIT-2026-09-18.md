# Adversarial project audit, September 18, 2026

This audit reads the whole repository against five questions the owner asked
on September 18: is every component sectioned off behind an interface that
lets a subcomponent be replaced without reprogramming its callers; are the
solutioning space and the solutions space clear and consistently named; is a
model call a model call rather than a language-model call; are the prompts,
suggested outputs, and metadata recorded in a form that can be learned from;
and does the system ask the questions a laboratory of engineers asks before
it spends a model call, so that it converges on the most efficient solution.

It is adversarial: it looks for the places where the architecture's own
rules are not enforced, where a concept exists in three names, where a seam
is missing, and where a record cannot be joined to an outcome. Every number
below was measured on the working tree at `main` `97c6164` plus the
uncommitted batch 13 and OpenCode changes on September 18. No provider or
model call was made. Labels: observed, owner requirement, proposal.

The ranked backlog is in section 8. The companion records are the
[September 18 review](CLAUDE-FABLE-5-1-REVIEW-2026-09-18.md) and the
[session digest and research inventory](../context/AGENT-SESSION-DIGEST-AND-RESEARCH-INVENTORY-2026-09-18.md).

## 1. Summary

1. The package layering is circular. `core` imports `code_nodes` 56 times
   and `code_nodes` imports `core` 79 times; `loop` imports `core` 33 times;
   7 of the 15 `strings` modules import `core`. No conformance gate declares
   an allowed dependency direction, so nothing stops the next inversion.
2. Two modules are hubs that every replacement has to edit:
   `core/adaptive_practitioner_records.py` (2,959 lines, imported by 38
   modules, importing 44) and `loop/recursive_loop.py` (2,654 lines,
   imported by 131). Twenty-seven modules hold size exceptions with written
   split plans; none has been executed.
3. The genuine replacement seams are real but partial: 21 `Protocol`
   interfaces and the eight injectable dependencies of the Practitioner.
   The model is reached through three different call shapes in 29 modules,
   the capability list is a constant inside the records module, and the
   independent verifier has no port for its judge, designer, or reviewer
   routes.
4. The model seam is text only. `ModelInvocationRequest` carries a prompt, a
   system text, and a temperature; the route vocabulary already names
   vision, embedding, reranking, and structured extraction as purposes, but
   no model ontology, no non-text input, and no typed output kind exist,
   and the route policy hardcodes a "cloud-only now" rule for counted
   generation.
5. The solutions space already exists as data (2 to 22 candidate canvases
   are kept per run) but not as a term or a typed record; the public word
   is the singular Solution Canvas, and the solutioning space has no term at
   all. Two working-tree documents use a third pair of names.
6. Each model call is recorded in pieces that can be joined but are not
   joined: gateway results, ledger events, packet artifacts, stage evidence
   rows, lineage links, and campaign tables. Forty-five response contracts
   are ad hoc JSON strings; the typed `ObservationExpectation` is built in
   two places; no suggested-output field exists; nothing exports a training
   set.
7. The engineering questions the owner wants asked before a model call (is
   a model needed, deterministic or learned, train our own, is there data,
   confidence from 0 to 100 for the best next step) do not exist as a
   portfolio, although the interrogation bank already labels 17 of its 31
   questions as answerable by code.
8. Repository weight and hygiene: 647 documentation files against a
   component guide of five pages; 45 modules at or above 700 lines; 27,200
   lines of test code inside runtime modules; 9 modules nothing imports;
   two folder ontologies (`embodiments` beside the term harness,
   `code_nodes` beside the rule that forbids Node classes); 6.3 GB of
   ignored harness runtimes and 718 MB of untracked experiments inside the
   checkout.

## 2. Inventory

```text
src/loop_engine (593 tracked files)
├── core        320 modules, 129,828 lines (251 runtime, 72 checks modules)
├── loop         43 modules,  21,364 lines (kernel, Loop runtime, contracts)
├── code_nodes   48 modules,  20,230 lines (solve entry, canvas, model port)
├── root         30 modules,  10,584 lines (command line, conformance)
├── memory       29 modules,   5,369 lines
├── strings      15 modules,   4,283 lines (prompts, templates, questions)
├── generation   17 modules,   2,628 lines (configuration search)
├── catalog      14 modules,   2,361 lines
├── ontology      9 modules,   1,361 lines
├── templates     5 modules,   1,358 lines
├── node          2 modules,      38 lines (legacy reader only)
└── data, evidence, governance, intelligence, kernel, runtime, skills
    folder ontology with READMEs and data files, no modules
```

The folder ontology (`intelligence`, `kernel`, `runtime`, `governance`,
`skills`) names the concepts the code implements elsewhere: the four
intelligence layers live in `core/intelligence_layers.py`, the kernel in
`loop/kernel.py`, governance in `loop/effect_approval.py` and
`core/boundary_registry.py`. A reader who follows the folders finds
READMEs; a reader who follows the code finds `core`.

## 3. Separation of concerns and replaceability

### 3.1 Dependency direction is not declared or enforced

Observed import edges between packages (count of importing statements):

| From | To | Count | Reading |
|---|---|---|---|
| core | loop | 297 | expected: the runtime is the foundation |
| code_nodes | core | 79 | expected: the solve entry composes core |
| core | code_nodes | 56 | inversion: the foundation reaches up into the entry package |
| loop | core | 33 | inversion: the kernel reaches up into core |
| strings | core | 14 | inversion: text resources import runtime code (7 of 15 modules) |
| loop | code_nodes | 3 | inversion |
| core | strings | 26 | expected |

The clearest case is the model seam: `code_nodes/solution_model_port.py`
defines `ModelExecution`, `ModelInvocationRequest`, and the session, and 33
modules import it, most of them in `core`. The seam of the whole system sits
in the package that should be its top consumer. `AGENTS.md` requires
import-boundary tests before a new top-level folder, but no gate covers the
edges between the existing packages, so each inversion was free.

Proposal S1: declare the allowed direction (`strings` and `ontology` depend
on nothing at runtime; `loop` depends on `ontology` and `catalog` only;
`core` depends on `loop`; `code_nodes` and the root depend on `core`), move
the model seam into `core` (or a new `core/model` group) with compatibility
imports, and add a conformance gate that fails on a new edge against the
direction. Discriminating test: an added import from `loop` into `core`
fails conformance.

### 3.2 Two hub modules absorb every change

`core/adaptive_practitioner_records.py` holds the request record, the
services object, the capability catalog constant `ADAPTIVE_CAPABILITIES`, the
model step loop with its format and transport repair, the context pack and
work packet events, the selection tally, and more. It is 2,959 lines, is
imported by 38 modules, and imports 44. Replacing the packet assembly, the
admission policy, or the capability list means editing it. Its own size
exception records the split plan ("move model context assembly bindings into
adaptive_practitioner_model_context.py"); that plan has not run.

`loop/recursive_loop.py` is 2,654 lines with a 961-line inline self-test and
131 importers. Its split plan ("extract LoopSpec and pause-resume into
loop/spec.py once the kernel routes through run_next_iteration") has not
run either.

Observed: 27 modules carry size exceptions with split plans; 45 modules are
at or above 700 lines; the total inline `self_test` code inside runtime
modules is 27,200 lines. Tests inside a module are one reason the module
cannot shrink, and they cannot be run without importing the runtime module.

Proposal S2: execute the recorded split plans in order of fan-in, starting
with the records module and the runtime, moving inline self-tests into
sibling checks modules as each split lands. Discriminating test: the size
exception list shrinks and the self-test count does not.

### 3.3 The seams that exist

Observed replaceable interfaces: 21 `Protocol` classes, among them
`ProviderAdapter` (model gateway), `WorkspaceBackend`,
`InformationStorageAdapter`, `CatalogStore`, `ExternalHarnessAdapter`,
`SpawnedExecutor`, `RuntimeObserver`, `DeterministicTaskResolver`,
`McpTransport`, and `SpanExporter`. The Practitioner's injection point,
`AdaptivePractitionerDependencies`, carries `model_execution`,
`deterministic_resolvers`, `context_portfolio`, `project_executor`,
`web_fetcher`, `web_searcher`, `reuse_observation_port`, and `host_runtime`.
These are the real places where a subcomponent can be replaced today, and
the offline checks already exercise them with fixtures.

### 3.4 The seams that are missing

| Concern | Observed today | Consequence |
|---|---|---|
| Model call | three call shapes: `services.model(ModelStepRequest)` in 8 modules, `session.invoke(ModelInvocationRequest)` in 21, and the harness semantic binding | a new model kind or a new record must be added in three places |
| Capabilities | `ADAPTIVE_CAPABILITIES` is a constant tuple inside the records module; `capability_directory.py` is a separate registry with locality, effects, and cost class | the Practitioner's capability list and the directory can drift; adding a capability edits the hub module |
| Verifier routes | `run_independent_verification` is a function whose `_call` uses the one shared session for design, file, review, judgment, and failure review | the judge cannot run on a cheaper or different route than the designer |
| Prompts and contracts | `prompt_fragments` imported by 12 modules; 45 `response_contract` uses, 14 of them inline `json.dumps` in the Practitioner | no registry of contracts with ids and versions; learning cannot group calls by contract |
| Recovery and routing | functions bound to the services object; the recovery panel, stall ladder, and route guard live in three modules | a different recovery policy is a code change, not a configuration |
| Folder ontology | `intelligence`, `kernel`, `runtime`, `governance`, `skills` hold READMEs; the code lives in `core` | the documented map and the executable map disagree |

### 3.5 Dead weight and drift

Observed: nine modules are never imported, not registered in the self-test
list, not in the boundary register, and not named by the command line:
`core/stage_store_records.py`, `generation/expansion.py`,
`generation/model/seeds.py`, `memory/query/receipts.py`, the
`memory/episodic`, `memory/procedural`, and `memory/working` packages,
`node/loop_node`, and the `strings` package initializer. Some are reached
through package initializers; each needs a stated owner or removal.

Naming drift: the package `code_nodes` carries "nodes" while the
Constitution forbids Node classes; the folder `embodiments` and the term
harness name one thing (the harness guide lives under `embodiments`);
"Solution Canvas", "solution matrix", "candidate canvases", and
"exploration canvas" describe two things (section 4).

Weight: `embodiments` holds 6.3 GB of ignored runtimes on disk; `artifacts`
holds 221 tracked files (two 17 MB audit files); `showcase` tracks 36 MB of
media; the checkout also holds 718 MB of untracked experiments. Documentation
has 647 files (67 verification records, 53 architecture documents, 32
research records, 26 prompt records) while the component guide has five
pages for 320 core modules.

## 4. The solutioning space and the solutions space

Owner requirement (September 18): the space where the Practitioner reasons
and builds is the solutioning space (the new name for what earlier notes
called the practitioner space or the build space); the space that holds
finished, reusable solutions is the solutions space, plural, because it must
hold several solutions for one task.

Observed vocabulary today:

| Term | Where | Count |
|---|---|---|
| Solution Canvas | documents 55, source 8, `terminology.yaml` term `core.term.solution_canvas` bound to `SolutionSpec` | the only registered term |
| candidate canvases, exploration canvas, matrix of candidates | `loop/canvas.py` (`Canvas`, `SolutionSlot`, `SolutionLoopCandidate`, `MatrixExecution`), adaptive results (`candidate_solution_canvases`, `selected_solution_canvas`) | data, no term |
| solutioning | documents 11, source 2 (`housekeeping.py` calls one lane "direct solutioning", `runtime_capacity.py`) | prose only |
| practitioner space, deliverable space | 2 documents each, both untracked working-tree documents from September 16 | conflicting names |
| solution matrix, matrix of solutions | 3 documents | older name |
| solutions space, solution space, build space | none | not present |

Observed in the four September 16 qualification trials: 2, 7, 7, and 22
candidate canvases were kept per run, and one was selected. So the plural
already exists as data. What does not exist is a typed record of the
solutions space for a task: which members exist, their graph digests,
their evidence and verification status, their applicability, and their cost,
so that a later run can choose among them or add to them.

Proposal N1 (nomenclature): add two terms to `terminology.yaml`:

```text
Solutioning space
├── the Practitioner's work for one task: its Loops, steps, evidence,
│   the task working folder, and the exploration canvas
├── replaces: practitioner space, build space
└── owns: candidate generation, verification, and the decision to publish

Solutions space
├── the set of published Solution Canvases for one task, each a member
│   with its LoopGraphDefinition, evidence, verification status,
│   applicability record, and measured cost
├── replaces: solution matrix, matrix of solutions, deliverable space
└── a Solution Canvas is one member; the space may hold several
```

Code identifiers (`SolutionSpec`, `Canvas`, `SolutionLoopCandidate`) stay
unchanged; documents adopt the two names; the two untracked September 16
documents are revised to them before landing.

Proposal N2 (record): a typed `SolutionsSpaceRecord` per task, owned beside
`code_nodes/solution_records.py`, that lists members with canvas reference,
graph digest, verification report digest, applicability conditions, cost,
and status (candidate, verified, superseded). Discriminating test: a run
that publishes a second verified canvas for the same task adds a member
instead of replacing the first.

## 5. A model call, not a language-model call

Owner requirement: wrap every model invocation as a model call, because a
reasoning step may need an image model, a tabular foundation model, a
forecasting model, a typed-judgment model, a small classifier, or a custom
trained model, not always a large language model; classify models with an
ontology; keep heavy models behind a service boundary so that a tool may
call a model but never load a large model inside itself.

Observed:

- `ModelInvocationRequest` fields: `prompt`, `system`, `model`,
  `temperature`, `semantic_call_id`, `output_allocation`,
  `response_expectation`, `response_admission_policy`,
  `harness_selection_scope`, `response_evaluation_ref`. Text in, text out.
- `ModelRoute.purposes` already declares a vocabulary of eleven purposes:
  counted generation, decide label, generation, reasoning, code, vision,
  tool use, embedding, reranking, query rewrite, structured extract.
  `ProviderSettings` declares endpoint, wire, locality, purposes, output
  capacity, context window, and authentication. `ModelProviderCapabilities`
  declares structured output, tool calls, and context size.
- `RoutePolicy` hardcodes `allow_local_counted_generation=False` with the
  comment "HARD rule: cloud-only now", and `runtime_settings.py` defaults it
  to false. The owner said on September 13 that cloud and local endpoints
  are both endpoints and should not be treated differently.
- `capability_directory.py` records for tools: locality, effects, cost
  class, input and output schema, ranking, health. Nothing records whether
  a tool loads a model, how large it is, or what hardware it needs.
- No route, provider, or capability record has an input modality other
  than text, an output kind other than text, a determinism declaration, a
  size class, a placement, or a training provenance. `task_fingerprint`'s
  `modality` describes tasks, not models.
- The model is reached through three call shapes (section 3.4).

Proposal M1 (one model call boundary): a `ModelCallRequest` in `core` with
`purpose` (the existing vocabulary, extended), `model_kind` (ontology below),
`inputs` (typed parts: text, image reference, table reference, series
reference, file digest), `output_contract_ref` and `suggested_output`
(section 6), `determinism_expectation`, `route_policy`, and `budget`; and a
`ModelCallRecord` response (section 6). The three existing call shapes
become adapters over it, so callers change once. Discriminating test: an
image classification purpose reaches a registered vision route without a
prompt string, and a text purpose reaches the existing gateway unchanged.

Proposal M2 (model ontology), as typed fields on routes and on tool
handshakes, not prose:

```text
Model ontology
├── kind: generative text, judgment, classification, extraction,
│   embedding, reranking, vision, forecasting, tabular foundation,
│   custom trained
├── determinism: deterministic, seeded, non-deterministic
├── size class: in-process small, local service, remote service
├── placement: in-process (declared memory ceiling), local endpoint,
│   remote endpoint
├── provenance: vendor foundation, open weights (digest), custom trained
│   (dataset digest, training record)
├── inputs and outputs: modalities and typed output kinds
├── measured: latency, cost per call, error among accepted cases,
│   cold start
└── qualification: candidate, qualified for purpose, retired
```

Proposal M3 (tools and models): a tool handshake declares `model_use`
(none, calls a model service, embeds a small model with a memory ceiling).
Conformance refuses a tool that embeds a model above the ceiling; heavy
models are always services. The route policy's locality rule becomes a
declared setting per route rather than a hardcoded default.

Owner note: a new endpoint with smaller models is expected while the Ollama
allowance is down. With M1 and M2 it is one more provider declaration with
purposes and a size class, not a code change.

## 6. Learnable records: prompts, suggested outputs, and metadata

Owner requirement: every model call should carry a suggested output (for
example "a two-dimensional array of candidate and confidence, top ten,
confidence from 0 to 100"), like a system instruction to answer in JSON but
specific, so that the records are consistent enough to learn and train from.

Observed, what one call records today:

| Layer | Record | Fields |
|---|---|---|
| Gateway | `ModelGatewayResult` | provider, model, route, thinking power, input and output tokens, attempts, semantic call id, owner Loop, prompt and system and request digests, transport codes, prompt envelopes, response admissions |
| Run History | `model_invocation` event | model, tokens, status, per Loop |
| Practitioner step | `context_pack_compiled`, `llm_work_packet_assembled` | packet id and digest, packet artifact reference, context block ids and digests, prompt assembly id, budget and trims |
| Practitioner step | completion event | step, format and transport attempt, output digest, admitted strategy, output bytes, output preview (truncated under quiet mode) |
| Lineage | `stage_action_lineage` | semantic call id joined to stage occurrence, action, execution, and verification outcome |
| Projections | `stage_evidence_projection` (SQLite), campaign DuckDB tables | records by namespace, occurrence, digest, payload |
| Contracts | 45 `response_contract` uses (14 inline in the Practitioner), `decision_schemas.SCHEMA_REGISTRY` (4 schemas), `output_templates.OUTPUT_TEMPLATE_REGISTRY` (7 forms with `recommend_form`), `ObservationExpectation` (built in 2 places) | partial infrastructure, not applied to every call |

Findings:

1. No call carries a typed suggested output. The registries for output
   forms and decision schemas exist but the Practitioner's contracts are
   JSON strings written inline, without ids or versions.
2. The pieces of one call can be joined through `semantic_call_id`,
   `packet_digest`, and artifact references, but no projection joins them.
   A training set has to be assembled by hand from six stores.
3. Full prompt text is retrievable only through artifact references; quiet
   mode truncates output previews, so a projection must read artifacts.
4. Nothing exports a training set, and nothing labels rows with holdout
   membership.

Proposal R1 (suggested output as a typed field): `SuggestedOutput` with
`form` (from `output_templates`), `shape` (a small grammar: scalar, list,
table with named columns, ranked list with a score column), `cardinality`
(top k), `confidence_scale` (0 to 100 or 0 to 1), `abstention_allowed`, and
`schema_ref`; attached to every `ModelCallRequest`; rendered into the
instruction; checked at admission.

Proposal R2 (contract registry): every response contract gets an id and a
version in `strings/decision_schemas.py` or a sibling registry; the inline
JSON strings become registry references; the registry is a versioned public
contract per `LE-VERSION-001`.

Proposal R3 (one joined record): `ModelCallRecord` rows in the stage
evidence projection: call id, run and Loop ids, step and pass, contract id
and version, suggested output, packet digest and block digests, route and
model kind, tokens, latency, cost, output digest and admission strategy,
grounding or judgment result, verification verdict, outcome label from
lineage, and holdout flag. Discriminating test: a `loop-engine records`
query returns, for one run, every call with its contract and its outcome
without reading artifacts.

Proposal R4 (training export): a command that writes the joined rows with
prompt and output bodies resolved from artifacts, holding secrets and
private material out by the existing exclusion rules, with a recorded
holdout split.

## 7. The questions a laboratory of engineers asks

Owner requirement: before each step the system should ask what an
engineering laboratory asks: with confidence from 0 to 100, what is the best
next step; is this step best served by a language model, a deterministic
model, or a trained model; would training our own model be more efficient;
do we have the data; what information does this node actually need; and
would adding variation to what we provide teach us where the boundary is.
The system should converge on the most efficient solution from historical
runs, data, knowledge, and prompts.

Observed:

- The interrogation bank has 31 questions in 10 categories and labels each
  as answerable by code (17), by a model (6), or either (8). This is the
  precedent for "is this best answered without a model".
- The question engine multiplies forms by personas and policies; the ask
  strategies include "are you sure" and masked asks; `cognitive_grammar.py`
  derives the operator catalog from the kernel and records what the runtime
  lacks; orientation carries a `confidence_profile`.
- `information_theory_evidence.py` estimates predictive information of
  state samples, and `context_budget.py` applies a typed budget: the
  measurement basis for "how much information does a step need" exists.
- Stage assistance runs paired arms (advisory against fresh), the
  generation package offers grid, random, vector warm start, and Optuna
  search, and campaigns freeze configuration spaces. These are the variation
  mechanisms.
- No portfolio asks the engineering questions above, no record stores their
  answers, no operation-level cost record exists, and no policy varies the
  information given to a step on purpose to find its boundary.

Proposal C1 (engineering question portfolio): a typed portfolio, in the
question engine's own format, of questions bound to plan time and to each
operation: best next step with confidence 0 to 100; implementation class
(read, reuse, compute, search, classify, control, model); whether a
deterministic or trained model would be cheaper; whether data exists to train
it and where; what evidence the step needs and what it can omit. Answers are
records, some answerable by code (from operation cost records), some by a
model. Discriminating test: a step whose answer is "deterministic" runs
without a model call and the record shows why.

Proposal C2 (information variation dimension): a declared campaign axis that
varies the packet given to a step (remove one context block, add one, halve
the budget, change the suggested output) with the outcome compared per
variation, so the boundary of sufficient information is measured rather than
assumed. Owner: `context_budget.py`, stage assistance experiment records.

Proposal C3 (operation cost records and convergence): per-operation cost,
implementation, and outcome rows (see the September 18 digest, section 7)
read by a selector that chooses the cheapest validated implementation per
operation and task family, with abstention when evidence is thin.

## 8. Ranked backlog

Ranked by the owner's stated priorities: separation first, then the two
spaces, then model calls and learnable records, then convergence. Effort is
small (a day), medium (a week), or large (more).

| Id | Item | Owner boundary | Effort | Discriminating test |
|---|---|---|---|---|
| L1 | Land the working tree in order: batch 13, OpenCode mechanisms, documents; fix the two documentation defects and the seven hardcoding findings first | `main` | small | continuous integration green on each commit |
| L2 | Move `.loop-engine-dev/stub-experiments-20260916` out of the checkout; add its location to the experiment README | repository | small | `git status` clean of it |
| S1 | Declare the package dependency direction and add a conformance gate | `_conformance_scan.py`, `forbidden_paths.json` | medium | a new upward import fails conformance |
| S2 | Move the model seam from `code_nodes` into `core` with compatibility imports | `solution_model_port.py` | medium | `core` no longer imports `code_nodes` for the seam |
| S3 | Execute the recorded split plans for the records module and the runtime; move inline self-tests to checks modules | 27 exception modules | large | exception list shrinks, check count constant |
| S4 | Make `ADAPTIVE_CAPABILITIES` a registry entry set read from the capability directory | `capability_directory.py` | medium | a capability added in the directory appears to the Practitioner |
| S5 | Give the verifier route ports (designer, reviewer, judge, failure review) | `independent_verification.py` | medium | the judge runs on a second route in a fixture |
| S6 | Resolve the nine unreferenced modules (own or remove) and the folder ontology (either populate the folders or point their READMEs at the code) | package layout | small | orphan count zero |
| N1 | Register the terms solutioning space and solutions space; revise the two September 16 documents; update the component guide | `terminology.yaml`, documents | small | terminology and documents agree |
| N2 | `SolutionsSpaceRecord` per task with members, status, evidence, applicability, cost | `code_nodes/solution_records.py` | medium | a second verified canvas becomes a member |
| M1 | One `ModelCallRequest` and `ModelCallRecord`; the three call shapes become adapters | `core` model seam | large | a vision purpose reaches a vision route without a prompt |
| M2 | Model ontology fields on routes and providers; retire the hardcoded cloud-only rule into a declared setting | `model_routes.py`, `runtime_settings.py` | medium | a local route with declared purposes is admitted |
| M3 | Tool handshakes declare model use and memory ceilings; conformance refuses embedded heavy models | `capability_directory.py` | medium | a handshake over the ceiling fails conformance |
| M4 | Declare the incoming small-model endpoint as a provider with purposes and size class | settings | small | the route registry lists it with its purposes |
| R1 | `SuggestedOutput` on every call, rendered and checked | `strings/output_templates.py`, admission | medium | a call with a ranked list of ten returns ten rows or abstains |
| R2 | Contract registry with ids and versions; inline contracts become references | `strings/decision_schemas.py` | medium | no inline `json.dumps` contract remains in the Practitioner |
| R3 | Joined `ModelCallRecord` rows in the stage evidence projection | `stage_evidence_projection.py` | medium | one query returns every call of a run with contract and outcome |
| R4 | Training export with holdout labels and exclusions | records command | medium | the export contains no secret-shaped value and a holdout column |
| C1 | Engineering question portfolio with recorded answers | `strings/question_engine.py`, planning | medium | a deterministic answer skips the model call |
| C2 | Information variation axis in campaigns | `context_budget.py`, campaign configuration | medium | a campaign reports outcome per variation |
| C3 | Operation cost records and the implementation selector | Run History projections, routing | large | the selector picks a cheaper validated implementation on held-out tasks |
| C4 | Reasoned choice before every deterministic fallback, as the engine's rule rather than the stub's | `recovery.py`, routing | medium | a fallback record shows the reasoned selection or its absence |
| X1 | Research: model ontologies and registries for mixed model kinds (vision, tabular foundation, forecasting, typed judgment), with candidate routes for each | research record | medium | a record with sources and a proposed route table |
| X2 | Research: cost-based semantic query optimization (Palimpzest and Abacus, cost-aware agentic execution) as a design input for C3 | research record | small | a record that maps their operators to Loop Engine operations |
| X3 | Research: training-set formats for tool-use and judgment fine-tuning, so R3 and R4 produce rows other tooling can consume | research record | small | a record with the chosen row schema |
| X4 | Research: the acquisition landscape named in the September 15 radar, with each company's product surface mapped to Loop Engine's layers | research record | medium | a record with sources per company |

## 9. Decisions for the owner

- Whether the package dependency direction in S1 is the one you want, or
  whether `code_nodes` should be renamed and reorganized at the same time.
- Whether the two terms in N1 are final: solutioning space and solutions
  space, with Solution Canvas as one member of the solutions space.
- Whether a typed-judgment service (hosted, text only) is an acceptable
  model kind under the privacy rules, or whether only local models qualify
  for task material.
- The provider declaration for the new small-model endpoint: name, wire,
  purposes, and whether it counts as evidence.
