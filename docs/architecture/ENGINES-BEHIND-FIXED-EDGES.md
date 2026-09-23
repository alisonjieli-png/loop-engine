# Engines behind fixed edges: how every functional component is wrapped, chosen and replaced

Kind: design. The single synthesis of three independent designs, written for
the owner, for the engineers and coding harnesses who build it, and for
reviewers.
Date: September 22, 2026.
Status: proposed. Nothing described as new in this document is implemented.
A statement marked **exists** was read from source on `main`. Everything else
is design.
Roadmap: delivery package D-19, "Engines behind fixed edges for every
functional component", with seven steps: S-6.30 (the shared engine
framework), S-6.31 (the harness executor slot), S-6.32 (hosted search as an
engine slot), S-6.40 (the library ingestion worker behind an ingestion engine
slot), S-6.41 (harness run records that feed engine selection and library
quality), S-6.42 (a fresh, independent harness instance for every step) and
S-6.60 (a layer before every model call that decides one model or several).
D-19 entered the roadmap at `7203492` with the first three steps; `4249eca`
added S-6.40 to S-6.42 and four verification items to S-6.30 (engine
preferences sent by a harness or a Loop, slots nested at every level, one
folder per functional component with one module per engine, and the earlier
custom loop-node engine kept restorable); `0f1c690`, which landed while this
revision was being checked, added S-6.60 and verification items to S-6.31,
S-6.40 and S-6.42. This document covers all seven. The work packages that build
it are in `ENGINE-IMPLEMENTATION-PLAN.md` beside this file.
Source state: this repository. The first draft read
`main` at `c96b546`; this revision was checked against `main` at `230c91e`
(September 22, afternoon). Between those revisions the engine-side source is
unchanged; the service side changed only in checks, web pages, the capacity
checks, the conformance report, the architecture map and the retirement of the
README title in `terminology.yaml` (section 2). Both architecture inventories
describe `97e805f`, whose engine and service source equals `c96b546`.
Deployed: pilot release 9 (Fly release v11), built from `81f341d`. The
repository was read, never changed, to write this.

## How to read this document

Sections 1 to 3 give the whole idea, the words and where engines sit inside
the one Loop runtime. Sections 4 to 6 give the anatomy of one engine slot, the
map and table of every functional component, and the records. Sections 7 to 10
explain registration, selection at run time, recording and measurement, and
evidence. Sections 11 and 12 are the procedures and the rules for a person or
coding harness that changes one engine. Sections 13 to 15 treat the three
slots that come first: the step executor, hosted search and the service slots.
Section 16 maps the configuration dimensions, section 17 lists the named
checks, section 18 separates what exists from what is planned, and section 19
records risks and decisions. Appendix A records how the three designs were
scored and what was taken from each. The final section, "Rules check",
records the adversarial check of this document against the repository rules
and the code, and every correction it made.

State words, used on every engine and component:

| Word | Meaning |
|---|---|
| exists | On `main`, reachable from live code, and its own checks run in the `main` self-test |
| exists, suite parked | On `main` and used by live code, but its own checks were retired from the self-test on September 21 |
| exists, no live caller | On `main` with collected checks, but the only production caller is parked |
| deployed | Running in the pilot image (Fly release v11) together with the live host file |
| built, off | In the image or on `main`, switched off by host configuration |
| main only | Committed on `main`, not in the deployed image |
| parked | Suite retired; the working implementation is frozen on `checkpoint/full-capability-2026-09-21` at `a3bd0f1` |
| planned | Named in a decision record, the roadmap or this design; no code |
| documented only | A written procedure or provider profile; nothing built |

## 1. The whole idea on one page

### 1.1 What the owner asked for

The owner's words, in time order (from the owner direction register of
September 22 and the repository decision records):

- September 19, 13:04: "build it out so we can easily turn on, turn off, and
  swap out components, so we have everything appropriately containerized,
  wrapped in wrappers. ... A wrapper around the database, so it always works
  the same way, so we can swap out the database, we can swap out the search
  and retrieval logic without requiring significant changes to the edges of
  those components. And that should be universal."
- September 19, 13:04: "That shouldn't be something that's done via CI/CD.
  That should be logic built into these wrappers, or wrappers of wrappers,
  that can do handshakes and make sure that it's initializing in the
  appropriate manner."
- September 19, 13:27: "for this particular task or atomic reasoning or build
  item, what is the most efficient, from a cheap, speed, etc. perspective,
  retrieval engine that should be used? If the first one doesn't work, we can
  try other ones. And that same thing for loop nodes."
- September 21, 14:08, recorded in the harness-first decision record: "we
  still need the layers, types, abstract classes, encapsulation, middlewares,
  etc to allow easily replacement, and switch out of different engines or
  harnesses."
- September 21, about 21:13: "turn them on and off without having to change
  too many edges between main components ... keep it clean to avoid confusion
  when using LLM harnesses".
- September 21, 23:11: "main components wrapped so that communication between
  components don't change (the edges stay the same) even though we can switch
  out the engines of each component".
- September 21, 23:14: "every functional unit should be wrapped so that we can
  replace the unit engine without impacting functional unit to unit edge
  communication".
- September 22, 13:36: "not only should we have swap points, but we should
  have 'engines' and different types of 'engines' for each functional
  component so that the runtime can select the most efficient engine, we can
  change, update and add new engines for each functionality component without
  having to significantly rewire things everywhere".

And the harness-first decision record, accepted September 21: "Every
executable step delegates to a standard harness ... through the existing
adapter contracts. The wrapper, comparison, middleware and adapter layers
stay, so any engine or harness can be replaced or added later", and "a host
chooses the executor the way it chooses a harness: by declared, tested
profile, not by import path."

### 1.2 The answer in one paragraph

Every functional component keeps one frozen, versioned edge contract: the
typed request and result records its neighbours send and receive. The
component's registered envelope Loop holds that edge constant. Inside the
envelope sits one engine slot, the owner's swap point, where engines of
declared kinds plug in through one small engine protocol. Engines stay in the
registry that already owns that kind of implementation; a descriptor is
computed from what each engine already declares, so no second source of truth
appears. A host declares, in one record shape per slot, which engines are
installed and switched on, the initial choice and the ordered fallbacks. One
effect-free selection procedure, run as a deterministic Loop, removes every
ineligible engine with a recorded reason, keeps the declared order unless
independently reviewed evidence for the exact same step reaches a declared
minimum sample and passes a declared rule that never lets a cheaper but worse
engine win, records the decision before anything runs, rechecks the chosen
engine at use, measures the attempt in the envelope, and falls back only on a
declared failure kind without resetting consumed authority. Adding, updating,
switching on or off, and retiring an engine touches the engine's own module,
one factory table row, its checks and the host configuration. No neighbour and
no call site changes, and a static check keeps it that way.

### 1.3 The five parts of every functional component

```text
Functional component (one job: step execution, model access, search, record storage, sign-in, ...)
├── Edge contract: what neighbours see; frozen for one contract version
│   ├── a typed request record and a typed result record, both versioned
│   ├── a declared "unavailable" result, so switching the component off is an answer, not a crash
│   └── interaction rows in data/component_interactions.yaml
│       (delivery, retry owner, timeout, cancellation, authority transfer, failure, Run History)
├── Envelope Loop: the registered boundary that holds the edge constant
│   ├── validates the request, selects, binds, dispatches and measures
│   ├── validates the engine's answer against the result record
│   └── records the decision, the attempt and any fallback in Run History
├── Engine slot: the owner's swap point, where engines plug in
│   ├── the engine protocol, versioned, checked at registration and again at use
│   ├── the engine kinds: the owner's "different types of engines"
│   ├── the factory table: the only code that names concrete engine classes
│   └── the registry that already holds this kind of implementation
├── Engines: interchangeable implementations, each with a computed descriptor
│   └── identity, kind, version, digest, capabilities, effects, isolation,
│       cost basis, availability, qualification, lifecycle, implementation location
└── Selection policy: declared by the host, versioned and digested
    ├── the initial choice and the ordered fallbacks, or an explicit "no fallback"
    ├── the ranking methods, with the declared order always last
    ├── the evidence rule and its minimum sample, only when the host enables it
    └── permitted narrowing by a Loop, and an optional side-by-side comparison
```

### 1.4 Thirteen rules that keep a swap local

The first ten rules are already enforced somewhere in the source (the
engine-side inventory verified each one). This design applies them to every
component and adds the last three.

| # | Rule | Where it is enforced |
|---:|---|---|
| 1 | One runtime vertex. Every engine runs inside a Loop and never becomes the runtime. | **exists**: `_LoopMeta` refuses subclassing (`loop_cannot_be_subclassed`); `forbidden_class_names` in `architecture.yaml` |
| 2 | Typed ports. Producers and consumers must match roles, modes and effect ceilings. | **exists**: `LoopContract`, `LoopConnectionSpec`, `LoopPortBinding` |
| 3 | Versioned records. Readers refuse unknown versions and unknown keys. | **exists**: every `record_type` of the form `name/vN` |
| 4 | Protocols, not base classes. Neighbours depend on a small surface. | **exists**: `ExternalHarnessAdapter`, `ProviderAdapter`, `CatalogStore`, `WorkspaceBackend`, `RetrievalSearchBackend` |
| 5 | Declared capabilities are compared before use; missing support refuses before any effect. | **exists**: `unmet_harness_requirements`, `negotiate`, `require_atomic_batch`, `screen_route`, `CapabilityHandshake` |
| 6 | Explicit registries. Importing registers nothing. | **exists**: `HarnessRegistry`, `AdapterRegistry`, `RouteRegistry`, the boundary registry |
| 7 | Selection by a declared record with an ordered fallback. | **exists** for harnesses, routes, stores and preference engines only |
| 8 | Choice never grants authority. | **exists** in part: `configuration_preference_decision/v1` and `loop_mode_policy_view/v1` record `execution_authority_granted: false`; `harness_selection_decision/v1` records only `task_accepted: false`; model route selection events carry neither flag; failover is a separate permission (`allow_failover` defaults to false). The common decision record of section 6.4 carries the flag on every slot |
| 9 | Revalidate at use. | **exists**: `HarnessRegistry.get`, `HarnessProcessSpec.validate_unchanged`, `CapabilityInvocationPolicy` |
| 10 | A named check for the known-wrong case, so removing a guard fails a check. | **exists** as the repository's `removed_*_is_detected` pattern |
| 11 | The envelope measures; an engine only reports. Engine-reported time, tokens or cost are kept apart and never ranked. | planned (section 9) |
| 12 | A decision exists before a dispatch. Every dispatch names the digest of an earlier selection decision. | planned (section 9) |
| 13 | One result shape per edge version. Every engine behind one slot returns the same record type and keys, proven by one conformance kit per slot. | planned (section 7.6) |

### 1.5 What changes for the people who operate and build the system

| Task | Today (observed in source) | With engine slots |
|---|---|---|
| Add a command-line harness | Edit six places in core code (the style tuple, the relay preparation chain, the relay's wire choice, the output extraction chain, the sandbox mount list, the identity digest list) plus special cases | Add one recipe module and one `harness_recipe/v1` record; a host adds one installation entry |
| Delegate a step to a harness | No typed step seam; the Loop takes an untyped handler function | The host binds a step executor engine; the owning Loop's one delegate handler never changes |
| Choose the served search engine or policy | Edit `ServiceHttpApplication._search`, which builds `Retriever(records)` with defaults | Change the initial choice in the host file and restart |
| Choose the service record store | Pass `open_store` in code; the host file names only a database path | Declare the store engine in the host file; the atomic batch capability is checked before any write |
| Switch an engine off | Remove its construction or its host block | Set `enabled: false` on its installation, or remove it from the policy |
| See what is installed and why it was chosen | Read code; harness selection (`harness_selection_decision/v1`), preference resolution (`configuration_preference_decision/v1`) and model route selection (`model.route.selected` events) each record a decision in its own shape; no other component records one | `loop-engine engines list`; every selection writes `engine_selection_decision/v1` |
| Send an engine preference from a harness or a Loop | Only the Loop's own code can choose; a harness cannot express a preference | A typed `engine_selection_override/v1` applied within the sender's authority (section 8.4) |
| Find the code of one engine | Search the 371 flat modules in `core/` (counted at `230c91e`) by name | One folder per functional component, one module per engine (section 7.8) |
| Let measured evidence choose the most efficient engine | Only harness selection ranks by reviewed evidence | Every slot can name reviewed evidence, a rule and a minimum sample |
| Bring back a parked capability | "behind the typed executor interface that phase 2 creates", which does not exist | A read-only restore plan, an owner decision, then the capability returns as a custom Loop harness engine of the step executor slot |
| Change one engine as a coding harness | Find every place its name is spelled; risk editing neighbours | One engine card lists the files that may change and the files that are edges |

### 1.6 What is deliberately not built

- No new runtime type, no graph vertex other than `Loop`, no subclass of
  `Loop`, and no class whose name ends in `Node`.
- No universal engine registry. Engines stay in `HarnessRegistry`,
  `AdapterRegistry`, `ModelGateway` with `RouteRegistry`, `McpRegistry`, the
  retrieval bindings, the decision factory table and the service loader's
  tables.
- No new event family and no new store. Decisions and measurements are new raw
  event kinds projected into existing canonical families; evidence is kept
  through the existing `CatalogStore` contract.
- No learned ranking, similarity routing or bandit before the declared run
  count of one million recorded runs, except an exact fingerprint at the
  atomic step level.
- No model call inside selection, and no authority granted by selection.
- No automatic fallback for anything chosen at release time (domain records,
  proxy, compute host, release pipeline). Destructive changes there stay with
  the owner.
- No import path in any host file. A host names engines by identity; code
  names classes only in factory tables.

## 2. Words, one meaning each

The owner asked for a system that stays "clean to avoid confusion when using
LLM harnesses". Each term below has exactly one meaning in this design and
gains an entry in `terminology.yaml` when the first slot lands. The owner says
"swap point"; the roadmap (D-19) says "engine slot". They are the same thing.
This design writes "engine slot", always in full, because "slot" alone already
names prompt slots.

| Term | Meaning | It is not |
|---|---|---|
| functional component | A part of the system with one job and one owner: step execution, model access, search, record storage, browser sign-in | A folder, a class or a graph vertex |
| edge contract | The versioned request and result records a functional component accepts and returns, plus its interaction rows | The engine protocol, which neighbours never see |
| edge | A declared interaction between two functional components in `data/component_interactions.yaml` | A call into one engine |
| envelope Loop | The registered boundary Loop that owns a component's work and holds its edge constant while engines change | A harness "wrapper layer" (section 13.8), which is a composition inside one executor engine |
| engine slot | The owner's swap point: one component's typed socket, fixing the edge contract, engine protocol, engine kinds, factory table, registry, selection rules and conformance kit | A prompt slot or a task preference slot |
| engine | One interchangeable implementation behind one engine slot, identified as `engine_id@version` with a content digest | Loop Engine (the repository, package and command) or the Loop runtime |
| engine kind | The owner's "type of engine": a closed, per-slot class of engines that share an isolation and cost profile, for example `agent_protocol_harness` | A run mode, a role, a profile or an intelligence family |
| engine protocol | The small method surface an engine slot calls on its engines | The edge contract |
| native declaration | What an engine already declares in its own registry, for example `HarnessAdapterInfo` or `StoreCapabilities` | The descriptor, which is computed from it |
| engine descriptor | The passive, digested projection of a native declaration into one common shape (`engine_descriptor/v1`) | Permission, qualification or a promise of behavior |
| executor profile | The step executor slot's own capability record inside its descriptors (`executor_profile/v1`) | A Loop role profile |
| engine installation | One host's declaration that an engine is installed, with typed settings and an explicit `enabled` flag | Permission to run it |
| slot configuration | The one host record per slot: installed engines plus the selection policy for each scope key | A grant |
| declared order | The host's initial choice followed by its ordered fallbacks | A ranking learned from data |
| selection decision | The recorded result of one selection, one fallback transition or one reuse, with every rejection reason | Task acceptance |
| engine preference | A typed request from a Loop or a harness to pin, exclude or prefer eligible engines, carried as `engine_selection_override/v1` and applied only within the sender's authority (section 8.4) | A grant, or an instruction read from prose or model output |
| nested slot | A slot whose engine is chosen inside the envelope of another slot's engine, with the parent decision recorded (section 4.6) | A second runtime, a graph vertex or a new relationship kind |
| qualification | An independent record that an engine passed its slot's conformance kit and trials at an exact installation digest, for a named scope and proof level | Availability (installed) or declaration (claimed) |
| lifecycle | The existing component lifecycle vocabulary: candidate, under_review, active, deprecated, rejected, archived | "Parked" |
| implementation location | Where an engine's working code lives: `main`, or the checkpoint branch at a named revision | A lifecycle state |
| scope fingerprint | The exact digest of the fields that make two attempts "the same step" for evidence | A similarity score |
| incumbent, challenger | The declared first eligible engine, and any other eligible engine that evidence might move ahead of it | The previous evidence winner |
| propensity | The probability with which the decision chose the engine: 1 under the declared order, the sampling rate for a comparison arm | A confidence |
| checkpoint branch | The git branch `checkpoint/full-capability-2026-09-21` at `a3bd0f1` | The spawned-task checkpoint record |

Existing uses of the word "engine" keep their meaning and fall inside this
vocabulary: the typed decision engines (`jev`, `circuit`, `system_one`) are
engines of the `typed_decision` slot; the preference engines of
`core/configuration_preferences.py` are engines of the `ranking_strategy`
slot; `SimilarityEngine` owns the `similarity_candidate_source` slot. One
existing use does not fall inside it: in the record store's native
declaration, `StoreCapabilities.engine` and `transactions.engine_version`
name the database software under an adapter (`sqlite` and the SQLite library
version), not an engine of this design. The engine of the `record_store` slot
is the adapter (`local.sqlite`); the database software and its version are
pinned software inside that engine's `implementation_digest` and `source`, and
the projection never copies `StoreCapabilities.engine` into `engine_id` or
`engine_version`.

The proper name Loop Engine keeps its definition. The first draft proposed
rewriting the `terminology.yaml` definition ("The repository, the engine, the
Python distribution ...") to say "the local runtime". That is withdrawn: the
owner's text in `AGENTS.md` calls the product's local part "a local engine",
and the README the owner asked for on September 22 (`230c91e`) names Loop
Engine "the open engine behind Baltor". Instead, two writing rules keep the
meanings apart. Technical documents write the proper name Loop Engine, or
"the local engine", for the product part, and write "engine" for an
implementation only with its slot or its identifier ("an engine of the
`step_executor` slot", "the engine `local.sqlite`"). `terminology.yaml` gains
the term "engine (of an engine slot)" with that qualification rule, and
`docs/architecture/SEMANTIC-AMBIGUITY-REGISTER.yaml`, the existing register
for words with two uses, gains an entry for "engine". Changing the owner's
own wording is not an engineering decision.

This design never writes "engine family": "family" already names the
intelligence serving axis, and the September 22 seam review found it overloaded
once already.

## 3. Where engines sit inside the one runtime

The complete classification first, as `AGENTS.md` requires:

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

The role profiles this design touches:

```text
Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution  (runs every engine selection and every envelope, deterministic)
│   └── self-improvement task  (may stage engine candidates; never approves them)
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence
│   │   └── serve, search, and frame  (the retrieval slots serve these Loops)
│   ├── Code Intelligence
│   │   └── resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence
│   │   └── search, replay, and compare  (holds compiled engine evidence)
│   └── User Feedback Intelligence
│       └── serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

Where engines sit:

```text
Engines inside the one runtime
└── Loop (the only operational runtime type)
    ├── owns work at a registered boundary (a row of core.boundary_registry.BOUNDARIES)
    │   └── that boundary's envelope reaches engines only through one engine slot
    │       ├── edge contract: request and result records, interaction rows
    │       ├── engine protocol: the surface every engine of the slot implements
    │       └── engines: adapters or strategies of declared kinds; never graph
    │           vertices, roles, modes, profiles or runtime types
    ├── choosing an engine is governed work: a deterministic Practitioner Loop
    │   (practitioner.code_execution) at the new boundary "component engine selection"
    └── the chosen engine is carried in the runtime context of the Loop that uses it
        ├── internal slots: InternalRuntimeMechanics.bindings
        ├── public capability groups: the three port objects
        └── service slots: attributes of ServiceHttpApplication, set once by the host loader
```

Four rules place engines inside that classification. First, an engine is an
adapter or a strategy used by a Loop, exactly as the extension ladder in
`docs/architecture/COMPONENT-EXTENSION-AND-PARAMETERIZATION-RULES.md` says:
"different algorithm behind one contract → strategy", "different provider,
backend, or protocol → adapter". Second, an engine's work always happens
inside the envelope Loop of its boundary, for example
`core.external_harness.run_external_harness` or
`core.model_gateway.invoke_model_gateway`. Third, a run mode, an engine kind,
an installation and a selection decision never grant model, file, network,
secret, spending or external-effect authority. Fourth, work that needs its own
goal, authority or Run History identity is another Loop, never an engine.

## 4. The anatomy of one engine slot

### 4.1 The shape every engine slot has

```text
Engine slot (one record engine_slot/v1 in data/engine_slots.yaml)
├── identity: slot_id, slot_version, title, function (for readers only)
├── joins to what already exists
│   ├── work boundaries: exact row names in core.boundary_registry.BOUNDARIES
│   ├── interactions: exact ids in data/component_interactions.yaml
│   ├── conformance suite: a suite the main self-test collects
│   ├── component folder: its row in data/component_folder_map.yaml (section 7.8)
│   └── nested under: the slots whose engines reach this slot through their
│       envelope's runtime context (section 4.6)
├── edge contract: read from the joined interaction rows, never restated in the slot
│   ├── one interaction row per supported request and result version pair, newest first
│   └── the declared unavailable result when no engine is eligible
├── engines
│   ├── engine protocol (dotted symbol) and its version
│   ├── engine kinds (closed list); for the step executor, which kinds count as delegation
│   ├── native registry, native declaration, descriptor projection (dotted symbols)
│   └── factory table (dotted symbol): the only place concrete classes are named
├── selection rules
│   ├── selection mode: one_of | set_of | derived
│   ├── selection phase: per_attempt | loop_start | host_start | release
│   ├── fallback ceiling: none | before_dispatch_only | after_failure_without_effects
│   ├── failure kinds this slot can report
│   ├── ranking objectives that make sense here, and the evidence floor
│   ├── scope class: the fields that form the scope fingerprint
│   └── binding site and whether a host that uses the boundary must bind an engine
└── housekeeping
    ├── retired engines (engine_retirement/v1 entries shipped by the release)
    ├── known direct construction sites (the shrinking baseline of the static guard)
    └── implementation state: active | candidate | planned
```

A slot is data shipped with a release. It changes rarely, only with code,
because a new function needs a boundary, a protocol and checks. Engines change
often and never need a slot change.

### 4.2 Worked example: the step executor slot

```text
Step execution (functional component)
├── Edge contract (target)
│   ├── step_run_request/v1: one step's typed assignment, authority, budget and requirements
│   └── step_run_result/v1: status, typed outputs, candidates, observed effects, accounting,
│       the executor identity actually used, and "delegated" computed by the envelope
├── Envelope Loop: core.step_execution.envelope.run_step_attempt (planned), a Spawned Loop of the owning Loop
├── Engine slot step_executor
│   ├── protocol: ExternalHarnessAdapter, contract external_harness_adapter/v2: info() and run_step()
│   ├── kinds: agent_protocol_harness, native_protocol_harness, text_relay_harness,
│   │   custom_loop_harness, remote_agent (these count as delegation);
│   │   agent_framework_kit, direct_model_step, in_process_runner, typed_decision_step,
│   │   structural (these never count as delegation)
│   ├── factory table: core/step_execution/engines.py (planned; one module per engine
│   │   beside it in the same folder, section 7.8)
│   ├── registry: core.external_harness.HarnessRegistry (exists), extended
│   └── requirement comparison: core.harness_execution_contracts.unmet_harness_requirements (exists)
└── Engines: OpenCode through the Agent Client Protocol first; the 18 text relay recipes;
    the four framework kits; the overnight direct step; the parked in-process runners;
    the planned custom Loop harness
```

Section 13 is the full treatment.

### 4.3 Worked example: the record store slot

```text
Record storage (functional component)
├── Edge contract (exists)
│   ├── CatalogStore operations with IntelligenceQuery for reads
│   └── catalog_atomic_write_batch/v1 -> catalog_batch_acknowledgment/v1 for writes;
│       an unknown commit is never success
├── Envelopes: "remote intelligence service operation" and "managed record operation"
├── Engine slot record_store
│   ├── protocol: catalog.protocol.CatalogStore, with the optional AtomicCatalogStore extension
│   ├── kinds: embedded_database, file_engine, reference_memory, server_database
│   ├── factory table: catalog/record_store_engines.py (planned)
│   ├── registry: catalog.registry.AdapterRegistry (exists), extended with descriptors()
│   └── requirement comparison: catalog.handshake.negotiate and require_atomic_batch (exist)
├── Selection: one_of at host start; fallback ceiling none, because two stores
│   written as authorities would diverge
└── Engines: local.sqlite (deployed) and local.in-memory apply the atomic batch and its
    removal extension, catalog_atomic_write_batch/v2; local.duckdb, core.duckdb-files
    and core.package-jsonl declare neither; remote.postgres (planned, D-05)
```

### 4.4 Turning a component off is a declared answer on its edge

Every edge contract declares its unavailable result. The harness boundary
already has the status `unavailable`; the store handshake has the verdict
`incompatible`; a search can return an empty hit list with a reason. When a
host switches off every engine of a slot, neighbours receive that declared
result with the reason `no_eligible_engine`, which they already handle, instead
of a missing function. That is how a whole component is switched off without
changing an edge.

### 4.5 One engine, many settings: the identity rule

The owner asked for "multiple options / dimensions for each component/engine
that is wrapped". The rule that keeps those options governable:

```text
What makes an engine distinct
├── Engine identity = code plus any pinned software, digested (implementation_digest)
│   └── code that behaves differently is a different engine:
│       codex (text response recipe) and codex.workspace_tools are two engines,
│       each with its own recipe record and qualification
├── Engine installation = engine plus typed settings, digested (installation_digest)
│   ├── a setting that changes what the engine can do, or how it was qualified,
│   │   is part of the installation digest that qualification binds
│   │   (the exact model of a route, a recipe variant, an embedding space, a placement)
│   └── two installations of one engine with different settings are two choices
│       (two routes of one provider with two models)
└── Run parameter = a setting inside the qualified range (a timeout below the ceiling)
    └── recorded in the decision's settings digest, never a new engine
```

Each engine kind publishes its settings as a typed settings record named in the
slot's factory table. Its searchable dimensions are described by the existing
`configuration_target/v1` record and changed through the existing
`apply_configuration_as_loop`. Which engine runs and how it is configured stay
separate facts, and the decision records both digests.

### 4.6 Slots nest at every level

`AGENTS.md` asks for engines "at the component level and above and below it",
and roadmap S-6.30 verifies "slots nested at every level, from a whole step
down to search and model access". Nesting uses only what the runtime already
has; it adds no runtime type, no relationship kind and no graph vertex.

```text
Nested slots, one example
└── One step, owned by its Loop
    ├── intelligence_search_retrieval_port (the owning Loop selects the step's material
    │   │   before launch; bodies load only after selection)
    │   └── catalogue_search_policy
    │       ├── record_store (the cards the stages rank)
    │       ├── retrieval_lexical_stage
    │       └── retrieval_vector_stage (its embedding space is part of the installation)
    └── step_executor (the harness that performs the step; per_attempt)
        ├── harness_instruction_files (derived from the bound executor's instruction style)
        ├── process_confinement (derived from the executor profile's isolation)
        ├── model_call_strategy (one model or several, roadmap S-6.60)
        │   └── model_access (every physical call the harness makes, through the broker)
        ├── tool_protocol_transport (each protocol server the step may reach)
        └── workspace_backend (the confined work folder)
```

Four rules make a nested slot safe:

1. **Reach only through the envelope.** An engine uses another slot only
   through the runtime context of its own envelope Loop, where the nested
   slot's binding lives. `LoopRuntimeContext.derive` already only narrows, so a
   nested engine never holds a binding, grant or budget its parent does not
   hold (Constitution LE-PERM-001).
2. **Record the parent.** A nested selection's decision carries
   `parent_decision_digest`, the digest of the decision that bound the engine
   whose envelope asked. Run History can therefore show which step engine
   caused which model route choice.
3. **Fix the parent in the scope where it matters.** Where the parent's
   engine changes what the nested engine does (a harness and the model route
   it calls), the parent's installation digest is part of the nested slot's
   scope fingerprint, or the pair is selected jointly (section 8.11), so
   evidence measured under one parent never ranks engines under another.
   Where it does not (the record store under search), the slot record says
   so, and evidence is not split without a reason.
4. **Account once.** A nested attempt's model calls, tokens, time and cost are
   counted once, in the nested envelope, and summed into the parent's consumed
   authority; they are never counted again by the parent's envelope.

Selection itself is not nested without end: the selection Loop and its ranking
engines take their order from declared values and never from another
selection (the base case of section 8.2).

## 5. Every functional component

### 5.1 The map

Every component in the two architecture inventories (engine side E1 to E26,
service side C1 to C19) lands in exactly one branch of this tree. Section 5.7
is the coverage map from inventory record to row.

```text
Loop Engine and the Baltor service, by functional component
├── A. Fixed frame: holds the edges, never swapped (section 5.5)
│   ├── the Loop runtime, role profiles, run mode policy, step profile
│   ├── typed contracts and ports, the boundary registry, Run History and event vocabulary
│   ├── the host configuration loader and the transport kernel
│   └── the selection mechanism itself
├── B. Engine slots chosen at run time on the engine side (table 5.2)
│   ├── work: step_executor, harness_instruction_files, process_confinement, workspace_backend
│   ├── models and judgments: model_call_strategy (planned, roadmap S-6.60), model_access,
│   │   typed_decision, response_evaluator
│   ├── search: retrieval_lexical_stage, retrieval_vector_stage, retrieval_rerank_stage,
│   │   catalogue_search_policy
│   ├── records and memory: record_store, runtime_memory, similarity_candidate_source
│   ├── library growth: library_ingestion_source (planned, roadmap S-6.40)
│   ├── tools and public ports: tool_protocol_transport, intelligence_search_retrieval_port,
│   │   web_research_port, custom_plugins_port
│   └── mechanics: ranking_strategy, configuration_setter, run_history_export
├── C. Engine slots chosen when the hosted service starts (table 5.3)
│   ├── identity and access: browser_identity_provider, credential_authentication
│   ├── account and money: account_email_delivery, payment_provider, usage_export
│   ├── catalogue: catalogue_body_store, catalogue_qualification_resolver, hosted search
│   ├── protocol and state: protocol_endpoint, record_store (service scope), request_limit_state
│   └── operations: failure_journal, secret_resolver
├── D. Engine slots chosen at release time by the operator (table 5.4)
│   ├── domain_name_records, edge_proxy, compute_host, web_server_process, release_executor
│   └── web_page_delivery, customer_client_recipe, material_install_layout
└── E. Policies and settings that shape slots but are not engines (section 5.6)
    ├── intelligence family policy, licence policy, entitlement sources
    ├── skill front-matter policies, contract match modes, route purpose policy
    └── wrapper composition, native control ownership, placement (executor installation settings)
```

### 5.2 Engine slots on the engine side

Selection column: mode; phase; fallback ceiling; where the declaration comes
from. Checks column: an existing check (**exists**) and new checks, each with
its known-wrong case in brackets. Section 17 lists the framework and first-slot
checks; section 17.8 lists every remaining slot check from tables 5.2 to 5.4
with its known-wrong case.

| Engine slot (inventory) | Function | Edge contract | Engine protocol | Engines and their state | Selection | Checks |
|---|---|---|---|---|---|---|
| `step_executor` (E5, E6, E10, E11, E24, E25) | Perform one step's assignment (section 13.1) in a separately started harness and return typed outputs to the owning Loop; completion is never acceptance | Target `step_run_request/v1` -> `step_run_result/v1`. Today an untyped `handler(loop, step, context)` and, for harnesses, `harness_request_identity/v3` -> `external_harness_result/v3`, shaped as one model response | `ExternalHarnessAdapter` under contract `external_harness_adapter/v2`: `info()` and `run_step()` (today `info()` and `run()`, duck typed) | Delegating kinds: `agent_protocol_harness` OpenCode first, Goose second (planned); `native_protocol_harness` Codex app-server, Claude Code stream mode, Pi remote control (planned); `text_relay_harness` 18 recipe styles (exists, no live caller; offline qualified: codex, openinterpreter_rust, nanocode, trae_agent); `custom_loop_harness` (planned, after a large user base); `remote_agent` (deferred). Never delegation: `agent_framework_kit` pydantic_ai, deep_agents, openai_agents, microsoft_agent_framework (exists, isolation none, packages absent); `direct_model_step` overnight night runner (exists, bypasses the gateway); `in_process_runner` solve, kernel, delegation, Solution Canvas, campaign, Kaggle, OpenCode step session (parked); `typed_decision_step` (planned); `structural` `default_handler` (exists, deterministic only) | `one_of`; `per_attempt`; `after_failure_without_effects`; host settings `engines.step_executor` or projected from `harness.json` plus `HarnessFallbackPolicy`; joint with `model_access`; delegation required for hybrid and model-led modes | **exists** `adapter_completion_does_not_claim_task_acceptance`, `fallback_never_resets_call_allowance`; new `a_delegation_claim_cannot_be_met_by_an_in_process_engine` [a framework kit, or an in-process runner registered as `opencode_local`, accepted for a step that requires delegation]; `a_harness_without_a_proven_fresh_instance_is_ineligible_for_one_harness_per_step` [a harness whose instance reads a user-level configuration file or a previous step's session selected for a step; roadmap S-6.42] |
| `harness_instruction_files` (E14) | Write the instruction file a harness instance reads before it starts | `InstructionMaterial` with `node_assignment/v3` -> `instance_instruction_file/v1`; `instance_instruction_verification/v1` | `InstanceInstructionWriter.write_for()` | `STYLE_FILES` rows: claude_code (AGENTS.md plus a CLAUDE.md that imports it), gemini_cli, qwen_code, codex (32 KiB ceiling), windsurf, factory, default AGENTS.md (exists; native loading never observed) | `derived` from the bound step engine's instruction style; ceiling none | **exists** `core.instance_instructions` suite; new `instruction_style_follows_the_bound_step_engine` [a CLAUDE.md composed for a codex engine]; `an_instruction_file_is_not_counted_as_loaded_without_an_observation` [file presence counted while `instruction_loading_observed: false`] |
| `process_confinement` (E21, harness part) | The sandbox a harness process runs in | `confined_environment/v1` and the process identity it produces | Planned `ProcessConfinementBackend`: `availability()`, `launch_arguments(request)`; today built inside `run_harness_process` | Bubblewrap at `/usr/bin/bwrap`, all namespaces unshared (exists, Linux only); Bubblewrap with one egress proxy and a domain allowlist from the step's authority (planned; design copied from the Anthropic sandbox runtime); container by image digest, then gVisor `runsc` (planned); E2B, Modal (planned, remote, need spending authority) | `derived` from the executor profile's isolation; `loop_start`; ceiling none: never fall back to weaker isolation | **exists** `host_configuration_and_credentials_are_not_inherited`; new `harness_process_refuses_without_an_available_confinement_engine` [a process started unconfined because `bwrap` is missing] |
| `workspace_backend` (E21) | Confined file, command and snapshot effects for a Loop | `FileRequest`, `CommandRequest`, `SnapshotRequest` -> typed results; no record types today (planned `workspace_file_request/v1`, `workspace_command_request/v1`, `workspace_snapshot_request/v1`) | `WorkspaceBackend`: `reference`, `availability`, `file`, `command`, `snapshot` | `restricted_local` (exists); `docker` (exists; availability checks only that the binary exists); `e2b`, `modal` (declared only, every operation `adapter_not_registered`) | `one_of`; `loop_start`; `before_dispatch_only`; untrusted code requires `container` or `remote` | **exists** `core.workspace_backends`, `core.workspace_operations`; new `untrusted_code_is_never_placed_in_the_restricted_local_backend` [an untrusted command selecting `restricted_local`]; `workspace_engine_availability_is_not_runtime_verification` [Docker qualified because the binary is on the path] |
| `model_access` (E15, E12 kind) | One semantic model call, each physical attempt in its own Loop, with call and token limits | `ModelGatewayRequest` with `ModelGatewayConfig` (the catalogue row names it `model_invocation_request/v1`; not serialized today) -> `model_gateway_result/v1`, `v2` with evaluations | `ProviderAdapter`: `chat_maxout`, `verify`, `live_models`, `output_capability_for`, `DEFAULT_MODEL`, wrapped by `ProviderSpec`; one engine is one route | `cloud_provider_route`: ollama_cloud (exists; its one authorized route answered `usage_limit_reached` on September 18), mistral and openrouter (exists, suites parked), openai Responses (only when a caller supplies it); `organization_endpoint_route`, `local_endpoint_route`: custom endpoints on the openai or ollama wire (exists, suite parked), `local.slm`, `local.embed` (policy gated); `harness_brokered_response`: `HarnessSemanticBinding` (exists, only consumer parked). No native Anthropic wire | `one_of` per attempt; scope key = thinking power; projected from `models.tiers`; cross-provider fallback only with `allow_failover` in the run contract | **exists** `unknown_output_capability_refuses_before_provider_use`, `default_gateway_does_not_enable_cross_provider_failover`; new `no_caller_reaches_a_provider_except_through_model_access` [the overnight runner's direct `make_adapter(endpoint).chat(...)`] |
| `model_call_strategy` (roadmap S-6.60; no inventory record) | Decide, before a model call, whether one model answers or several, and how their answers are combined; every physical call still goes through `model_access` | Planned: the step's model request and the preferences the harness or step sets in, one typed answer out with every physical call, its usage and cost, the chosen strategy and its reason; agreement among models is recorded as evidence, never as acceptance | Planned `ModelCallStrategy`: `plan(request, allowance)` and `run(plan, model_access)` | pass-through (planned, the default and the first engine: exactly today's single call); one model chosen from the models the customer configured; a vote among several models; a disagreement chain that asks the models to answer each other; a resolution chain that settles a disagreement by a named method (all planned). The Solution role's ensemble profile and `examples/18_three_model_ensemble` (a machine-learning ensemble with no model calls) are the nearest existing pieces; neither is a strategy engine | `one_of`; `per_attempt`; nested between `step_executor` and `model_access` (section 4.6); `before_dispatch_only`; a strategy is eligible only when the step's budget and authority allow every call it will make | new `a_strategy_that_needs_more_calls_than_the_step_allows_is_refused_before_the_first_call` [a three-model vote started under an allowance of two calls]; `agreement_among_models_is_evidence_never_acceptance` [a unanimous vote recorded as an accepted result] |
| `typed_decision` (E16) | A closed-set judgment from a decision endpoint, admitted as a typed answer | `decision_batch_request/v1` -> `decision_batch_result/v1`; provider capability `typed_decisions/v1` | `ProviderSpec` offering `decide_questions`, `prepare_decisions`, `decision_capabilities` | `decision_endpoint`: jev, circuit, system_one (exists; `live_provider_qualified: false`) | `one_of`; per request; projected from `decision_host_configuration/v2`; failover only when declared | **exists** `core.decisions.contracts`, `core.decisions.jev`; new `an_unqualified_decision_endpoint_is_not_selected_by_default` [jev chosen with `allow_unqualified` false]; `decision_confidence_is_not_an_accepted_outcome` [a reported 0.95 counted as accepted] |
| `response_evaluator` (E12) | Check an admitted response against an independently registered obligation; the only source of "accepted" in measurement | Response and `ResponseEvaluationContext` -> `harness_response_evaluation/v1` or `v2`: passed, rejected, inconclusive | `HarnessResponseEvaluator.evaluate` | Registered deterministic evaluators (exists); model-led evaluation through the gateway with route separation (exists); independent task verification (parked) | `derived` from the exact evaluation contract; never ranked, because it defines what accepted means | **exists** `missing_evaluator_refuses_before_provider_dispatch`; new `an_engine_cannot_evaluate_its_own_output` [evaluator digest equal to the producing engine's] |
| `retrieval_lexical_stage` (E18) | The word-match stage of search over small cards; bodies stay behind references | `retrieval_query/v1` -> `retrieval_candidates/v1`; the surface returns `retrieval/v1` | `RetrievalSearchBackend.search(query, top_n)`; host engines bound by `RetrievalBackendBinding` with a `CapabilityHandshake` | fts5 (exists, default, deployed); store (exists); lancedb (optional, not in the serving extra); an fts5 all-terms variant as its own engine, bm25s (planned); tantivy, OpenSearch (documented only) | `one_of`; `loop_start` on the engine side (settings `search:`), `host_start` on the service; `before_dispatch_only` | **exists** the `core.retrieval` canaries; new `served_search_uses_the_engine_and_policy_the_host_declared` [today's `Retriever(records)` defaults] |
| `retrieval_vector_stage` (E18) | The similarity stage of search | As above, plus an exact `EmbeddingSpace` (model, revision, dimensions) | As above; a vector binding must declare its embedding space | hash (exists, default, deployed); model2vec potion-base-8M (optional; its revision is the literal "hf-cache-pin" and must become a commit hash); fastembed, a Qdrant binding (planned) | As above; the embedding space is part of the installation digest | **exists** the `require_same_space` refusal; new `equal_dimensions_do_not_establish_embedding_compatibility` [two spaces with equal dimensions and different models compared] |
| `retrieval_rerank_stage` (planned) | Reorder fused candidates | `retrieval_candidates/v1` -> `retrieval_candidates/v1` | A third stage in `STAGES`, added only when an engine exists | none (default); FlashRank, model-judged ranking (planned; the second needs model authority) | Added only after the evaluation shows a gap on held-back queries | new `a_rerank_stage_cannot_add_candidates_the_earlier_stages_did_not_return` [a reranker that returns an item absent from the fused candidate list] |
| `catalogue_search_policy` (E18, C11) | The matching and ranking strategy applied to catalogue search | Search request -> ranked, body-free references (`harness_intelligence_search_result/v1`) | A `CatalogueSearchPolicy` record, `harness_intelligence_search_policy/v1` (`v2` adds the relevance floor) | `served_before_2026_09_21`, what the service serves implicitly (exists); `purpose_match_default`, the measured `DEFAULT_SEARCH_POLICY` (exists, no caller; measured on 354 queries over 123 items) | `one_of`; `host_start`; switching needs a recorded comparison | **exists** `a_policy_names_its_match_mode_and_the_fields_it_reads`; new `a_query_with_no_good_match_says_so` [the best poor items returned as if they matched] |
| `record_store` (E17, C13) | One backend-neutral durable record contract for intelligence and service state | `CatalogStore` operations with `IntelligenceQuery`; writes `catalog_atomic_write_batch/v1` -> `catalog_batch_acknowledgment/v1` | `CatalogStore`, optional `AtomicCatalogStore`, `StoreCapabilities`, `negotiate()` | `embedded_database`: local.sqlite (exists, deployed, the only adapter with the atomic batch), local.duckdb (exists, no atomic batch); `file_engine`: core.duckdb-files, core.package-jsonl (read only); `reference_memory`: local.in-memory; `server_database`: remote.postgres (planned, D-05) | `one_of`; `host_start`; ceiling none (never two authorities) | **exists** `atomic_batch_conflict_writes_nothing`, `unknown_commit_is_not_success_and_exact_retry_reconciles_once`; new `a_store_without_the_atomic_batch_cannot_serve_service_writes` [local.duckdb declared for the service stops the host] |
| `similarity_candidate_source` (E20) | Find prior work that resembles the task, as evidence only | `task_similarity/v1` -> `similarity_hit/v1`, each hit naming its source | `SimilarityCandidateSource.find_candidates()` | LibraryCandidateSource (exists; reads the parked `solution_library`); FacetCandidateSource (exists) | `set_of` by source role; merged, never ranked | **exists** `facet_order_cannot_change_similarity_results`; new `similarity_hits_never_become_engine_selection_evidence` [a similar run used to reorder engines] |
| `runtime_memory` (E19, run-scoped part) | Notes shared by sibling Loops of one run; never persistent intelligence | `RuntimeMemoryService` (`loop/spawned_runtime_port.py`) write, read, search (no record type today) | Same | RunNoteBoard (exists) | `one_of` per run; switching off = not binding it | **exists** `core.runtime_memory`; new `runtime_memory_is_not_visible_to_another_run` [a note written in one run returned by a search in another run] |
| `library_ingestion_source` (roadmap S-6.40; no inventory record) | Bring outside harness material (skills, context files, plugin declarations, protocol server configurations) into the library as candidates with source, revision, licence and digest | Planned `library_candidate_request/v1` -> `library_candidate_batch/v1`; every item a candidate, never approved, carrying a versioned per-source provenance record (origin, immutable revision, path, source digest, licence evidence, fetch date) and, for a skill with scripts, references or assets, a multi-file package (roadmap S-6.40) | Planned `LibrarySourceReader`: `list_sources()`, `read_candidates(source, cursor)` | The offline preparer `tools/prepare_harness_candidates.py` (main; a tool today, not an engine); readers for public repositories, skill directories, and plugin and protocol server registries (planned) | `set_of` by source kind; `loop_start` of the scheduled ingestion Loop; `before_dispatch_only`; network authority comes from the ingestion Loop's grant, never from the reader | new `an_item_without_an_accepted_licence_is_never_imported_verbatim` [a body under a licence the host's licence policy does not accept copied into a candidate]; `an_ingested_item_stays_a_candidate_until_independent_review` [a reader that marks its own item approved]; `a_duplicate_item_is_merged_not_added` [one body digest added twice under two identifiers] |
| `tool_protocol_transport` (E22) | Reach a registered Model Context Protocol server's tools | `McpCallRequest` -> completed, failed, refused, approval_required, unavailable (no record type today) | `McpTransport`: `list_tools`, `call_tool` | in_process (exists); stdio, streamable_http, sse (exists; need the optional `mcp` package) | `derived` from the server declaration; ceiling none | **exists** `core.mcp_adapter`; new `a_tool_call_is_never_retried_on_another_transport` [a timed-out call repeated through a second transport] |
| `intelligence_search_retrieval_port` (E8) | Public capability group Intelligence Search and Retrieval | The port's capabilities plus the retrieval and provisioning edges | Port adapter | Retriever plus the intelligence layers (exists) | `loop_start`; `derive()` only narrows | **exists** `three_public_capability_groups_map_to_real_boundaries` |
| `web_research_port` (E8) | Public capability group Web Research | Untyped today; planned `web_research_request/v1` -> `web_research_result/v1` with source identity, time and licence | Planned `WebResearchBackend` | brave_search, web_search, web_fetch (parked); planned kinds from the owner's list of September 19: plain request, search service, scripted browser, browser service, a harness's own browser plugin, a custom browser | `loop_start`; network authority required; turning it on is a recorded owner decision | new `the_web_research_port_reports_unavailable_on_main` [research recorded as done with no live engine] |
| `custom_plugins_port` (E8, E22) | Public capability group Custom Plugins | The `CapabilityHandshake` operations and schemas | Registered endpoints through `CapabilityDirectory.call` | Registered capability surfaces (directory parked but imported by live code); plugin bundles (checks parked); skills are admitted content, not engines | By operation | new `public_capability_groups_map_to_collected_boundaries` [Web Research mapped to a parked envelope] |
| `ranking_strategy` (E23) | Order already-eligible engines for every other slot | `PreferenceSnapshot` -> `PreferenceProposal`, recorded as `configuration_preference_decision/v1` | `rank()` and `descriptor()`, bound by `PreferenceEngineBinding` | declared order, explicit order, supplied agent proposal (exists); matched evidence ranker, paired efficiency ranker (planned); Thompson sampling (only after the adoption threshold) | `MetaPreferencePolicy` with a declared order only; never ranked by evidence | **exists** `preference_cannot_restore_a_hard_rejected_harness`, `active_selector_cycle_refuses_without_fallback`; new `ranking_policy_must_end_with_the_declared_order` [`engine_order: [evidence-ranker]` alone] |
| `configuration_setter` (E23) | Apply one checked configuration change | `apply_configuration_as_loop` request -> new value and change record | A setter backend bound to `ConfigurationSettingSpec` | In-memory field binding (exists); file, command and remote setters (planned) | By the target's declared setter | **exists** `authority_bearing_is_refused` in `core/configuration_setter_checks.py`, the check behind the `architecture.yaml` invariant `authority_bearing_settings_are_not_generic_setter_targets`; new `enable_and_disable_change_only_the_installation_flag` [a disable command that also edits the selection policy or another installation] |
| `run_history_export` (boundary "OpenTelemetry export") | Export saved runs for outside tools | Run History -> spans or trajectories | Exporter | OpenTelemetry span exporter (parked; exports zero durations and the non-conforming span name `gen_ai.request`); trajectory export in the shape of the Agent Trajectory Interchange Format, version 1.7, the trajectory format of the Harbor evaluation framework (planned) | `set_of` by destination | new `an_exported_attempt_span_has_its_measured_duration` [a span exported with equal start and end times, as the parked exporter does today]; `exported_spans_carry_no_prompt_or_secret` [a span attribute holding prompt text or an authorization header value] |

### 5.3 Engine slots chosen when the hosted service starts

All of these select inside the host loader, which stays the one wiring point
but reads engine rows instead of naming classes. Their boundary row is "remote
intelligence service operation" (envelope `invoke_http_service_as_loop`),
except search, whose row is "remote intelligence metadata search".

| Engine slot (inventory) | Function | Edge contract | Engine protocol | Engines and their state | Selection | Checks |
|---|---|---|---|---|---|---|
| `browser_identity_provider` (C7d) | Verify a browser access token and map issuer and subject to a durable tenant; `/mcp` never accepts a browser token | Adapter `protocol_version = browser_identity/v1`; records `service_subject_tenant_registration/v1`, `service_browser_session_revocation/v1`; every path ends in `service_principal/v1` | The `BrowserIdentityAdapter` surface the authenticator calls | `supabase_user/v1` (deployed since Fly v9; account creation closed) | `one_of`; projected from `browser_identity.provider_profile`; ceiling none | **exists** `activation_rejects_client_supplied_tenant_and_authority`, 15 more; new `removed_browser_identity_protocol_check_is_detected` [a `browser_identity/v2` adapter installed once the comparison is patched out] |
| `credential_authentication` (C7a, C7b, C7c, C7e) | Turn one bearer credential into one in-process principal, rechecked at every use | `Authorization: Bearer` -> `service_principal/v1`; keys `service_key/v1`, `service_key/v2` | The modes of `ServiceHttpAuthentication` | Host key, personal client keys, administrator (deployed); external token for `/mcp` (built, off) | `set_of`, dispatched by credential form and route; never ranked | **exists** `key_revocation_invalidates_previously_issued_principals`, `removed_key_version_change_is_detected`; new `a_mode_the_host_did_not_enable_cannot_authenticate` [an external token accepted with `external_jwt` absent] |
| `account_email_delivery` (C8) | Sign-up and recovery email that stays on the baltor.ai domain | Adapter `account_email/v1`; `service_account_signup_request/v1` -> `service_account_signup_result/v1` and the recovery pair; the same answer whether or not the address has an account | `AccountEmailAdapter` with two transports | `supabase_generate_link_and_resend_send/v1` (main only; no mail credential staged); identity-provider-sent mail through Resend SMTP (documented only; needs a permission engineering lacks); the operator invitation tool is a tool, not an engine | `one_of`; projected from the `account_email` block; `before_dispatch_only`: an uncertain send is reconciled, never repeated | **exists** 71 checks and 9 removed-guard controls; new `an_uncertain_send_blocks_every_fallback` [a timed-out send followed by a send through another engine] |
| `payment_provider` (C9a, C9b) | Checkout and portal sessions, one provider customer per account, verified subscription events turned into the entitlement | Provider-neutral part: `billing_session_request/v1` -> `billing_session_result/v1`, `billing_session_options/v1`; entitlement only through `ServiceRuntime` records. Provider-shaped today: `service_stripe_event/v1`, the `stripe_*` records, entitlement source `stripe_snapshot` | Today the loader builds three Stripe objects by name, and the transport calls two attributes: `billing_processor.handle(raw_body, signature_header)` and `billing_sessions.options`, `create` and `configure_policy`; the subscription reader works inside the event processor as its resolver. Planned: one surface `billing_provider/v1` that names exactly the methods the transport already calls, so no neighbour changes | Stripe (deployed on the live account; no real subscription processed yet). Live and test mode are settings of one engine | `one_of`; ceiling none | **exists** `webhook_does_not_accept_unsigned_or_wrongly_signed_subscription_authority`, `removed_customer_search_before_creation_is_detected`; new `removed_webhook_signature_check_is_detected` [an unsigned subscription event accepted once the signature check is patched out]; `live_account_engine_refuses_a_test_key` [a test key staged where the live account is configured] |
| `usage_export` (planned, research of September 22) | Send metered usage to a billing system | `durable_tenant_usage/v1` -> provider meter events | Planned | none (default); Stripe Billing Meters with a count meter (planned, only when a priced overage exists, because a meter's settings are fixed at creation) | `one_of`; sending meter events is an external effect that needs its own network and external-mutation authority in the host file, which choosing the engine never grants | new `a_meter_event_is_sent_once_per_usage_record` [a retry after a lost acknowledgment sends a second meter event for one usage record] |
| `catalogue_body_store` (C10) | Hand exact approved bytes to delivery | Body read bound to `expected_digest`; `service_download/v1` with `X-Content-SHA256`; inline up to 16 KiB | The body reader from `load_host_manifest`, which rechecks path and size | Files in the image under `/opt/baltor/catalogue` (deployed; a catalogue change needs a release); private object storage (planned, D-05) | `one_of`; ceiling none | **exists** `selected_digest_mismatch_refuses_before_body_read_and_metering`; new `body_store_engine_switch_serves_identical_digests` [an object store returning re-encoded bytes] |
| `catalogue_qualification_resolver` (C10) | Decide whether an item binding is approved for serving | `ProvisioningQualification`: binding, decision, basis, reference | `ProvisioningQualificationResolver` | `host_manifest_review/v1`, basis `host_attested` (deployed); an independent authoritative resolver (planned) | `one_of`; from the manifest's declared basis | **exists** `host_review_is_bound_to_exact_bytes_not_only_an_item_name`; new `host_attestation_is_never_reported_as_independent_qualification` [a provisioning or capabilities record that reports the basis `host_attested` as independent qualification] |
| hosted search (C11) | Search the caller's authorized metadata and return references, never bodies | `service_retrieval_request/v2` -> `service_retrieval_result/v1` (`v2` planned in S-6.32 to carry the "no good match" signal) | The slots `retrieval_lexical_stage`, `retrieval_vector_stage` and `catalogue_search_policy` at scope `hosted_catalogue_metadata` | fts5 plus hash with the implicit policy (deployed; index rebuilt on every request; capabilities report fixed backend names) | `host_start` | **exists** `protocol_search_returns_typed_authorized_references_without_bodies`; new `hosted_capabilities_name_the_bound_retrieval_engines` [fixed strings while another engine is bound] |
| `protocol_endpoint` (C12) | Let a native harness list and call the five service tools | Tools `provisioning_discover`, `provisioning_list`, `provisioning_manifest`, `provisioning_read`, `intelligence_search`, each returning `service_http_result/v1`; exact version on `initialize` and on every later request | A server factory over the protocol software kit that serves `TOOL_OPERATIONS` for one exact version | Version `2025-11-25` through `mcp==1.29.1`, stateless Streamable HTTP (deployed); version `2026-07-28` through the 2.x kit (planned; the research recommends serving both by explicit negotiation) | `set_of` by protocol version; never a downgrade | **exists** `remote_protocol_refuses_unqualified_versions_without_silent_negotiation`; new `a_second_protocol_version_is_selected_only_by_exact_negotiation` [a request served under the older version when both sides support the newer] |
| `record_store`, service scope (C13) | All service state in one namespace | As in 5.2, plus: every write is one atomic batch with a read set | As in 5.2 | local.sqlite on one volume (deployed); remote.postgres (planned) | `host_start`; eligibility requires `authoritative`, `catalog_atomic_write_batch/v1` and `atomic_read_set` | **exists** `atomic_read_set_serializes_two_competing_writers`; new `a_store_fallback_is_refused_by_the_slot_ceiling` [a second store listed as a write fallback] |
| `request_limit_state` (C14) | Count failed attempts per client address | `service_request_limits/v1` (published as `service_failed_attempt_limit/v1`); refusal `service_request_limit_refusal/v1` | `FailedAttemptLimiter` | In-process tables (in the image, inactive in the live host file; main refuses a public binding without the header source); a shared store, a proxy-level limit (documented only) | `one_of`; ceiling none | **exists** 9 removed-guard controls, `a_caller_controlled_header_is_the_known_wrong_case`; new `multi_machine_service_refuses_an_in_process_limit_engine` [a host declaring more than one Machine starts with the in-process limiter tables, so each Machine counts separately] |
| `failure_journal` (C15) | A searchable reference for each refusal; "alive" kept apart from "ready" | `service_request_failure/v1`, `service_request_failure_list/v1`, `service_health/v2`, policy `service_observability_policy/v1` | Journal plus `readiness_report` | The in-service journal (main only and not wired, finding F1; its restoration is part of the September 22 consolidation) | `set_of`, zero or more sinks | 34 named checks that nothing runs today; new `the_health_route_serves_the_version_the_release_gate_expects` [route serves `service_health/v1` while the gate requires `v2`] |
| `secret_resolver` (C16) | Resolve a configured reference to a credential without ever recording it | `env:NAME` -> a value held in memory; refusals `unsupported_secret_resolver`, `configured_secret_unavailable` | `resolve(reference)` | Environment references with Fly secrets (deployed); another secret manager (documented only) | By scheme; no fallback, never to a less protected source | **exists** `server_secret_cannot_be_serialized_as_a_publishable_key`; new `no_secret_resolver_writes_a_value_to_a_record_event_or_measurement` [a resolved value, or a string with the shape of a staged key, found in a record, a ledger event or a cost record] |

### 5.4 Engine slots chosen at release time

These are chosen by the operator when a release is prepared, never at run
time and never by an automatic fallback. Destroying a record, a volume or an
application, or changing a name server delegation, needs the owner's
confirmation in the current conversation. The decision record is the release
record, `pilot_release_record/v2` with an engines map (planned).

| Engine slot (inventory) | Function | Edge the rest of the system depends on | Engines and their state | Checks |
|---|---|---|---|---|
| `domain_name_records` (C1) | Map each hostname to the service; carry certificate and mail records | Hostname to address or canonical name; the service answers only names in `allowed_hosts` | Cloudflare zone with unproxied records (deployed since September 20); the previous Namecheap delegation (saved rollback); Cloudflare proxy (documented only; it changes which header carries the client address) | evidence `domain-cutover-verification-2.json`; new `every_served_hostname_has_a_saved_evidence_record` [the four subdomains added September 21] |
| `edge_proxy` (C2) | Terminate encrypted connections, route, health-check, cap concurrency | Plain traffic to port 8080 with the original Host; the health check's Host `localhost:8080` | Fly proxy (deployed); Cloudflare proxy in front (documented only) | **exists** `test_service_profile_has_persistence_tls_and_a_real_server_command` |
| `compute_host` (C3) | Run the one service process beside its one volume | Image by digest, command, port 8080, `/data`, environment secrets | Fly Machines, one Machine in `iad` (deployed); thirteen other profiles (documented only) | **exists** `tools/check_fly_service_container.py`, `test_removed_guards_are_detected_by_their_counterexamples` |
| `web_server_process` (C5, server part) | Host the application object | `create_app()` and the `serve` command, proxy headers off | uvicorn with Starlette (deployed); other servers untested; a Vercel Python function (documented only) | **exists** `the_real_serve_command_stops_before_it_serves_the_public_without_the_limit` |
| `release_executor` (C18) | Build from a checked commit, deploy by digest, keep the previous digest | `pilot_release_record/v1` (`v2` planned with the engines map) | The guarded workflow `fly-pilot.yml` (used for release 8); a local build deployed by digest (release 9, recorded as a departure) | **exists** `test_workflow_is_manual_and_secrets_are_step_scoped`; new `a_release_record_names_every_bound_engine_and_its_digest` [a release record without the engines map, or naming an engine without its descriptor digest, accepted by the release check] |
| `web_page_delivery` (C6) | Public site, account pages, workspace, administrator dashboard | The page table in `web_pages.py`, `website_client_recipes/v2`, strict page headers | Pages served by the service process (deployed); a static host on a content network (documented only). The per-hostname surface map (worktree only) is a routing policy, not an engine | **exists** the hosted website checks, 60 in release 9 |
| `customer_client_recipe` (C19) | Tell each supported harness how to reach `/mcp` with `BALTOR_SERVICE_TOKEN` | `website_client_recipes/v2` | Codex, OpenCode 1.x, Claude Code (deployed on the Connect page) | new `adding_a_client_is_one_recipe_row_and_no_page_code_change` [a new client recipe that needs an edit to `service.js` or `index.html`] |
| `material_install_layout` (C19, installer) | Install selected material where a harness discovers it | Planned `harness_bundle_rendering/v1` | OpenCode skills layout in `tools/install_selected_material.py` (main); `.agents/skills` layout, an Agent Plugins 1.0.0 bundle, Claude Code and Codex plugin renderings (planned) | new `offered_fetched_installed_and_used_are_recorded_as_separate_facts` [an installation reported as use] |

### 5.5 The fixed frame: components that hold the edges and are never swapped

| Component (inventory) | Why it is not an engine slot | What it does for the slots |
|---|---|---|
| The Loop runtime: `Loop`, `LoopConfig`, `LoopLedger`, `LoopResult` (E1) | It is the envelope every engine runs inside; swapping it would make every edge unstable | Every attempt runs inside a Loop; the sealed class blocks subclassing |
| Role profiles and the profile handshake (E2) | Versioned behavior presets, data | Part of every scope fingerprint; `profile_handshake` should run at binding (roadmap D-12-T01) |
| Run mode policy (E3) | Policy over three closed modes | Installed executor modes become backed by a bound step executor engine (section 13.9) |
| Step profile and step templates (E4) | Data | Declare which steps call the step executor |
| Typed Loop contract and ports (E7) | The edge mechanism itself | Edge contracts use `LoopContract` roles; each contract declares its match mode (exact, canonical, purpose, semantic with blocking keys, model judged) |
| Operational boundary registry (E9) | The index of work boundaries | Joined by name to the engine slot catalogue; `boundary_report()` lists the slot index |
| Run History and the event vocabulary | The one record of every decision and attempt | Extended with five raw event kinds, no new family |
| Host configuration loader (C4) | The one service wiring point | Becomes table-driven through `core/service_runtime/service_engines.py` and stays one function |
| Transport kernel (C5, and the worker shares and nesting limit of C14) | Exact Host and Origin, body and nesting limits, worker shares, the route table | Unchanged by any engine choice |
| The selection mechanism, `core/engines/selection.py` (planned; section 7.8) | It is the thing that selects | Only its ranking engines form a slot (`ranking_strategy`) |
| Configuration dimensions (E26) | A requirement inventory | Mapped in section 16 |

### 5.6 Policies and settings that shape slots but are not engines

| Component (inventory) | How it is expressed |
|---|---|
| Intelligence family policy and the four layers (E19, C10) | `service_host_family_policy/v1` switches families on and off; the main line serves the harness family alone. The four layers are the storage taxonomy. The Open Knowledge Format family cannot be represented today because an item's family is derived from its source layer (finding F8) |
| Licence policy (C10) | `service_host_license_policy/v1`, MIT only by default |
| Entitlement sources (C9c) | `stripe_snapshot`, `explicit_host_grant`, `promotion_code_grant`: three business paths to one entitlement record, kept apart for reporting money |
| Skill front-matter policies (E22) | `agent_skills_standard_strict/v1`; the older `loop_engine_skill_frontmatter_legacy/v1` conflicts with the pre-launch version policy (roadmap S-6.26) |
| Contract match modes (E7) | Declared per contract; solution ports stay strict |
| Route purpose policy (E15) | `RoutePolicy`, an eligibility input of `model_access` |
| Wrapper composition and native control ownership (E13) | Settings of a step executor installation; only the direct adapter is eligible until a composition executor exists (`composition_without_executor`) |
| Experimental embodiments (E25) | Candidate placement settings of step executor installations; development only (`no_product_import_of_experimental_code`) |
| Web surface map per hostname (C6) | A routing policy under `http.surfaces` (worktree only) |

Retained or superseded surfaces: the older worker service (C17) is not
deployed and is not a slot; `provisioning.py` imports `key_digest` from it
(finding F10), so the helper moves. The parked precursors
`core/implementation_choice.py` and `core/step_efficiency_review.py` carry the
same intent as this design and stay parked; if ever restored, their choice
becomes a slot, not a parallel selector.

### 5.7 Coverage map

| Inventory record | Where it lands |
|---|---|
| E1 Loop runtime envelope | Fixed frame |
| E2 Role profiles and handshake | Fixed frame |
| E3 Run mode policy and installed executor modes | Fixed frame; section 13.9 |
| E4 Step profile | Fixed frame |
| E5 Step handler; E6 planned executor interface; E10 external harness boundary and kits; E11 process recipes; E24 overnight runner; E25 embodiments | `step_executor` (section 13) |
| E7 Typed contract and ports | Fixed frame |
| E8 Runtime context ports | `intelligence_search_retrieval_port`, `web_research_port`, `custom_plugins_port` |
| E9 Boundary registry | Fixed frame; section 7.2 |
| E12 Harness realization policy | `ranking_strategy` and the selection mechanism (selection and fallback); `response_evaluator`; kind `harness_brokered_response` of `model_access` |
| E13 Layered wrappers and native control | Executor installation settings (section 13.8) |
| E14 Harness instance provisioning | `harness_instruction_files` |
| E15 Model gateway | `model_access` |
| E16 Typed decision engines | `typed_decision` |
| E17 Catalog store | `record_store` |
| E18 Retrieval and search policies | `retrieval_lexical_stage`, `retrieval_vector_stage`, `retrieval_rerank_stage`, `catalogue_search_policy` |
| E19 Layers, Runtime Memory, family axis | `runtime_memory`; family policy (5.6) |
| E20 Task similarity | `similarity_candidate_source` |
| E21 Workspace and sandboxes | `workspace_backend`, `process_confinement` |
| E22 Protocol transports and skills | `tool_protocol_transport`; skills policy (5.6) |
| E23 Preference engines, setters, search | `ranking_strategy`, `configuration_setter`; configuration search stays parked |
| E26 Configuration dimensions | Section 16 |
| C1, C2, C3, C5 (server), C18 | Release-time slots (5.4) |
| C4 Host configuration loader | Fixed frame; section 15.1 |
| C5 Transport | Fixed frame (kernel) |
| C6 Website and surfaces | `web_page_delivery` |
| C7a to C7e Authentication | `credential_authentication`, `browser_identity_provider` |
| C8 Account email | `account_email_delivery` |
| C9a, C9b Billing | `payment_provider`; C9c entitlement sources are policy |
| C10 Catalogue and provisioning | `catalogue_body_store`, `catalogue_qualification_resolver`; licence and family policies |
| C11 Search | Hosted search row (retrieval slots at hosted scope) |
| C12 Protocol endpoint | `protocol_endpoint` |
| C13 Record store | `record_store`, service scope |
| C14 Request limits | `request_limit_state`; shares and nesting are transport kernel |
| C15 Observability | `failure_journal` |
| C16 Secrets | `secret_resolver` |
| C17 Older worker service | Retained surface, not a slot |
| C19 Customer client connection | `customer_client_recipe`, `material_install_layout` |
| Roadmap S-6.40, library ingestion worker (no inventory record; the component is new) | `library_ingestion_source` |
| Roadmap S-6.41, harness run records for self-improvement (no inventory record) | Input to the evidence pipeline, never a ranking source by itself (section 10.1) |
| Roadmap S-6.42, a fresh independent instance per step (no inventory record) | A qualification requirement of `step_executor` engines (section 13.5) |
| Roadmap S-6.60, the layer that decides one model or several (no inventory record; the component is new) | `model_call_strategy` |

## 6. The records

### 6.1 Every record, by purpose

Every record is a frozen data class with an exact field set. `to_dict()`
carries `record_type`; `from_dict()` refuses unknown or missing keys and any
unsupported version before any effect; `content_digest` is SHA-256 over
canonical JSON through the existing `canonical` and `digest` helpers in
`core/configuration_capabilities.py`. Identifiers use the existing bounded
pattern `^[a-z][a-z0-9_.-]{0,95}$`. A version rises only when a new field or
value is present, the encoding `harness_fallback_policy/v1` to `/v3` already
uses, so existing digests hold. A record an older release must not honour gets
a new version, so the older release refuses it.

```text
Records added or versioned by this design
├── Declaration, shipped with a release
│   ├── engine_slot/v1, inside engine_slot_catalog/v1 (src/loop_engine/data/engine_slots.yaml)
│   ├── harness_recipe/v1, inside harness_recipe_catalog/v1 (src/loop_engine/data/harness_recipes.yaml)
│   └── engine_retirement/v1, inside a slot (release-wide) or a host policy (one host)
├── Projection, computed and never written by hand
│   ├── engine_descriptor/v1
│   └── executor_profile/v1, the step executor slot's capability record inside its descriptors
├── Host configuration, declared once per slot or projected from a declaration that exists
│   ├── engine_installation/v1
│   ├── engine_slot_configuration/v1: installed engines plus one policy per scope key
│   ├── engine_selection_policy/v1
│   ├── engine_evidence_rule/v1
│   ├── engine_comparison_policy/v1
│   ├── service_host_engines/v1: the optional "engines" block of the service host file
│   └── engine_selection_override/v1: a narrowing source carried by a Loop or sent by a
│       harness, with its existing ParameterSourceKind and its sender
├── Decision and measurement
│   ├── engine_selection_decision/v1: in Run History, the host start report or the release record
│   ├── operation_cost_record/v2: versions operation_cost_record/v1
│   ├── engine_bindings_report/v1: what a host bound at start, and why
│   └── pilot_release_record/v2: adds the engines map
├── Evidence and qualification, kept through the CatalogStore contract
│   ├── engine_trial_evidence/v1: generalizes harness_trial_evidence/v1
│   ├── engine_evidence_review/v1: generalizes HarnessEvidenceReview
│   ├── engine_evidence_snapshot/v1
│   └── engine_qualification/v1: generalizes harness_project_qualification/v1
└── Edges created or versioned by adoption
    ├── step_run_request/v1 and step_run_result/v1 (S-6.31)
    ├── harness_intelligence_search_policy/v2 and service_retrieval_result/v2 (S-6.32)
    └── later: web_research_request/v1 and result, workspace_file_request/v1 and siblings,
        tool_call_request/v1, runtime_memory_note/v1, harness_bundle_rendering/v1
```

### 6.2 `engine_descriptor/v1`

Computed by the slot's projection function from the engine's native
declaration. It carries the native record's type and digest, so a changed
declaration changes the descriptor digest and fails revalidation.

| Field | Rule |
|---|---|
| `slot_id`, `engine_id`, `engine_version`, `engine_ref` | `engine_ref` = `engine_id@engine_version`; an identifier appears once per slot |
| `engine_kind` | One of the slot's `engine_kinds` |
| `implementation_ref` | Dotted symbol of the adapter, resolvable without import |
| `implementation_digest` | Digest of the code and pinned software: spec digest, package version, file digests |
| `native_record_type`, `native_record_digest` | For example `harness_execution_capabilities/v2`; a type without a record version today is named by its dotted symbol |
| `capability_record`, `capability_record_digest` | The slot's own typed record: `executor_profile/v1`, `StoreCapabilities`, `ModelProviderCapabilities` with the route, a `CapabilityHandshake`, or a service adapter's `protocol_version` and `provider_profile` |
| `supported_edge_contracts` | The request and result versions the engine speaks |
| `supported_modes` | Subset of deterministic, hybrid, non_deterministic |
| `effects`, `isolation`, `locality`, `data_recipients` | Effects from `core.facets.EFFECTS`; isolation from `core.harness_execution_contracts.ISOLATIONS`; locality in the slot's native vocabulary, named beside the value, because the repository has two (`core.facets.LOCALITY`: local_machine, api_calling, external_resources; `core.model_routes.LOCALITIES`: cloud, organization, local for model routes), and values from different vocabularies are never compared; recipients are the outside origins data can reach |
| `enforced_limits` | Preemptive limits only, from `core.harness_execution_contracts.LIMITS`; post-run bounds do not count |
| `cost_class`, `cost_basis` | `core.facets.COST_CLASSES`; basis is `provider_reported`, a price record reference with digest and date read, or `unknown`. `cost_class` (free, cheap, metered, expensive) is a descriptive label only: no eligibility screen and no ranking method reads it, because it is a declared adjective, not a measurement |
| `licence`, `source` | SPDX identifier or `unknown`; upstream and revision where known |
| `availability`, `qualification` | `ConfigurationFact` values with source, digest and expiry; `qualified` only when the source binds the same installation digest. Where a qualification record already exists, it stays the one source: the five `embodiments/*/qualification.json` files (`harness_project_qualification/v1`) are projected, never copied into a second `engine_qualification/v1` for the same installation |
| `lifecycle`, `implementation_location` | Component lifecycle vocabulary; `main` or `checkpoint@a3bd0f1` |
| `checks` | The named checks that guard the engine |

### 6.3 Host configuration records

`engine_installation/v1`: `installation_id` (equals `engine_id` unless one
engine is installed twice), `engine_id`, `engine_kind`, `enabled` (an explicit
Boolean), `settings` (typed by the factory table's settings record),
`settings_digest`, optional `declaration` (absolute path and SHA-256 of a host
declaration file such as `embodiments/codex/harness.json`), optional
`qualification` (path and SHA-256 of an `engine_qualification/v1`, or of the
existing `harness_project_qualification/v1` it projects), and
`installation_digest`.

Settings never carry authority. A field that would allow network access,
file writes, commands, model calls, spending or secret use stays where the
host already declares authority (for example `allow_network` and
`writes_authorized` in the existing host blocks, and the owning Loop's grant),
and the eligibility screen reads it there as a grant. A settings record that
declares such a field is refused, which is the rule the setter check
`authority_bearing_is_refused` already enforces for configuration targets.

`engine_slot_configuration/v1`: `slot_id`, `slot_version`, `installed` (a list
of installations), `selection` (a map from scope key to
`engine_selection_policy/v1`), `source` (`declared` or
`projected:<existing declaration>`), `source_digest`.

`engine_selection_policy/v1`:

| Field | Rule |
|---|---|
| `slot_id`, `slot_version`, `scope_key` | A different slot major version is refused |
| `initial` | Ordered installation identifiers for the first attempt; evidence may reorder only these |
| `fallbacks` | Ordered installation identifiers used only after a typed failure; initial and fallback priorities may differ, as the configuration dimensions requirement asks |
| `no_fallback` | Exactly one of "fallbacks is not empty" and "no_fallback is true" must hold, so missing configuration never masquerades as a deliberate empty set |
| `fallback_on` | A subset of the slot's fallback-eligible failure kinds; empty when `no_fallback` |
| `ranking` | `MetaPreferencePolicy` fields; `engine_order` must end with `declared-order`, so ranking never abstains silently |
| `evidence` | Null, or an `engine_evidence_rule/v1` plus the reference and digest of an approved `engine_evidence_snapshot/v1` |
| `overrides_permitted` | Override kinds each source may use (a Loop, a harness; section 8.4): pin, exclude, prefer, declared_order_only, objective |
| `comparison` | Null, or an `engine_comparison_policy/v1`; off unless declared. Its allowance is a reference to a separately approved authority grant, never an amount the policy itself declares (section 10.2) |
| `retired` | `engine_retirement/v1` entries for this host |
| `allow_unqualified` | False; true only inside a declared trial, never on a served path |

Validation refuses, before any effect: an engine listed twice across
`initial` and `fallbacks`; a retired or uninstalled engine; a policy wider
than the slot's fallback ceiling (a ceiling of `none` forces `no_fallback`);
an evidence objective the slot does not declare; a minimum sample below the
slot's floor. A policy grants nothing: it cannot enable an engine the registry
does not hold, name an engine of an undeclared kind, or widen any permission.

`service_host_engines/v1` is the optional top-level `engines` block of the
service host file: a map from slot to `engine_slot_configuration/v1`. The host
loader refuses unknown top-level keys, so an older release refuses a host file
that carries the block and does not start. That is the intended rollback
behaviour, the same as `request_limits` today.

### 6.4 `engine_selection_decision/v1`

Written before any dispatch.

| Field | Content |
|---|---|
| `slot_id`, `slot_digest`, `scope_key`, `phase` | Phase is `initial`, `fallback` or `reuse` |
| `scope` | Operation contract, owning profile, owning Loop, fixed settings of joined slots, evaluation contract, and `scope_digest` |
| `policy_digest`, `policy_source`, `configuration_digest` | The policy used, where it came from (with the parameter resolution trace) and the host configuration revision |
| `universe` | Every installed and enabled engine with its descriptor and installation digests |
| `eligibility` | For every installation: eligible, or every refusal code with its detail |
| `declared_order`, `override`, `order_without_override` | The order after eligibility, the override applied with its source kind and sender identity (section 8.4), and what the order would have been without it |
| `ranking` | The embedded `configuration_preference_decision/v1` (or `/v2`) with every ranking attempt |
| `evidence` | Used or not; reason (`ranked_matched_reviewed_evidence`, `insufficient_matched_reviewed_evidence`, `evaluation_scope_mismatch`, `not_requested`); whether evidence changed the declared order; the uncertainty the rule computed (the bounds and tail probabilities of the paired rule), or `not_computed`; snapshot digest; history references; the heuristic adoption reference, if any |
| `selected`, `propensity` | Installation, engine reference and descriptor digest; the probability of this choice (1 under the declared order) |
| `fallbacks`, `no_fallback` | The ordered transition chain, or the explicit no-fallback decision |
| `transition` | For phase `fallback`: previous engine, failure kind, attempt Loop, whether accounting was uncertain, the expected effect of the change and the settings that stay fixed |
| `consumed` | Model calls, tokens, elapsed time and cost state already spent, carried into the next attempt |
| `status` | `selected`, `no_eligible_engine`, `refused_policy`, `terminal_failure` |
| `selection_loop_id`, `as_of`, `binding_site` | The deterministic Loop that decided, when, and where the engine is bound |
| `parent_decision_digest` | For a nested slot, the digest of the decision that bound the engine whose envelope asked; empty for a slot at the top of its tree (section 4.6) |
| Constant flags | `execution_authority_granted: false`, `task_accepted: false`, `model_call_performed_by_boundary: false` (the flag name `configuration_preference_decision/v1` already uses, so one idea keeps one name) |

These fields cover the eight items of the "Required choice and fallback
record" in `docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md`:
the initial value and its source; required, absent, unsupported and unknown
states; ordered fallbacks with an explicit no-fallback decision; eligibility
and compatibility; the observation that permits each transition; the
authority consumed; the objective, evidence and reason; and the attempt and
outcome in Run History.

### 6.5 Evidence records

| Record | Content |
|---|---|
| `engine_evidence_rule/v1` | `method` (`matched_quality_then_efficiency` or `paired_efficiency_within_loss_margin`), `objective` (`tokens`, `elapsed_seconds` or `priced_cost`), `minimum_matched_records`, `evaluator_ref` and `evaluator_digest`, `window` (maximum age and maximum records). The paired method adds `confidence`, `loss_margin`, `minimum_relative_gain`, `completeness_floor`, `maximum_looks`. No field has a default in code |
| `engine_trial_evidence/v1` | Every field of `harness_trial_evidence/v1` with `harness_id` replaced by `slot_id` plus `engine_ref`, plus `installation_digest`, `selection_path` (`comparison_arm` or `frozen_population`), `pair_id`, and the paired counts: discordant acceptance counts, objective wins and losses, known-value counts, engine refusals and excluded attempts by reason. Until the harness records converge on this one (plan package X10), a harness engine's trials exist only as `harness_trial_evidence/v1`; the evidence reader projects them and never writes a second copy |
| `engine_evidence_review/v1` | Binds the exact trial digest; names the reviewer and the review evidence; refuses a reviewer who is the engine, the producing Loop or the compiling Loop |
| `engine_evidence_snapshot/v1` | For one slot and scope class: the digests of approved trials and reviews at one moment. Selection reads a snapshot, never a live query, so every decision is reproducible from its snapshot digest. Each publication is one "look" |
| `engine_qualification/v1` | Slot, engine reference, descriptor and installation digests, scope (edge version, recipe variant, the step contracts covered), proof level, for a step executor engine the highest rung of the qualification ladder roadmap S-6.31 names (connected, material listed, material loaded, step finished, independently accepted), evidence references with digests, reviewer, decision, issue time and expiry. A documented bridge, a session identifier or a process exit never counts as the rung "material loaded". An installation that already has a `harness_project_qualification/v1` keeps it as its one qualification source, projected into this shape; writing a second qualification for the same installation is refused |

Proof levels, the ones the roadmap's verification cases already use:

| Proof level | What it proves | Model-call authority needed |
|---|---|---|
| `local_contract` | The engine honours the edge contract and the refusals offline | No |
| `real_provider` | The engine works against a real provider with real accounting | Yes |
| `held_out_comparison` | A matched comparison on a frozen population with an independent evaluator | Usually |
| `end_to_end` | A complete checked task through the engine | Yes |
| `operational_drill` | A cutover, rollback, restore or incident drill on the real deployment | Depends |

Today's Codex status `qualified_offline_native_cli_text_profile`, with zero
real model calls, maps to proof level `local_contract` for recipe variant
`text_response`.

### 6.6 Measurement and reporting records

`operation_cost_record/v2`, written only by the envelope, one per physical
attempt:

| Field | Meaning |
|---|---|
| `operation_id` | The edge interaction identifier |
| `slot_id`, `engine_ref`, `engine_kind`, descriptor and installation digests | Exactly what ran; never the gateway's own name |
| `scope_digest`, `subject_digest` | The scope fingerprint and the digest of the exact edge request, which pairs two attempts on one subject |
| attempt, run, owning Loop and envelope Loop identities | Identity |
| `selection_decision_digest`, `selection_path`, `propensity`, `comparison_pair_id` | `first_choice`, `fallback_after:<kind>`, `override_pin`, `comparison_arm` or `frozen_population` |
| `disposition` | `completed_unverified`, `failed`, `engine_refused`, `refused_before_dispatch`, `cancelled`, `deadline_exceeded`, `budget_stopped`, `effects_uncertain`. There is no `verified` value: acceptance arrives only as an independent verdict joined later. `effects_uncertain` is spelled the same in the step result status, the failure kind and this disposition |
| `phase_ms` | `admission`, `setup`, `execution`, `verification`, `recovery` from the envelope's monotonic clock; unknown stays null |
| `engine_reported_seconds` | What the engine said about itself; kept, never ranked |
| model calls, input and output tokens, `usage_source` | Calls counted by the gateway; tokens as the provider reported them; null when unknown |
| `monetary_cost`, `cost_source` | Provider-reported, or provider-reported usage times a price record with digest; else null |
| `refusal_code`, `effects` | Stable refusal code; `none`, the committed effect digests, or `uncertain` |

The version change exists because one field changes meaning: version 1 lets
the producing caller write `verified`, which is self-acceptance.

`engine_bindings_report/v1` is what a host bound when it started: the
configuration digest, one decision digest per host-start slot, the slots left
unbound with their reasons, and the intelligence family policy in force with
its reason. It also delivers what the harness-first decision record promised
and `configure_host` does not produce today: "a recorded reason in the host
loader's output" when a host file declares no family policy.
`pilot_release_record/v2` adds an `engines` map naming the engine and
descriptor digest of every release-time and host-start slot, so a rollback
knows exactly which engines it restores.

## 7. Registration: which existing registries are extended

### 7.1 Engines stay where they already live

No engine moves. Each slot names the registry that already holds its kind of
implementation, and that registry gains one effect-free projection method.

| Engine slot | Existing registry (native) | Native declaration | New projection | Factory table (planned unless marked) |
|---|---|---|---|---|
| `step_executor` | `core.external_harness.HarnessRegistry` | `HarnessAdapterInfo`, `HarnessExecutionCapabilities`, the recipe record, the host declaration | `HarnessRegistry.descriptors("step_executor")` producing `executor_profile/v1` | `core/step_execution/engines.py` (section 7.8) |
| `model_access` | `ModelGateway.providers` with `RouteRegistry` | `ProviderSpec.describe()`, `ModelRoute`, `ModelProviderCapabilities` | `ModelGateway.descriptors(purpose)`, one per route | `core/model_provider_engines.py`, absorbing `builtin_provider_specs` and `provider_spec_from_endpoint` |
| `typed_decision` | The gateway provider registry, compiled by `configured_engines` | The compiled decision `ProviderSpec` | From `ConfiguredDecisionEngine` | `ADAPTER_FACTORIES` in `core/decisions/configuration.py` (**exists**: this is the pattern every other factory table copies) |
| retrieval stages | `Retriever` built-ins and host `RetrievalBackendBinding` values | `backend_handshakes()`, `CapabilityHandshake`, `EmbeddingSpace` | `retrieval_descriptors(bindings, stage)` | `core/retrieval_engines.py` |
| `catalogue_search_policy` | The policy table in `core/harness_intelligence_search.py` | The policy record | From the record | The same module |
| `record_store` | `catalog.registry.AdapterRegistry` | `StoreCapabilities` | `AdapterRegistry.descriptors()` | `catalog/record_store_engines.py` |
| `workspace_backend` | `WorkspaceOperationService` backends | `WorkspaceSpec`, `BackendAvailability` | `describe_workspace_backend()` | `core/workspace_engines.py` |
| `process_confinement` | The runner in `core/harness_process.py` | `confined_environment/v1` | `describe_confinement()` | `core/process_confinement_engines.py` |
| `tool_protocol_transport` | `McpRegistry` | `McpServerSpec` and the transport | `McpRegistry.descriptors()` | `core/tool_transport_engines.py` |
| `harness_instruction_files` | `STYLE_FILES` | The style row | `style_descriptors()` | The table itself |
| `library_ingestion_source` | None today: a new component, whose factory table is its registry, as `ADAPTER_FACTORIES` is for typed decisions | The reader's source declaration (source kind, address, licence policy) | `describe_source()` | `core/library_ingestion/engines.py` (planned, the component's own folder) |
| `model_call_strategy` | None today: a new component, whose factory table is its registry | The strategy's declaration (how many calls it plans, its combination method) | `describe_strategy()` | `core/model_call_strategy/engines.py` (planned, the component's own folder) |
| `ranking_strategy` | `PreferenceEngineBinding` tuples on a request | The binding's own fields | `PreferenceEngineBinding.descriptor_record()` | `core/configuration_preferences.py` (**exists**) |
| service slots | The attributes `ServiceHttpApplication` and `ServiceHttpAuthenticator` already read | `protocol_version`, `provider_profile`, the configuration record | A `describe()` function per slot module | `core/service_runtime/service_engine_<slot>.py`, dispatched by `core/service_runtime/service_engines.py` |

Each registry keeps revalidating at use as it does today:
`HarnessRegistry.get` compares `info()`; `HarnessProcessSpec.validate_unchanged`
re-digests installed software; `negotiate` runs before use and
`require_atomic_batch` before a service write; route screening runs for each
call; `CapabilityInvocationPolicy` pins the handshake digest; the service
refuses an adapter whose `protocol_version` differs. Slots without any
revalidation today (similarity, workspace, sandbox, tool transport, plugins,
run-scoped notes, setters) get their first one from the shared descriptor
recheck of section 8.8.

### 7.2 The engine slot catalogue, joined to the boundary registry

The slot index is one data file, `src/loop_engine/data/engine_slots.yaml`
(record `engine_slot_catalog/v1`), loaded through the existing
`core.component_contracts.load_component_resource`, whose closed list of
resource names gains the file. A coding harness reads one file to see every
slot. Each slot joins by exact name to rows of
`core.boundary_registry.BOUNDARIES`, the same join `BOUNDARY_ONTOLOGY` already
uses, and `boundary_report()` gains a section that lists the slot index, so
the boundary registry remains the one place that proves every swap point is
wrapped by a Loop and tested. The existing 87 rows do not change. New rows are
added only for new envelopes: "component engine selection" (the selection
Loop), "delegated step execution" (the step envelope), "engine evidence
compilation" (the evidence compiler) and, later, "engine comparison arm" (a
side-by-side comparison). The existing row "assignment harness selection"
stays, because `select_harness_as_loop` remains the step executor's instance
of selection until it converges on the general rule. Release-time slots name
no work boundary and carry an explicit reason instead, because deployment
choices are not run-time boundaries.

A planned slot whose envelope does not exist yet names the row its first
package will add and is reported as `planned_without_envelope`. The join
check requires existing rows only for active and candidate slots, so the
catalogue never names a row that does not exist and never hides a missing
one. The slot record does not restate its edge: the request and result
contracts are read from the joined interaction rows (section 7.3), which stay
the one source. Roadmap D-19's first action, "Index every engine slot in the
boundary registry", is met by this join: `boundary_report()` reads and
validates the slot index, and none of the 87 existing rows is restated.

### 7.3 The interaction catalogue holds the edges

`src/loop_engine/data/component_interactions.yaml`
(`component_interaction_catalog/v1`) declares seven interactions today, all
for the parked in-process solve chain. Every slot gains its edge rows, using
the existing fields (delivery, scheduling, retry, timeout, cancellation,
compatibility, context handoff, authority transfer, privacy, failure, repair,
verification, Run History) with `implementation_state: candidate` until the
row's checks are collected. One complete row, for the step edge:

```yaml
  - interaction_id: core.interaction.step.execute
    producer_kind: runtime_definition
    consumer_kind: adapter
    operation: run_delegated_step
    request_contract: step_run_request/v1
    result_contract: step_run_result/v1
    relationship: spawned_by
    delivery: at_most_one_physical_engine_invocation_per_attempt
    scheduling: serial
    retry: engine_selection_policy_fallback_only
    timeout: step_budget
    cancellation: inherited_run_cancellation
    compatibility: exact_engine_descriptor_and_edge_version
    context_handoff: selected_refs_and_instruction_files
    authority_transfer: explicit_narrowing_only
    privacy: no_parent_private_scratch
    failure: typed_engine_failure_kind
    repair: declared_fallback_or_new_spawned_loop
    verification: independent_response_evaluation
    run_history: engine_selection_decision_and_attempt_loop
    implementation_state: candidate
```

Every field on this row stays the same when the engine behind it changes.
That is what "the edges stay the same" means in code. The existing check
`component_interactions_are_unique_and_typed` grows to require exact
versioned contracts and known component kinds.

### 7.4 One bounded factory table per slot

`core/decisions/configuration.py` already does exactly what the owner asks
for one slot: `ADAPTER_FACTORIES` maps an engine kind to its settings record
and constructor, the module calls itself "a bounded factory for shipped
adapters, not dynamic plugin loading or a parallel provider registry", host
entries are exactly `{"name", "engine", "settings"}`, and an unknown engine or
wrong settings refuse (`unsupported_decision_engine`,
`decision_engine_settings_refused`). Every slot gets one table on that
pattern: engine kind to settings record, constructor and module path. The
module path lets `loop-engine engines explain` name the file to edit.
Constructors receive typed settings only; they never read environment
variables, discover packages or grant effects. A factory table is the only
code allowed to name a concrete engine class, and the static check of section
17 keeps it that way.

### 7.5 Engines from other packages: discovery without registration

A third party, or a customer, can ship an engine in its own Python
distribution. The standard library's `importlib.metadata.entry_points(group=
"loop_engine.engines")` lists advertised engines from installed package
metadata without importing anything, so discovery stays effect-free. A listed
engine is only a candidate (lifecycle `candidate`, qualification `unknown`).
Loading happens only when a host file names the exact entry point,
distribution name and version; the loaded object is a factory, and the
owning registry registers what it returns through its normal path with every
protocol and declaration check. Installing a package therefore offers an
engine but never registers or selects it, which keeps "importing registers
nothing" true.

Loading an entry point imports and runs that distribution's code inside this
process. A host therefore names only a distribution it trusts as it trusts any
installed dependency, pinned by exact version and recorded in the installation
digest. Code from an untrusted source is never loaded this way: it runs as a
separate confined process behind the step executor slot, the declared sandbox
`AGENTS.md` requires for untrusted code.

### 7.6 One conformance kit per slot

Every slot has one kit of golden fixtures that every engine must pass,
modelled on the existing `run_store_conformance`: the same requests, the same
known-wrong cases, the same expected result keys and refusal codes. Today the
store's golden suite runs only on the in-memory reference store; under this
design it runs on every store engine. The kit is also what rule 13 of section
1.4 rests on: two engines behind one slot return the same record types and
keys, and an engine that adds a field or a status fails the kit.

### 7.7 Why there is no new engine registry

`AGENTS.md`: "Extend existing registries and event vocabularies. Do not
create parallel stores, event systems, runtime classes, or sources of truth."
`docs/architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md`: "Do not introduce a
second universal registry or infer behavior from a version string." A
universal registry would hold a harness process, a database connection and a
model route side by side, objects with different lifecycles that already have
tested registries. The descriptor view gives one listing without moving any
object out of the registry that owns it.

### 7.8 Folder layout: one folder per functional component, one module per engine

Roadmap S-6.30 verifies "a folder structure with one folder per functional
component and one module per engine", and `AGENTS.md` says "The folder
structure should follow the components and their engines." The repository
already has the pattern, the registry and the migration method:

- `core/decisions/` is the model. One folder holds the typed decision
  component: its contracts, its factory table (`configuration.py`) and one
  module per engine (`jev.py`, `system_one.py`). `catalog/stores/` holds one
  module per record store engine.
- `src/loop_engine/data/component_folder_map.yaml` (`component_folder_map/v1`)
  is the existing registry of folders. Each row names the semantic owner, the
  allowed and forbidden component kinds, the public boundary and the
  dependency direction. A new component folder is one new row there, never a
  second folder registry.
- `docs/architecture/FOLDER-DEPTH-AND-THE-FLAT-CORE-2026-09-18.md` is the
  accepted method for moving an existing flat family into its folder: one
  family per commit, the public import path unchanged, no behaviour change in
  a move, and the architecture map, the folded self-test list and every
  string that names a module moving in the same commit.

Decisions, with their reasons:

| Code | Folder | Reason |
|---|---|---|
| The shared framework: records, slot catalogue loader, selection, evidence, measurement, discovery, conformance detectors, settings projection, comparison | `core/engines/` (new); module names drop the `engine_` prefix, for example `core/engines/selection.py` | A new component starts in its own folder instead of adding about fifteen more flat names to `core/` |
| The step execution component: edge records, the step attempt envelope, the executor factory table, the session process and one module per step executor engine | `core/step_execution/` (new), for example `records.py`, `envelope.py`, `engines.py`, `session_process.py`, `text_relay.py`, `agent_client_protocol.py` | The component the harness-first plan needs most follows the owner's layout from its first commit |
| The library ingestion component (roadmap S-6.40) | `core/library_ingestion/` (new), one module per source reader | A new component |
| The model call strategy component (roadmap S-6.60) | `core/model_call_strategy/` (new), one module per strategy | A new component |
| Engines of components whose code is still flat: harness recipes, retrieval, model providers, process confinement, workspaces, tool transports | Stay flat, with their family prefix, until that family's folder move lands | A package such as `core/retrieval/` beside the module `core/retrieval.py` would shadow it, so a family moves whole, in its own commit, with no behaviour change |
| Record store engines | `catalog/stores/` (exists); the factory table in `catalog/record_store_engines.py` | The folder already follows the rule |
| Service slot factory modules | `core/service_runtime/`, the service component's folder | Its engines are already one module each (`browser_identity.py`, `account_email.py`, the `stripe_*` modules) |

Rules. A factory table module names engine classes and defines none. An engine
module holds exactly one engine. A folder grants nothing: no folder path
implies access, authority or routing (Constitution LE-INTEL-002, LE-DOC-001).
Each new folder carries a README, a row in `component_folder_map.yaml` and a
key in `MODULE_MAP` (`architecture_map.py`). None of the new folders is
top-level; a new top-level folder under `src/loop_engine/` would still need
the five steps `AGENTS.md` lists. The check
`every_engine_module_holds_one_engine_in_its_component_folder` refuses a
factory table module that defines an engine class, and an engine module
outside the folder its slot names. Existing modules that hold several engines
(`core/retrieval.py` with three backends; recipe modules such as
`core/harness_responses_recipes.py` with two styles) start in a baseline that
may only shrink, and are split when their family moves.

## 8. Selection at run time

### 8.1 When selection runs

```text
Selection phases
├── per_attempt: step_executor, model_call_strategy, model_access, typed_decision,
│   harness_instruction_files, response_evaluator, tool_protocol_transport,
│   similarity_candidate_source, ranking_strategy
├── loop_start: workspace_backend, process_confinement, runtime_memory, the three public
│   ports, library_ingestion_source, and the engine-side retrieval stages (when their
│   owner is constructed)
├── host_start: every service slot, and the retrieval stages and search policy of the
│   hosted service
└── release: domain_name_records, edge_proxy, compute_host, web_server_process,
    release_executor, web_page_delivery, customer_client_recipe, material_install_layout
```

A slot is `per_attempt` only when its engines are interchangeable without
moving state, without changing who holds authority and without a
customer-visible external effect. Authoritative record storage, identity,
account email, billing, secrets and protocol versions are therefore chosen
once, at host start.

### 8.2 The procedure, step by step

`core/engines/selection.py` (planned) provides `select_engine(request)`,
`select_engine_as_loop(request, parent=None)` and
`assess_engine_attempt(policy, attempt)`. The request is one frozen object
(the slot, the policy, the candidate bindings, the ranking engine bindings,
the scope, the owning Loop's grants and remaining budget, any override, the
evidence snapshot and the time), which keeps the public functions under the
repository's cap of nine parameters.

Base case. The selection Loop needs no selection to start (Constitution
LE-CONFIG-001 and LE-CONFIG-002): its ranking engines and their order come
from the declared `MetaPreferencePolicy` inside the slot configuration, which
is resolved without another selection Loop, and the `ranking_strategy` slot is
never ranked by evidence. The check
`engine_selection_needs_no_selection_to_start` refuses a policy whose ranking
engine would itself be chosen by a nested selection.

0. **Inputs.** Everything is typed and digested: the edge request and its
   scope fingerprint, the slot record, the host's slot configuration for this
   scope key, the descriptors, the owning Loop's grants, budget and override,
   and the approved evidence snapshot when the policy names one.
1. **Universe.** Only installations the host declared and switched on. An
   engine the host did not install is never a candidate, whatever else offers
   it (a narrower source, an entry point, the registry's own order).
2. **Discovery.** The slot's projection reads the native registry. Nothing is
   started, nothing is probed over the network, no model is asked.
   Availability comes from recorded observations with an expiry.
3. **Eligibility.** The screens of section 8.3 run in a fixed order. They
   remove and never reorder, and every refusal is recorded, not only the
   first.
4. **Declared order.** `initial` filtered to eligible engines, then narrowed
   or reordered by permitted overrides from higher-precedence sources
   (section 8.4). A pin to an ineligible engine refuses; nothing is silently
   substituted.
5. **Ranking.** `MetaPreferencePolicy` tries the ranking engines in the
   policy's order. The evidence ranker may move a challenger ahead of the
   incumbent only under the evidence rule (section 8.5). When evidence is
   insufficient it signals `insufficient_evidence`, a new typed fallback
   class, and the always-present `declared-order` engine orders the list with
   the reason recorded.
6. **Record.** `engine_selection_decision/v1` is written before any dispatch:
   into the owning Loop's ledger for per-attempt and Loop-start slots, into
   the host start report for host slots, into the release record for release
   slots.
7. **Bind.** The selected engine is bound where the slot says:
   `InternalRuntimeBinding(binding_id=slot_id, ...)` in
   `LoopRuntimeContext.internal`, a public port's adapter field, a
   `ServiceHttpApplication` attribute set by the loader, the gateway's route
   plan, or the release record. `LoopRuntimeContext.derive` already only
   narrows, so a Spawned Loop can receive fewer bindings but never a new one.
   Binding grants nothing.
8. **Revalidate at use.** Immediately before invocation, the envelope
   recomputes the descriptor and installation digests and runs the slot's own
   recheck. A change is the terminal failure `engine_changed_after_selection`,
   never a fallback trigger.
9. **Invoke and measure.** The envelope invokes the engine through the engine
   protocol, measures the attempt with its own clock and the gateway's call
   count, writes `operation_cost_record/v2`, and validates the answer against
   the edge result record, refusing extra or missing fields.
10. **Fallback.** Only on a declared failure kind, within the slot's ceiling,
    to the next eligible engine in `fallbacks`, carrying consumed authority
    forward (section 8.9). The transition is a new decision with phase
    `fallback`.
11. **Reuse.** A decision is reused within a run when the slot, policy,
    scope, snapshot, override and every candidate descriptor digest are
    unchanged and no fact has expired. Reuse is recorded with phase `reuse`.

This is the decision sequence of the configuration dimensions requirement
("effect-free discovery -> eligibility and compatibility checks ->
comparison using applicable reviewed evidence -> initial configuration
selection -> ..."), applied to one slot at a time.

### 8.3 Eligibility screens and their reason codes

| Order | Screen | Refusal code |
|---:|---|---|
| 1 | Retired by the release or the host | `engine_retired` |
| 2 | Lifecycle not permitted in this position: candidate outside a declared trial, deprecated as an initial choice, archived or rejected | `engine_not_active`, `engine_deprecated_as_initial`, `engine_rejected` |
| 3 | Kind not declared by the slot, or not allowed for this request (the delegation rule of section 13.5) | `engine_kind_not_allowed` |
| 4 | No common edge version | `edge_version_unsupported` |
| 5 | Availability not `available` at decision time; an open circuit breaker is simply an expiring availability fact | `engine_unavailable` |
| 6 | Qualification not `qualified` for this scope, expired, or bound to another installation digest, while `allow_unqualified` is false | `engine_unqualified`, `qualification_expired`, `qualification_scope_mismatch` |
| 7 | The slot's native screen refuses: `unmet_harness_requirements`; `negotiate` with `require_atomic_batch`; `screen_route` with localities, models, output allocation and excluded routes; the retrieval handshake with `require_same_space`; a service adapter's `protocol_version` | `capability_requirement_unsatisfied:<detail>` |
| 8 | Declared effects, isolation or data recipients outside the owning Loop's grants | `permission_not_granted:<detail>` |
| 9 | A required preemptive limit not enforced; an unknown cost under a bounded spending budget (unless the engine itself enforces a declared spend limit); a locality not allowed | `budget_requirement_unsatisfied:<detail>` |
| 10 | Incompatible with an engine already chosen for a joined slot (the executor and its model route, the instruction style) | `incompatible_with_selected:<slot>` |

Permissions never come from a run mode, a configuration convenience or an
engine's own declaration. A declaration can only make an engine ineligible,
when it asks for more than the Loop holds.

### 8.4 Who may change the declared order

The declared order is a parameter resolved by the existing
`core.parameter_resolution.resolve_parameter`, with the existing
`SOURCE_PRECEDENCE` and its trace kept in the decision.

| Source | Existing `ParameterSourceKind` (precedence) | May | May not |
|---|---|---|---|
| Explicit invocation, for example `--engine step_executor=opencode` | `explicit_invocation` (1) | Choose among eligible installations | Install, enable or widen |
| Run override | `run_override` (2) | Reorder or remove installations for one run | Widen |
| Loop profile and Loop definition | `loop_profile` (3) | Constrain eligibility; express preferences and exclusions | Name a host's engine identifier as a requirement; widen |
| Loop override (`engine_selection_override/v1`) | `run_override` when the run's caller supplied it, `loop_profile` when the Loop definition declares it | pin, exclude, prefer, declared_order_only, or choose an objective the host permits for that source | Add an engine, make an ineligible engine eligible, change the evaluator, raise a budget, add a recipient, or start a comparison |
| Deployment configuration (the settings file or host file) | `deployment_configuration` (6) | Install, enable and disable engines; declare the initial choice, fallbacks, ranking, evidence rule, comparison and permitted overrides | Grant permissions |
| Harness preference: a preference a harness sends as the typed field `engine_preferences` of its step result, or of a service request whose record declares that field | `intelligence_proposal` (9, the lowest) | prefer or exclude eligible installations for later attempts of the same owning Loop, and pin only where the host permits pins for harness sources | Everything a Loop override may not do; change the engine of the attempt that sent it; count as evidence |
| Intelligence proposal | `intelligence_proposal` (9) | Propose an ordering, admitted only through the existing `SuppliedAgentPreference` with evidence references, produced by a separately authorized reasoning Loop | Select an ineligible engine or grant anything |

Every source maps to an existing `ParameterSourceKind`; no source kind is
added and `SOURCE_PRECEDENCE` is unchanged. A harness preference is output
from inside an engine, so it is untrusted data (Constitution LE-TRUST-001 and
LE-DOC-001): the owning Loop admits it only as a typed
`engine_selection_override/v1` whose kind the host permits for harness
sources, it can only narrow or reorder eligible installations, and prose in a
harness's output never becomes a preference. This is how "a harness or a Loop
may send engine preferences within its authority" (`AGENTS.md`) is met.

A Spawned Loop inherits at most its parent's permitted override kinds. Every
override is recorded with its sender (a Loop identity, or the engine reference
and attempt of the harness that sent it), its source kind, its digest, the
resulting order and the order without it.

### 8.5 Ranking and the evidence rule

The declared order decides unless the host enables evidence ranking for the
slot and the evidence passes a declared rule. The rule is a versioned record
with no defaults in code. Two methods exist; both are deterministic, exact and
computed from counts, with no learned weights.

Rules common to both methods:

1. Only approved evidence counts, reviewed by someone who is not the engine,
   the producing Loop or the compiling Loop.
2. The scope fingerprint must equal the current scope exactly. The host
   declares which fields form it (for the step executor: operation contract,
   output contract, owning profile, resource profile, execution settings,
   owning definition, and the fixed settings of joined slots such as the
   model route).
3. Evidence binds the exact engine version and installation digest; a new
   version starts with none.
4. Engines are compared only on a shared population digest with the same
   evaluator identity; unmatched populations are never pooled.
5. Only attempts from a comparison arm or a frozen population count. First
   choice attempts alone compare nothing, fallback attempts saw only the hard
   cases, and pinned attempts were chosen by a Loop, not sampled.
6. Distinct Run History references count toward the minimum sample.
7. An unknown metric never wins and is never read as zero.
8. The incumbent is always the host's declared first eligible engine, never
   the last evidence winner, which stops a chain of drifting winners.
9. Evidence reorders one decision. It never edits the host's policy; making a
   challenger the declared first choice is a separate, reviewed host decision
   and a new policy version (roadmap D-12-T05: "Production interactions
   cannot directly rewrite global policy").

Method 1, `matched_quality_then_efficiency` (**exists** for harnesses as
`select_harness`; generalized without changing its behaviour): when every
eligible engine has at least the minimum of matched records, order by exact
verified success fraction, then a known efficiency metric before an unknown
one, then the lower metric, then declared position. Efficiency only breaks
ties on verified outcome, so a cheaper engine with a lower verified outcome
can never move first. Existing checks already hold this for harnesses:
`unmatched_populations_are_not_pooled`, `rejected_review_cannot_rank_a_harness`,
`changed_adapter_version_invalidates_the_comparison`.

Method 2, `paired_efficiency_within_loss_margin` (planned): the method that
lets the runtime choose "the most efficient engine" without ever choosing a
worse one. Over the N paired subjects in the window, for the incumbent I and a
challenger C:

```text
k   = number of challengers with N >= minimum_matched_records
g*  = 1 - (1 - confidence) / (k * maximum_looks)                 (conservative correction)

loss gate:     c = subjects accepted for I and not for C
               exact one-sided Clopper-Pearson upper bound of c / N at g*  <=  loss_margin
completeness:  share of pairs with the objective known for both  >=  completeness_floor
gain gate:     among pairs with both values known,
               w = pairs with value(C) <= (1 - minimum_relative_gain) * value(I)
               l = pairs with value(C) >  value(I)
               P(X >= w | X ~ Binomial(w + l, 1/2))  <=  1 - g*        (exact sign test)
C moves directly ahead of I only when all three pass; several passing
challengers are ordered by w / (w + l); ties keep the declared order.
```

The loss gate ignores the challenger's wins, so "faster but fails on cases
the incumbent handles" cannot pass: that is the D-12 adversarial line
("cheaper but lower-quality routes must not become defaults"). Paired tests
remove differences between subjects, so they need fewer subjects when two
engines' outcomes on the same subject are correlated, as they usually are. The
correction for several challengers and several looks keeps repeated
evaluation from manufacturing a false switch; when `maximum_looks` is reached
the comparison closes as "not established". The statistics are implemented
with the standard library (`math.comb` for the binomial tail, bisection for
the Clopper-Pearson bound) and cross-checked against `scipy.stats.binomtest`
in a check that runs only when scipy is installed.

### 8.6 The minimum sample and its floor

The host declares `minimum_matched_records` in the rule; there is no default
in code. Each slot record declares an `evidence_minimum_floor`, reviewable
data rather than a hidden constant, and a policy below it is refused. The
initial floor is 10 for every per-attempt slot. Reason: below ten matched
records one success moves the verified rate by ten percentage points or more,
so a single lucky run could reorder a production slot. A slot can raise its
floor in data (served search, where judged queries are plentiful, can use 30).

### 8.7 The one-million-run rule

The owner, September 18, 14:15: "we don't want to make any decisions yet on
heuristics until we get at least one million runs ... An exact fingerprint
heuristic at an atomic level for a reason, build, or execute could be okay".
The repository records it as the proposed Constitution rule LE-DATA-001 and in
`core/heuristic_adoption.py` (`DEFAULT_MINIMUM_RUNS = 1_000_000`).

This design stays inside the exception. Evidence ranks engines only for
requests whose scope fingerprint is identical to the one the evidence was
measured on: an exact fingerprint at the atomic level of one step. Every
number the rules use is a declared, digested policy value, not a code default.
Anything that transfers evidence across scopes (a similar task, a learned
router, a bandit, a transferred threshold) is a heuristic of kind
`similarity` or `routing_model` and goes through
`HeuristicAdoptionPolicy.decide`, which refuses below the declared run count
and without a published dataset version. That module is parked today, so the
path stays closed until its suite is collected again (package F11 of the plan).
Every decision already records its propensity, so the data for later
off-policy evaluation is collected from day one without adopting anything.

Evidence ranking therefore pays off for recurring steps: hosted search, a
customer's nightly job, a repeated build or test step. A one-off step runs on
the declared order. That is intended and must be explained, so it is not
reported as a defect.

### 8.8 Binding and revalidation at use

The envelope rechecks, before every use: the registry still holds the same
engine object; its current native declaration still projects to the bound
descriptor digest (the existing `CapabilityInvocationPolicy` pattern of
`expected_handshake_digest`); the installation digest is unchanged; and the
slot's own recheck passes (`HarnessRegistry.get`,
`HarnessProcessSpec.validate_unchanged`, `negotiate`, the retrieval handshake
digest, the service `protocol_version`). A harness binary replaced between
selection and launch is refused as `engine_changed_after_selection`.

### 8.9 Fallback

```text
Engine failure kinds
├── may trigger a declared fallback
│   ├── engine_unavailable                  (HarnessFailureKind.UNAVAILABLE)
│   ├── capability_requirement_unsatisfied  (HarnessFailureKind.INCOMPATIBLE)
│   ├── engine_reported_failure             (HarnessFailureKind.EXECUTION_FAILED)
│   ├── output_validation_failed            (HarnessFailureKind.RESPONSE_REJECTED)
│   └── semantic_response_rejected          (HarnessFailureKind.SEMANTIC_REJECTED)
└── terminal: never a fallback trigger
    ├── engine_changed_after_selection
    ├── effects_uncertain                   (UNEXPECTED_EFFECTS_REQUIRE_RECONCILIATION)
    ├── accounting_uncertain                (UNRESOLVED_MODEL_ACCOUNTING)
    ├── shared_provider_failure             (PROVIDER_OR_SHARED_GATEWAY_FAILURE)
    ├── evaluation_inconclusive             (RESPONSE_EVALUATION_INCONCLUSIVE)
    ├── authority_exhausted                 (SHARED_BUDGET_EXHAUSTED)
    └── policy_refused
```

The first five map one to one onto today's harness failure kinds in
`core/harness_fallback.py`, and the terminal kinds in brackets are the
outcomes `assess_harness_attempt` already returns instead of a switch, so the
general rule keeps every refusal the harness rule has today. An inconclusive
evaluation is never a pass and never permission to try another engine
(`architecture.yaml`, `inconclusive_evaluation_never_becomes_a_pass_or_permission_to_retry`). The slot's fallback ceiling bounds what a host may
declare: `none` (never a second engine: store, identity, payment, secrets),
`before_dispatch_only` (a second engine only if the first never started:
email, retrieval, workspace), or `after_failure_without_effects` (a second
engine after a typed failure that left no effect: step executor, model
access). `assess_engine_attempt` generalizes `assess_harness_attempt`: it
fails closed on uncertain accounting, on unexpected effects (tool events,
spawned tasks, committed writes), on a provider failure shared by both
engines, and on exhausted shared budget; then it maps the failure to a kind
and switches only when that kind is in `fallback_on` and a next engine exists.
A fallback never replenishes consumed authority, never grants tools or
skills, and never moves past an uncertain effect: `effects_uncertain` stops the
sequence until reconciliation. Same-configuration retry, changed settings,
engine fallback, same-provider model fallback, cross-provider failover,
formatting repair, evaluator-triggered repair and task replanning stay
distinct decisions, and cross-provider failover still needs `allow_failover`
in the run contract.

### 8.10 Three selection modes

```text
Selection modes
├── one_of: one engine serves each invocation
│   └── initial candidates, ranking, ordered fallbacks or an explicit no-fallback
├── set_of: a declared set of engines is enabled at the same time
│   ├── each invocation goes to exactly one member, picked by the slot's dispatch key
│   │   (credential form, protocol version, client, source role, destination)
│   ├── never by preference and never as a fallback between members
│   └── an ineligible member is recorded and left unbound; an ineligible required member stops the host
└── derived: the engine follows another slot's choice
    ├── through a declared field (the step engine's instruction style, the evaluation
    │   contract, the server's transport, the executor profile's isolation)
    └── no ranking; an ineligible derived engine refuses the invocation
```

### 8.11 Joint selection

Where two slots interact, the candidate is the pair. The step executor and
model access are the main case: the existing guide
`docs/guides/configuration-preferences-and-meta-selection.md` says "Do not
choose the highest-ranked model and highest-ranked harness independently and
assume they work together", and `select_harness` already matches evidence on
provider and model. The eligibility screen checks the pair, the evidence is
keyed by the pair, and the scope fingerprint holds the fixed side. Only slots
declared as joined are selected jointly, so evidence does not fragment.

### 8.12 The cost of selecting

Selection is deterministic and effect-free, so an identical input gives an
identical decision, and exact reuse bounds the cost on hot paths. The
selecting work itself is measured like any engine, so its overhead appears in
Run History. The overhead must be measured before per-call selection is
enabled on a hot path such as hosted search.

### 8.13 What selection never does

- It never considers an engine the host did not install and switch on.
- It never grants model, file, network, secret, spending or external-effect
  authority, and never turns failover on.
- It never calls a model, probes a provider, installs software or starts a
  process.
- It never ranks from confidence, a guessed cost, a vendor benchmark, or
  evidence the review process rejected or the producer approved.
- It never pools unmatched populations or evaluators.
- It never accepts a task or promotes intelligence.

## 9. Recording and measuring

### 9.1 Where every decision is recorded

Decisions use the existing event vocabulary. Five raw event kinds are added to
`_CANONICAL_EVENT_MAP` in `core/event_vocabulary.py` and to the ledger to Run
History mapping in `core/run_history.py`, mirroring the model route kinds that
exist (`model.route.selected`, `model.route.rejected`). No new family is
created. The existing detector `unmapped_ledger_event_kind` fails the build on
any raw kind missing from the map, so the vocabulary cannot drift.

| Raw kind | Canonical family (exists) | Run History type (exists) | Carries |
|---|---|---|---|
| `engine.selection.requested` | `capability.search.started` | `capability_search` | Slot, scope digest, policy digest |
| `engine.selection.completed` | `capability.search.completed` | `capability_search` | The full `engine_selection_decision/v1` |
| `engine.selected` | `capability.selected` | `capability_search` | Binding or reuse, with the decision digest |
| `engine.rejected` | `capability.rejected` | `fallback` | One ineligible candidate or one failed attempt |
| `engine.attempt.measured` | `state.committed` | `custom` | One `operation_cost_record/v2` |

Where the decision lands depends on the selection phase:

| Phase | Record | Location |
|---|---|---|
| per_attempt, loop_start | `engine_selection_decision/v1` | The ledger of the owning Loop, then Run History |
| a fallback | the same record with phase `fallback` | The same ledger |
| host_start | `engine_bindings_report/v1` with one decision per slot | The host loader's output: `configure` prints it, `serve` logs it once without secret values, administrators read it with `loop-engine engines list --config`. The public capabilities record carries only client-relevant facts derived from it, such as the bound search engines |
| release | `pilot_release_record/v2` engines map | The release record under `artifacts/` |

### 9.2 What the envelope measures for every attempt

```text
Per attempt, by the envelope, never by the engine
├── Time, from the envelope's monotonic clock
│   ├── admission: waiting for a capacity slot
│   ├── setup: process start, sandbox, session, index build
│   ├── execution: the engine's work
│   ├── verification: structural checks inside the envelope
│   └── recovery: repair or fallback bookkeeping
├── Usage: physical model calls counted by the gateway; tokens as the provider reported them
├── Cost: provider-reported, or reported usage times a price record with digest; else unknown
├── Disposition: completed_unverified, failed, engine_refused, refused_before_dispatch,
│   cancelled, deadline_exceeded, budget_stopped, effects_uncertain
├── Identity and pairing: engine, digests, scope, subject, selection path, propensity, pair
└── Acceptance: never written here; it arrives later as an independent verdict
```

A refusal by this system's own guard before the engine ran
(`refused_before_dispatch`) is not counted against the engine; repeated
occurrences mean its declaration does not match reality, which triggers
requalification, a host review. A refusal by the engine itself
(`engine_refused`, for example a provider content refusal) counts as not
accepted, and its rate is reported separately. An `inconclusive` verdict
counts as not accepted for both arms of a pair. Measurement records hold
identities, digests, counts, timings and codes, never prompts, outputs,
request bodies, headers or secret values: the telemetry baseline of `ASTRA.md`
("metadata only"). Evidence compiled from hosted tenants is kept per tenant
unless a declared consent scope permits pooling.

### 9.3 Defects that must be fixed before any number is trusted

Each was read in source at `97e805f`.

| Defect | Where | Consequence if left | Fix |
|---|---|---|---|
| An adapter-reported time replaces the envelope clock | `core/external_harness.py`, `run_external_harness`: `elapsed = result.elapsed_seconds`, measured only when the adapter left it empty | An engine can report itself fast | The envelope's time is authoritative; the adapter's value is kept apart as `engine_reported_seconds` |
| A zero default for attempt time | `core/model_gateway.py`: `GatewayAttempt.elapsed_seconds: float = 0.0` | An attempt that never set its time reads as the fastest | The default is removed; every construction site passes its measured time |
| The gateway names itself as the implementation | `core/model_gateway.py`: `OperationCostCapture(..., "model_gateway", ...)`, asserted by `a_gateway_with_a_cost_ledger_writes_one_cost_record_per_invocation`; the live typed decision path does the same in `core/decisions/gateway.py` (`OperationCostCapture(gateway.cost_ledger, "model_call.typed_decisions", "model_gateway", ...)`) | Routes and decision engines cannot be ranked from cost records | The record names the route's engine reference, and for typed decisions the decision engine and its route; the check's expectation changes with a recorded reason |
| Cost records live in process memory and are optional | `OperationCostLedger` is a list; the gateway writes only when a ledger is passed | Nothing survives the process; evidence cannot be compiled | Every envelope writes `engine.attempt.measured` into Run History |
| The cost ledger already ranks implementations, on the producer's own outcome | `core/operation_cost_records.py`: `OperationCostLedger.compare` orders implementations by mean time over records whose producer wrote `verified`, with `min_samples: int = 2` as a code default, and names a `preferred` one; `implementations()` feeds the parked `core/implementation_choice.py` | A second ranking path beside the evidence rule, admitting self-acceptance, a sample size nobody declared, and a faster engine that fails more | With version 2 the ledger only reports: acceptance comes from joined independent verdicts, the sample size has no default, and no selection path reads it; only the evidence pipeline of section 10 ranks engines |
| The live overnight runner bypasses the gateway | `overnight_cli.py`, `_model_caller`: `make_adapter(endpoint).chat(...)` | Its model calls are invisible to measurement | It reaches models through `model_access` |
| The hosted service records no operation durations | `core/service_runtime/http.py` | Search engines cannot be compared on the served path | The service envelopes write the same record |
| The span exporter writes zero durations and a non-conforming name | `core/otel_export.py` (parked) | Exported traces cannot show engine time | Fix when the exporter is restored behind `run_history_export` |

## 10. Evidence: from measurements to a changed order

### 10.1 The pipeline

```text
Evidence pipeline
├── 1. Attempt records: operation_cost_record/v2 on each run's chain
├── 2. Independent verdicts: evaluation events from a different Loop, bound to attempt identity
├── 3. Commit: the run's chain is committed and verify_chain() reports it intact
├── 4. Compile: a deterministic Practitioner Loop (practitioner.code_execution)
│   ├── reads committed histories by reference and verifies chain and authorship
│   ├── joins attempts with verdicts by attempt identity and output digest
│   ├── keeps only matched records: same subject, same scope, same evaluator identity,
│   │   exact engine versions, selection path comparison_arm or frozen_population
│   ├── excludes synthetic records and lists every exclusion with its reason
│   └── writes engine_trial_evidence/v1 through the CatalogStore contract into the
│       Runtime History and Solution Intelligence layer
├── 5. Review: an independent reviewer issues engine_evidence_review/v1
│   └── not the engine, not the producing Loop, not the compiling Loop
├── 6. Snapshot: engine_evidence_snapshot/v1 lists approved evidence; one publication = one look
└── 7. Qualification: a host decision writes engine_qualification/v1 for the scope,
       citing approved evidence, with an expiry after which the fact returns to unknown
```

Evidence expires with the engine version (a new version starts with none),
with the rule's window, and with the qualification's expiry. A provider that
silently changes a model behind a stable name is caught only through the
window and the expiry, which is why both are required fields. Every snapshot
is reported against two baselines, the single best engine for the scope and
the per-subject best engine computed from paired runs, and the share of that
gap a policy closes is the comparable number. Snapshots can also be exported
as an offline file shaped like the algorithm selection library layout (runs,
features, splits), so outside selectors can be evaluated on this data without
entering the runtime.

The same records feed the existing learnable-record path
(`model_call_learning_record/v2`, `model_call_training_export/v1`), so data
toward the one-million-run threshold is collected now without adopting
anything learned.

Harness run records that consenting customers contribute (roadmap S-6.41: how
each harness and step broke a problem down, which items it loaded, and whether
the step was accepted) enter this pipeline at step 1, as metadata-only attempt
records under the customer's declared consent scope. They rank nothing by
themselves: like every attempt, they count only after compilation, independent
verdicts and review, only for the exact scope, and never across tenants
without that consent. Raw prompts, code or data are never collected without
explicit opt-in, and a record never carries a credential.

### 10.2 Side-by-side comparison on a sample of traffic

Paired evidence needs both engines to run on the same subject.
`engine_comparison_policy/v1` makes that safe:

```text
engine_comparison_policy/v1
├── slot and the scope classes it covers
├── comparison engines: registered; candidate or active; every eligibility screen passes
│   except qualification, which may be "candidate" for a comparison arm
├── sampling: SHA-256 over (salt, attempt identity), first eight bytes as an integer,
│   compared with a declared rate written as a fraction; a maximum per window;
│   the hash version is recorded, and each comparison has its own salt
├── allowance: a reference, with its digest, to a separately approved authority grant
│   for exactly this comparison (model calls, tokens, spending, wall time, concurrency);
│   the policy itself grants nothing, and without such a grant the allowance is zero
├── timing: after the primary by default, so the primary's time is not contaminated
├── effects: the arm declares no external effect, or runs in a discardable confined
│   workspace with network limited to the model broker
├── privacy: recipients must be inside the step's authorized recipients; hosted tenant
│   traffic needs the tenant's declared consent scope
├── outputs: never served, never metered, never written to Runtime Memory, never passed on
├── evaluation: the same evaluator identity for both; a model-led evaluator is not told
│   which arm produced which output
└── stop: allowance exhausted, maximum looks reached, or primary admission time above a ceiling
```

The comparison runs as a Spawned Loop of the owning Loop, with its budget
carved from the comparison allowance, never from the step's allowance.
Cancelling the owning Loop cancels it. An arm whose effect state becomes
uncertain is reconciled, never retried.

Where comparisons start, in order of safety: first hosted search (no effects,
local compute, no model calls, no spending: the served behaviour against the
measured purpose-match policy); second, record store reads against a
read-only replica during the PostgreSQL migration rehearsal (writes are never
duplicated); third, step execution on a customer's own machine under the
customer's own allowance, zero by default; last, model routes, only with a
recorded owner decision, because engineering holds no authority for model
calls or live charges.

## 11. Procedures

### 11.1 Add an engine

1. Read `loop-engine engines explain SLOT` (planned; until then, the slot's
   generated page). It names the edge contract, the engine protocol, the
   kinds, the factory table file, the conformance kit and the checks.
2. Search for an existing project, repository, design or paper that already
   provides the engine, and record the decision (reuse, adapt or build, with
   its sources) beside the engine card, as `AGENTS.md` and roadmap D-19
   require before any component is built.
3. Write one engine module implementing the engine protocol, in the folder of
   the slot's functional component (section 7.8). Its first docstring line
   names the slot, the kind, the edge contract and the checks, and a check
   compares it with the factory table.
4. Add one factory table row: kind, settings record, constructor, module path.
   For a process harness, add one `harness_recipe/v1` record instead of the
   six code edits of today.
5. Map the module in the architecture map and put its checks in a collected
   suite. An engine whose checks resolve only to a parked suite cannot become
   active.
6. Run the slot's conformance kit. The engine enters lifecycle `candidate`.
7. A host adds one `engine_installation/v1` with `enabled: false`, validates
   the file with `loop-engine engines check`, then runs a declared trial under
   explicit authority.
8. An independent reviewer approves or rejects; `engine_qualification/v1` is
   written; the host switches the engine on and places it in the policy.

No call site changes, because call sites depend on the edge contract and the
slot's entry point only.

### 11.2 Update an engine to a new version

A new version is a new engine reference with no inherited evidence and no
inherited qualification. It enters as a candidate, is compared side by side
with the version it replaces, and is promoted by a new host policy version.
The old version is deprecated, then archived.

### 11.3 Swap the initial choice

Change `initial` in the host's slot configuration; nothing else. For a
service slot, follow the host file procedure the operator already uses:
validate the new file offline with known-wrong variants, copy the live file to
a dated backup on the volume, load the new file with the real loader inside
the running Machine, move it into place, restart, read `/api/v1/capabilities`
on every hostname, and save a record under a new name. Rollback is the dated
backup and a restart.

### 11.4 Switch things on and off

| Level | How | Effect on edges and call sites |
|---|---|---|
| One engine on one host | `enabled: false` on its installation, or remove it from the policy; restart a service | None. Decisions record `engine_disabled` |
| One engine for one run | `exclude` override, or `excluded_installations` in the Loop definition | None |
| A whole functional component | Switch off every installation of the slot | None. Neighbours receive the slot's declared unavailable result |
| An intelligence family | `intelligence_family_policy` (**exists**) | None; refusal `item_family_not_accepted` |
| Emergency on the live service | `loop-engine engines disable SLOT/ENGINE --config /data/host.json` (planned) prints the exact change and its digest; rerun with `--approve-effect-digest` writes a dated backup and the new file beside the old one | None |

Every change keeps the previous file as a dated backup, which is the owner's
"make sure we ALWAYS have a backup via checkpoints" applied to configuration,
and every decision carries the configuration digest, so a person can tell
which revision made a choice.

### 11.5 Retire, archive and park

1. `engine_retirement/v1` names the engine, the reason, the replacement and
   the decision record. The engine becomes `deprecated`: it can no longer be
   an initial choice, it remains a valid fallback, and each decision that uses
   it carries a warning.
2. `loop-engine engines check` reports every host file that still names it.
3. In the next release it becomes `archived`: a host file that enables it is
   refused at load with `engine_retired` and the named replacement. Two
   releases give operators one release of warning, which avoids the startup
   refusal that finding F2 describes.
4. Parking, when the owner decides to take archived code off `main`: the
   module and its suites leave `main`, the implementation location becomes the
   checkpoint branch at the last working revision, and the folder's
   `PARKED.md` names the slot, the engine identifier and the restore command.
   The slot keeps listing the engine, so a coding harness knows it exists
   without its code being in the tree. The owner's standing rule "do not
   remove components, just build out" holds: nothing is lost from history.

### 11.6 Restore a parked engine from the checkpoint branch

The branch strategy says turning a capability back on is "a recorded owner
decision implemented behind the named boundary, never a silent merge from the
checkpoint branch". The checkpoint branch is an ancestor of `main`, so a merge
would bring nothing back; a restore is always an exact path checkout.

1. `loop-engine engines restore step_executor/in_process_solve --plan`
   (planned) is read only. It prints the implementation location
   (`a3bd0f1`), the owner decision it needs, the exact paths and their blob
   digests, the suites to collect again (read from
   `suite_collection_exceptions`), the boundary rows they touch, and the
   engine it will return as.
2. The owner's decision is written into a decision record and the roadmap.
3. On a work branch, `git checkout a3bd0f1 -- PATHS` for exactly the listed
   paths (only needed once they have left `main`), plus one piece of new code:
   the adapter that wraps the restored runner as a `custom_loop_harness`
   engine of the step executor slot (section 13.10).
4. The restored suites are collected again, the executor's conformance kit
   runs, and `a_delegation_claim_cannot_be_met_by_an_in_process_engine` stays
   green, because the restored code runs only inside a separate confined
   process.
5. The folder's `PARKED.md` gains one line naming the restored engine, its
   revision and the decision.

### 11.7 Change an edge contract (rare, and deliberately heavier)

1. Write the new contract version and its record type (`/vN+1`).
2. Revise the interaction rows in `component_interactions.yaml`.
3. Update every producer, consumer and engine in the same change; the
   pre-launch version policy forbids keeping the old reader.
4. Add a named check that the old version is refused before effects, with a
   removed-guard mutant.
5. If an older release must not honour a record the new release writes, the
   new record version is what makes the older release refuse it.

Independently deployed components (the hosted service and a customer's local
engine, a protocol client and the protocol endpoint) negotiate the highest
mutually supported version at initialization and refuse a downgrade that
loses semantics, integrity or authority checks.

### 11.8 Worked examples

**Claude Code as a step executor engine.** Today Claude Code is an
instruction-file style and a customer connection recipe, not an executor.
The path: a native adapter that drives the installed command in print mode
with streamed JSON output and bare configuration, answering each effect
request through a permission tool the envelope controls, with its model
traffic pointed at the relay broker. The relay already translates an
Anthropic Messages wire (`decode_anthropic_text_request` and
`encode_anthropic_text_response` in `core/harness_lightweight_recipes.py`,
used today for nanocode), but only for text: it refuses non-text content, so
Claude Code's streamed and tool-use traffic needs that codec extended. Claude
Code's support for a custom gateway address is inferred and must be verified
when the engine is built.
One recipe record (instruction style `claude_code`, already in
`STYLE_FILES`), one host declaration, offline probes producing a
`local_contract` qualification, then review. Every run needs explicit model
authority. Shipping any Anthropic software development kit inside the product
is a legal decision for the owner; driving a customer's own installed command
does not ship it.

**PostgreSQL as a record store engine (D-05).** A `server_database` engine in
`catalog/stores/`, declaring the atomic batch and the atomic read set only
when both are implemented: canonical JSON stored as text (not `jsonb`, which
reorders keys and would change digests), transaction-scoped advisory locks
taken in sorted order for every precondition identifier, a batch digest row
written in the same transaction, and reconciliation of an unknown commit
through that row and `pg_xact_status`. It runs the golden store suite and the
D-05-T01 negative control, then a migration rehearsal, cutover and rollback
drill for an `operational_drill` qualification. Only then does the host switch
its initial choice from local.sqlite, and only then may the service run more
than one Machine. A serializable variant without advisory locks is a second
engine, compared on the same transaction suite, as the owner's "test two
versions" direction asks.

**The served search moves to the measured policy (S-6.32).** The host
installs both `served_before_2026_09_21` and `purpose_match_default`, with the
first as the initial choice. A held-out comparison on the frozen judged query
set, through the existing "retrieval tournament" boundary, produces trial
evidence for both. After independent review the host makes
`purpose_match_default` the initial choice and keeps the other as its
fallback. The capabilities record, derived from the bound engines, reports the
new policy instead of fixed strings.

## 12. Rules for a person or coding harness that changes one engine

```text
Changing one engine
├── You may edit
│   ├── the engine module named on its engine card
│   ├── its row in the slot's factory table
│   ├── its recipe record (step executor engines)
│   ├── its checks and conformance fixtures
│   └── example host configurations that name it
├── You must not edit (these are edges)
│   ├── the slot's edge contract records
│   ├── the interaction rows in component_interactions.yaml
│   ├── any call site (no call site names an engine)
│   └── another engine's module
└── If the change needs anything from the second list, it is an edge contract
    change: stop and follow section 11.7
```

The guards that keep an edit local: `engine_classes_are_named_only_at_their_registration_sites`
(an abstract syntax tree scan; concrete engine classes may be constructed only
in their factory table module and its checks), `importing_an_engine_module_registers_nothing`,
`engine_module_imports_only_its_slot_contract_and_its_own_dependencies`,
`engine_checks_resolve_to_collected_suites_before_qualification`,
`every_engine_module_holds_one_engine_in_its_component_folder`, and
`generated_engine_pages_are_current`.

The command group `loop-engine engines` (planned, dispatched early like
`records` and `service`):

| Command | Effect | Writes anything |
|---|---|---|
| `list [--slot SLOT] [--config FILE]` | Every slot and its engines, with kind, lifecycle, location, enabled, availability and qualification | No |
| `explain SLOT` | The slot card: function, edge contract, protocol, kinds, factory table file, registry, kit, checks, and the files you may and may not edit | No |
| `show SLOT/ENGINE` | The engine card: descriptor, installations, qualification, checks, module path | No |
| `check --config FILE` | Validates every engine section of a settings or host file against this release, starting nothing | No |
| `select SLOT --config FILE --profile PROFILE@VERSION` | Runs the selection path and prints the decision | No |
| `enable` or `disable SLOT/ENGINE --config FILE [--approve-effect-digest D]` | Prints the exact change; with approval, writes a dated backup and the new file | With approval |
| `qualify SLOT/ENGINE --evidence FILE --review FILE` | Admits a qualification bound to exact evidence and an independent review | Yes |
| `retire SLOT/ENGINE --replacement ENGINE --reason TEXT` | Writes `engine_retirement/v1` | Yes |
| `restore SLOT/ENGINE --plan` | The read-only restore plan of section 11.6 | No |

Generated documentation: one page per slot under
`docs/components/engines/`, built from the slot catalogue, the factory tables,
the descriptors, the recipe catalogue and the checks, like
`docs/roadmap/CONTINUATION-STATUS.md` is built from the roadmap. Never edited
by hand; a check fails when a page is stale. The same content as data,
`docs/components/engines/engines.json`, lets a coding harness orient itself
without reading code. `AGENTS.md` gains one short section, "Changing one
engine", that points to these pages and states the rules above.

## 13. The step executor slot (S-6.31, phase 2 of the harness-first plan)

### 13.1 Function

The step executor slot performs the work of a discrete cognitive or act step
Loop node in a separately initialized harness, and returns one typed,
observed result to the owning Loop. The complete behavioral explanation, from
`ASTRA.md`:

A discrete cognitive or act step Loop node is an independently governed
instance of the Loop runtime responsible for one clearly defined cognitive
step or action. A cognitive step might interpret information, identify a
missing requirement, compare alternatives, or evaluate a result. An action
might inspect a directory, build software, execute a test, create an artifact,
or send an authorized email.

Each discrete cognitive or act step Loop node receives the context,
instructions, skills, plugins, tools, and working files relevant to its
assignment. Essential information can be supplied directly, while additional
information can remain in centralized storage behind authorized, versioned
references. It does not automatically need the entire task history or every
available tool.

A separately initialized harness process, such as OpenCode, Pi, Codex, or a
custom implementation, can perform the assignment. When explicitly permitted,
another harness can attempt the same assignment after a failure. The
assignment's contracts, permissions, history, and remaining authority persist
across those attempts.

Discrete describes the scope of the assignment, not a restriction to one
attempt, one model call, or one output. A discrete cognitive or act step Loop
node can examine whether an observation matches its expectations, identify a
problem, repair or change its approach, and repeat until its declared
completion conditions are satisfied.

Alternatively, a discrete cognitive or act step Loop node can publish an
initial candidate output and continue working while its continuation
conditions and authority permit. It can produce additional alternatives over
time, including alternatives that are better, worse, or useful under different
circumstances. Consumers must identify exactly which output they used.
Publishing an output does not necessarily mean that the producing assignment
has finished.

For externally consequential actions, continued operation does not authorize
repeated effects. For example, generating alternative email drafts can
continue, but sending an email requires its own authorization and protection
against duplicate delivery.

In this slot, "a separately initialized harness process ... can perform the
assignment" is engine selection, and "another harness can attempt the same
assignment after a failure" is the slot's declared fallback, which carries the
assignment's consumed authority forward. The owning Loop keeps the task, its
contracts, its authority, its independent evaluation and its Run History.
Completion by an engine is never task acceptance.

### 13.2 Why the step needs its own edge

Today the harness boundary serves one function: realizing one semantic model
response. `HarnessRunRequest` (`harness_request_identity/v3`) requires
`authorize_model_calls=True`, takes a finite JSON input, and the process path
admits output only when it equals a brokered model response. Its only
production consumer is `HarnessSemanticBinding`, reached from the parked
`code_nodes/solution_model_port.py`. A step of work is a different function:
it has typed inputs and outputs, effect grants, spawn rights, candidate
publication and cancellation. Two functions get two edges. The model response
edge stays exactly as it is, as the `harness_brokered_response` kind of
`model_access`; the step gets `step_run_request/v1` and `step_run_result/v1`,
the "typed step run request and result records" roadmap step S-6.31 names.
Both edges are served by engines held in the same `HarnessRegistry`: an
engine declares which edges it serves, so there is still one registry and one
declaration per engine.

### 13.3 The edge

```text
step_run_request/v1  (in)
├── step identity: owning Loop, definition reference and digest, step name,
│   attempt number, idempotency key
├── assignment: goal, typed inputs as references with role and digest,
│   output contract (LoopContract ports and their match mode)
├── publication: final_only | candidates_then_final
├── authority: exact effect grants bound to approval references, tool, skill and
│   protocol server references, a path-confined workspace view, a network
│   allowlist, model routes and authorized model identities
├── budget: preemptive limits (wall time, model calls, tokens, spawned tasks),
│   kept apart from post-run acceptance bounds
├── instruction material and context references, with their visibility
├── executor requirements: required features, preemptive limits, allowed
│   isolations, allowed engine kinds, delegation_required
├── cancellation: an owned handle reference and a deadline
└── spawn rights and the outcome vector policy

step_run_result/v1  (out)
├── status: completed | failed | refused | unavailable | cancelled |
│   budget_exhausted | input_required | auth_required | effects_uncertain
│   (Agent Client Protocol stop reasons and Agent2Agent task states map into this list)
├── outputs by port with digests; published candidates in order; artifacts with digests
├── workspace change set and observed effects: committed, not committed or uncertain
├── permission requests and the envelope's answers
├── accounting: calls counted by the gateway, reported tokens, unknown kept unknown
├── loaded material observed: offered, fetched, loaded and used kept apart
├── native session, goal, turn and tool-call identities where the harness exposes them
├── trajectory reference, exportable in the shape of the Agent Trajectory Interchange
│   Format, version 1.7 (the Harbor evaluation framework's trajectory format)
├── executor actually used: engine reference, descriptor and installation digests,
│   process identity and sandbox profile digest, and "delegated", computed by the envelope
├── engine_preferences: typed preferences for later attempts of the owning Loop
│   (section 8.4); data the owning Loop may admit, never an instruction
└── consumed authority, and the owning Loop's outcome vector (the engine cannot grade it)
```

`effects_uncertain` blocks every fallback until reconciliation. Unknown usage
stays unknown, never zero. Every key is present in every result, whichever
engine produced it; a value the engine does not expose is null and reads as
unknown, so every engine behind the slot returns the same keys (rule 13).

### 13.4 Engine protocol and registration

The engine protocol stays `ExternalHarnessAdapter`, versioned as contract
`external_harness_adapter/v2`: `info()` plus `run_step(request, services)` for
engines that serve the step edge, and the existing `run(request, services)`
for engines that serve the model response edge. `HarnessAdapterInfo` gains
three required fields: `adapter_contract_version`, `engine_kind` and
`supported_edge_contracts`. `HarnessRegistry.register` gains three refusals:
a missing or unknown contract version, an unknown kind, and an adapter whose
supported edges include none of the slot's current versions. It already
refuses an identifier registered twice unless the caller passes
`replace=True`, which fixtures use; a replacement changes the descriptor
digest, so a decision made before it fails revalidation at use. This moves the
pre-execution refusals of `run_external_harness` into registration, as the
September 22 seam review asked, so an incompatible adapter can never be
selected and then refused mid-run. The identity gap is elsewhere: one
identifier, `opencode`, names two different engines in two places, the parked
`OpenCodeProcessAdapter` (`OPENCODE_HARNESS_ID = "opencode"`, refusal only)
and the recipe engine of `embodiments/opencode/harness.json`, so a record that
says `opencode` does not say which engine ran. The parked adapter is renamed
`opencode.raw_host`, matching the `architecture.yaml` invariant
`opencode_raw_host_execution_is_quarantined`, and from then on one engine
identifier names one implementation across the slot catalogue and every
installed declaration.

### 13.5 Engine kinds and the delegation rule

| Engine kind | What it is | Isolation | Counts as delegation | State today |
|---|---|---|---|---|
| `agent_protocol_harness` | A harness driven through the Agent Client Protocol: JSON-RPC 2.0 over standard input and output; `initialize` negotiates capabilities; the client answers `session/request_permission` and may serve file and terminal requests; `usage_update` reports tokens; stop reasons map to statuses | `os_sandbox` today, `container` later | yes | planned; OpenCode (`opencode acp`, native, MIT) first, Goose (`goose acp`, native) second |
| `native_protocol_harness` | A harness driven through its own documented protocol: Codex app-server (JSON-RPC over JSON lines, a generated schema pinned per release), Claude Code print mode with streamed JSON, Pi remote control mode; ZCode through its app-server path is a candidate (roadmap S-6.42), listed only after isolation, cancellation and native loading are tested | `os_sandbox` or `container` | yes | planned |
| `text_relay_harness` | The 18 recipe styles run in Bubblewrap with native tools denied and every model request brokered; fits steps whose whole output is text and which need no tools or effects | `os_sandbox` | yes, for text-only steps | exists, no live caller; offline qualified: codex, openinterpreter_rust, nanocode, trae_agent |
| `custom_loop_harness` | The harness the owner may build after a large user base: the Loop runtime inside a separate confined process, speaking the step edge, with model calls relayed back through the broker | `os_sandbox` or `container` | yes | planned |
| `remote_agent` | An opaque agent across an organization boundary through Agent2Agent | `remote` | yes | deferred until a customer needs one |
| `agent_framework_kit` | Pydantic AI, Deep Agents, OpenAI Agents SDK, Microsoft Agent Framework, run in this process | `none` | no | exists; packages not installed in the verified environment |
| `direct_model_step` | A step that calls a model endpoint directly in this process | `none` | no | exists: the overnight night runner |
| `in_process_runner` | The retired in-process path: solve, kernel, delegation, Solution Canvas, campaign, Kaggle, OpenCode step session | `none` | no | parked, frozen at `a3bd0f1` with 6229 of 6229 checks |
| `typed_decision_step` | A streamlined step answered by a typed decision endpoint (Jev, Circuit, System One) through `model_access`, the "streamlined harness" the owner described on September 19 | `none` | no | planned |
| `structural` | The deterministic structural handler that crosses a step position without semantic work | `none` | no, and it does no executable work | exists: `default_handler` |

The harness-first rule becomes typed data instead of prose. The slot record
declares which kinds count as delegation and that delegation is required for
the hybrid and non-deterministic modes on the main line. A step request
carries `delegation_required`, and an engine of a non-delegating kind is
ineligible for it with reason `engine_kind_not_allowed`. The envelope, never
the engine, computes `delegated`: true only when the engine's kind is a
delegating kind, its isolation is `os_sandbox`, `container` or `remote`, the
result carries a process identity and a sandbox profile digest (or, for a
remote agent, the remote task identity), and, for engines that run as local
processes, every model call entered through the broker as a Spawned Loop of
the owning Loop. A remote agent's model calls are reported, not brokered, and
are recorded as such. An adapter that writes `delegated: true` into its own
result is ignored. This is
what makes "a delegation claim met by the in-process path, however the call
site is disguised" impossible to select and impossible to report.

One harness per step. `AGENTS.md` makes a unique, freshly started harness for
every step the default design, and roadmap S-6.42 asks for a recorded test,
for Codex, Claude Code, OpenCode and Pi, that each can start an independent
instance with only the step's files. The executor profile therefore carries
`fresh_instance_per_step`: `proven` only when a recorded qualification shows
an instance that started with only the step's mounted material (no user-level
configuration, no earlier session, no shared cache that carries state), and
`unproven` otherwise. A step that requires one harness per step, the default,
refuses an engine whose value is not `proven`, with reason
`engine_unqualified`; such a harness is marked unsupported for
one-harness-per-step, never assumed to work. Placement `fresh_process` is this
default; `long_lived_session` and `pooled_sessions` are separate qualified
placements and never the default.

### 13.6 Engines, in order of adoption

1. **Text relay engines for text-only steps.** The 18 existing styles become
   step engines through one small step wrapper: the step's typed inputs are
   rendered into the instruction and prompt material, and the admitted text is
   parsed into the output ports. No tools, no effects. Codex is already
   qualified offline for this variant. This is the fastest way to meet phase
   2's acceptance ("one executable step goes only through a harness") for a
   reasoning step.
2. **OpenCode through the Agent Client Protocol.** The first engine that can
   do a step needing tools and file effects. The protocol's Python library is
   Apache 2.0, supports Python 3.10 or newer and reaches about 39 agents;
   OpenCode speaks it natively, so no wrapper layer is needed. The adapter
   converts protocol types to this repository's records, so library types never
   cross the edge. The harness runs inside Bubblewrap; its provider base
   address points at the relay broker, so model authority and accounting stay
   in the engine; `session/request_permission` is answered only within the
   step's exact grants; file effects are confined to the mounted work folder.
   The client-side file and terminal methods help only if the agent uses them;
   many agents use their own tools, so the sandbox remains the effect boundary.
3. **Goose through the same adapter.** A second native protocol agent proves
   the edge does not fit one harness.
4. **Native adapters.** Codex app-server (the per-release generated schema is
   pinned by digest in the executor profile and refused on mismatch), Claude
   Code print mode, Pi remote control. Each is a new engine behind the same
   edge.
5. **The custom Loop harness**, when the owner decides to build it.

### 13.7 The harness recipe catalogue

Today adding a command-line harness edits six places in core code: the style
tuple in `HarnessProcessSpec.__post_init__` (`core/harness_process.py` line
111), the sandbox mount list (lines 263 to 270), the output extraction chain
(`_output`, from line 280), the relay preparation chain in
`core/harness_process_relay.py` (`_recipe` and `main`, from line 205), the
relay's wire choice in its request handler (`core/harness_process_relay.py`
lines 111 to 119: `gemini_cli` selects the Google wire, `nanocode` the
Anthropic Messages wire, `codex` and `openinterpreter_rust` the Responses
wire), and the recipe digests inside the process identity (lines 380 to 386),
plus two special cases (the Pi context capacity check at line 181 and the
Aider `COLUMNS` line at 275). The engine-side inventory counted five places;
the wire choice is the sixth. No named check covers the `unsupported_style`
refusal that the `freebuff` host file hits today.

The design replaces all of that with one package data file,
`src/loop_engine/data/harness_recipes.yaml` (`harness_recipe_catalog/v1`),
holding one `harness_recipe/v1` per recipe, shaped like the Agent Client
Protocol registry's entries:

| Field | Meaning |
|---|---|
| `style` | The recipe identifier a `harness.json` names |
| `variant` | `text_response`, `workspace_tools` or `agent_protocol` |
| `module`, `prepare_function`, `extract_function` | The one module mounted into the sandbox, and its functions; every recipe function takes one signature: `prepare(style, config, base)` returns command, overrides and prompt; `extract(style, stdout, expected)` returns the admitted text |
| `wire_protocols` | The model wire the relay translates, for example `openai_responses` or `anthropic_messages`; it replaces the style-keyed wire choice in the relay's request handler, and names the codec module the runner mounts beside the recipe's own |
| `instruction_style` | The row of `STYLE_FILES` this harness reads, which removes the second style vocabulary |
| `requires_context_capacity`, `sandbox_environment` | The Pi and Aider special cases, as data |
| `native_controls` | Native controls the recipe declares, with their owners |
| `distribution` | binary, npx, uvx or local; the version and SHA-256 the release qualified. The host's `harness.json` stays the one statement of what is installed (`package_version`, the digested software paths); binding refuses an installation outside the qualified pin rather than keeping two versions that could disagree |
| `module_sha256` | The digest of the recipe module |

The runner mounts and digests the selected recipe's module and the codec
module of each wire the record declares, and applies the special cases from
the record; the relay receives the record inside its configuration, chooses
the wire from `wire_protocols` instead of from the style, and imports only the
mounted modules by name. Today the wire codecs live in three recipe modules
(the Responses codec in `harness_responses_recipes.py`, the Google codec in
`harness_additional_recipes.py`, the Anthropic Messages codec in
`harness_lightweight_recipes.py`), so mounting only the recipe's own module
would break a recipe whose wire codec lives in another module. The catalogue is package data, never host data, so
a host file can choose only a recipe the release ships and digests, and the
sandbox mounts only the selected module. One harness program can therefore be
several engines: `codex` (text response, exists, qualified offline) and
`codex.workspace_tools` (native tools confined to the work folder, planned),
each with its own record and qualification.

### 13.8 Wrapper composition, native control, placement and confinement

These are settings of an executor installation, part of its installation
digest, never separate engines of their own:

| Setting | Values | Rule |
|---|---|---|
| `wrapper_composition` | `direct_adapter`, or a `harness_wrapper_composition/v1` reference | Only `direct_adapter` is eligible until a composition has a registered executor; the refusal is the existing `executor_refusal` state (`composition_without_executor`). A transport wrapper such as `codex-acp` needs the one-layer wrapper executor first |
| `native_control_policy` | A `harness_native_control_policy/v1` reference | A natively owned control is eligible only when the adapter declares it and the fallback policy allows native retry; native completion is a candidate observation, never acceptance |
| `placement` | `fresh_process` today; `long_lived_session`, `pooled_sessions` after product qualification | Placement changes isolation and state continuity, so qualification binds it; the embodiment lab stays development only |
| `confinement` | Derived from the executor profile's isolation through the `process_confinement` slot | Never falls back to weaker isolation; a tool-using step needs the egress proxy with an allowlist taken from the step's authority |

Outer and inner iteration share cumulative accounting, effect identity and
cancellation. A native goal replacement that resets the harness's own counters
(Codex documents this) never resets the envelope's measured usage.

### 13.9 Installed executor modes become backed by engines

Today "installed executor" is only a list of mode names; the established Loop
constructor declares every allowed mode installed
(`installed_executor_modes=selected_config.allowable_modes`, with
`compatibility=True`), so "a non-deterministic executor is installed" cannot
say which engine. Under this design, when a host binds a step executor engine
for a Loop that runs steps, that Loop's runtime context receives the binding
`step_executor`, and its executor modes are derived from the bound engine's
`supported_modes` instead of being copied from the allowed modes. The slot's
one delegate handler refuses a hybrid or non-deterministic step when no
`step_executor` engine is bound (`no_bound_step_executor`), before any effect.
Envelope Loops that wrap one physical attempt (a gateway route attempt, a
harness attempt) are unchanged, because the attempt itself is the executor.
The compatibility constructor keeps its recorded gap until the pre-launch
cleanup (roadmap S-6.26) retires it.

### 13.10 The future custom Loop harness, and how parked runners return

The owner's direction of September 21: "Once we have a large number of users
we can consider adding in a custom loop-node type of harness that we build",
and at 14:33, "later we will create our own custom loop-node in the format of
a harness like loop-node harness". The decision record adds that it is "not a
new runtime type, not a `*Node` class, and not a fork of the Loop runtime".

Shape: engine kind `custom_loop_harness`, a process entry point started inside
the confinement slot exactly like any harness, speaking `step_run_request/v1`
and `step_run_result/v1`. Inside that process the Loop runtime runs the step
with a model gateway whose only provider engine is a relay back through the
broker, so every model call is still brokered, counted and authorized by the
owning Loop outside. Its Run History returns as a trace artifact bound to the
owning Loop through the existing "external harness memory import" boundary.
This is also the only way a parked in-process runner can return: as the inner
implementation of a `custom_loop_harness` engine, never as an in-process call
site, so the phase 2 guarantee survives any restore.

### 13.11 The overnight night runner

`code_nodes/overnight_night.py` is the one live step path on `main`, and
`overnight_cli.py::_model_caller` calls `make_adapter(endpoint).chat(...)`
directly, bypassing both `ModelGateway` and every harness. It becomes a
visible engine, `overnight_direct_local_model`, kind `direct_model_step`, so
its use stays recorded; its model calls go through `model_access` with a local
endpoint route; and the overnight profile declares the step executor slot with
a harness engine as its initial choice (Pi, which already requires a
source-backed context capacity, against a local route through the broker) and
no fallback to the direct engine. The direct engine stays selectable only by a
profile that explicitly allows `direct_model_step`, which no harness-first
profile does. Reason: overnight work is a launch benefit, so it should run
through the same governed path customers use, while "build out, never remove"
keeps the direct option visible.

### 13.12 Deterministic steps: a recorded decision

The harness-first rule applies to hybrid and model-led steps. Deterministic
governed operations (engine selection itself, admission, structural
verification gates, service operations, workspace commands issued by the Loop)
stay the Loop's own deterministic handlers. Reason: a deterministic check has
no harness to delegate to, delegating it would add a model-driven process to
work that must stay exact and independent, and the phase 2 known-wrong case
concerns the retired in-process solve path. If the owner means literally every
step, the slot gains a deterministic engine kind and this decision is revisited.

### 13.13 Phase 2 acceptance

The harness-first record makes phase 2's acceptance "one executable step goes
only through a harness", with "a delegation claim met by the in-process path,
however the call site is disguised" as the known-wrong case. Three checks make
it provable, and a fourth keeps the qualification ladder of roadmap S-6.31
honest:

| Check | Known-wrong case it must reject |
|---|---|
| `a_delegation_claim_cannot_be_met_by_an_in_process_engine`, with control `removed_delegation_kind_rule_is_detected` | A step requiring delegation offered only a framework kit (isolation `none`), the overnight direct step, or an in-process runner registered under a harness-looking identifier such as `opencode_local`; the status must be `no_eligible_engine` and no adapter may be called |
| `delegated_is_computed_by_the_envelope_and_names_a_separate_confined_process` | A result produced by `default_handler` with `delegated: true` written into it; an adapter that sets its own flag |
| `a_step_needing_tools_or_file_effects_is_refused_by_a_text_only_engine` | A request with `writes_fs` or tool references reaching a text relay recipe |
| `native_loading_is_never_inferred_from_a_bridge_a_session_or_an_exit` (roadmap S-6.31's qualification ladder) | A harness recorded at the rung "material loaded" because a bridge is documented, a session identifier exists or the process exited cleanly |

Proof levels: `local_contract` first, a text-only step through the real
Bubblewrap sandbox with a deterministic broker fixture, then OpenCode through
the Agent Client Protocol with the same fixture. `end_to_end`, a real step
with a real provider, needs the owner's model-call authority, which the
September 20 authority record does not include. Until then the proof is
labelled `local_contract` and never reported as more. Roadmap D-19-T03 is the
end-to-end case: "Delegate one real step through a harness engine chosen by
the executor slot", with a second harness able to replace the first by
configuration.

## 14. Hosted search as an engine slot (S-6.32)

### 14.1 Today

`ServiceHttpApplication._search` builds `Retriever(records)` with default
backends and its own record shape, which matches the constant
`SERVED_BEFORE_2026_09_21`. The measured `DEFAULT_SEARCH_POLICY` (purpose match
mode; measured on 354 queries over 123 items, with a held-back split and a
removed-guard control in `tools/test_search_quality.py`) has no caller. The
capabilities record reports the backend names as fixed strings
(`sqlite_fts5`, `deterministic_character_hash`). The index is rebuilt on every
request. There is no relevance floor, so a query with no good match returns
the best poor items as if they matched.

### 14.2 Target

```text
Hosted search at scope hosted_catalogue_metadata
├── Edge: service_retrieval_request/v2 -> service_retrieval_result/v2
│   └── v2 adds the explicit "no good match" signal (S-6.32); this is a functional
│       change made once through the edge-change procedure, not an engine change
├── Engines, chosen at host start from the host file
│   ├── catalogue_search_policy: served_before_2026_09_21 (initial today),
│   │   purpose_match_default (becomes initial after the held-out comparison);
│   │   policy v2 carries the relevance floor as an installation setting
│   ├── retrieval_lexical_stage: fts5 (initial); bm25s with a memory-mapped index
│   │   prebuilt at release (planned)
│   └── retrieval_vector_stage: hash (initial); model2vec potion-base-8M vendored into
│       the image and loaded offline with a pinned commit revision (planned: the second
│       vector engine S-6.32 asks for)
├── Index: built once per host start (or at release beside the manifest, keyed by the
│   manifest digest and the embedding space), filtered by the caller's authorization at
│   query time; bodies never enter the index
├── Capabilities: the retrieval section keeps its keys (modes, lexical_backend,
│   vector_backend, semantic_embedding_model_installed, scope, returns_bodies), whose
│   values now come from the bound engines, so service_capabilities/v1 does not change
│   and service.js, the website checks and tools/install_selected_material.py keep
│   working; handshake digests go to the administrators' engine_bindings_report/v1
└── Qualification: the existing retrieval tournament over the frozen judged queries,
    extended to vector and hybrid stages, with a significance test (ranx, in a
    development extra, never in the serving image)
```

A query with no good match says so instead of returning the best poor items;
switching policies must not change results for the fixed evaluation set
without a recorded comparison (both are the step's adversarial cases).
Reranking stays a documented engine kind with no installed engine until the
evaluation shows a gap on the held-back queries.

The result version change reaches every consumer in the same commit, as the
pre-launch version policy requires: the transport and its checks,
`core/provisioning_mcp_checks.py`, `tools/install_selected_material.py` and
`tools/check_client_journey_in_containers.py` (both pin
`service_retrieval_result/v1` as a constant),
`tools/test_check_client_journey_in_containers.py`, and the documents
`docs/components/service-runtime/README.md`,
`docs/guides/service-searching-and-retrieving.md` and
`docs/guides/client-journey-container-test.md`.

## 15. The service slots and the host loader

### 15.1 The host loader becomes a table

`load_host_application` in `core/service_runtime/http_entrypoint.py` stays the
one wiring point, but stops naming concrete classes. A dispatcher,
`core/service_runtime/service_engines.py`, reads each service slot's
configuration and constructs its engine through that slot's own factory module
(`service_engine_identity.py`, `service_engine_account_email.py`,
`service_engine_billing.py`, `service_engine_record_store.py`,
`service_engine_search.py`, `service_engine_request_limits.py`,
`service_engine_observability.py`, `service_engine_secrets.py`), each keyed by
engine kind and provider profile, the table design of a dependency injection
"selector" without the dependency. An unknown profile refuses before any
effect. The first version of every table is behaviour-preserving: it builds
exactly today's single engine. The report `engine_bindings_report/v1` names
what was bound.

Where each slot's configuration comes from, one source per slot:

| Service slot | Declaration today, projected without a second copy |
|---|---|
| `browser_identity_provider` | `browser_identity.provider_profile` (`supabase_user/v1`) |
| `account_email_delivery` | The provider pair of the `account_email` block |
| `payment_provider` | The `billing` block (Stripe) |
| `request_limit_state`, `failure_journal`, `secret_resolver` | The `http.request_limits` block, the `observability` block once restored, the `env:` reference scheme |
| `record_store` (service scope) | Declared in the new `engines` block; today only `runtime.database_path` exists and SQLite is a default in code |
| hosted search | Declared in the new `engines` block; today nothing, defaults in code |

A slot declared both by projection and in the `engines` block is refused
(`a_slot_is_declared_by_one_source_only`).

The record store default moves into `service_engine_record_store.py`, and
`ServiceCatalogBinding` resolves its default through that factory instead of
naming `SQLiteRecordStore`. `ServiceRuntime(config)` in `runtime.py`, the
failure journal in `observability.py` (which builds its own binding) and the
checks and tools that construct `ServiceRuntime(config)` without a storage
argument therefore keep working unchanged.

### 15.2 Per-slot notes

- **Identity.** One profile today (`supabase_user/v1`). A second profile is a
  new factory row and a new adapter implementing the same surface, mapping
  subjects through durable bindings, never through token claims.
  Self-registration is still open at the provider and blocked only by the
  service (finding F7 notes the capabilities record understates this).
- **Account email.** The service-sent pair is on `main`, not deployed, and no
  mail credential is staged. The unconfirmed-address case must be observed
  before sign-up opens. Its ceiling is `before_dispatch_only`: a send that
  timed out is reconciled, never repeated through another engine.
- **Billing.** Today the loader builds three Stripe objects by name. The
  engine becomes one `stripe` engine behind one surface, `billing_provider/v1`,
  which names exactly the methods the transport already calls (`handle` on the
  event processor; `options`, `create` and `configure_policy` on the session
  adapter), composing the three objects unchanged, so `http.py` does not
  change. New method names would force a transport edit, which is the
  neighbour change this design exists to avoid. Live and test mode are settings of that one engine,
  and the accident control that refuses a test key where the live account is
  configured stays. Honest gap: the entitlement source value
  `stripe_snapshot`, the `service_stripe_event/v1` record and the webhook
  route are provider-shaped, so a second payment provider is an edge change
  (section 11.7), not an engine swap.
- **Record store.** SQLite on one volume is one writer on one Machine. A copied
  volume on a second Machine would be a second, diverging authority, which is
  why the ceiling is `none` and why PostgreSQL comes before a second Machine.
- **Protocol endpoint.** One exact version today, and the host cannot select
  another. The research of September 22 found version `2026-07-28` is current
  and that serving both versions by explicit negotiation, answering the
  discovery call and refusing any other version with the supported list,
  satisfies both owner rules ("negotiate the mutually supported protocol" and
  "no silent downgrade"). That is a second engine of a `set_of` slot, landed
  in its own change with the 2.x software kit.
- **Failure journal.** The module and its 34 checks exist on `main` but the
  wiring was lost in merge `8892677` (finding F1); the consolidation of
  September 22 restores it. The release gate expects `service_health/v2`
  while the route serves `service_health/v1`.

### 15.3 Rollback compatibility

The new `engines` block of the host file and the new `engines` section of the
settings file are refused by older releases, because both loaders refuse
unknown top-level keys. That is correct: an older release must not honour a
configuration it does not understand. The rollback runbook therefore restores
the dated host file backup together with the previous image digest, exactly
as for `request_limits` today, and a rollback drill (the pattern of
`rollback-key-version-1.json`) proves it before the first release that uses
the block.

## 16. The configuration dimensions, mapped

The owner's requirement: every discrete cognitive or act step Loop node (its
complete explanation is in section 13.1) "needs an explicit initial
configuration and ordered fallback priorities across all applicable
configuration dimensions". Each baseline dimension below either becomes a
field of the slot policy that owns it, or stays a field of the Loop
definition, which this design does not rank. The list is a required baseline,
not a maximum.

| Dimension | Owner under this design | Initial choice lives in | Fallbacks live in | Ranked by evidence |
|---|---|---|---|---|
| Harness implementation and process initialization | `step_executor` (recipe), `process_confinement`, placement setting | `initial[0]` of the slot policy | `initial[1:]` and `fallbacks`, `fallback_on` | Yes, per exact scope |
| Harness wrapper composition (proposed dimension) | Executor installation setting | The layering `initial` | Layering `fallbacks` | Only after a composition executor exists |
| Native control ownership (proposed dimension) | Executor installation setting | `control_policy` | Composition fallbacks | No |
| Role profile | Loop definition (fixed frame) | The definition | A new governed definition | No |
| Step profile | Loop definition (fixed frame) | The definition | Declared repair procedures | No |
| Model | `model_access` (route) | The tier's first route | The tier's ordered routes | Yes, inside the authorized model identities |
| Provider and route | `model_access` | The route plan | Same-provider routes; cross-provider only with failover authority | Yes, same limits |
| Tools | `tool_protocol_transport`, `custom_plugins_port`, the request's tool references | The declared tool set | Declared alternatives for the same typed capability | Only between declared equivalents |
| Skills | Skill admission and references (content) | Admitted skills | Declared alternatives or an explicit "no skill" | No |
| Context Markdown files | Step request context references (content) | The request | Declared supported files | No |
| Harness-native instruction files | `harness_instruction_files` | The style of the chosen executor engine | Declared supported files | No |
| Prompt construction | Prompt templates (profiles) | The template version | Permitted templates | Not in this design |
| Plugins | `custom_plugins_port` | The registered set | Compatible alternatives | No |
| Hooks | Lifecycle extensions (checks parked) | A future slot, only after their checks are collected again; until then no hook is bound, recorded as an explicit no-hook choice | A permitted no-hook path; a mandatory approval or verification hook is never bypassed | No |
| Input and output contracts | The edge contracts and `LoopContract` (fixed frame) | The contract version | Explicit adapter Loops | No |
| Supervisors and independent verifiers | `response_evaluator` | The evaluation contract | Qualified alternates; never self-approval | No |
| Thinking power | The scope key of `model_access` | The route attempt setting | Ordered supported settings | Jointly with the route |
| Model-call strategy | `model_call_strategy` (roadmap S-6.60), with the gateway's failover and escalation flags in `model_access` | The pass-through strategy and the declared flags | Declared strategies within the step's call allowance | Yes, per exact scope, once strategies have reviewed evidence |
| Model generation settings | `model_access` installation settings | Request settings | Supported changes | No |
| Model output allocation | `ModelOutputAllocation`, bound to the selected route | Source-backed allocation | Authorized alternatives | No |
| Loop usage and orchestration | The Loop runtime, placement setting | The definition | Declared decomposition changes | No |
| Run mode | `LoopModePolicy`; executor engines declare supported modes | Preferred modes | The mode waterfall | No |
| Intelligence and Runtime Memory | Retrieval slots, `record_store`, `runtime_memory`, family policy | The search policy and family policy | Declared sources | Search engines only |
| Workspace and execution environment | `workspace_backend`, `process_confinement` | The isolation requirement and declared engine | Same or stronger isolation only | Yes, among equal or stronger isolation |
| Budgets, permissions and effect policy | The Loop's grant; eligibility inputs only | The grant | Narrower allocations | Never |
| Loop, exit and publication conditions | The Loop runtime; candidates in the step result | The definition | Declared recovery paths | No |
| Objective and risk (proposed dimension) | `engine_evidence_rule/v1` | `method` and `objective` | Objectives the host permits in overrides | This is the ranking objective |
| Observability and attribution (proposed dimension) | Section 9 measurement | Measurement fields | None; a missing record refuses a success claim | No |

## 17. Named checks

Every new check names its known-wrong case: the input that must be refused, so
that removing the guard makes the check fail. A check marked "control" also
gets a removed-guard mutant: the guard is removed inside the test, the
known-wrong case must then be accepted, which proves the check detects the
removal (the repository's `removed_*_is_detected` pattern). Every check lives
in a suite the `main` self-test collects; a check that exists only in a parked
suite does not count.

### 17.1 The slot index and the edges

| Check | Known-wrong case |
|---|---|
| `every_engine_slot_names_registered_work_boundaries_or_a_release_reason` (control `removed_slot_boundary_join_is_detected`) | A slot naming a misspelled boundary; an active or candidate run-time slot naming none; a planned slot without an envelope not reported as `planned_without_envelope` |
| `every_engine_slot_edge_is_read_from_its_interaction_rows` | A slot record that carries its own copy of a request or result version, which could then disagree with its interaction row |
| `every_interaction_names_exact_versioned_contracts_and_known_components` | A request contract without `/vN`; a component kind outside the ontology |
| `engine_slot_symbols_resolve_without_import` | `core.external_harness.NoSuchProtocol` |
| `every_active_engine_slot_conformance_suite_is_collected` (control `removed_collected_suite_requirement_is_detected`) | An active slot whose suite is listed in `suite_collection_exceptions`: today's text-search test resolution would pass it |
| `every_edge_contract_declares_an_unavailable_result` | Neighbours receive an exception when every engine is switched off |
| `every_slot_policy_states_an_initial_choice_and_ordered_fallbacks_or_an_explicit_no_fallback` (control `removed_no_fallback_rule_is_detected`) | Empty `fallbacks` with `no_fallback` false |
| `a_changed_engine_does_not_change_the_edge_record` (control `removed_edge_shape_check_is_detected`) | A fixture engine returns an extra field, a missing key or another record version |
| `every_engine_module_holds_one_engine_in_its_component_folder` | A factory table module that defines an engine class; an engine module outside the folder its slot names (section 7.8) |
| `a_nested_selection_names_its_parent_decision_and_never_widens_it` | A model route chosen inside a step attempt whose decision names no parent decision; a nested engine given a binding or grant its parent does not hold (section 4.6) |
| `engine_selection_needs_no_selection_to_start` | A policy whose ranking engine is itself chosen by a nested selection (section 8.2, base case) |

### 17.2 Registration and structure

| Check | Known-wrong case |
|---|---|
| `descriptors_are_projections_of_native_declarations` | A hand-made descriptor whose native digest differs from the registry's declaration |
| `descriptor_digest_moves_when_the_native_declaration_moves` | Isolation changed from `os_sandbox` to `none` without a descriptor change |
| `registration_refuses_an_unknown_or_missing_adapter_contract_version` | An adapter whose `info()` omits `adapter_contract_version` registers |
| `one_engine_identifier_names_one_implementation` | The parked `OpenCodeProcessAdapter` and the `opencode` recipe engine both answering to `opencode`; a registration that replaces an engine (`replace=True`) while its descriptor digest stays the same. A second registration of one identifier without `replace=True` is already refused today |
| `importing_an_engine_module_registers_nothing` | A module-level `registry.register(...)` |
| `an_installed_entry_point_is_listed_but_not_registered` and `listing_entry_points_imports_nothing` | An entry point loaded, or its module present in `sys.modules`, after listing |
| `a_version_mismatch_between_host_file_and_distribution_refuses_load` | A host naming version 1.2 while 1.3 is installed |
| `engine_classes_are_named_only_at_their_registration_sites` (ratchet with a shrinking baseline per slot) | A new `SQLiteRecordStore(` in a service module. The baseline is whatever the scanner finds on `main` when it lands, never a hand-written list; source search already finds six sites: `storage.py`, `http_entrypoint.py`, `http.py` (`_search` and `capabilities`), `retrieval.py` constructor strings, `overnight_cli.py`, and `record_cli.py`, where the managed record command constructs `SQLiteRecordStore` or `PackageJsonlStore` from a backend string |
| `engine_module_imports_only_its_slot_contract_and_its_own_dependencies` | A recipe module importing `core.model_gateway` |
| `engine_checks_resolve_to_collected_suites_before_qualification` | An engine whose named check lives only in a parked suite made active |
| `factory_table_refuses_an_unknown_engine_kind` | A host installation with `kind: shell_script` |
| `adding_an_engine_by_registration_changes_no_call_site` | A fixture engine unknown at import time must be registered, qualified, listed and served through the unchanged call site; the check fails if any call site had to name it (roadmap D-19-T01) |

### 17.3 Selection

| Check | Known-wrong case |
|---|---|
| `selection_never_considers_an_engine_outside_the_installed_enabled_universe` | A disabled engine chosen because it is first in the declared order; `AdapterRegistry.select` falling through to an adapter the host never declared |
| `a_narrower_source_can_reorder_but_never_widen` | A run override naming an engine the host did not install |
| `a_slot_is_declared_by_one_source_only` | Settings carrying both `engines.model_access` and `models.tiers` |
| `eligibility_precedes_ranking_and_ranking_cannot_restore_an_ineligible_engine` | Evidence ranking an ineligible engine first (generalizes `preference_cannot_restore_a_hard_rejected_harness`) |
| `undeclared_engine_kind_is_ineligible` | A `server_database` engine offered to `step_executor` |
| `unsupported_edge_version_is_ineligible_before_dispatch` | An engine speaking only an older edge version; zero adapter calls allowed |
| `unavailable_unqualified_or_expired_engine_is_ineligible_by_default` | Qualification `unknown`, or an expired availability fact, selected |
| `mode_or_configuration_never_grants_engine_permission` (control) | A hybrid-mode profile making a network engine eligible without a network grant; an installation whose settings declare `allow_network: true` making a network engine eligible when the host's grant does not; the decision must say `execution_authority_granted: false` |
| `a_harness_preference_is_applied_only_within_its_authority` (control `removed_harness_preference_bound_is_detected`) | A step result preference that pins an engine where the host permits harness sources only to prefer; a preference that outranks a run override; prose in a harness's output treated as a preference |
| `missing_preemptive_limit_is_ineligible_under_a_preemptive_budget` | An engine without `total_tokens` enforcement chosen when the budget requires prevention |
| `unknown_cost_under_a_bounded_spending_budget_is_ineligible` | An engine with no price source chosen under a spending ceiling |
| `selection_performs_no_probe_no_network_and_no_model_call` | A projection that calls `live_models()` or opens a socket (fixture engines raise if touched) |
| `ranking_policy_must_end_with_the_declared_order` | `engine_order: [evidence-ranker]` alone |
| `insufficient_evidence_is_recorded_as_a_fallback_not_an_engine_failure` | A decision attributing insufficient evidence to `engine_failed` |
| `selection_decision_records_every_rejection_reason_and_its_propensity` | A decision listing only the winner |
| `every_selection_is_recorded_in_existing_event_families` | A raw kind missing from `_CANONICAL_EVENT_MAP` |
| `a_decision_exists_before_every_dispatch` (control) | A dispatch whose decision digest matches no earlier decision on the chain |
| `bound_engine_is_revalidated_at_use` (control) | A harness binary replaced between selection and launch |
| `exact_reuse_needs_every_digest_unchanged_and_no_expired_fact` | A decision reused after an availability fact expired |
| `a_pin_to_an_ineligible_engine_refuses_without_substitution` | The pin fails and another engine runs silently |
| `a_spawned_loop_cannot_widen_its_parents_override_authority` | A Spawned Loop uses `pin` when its spawning Loop may only `prefer` |
| `an_override_cannot_change_the_evaluator_or_start_a_comparison` | An override naming another evaluator identity |

### 17.4 Evidence

| Check | Known-wrong case |
|---|---|
| `below_the_minimum_sample_the_declared_order_stands` (control `removed_minimum_sample_rule_is_detected`) | 9 records against a minimum of 10 reorder the engines |
| `minimum_below_the_slot_floor_is_refused` | A host policy with a minimum of 3 |
| `unmatched_populations_and_evaluators_are_not_pooled` (generalizes the existing harness check) | Trials from two population digests averaged together |
| `evidence_from_another_scope_cannot_rank` (control `removed_scope_match_rule_is_detected`) | Evidence for scope X ranking engines for scope Y |
| `only_comparison_arm_or_frozen_population_attempts_become_ranking_evidence` | Fallback attempts pooled with first-choice attempts |
| `changed_engine_version_invalidates_its_evidence` | A new version inheriting the old version's evidence |
| `rejected_or_self_reviewed_evidence_cannot_rank` | A review whose reviewer is the engine, the producer or the compiler |
| `lower_verified_outcome_never_outranks_on_efficiency` (control) | 0.7 verified at 100 tokens ranked above 0.9 verified at 1,000 tokens |
| `unknown_usage_ranks_after_known_and_is_never_zero` | Missing token counts averaged as zero |
| `a_faster_engine_that_loses_accepted_cases_does_not_move_ahead` (control `removed_loss_margin_rule_is_detected`) | A challenger twice as fast whose loss share exceeds the margin moves first |
| `several_challengers_and_looks_use_the_corrected_confidence` | Ten challengers each tested at the uncorrected confidence |
| `the_comparison_closes_after_the_declared_looks` | An eleventh look with `maximum_looks` 10 |
| `the_incumbent_is_the_declared_first_choice_not_the_last_winner` | A previous winner becomes the baseline for the next comparison |
| `evidence_ranking_never_rewrites_the_host_policy` | A ranking writes a new declared order into the policy |
| `cross_scope_or_learned_ranking_is_refused_below_the_adoption_threshold` | A `routing_model` proposal with 50,000 recorded runs adopted |
| `the_general_rule_and_select_harness_agree_on_the_same_evidence` | The lifted rule and `select_harness` ordering the same evidence differently |
| `standard_library_statistics_match_scipy_when_available` | A binomial tail or bound that differs from `scipy.stats.binomtest` |
| `evidence_bound_to_a_broken_chain_is_refused` | One edited event inside a history the compiler reads |
| `synthetic_records_never_become_evidence` | A record carrying the synthetic marker compiled |

### 17.5 Measurement

| Check | Known-wrong case |
|---|---|
| `every_engine_attempt_writes_one_cost_record_in_its_envelope` (control `removed_envelope_measurement_is_detected`) | An adapter invoked outside its envelope: zero records |
| `engine_reported_time_never_replaces_the_envelope_clock` | Adapter reports 0.001 seconds while the envelope measured two seconds |
| `an_attempt_always_carries_its_envelope_measured_time` | A `GatewayAttempt` constructed without a time (today's default of 0.0) |
| `a_gateway_cost_record_names_the_route_that_ran` | `implementation_id="model_gateway"` |
| `a_decision_cost_record_names_its_engine_and_route` | The typed decision path in `core/decisions/gateway.py` writing `implementation_id="model_gateway"` |
| `the_cost_ledger_is_never_a_selection_input` | A selection path that reads `OperationCostLedger.compare`, or a comparison that counts a producer-written acceptance |
| `a_producer_cannot_write_an_accepted_outcome` | The capturing envelope writes `verified` |
| `a_refusal_before_dispatch_is_not_counted_against_the_engine` and `an_engine_refusal_counts_as_not_accepted` | A capability refusal lowering an engine's accepted rate; a provider refusal excluded so the engine looks better |
| `measurement_records_hold_no_secret_or_content` | A cost record carrying prompt text or a credential shape |
| `an_exported_attempt_span_has_its_measured_duration` | A span exported with equal start and end times |

### 17.6 Fallback, comparison and lifecycle

| Check | Known-wrong case |
|---|---|
| `fallback_only_on_declared_failure_kinds` | A semantic rejection switching engines when `fallback_on` lacks it |
| `fallback_carries_consumed_authority` (generalizes `fallback_never_resets_call_allowance`) | The second engine receiving a fresh call allowance |
| `uncertain_effect_or_accounting_blocks_fallback` | A fallback after a timed-out send or after tool events |
| `host_policy_cannot_widen_the_slot_fallback_ceiling` (control) | A fallback declared for `payment_provider` |
| `model_slot_fallback_requires_failover_permission` | Declared model fallbacks used when `allow_failover` is false |
| `an_open_breaker_is_an_expiring_availability_fact_not_a_hidden_retry` | A breaker that retries inside the call |
| `comparison_spending_never_draws_on_the_step_allowance` (control) | The comparison's model calls reduce the primary's remaining calls |
| `a_comparison_needs_a_separately_approved_authority_grant` | A comparison policy whose allowance is an amount the selection policy declares, with no reference to an approved grant; a grant for another comparison reused |
| `a_comparison_output_is_never_served_metered_or_remembered` (control) | The comparison result reaches the consumer, a meter or Runtime Memory |
| `a_comparison_arm_with_an_external_effect_is_refused_before_dispatch` | An email-sending engine sampled |
| `comparison_sampling_is_deterministic_and_reproducible` | Replaying a run samples different attempts |
| `a_comparison_arm_is_cancelled_with_its_owning_loop` | The owner is cancelled and the arm keeps running |
| `retired_engine_is_never_selected_even_when_listed` (control) | A retired engine listed first by a narrower source |
| `candidate_engine_is_refused_outside_a_declared_trial` | A candidate chosen as the initial choice |
| `deprecated_engine_cannot_be_the_initial_choice` | A deprecated engine as `initial` |
| `archived_engine_refuses_with_its_replacement` | An archived engine silently disabled instead of refused |
| `qualification_binds_the_installation_digest` | A qualification for one model reused for another |
| `expired_qualification_becomes_unknown_and_ineligible` | An expired qualification still counted |
| `qualification_grants_no_authority` | A qualified engine run without model-call authority |
| `restore_takes_exact_paths_and_never_merges_the_checkpoint_branch` | The restore plan accepting a branch or merge argument |
| `older_release_refuses_a_settings_or_host_file_with_an_engines_section` (operational drill) | The deployed image started with the new block |
| `generated_engine_pages_are_current` | A page that no longer matches the catalogue |

### 17.7 Step executor and service slots

The phase 2 checks are in section 13.13. The remaining slot checks:

| Check | Known-wrong case |
|---|---|
| `adding_a_process_harness_recipe_needs_no_core_dispatch_edit` | A recipe style spelled as a literal in `harness_process.py` or `harness_process_relay.py`, including the relay's wire choice (`gemini_cli`, `nanocode`, `codex` and `openinterpreter_rust` select a wire there today) |
| `unsupported_style_is_refused_with_its_named_reason` | The `freebuff` host file binds and runs |
| `recipe_module_mount_and_digest_follow_the_selected_recipe_and_its_wire_codec` | Every recipe module mounted, so an unselected one is importable in the sandbox; the codec module of the recipe's declared wire missing, so the relay cannot decode it |
| `a_harness_without_a_proven_fresh_instance_is_ineligible_for_one_harness_per_step` | A harness whose instance reads a user-level configuration file or a previous step's session selected for a step that requires one harness per step (roadmap S-6.42) |
| `the_billing_surface_names_the_methods_the_transport_already_calls` | A billing engine surface that renames `handle`, `options`, `create` or `configure_policy`, so `http.py` has to change |
| `engine_preferences_in_a_result_are_data_until_admitted` | A preference in a step result that changes the next attempt's engine without passing the owning Loop's admission |
| `a_session_process_never_outlives_its_step_attempt` | The same harness session process answering a second step |
| `hosted_capabilities_keep_their_retrieval_keys` | A capabilities record whose retrieval section gains or loses a key |
| `the_store_default_resolves_through_its_factory` | `core/service_runtime/storage.py` still naming `SQLiteRecordStore` after the record store slot lands |
| `installation_settings_carry_no_authority` | An installation whose settings declare `allow_network`, a spending ceiling or a model identity grant |
| `agent_protocol_permission_requests_are_answered_only_within_the_step_grants` | A write outside the work folder approved |
| `agent_protocol_stop_reasons_map_to_typed_statuses_and_cancel_is_not_an_error` | `cancelled` reported as `failed` |
| `the_agent_protocol_engine_reaches_models_only_through_the_broker` | An agent configured with a provider address outside the relay |
| `a_semantic_step_without_a_bound_step_executor_is_refused` | The delegate handler invoked for a `non_deterministic` step with no `step_executor` binding, or executor modes copied from allowed modes instead of the bound engine |
| `no_caller_reaches_a_provider_except_through_model_access` (ratchet) | The overnight runner's direct call |
| `a_host_block_selects_its_engine_by_provider_profile_without_a_loader_edit` | Adding a fixture identity profile requires editing `load_host_application` |
| `an_unknown_provider_profile_stops_the_host_before_it_serves` | An unknown profile falls back to the default engine |
| `the_loader_output_names_the_engine_bound_at_every_service_slot_and_the_family_reason` | `configure_host` output without the bindings or the family-policy reason |
| `hosted_capabilities_name_the_bound_retrieval_engines` | Fixed backend strings while another engine is bound |
| `served_search_uses_the_engine_and_policy_the_host_declared` (control `removed_search_binding_is_detected`) | Today's `Retriever(records)` defaults ignoring a declared policy |
| `a_query_with_no_good_match_says_so` | The best poor items returned as if they matched |
| `switching_search_policy_changes_no_fixed_evaluation_result_without_a_recorded_comparison` | A policy switch with no comparison record |
| `a_store_without_the_atomic_batch_cannot_serve_service_writes` (roadmap D-05-T01) | `local.duckdb` declared for the service |
| `a_store_fallback_is_refused_by_the_slot_ceiling` | A second store listed as a write fallback |
| `instruction_style_follows_the_bound_step_engine` | A CLAUDE.md composed for a codex engine |
| `every_store_engine_passes_the_golden_conformance_suite` | An engine that drops the read-set guard |
| `an_uncertain_send_blocks_every_fallback` | A second email after a timeout |
| `removed_browser_identity_protocol_check_is_detected` | A `browser_identity/v2` adapter installed once the comparison is patched out |
| `removed_webhook_signature_check_is_detected` | An unsigned subscription event accepted once the check is patched out |
| `a_billing_provider_is_never_switched_during_a_request` | A fallback after a provider outage creating a second customer |
| `live_account_engine_refuses_a_test_key` | A test key staged where the live account is configured |
| `a_second_protocol_version_is_selected_only_by_exact_negotiation` | A request served under the older version when both sides support the newer |
| `a_secret_resolver_has_no_fallback` | A missing environment reference answered from another source |

### 17.8 The remaining slot checks

Tables 5.2 to 5.4 name these checks for slots whose adoption packages come
later. Each is written first, with its known-wrong case, by the package that
adopts its slot; until then the slot stays `planned` or `candidate` in the
catalogue.

| Check | Known-wrong case |
|---|---|
| `an_instruction_file_is_not_counted_as_loaded_without_an_observation` | File presence counted as loading while `instruction_loading_observed: false` |
| `harness_process_refuses_without_an_available_confinement_engine` | A process started unconfined because `bwrap` is missing |
| `equal_dimensions_do_not_establish_embedding_compatibility` | Two embedding spaces with equal dimensions and different models compared (roadmap D-12-T01's negative control) |
| `untrusted_code_is_never_placed_in_the_restricted_local_backend` | An untrusted command selecting `restricted_local` |
| `workspace_engine_availability_is_not_runtime_verification` | Docker qualified because the binary is on the path |
| `an_unqualified_decision_endpoint_is_not_selected_by_default` | Jev chosen while `allow_unqualified` is false and its qualification is unknown |
| `decision_confidence_is_not_an_accepted_outcome` | A reported confidence of 0.95 counted as accepted |
| `an_engine_cannot_evaluate_its_own_output` | An evaluator whose digest equals the producing engine's |
| `a_rerank_stage_cannot_add_candidates_the_earlier_stages_did_not_return` | A reranker that returns an item absent from the fused candidate list |
| `similarity_hits_never_become_engine_selection_evidence` | A similar run used to reorder engines |
| `runtime_memory_is_not_visible_to_another_run` | A note written in one run returned by a search in another run |
| `a_tool_call_is_never_retried_on_another_transport` | A timed-out call repeated through a second transport |
| `the_web_research_port_reports_unavailable_on_main` | Research recorded as done with no live engine |
| `public_capability_groups_map_to_collected_boundaries` | Web Research mapped to a parked envelope |
| `enable_and_disable_change_only_the_installation_flag` | A disable command that also edits the selection policy or another installation |
| `exported_spans_carry_no_prompt_or_secret` | A span attribute holding prompt text or an authorization header value |
| `an_item_without_an_accepted_licence_is_never_imported_verbatim` | A body under a licence the host's licence policy does not accept copied into a candidate |
| `an_ingested_item_stays_a_candidate_until_independent_review` | A source reader that marks its own item approved |
| `a_duplicate_item_is_merged_not_added` | One body digest added twice under two identifiers |
| `every_ingested_item_carries_its_source_provenance` | A candidate without its origin, immutable revision, path, source digest, licence evidence or fetch date (roadmap S-6.40) |
| `a_strategy_that_needs_more_calls_than_the_step_allows_is_refused_before_the_first_call` | A three-model vote started under an allowance of two calls (roadmap S-6.60) |
| `agreement_among_models_is_evidence_never_acceptance` | A unanimous vote recorded as an accepted result |
| `a_mode_the_host_did_not_enable_cannot_authenticate` | An external token accepted while `external_jwt` is absent from the host's modes |
| `a_meter_event_is_sent_once_per_usage_record` | A retry after a lost acknowledgment sends a second meter event for one usage record |
| `body_store_engine_switch_serves_identical_digests` | An object store returning re-encoded bytes |
| `host_attestation_is_never_reported_as_independent_qualification` | A provisioning or capabilities record that reports the basis `host_attested` as independent qualification |
| `multi_machine_service_refuses_an_in_process_limit_engine` | A host declaring more than one Machine starts with the in-process limiter tables |
| `the_health_route_serves_the_version_the_release_gate_expects` | The route serves `service_health/v1` while the gate requires `v2` |
| `no_secret_resolver_writes_a_value_to_a_record_event_or_measurement` | A resolved value, or a string with the shape of a staged key, found in a record, a ledger event or a cost record |
| `every_served_hostname_has_a_saved_evidence_record` | The four subdomains added on September 21, which have no evidence record |
| `a_release_record_names_every_bound_engine_and_its_digest` | A release record without the engines map, or naming an engine without its descriptor digest, accepted by the release check |
| `adding_a_client_is_one_recipe_row_and_no_page_code_change` | A new client recipe that needs an edit to `service.js` or `index.html` |
| `offered_fetched_installed_and_used_are_recorded_as_separate_facts` | An installation reported as use |

## 18. Current state versus target state

### 18.1 The honest one-line story

The wrapping is real: a sealed runtime, typed ports, versioned records, small
protocols with declared capabilities compared before use, explicit
registries, and revalidation at use all exist in source. Most engines can
already be swapped by configuration on the engine side (model routes, the
retrieval backends, harness process choice and fallback order, typed decision
engines, the family policy). What does not exist is the common layer over
them: no slot index, no common descriptor, no common selection record, no
envelope-owned measurement, no evidence ranking outside harnesses, and above
all no typed step executor seam, which is the piece the harness-first plan
needs most. The service side has one implementation per boundary, chosen by
class name in the loader.

### 18.2 Slot by slot

| Engine slot | Engines working today | How the engine is chosen today | Target |
|---|---|---|---|
| `step_executor` | No typed seam; the harness chain exists but its only production caller is parked; the hosted service executes no steps; the one live step path is the overnight runner's direct model call | The caller passes a function in code | Slot selection with the delegation rule; text relay for text-only steps, then OpenCode through the Agent Client Protocol |
| `model_access` | Gateway live; one authorized cloud route, quota-limited on September 18; other clients' suites parked | Settings `models.tiers`; failover off by default | Projected slot configuration; per-route descriptors; the gateway names the route in its records |
| `typed_decision` | jev, circuit, system_one, live but unqualified | `decision_host_configuration/v2` | Projected; qualification required by default |
| Retrieval stages and search policy | fts5 plus hash deployed; store, lancedb, model2vec optional; the measured policy unused | Settings `search:` on the engine side; hard-coded defaults on the hosted route | Host-declared; measured policy; relevance floor; second lexical and vector engines |
| `record_store` | local.sqlite deployed; four more adapters | `AdapterRegistry.select(preferred=...)`; the service default is in code | Host-declared with atomic batch eligibility; PostgreSQL later |
| `workspace_backend` | restricted_local; Docker (binary check only); two declarations | `WorkspaceSpec.backend_kind`; the only choosing site is parked | Selected by required isolation |
| `process_confinement` | Bubblewrap, Linux only, no network | Fixed in code | Its own slot; egress allowlist; containers |
| Service identity, email, billing | One engine each (email on `main` only) | The loader names each class | Factory rows keyed by profile; one billing surface |
| `protocol_endpoint` | Version `2025-11-25` | Fixed; the host cannot select | Two versions by explicit negotiation |
| `failure_journal` | Module present, not wired (F1) | None | Wired, then sinks |
| Release-time slots | Fly, Cloudflare, the guarded workflow | The release | The release record names every engine and digest |

### 18.3 What the design reuses, observed in source

| Mechanism | Where | State |
|---|---|---|
| Selection by declared, qualified binding with ordered fallback, cycle refusal and a decision record | `core/configuration_preferences.py` (`PreferenceEngineBinding`, `MetaPreferencePolicy`, `resolve_preference`, `configuration_preference_decision/v1`) | exists |
| Ranking over matched, independently reviewed trials with a minimum count of distinct Run History references | `core/harness_selection.py`, `core/harness_selection_records.py` | exists, harnesses only |
| Ordered fallback on typed failure kinds, never resetting allowance | `core/harness_fallback.py` | exists |
| A bounded factory table with refusals | `core/decisions/configuration.py` (`ADAPTER_FACTORIES`) | exists |
| Store capability negotiation and the atomic batch contract | `catalog/handshake.py`, `catalog/protocol.py` | exists |
| Sourced facts with a state and an expiry | `core/configuration_capabilities.py` (`ConfigurationFact`) | exists |
| Edge records with delivery, retry, cancellation, authority and failure fields | `data/component_interactions.yaml` | exists (seven rows, parked chain only) |
| The index of operational boundaries | `core/boundary_registry.py` (87 rows) | exists; 31 rows have a collected test |
| Parameter precedence with a trace | `core/parameter_resolution.py` (`SOURCE_PRECEDENCE`) | exists |
| Per-implementation cost records with phases and unknowns | `core/operation_cost_records.py` | exists, in memory, optional |
| The one-million-run adoption policy | `core/heuristic_adoption.py` | parked |
| The capability handshake of retrieval bindings | `core/capability_directory.py` (`CapabilityHandshake`) | exists, suite parked |
| The registry of component folders | `data/component_folder_map.yaml` (`component_folder_map/v1`), loaded through `load_component_resource` | exists |
| One folder per component with one module per engine | `core/decisions/` (typed decisions), `catalog/stores/` (record stores) | exists |
| Qualification records for harness projects | `embodiments/*/qualification.json` (`harness_project_qualification/v1`, five files, no Python reader yet) | exists as data |

### 18.4 What is missing or weaker than it looks

1. **No typed step executor seam.** The step executor is a bare callable; the
   planned executor interface of phase 2 does not exist; "installed executor"
   is a mode name.
2. **A harness today realizes one model response, not one step.** Every recipe
   is a restricted text-response profile, so no step that needs tools or file
   effects can be delegated yet.
3. **Parked retires suites, not dependencies.** At least 48 parked modules are
   imported at module load by the 133 collected suites. Live slots depend on
   parked code: `CapabilityHandshake` (`capability_directory`), the output
   store every harness run requires (`context_artifacts`), the outcome vector,
   model output capacity records, contract match modes, effect approval, the
   profile ontology, the heuristic adoption gate.
4. **Guards that exist only as text.** The boundary registry resolves test
   names by text search, so 56 of its 87 rows name a test that the `main`
   self-test does not run (36 envelopes in parked modules, 20 tests in parked
   suites).
5. **Measurement cannot yet be trusted.** The four defects of section 9.3.
6. **Evidence is scarce.** Four offline text-profile qualifications exist, and
   Codex's has zero real model calls. The declared order will decide for a
   long time.
7. **Engine names inside edges.** The `stripe_*` records and the
   `stripe_snapshot` source, `supabase_user/v1` inside the identity
   configuration, and the protocol server name `loop-engine-intelligence` put
   engine identity into edges; swapping those engines still touches
   neighbours until neutral records exist.
8. **Unversioned edges.** Workspace requests, tool calls and Runtime Memory
   notes have typed classes but no record types.
9. **Claude Code is not an execution harness today.** It is an
   instruction-file style and a customer recipe. The harness-first record's
   phrase "OpenCode, Codex, Claude Code, and others" overstates the executor
   set.
10. **The Open Knowledge Format family cannot be represented**: an item's
    family is derived from its source layer.
11. **No live class name ends in `Node`, but five begin with it.**
    `NodeAssignment` and `NodeProvisioningError` in the live
    `core/node_provisioning.py`, and `NodeGrid`, `NodeParameter` and
    `NodeGridError` in the parked `core/node_grid.py`, have the prefix shape
    the September 22 seam review asks the conformance gate to catch. The rule
    in `AGENTS.md` concerns names that end in `Node`, so this is naming
    hygiene, not a violation; the engine inventory's statement that two live
    names "end in `Node`" was inaccurate.
12. **The deployed pilot is behind `main`.** Pilot release 9 came from an
    unpushed branch with no continuous integration run; the observability
    wiring lost in merge `8892677` and the request-limit mapping the container
    drills lack (findings F1 and F2) block a guarded release from `main` until
    the September 22 consolidation (roadmap S-6.29) lands.

### 18.5 Target state, in one tree

```text
Target
├── Every functional component names its edge, its engines and its selection
│   (data/engine_slots.yaml, joined to the boundary registry and the interaction catalogue)
├── Every engine has a computed descriptor, a lifecycle and an implementation location
├── Every host declares, in one record shape per slot, what is installed and switched on,
│   the initial choice and the ordered fallbacks
├── Every selection is effect-free, recorded before dispatch with every reason and its
│   propensity, and rechecked at use
├── A harness or a Loop sends engine preferences only within its authority, and a nested
│   slot's decision names its parent decision
├── Every functional component has one folder, and every engine one module
├── Every attempt is measured by its envelope into Run History
├── Evidence reorders engines only under the declared rule, above the declared minimum,
│   for the exact scope, never cheaper-but-worse, never rewriting the host's policy
├── Every executable hybrid or model-led step delegates to a harness engine through
│   step_run_request/v1; an in-process engine can never satisfy a delegation claim
├── Adding, swapping or retiring an engine changes one adapter and one declaration and
│   no neighbour (roadmap D-19 acceptance)
└── A static check, generated slot pages and engine cards keep it that way for people
    and for coding harnesses
```

## 19. Risks, decisions and owner-only items

### 19.1 Decisions taken, with reasons

The owner's direction of September 20 is to decide, record the reason and
move on. These are engineering decisions under that direction.

| Decision | Reason |
|---|---|
| The owner's "swap point" is written "engine slot", the roadmap's term, always in full | The roadmap is the work authority; "slot" alone already names prompt slots |
| The slot index is a data catalogue joined by name to the boundary registry, not a new field on 87 rows | One file a coding harness can read; the 966-line registry, already over the size cap with a recorded exception, does not grow; the join is the pattern `BOUNDARY_ONTOLOGY` already uses |
| Engines stay in their existing registries; descriptors are projections | `AGENTS.md` forbids parallel registries and sources of truth |
| Existing declarations are projected, never copied (`models.tiers`, `search:`, `harness.json`, the decision host file, `browser_identity`, `account_email`) | One source per slot; a copy would drift |
| New optional `engines` sections instead of new host file and settings versions | Least rewiring; older releases already refuse unknown keys, which is the rollback behaviour needed |
| The step gets a new edge (`step_run_request/v1`) instead of evolving `harness_request_identity/v3` | Two functions (one model response, one step of work) deserve two edges; the roadmap names "typed step run request and result records"; the model response edge stays untouched |
| The executor profile is the step executor slot's capability record inside its descriptors | The roadmap names "an executor profile record for each engine"; one descriptor type still serves every slot |
| The first delegated engine is OpenCode through the Agent Client Protocol; text relay engines serve text-only steps first | Research of September 22: one protocol reaches about 39 agents, OpenCode is native, MIT, and already has a recipe; the text relay path already has offline qualifications |
| Two evidence methods, both declared: the lifted harness rule and the paired rule | Test two versions instead of guessing; the lifted rule exists and is checked, the paired rule is the one that lets efficiency matter without admitting a worse engine |
| No default minimum sample in code; a per-slot floor of 10 in data | "No heuristics before one million runs" means every number is a declared, reviewable value; ten is the smallest sample where one run cannot move the rate by more than ten points |
| Deterministic governed operations are not delegated | Section 13.12 |
| The overnight direct step stays a visible `direct_model_step` engine that no harness-first profile may select | Build out without letting it satisfy a delegation claim |
| The public capabilities record omits engine identities except the client-relevant search facts | Engine identities are internal; administrators read the bindings report |
| Parked suites of modules that live slots import are collected again, or the needed types move into collected modules | They are live dependencies, not the retired in-process capability; the owner's retirement concerned the in-process execution path |
| The Loop Engine definition keeps the owner's wording; "engine" for a slot implementation is always qualified by its slot or identifier | `AGENTS.md` ("a local engine") and the README of `230c91e` ("the open engine behind Baltor") use the word for Loop Engine; rewriting the owner's text is not an engineering decision (section 2) |
| New components start in their own folder (`core/engines/`, `core/step_execution/`, `core/library_ingestion/`); existing flat families move whole, one family per commit, later | Roadmap S-6.30 and `AGENTS.md` ask for one folder per component and one module per engine; the folder-depth record gives the safe way to move existing code (section 7.8) |
| A harness preference enters only as a typed override at the lowest existing precedence (`intelligence_proposal`) | A harness's output is untrusted data (Constitution LE-TRUST-001); the existing precedence vocabulary needs no new source kind (section 8.4) |
| The billing surface names the methods the transport already calls | A renamed surface would force an edit to `http.py`, the neighbour change this design exists to avoid |
| The record store default resolves through its factory module, not through each caller | `ServiceRuntime(config)` and the failure journal keep working unchanged, and no caller names the concrete store |
| The public capabilities record keeps its retrieval keys; handshake digests go to the bindings report | `service_capabilities/v1` has four outside consumers (`service.js`, two website checks, the material installer); new keys would be an edge change |
| A comparison's allowance cites a separately approved authority grant | A selection policy is configuration, and configuration never grants model-call or spending authority (D-19 authority note) |

### 19.2 Risks

1. **Scope.** About forty slots. Landing them together would break the
   working cycle; the plan lands one slot group at a time, each behind its own
   checks and mutants.
2. **Parked dependencies.** Until plan package F11 lands, some guarantees rest on
   code whose own checks do not run.
3. **Evidence will rarely trigger during the private beta.** That is intended
   and must be explained, or it will be reported as a defect.
4. **Rollback friction.** Every new optional section is refused by older
   releases; the rollback runbook must restore the dated configuration backup
   with the previous image.
5. **The relay and new protocol adapters add dynamic imports and new
   processes.** They stay safe only while recipe catalogues are package data
   and the sandbox mounts only the selected module; a future change that lets
   a host file name a module would break that.
6. **Harness protocols move fast.** The Agent Client Protocol library is at a
   release candidate; Codex regenerates its schema per release. Pinning and
   schema digests per engine version, and qualification that expires, are the
   defence.
7. **Selection overhead on hot paths.** Exact reuse bounds it; it must be
   measured before per-call selection is enabled on hosted search.
8. **Vocabulary.** "Engine" names Loop Engine in the owner's text (`AGENTS.md`
   "a local engine", the README since `230c91e`) and an implementation behind
   a slot in this design. Without the qualification rule and the
   ambiguity-register entry of section 2, editors and harnesses will conflate
   the two; an unqualified "the engine" in a technical document is the
   known-wrong case for the documentation check.
9. **Concurrent work.** The consolidation worktrees of September 22, none of
   them merged into `main` when this revision was checked, edit
   `http.py`, `http_entrypoint.py`, `runtime.py`, `observability.py`,
   `forbidden_paths.json`, `architecture_map.py`, `service.js`,
   `tools/check_client_journey_in_containers.py`,
   `tools/check_fly_service_container.py`, the component guide map, and
   `AGENTS.md`, `ASTRA.md` and `CLAUDE.md`; service-side packages and every
   desk edit of those files wait for them (the plan's gate G0).
10. **Self-referential ranking.** Ranking strategies are a slot; the
    selector-cycle guard stays, and they are never ranked by evidence.

### 19.3 Items only the owner can decide

- Model-call authority for `real_provider` and `end_to_end` proofs, for
  evidence trials of model-backed engines, and for comparisons that call
  models on the operator's account.
- Turning any parked capability back on (web research, an in-process runner
  as a custom Loop harness engine), per the branch strategy.
- Legal commitments: shipping any Anthropic software development kit inside
  the product; accepting a copyleft licence in a shipped extra if the
  engineering reading is not enough (the PostgreSQL driver psycopg is LGPL;
  pg8000, BSD, is the named fallback so this never blocks).
- Destructive provider operations a release-time slot change might need.
- Whether engine evidence measured on Baltor's own populations should later
  be served to customers as intelligence, which needs the evidence rules of
  `docs/guides/launch-benefits-and-evidence.md`.

## Appendix A. How this design was made: the three designs and their scores

Three independent designs were written the same day, each from one angle:
`engine-design-minimal-extension.md` (the smallest extension of what exists),
`engine-design-evidence-selection.md` (runtime efficiency and evidence) and
`engine-design-operator-ergonomics.md` (the person or coding harness who adds,
swaps and switches engines). All three were read in full and scored from 1 to
10 on seven criteria.

| Criterion | Minimal extension | Evidence selection | Operator ergonomics |
|---|---:|---:|---:|
| Fidelity to the owner's direction | 8 | 8.5 | 9.5 |
| Obedience to the repository rules | 9 | 8 | 7.5 |
| How little it rewires call sites | 9 | 7 | 5.5 |
| Evidence discipline in selection | 7 | 10 | 7.5 |
| Completeness across both inventories | 9 | 9.5 | 9 |
| Testability | 9 | 9.5 | 9 |
| Honesty about what exists today | 9 | 9.5 | 8.5 |
| Total (of 70) | 60 | 62 | 56.5 |

Why the scores fell where they did:

- **Minimal extension** has the strongest structure: four records and one
  procedure over the registries that exist, descriptors as projections, one
  declaration source per slot, three selection modes, fallback ceilings, a
  closed failure vocabulary, and raw event kinds projected into existing
  families. It rewires least and breaks no rule. It was weakest on evidence:
  it lifts the harness rule without pairing, leaves the minimum sample
  undeclared (its example is 3), does not find the measurement defects, and
  keeps the step edge shaped as one model response.
- **Evidence selection** scored highest in total. It is the only design that
  makes "the most efficient engine" real without admitting a worse one: the
  envelope measures, the measurement defects are found in source, only paired
  evidence counts, the paired rule with its loss gate and correction, snapshots
  for reproducibility, anchored incumbents, overrides that only narrow, and
  side-by-side comparison starting where it is free. It loses points for a
  heavier concept count, for recording decisions as generic `custom` events
  that lose their family, and for a host file version bump.
- **Operator ergonomics** is closest to the owner's words about turning things
  on and off and keeping it clean for coding harnesses: installations with an
  explicit `enabled` flag, the lifecycle vocabulary reused, factory tables on
  the proven decision pattern, the harness recipe catalogue with exact line
  numbers, one harness as several engines, the declared unavailable result,
  engine cards, the command group, generated pages, and the exact-path restore
  procedure. It rewires most (new versions of the settings file, host file,
  Loop definition, harness request and result, and profile majors) and puts a
  default minimum sample in code.

What this synthesis took: the structure of the minimal extension design; the
measurement, pairing, paired rule, snapshots, anchored incumbent, overrides and
comparison policy of the evidence design; and the installations, lifecycle,
factory tables, recipe catalogue, identity rule for settings, unavailable
result, operator procedures, command group, engine cards and restore procedure
of the operator design. What it did not take, and why: the host file and
settings version bumps (optional sections already make older releases refuse);
moving existing blocks into a new section (projection avoids a second copy);
evolving `harness_request_identity/v3` into a step request (two functions, two
edges); a code default for the minimum sample (a floor in data instead); new
event families or generic `custom` decision events (five raw kinds into
existing families instead); replacing the "assignment harness selection"
boundary row (it stays; a new row is added).

Later the same day the roadmap recorded D-19 and steps S-6.30 to S-6.32, and
four prior-art research notes informed the synthesis: the harness executor
slot (the Agent Client Protocol first with OpenCode; native adapters for
Codex, Claude Code and Pi; sandbox engines; no Temporal, Hatchet or LangGraph),
registries and selection (standard-library entry points for discovery only;
exact sign tests in the standard library; propensity in every decision;
SHA-256 bucketing for comparisons; circuit breakers as expiring availability
facts; the PostgreSQL adapter design), search and standards (bm25s and a
vendored model2vec as second engines; a significance test for adoption; two
protocol versions by negotiation), and the everyday service pieces (a usage
export slot with a "none" engine first).

## Appendix B. Sources read

Inventories of September 22 (session scratchpad): `reports/ARCH_engine_side.md`
and `reports/ARCH_service_side.md`, both read in full, both describing
`97e805f`. The three designs and the four prior-art notes named in Appendix A,
read in full. The owner direction register (`research/OWNER-ARCHITECTURE-INTENT.md`,
sections 2.5, 2.6 and 4).

Decision and design records: `docs/architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md`,
`docs/architecture/BRANCH-STRATEGY-2026-09-21.md`,
`docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md`,
`docs/architecture/ADVERSARIAL-SEAM-AND-NOMENCLATURE-REVIEW-2026-09-22.md`,
`docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md`
(sections "Required choice and fallback record" and "Selection, evaluation,
and safe transitions"), `docs/roadmap/roadmap.yaml` (D-12, D-19, S-6.28 to
S-6.32), `AGENTS.md`, `ASTRA.md`, `CLAUDE.md`, `terminology.yaml`.

Source read at `c96b546` (engine and service source identical to `97e805f`):
`core/configuration_preferences.py` (in full), `core/boundary_registry.py`
(rows, `_mapped_symbol_exists`, `_test_reference_resolves`, `_validate`),
`core/external_harness.py` (registry, protocol, `run_external_harness`),
`core/harness_process.py` (style tuple, mounts, extraction chain, identity),
`core/harness_selection.py` (in full), `core/harness_selection_records.py`,
`core/harness_selection_checks.py` (fixtures), `core/harness_execution_contracts.py`
(vocabularies, `unmet_harness_requirements`), `core/model_gateway.py`
(protocol, specification, attempt timing, cost capture),
`catalog/registry.py` (in full), `core/retrieval_backends.py` (in full),
`core/retrieval.py` (constructor), `core/harness_intelligence_search.py`
(policies), `core/service_runtime/http_entrypoint.py` (`load_host_application`,
`configure_host`), `core/service_runtime/http.py` (`_search`,
`capabilities`), `core/service_runtime/storage.py`, `core/event_vocabulary.py`
(families and map), `core/run_history.py` (event types and ledger mapping),
`core/component_contracts.py`, `data/component_interactions.yaml`,
`data/component_ontology.yaml` (lifecycles), `core/heuristic_adoption.py`,
`core/parameter_resolution.py`, `core/decisions/configuration.py`,
`core/operation_cost_records.py`, `core/configuration_capabilities.py`,
`core/capability_directory.py`, `core/facets.py`, `loop/runtime_context.py`,
`loop/recursive_loop.py` (compatibility constructor), `loop/loop_profile_catalog.py`,
`overnight_cli.py`, `code_nodes/overnight_night.py`, `_self_test.py`,
`_conformance_scan.py` (detectors), `forbidden_paths.json` (suite exceptions,
size cap, parameter cap), `.github/workflows/ci.yml`, `embodiments/*/harness.json`
and the qualification files. Git: the worktrees of the September 22
consolidation (`.le-stabilize/r1-restore`, `.le-consolidation/g1-payments`) and
their changed files.

Read again for the rules check of this revision, at `230c91e`: `AGENTS.md`,
`ASTRA.md`, `docs/architecture/CONSTITUTION.md`, `architecture.yaml`
(`semantic_identity`, `component_architecture`, `external_harness_execution`,
the invariants and `forbidden_class_names`), `terminology.yaml` (the
vocabulary with its retired words, `qualified_terms`, `forbidden_class_names`)
and its installed projection `src/loop_engine/data/terminology.yaml`,
`docs/roadmap/roadmap.yaml` at `7203492`, `4249eca` and `230c91e` (D-19 and
S-6.30 to S-6.42), `data/component_folder_map.yaml`,
`docs/architecture/FOLDER-DEPTH-AND-THE-FLAT-CORE-2026-09-18.md`,
`forbidden_paths.json` (`retired_source_nomenclature`,
`direct_resource_access_baseline`, `resource_surfaces`, size and parameter
caps, suite exceptions), `.github/workflows/ci.yml` (documentation job),
`core/configuration_preferences.py`, `core/configuration_setter_checks.py`,
`core/parameter_resolution.py`, `core/harness_fallback.py`,
`core/harness_selection_records.py`, `core/harness_process_relay.py` (the
request handler's wire choice), `core/harness_lightweight_recipes.py`,
`core/decisions/gateway.py`, `core/facets.py`, `core/model_routes.py`,
`catalog/capabilities.py`, `catalog/stores/sqlite_store.py`, `record_cli.py`,
`core/service_runtime/storage.py`, `runtime.py`, `observability.py`, the
billing and capabilities code of `http.py`, `code_nodes/guided_setup.py`, and
every consumer of `service_retrieval_result/v1` and `service_capabilities/v1`.

## Rules check

Kind: adversarial review of this document, September 22, 2026, against
`AGENTS.md`, `ASTRA.md`, the Constitution, `architecture.yaml`,
`terminology.yaml` and the source at `main` `230c91e`, with the roadmap read
again at `0f1c690`, which landed during the check and changed only the
roadmap and its generated views. The repository was
read, never changed. Every issue below was verified in a file named beside
it, and every correction is already made in the section named. Nothing here
claims that the design is implemented.

### What the check looked for, and what held

| Rule | Result |
|---|---|
| One operational runtime type; no class name ending in `Node` (`AGENTS.md`, LE-NODE-001 to 009, `forbidden_class_names`) | Held. Engines are adapters or strategies used by a Loop; selection, evidence compilation and every envelope are Loops; the future custom Loop harness runs the same Loop runtime in a separate confined process and is not a new type. No proposed class name ends in `Node`. One inaccurate statement about existing names was corrected (issue 22) |
| No parallel registry or source of truth | Mostly held: engines stay in their registries and descriptors are projections; the slot catalogue is joined to and validated by the boundary registry, which meets D-19's "indexed in the boundary registry". Four duplications were corrected (issues 6 to 8) |
| No selection by guessed scores (no heuristics before one million runs, LE-DATA-001) | Held for the design's own rule: exact-scope evidence only, every threshold declared with no code default, snapshots approved and named by digest in the host policy. An existing ranking path in the source and a descriptive field that could be misread were corrected (issues 8 and 9) |
| Permissions never from mode or configuration | Two gaps corrected (issues 10 and 11) |
| An edge never changes when an engine changes | Four gaps corrected (issues 12 to 15) |
| Claims match the source | Eleven corrections (issues 16 to 25, 37) |
| Owner direction of September 22 (`AGENTS.md`, roadmap `4249eca` and `0f1c690`) | Seven missing requirements added (issues 1 to 5, 38, 39) |
| Vocabulary: one meaning per word, no retired words, no acronyms (`terminology.yaml`, `semantic_identity.rules`) | Seven corrections (issues 26 to 32) |
| Known-wrong cases: a removed guard must fail a named check | Two corrections (issues 33 and 35) |
| The Constitution's bootstrap rule and the dimension requirement | Two corrections (issues 34, 36) |

### Issues and corrections

| # | Issue found | Correction made |
|---:|---|---|
| 1 | The header cited D-19 with three steps and the source state `c96b546`. `c96b546` holds no D-19 at all; D-19 entered at `7203492` and gained S-6.40, S-6.41, S-6.42 and four S-6.30 verification items at `4249eca`, before this document was written. `main` is now `230c91e` | Header rewritten with all six steps and the revisions; S-6.40 became the `library_ingestion_source` slot (5.2, 5.7, 7.1), S-6.41 enters the evidence pipeline (10.1), S-6.42 became the fresh-instance rule (13.5) |
| 2 | `AGENTS.md` and S-6.30: "A harness or a Loop may send engine preferences within its authority". The design had Loop overrides only, and its "Loop override" source had no existing `ParameterSourceKind` although the text claimed the existing precedence | 8.4 maps every source to an existing `ParameterSourceKind` (no new kind); a harness preference enters as the typed `engine_preferences` field of the step result (13.3) at `intelligence_proposal`, the lowest precedence, as untrusted data (LE-TRUST-001, LE-DOC-001); checks `a_harness_preference_is_applied_only_within_its_authority` and `engine_preferences_in_a_result_are_data_until_admitted` |
| 3 | S-6.30 "slots nested at every level" and `AGENTS.md` "at the component level and above and below it" were not addressed | New section 4.6; `parent_decision_digest` in the decision record (6.4); check `a_nested_selection_names_its_parent_decision_and_never_widens_it` |
| 4 | S-6.30 "one folder per functional component and one module per engine" and `AGENTS.md` "The folder structure should follow the components and their engines" were not addressed: every new module was flat in `core/`, and `TextRelayStepEngine` sat inside a factory table module | New section 7.8, extending the existing `data/component_folder_map.yaml` registry and following `core/decisions/` and the folder-depth record; new folders `core/engines/`, `core/step_execution/`, `core/library_ingestion/`; paths updated (4.2, 5.5, 7.1, 8.2); check `every_engine_module_holds_one_engine_in_its_component_folder` |
| 5 | `AGENTS.md` and a D-19 action require a search for existing projects, designs and papers before any component is built; the add-an-engine procedure had no such step | 11.1 step 2 |
| 6 | The slot record restated the request and result versions its interaction rows already hold, kept in step only by a consistency check: two sources for one fact | The edge is read from the joined rows (4.1, 7.2); check renamed `every_engine_slot_edge_is_read_from_its_interaction_rows`, known-wrong case a slot record carrying its own copy |
| 7 | `engine_qualification/v1` would sit beside the existing `harness_project_qualification/v1` files (five in `embodiments/`), and `engine_trial_evidence/v1` beside `harness_trial_evidence/v1`, with no rule that one installation has one source | One source per installation: existing records are projected, a second record is refused (6.2, 6.3, 6.5); harness trials stay only in harness records until package X10 converges them |
| 8 | The source already has a second ranking path: `OperationCostLedger.compare` orders implementations by time over producer-written `verified` outcomes with a code default of two samples and names a `preferred` one | Added to the defects of 9.3: with version 2 the ledger only reports, acceptance comes from joined independent verdicts, no default sample size, and no selection path reads it; checks `the_cost_ledger_is_never_a_selection_input`, `a_decision_cost_record_names_its_engine_and_route` (17.5) |
| 9 | The descriptor's `cost_class` (free, cheap, metered, expensive) is a declared adjective that an implementer could rank by | 6.2: descriptive only; no eligibility screen or ranking method reads it |
| 10 | A comparison's allowance (model calls, tokens, spending) was declared inside the selection policy, which is configuration granting spending and model-call authority, against the D-19 authority note | 6.3, 10.2: the allowance cites a separately approved grant for exactly that comparison, zero without one; check `a_comparison_needs_a_separately_approved_authority_grant` (17.6) |
| 11 | Installation settings could carry an authority field such as `allow_network` | 6.3: authority stays in the existing grant fields and the Loop's grant; a settings record that declares authority is refused, the pattern `authority_bearing_is_refused` already enforces; known-wrong case added to `mode_or_configuration_never_grants_engine_permission` (17.3) |
| 12 | The billing surface `billing_provider/v1` renamed the methods the transport calls (`process_event`, `create_session`, `subscription_snapshot` instead of `handle`, `options`, `create`, `configure_policy`), which would force an edit to `http.py`, a neighbour change | 5.3, 15.2: the surface names the existing methods; check `the_billing_surface_names_the_methods_the_transport_already_calls` (17.7) |
| 13 | Hosted capabilities would gain handshake digests, changing `service_capabilities/v1`, which `service.js`, `tools/check_hosted_website.mjs`, `tools/check_service_workspace.mjs` and `tools/install_selected_material.py` read | 14.2: the retrieval keys stay, their values come from the bound engines, digests go to the bindings report |
| 14 | The `service_retrieval_result` version change named only the transport and two check modules; `tools/install_selected_material.py` and `tools/check_client_journey_in_containers.py` pin `v1` as a constant, and three documents quote it | 14.2 lists every consumer, to change in the same commit as the pre-launch policy requires |
| 15 | Rule 13 (one result shape per edge) was not stated for optional values in the step result | 13.3: every key is present in every result; unexposed values are null and read as unknown |
| 16 | Rule 8 claimed "every selection record says `execution_authority_granted: false`". `harness_selection_decision/v1` records only `task_accepted: false`, and route selection events carry neither flag | 1.4 rule 8 states which records carry the flag today |
| 17 | 1.5 said only harness selection records a decision; preference resolution and model route selection record decisions too | 1.5 corrected |
| 18 | `authority_bearing_settings_are_not_generic_setter_targets` was cited as an existing check; it is an `architecture.yaml` invariant, and the check is `authority_bearing_is_refused` in `core/configuration_setter_checks.py` | 5.2 `configuration_setter` row corrected |
| 19 | 13.4 presented refusing a second registration of one identifier as new; `HarnessRegistry.register` already refuses it unless `replace=True`. The real gap is one identifier, `opencode`, naming two engines in two places | 13.4 rewritten; check renamed `one_engine_identifier_names_one_implementation` with the real known-wrong case (17.2) |
| 20 | Adding a process harness edits six places, not five: the relay's request handler chooses the wire by style (`core/harness_process_relay.py` lines 111 to 119). Mounting only the selected recipe's module would also break recipes whose wire codec lives in another recipe module | 1.5, 11.1, 13.7 corrected; `wire_protocols` replaces the style-keyed choice and names the codec module to mount; checks updated (17.7) |
| 21 | 11.8 said the relay needs an Anthropic Messages wire; a text-only codec already exists (`decode_anthropic_text_request` in `core/harness_lightweight_recipes.py`, used for nanocode) | 11.8: extend the existing codec to streamed and tool-use traffic |
| 22 | 18.4 said two live class names end in `Node`; none does. Five begin with it (`NodeAssignment`, `NodeProvisioningError` live; `NodeGrid`, `NodeParameter`, `NodeGridError` parked) | 18.4 item 11 corrected; the engine-side inventory carried the same error |
| 23 | `ISOLATIONS` and `LIMITS` were attributed to `core.facets`; they are in `core.harness_execution_contracts`. "Locality" has two vocabularies (`core.facets.LOCALITY` and `core.model_routes.LOCALITIES`) | 6.2 names each source and forbids comparing across vocabularies |
| 24 | The measurement defect "the gateway names itself" also occurs in the live typed decision path (`core/decisions/gateway.py`) | 9.3 row extended |
| 25 | The construction-site baseline listed five sites; `record_cli.py` also builds `SQLiteRecordStore` or `PackageJsonlStore` from a backend string in live code | 17.2: the baseline is the scanner's output; six sites already found by source search |
| 26 | Section 2 proposed rewriting the Loop Engine definition ("the engine" to "the local runtime"). The owner's text says "a local engine" (`AGENTS.md`) and the README of `230c91e` calls Loop Engine "the open engine behind Baltor" | Withdrawn; instead a qualification rule and an entry in the existing semantic ambiguity register (section 2, 19.1, 19.2 item 8) |
| 27 | "Engine" already has a third use in the record store's native declaration: `StoreCapabilities.engine` and `engine_version` name the database software | Section 2: the adapter is the engine; the database software is pinned inside it and never copied into `engine_id` or `engine_version` |
| 28 | One idea, three spellings (`effects_uncertain`, `effect_outcome_uncertain`, `effect_uncertain`); one flag, two names (`model_call_performed_by_selection` against the existing `model_call_performed_by_boundary`) | One spelling, `effects_uncertain` (6.6, 8.9, 9.2); the existing flag name (6.4) |
| 29 | Several checks had different names in this document and the plan | Aligned: `every_active_engine_slot_conformance_suite_is_collected`, `every_slot_policy_states_an_initial_choice_and_ordered_fallbacks_or_an_explicit_no_fallback`, `selection_decision_records_every_rejection_reason_and_its_propensity`, `expired_qualification_becomes_unknown_and_ineligible` |
| 30 | A known-wrong case used the retired topology word for a Spawned Loop, which `terminology.yaml` forbids in technical documents and the documentation job refuses in `docs/` | 17.3: "A Spawned Loop uses `pin` when its spawning Loop may only `prefer`" |
| 31 | An unexpanded abbreviation named the trajectory format | Spelled out as the Agent Trajectory Interchange Format, version 1.7, of the Harbor evaluation framework (5.2, 13.3) |
| 32 | The generalized failure vocabulary dropped two terminal outcomes that `assess_harness_attempt` already returns (inconclusive evaluation, shared provider failure), so the general rule would have been weaker than the harness rule it claims to keep | 8.9 lists them, mapped to the existing constants |
| 33 | Ten checks in tables 5.2 to 5.4 had no known-wrong case, and "Section 17 lists the full set" was false | Known-wrong cases added in the tables; new section 17.8; four further checks added to 17.7 and 17.8 |
| 34 | Constitution LE-CONFIG-001 and LE-CONFIG-002 require a bounded bootstrap base case; selection uses a ranking slot but the base case was not stated | 8.2 "Base case"; check `engine_selection_needs_no_selection_to_start` |
| 35 | The join check required every run-time slot to name an existing boundary row, which planned slots without an envelope cannot do honestly | 7.2 and 17.1: `planned_without_envelope`; only active and candidate slots must join |
| 36 | The dimension requirement: the Hooks row had an empty fallback cell, and the decision record lacked "the expected effect of the change" and "uncertainty" although the text claimed all eight items | 16 Hooks row filled; 6.4 `transition` and `evidence` fields extended |
| 37 | Entry point loading was described as effect-free discovery followed by loading, without saying that loading runs a third party's code in this process | 7.5: only a distribution the host names, pins and trusts is loaded; untrusted code runs as a confined process engine |
| 38 | `AGENTS.md` makes a unique, freshly started harness for every step the default design; the design did not require proof that an engine can start one | 13.5 `fresh_instance_per_step`; placement `fresh_process` is the default; check `a_harness_without_a_proven_fresh_instance_is_ineligible_for_one_harness_per_step` |
| 39 | Roadmap `0f1c690`, which landed during this check, added S-6.60 (a layer before every model call that decides one model or several, behind a fixed edge with engines of its own), the S-6.31 qualification ladder (connected, material listed, material loaded, step finished, independently accepted) and a fresh process for each step, a per-source provenance contract and multi-file skill packages for S-6.40, and ZCode as an S-6.42 candidate | New planned slot `model_call_strategy` nested between `step_executor` and `model_access` (5.1, 5.2, 4.6, 7.1, 7.8, 8.1, 16, 17.8); the ladder in `engine_qualification/v1` (6.5) and the check `native_loading_is_never_inferred_from_a_bridge_a_session_or_an_exit` (13.13); provenance and packages on the ingestion edge (5.2) with a check (17.8); ZCode listed as a candidate only (13.5) |

### Left as recorded decisions, not changed

- Deterministic governed operations are not delegated to a harness (13.12).
  `AGENTS.md` calls one harness per step "the default design", which allows
  a recorded exception; the decision stays open to the owner.
- The slot catalogue is a data file joined to the boundary registry rather
  than new fields on its 87 rows (19.1); the join is validated by
  `boundary_report()`, which is how D-19's first action is met.
- The floor of ten matched records is a declared, reviewable value in data,
  not a code default (8.6); the one-million-run rule governs learned or
  cross-scope heuristics, which this design does not adopt (8.7).
