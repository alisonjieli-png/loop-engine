# The Loop Node Constitution: harnesses as capability units

Status: synthesis, 2026-09-10. This document unifies everything the Loop
Engine repository, the sibling solvers (overnight, vigil, new_overnight_build),
and the embodiment experiments have built, discussed, and measured about one
question:

> What does a loop node need to carry, and how do external coding harnesses
> become swappable capability units inside it without becoming a second
> runtime?

It is the constitutional answer. It does not grant execution authority, and
it does not replace `AGENTS.md`, `architecture.yaml`, or the
[harness capability matrix](HARNESS-CAPABILITY-MATRIX.md). Where this document
and those authorities disagree, those authorities win. This file binds the
vocabulary everyone building harness integration uses from here.

## 1. The one runtime, and where the harness sits

```text
Operational runtime type
└── Loop  (the only executable graph vertex — constitution LE-NODE-001)
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile (practitioner.solver, intelligence.search, solution.pipeline, ...)
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Step profile: the ordered cognitive steps this Loop may run
    ├── Typed input and output contract
    ├── Loop and exit conditions
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the mode permits
    └── Run History records
```

A harness is none of these things. A harness is an **internal execution
substrate** that one Loop binds for a bounded stretch of semantic work — the
way the Model Gateway is a substrate for model calls and the Workspace
Backends are a substrate for file and command effects. The constitution's
rule stays absolute: no harness owns task authority, acceptance, promotion,
history, or the intelligence flywheel. A harness that owned those would be a
second runtime, which the constitution forbids.

## 2. Why harnesses at all (the measured case)

The cloud-harness campaign (30 harnesses live-tested on Ollama Cloud) and the
overnight line measured what harnesses actually buy:

- A harness ships the tool-invocation loop for free: when to call a tool,
  when to read a file, when to stop, how to recover from a failed call. The
  overnight line had to build none of that; the repo's own event parser
  originally got it wrong for months (hyphenated event names, zero tool-call
  accounting) because the loop was hand-rolled.
- Composed instances give exact tool grants structurally (agent frontmatter
  permissions), not by prompt.
- The harness is the larger variable: on one identical fix, aider 738 input
  tokens vs opencode 16,066 vs codex 88,080. Architecture races separated
  four arms; the harness choice moved 22x-100x.

So harnesses are worth wrapping. The wrapper — the loop node — is what keeps
them bounded.

## 3. The anatomy of a loop node (the full capability list)

Every loop node is seeded with a typed envelope and nothing else. The
envelope answers, before any model call: where am I, what do I have, what am
I allowed, how do I get more, and what shape must my answer take.

```text
NodePackage (the launch envelope — closed vocabulary, profile-switchable)
├── procedure          — the cognitive step's procedure text (P)
├── state              — horizon-rendered S: long (constitutional: task, gate,
│                        acceptance), medium (run knowledge: found/tried/decided),
│                        short (this step's live working set)
├── observation        — the latest verbatim observation (O)
├── contract           — the machine-checkable reply format (schema rendered
│                        into the prompt, reply validated, one re-ask)
├── tools              — the EXACT tool grant (also enforced in frontmatter)
├── plugins/skills     — declarable, list-then-load resources staged in-instance
├── intelligence       — references to what the four layers served this run
├── files              — references to staged files to read first
└── ledger             — LEDGER_ID + the closed pull vocabulary
```

Each part is **inline bytes or a ledger-resolvable reference** — never both.
Six transport mechanisms carry it (`argv`, `blob`, `env`, `stdin`,
`ledger-ref`, `hybrid`), all first-class and per-run switchable, because
transport choice is an A/B measurement, not a doctrine. The privacy floor
is the only gate: argv's `/proc` exposure is legal only on a declared
single-user A/B machine.

## 4. Static core architecture as the always-there floor

The three public capability ports are the parts of Loop Engine that every
node can reach, in-process or through the harness's plugin surface:

```text
LoopRuntimeContext
├── IntelligenceSearchRetrievalPort   — query the four layers, get typed refs
├── WebResearchPort                    — browser/search through Brave plugin
└── CustomPluginsPort                  — MCP, skills, registered tools
└── (internal mechanics: gateway, workspaces, approvals, stores, history)
```

The four persistent intelligence layers are non-negotiable and the flywheel
owns them:

| Layer | What it serves | Flywheel behavior |
|---|---|---|
| Context Intelligence | prompts, personas, heuristics, checklists, output contracts, decision schemas | candidate until approved; served as references first |
| Code Intelligence | verified functions, pipelines, packages, repos, tools | admitted with immutable body + contract + evidence; invoked, not just displayed |
| Runtime History & Solution Intelligence | fingerprints, runs, what worked/failed, repairs, measurements | replay and compare; prior-not-proof |
| User Feedback Intelligence | kept/rejected verdicts, corrections, approvals, vetoes | moves serving weights; scoped to a person |

Runtime Memory stays separate: run-scoped, temporary, one run. The layer
vocabulary is closed; a fifth layer is an owner decision, not a discovery.

**Query discipline**: search returns small typed references (LayerRef with
contract and digest); materialize loads a body only after selection and
permission; `intelligence.code.invoke` executes admitted code; retrieval
never promotes. This is the "just enough information" principle: the node's
opening envelope carries references and small criticals, never warehouses.

## 5. Cognitive steps and the Practitioner arc

The step catalog is the shared vocabulary of what a node does. The current
sixteen kinds all answer one bounded question each (orient, decompose, model,
evaluate, improve, audit, verify, decide-next, summarize, plan, observe,
standardize, ...) with exact tool grants and harness affinity per kind.

The full-task arc a Practitioner walks:

```text
Starting Practitioner
├── 1  intake: reconstruct the task and its acceptance (a folder with a
│       task.md referencing zipped CSVs IS the task; extraction is step 0)
├── 2  orient: what do I actually have — run real commands, quote real numbers,
│       never summarize from imagination
├── 3  query intelligence: four layers, before composition, hits ride the record
├── 4  plan/decompose: only after orientation; split when a verified failure
│       says so, never because the first try failed
├── 5  model/build: exact grants; contract-checked replies
├── 6  verify/evaluate: the gate is the only oracle; the auditor attacks the
│       measurement; completion signal stops the tree when acceptance holds
├── 7  record: patches to the shared ledger as this node's identity; usage,
│       tokens, elapsed on every call; failures retained
└── 8  promote candidates: never; the flywheel owns promotion
```

**Suggested outputs and fingerprinting** (the dual discipline): when the
engine knows the domain of a step's output — five variables, three
categorical, two numeric — it suggests that shape in the contract. This does
two jobs at once: the node's reply is checkable (admission has a schema to
enforce), and the *step fingerprint* (procedure + state-shape + input shape +
output shape, not prose) becomes the reuse key. Two steps with the same
fingerprint are the same work in different words; the flywheel can hand back
the code that worked and skip regeneration. Small steps, precise fingerprints,
cheap reuse — that is the whole economics of the loop node system.

## 6. Node-to-node communication: the ledger is the bus

Every node writes to one shared run ledger **as its own identity** — the
spawned-node crash-isolation measurements showed that a dying process takes
its own work only; siblings complete; the queue survives; history is durable.
The pull tool serves the closed vocabulary (`task`, `horizon_long|medium|
short`, `fingerprint`, `intelligence`, `memory`, `node_patches`,
`sibling_files`, `ledger_log`) with every query logged — the log itself is
the measured signal for improving the push.

```text
One run, many nodes
├── shared ledger: each node publishes patches under its node id
├── pull: named keys only, engine-authored read-only tool, never SQL from a model
├── push improvement loop: what nodes asked for that push didn't carry
│   becomes next runs' push composition
└── backend: SQLite today, DuckDB behind the same interface when runs
    reach millions of rows — the node never knows which answered
```

## 7. Multiple solutions: portfolios, canvases, and export

A node does not produce one response; it produces **candidates**. The
reactive output store keeps immutable candidate metadata, independent
evaluations, and policy-versioned ranks; the Canvas holds alternative
Solution Loop candidates and projects the selected ones into one
authoritative graph before execution. The export contract: independently
checked source, dependencies, tests, usage, digests — a human can replay the
solution without the engine. The overnight line's solution-export and the
reactive portfolio are the two live shapes of this; neither deletes a failed
candidate.

## 8. The harness unit contract (what we are building toward)

Everything above collapses to one design rule: **a harness unit is a
containerized, seeded, bounded instance of a coding agent that a loop node
launches, feeds a package to, and reads a checked reply from.**

```text
Harness unit (one node's execution)
├── containerize: bwrap or network-denied container; private XDG home;
│   no ambient credentials; telemetry off; relocatable state
├── seed: CoreBundle (pinned core context+skills+plugins) + InstanceGrant
│   (this activation's optional resources, tools, hydration ceiling) +
│   NodePackage (the envelope; six transports)
├── run: the harness's own tool/skill/MD-file heuristics — we do NOT rebuild
│   them; native tools denied or granted exactly per step
├── survive: supervisor kills at budget; a crash is one node's crash;
│   siblings, queue, and history survive (measured)
└── return: parsed events -> admission (schema, one re-ask) -> typed
    candidate; usage recorded; nothing the harness says is acceptance
```

The defaults: core plugins for the three capability ports staged in every
instance (a node that doesn't need them never calls them — offline tasks
simply never pull); tool grants off unless the step kind needs them; cheap
steps (decide-next, summarize, verify) on the gateway harness with no process
at all, because the ~8k-token instance overhead is waste there.

## 9. What the harness must provide vs never own

From the capability matrix, binding for harness integration work:

```text
The harness must provide (substrate)
├── headless machine interface: structured events, stdin prompts, exit codes
├── model transport plumbing: endpoint, usage reporting, output knobs
├── tool registry surface: exact disable lists, effect-mappable calls
├── bounded context injection and resume primitives
├── skills/plugins as declarable, list-then-load files
├── sandbox tolerability: relocatable state, no telemetry, no TUI assumptions
├── obedient process behavior: dies on signal, no daemons, final artifact
└── exportable complete event history

Loop Engine always owns (never delegated)
├── task and step fingerprints; compatibility and context fingerprints
├── the flywheel: harvest, eligibility, promotion, repair, quarantine
├── all four intelligence layers + run-scoped Runtime Memory
├── boundary registry, conformance, ontology
├── managed records, revisions, exports
├── preemptive budgets (harness may expose knobs; the host enforces)
├── replay, comparison, evaluation, acceptance
└── authority: permissions, approvals, verification, promotion
```

Fork patches therefore target only substrate gaps (veto hooks, event-schema
pins, budget kills, config isolation, telemetry removal). A fork patch
touching the owned column duplicates the runtime and is refused.

## 10. The experiment program (how we find out, in order)

Preliminary evidence favors OpenCode (and its forks) and Pi: containerized
per-node instances with composed permissions, proven live in the overnight
line and the instance-builder experiment. The frozen trial pipeline decides
the rest — data over review:

```text
T0  desk audit       — matrix rows, pinned versions, license, audit surface
T1  transport        — stub relay, headless run, event schema, usage parse (no spend)
T2  containment      — network-none, read-only workspace, scrubbed env,
                       credential probe must fail closed
T3  budget           — kill at N calls / wall time; no effect after kill;
                       native knobs vs supervisor kills as separate arms
T4  effects          — exact tool disable lists, veto refusal, effect classes
T5  frozen compare   — T1-T4 passers only: same tasks, same model, same
                       packets, independent evaluator; failures retained
```

Arms for the first frozen comparison: opencode 1.18.29 (control), pi (JSON-RPC
contract), codewhale (small Rust audit surface), crush 0.92.0 (native budget
knobs), gptme 0.33.0 (Python-auditable, budget flags). The task population:
frozen, machine-checkable postconditions (adapted-Kaggle shape: task text +
sealed data + holdout gate with a majority-class floor). Fairness rules:
identical prompts, packets, model, information; differences recorded, never
adjusted away.

## 11. The give-up rule (the zipped-CSV lesson)

A harness that sees `task.md` referencing `train.csv`, finds no such file,
and reports failure — when `data.zip` sits right there — is not an
unattended solver. The loop-node contract makes resolution structural:

1. The orientation procedure REQUIRES attempting extraction when referenced
   files are absent and archives are present (a human does this instantly).
2. The observation channel carries verbatim command output; a node that
   gave up must show the commands it actually ran.
3. A failed first attempt is a patch, not a verdict: classify the failure
   (missing input? wrong contract? infrastructure?) before retrying or
   splitting — the classification decides, never the clock alone.
4. The completion signal is engine-owned: the tree stops when the real gate
   passes, not when a node says "done" — and it does not stop while the
   gate is red just because a node stopped trying.

## 12. Standing constraints (what never changes)

- Every executable vertex is a Loop. Harnesses are adapters; MCP servers,
  skills, plugins, tools are adapters. None gain graph-vertex status.
- Harness completion is never task acceptance; exit zero is never success.
- Candidate until approved: intelligence, code, outputs — no retrieval,
  score, or self-report promotes anything.
- No silent ceilings or invented caps; budgets are typed and enforced
  before effects; missing usage is unknown, never zero.
- Failures and false acceptances are retained with the prominence of
  successes; the denominator is always reported.
- Published comparisons cite exact population, model, version, evaluator,
  and limitations; one passing population is never a universal claim.
- Nothing in this document authorizes spend, execution, or promotion. The
  authorities in `architecture.yaml` and the contract index govern.

## Provenance

Synthesized from: the constitution and contract index; the harness ADRs
(REALIZATIONS, HOST-OWNED-EXECUTION); the capability matrix and T0-T5 trial
protocol; the embodiment build results and catalog (6 runnable arrangements,
7 planned, 30 axis experiments); the cloud-harness campaign (30 live-tested);
the overnight line's four intelligence ports, horizons, ledger pull, NodePackage
transports, and 1,000-task corpus; the live instance-builder experiment
(CoreBundle/InstanceGrant/InstanceSelection, read+skill qualified bridge);
the novel-task campaign and its audit lessons (oracles are code; prompt-oracle
contradictions; false-acceptance survives 10/10 verification); the reactive
crash-isolation measurements; and the give-up observation that started this
round.
