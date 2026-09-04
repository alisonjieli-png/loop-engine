# Architecture diagrams

Generated from the typed model in
`src/loop_engine/code_nodes/architecture_diagram.py`. Every element
names a module that must exist; a self-test fails if one stops
existing, so a rename breaks the diagram loudly rather than leaving
it quietly wrong.

These are renderings. The typed model is the record — a diagram
language can express things the system does not do, and once the
picture is authoritative those inventions become requirements
nobody agreed to.

## Loop Engine in its setting

*context level.* What a run reaches outside itself.

```mermaid
%% Loop Engine in its setting — context level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    operator(["Operator<br/><small>Sets the task, the authority, and the budget.</small>"])
    engine["Loop Engine<br/><small>Interprets the task and performs the work through Loops.</small>"]
    providers[/"Model providers<br/><small>Ollama, Mistral, OpenRouter and other configured routes.</small>"/]
    sandbox[/"Execution sandbox<br/><small>Docker or a confined host process.</small>"/]
    kaggle[/"Kaggle<br/><small>Competition data in, submissions out and graded.</small>"/]

    operator -->|"gives a task and authority<br/><i>task text, permissions, budget</i>"| engine
    engine -->|"asks<br/><i>work packets, typed output contracts</i>"| providers
    engine -->|"runs generated code in<br/><i>projects, commands, artifacts</i>"| sandbox
    engine -->|"reads and submits<br/><i>datasets, submission files</i>"| kaggle
    engine -->|"returns<br/><i>verified result, or a precise blocker</i>"| operator

%% What a run reaches outside itself.
```

## What a task passes through

*container level.* The middle level, between the setting and the components. Each box is a responsibility with a module behind it, not a plane this repository intends to build.

```mermaid
%% What a task passes through — container level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    frontier["Task and frontier<br/><small>The task as given, and what is still open about it.</small>"]
    practitioner["Practitioner runtime<br/><small>Runs the task as Loops and owns what happens next.</small>"]
    orientation["Orientation<br/><small>Reads the situation before committing to an approach.</small>"]
    planning["Planning<br/><small>Turns an approach into bounded steps.</small>"]
    context["Context compiler<br/><small>Fits the chosen evidence into the window that exists.</small>"]
    interface["Semantic interface<br/><small>Offers a response shape the answer may negotiate.</small>"]
    calls["Model calls and recording<br/><small>Asks providers, and writes down what was decided.</small>"]
    allocation["Model allocation<br/><small>Which route to try first, where evidence supports one.</small>"]
    capabilities["Capability fabric<br/><small>Tools and skills the run may reach for.</small>"]
    harness["External harnesses<br/><small>Other coding agents driven as subordinate workers.</small>"]
    verification["Verification<br/><small>Decides whether the work actually satisfies the task.</small>"]
    recovery["Recovery<br/><small>Chooses what to do after a failure, by reasoning.</small>"]
    history[("Run history<br/><small>Every stage seen, and what became of it.</small>")]

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
    calls -->|"records every stage in<br/><i>situation, route, and what it contributed</i>"| history
    history -->|"is the only evidence for<br/><i>prior outcomes, or too few to advise on</i>"| allocation
    verification -->|"closes or reopens<br/><i>what is now settled, what is still open</i>"| frontier

%% The middle level, between the setting and the components. Each box is a responsibility with a module behind it, not a plane this repository intends to build.
```

## What a run records, and what later runs read

*component level.* The loop that makes the engine self-observing. Advice flows out of the store and is recorded rather than obeyed.

```mermaid
%% What a run records, and what later runs read — component level
%% Generated from the typed model; do not edit by hand.
flowchart TD
    practitioner["Adaptive Practitioner<br/><small>Runs the kernel passes and owns every semantic decision.</small>"]
    stage("Stage fingerprint<br/><small>Names one cognitive situation; its motif crosses domains.</small>")
    decision("Semantic decision<br/><small>Who decided, from which alternatives, and why.</small>")
    outcome("Decision outcome<br/><small>Joins a decision forward to whether it helped.</small>")
    choice("Choice contract<br/><small>One typed shape for every decision put to a model.</small>")
    template("Template negotiation<br/><small>The response shape is offered, and may be refused.</small>")
    recovery("Recovery<br/><small>Reasoning chooses what to do after a failure.</small>")
    ladder("Model ladder<br/><small>Which route to try first, fitted to what worked.</small>")
    convergence("Convergence measure<br/><small>Splits an arm off so agreement can be told from suggestion.</small>")
    credit("Outcome vector<br/><small>What a stage contributed, kept apart from how its run ended.</small>")
    store[("Stage store<br/><small>Append-only; indexed by exact identity, motif, and shape.</small>")]
    lifecycle("Run stage lifecycle<br/><small>Loads the store at the start, closes it at every exit.</small>")

    store -->|"grades each stage through<br/><i>verification, contribution, run fate, and which of those nobody observed</i>"| credit
    credit -->|"supplies evidence to<br/><i>credit and the granularity it was earned at</i>"| ladder
    practitioner -->|"names each step<br/><i>responsibility, horizons, what is open</i>"| stage
    practitioner -->|"records every choice<br/><i>owner, alternatives, reason</i>"| decision
    decision -->|"is followed forward<br/><i>admitted, executed, observed, verified</i>"| outcome
    practitioner -->|"asks through<br/><i>options, enforced bounds, novel proposals</i>"| choice
    choice -->|"may negotiate the shape with<br/><i>disposition, replacement, extensions</i>"| template
    choice -->|"carries the failure decision for<br/><i>eligible routes, mechanical facts</i>"| recovery
    stage -->|"assigns an arm from its identity<br/><i>offered or control, before anything is shown</i>"| convergence
    lifecycle -->|"loads and closes<br/><i>prior stages in, closed stages out</i>"| store
    stage -->|"is recorded in<br/><i>digest, motif, shape, route</i>"| store
    store -->|"supplies prior shapes to<br/><i>routes tried and whether they helped</i>"| ladder
    ladder -->|"advises, and is not obeyed<br/><i>an order to try, or an honest refusal</i>"| practitioner
    outcome -->|"closes stages with the run's result<br/><i>helped, hurt, or still unknown</i>"| store

%% The loop that makes the engine self-observing. Advice flows out of the store and is recorded rather than obeyed.
```

## The same models as C4 DSL

Rendered for a Structurizr-style tool.

### Loop Engine in its setting (DSL)

```text
# Loop Engine in its setting
# level: context
# Generated from the typed model; do not edit by hand.
workspace {
    model {
        operator = person "Operator" "Sets the task, the authority, and the budget."
        engine = system "Loop Engine" "Interprets the task and performs the work through Loops."
        providers = system_ext "Model providers" "Ollama, Mistral, OpenRouter and other configured routes."
        sandbox = system_ext "Execution sandbox" "Docker or a confined host process."
        kaggle = system_ext "Kaggle" "Competition data in, submissions out and graded."

        operator -> engine "gives a task and authority"
        engine -> providers "asks"
        engine -> sandbox "runs generated code in"
        engine -> kaggle "reads and submits"
        engine -> operator "returns"
    }
}
```

### What a task passes through (DSL)

```text
# What a task passes through
# level: container
# Generated from the typed model; do not edit by hand.
workspace {
    model {
        frontier = container "Task and frontier" "The task as given, and what is still open about it."
        practitioner = container "Practitioner runtime" "Runs the task as Loops and owns what happens next."
        orientation = container "Orientation" "Reads the situation before committing to an approach."
        planning = container "Planning" "Turns an approach into bounded steps."
        context = container "Context compiler" "Fits the chosen evidence into the window that exists."
        interface = container "Semantic interface" "Offers a response shape the answer may negotiate."
        calls = container "Model calls and recording" "Asks providers, and writes down what was decided."
        allocation = container "Model allocation" "Which route to try first, where evidence supports one."
        capabilities = container "Capability fabric" "Tools and skills the run may reach for."
        harness = container "External harnesses" "Other coding agents driven as subordinate workers."
        verification = container "Verification" "Decides whether the work actually satisfies the task."
        recovery = container "Recovery" "Chooses what to do after a failure, by reasoning."
        history = containerdb "Run history" "Every stage seen, and what became of it."

        frontier -> practitioner "hands the open work to"
        practitioner -> orientation "starts by"
        orientation -> planning "settles enough to"
        planning -> calls "issues steps through"
        context -> calls "supplies the evidence to"
        interface -> calls "shapes the answer for"
        allocation -> calls "orders the routes for"
        calls -> capabilities "may reach for"
        calls -> harness "may delegate to"
        calls -> verification "submits the result to"
        verification -> recovery "escalates a failure to"
        recovery -> practitioner "returns a plan to"
        calls -> history "records every stage in"
        history -> allocation "is the only evidence for"
        verification -> frontier "closes or reopens"
    }
}
```

### What a run records, and what later runs read (DSL)

```text
# What a run records, and what later runs read
# level: component
# Generated from the typed model; do not edit by hand.
workspace {
    model {
        practitioner = container "Adaptive Practitioner" "Runs the kernel passes and owns every semantic decision."
        stage = component "Stage fingerprint" "Names one cognitive situation; its motif crosses domains."
        decision = component "Semantic decision" "Who decided, from which alternatives, and why."
        outcome = component "Decision outcome" "Joins a decision forward to whether it helped."
        choice = component "Choice contract" "One typed shape for every decision put to a model."
        template = component "Template negotiation" "The response shape is offered, and may be refused."
        recovery = component "Recovery" "Reasoning chooses what to do after a failure."
        ladder = component "Model ladder" "Which route to try first, fitted to what worked."
        convergence = component "Convergence measure" "Splits an arm off so agreement can be told from suggestion."
        credit = component "Outcome vector" "What a stage contributed, kept apart from how its run ended."
        store = containerdb "Stage store" "Append-only; indexed by exact identity, motif, and shape."
        lifecycle = component "Run stage lifecycle" "Loads the store at the start, closes it at every exit."

        store -> credit "grades each stage through"
        credit -> ladder "supplies evidence to"
        practitioner -> stage "names each step"
        practitioner -> decision "records every choice"
        decision -> outcome "is followed forward"
        practitioner -> choice "asks through"
        choice -> template "may negotiate the shape with"
        choice -> recovery "carries the failure decision for"
        stage -> convergence "assigns an arm from its identity"
        lifecycle -> store "loads and closes"
        stage -> store "is recorded in"
        store -> ladder "supplies prior shapes to"
        ladder -> practitioner "advises, and is not obeyed"
        outcome -> store "closes stages with the run's result"
    }
}
```
