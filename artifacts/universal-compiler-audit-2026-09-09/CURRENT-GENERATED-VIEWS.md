# Architecture diagrams

Generated from the typed model in
`src/loop_engine/code_nodes/architecture_diagram.py`. Every code-backed
element names a module that must exist. A self-test fails if one stops
existing, so a rename breaks the diagram instead of leaving it quietly wrong.

These are renderings. The typed model is the record. A diagram language can
express things the system does not do, so each element carries an evidence
state: `implemented` has a current execution path, `partial` has a real
contract or incomplete path, `shadow` observes without changing the solve,
and `target` is planned rather than shipped.

## Loop classification

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
    │   └── non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

## Loop role profiles

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

## Loop Engine in its setting

*context level.* What a run reaches outside itself.

```mermaid
%% Loop Engine in its setting: context level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    operator(["Operator<br/><small>Sets the task, the authority, and the budget.</small><br/><small>State: implemented.</small>"])
    engine["Loop Engine<br/><small>Interprets the task and performs the work through Loops.</small><br/><small>State: implemented.</small>"]
    providers[/"Model providers<br/><small>Ollama, Mistral, OpenRouter and other configured routes.</small><br/><small>State: implemented.</small>"/]
    sandbox[/"Execution sandbox<br/><small>Docker or a confined host process.</small><br/><small>State: implemented.</small>"/]
    sources[/"Task and data sources<br/><small>Files, repositories, datasets, task systems, and benchmarks.</small><br/><small>State: partial.</small>"/]
    tools[/"External tools and services<br/><small>Typed capabilities selected under explicit effect authority.</small><br/><small>State: partial.</small>"/]

    operator -->|"gives a task and authority<br/><i>task text, permissions, budget</i>"| engine
    engine -->|"asks<br/><i>work packets, typed output contracts</i>"| providers
    engine -->|"runs generated code in<br/><i>projects, commands, artifacts</i>"| sandbox
    engine -->|"reads from or writes to<br/><i>authorized source refs and verified artifacts</i>"| sources
    engine -->|"invokes<br/><i>typed requests, observations, effect records</i>"| tools
    engine -->|"returns<br/><i>verified result, or a precise blocker</i>"| operator

%% What a run reaches outside itself.
```

## What a task passes through

*container level.* The middle level between the setting and the components. The state label distinguishes working paths from partial and shadow contracts.

```mermaid
%% What a task passes through: container level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    frontier["Task and frontier<br/><small>The task plus a post-run projection of what stayed open. A living frontier is not implemented.</small><br/><small>State: partial.</small>"]
    practitioner["Practitioner runtime<br/><small>Runs the task as Loops and owns what happens next.</small><br/><small>State: implemented.</small>"]
    orientation["Orientation<br/><small>Reads the situation before committing to an approach.</small><br/><small>State: implemented.</small>"]
    planning["Planning<br/><small>Turns an approach into bounded steps.</small><br/><small>State: implemented.</small>"]
    context["Context compiler<br/><small>Fits the chosen evidence into the window that exists.</small><br/><small>State: implemented.</small>"]
    interface["Semantic interface<br/><small>Defines negotiable response contracts but is not yet wired into product calls.</small><br/><small>State: partial.</small>"]
    calls["Model calls and recording<br/><small>Asks providers, and writes down what was decided.</small><br/><small>State: implemented.</small>"]
    allocation["Model allocation<br/><small>Computes a shadow ladder. Product solve keeps one run-scoped model configuration.</small><br/><small>State: shadow.</small>"]
    capabilities["Capability fabric<br/><small>Tools and skills the run may reach for.</small><br/><small>State: implemented.</small>"]
    harness["External harnesses<br/><small>Other coding agents driven as subordinate workers.</small><br/><small>State: implemented.</small>"]
    verification["Verification<br/><small>Decides whether the work actually satisfies the task.</small><br/><small>State: implemented.</small>"]
    recovery["Recovery<br/><small>Chooses what to do after a failure, by reasoning.</small><br/><small>State: implemented.</small>"]
    stage_evidence[("Stage evidence sidecar<br/><small>Local observations beside selected facts in Run History.</small><br/><small>State: partial.</small>")]
    history[("Run History<br/><small>Canonical ordered evidence for governed Loop work.</small><br/><small>State: implemented.</small>")]

    frontier -->|"hands the open work to<br/><i>task, authority, what is unresolved</i>"| practitioner
    practitioner -->|"starts by<br/><i>the task as given, and the situation</i>"| orientation
    orientation -->|"settles enough to<br/><i>approach, knowns, what is still unknown</i>"| planning
    planning -->|"issues steps through<br/><i>one bounded responsibility at a time</i>"| calls
    context -->|"supplies the evidence to<br/><i>selected evidence, within the window</i>"| calls
    interface -->|"shapes the answer for<br/><i>offered contract, and room to refuse it</i>"| calls
    allocation -->|"orders the routes for<br/><i>a ladder, or a refusal to advise</i>"| calls
    calls -->|"may reach for<br/><i>a tool, with its contract and effects</i>"| capabilities
    calls -->|"may delegate to<br/><i>bounded work, returned as events</i>"| harness
    calls -->|"submits the result to<br/><i>artifacts, claims, evidence</i>"| verification
    verification -->|"escalates a failure to<br/><i>what failed, and what survived it</i>"| recovery
    recovery -->|"returns a plan to<br/><i>the smallest change worth trying</i>"| practitioner
    calls -->|"records stage observations in<br/><i>semantic signature, motif, shape, route</i>"| stage_evidence
    stage_evidence -->|"supplies observations to<br/><i>prior outcomes, or too few to advise on</i>"| allocation
    practitioner -->|"records governed work in<br/><i>Loop events, effects, decisions, verification</i>"| history
    verification -->|"closes or reopens<br/><i>what is now settled, what is still open</i>"| frontier

%% The middle level between the setting and the components. The state label distinguishes working paths from partial and shadow contracts.
```

## What a run records, and what later runs read

*component level.* Default ladder advice stays shadow. An explicit offline binding can expose prior material, with mechanism-only evidence.

```mermaid
%% What a run records, and what later runs read: component level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    practitioner["Adaptive Practitioner<br/><small>Runs the kernel passes and owns every semantic decision.</small><br/><small>State: implemented.</small>"]
    stage("Stage fingerprint<br/><small>Names a semantic situation, motif, and shape. It does not persist exact occurrence identity.</small><br/><small>State: partial.</small>")
    decision("Semantic decision<br/><small>Who decided, from which alternatives, and why.</small><br/><small>State: implemented.</small>")
    outcome("Decision outcome<br/><small>Provides an initial forward join. Complete stage contribution is not wired.</small><br/><small>State: partial.</small>")
    choice("Choice contract<br/><small>One typed shape for every decision put to a model.</small><br/><small>State: implemented.</small>")
    template("Template negotiation<br/><small>Defines negotiable response shapes. Product calls still use fixed step schemas.</small><br/><small>State: partial.</small>")
    recovery("Recovery<br/><small>Reasoning chooses what to do after a failure.</small><br/><small>State: implemented.</small>")
    ladder("Model ladder<br/><small>Computes a shadow route order from coarse prior outcomes. It does not select a route.</small><br/><small>State: shadow.</small>")
    convergence("Convergence measure<br/><small>Default arms stay shadow; explicit bindings control offline packet exposure with injected-provider evidence only.</small><br/><small>State: shadow.</small>")
    credit("Outcome vector<br/><small>Separates several signals from run outcome. Production stage attribution remains partial.</small><br/><small>State: partial.</small>")
    store[("Stage JSONL store<br/><small>Local sidecar index; selected exposure, decision, and action facts also enter Run History, but canonical rows are pending.</small><br/><small>State: partial.</small>")]
    lifecycle("Run stage lifecycle<br/><small>Loads the sidecar and closes it at run exits. Durable campaign storage is not implemented.</small><br/><small>State: partial.</small>")
    history[("Run History<br/><small>Canonical append-only runtime evidence and event chain.</small><br/><small>State: implemented.</small>")]

    credit -->|"is stored beside each stage<br/><i>known signals, unknown signals, granularity</i>"| store
    store -->|"projects coarse evidence into<br/><i>route, attempts, Boolean helped projection</i>"| ladder
    practitioner -->|"names each step<br/><i>responsibility, horizons, what is open</i>"| stage
    practitioner -->|"records every choice<br/><i>owner, alternatives, reason</i>"| decision
    decision -->|"is followed forward<br/><i>admitted, executed, observed, verified</i>"| outcome
    practitioner -->|"asks through<br/><i>options, enforced bounds, novel proposals</i>"| choice
    choice -->|"may negotiate the shape with<br/><i>disposition, replacement, extensions</i>"| template
    choice -->|"carries the failure decision for<br/><i>eligible routes, mechanical facts</i>"| recovery
    stage -->|"requests an occurrence assignment<br/><i>experiment, signature, ephemeral occurrence, seed</i>"| convergence
    lifecycle -->|"loads and closes<br/><i>prior stages in, closed stages out</i>"| store
    stage -->|"is recorded in<br/><i>digest, motif, shape, route</i>"| store
    ladder -->|"is recorded but not applied<br/><i>shadow route order, or an honest refusal</i>"| practitioner
    outcome -->|"adds the run-level result to<br/><i>task outcome beside any local signals</i>"| store
    practitioner -->|"records governed work in<br/><i>Loop events, decisions, effects, verification</i>"| history

%% Default ladder advice stays shadow. An explicit offline binding can expose prior material, with mechanism-only evidence.
```

## One governed semantic responsibility

*dynamic level.* Current product sequence. Response negotiation and stage model allocation have contracts but do not yet control this path.

```mermaid
%% One governed semantic responsibility: dynamic level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    request("Typed responsibility<br/><small>Goal, inputs, authority, budget, and completion condition.</small><br/><small>State: partial.</small>")
    loop["Owning Loop<br/><small>The only executable graph vertex.</small><br/><small>State: implemented.</small>"]
    context("Context selection<br/><small>Selects bounded task and intelligence material.</small><br/><small>State: implemented.</small>")
    interface("Response program<br/><small>Negotiable contract exists but is not on the product path.</small><br/><small>State: partial.</small>")
    allocation("Model allocation<br/><small>A shadow ladder is recorded; the run route stays fixed.</small><br/><small>State: shadow.</small>")
    call("Semantic model call<br/><small>Provider-neutral call through the ModelGateway.</small><br/><small>State: implemented.</small>")
    candidate("Candidate admission<br/><small>Parses and validates an untrusted response.</small><br/><small>State: implemented.</small>")
    action("Authorized action<br/><small>Executes a selected registered capability.</small><br/><small>State: implemented.</small>")
    verify("Verification<br/><small>Checks task evidence and produces a verdict.</small><br/><small>State: implemented.</small>")
    state("Trusted state transition<br/><small>Implemented for the semantic runtime, not yet for every adaptive Practitioner update.</small><br/><small>State: partial.</small>")
    outcome("Stage outcome<br/><small>One selected-action stage has a local result signal; complete stage contribution is unavailable.</small><br/><small>State: partial.</small>")
    history[("Run History<br/><small>Preserves the governed event sequence.</small><br/><small>State: implemented.</small>")]

    request -->|"starts<br/><i>typed work</i>"| loop
    loop -->|"requests<br/><i>context need</i>"| context
    context -->|"supplies<br/><i>selected references and task state</i>"| interface
    interface -->|"describes<br/><i>response and model demand</i>"| allocation
    allocation -->|"would select<br/><i>eligible model portfolio; currently shadow</i>"| call
    call -->|"returns<br/><i>untrusted model response</i>"| candidate
    candidate -->|"proposes<br/><i>validated action request</i>"| action
    action -->|"produces<br/><i>observation, artifacts, execution records</i>"| verify
    verify -->|"authorizes or refuses<br/><i>verified proposed state change</i>"| state
    state -->|"reports<br/><i>local and downstream outcome signals</i>"| outcome
    outcome -->|"records<br/><i>identity, evidence, unknowns, cost</i>"| history

%% Current product sequence. Response negotiation and stage model allocation have contracts but do not yet control this path.
```

## Identity scales and their current linkage

*component level.* Several records exist, but one linked multi-scale fingerprint lattice is not implemented. Partial labels prevent the drawing from claiming otherwise.

```mermaid
%% Identity scales and their current linkage: component level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    f8("F8 Campaign<br/><small>A bounded task population and evaluation run.</small><br/><small>State: partial.</small>")
    f7("F7 Task<br/><small>Structured task identity and compatibility facts.</small><br/><small>State: implemented.</small>")
    f6("F6 Solution branch<br/><small>Independent branch identity and outcome linkage are target behavior.</small><br/><small>State: target.</small>")
    f5("F5 Structural subgraph<br/><small>Solution graphs exist; cross-run subgraph fingerprints do not.</small><br/><small>State: partial.</small>")
    f4("F4 Cognitive episode<br/><small>Reviewed episode records exist outside the production stage lattice.</small><br/><small>State: partial.</small>")
    f3("F3 State transition<br/><small>Versioned semantic transitions exist on a narrower runtime path.</small><br/><small>State: partial.</small>")
    f2("F2 Loop activation occurrence<br/><small>Product events link activation, semantic call, and attempts; canonical projection records are pending.</small><br/><small>State: partial.</small>")
    f1("F1 Logical semantic call<br/><small>One coherent semantic invocation identity.</small><br/><small>State: partial.</small>")
    f0("F0 Physical provider attempt<br/><small>Exact provider attempt and usage evidence.</small><br/><small>State: implemented.</small>")
    f9("F9 Cross-run motif<br/><small>Derived stage motif with no campaign outcome linkage.</small><br/><small>State: partial.</small>")

    f8 -->|"contains<br/><i>task references</i>"| f7
    f7 -->|"may compare<br/><i>branch identity and task objective</i>"| f6
    f6 -->|"contains<br/><i>subgraph identity and topology</i>"| f5
    f5 -->|"contains<br/><i>episode references</i>"| f4
    f4 -->|"summarizes<br/><i>ordered transition references</i>"| f3
    f3 -->|"is produced by<br/><i>exact Loop activation reference</i>"| f2
    f2 -->|"owns<br/><i>logical semantic call references</i>"| f1
    f1 -->|"may require<br/><i>one or more physical attempt references</i>"| f0
    f4 -->|"may project to<br/><i>cross-run motif candidate</i>"| f9

%% Several records exist, but one linked multi-scale fingerprint lattice is not implemented. Partial labels prevent the drawing from claiming otherwise.
```

## Candidate paired stage assistance path

*dynamic level.* The evidence contracts and rebuildable projection are implemented as a partial foundation. The public offline solve path executes both arms with injected responses and hydrated advisory material. Its control manifest says mechanism-only; live benefit is unproven.

```mermaid
%% Candidate paired stage assistance path: dynamic level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    history[("Canonical Run History<br/><small>Immutable source events for experiment records.</small><br/><small>State: implemented.</small>")]
    projection[("Stage evidence projection<br/><small>Rebuilds canonical source rows, not current product histories.</small><br/><small>State: partial.</small>")]
    trial("Control manifest and trial<br/><small>The fixture shares one manifest with six blocking unknowns.</small><br/><small>State: partial.</small>")
    retrieval("Prior candidate snapshot<br/><small>Offline fixture injects typed candidates and digest-bound hydrated material; canonical Run History query is pending.</small><br/><small>State: partial.</small>")
    advisory("Advisory assignment<br/><small>Exposure manifest may name retrieved prior references.</small><br/><small>State: partial.</small>")
    fresh("Fresh assignment<br/><small>Exposure manifest requires zero prior references.</small><br/><small>State: partial.</small>")
    assisted_call("Assisted model call<br/><small>Public offline solve sends hydrated prior material through the prompt-sensitive injected provider adapter.</small><br/><small>State: partial.</small>")
    fresh_call("Fresh model call<br/><small>Public offline solve sends no candidate or hydrated prior material through the same injected provider path.</small><br/><small>State: partial.</small>")
    verify("Action result verification<br/><small>Exact occurrence refs link one selected action, execution, and same-Practitioner verifier; independence is pending.</small><br/><small>State: partial.</small>")
    outcome("Linked trial outcomes<br/><small>The contract can hold outcomes; the fixture emits none.</small><br/><small>State: partial.</small>")

    history -->|"rebuilds<br/><i>digest-bound stage experiment records</i>"| projection
    projection -->|"is intended to supply<br/><i>scoped prior occurrence references</i>"| trial
    trial -->|"freezes<br/><i>source-state digest and control unknowns</i>"| retrieval
    retrieval -->|"may expose<br/><i>exact prior candidate references</i>"| advisory
    trial -->|"also creates<br/><i>an occurrence with zero prior references</i>"| fresh
    advisory -->|"feeds offline<br/><i>hydrated material and explicit use contract</i>"| assisted_call
    fresh -->|"feeds offline<br/><i>fresh packet from the same declared source state</i>"| fresh_call
    assisted_call -->|"submits offline<br/><i>assisted output and call records</i>"| verify
    fresh_call -->|"submits offline<br/><i>fresh output and call records</i>"| verify
    verify -->|"would produce canonical<br/><i>metric, run validity, cost, latency, usage</i>"| outcome
    outcome -->|"must be recorded in<br/><i>linked immutable outcome evidence</i>"| history

%% The evidence contracts and rebuildable projection are implemented as a partial foundation. The public offline solve path executes both arms with injected responses and hydrated advisory material. Its control manifest says mechanism-only; live benefit is unproven.
```

## Learning evidence deployment boundary

*container level.* Current runs and Run History are local. The SQLite stage evidence projection is a rebuildable index, not a shared authority. A multi-tenant learning service remains a target.

```mermaid
%% Learning evidence deployment boundary: container level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    solve["Local product solve<br/><small>One adaptive Practitioner run.</small><br/><small>State: implemented.</small>"]
    history[("Local Run History<br/><small>Canonical event and artifact references.</small><br/><small>State: implemented.</small>")]
    sidecar[("Stage JSONL sidecar<br/><small>Optional shared path with no campaign transaction contract.</small><br/><small>State: partial.</small>")]
    projection[("SQLite stage projection<br/><small>File-backed WAL index rebuilt from Run History events.</small><br/><small>State: partial.</small>")]
    scheduler["Reactive scheduler<br/><small>Local durable activation scheduling and fencing.</small><br/><small>State: implemented.</small>"]
    providers["Model gateway<br/><small>Configured provider routes and exact physical attempts.</small><br/><small>State: implemented.</small>"]
    tools["Capability directory<br/><small>Effect-free discovery before authorized invocation.</small><br/><small>State: implemented.</small>"]
    shared[/"Shared learning service<br/><small>Transactional multi-tenant ingestion, retention, and query.</small><br/><small>State: target.</small>"/]

    solve -->|"writes<br/><i>canonical Loop events and artifact refs</i>"| history
    solve -->|"may write<br/><i>shadow stage observations</i>"| sidecar
    history -->|"rebuilds<br/><i>committed intact stage evidence events</i>"| projection
    scheduler -->|"may activate<br/><i>leased finite Loop work</i>"| solve
    solve -->|"calls through<br/><i>authorized semantic requests</i>"| providers
    solve -->|"discovers and invokes through<br/><i>typed capability requests and effect records</i>"| tools
    history -->|"could publish to<br/><i>privacy-scoped immutable evidence</i>"| shared
    shared -->|"could replace<br/><i>shared query projection, never runtime authority</i>"| projection

%% Current runs and Run History are local. The SQLite stage evidence projection is a rebuildable index, not a shared authority. A multi-tenant learning service remains a target.
```

## Typed record access and distinct storage authorities

*component level.* Store and artifact boxes are internal mechanics, not executable Loop graph vertices. Managed notes use a tool; committed Run History has a separate immutable owner. PostgreSQL remains a target.

```mermaid
%% Typed record access and distinct storage authorities: component level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    caller["Developer or operational Loop<br/><small>Submits a typed record request under host-granted scope.</small><br/><small>State: implemented.</small>"]
    operations("Managed record operations<br/><small>Schema, scope, exact effect approval and revision checks.</small><br/><small>State: partial.</small>")
    query("Catalog query contract<br/><small>One closed filter contract; no LLM SQL text.</small><br/><small>State: implemented.</small>")
    files[("Immutable package JSONL<br/><small>Shipped read-only records; not a mutable notes document.</small><br/><small>State: implemented.</small>")]
    duckdb("DuckDB file query adapter<br/><small>Bounded JSONL reads with typed filters; no file CRUD.</small><br/><small>State: partial.</small>")
    sqlite[("Local SQLite records<br/><small>Scoped mutable heads with atomic version preconditions.</small><br/><small>State: implemented.</small>")]
    artifacts[("Immutable revision artifacts<br/><small>Digest-addressed document revisions with prior references.</small><br/><small>State: implemented.</small>")]
    history[("Canonical Run History<br/><small>Append-only execution evidence; not edited by note CRUD.</small><br/><small>State: implemented.</small>")]
    postgres[/"Server record adapter<br/><small>Future qualified multi-process database backend.</small><br/><small>State: target.</small>"/]

    caller -->|"requests<br/><i>typed operation, expected revision, document</i>"| operations
    operations -->|"compiles bounded reads<br/><i>host-enforced namespace and typed predicates</i>"| query
    query -->|"reads through adapter<br/><i>record cards and selected values</i>"| files
    query -->|"uses optional SQL implementation<br/><i>bound literals and declared source files</i>"| duckdb
    duckdb -->|"scans without writing<br/><i>JSONL record bytes</i>"| files
    operations -->|"stores after approval<br/><i>immutable revision bytes and digest</i>"| artifacts
    operations -->|"commits after artifact write<br/><i>current reference with atomic precondition</i>"| sqlite
    query -->|"queries<br/><i>scoped record results</i>"| sqlite
    operations -->|"host may persist owning Loop events<br/><i>operation metadata; no automatic CLI history write</i>"| history
    query -->|"could use qualified adapter<br/><i>same typed request with declared capabilities</i>"| postgres

%% Store and artifact boxes are internal mechanics, not executable Loop graph vertices. Managed notes use a tool; committed Run History has a separate immutable owner. PostgreSQL remains a target.
```

## The same models as C4-PlantUML

Generated using C4-PlantUML standard-library macros. These blocks are not Structurizr DSL. Pin and verify the rendering tool before publication.

### Loop Engine in its setting (DSL)

```plantuml
@startuml
!include <C4/C4_Component>
' Generated from the typed model; do not edit by hand.
Person(element_0, "Operator", "[implemented] Sets the task, the authority, and the budget.")
System(element_1, "Loop Engine", "[implemented] Interprets the task and performs the work through Loops.")
System_Ext(element_2, "Model providers", "[implemented] Ollama, Mistral, OpenRouter and other configured routes.")
System_Ext(element_3, "Execution sandbox", "[implemented] Docker or a confined host process.")
System_Ext(element_4, "Task and data sources", "[partial] Files, repositories, datasets, task systems, and benchmarks.")
System_Ext(element_5, "External tools and services", "[partial] Typed capabilities selected under explicit effect authority.")

Rel(element_0, element_1, "gives a task and authority", "task text, permissions, budget")
Rel(element_1, element_2, "asks", "work packets, typed output contracts")
Rel(element_1, element_3, "runs generated code in", "projects, commands, artifacts")
Rel(element_1, element_4, "reads from or writes to", "authorized source refs and verified artifacts")
Rel(element_1, element_5, "invokes", "typed requests, observations, effect records")
Rel(element_1, element_0, "returns", "verified result, or a precise blocker")
@enduml
```

### What a task passes through (DSL)

```plantuml
@startuml
!include <C4/C4_Component>
' Generated from the typed model; do not edit by hand.
Container(element_0, "Task and frontier", "core.task_frontier", "[partial] The task plus a post-run projection of what stayed open. A living frontier is not implemented.")
Container(element_1, "Practitioner runtime", "core.adaptive_practitioner", "[implemented] Runs the task as Loops and owns what happens next.")
Container(element_2, "Orientation", "core.adaptive_practitioner_orientation", "[implemented] Reads the situation before committing to an approach.")
Container(element_3, "Planning", "core.adaptive_practitioner_planning", "[implemented] Turns an approach into bounded steps.")
Container(element_4, "Context compiler", "core.context_budget", "[implemented] Fits the chosen evidence into the window that exists.")
Container(element_5, "Semantic interface", "core.template_negotiation", "[partial] Defines negotiable response contracts but is not yet wired into product calls.")
Container(element_6, "Model calls and recording", "core.adaptive_practitioner_records", "[implemented] Asks providers, and writes down what was decided.")
Container(element_7, "Model allocation", "core.model_demand", "[shadow] Computes a shadow ladder. Product solve keeps one run-scoped model configuration.")
Container(element_8, "Capability fabric", "core.capability_directory", "[implemented] Tools and skills the run may reach for.")
Container(element_9, "External harnesses", "core.external_harness", "[implemented] Other coding agents driven as subordinate workers.")
Container(element_10, "Verification", "core.adaptive_practitioner_verification", "[implemented] Decides whether the work actually satisfies the task.")
Container(element_11, "Recovery", "core.adaptive_practitioner_recovery", "[implemented] Chooses what to do after a failure, by reasoning.")
ContainerDb(element_12, "Stage evidence sidecar", "core.stage_store", "[partial] Local observations beside selected facts in Run History.")
ContainerDb(element_13, "Run History", "core.run_history", "[implemented] Canonical ordered evidence for governed Loop work.")

Rel(element_0, element_1, "hands the open work to", "task, authority, what is unresolved")
Rel(element_1, element_2, "starts by", "the task as given, and the situation")
Rel(element_2, element_3, "settles enough to", "approach, knowns, what is still unknown")
Rel(element_3, element_6, "issues steps through", "one bounded responsibility at a time")
Rel(element_4, element_6, "supplies the evidence to", "selected evidence, within the window")
Rel(element_5, element_6, "shapes the answer for", "offered contract, and room to refuse it")
Rel(element_7, element_6, "orders the routes for", "a ladder, or a refusal to advise")
Rel(element_6, element_8, "may reach for", "a tool, with its contract and effects")
Rel(element_6, element_9, "may delegate to", "bounded work, returned as events")
Rel(element_6, element_10, "submits the result to", "artifacts, claims, evidence")
Rel(element_10, element_11, "escalates a failure to", "what failed, and what survived it")
Rel(element_11, element_1, "returns a plan to", "the smallest change worth trying")
Rel(element_6, element_12, "records stage observations in", "semantic signature, motif, shape, route")
Rel(element_12, element_7, "supplies observations to", "prior outcomes, or too few to advise on")
Rel(element_1, element_13, "records governed work in", "Loop events, effects, decisions, verification")
Rel(element_10, element_0, "closes or reopens", "what is now settled, what is still open")
@enduml
```

### What a run records, and what later runs read (DSL)

```plantuml
@startuml
!include <C4/C4_Component>
' Generated from the typed model; do not edit by hand.
Container(element_0, "Adaptive Practitioner", "core.adaptive_practitioner", "[implemented] Runs the kernel passes and owns every semantic decision.")
Component(element_1, "Stage fingerprint", "core.stage_fingerprint", "[partial] Names a semantic situation, motif, and shape. It does not persist exact occurrence identity.")
Component(element_2, "Semantic decision", "core.semantic_decision", "[implemented] Who decided, from which alternatives, and why.")
Component(element_3, "Decision outcome", "core.decision_outcome", "[partial] Provides an initial forward join. Complete stage contribution is not wired.")
Component(element_4, "Choice contract", "core.choice", "[implemented] One typed shape for every decision put to a model.")
Component(element_5, "Template negotiation", "core.template_negotiation", "[partial] Defines negotiable response shapes. Product calls still use fixed step schemas.")
Component(element_6, "Recovery", "core.recovery", "[implemented] Reasoning chooses what to do after a failure.")
Component(element_7, "Model ladder", "core.model_demand", "[shadow] Computes a shadow route order from coarse prior outcomes. It does not select a route.")
Component(element_8, "Convergence measure", "core.convergence", "[shadow] Default arms stay shadow; explicit bindings control offline packet exposure with injected-provider evidence only.")
Component(element_9, "Outcome vector", "core.outcome_vector", "[partial] Separates several signals from run outcome. Production stage attribution remains partial.")
ContainerDb(element_10, "Stage JSONL store", "core.stage_store", "[partial] Local sidecar index; selected exposure, decision, and action facts also enter Run History, but canonical rows are pending.")
Component(element_11, "Run stage lifecycle", "core.run_stages", "[partial] Loads the sidecar and closes it at run exits. Durable campaign storage is not implemented.")
ContainerDb(element_12, "Run History", "core.run_history", "[implemented] Canonical append-only runtime evidence and event chain.")

Rel(element_9, element_10, "is stored beside each stage", "known signals, unknown signals, granularity")
Rel(element_10, element_7, "projects coarse evidence into", "route, attempts, Boolean helped projection")
Rel(element_0, element_1, "names each step", "responsibility, horizons, what is open")
Rel(element_0, element_2, "records every choice", "owner, alternatives, reason")
Rel(element_2, element_3, "is followed forward", "admitted, executed, observed, verified")
Rel(element_0, element_4, "asks through", "options, enforced bounds, novel proposals")
Rel(element_4, element_5, "may negotiate the shape with", "disposition, replacement, extensions")
Rel(element_4, element_6, "carries the failure decision for", "eligible routes, mechanical facts")
Rel(element_1, element_8, "requests an occurrence assignment", "experiment, signature, ephemeral occurrence, seed")
Rel(element_11, element_10, "loads and closes", "prior stages in, closed stages out")
Rel(element_1, element_10, "is recorded in", "digest, motif, shape, route")
Rel(element_7, element_0, "is recorded but not applied", "shadow route order, or an honest refusal")
Rel(element_3, element_10, "adds the run-level result to", "task outcome beside any local signals")
Rel(element_0, element_12, "records governed work in", "Loop events, decisions, effects, verification")
@enduml
```

### One governed semantic responsibility (DSL)

```plantuml
@startuml
!include <C4/C4_Component>
' Generated from the typed model; do not edit by hand.
Component(element_0, "Typed responsibility", "core.task_frontier", "[partial] Goal, inputs, authority, budget, and completion condition.")
Container(element_1, "Owning Loop", "loop.recursive_loop", "[implemented] The only executable graph vertex.")
Component(element_2, "Context selection", "core.practitioner_context", "[implemented] Selects bounded task and intelligence material.")
Component(element_3, "Response program", "core.template_negotiation", "[partial] Negotiable contract exists but is not on the product path.")
Component(element_4, "Model allocation", "core.model_demand", "[shadow] A shadow ladder is recorded; the run route stays fixed.")
Component(element_5, "Semantic model call", "core.model_gateway", "[implemented] Provider-neutral call through the ModelGateway.")
Component(element_6, "Candidate admission", "core.model_response_admission", "[implemented] Parses and validates an untrusted response.")
Component(element_7, "Authorized action", "core.adaptive_practitioner_capabilities", "[implemented] Executes a selected registered capability.")
Component(element_8, "Verification", "core.adaptive_practitioner_verification", "[implemented] Checks task evidence and produces a verdict.")
Component(element_9, "Trusted state transition", "core.semantic_state", "[partial] Implemented for the semantic runtime, not yet for every adaptive Practitioner update.")
Component(element_10, "Stage outcome", "core.outcome_vector", "[partial] One selected-action stage has a local result signal; complete stage contribution is unavailable.")
ContainerDb(element_11, "Run History", "core.run_history", "[implemented] Preserves the governed event sequence.")

Rel(element_0, element_1, "starts", "typed work")
Rel(element_1, element_2, "requests", "context need")
Rel(element_2, element_3, "supplies", "selected references and task state")
Rel(element_3, element_4, "describes", "response and model demand")
Rel(element_4, element_5, "would select", "eligible model portfolio; currently shadow")
Rel(element_5, element_6, "returns", "untrusted model response")
Rel(element_6, element_7, "proposes", "validated action request")
Rel(element_7, element_8, "produces", "observation, artifacts, execution records")
Rel(element_8, element_9, "authorizes or refuses", "verified proposed state change")
Rel(element_9, element_10, "reports", "local and downstream outcome signals")
Rel(element_10, element_11, "records", "identity, evidence, unknowns, cost")
@enduml
```

### Identity scales and their current linkage (DSL)

```plantuml
@startuml
!include <C4/C4_Component>
' Generated from the typed model; do not edit by hand.
Component(element_0, "F8 Campaign", "code_nodes.campaign_runner", "[partial] A bounded task population and evaluation run.")
Component(element_1, "F7 Task", "core.task_fingerprint", "[implemented] Structured task identity and compatibility facts.")
Component(element_2, "F6 Solution branch", "unspecified", "[target] Independent branch identity and outcome linkage are target behavior.")
Component(element_3, "F5 Structural subgraph", "code_nodes.solution_graph", "[partial] Solution graphs exist; cross-run subgraph fingerprints do not.")
Component(element_4, "F4 Cognitive episode", "memory.episodic.record", "[partial] Reviewed episode records exist outside the production stage lattice.")
Component(element_5, "F3 State transition", "core.semantic_state", "[partial] Versioned semantic transitions exist on a narrower runtime path.")
Component(element_6, "F2 Loop activation occurrence", "loop.recursive_loop", "[partial] Product events link activation, semantic call, and attempts; canonical projection records are pending.")
Component(element_7, "F1 Logical semantic call", "core.semantic_runtime_records", "[partial] One coherent semantic invocation identity.")
Component(element_8, "F0 Physical provider attempt", "core.model_gateway", "[implemented] Exact provider attempt and usage evidence.")
Component(element_9, "F9 Cross-run motif", "core.stage_fingerprint", "[partial] Derived stage motif with no campaign outcome linkage.")

Rel(element_0, element_1, "contains", "task references")
Rel(element_1, element_2, "may compare", "branch identity and task objective")
Rel(element_2, element_3, "contains", "subgraph identity and topology")
Rel(element_3, element_4, "contains", "episode references")
Rel(element_4, element_5, "summarizes", "ordered transition references")
Rel(element_5, element_6, "is produced by", "exact Loop activation reference")
Rel(element_6, element_7, "owns", "logical semantic call references")
Rel(element_7, element_8, "may require", "one or more physical attempt references")
Rel(element_4, element_9, "may project to", "cross-run motif candidate")
@enduml
```

### Candidate paired stage assistance path (DSL)

```plantuml
@startuml
!include <C4/C4_Component>
' Generated from the typed model; do not edit by hand.
ContainerDb(element_0, "Canonical Run History", "core.run_history", "[implemented] Immutable source events for experiment records.")
ContainerDb(element_1, "Stage evidence projection", "core.stage_evidence_projection", "[partial] Rebuilds canonical source rows, not current product histories.")
Component(element_2, "Control manifest and trial", "core.stage_assistance_experiment", "[partial] The fixture shares one manifest with six blocking unknowns.")
Component(element_3, "Prior candidate snapshot", "core.stage_evidence_records", "[partial] Offline fixture injects typed candidates and digest-bound hydrated material; canonical Run History query is pending.")
Component(element_4, "Advisory assignment", "core.stage_assistance_experiment", "[partial] Exposure manifest may name retrieved prior references.")
Component(element_5, "Fresh assignment", "core.stage_assistance_experiment", "[partial] Exposure manifest requires zero prior references.")
Component(element_6, "Assisted model call", "core.model_gateway", "[partial] Public offline solve sends hydrated prior material through the prompt-sensitive injected provider adapter.")
Component(element_7, "Fresh model call", "core.model_gateway", "[partial] Public offline solve sends no candidate or hydrated prior material through the same injected provider path.")
Component(element_8, "Action result verification", "core.stage_action_lineage", "[partial] Exact occurrence refs link one selected action, execution, and same-Practitioner verifier; independence is pending.")
Component(element_9, "Linked trial outcomes", "core.stage_evidence_records", "[partial] The contract can hold outcomes; the fixture emits none.")

Rel(element_0, element_1, "rebuilds", "digest-bound stage experiment records")
Rel(element_1, element_2, "is intended to supply", "scoped prior occurrence references")
Rel(element_2, element_3, "freezes", "source-state digest and control unknowns")
Rel(element_3, element_4, "may expose", "exact prior candidate references")
Rel(element_2, element_5, "also creates", "an occurrence with zero prior references")
Rel(element_4, element_6, "feeds offline", "hydrated material and explicit use contract")
Rel(element_5, element_7, "feeds offline", "fresh packet from the same declared source state")
Rel(element_6, element_8, "submits offline", "assisted output and call records")
Rel(element_7, element_8, "submits offline", "fresh output and call records")
Rel(element_8, element_9, "would produce canonical", "metric, run validity, cost, latency, usage")
Rel(element_9, element_0, "must be recorded in", "linked immutable outcome evidence")
@enduml
```

### Learning evidence deployment boundary (DSL)

```plantuml
@startuml
!include <C4/C4_Component>
' Generated from the typed model; do not edit by hand.
Container(element_0, "Local product solve", "core.adaptive_practitioner", "[implemented] One adaptive Practitioner run.")
ContainerDb(element_1, "Local Run History", "core.run_history", "[implemented] Canonical event and artifact references.")
ContainerDb(element_2, "Stage JSONL sidecar", "core.stage_store", "[partial] Optional shared path with no campaign transaction contract.")
ContainerDb(element_3, "SQLite stage projection", "core.stage_evidence_projection", "[partial] File-backed WAL index rebuilt from Run History events.")
Container(element_4, "Reactive scheduler", "core.reactive_scheduler", "[implemented] Local durable activation scheduling and fencing.")
Container(element_5, "Model gateway", "core.model_gateway", "[implemented] Configured provider routes and exact physical attempts.")
Container(element_6, "Capability directory", "core.capability_directory", "[implemented] Effect-free discovery before authorized invocation.")
System_Ext(element_7, "Shared learning service", "[target] Transactional multi-tenant ingestion, retention, and query.")

Rel(element_0, element_1, "writes", "canonical Loop events and artifact refs")
Rel(element_0, element_2, "may write", "shadow stage observations")
Rel(element_1, element_3, "rebuilds", "committed intact stage evidence events")
Rel(element_4, element_0, "may activate", "leased finite Loop work")
Rel(element_0, element_5, "calls through", "authorized semantic requests")
Rel(element_0, element_6, "discovers and invokes through", "typed capability requests and effect records")
Rel(element_1, element_7, "could publish to", "privacy-scoped immutable evidence")
Rel(element_7, element_3, "could replace", "shared query projection, never runtime authority")
@enduml
```

### Typed record access and distinct storage authorities (DSL)

```plantuml
@startuml
!include <C4/C4_Component>
' Generated from the typed model; do not edit by hand.
Container(element_0, "Developer or operational Loop", "loop.recursive_loop", "[implemented] Submits a typed record request under host-granted scope.")
Component(element_1, "Managed record operations", "core.record_operations", "[partial] Schema, scope, exact effect approval and revision checks.")
Component(element_2, "Catalog query contract", "catalog.query", "[implemented] One closed filter contract; no LLM SQL text.")
ContainerDb(element_3, "Immutable package JSONL", "catalog.stores.package_jsonl", "[implemented] Shipped read-only records; not a mutable notes document.")
Component(element_4, "DuckDB file query adapter", "catalog.stores.duckdb_files", "[partial] Bounded JSONL reads with typed filters; no file CRUD.")
ContainerDb(element_5, "Local SQLite records", "catalog.stores.sqlite_store", "[implemented] Scoped mutable heads with atomic version preconditions.")
ContainerDb(element_6, "Immutable revision artifacts", "core.context_artifacts", "[implemented] Digest-addressed document revisions with prior references.")
ContainerDb(element_7, "Canonical Run History", "core.run_history", "[implemented] Append-only execution evidence; not edited by note CRUD.")
System_Ext(element_8, "Server record adapter", "[target] Future qualified multi-process database backend.")

Rel(element_0, element_1, "requests", "typed operation, expected revision, document")
Rel(element_1, element_2, "compiles bounded reads", "host-enforced namespace and typed predicates")
Rel(element_2, element_3, "reads through adapter", "record cards and selected values")
Rel(element_2, element_4, "uses optional SQL implementation", "bound literals and declared source files")
Rel(element_4, element_3, "scans without writing", "JSONL record bytes")
Rel(element_1, element_6, "stores after approval", "immutable revision bytes and digest")
Rel(element_1, element_5, "commits after artifact write", "current reference with atomic precondition")
Rel(element_2, element_5, "queries", "scoped record results")
Rel(element_1, element_7, "host may persist owning Loop events", "operation metadata; no automatic CLI history write")
Rel(element_2, element_8, "could use qualified adapter", "same typed request with declared capabilities")
@enduml
```
