# LLM-first universal solving

Loop Engine treats the task domain as unbounded. A new task does not need a
prewritten domain branch before the Practitioner can begin reasoning about it.

The first implementation priority is the model-led path:

```text
Unseen task
└── Starting Practitioner Loop
    ├── orient with an authorized language model
    ├── classify ambiguity and ask only material questions
    ├── inspect selected context, intelligence, tools, and capabilities
    ├── propose, compare, and select concrete next actions
    ├── determine how to reuse, compose, or build a capability
    ├── materialize model output into typed files, commands, or requests
    ├── execute through permissioned Solution Loops
    ├── inspect artifacts and runtime evidence
    ├── diagnose failure and propose an executable repair
    └── continue, ask, return, abstain, or stop honestly
```

The language model supplies semantic interpretation, hypotheses, plans, code,
diagnosis, and task-conditioned verification proposals. The runtime supplies
permissions, provider routing, budgets, deadlines, workspace confinement,
tool execution, artifact registration, Run History, deterministic checks, and
terminal authority.

The model cannot grant itself access, pretend an unavailable capability is
installed, treat a plan as execution, or claim completion without accepted
evidence.

The Practitioner steps are control points, not a task template. They ensure
that every run preserves the task, makes an explicit decision, performs work,
checks the result, and records why it continued or stopped. They do not choose
the domain, output, method, template, provider, or answer before the model sees
the task.

## Resolution modes

```text
Loop resolution mode
├── non_deterministic
│   └── LLM-first path for new and unbounded tasks
├── hybrid
│   └── use a model-selected reviewed capability with model reasoning where needed
└── deterministic
    └── run a verified exact capability without semantic model work
```

When a model route is authorized, public `solve` defaults to
`non_deterministic`. Templates, prior solutions, fingerprints, and exact
capabilities appear as candidates in model context. They do not select the
task or method. The model may choose one, modify one, combine several, or build
something new. Work without a model remains deterministic and returns an
honest capability gap when no exact executor exists.

These modes are internal runtime facts and Run History dimensions. A normal
user does not choose one. Public solve selects the model-led path when a model
is available. If the model chooses a reviewed exact capability, the execution
of that capability may be recorded as deterministic. The fingerprint never
replaces semantic orientation by itself.

Interaction is a separate policy. The default returns material questions. The
advanced `--unattended` option means the current activation must abstain rather
than wait for an answer. It does not change how intelligently the Loop reasons.

## Candidates and hard gates

Loop Engine gives the model candidates instead of preselecting task semantics:

```text
Model candidate context
├── perspectives, guidance, and question sets
├── templates, skills, capabilities, and prior solutions
├── Intelligence references and source files
├── Solution and recovery candidates
└── generation strategies
        ↓ explicit model selection
Runtime validation
├── user instructions and authority
├── capability availability and typed contracts
├── permissions, secrets, and workspace confinement
├── independent verification
└── terminal success rules
```

Step affinity, lexical score, retrieval score, fingerprint similarity, and
evaluation metrics help the model compare candidates. None of them may choose
the task meaning, method, or winner. If a model response conflicts with itself,
the runtime returns validation findings for model repair. Python does not
rewrite the semantic answer.

Search, generation, and spawned work have no implicit numeric ceiling. A user,
provider, or authorized policy may set one. Safety boundaries remain enforced
even when no work ceiling is configured.

## Questions and feedback

A material uncertainty returns `BLOCKED_MATERIAL_INPUT` with one or more typed
`MaterialQuestion` records. Each record includes an answer slot. Feedback is a
separate input on the next activation, so the original task remains unchanged.

```bash
loop-engine solve --file task.txt --quickstart \
  --task-feedback 'required_destination=./results/final.md'
```

Delegated choices, safe defaults, derived values, research questions, and
nonmaterial preferences do not interrupt the run.

## Task files and external data

`--file task.txt` reads the instruction text at intake. The Practitioner receives
that captured text with its digest and origin. The origin is provenance, not an
unread dataset, and no second file inspection is required to recover the task.
Changing the file after intake does not change the captured instruction.

`--dataset` and `--repository` are different: their referenced contents still
require explicit source-to-model authority and selected materialization. A path
mentioned in task text grants no access by itself.

## Source code is a deliverable

A code-only task can return authored modules and tests after they are written
and verified. It does not need an invented report file or a script whose only
purpose is to write another script.

The project contract separates authored `files` from command-produced
`expected_artifacts`. The latter may be empty when a zero-exit verification
command is declared. After execution, the runtime checks the authored bytes
against their manifest digests, checks Python syntax where applicable, and
requires the verification command to have passed. Returned source artifacts
are explicitly marked `authored_source`, not command-produced outputs.

Declared computed outputs must still exist and pass their checks. An authored
file cannot also satisfy a command-produced-output declaration. These checks
establish materialization and execution evidence; independent task evaluation
is still needed to catch incorrect code or weak generated tests.

## Learning and future shortcuts

Repeated use should make the system cheaper without narrowing the task domain:

```text
Verified Run History
├── task and context fingerprints
├── reviewed reusable capability candidates
├── successful plan and Solution Canvas candidates
├── failure and repair patterns
└── provider, cost, latency, and verification observations
        ↓ independent review and promotion
Future task
├── model receives exact verified reuse candidates
├── model may parameterize a candidate when safe dimensions differ
├── model may modify or compose candidates when evidence supports it
└── model may build a new approach when reuse is uncertain or unavailable
```

Fingerprints are context and search evidence, not proof that two tasks are
equivalent or permission to skip orientation.
New learned records remain candidates until independent review. No producer
may promote its own lesson or capability.

## What must be proven

Offline structured fixtures prove schemas and runtime plumbing. They do not
prove that a language model can solve an unseen task. Generalization claims
require frozen source-disjoint holdouts, an authorized live provider, real
artifacts, artifact inspection, repair evidence, complete Run History, and no
generic source edits between tasks.

Unsupported physical effects or missing tools remain honest capability gaps.
Universal solving means universal task orientation and governed attempts, not
pretending that every possible external capability is already installed.
