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
    store[("Stage store<br/><small>Append-only; indexed by exact identity, motif, and shape.</small>")]
    lifecycle("Run stage lifecycle<br/><small>Loads the store at the start, closes it at every exit.</small>")

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
        store = containerdb "Stage store" "Append-only; indexed by exact identity, motif, and shape."
        lifecycle = component "Run stage lifecycle" "Loads the store at the start, closes it at every exit."

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
