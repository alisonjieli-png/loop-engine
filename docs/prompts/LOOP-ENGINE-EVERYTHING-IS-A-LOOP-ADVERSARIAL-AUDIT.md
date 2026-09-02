# Everything Is a Loop: adversarial architecture audit mandate

Paste this prompt into a fresh Codex, OpenCode, Claude Code, Hermes, or
equivalent session rooted at the Loop Engine repository. It is an audit, not a
build order. It asks several hundred questions about one claim and refuses to
accept any answer that is not backed by source, tests, receipts, or a probe
you ran yourself.

The claim under audit:

> Every operationally executable thing in Loop Engine is one canonical `Loop`.
> Data stays passive and typed. The Loop is a general enough unit of work that
> it can represent a value, a function, a stream, a service, a model call, a
> human answer, a supervisor, an experiment, and a whole solution graph, and
> it is therefore a candidate for the last abstraction a computation and
> learning fabric needs.

The owner uses "loop node" colloquially. The canonical repository term is
`Loop`. A parallel `LoopNode` class hierarchy is prohibited by the
architecture. Where this document says "Loop", the owner's spoken phrase is
"loop node". Do not create a `LoopNode` class because this document mentions
the phrase.

---

## 0. How to run this audit

### 0.1 Progressive loading is part of the test

This file is long. Do not place the whole file into a single model call, and
do not re-send it on every turn. Load section 0, the scoring rules in
section 2, and one question bank at a time. An auditor that overflows its own
context while auditing a context-compilation architecture has already found a
defect in itself. Record how many tokens you spent per section.

### 0.2 Two phases, one report

**Phase A: read-only.** Reconstruct behavior from source, tests, schemas,
saved Run History, examples, and probes you execute in a scratch directory.
Documentation, comments, README claims, ADRs, and this prompt are claims, not
evidence. Green tests are evidence only for what the test body actually
asserts; read the assertion before crediting it.

**Phase B: optional bounded repair.** Only after the Phase A report is
durable, and only for findings you rated CONTRADICTED or ABSENT at severity
critical or high, may you change code. Every repair needs a regression test
that fails on the pre-repair tree. Do not commit, push, tag, publish, or change
provider credentials or billing. Other agents may be active in the same
worktree; check `git status` before and after every edit and never revert a
file you did not change.

### 0.3 Authorities to bind before answering anything

Read these first and cite them by path and symbol. They are discovery seeds;
verify each at the exact commit you audit and record the commit hash:

- `AGENTS.md`: one operational runtime, no `*Node` classes, passive records,
  Canvas has no mode of its own, no silent replay of committed effects.
- `docs/architecture/CONSTITUTION.md`: LE-NODE-001 through LE-NODE-009,
  LE-CONFIG, LE-INTEL, LE-PERM, LE-TRUST, LE-VERSION, LE-RUNTIME, LE-GOV.
- `architecture.yaml`: `execution_rule:
  every_semantic_value_and_transformation_is_a_logical_loop`,
  `default_atomic_mode`, `value_contract`, `intrinsic_kernel`.
- `terminology.yaml` and `docs/architecture/GLOSSARY.md`.
- `src/loop_engine/loop/recursive_loop.py`: `Loop`, `_LoopMeta`,
  `LoopConfig`, `LoopLedger`, `StepOutcome`, `LoopResult`.
- `src/loop_engine/loop/loop_definition.py`, `loop_contract.py`,
  `kernel.py` (`KERNEL_NODES`, `_MAX_NON_PROGRESS_PASSES`),
  `kernel_runtime.py`, `atomic_primitives.py`, `intrinsic_kernel.py`.
- `src/loop_engine/core/model_gateway.py`, `context_budget.py`,
  `adaptive_practitioner*.py`, `generated_project.py`, `run_history*`.
- The graph authority (`LoopGraphDefinition`), the reactive records
  (`CandidateOutput`, `CandidateEvaluation`, `OutputPortfolioSnapshot`),
  the flywheel modules, the semantic runtime modules, the external harness
  boundary, Studio, and `run_playback.py`.
- Related prompts in `docs/prompts/`: the strict primitives mandate, the
  superseded LoopNode specification mandate, the adversarial component
  review, and the product definition pack if it has been placed in the
  repository. Note where those documents contradict each other.

### 0.4 What "aggressive" means here

Aggressive does not mean rude, and it does not mean rewriting the system. It
means: assume every claim is false until a probe proves it; prefer the
question that would embarrass the architecture; count things instead of
describing them; separate "the code contains a class named X" from "X does
what the docs say under adversarial input"; and never let a beautiful idea
excuse a missing receipt. If the thesis survives this audit it deserves to.

---

## 1. The thesis, stated so it can be attacked

An audit of an abstraction has to say what the abstraction claims to remove
and what it must never re-introduce. Write your own version of this section
in the report, with citations, before answering the question banks. Use the
outline below; disagree with it where the code disagrees.

### 1.1 The abstraction ladder the owner points at

Each historical level kept one uniform substrate and removed one class of
decisions from the programmer:

| Level | Uniform substrate | Decisions removed | Decisions left behind |
|---|---|---|---|
| Machine code and assembly | the word, the register, the address | none: you name registers and jump targets yourself | everything |
| C | typed memory, functions, expressions | register allocation, instruction selection, calling conventions | memory ownership, manual dispatch, manual error propagation |
| C++ | objects with lifetimes, generic types | polymorphic dispatch by hand, resource cleanup by hand, per-type code duplication | ownership rules, build model, undefined behavior |
| Python | everything is an object (functions, classes, modules, `type` itself) | memory management, static bookkeeping, most build ceremony | control flow, orchestration, retries, verification, memory across processes, how humans, models, and tools are combined |
| Loop | every operation is a bounded, typed, described, replayable unit of work with a declared mode, relationships, evidence, and lifecycle; data stays passive | hand-written orchestration, ad hoc retry and verification, prompt glue, one-off supervisors, lost provenance, one-off reuse | to be audited |

The Python analogy is precise in one way and loose in another. It is precise
because Python's power comes from reflexive uniformity: `type(type) is type`,
a function is an object, a class is an object, so one set of tools (getattr,
pickling, introspection, decorators) works on everything. It is loose because
Python achieves uniformity by letting you subclass `object`, while Loop Engine
achieves it by refusing subclassing (`_LoopMeta`) and pushing all variation
into data (`LoopDefinition`, profiles, modes, relationships). The closer
analogies are "everything is a file" (Unix), "everything is an s-expression"
(Lisp), "everything is a process" (Erlang), and "everything is a reconcile
loop" (Kubernetes controllers). The audit must decide which analogy the code
actually earns.

### 1.2 What the Loop claims to be able to represent

The owner's list, which the question banks turn into probes:

- run once and behave exactly like a straight function;
- run many times with a loop condition and an exit condition;
- house logic, deterministic or model-led or mixed;
- carry typed input and output ports and typed edges;
- carry a description that a search engine and another Loop can read;
- have several ways of running (deterministic, hybrid, non-deterministic),
  chosen per instance, with a path to distill one into another;
- own the four fundamental data actions: store, transfer, transform, compute;
- communicate with other Loops on the same machine and across machines;
- host supervisors, experiments, checklists, shortcuts, and human answers
  without a second runtime;
- scale to a fabric of many machines without becoming an immortal process.

### 1.3 What the abstraction must never re-introduce

- a second executor hiding inside a record, index, decorator, store, Canvas,
  Series, queue, or scheduler;
- a step outcome that was not produced by the step (fabricated recovery,
  synthetic completion, a "complete" label on a structural boundary);
- control flow or code hidden in an edge;
- a mode explosion (more than three canonical modes) or a role explosion
  (role-specific subclasses);
- a runtime whose ledger costs more than the work it records without a
  physical fusion path that preserves logical history;
- claims of universality that rest on Turing completeness alone. Turing
  completeness is cheap; every language on the ladder has it. The claim
  worth defending is that the unit is the right size and shape for reuse,
  verification, distillation, and distribution.

### 1.4 Lineages the architecture must position itself against

For each lineage below, the report must state in one or two sentences what
Loop Engine takes from it, what it adds, and where the code proves the
addition. "We are different" without a probe is not an answer.

- lambda calculus and the function as the unit of composition;
- the actor model (Hewitt) and Erlang/OTP supervision trees: asynchronous
  messages, let-it-crash, restart strategies, per-process mailboxes;
- dataflow and Kahn process networks: typed channels, deterministic
  composition, backpressure;
- Petri nets and CSP: places, transitions, rendezvous;
- coroutines and generators: the same body running once or many times;
- Unix processes and pipes: one uniform vertex type and typed-by-convention
  edges;
- durable execution engines (Temporal, Cadence): event-sourced replay of
  workflow code, idempotent activities, retry policies as data;
- DAG schedulers (Airflow, Dagster, Prefect, Spark): task graphs, retries,
  lineage, why they needed a separate orchestration layer at all;
- Kubernetes controllers: observe, diff, act until converged, declared
  desired state, reconcile loops as the universal unit;
- production systems and cognitive architectures (Soar, ACT-R): chunking as
  the distillation of reasoning into rules, exactly the owner's "does this
  need non-deterministic intelligence or can it be if-thens";
- case-based reasoning (retrieve, reuse, revise, retain): the reusable
  capability flywheel's ancestor;
- evolutionary and program search (genetic programming, FunSearch,
  AlphaEvolve) and AI experiment engines (AI co-scientist, automated
  scientist systems): hypothesis, run, measure, select, mutate;
- Bayesian optimization and bandits: choosing a starting point and a
  "random sprout" rate from prior evidence;
- bounded rationality, satisficing, and checklists: the human colleague who
  does not carry a giant reasoning engine and still finishes the task;
- information theory: minimum description length as the criterion for a
  good shortcut; Kolmogorov complexity as the limit of distillation; entropy
  of a task fingerprint as the estimate of how much reasoning is left;
- current coding harness loops (Codex loop and goal commands, Claude Code,
  OpenCode, Hermes) and the supervisor and contract layers people stack on
  top of them. The owner calls these band-aids. The audit must say whether
  Loop Engine is a foundation or a taller band-aid, with a same-task
  benchmark as the evidence.

---

## 2. Scoring rules

Answer every question with a verdict, evidence, and one sentence. Nothing
else. The report is a table, not an essay.

| Verdict | Meaning |
|---|---|
| PROVEN | You ran a probe or test, it passed, and you cite the receipt, run id, digest, or test name. |
| IMPLEMENTED_UNPROVEN | Source exists that intends this; no probe demonstrates it under adversarial input. |
| PARTIAL | Some of the behavior is proven; state exactly which part is missing. |
| ABSENT | No source, test, or record addresses it. |
| CONTRADICTED | Documentation, prompt, or comment claims it and the code or a probe shows otherwise. Always severity high or critical. |
| NOT_APPLICABLE | The question does not apply at this commit; say why. |

Evidence forms accepted: `path:symbol`, `path:line`, test name, saved run id
and event index, artifact digest, exact command plus exit status, probe
script path plus its output. Not accepted: "the README says", "the design
intends", "this is handled by the architecture", a green test whose body you
did not read.

Severity: critical (the invariant is violated or a claimed safety property is
false), high (a headline capability is contradicted or absent), medium (a
capability is unproven or partial), low (naming, docs, hygiene).

Count everything you can count: events per operation, bytes per event,
tokens per call, model calls per task, Loops per solve, lines of glue outside
the Loop runtime, number of places that branch on a provider name string.
A number with a measurement method beats an adjective.

---

## 3. Question bank: the invariant itself

Every question here is about LE-NODE-001 through LE-NODE-009 and the passive
data rule. Probe the code, not the constitution.

**3.1** Enumerate every class in `src/` that has a method which runs
external code, contacts a provider, executes a subprocess, writes outside a
scratch directory, or schedules work. For each: is it `Loop`, is it called
from inside a `Loop` step, or is it a second executor? List the ones that
are neither.

**3.2** Does `_LoopMeta` refuse subclassing at class creation? Show the test.
Then show what happens with `type("X", (Loop,), {})` and with a class that
wraps a `Loop` and re-exports `run`. Is wrapping the loophole that
subclassing closed?

**3.3** Which passive record types carry methods that do work rather than
compute a projection of their own fields? A `to_dict` is a projection. A
`run`, `execute`, `apply`, `dispatch`, `fetch`, `write` on a record is a
hidden executor. Grep for them and read each one.

**3.4** Is `LoopGraphDefinition` the only executable graph authority? Find
every place that iterates a sequence of callables or steps and executes them
in order. Is each one a Loop step handler, or a private scheduler?

**3.5** Do edges carry code? Inspect the edge and port records. Can an edge
declare a transform, a default, a coercion, or a script? The rule says
adapters are explicit Loops. Probe with a graph whose edge tries to coerce a
type and confirm refusal.

**3.6** The Practitioner kernel runs ten `KERNEL_NODES` inside the owner
Loop's `act` step. The owner's other steps are labelled structural
boundaries. Is a kernel pass a Loop, a step, or a private loop inside a
step? Count how many `Loop` instances a single Practitioner pass creates and
how many things that behave like steps it executes without a Loop identity.
Is that within LE-NODE-008, or is it the exact "second orchestration
kernel" the constitution forbids? Argue it from the code.

**3.7** `architecture.yaml` says every semantic value and transformation is a
logical Loop. LE-NODE-008 says primitives stay inside a Loop unless they
need independent governance. Which rule wins at the atomic primitive
boundary, who decided, and where is the decision recorded? Does
`atomic_primitives.LoopValue` satisfy both readings or neither?

**3.8** Measure the cost of the strict reading: events, bytes, and wall time
per string join through an atomic Loop versus native. Report the ratio. Is
`physical_fusion_requires_logical_history` implemented anywhere, or is it a
flag with no consumer? If it is unimplemented, the strict reading is a cost
without its promised optimization; say so.

**3.9** Can a Loop run exactly once and be indistinguishable from a function
to its caller? Write a pure function, wrap it as a deterministic Loop, and
compare outputs, exceptions, and types over 1,000 random inputs. Then compare
the ledger cost. Report both.

**3.10** Can the same `LoopDefinition` run many times with a loop condition
and exit condition without changing code? Show the condition fields, show
the test that exercises a loop that runs 0, 1, and N times, and show what a
non-terminating condition does. Is the guard a ceiling, a non-progress
detector, or both?

**3.11** Are roles fields or types? Is there any `isinstance` or class-name
branch on Practitioner, Intelligence, or Solution anywhere in `src/`?

**3.12** Are modes fields or types? Is there any place where the deterministic
path and the model-led path are different classes, different runtimes, or
different call graphs rather than the same `Loop.run` with a different
handler policy?

**3.13** A Canvas or Series must not have its own mode. Find every Canvas,
Series, portfolio, and graph record and confirm none stores or infers an
execution mode for itself. Then confirm none of them executes.

**3.14** Relationships: Starting, Spawned by, Queried by, Retrieved by,
Connected from. Are these the only operational relationships? Where are the
semantic relationships (decomposes, alternative_to, verifies, supersedes,
harvested_from) stored, and is any of them being used as a runtime entry
relationship by accident?

**3.15** Does every Loop name its role, profile, mode, ports, loop condition,
exit condition, and relationships as AGENTS.md requires? Pick ten Loops from a
saved run and check each field is present and non-default.

**3.16** Historical `kind: loop_node` records: is the migration into
`LoopDefinitionRecord` the only reader? Grep for any other reader.

**3.17** Is there any `*Node` class active in first-party code? Include
generated code, examples, integrations, devtools, and tests.

**3.18** The compatibility constructor can coerce a requested role or mode.
Confirm the coercion is recorded on the init and spawn events and that a
caller can refuse coercion. Probe: request `role=solution,
execution_mode=model_led` where the profile demands otherwise and read the
event.

**3.19** Can a Loop fabricate an outcome? Probe: a step whose handler fails
under a model-led mode with a deterministic fallback. Read the recorded
outcome text. Then read the terminal code. If the terminal is ACCEPTED under
`steps_complete` while the only step failed, decide whether that semantics
is honest and where it is documented.

**3.20** Can a Loop run forever on identical failures with no ceiling? Probe
with `accepted_success` and a handler that fails identically. Report
iterations, events, and the terminal code.

**3.21** Can spawn recursion run away? Probe without `max_depth`. Is the
refusal typed, and does the error name the real cause?

**3.22** Where does the reflexive base sit? Is the thing that runs a Loop a
Loop? Is the scheduler a Loop? Is the ledger writer a Loop? Is the
qualification of a Loop definition itself a Loop? For each "no", is the
exception written down, and is it the same exception LE-NODE-008 grants?

**3.23** What is the type of a Loop, in the Python sense of `type(x)`? Is it
one class with one `run`, or does `run` dispatch to per-role or per-mode
private functions that are subclasses in disguise? Draw the actual call
graph of `Loop.run` from source.

**3.24** Count lines of orchestration code that live outside `Loop.run` and
its handlers: CLI glue, solve runtime, kernel runtime, reactive worker,
Studio server, external harness adapters. What fraction of the repository's
control flow is inside the abstraction it claims is universal?

**3.25** Find every `while True`, `for attempt in range`, `retry`, and
`sleep` in `src/` that is not inside a Loop step handler. Each one is a
candidate second loop. Classify each as: inside a Loop, transport plumbing
that belongs below the Loop, or a violation.

---

## 4. Question bank: the four fundamental data actions

The owner names store, transfer, transform, compute. The audit asks whether
each is Loop-owned or leaks into stores and helpers.

**4.1** Store: when Run History is written, which Loop owns the write? When a
context artifact is stored by digest, which Loop owns it? If the answer is "a
service", is the service called from inside a Loop step, and is the write
recorded as an event of that Loop?

**4.2** Retrieve: when a prior solution, capability, or intelligence record is
fetched, which Loop performs the retrieval, and does the Retrieved by
relationship appear in the ledger?

**4.3** Transfer: when data moves between two Loops, is the move a typed edge
with a recorded port-to-port binding, or a Python object passed through a
closure? Probe a two-Loop graph and read the events.

**4.4** Transfer across processes: can a Loop activation be serialized,
shipped to another process, executed there, and its ledger merged back with
the hash chain intact? Probe it with two processes on one machine.

**4.5** Transform: is a pure transformation a Loop, an atomic Loop, or a
helper? At what size does the architecture say a transform earns a Loop
identity? Cite LE-NODE-008 and the atomic primitives decision, then show
three examples of each classification from the code.

**4.6** Compute: when a model is called, is the physical call a Loop
(`model_loop` per attempt) and is the semantic use of the answer a separate
Loop? Count Loops per model call in a saved run.

**4.7** Human answer: when a material question blocks a solve and the user
answers later, is the answer's arrival a Loop activation with a Queried by
or Connected from relationship, or a CLI flag mutating state?

**4.8** Effects: is every workspace write, command execution, network call,
and external effect declared, approved, and recorded by a Loop, and can a
Loop claim an effect it did not perform? Probe by forging an approval record
and confirm refusal.

**4.9** Idempotency: can the same Loop activation be replayed without
repeating an external effect? Which record carries the idempotency key, and
which code checks it?

**4.10** Which of the four actions has no Loop-owned path at all today? Name
it plainly.

---

## 5. Question bank: typed ports, edges, descriptions, handshakes

**5.1** What is the type system of a port? Is it a JSON Schema, a Python
type, a semantic role string, or a mix? Can two ports with compatible schema
but different role names connect without an Adapter Loop? Should they?

**5.2** Are port types validated before execution, at execution, or never?
Probe a graph with a deliberately mismatched producer and consumer.

**5.3** Can a description be read by a machine? Is there one description
field, or several (summary, docstring, semantic_summary, embedding_text)?
Which is authoritative for search, and which for a model reading the Loop?

**5.4** Do Loops have versions in the V1, V1.1 sense the owner wants? Show a
definition's version field, its digest, and the rule for when a change
requires a new version versus a new digest.

**5.5** Handshakes: when one Loop consumes another's output, does either
side check version and schema compatibility? Is there a `CapabilityHandshake`
or equivalent record, and is it ever produced at runtime, or only in tests?

**5.6** Where is the central registry of schema versions? Grep for `/v1/`,
`_v1`, `record_type.*v1` and count the places a version string is spelled by
hand. Is there one authority or dozens?

**5.7** Are aliases ever authority? Find any place an alias string ("Quad
Code", "Open Quad", a provider nickname, a legacy kind) is compared to
select behavior.

**5.8** Parameter objects: list every public function or constructor in
`src/loop_engine` with more than five parameters. For each, is there a typed
request object it should take? The owner asked for parameter objects, not
eight-argument functions.

**5.9** Can a port carry a reference instead of a body, and does the runtime
hydrate lazily? This matters for the context compiler and for transfer
across machines.

**5.10** Is there a typed way to say "this port is optional", "this port is a
stream", "this port is a set of candidates"? Or is everything one value?

---

## 6. Question bank: modes and the distillation ladder

The owner's central bet is that non-deterministic reasoning can be distilled
into hybrid and then deterministic Loops, and that most tasks end up as
checklists.

**6.1** Show one Loop that exists in all three modes for the same contract,
with a test that runs all three and compares outputs.

**6.2** Show the path from a non-deterministic success to a deterministic
realization: reuse opportunity, candidate, qualification, promotion, exact
retrieval, zero-model execution. Run it end to end. Report model calls on
the warm path. Zero is the only passing number.

**6.3** The elbow-method test. Build a small EDA task where a
non-deterministic Loop chooses the number of clusters by reading a plot or a
table, then show a deterministic Loop that reproduces the choice from the
same data with an elbow rule and zero model calls. Is the deterministic
version a promoted realization of the same contract, or a separate Loop with
a different identity? The owner's thesis requires the former.

**6.4** How does the system decide a task does not need non-deterministic
intelligence? Is there a policy, a fingerprint threshold, a historical
success rate, or a human flag? Cite the code that makes the decision and the
receipt that records it.

**6.4b** Checklists. A human colleague runs a checklist: look at the data;
nothing is weird; move on; something is weird; ask what to do. Is there a
Loop profile that encodes "gate on anomaly, escalate only when the gate
fires"? Show it and its receipt when the gate does not fire (should be zero
model calls) and when it does.

**6.5** Hybrid variations: are they policies and stages under one `hybrid`
mode, or has a fourth mode appeared under another name (`semantic`,
`assisted`, `interpreted`)? Grep the mode vocabulary at every layer: runtime,
settings, records, Studio, CLI.

**6.6** Does the semantic runtime (implementationless contracts) run inside
`Loop`, or beside it? Trace one semantic invocation from contract to commit
and name every function that is not a Loop step.

**6.7** Trust states: Candidate, StructurallyValid, ContractValid, Verified,
EffectAuthorized, Committed. Can code outside the verifier construct a
Verified value? Try it.

**6.8** Can a model repair its own format failure and have the repaired
answer counted as zero-model? It must not. Show the accounting.

**6.9** Where is the record that says "this task region has been solved
deterministically N times with success rate p, so skip the model"? If it
does not exist, the distillation curve the owner expects cannot be measured.

**6.10** Physical fusion. When adjacent deterministic Loops are fused for
speed, is the logical history reconstructable? If fusion is not implemented,
what is the measured cost of not having it on the strict-primitives path?

**6.11** Does a deterministic Loop ever call a model "to confirm"? Grep the
deterministic handlers for gateway access.

**6.12** Does the runtime know when a deterministic realization is stale
(dependency drift, data drift, schema drift) and fall back to hybrid rather
than returning a wrong answer with a receipt that says deterministic?

---

## 7. Question bank: shortcuts, fingerprints, and the deterministic front end

The owner's example: "predict the likelihood of a snowstorm tomorrow"; the
system should recognize a solved task region and answer "zero, it is summer"
without reasoning, and for hard tasks should pick starting points from
histograms, n-grams, and semantics.

**7.1** Is there a task fingerprint? What fields does it have, and which are
typed compatibility dimensions versus text projections? Can text similarity
alone select a solution branch? It must not.

**7.2** Exact identity and digest matching (Stage 0): probe with a
byte-identical repeated task. Model calls on the second run?

**7.3** Paraphrase (Stage 1 and 2): probe with a reworded compatible task.
Which stage matched: structured facets, lexical, n-gram, MinHash, embedding?
Cite the retrieval receipt.

**7.4** The "zero because it is summer" case: does the system have a notion
of a precondition or context fact that makes a prior answer still valid?
Where is the invalidation rule stored, and what happens when the fact
changes?

**7.5** Negative evidence: when a shortcut is wrong, is the failure recorded
against the fingerprint region so the shortcut is not taken again blindly?

**7.6** Histograms and multivariate histograms: is there any statistical
profile of tasks, inputs, or outcomes that informs a starting point? If not,
say ABSENT and estimate the smallest record that would enable it.

**7.7** n-grams and LSH: is any lexical blocking used before embeddings, or
does search go straight to a vector index? Cost per query in tokens and
milliseconds for each channel.

**7.8** Starting settings: when a new task matches a region, does the system
inherit the region's best-known mode, budget, context policy, and model
tier? Show the record and the receipt.

**7.9** Random sprouts: is there an exploration rate, a recorded seed, and a
budget for trying a non-incumbent starting point on purpose? Is every sprout
recorded as an experiment with its outcome so the rate can be tuned?

**7.10** Does the fingerprint include the environment (dependency digests,
provider, model) so a "solved" region on one runtime is not assumed solved on
another?

**7.11** Can a user see, in Studio or the report, why the system chose a
shortcut and what it would have cost to reason from scratch? Estimated versus
realized savings must be labelled separately.

---

## 8. Question bank: streaming intelligence and editing the solution canvas

**8.1** When a solution exists and a new error arrives, does the next model
call receive the existing solution plus the error and produce an edit, or
does it start from nothing? Read the packet assembly and show the fields.

**8.2** Is the Solution Canvas a projection or a runtime? Confirm no code
path executes from a Canvas record.

**8.3** Which compatibility checks on a proposed edit are deterministic (type
check, schema check, test run, import check, effect check) and which are
delegated to a model? List both.

**8.4** Is a proposed edit a candidate until verified, and does a rejected
edit leave the incumbent untouched?

**8.5** Streaming: can a Loop consume partial model output and act before the
response completes, or is "streaming" only a transport detail? If only
transport, say so.

**8.6** Context reuse: across consecutive calls in one run, how much of the
packet is byte-identical? Measure it on a saved run. Is the duplicate part
deduplicated, referenced by digest, or re-sent?

**8.7** Is the packet bounded before it leaves the process, and is the
refusal typed when the estimated input plus requested output exceeds the
route's declared context? Probe at the boundary: one token under, one token
over.

**8.8** Are trims recorded with digests so a reviewer can recover what the
model did not see? Show the event and the artifact.

**8.9** Does the assembled packet include the same static instruction text
on every call? Count bytes of unchanging system text per call and per run.

**8.10** Can the Practitioner ask "does this already exist?" as a
deterministic retrieval step before it spends a model call on "what is
next"? Trace the actual order of operations in one pass.

---

## 9. Question bank: deterministic tools and hooks

The owner wants deterministic tools and hooks callable by both model-led and
deterministic Loops, with the same contract.

**9.1** What is the tool ABI? Is there one typed interface that a
deterministic step and a model tool call both go through? Or two?

**9.2** Do tool invocations from a deterministic Loop and from a model-led
Loop produce the same receipt shape? Probe one tool both ways and diff the
events.

**9.3** Effect declaration: can a tool run without a declared effect class?
Try it.

**9.4** Hooks: LE-LIFECYCLE says no fixed global hook list. What is the
mechanism, is it a Loop, and can a hook execute code that bypasses effect
approval? Try to register one that writes outside the workspace.

**9.5** Which deterministic checks exist today as callable tools: schema
validation, test execution, import check, type check, lint, dataset
profiling, leakage check, elbow method, duplicate detection? List each with
its Loop profile or say ABSENT.

**9.6** Can a model discover the deterministic tools available to it through
a manifest, and is the manifest bounded and versioned?

**9.7** Are imported skills (Agent Skills format) and MCP tools admitted as
candidates with effect declarations, or trusted on import? Probe by
importing a skill whose script writes a file.

**9.8** Can a deterministic tool be promoted from a model-generated
implementation, and does the promoted tool carry its qualification evidence
by exact digest?

---

## 10. Question bank: supervisors, budgets, and default run settings

**10.1** Is a supervisor a Loop? Show a Loop that watches another Loop,
detects non-progress, injects context, restarts, or stops, and records each
decision.

**10.2** OTP asks: what are the restart strategies (one-for-one, rest-for-one,
one-for-all), what is the maximum restart intensity, and where is "let it
crash" allowed versus forbidden? Map each to a Loop policy field or record
ABSENT.

**10.3** Non-progress ladder: soft reset, cold restart, stop unprofitable.
Show the code, the threshold, and the receipt. Can a supervisor distinguish
"no progress" from "slow progress"?

**10.4** Budgets: input tokens, output tokens, model calls, wall time, cost,
recursion depth, spawned work. Which are per Loop, per run, per tenant?
Which are unset by default, and what stops an unset budget from becoming an
immortal process?

**10.5** Default run settings: where is the one place a default lives?
Grep for the same default spelled in the CLI, a dataclass field, a YAML
example, and a docstring. Count the copies.

**10.6** Context limits: does each route declare its context window, and does
the runtime respect it before the network? Do routes with the same model
name on different endpoints have different declared limits?

**10.7** Random sprouts: is there a typed exploration policy with a recorded
rate, seed, and budget? Or is exploration an accident of temperature?

**10.8** Tuning: is there any record linking a default setting to measured
outcomes so a default can be changed with evidence? If not, defaults cannot
be tuned, only guessed.

**10.9** Can two supervisors disagree? What happens when a parent stops a
child that a supervisor wants to restart?

**10.10** When a run is cancelled with SIGINT, is the terminal record bound
in Run History? Probe it.

---

## 11. Question bank: communication fabric and distribution

The owner wants this to scale across millions of computers as a graph
communication fabric. Ask the distributed-systems questions the code has to
answer eventually, and record which are ABSENT today so nobody mistakes a
single-process design for a fabric.

**11.1** What is the unit of distribution: a Loop activation, a run, a graph,
a Series? Where is it serialized, and is the serialization versioned?

**11.2** Identity: is a Loop identity globally unique across machines, or a
process-local counter? Show the id format.

**11.3** Addressing and discovery: how does one Loop find another on a
different machine? Is there a registry, a handshake, a capability manifest?

**11.4** Messages: is inter-Loop communication a typed message with schema
version, sender identity, causal reference, and idempotency key? Or a Python
call?

**11.5** Leases and fencing: the reactive scheduler has leases and fencing
tokens. Do they survive a process crash? Probe by killing a worker mid-lease.

**11.6** Clocks: are timestamps wall-clock only, or is there a logical clock
or sequence per run that survives skew between machines?

**11.7** Hash chain across machines: can a Run History be split across two
writers and merged without breaking the chain? If not, is that a stated
limit?

**11.8** Partition and retry: what happens when a remote Loop is unreachable
mid-graph? Is the failure typed, is the partial state recoverable, and is
the retry idempotent?

**11.9** Trust boundaries: which Loops are allowed to accept messages from
another tenant, another machine, another organization? Where is the policy?

**11.10** Byzantine inputs: can a remote Loop's output be treated as
untrusted candidate data in the same way model output is? Or does the
runtime trust anything that arrives with the right shape?

**11.11** Cost of the fabric: bytes of ledger per Loop activation, times
activations per second, times machines. Compute the storage and network
budget for one million machines running one Loop per second each. Is that a
number the design can carry, and what compression, digest-only, or
summarization path exists?

**11.12** Back-pressure: what happens when producers outrun consumers?
Dataflow answers this; does Loop Engine?

**11.13** Placement: can a Loop declare that it must run near its data, on a
GPU, inside a sandbox, in a jurisdiction? Is placement a typed field or a
deployment accident?

**11.14** External harness as a remote Loop: is an OpenCode, Codex, or
Claude Code session modelled as a Loop with the same relationships, or as a
side channel? Show the adapter's event mapping and the unmapped event count.

**11.15** Is there a single machine-readable statement of which of 11.1 to
11.14 are implemented, planned, or out of scope? If not, write it as part of
the report.

---

## 12. Question bank: continuous learning and the experiment engine

**12.1** What is an experiment, as a record? Hypothesis, procedure, inputs,
metric, result, decision. Does it exist, or is it a portfolio entry with a
different name?

**12.2** Is the frontier of questions and work durable across runs, or
rebuilt from prompt text each pass? Show the record and its parent chain.

**12.3** Can a Loop propose a graph mutation, and does an admitted mutation
create a new immutable graph version with a fork from a checkpoint? Probe a
mutation that removes an already executed vertex; it must be refused.

**12.4** Ingesting new information: when a new document, dataset profile, or
user answer arrives mid-run, which Loop integrates it, and does it invalidate
any prior assumption record?

**12.5** Finding shortcuts: after N accepted runs in a region, does anything
propose a deterministic template for the region? Show the proposal record or
say ABSENT.

**12.6** Distilling: after a run, does anything write a compact lesson
(negative evidence, region note, prompt experiment record) that a later run
reads? Show one that was read by a later run, not just written.

**12.7** Testing itself: does the system run held-out tasks to check that a
promoted shortcut still works, and does it quarantine on failure?

**12.8** Portfolio: multiple solutions per task, independent evaluation,
ranked views, Pareto frontier. Run P2 from the proof ladder (two
deterministic candidates, zero model calls) and P8 (synthetic micro
competition) and report which parts of the lifecycle are joined and which
are separate stores with no lineage between them.

**12.9** Ensembles: can two candidates be blended without compatible output
contracts and independent verification? They must not. Probe it.

**12.10** Two terminal questions: `user_result_ready` and
`exploration_complete`. Are they separate records? Can a run return a
verified incumbent and keep exploring challengers under a finite lease?

**12.11** Token curve: measure model calls and input tokens across three
repeats of the same task region. If the curve does not fall, what would
have to exist for it to fall, and is that thing on the roadmap or ABSENT?

**12.12** Does the learning path ever learn from a failure it caused itself
(bad shortcut, wrong fingerprint match)? Show the record that closes that
loop.

---

## 13. Question bank: information theory and cost

**13.1** Bytes of ledger per useful byte of output, per run, on the saved
runs. Report the distribution.

**13.2** Events per model call, events per Loop, Loops per solve. Which
event families dominate, and are any redundant?

**13.3** Estimated tokens versus provider-reported tokens: the estimator uses
a bytes-over-four rule. Measure its error on real calls and calibrate it.
Is the calibration stored?

**13.4** Duplicate content across a run's packets: measure it. Is the
duplicate text referenced by digest or re-sent?

**13.5** What is the minimum description of a solved task region that would
let a future run skip reasoning? Does any record approach it, or does the
system store transcripts?

**13.6** Compression: is anything compacted with lineage to the raw digest,
or is compaction a summary that replaces the raw?

**13.7** What does a Loop cost when it does nothing? Instantiate a Loop with
a no-op handler and measure bytes and microseconds. That is the floor the
fabric pays per vertex.

**13.8** Are digests computed once and reused, or recomputed per event?

**13.9** Which records are append-only and which are rewritten in place?
Rewriting in place destroys the information-theoretic argument for the
ledger.

**13.10** Cache economics: how much of a call's input is stable prefix that a
provider could cache, and is the packet ordered to make that possible?

---

## 14. Question bank: humans in the loop and the colleague analogy

**14.1** Horizons: does a Loop track micro, short, medium, and long horizons
as fields, or only as prose in a prompt?

**14.2** Width versus depth: can the Practitioner hold several alternatives
at the same depth, and is the choice to widen or deepen recorded?

**14.3** Stepping back: when a failure is diagnosed, does the record say how
far the system stepped back (one node, one stage, one branch, one graph
version, full re-orientation)?

**14.4** Asking: are material questions typed with answer slots, and does an
answer arrive without changing the original task record?

**14.5** Checklists: can a checklist be a deterministic Loop with a gate that
escalates only when an item fails? Show one.

**14.6** Feedback: does user feedback create a typed record and a new
proposal or fork, never an edit to committed history? Probe by submitting
feedback through Studio or the CLI and reading the ledger.

**14.7** Digestibility: can a person read what a Loop did in under a minute
from the report or Studio, including what context it saw and what it
decided? Time it on a saved run.

**14.8** Playback: does the terminal tree render without a browser, and does
it show calls, tokens, and terminal state per Loop?

---

## 15. Question bank: class structures, hierarchies, and standardizations still needed

Answer each with EXISTS (cite), NEEDED (describe the smallest passive record
or Loop profile that would satisfy it, and which authority owns it), or NOT
NEEDED (say why the existing records cover it).

**15.1** A typed invocation request object for every public constructor with
more than five parameters.

**15.2** A single versioned schema registry with one place per record type
and a migration reader at boundaries.

**15.3** A `LoopDefinition` version policy: when does a change require a new
version, a new digest, requalification?

**15.4** A handshake record between producer and consumer Loops and between
Loop Engine and an external harness.

**15.5** A message envelope for inter-Loop communication with schema version,
identity, causality, and idempotency.

**15.6** An experiment record and a frontier item record with statuses and
horizons.

**15.7** A context pack manifest per model call with included, excluded, and
compacted items and their reasons.

**15.8** A prompt experiment record linking prompt resource, context policy,
model, task region, and outcome.

**15.9** A realized reuse receipt separating estimated from realized savings.

**15.10** A supervision policy record (restart strategy, intensity,
escalation) attached to a Loop profile.

**15.11** An exploration policy record (rate, seed, budget) for random
sprouts.

**15.12** A placement and locality declaration on a Loop profile.

**15.13** A trust class on every inbound value: model output, remote Loop
output, tool output, user input, retrieved document.

**15.14** A capability manifest for tools and hooks that both modes read.

**15.15** A fingerprint record that includes environment digests.

**15.16** A region statistics record (histograms, success rates, best-known
settings) per task region.

**15.17** A checklist profile: gate, escalate, record.

**15.18** A canonical run census record that reports unknowns as unknown, not
zero.

**15.19** A profile hierarchy: is inheritance between profiles (V1, V1.1)
data-level composition with explicit overrides, or is there any class-level
inheritance sneaking in?

**15.20** For every NEEDED answer: does adding it create a second runtime,
registry, or source of truth? If yes, it is the wrong shape; describe the
right one.

---

## 16. Question bank: harness comparison, the band-aid question

**16.1** Run the same tiny fixture (a `clamp` function with failing tests, or
the repository's own equivalent) through the native Practitioner and through
every installed harness (Codex, Claude Code, OpenCode, Hermes, others). Same
starting commit, same model where possible, bounded budgets. Report
success, tests passed, model calls, tokens, wall time, edits, retries, and
evidence completeness. Mark unavailable harnesses NOT_EXECUTED.

**16.2** For each harness, name the mechanism it uses for looping to a goal
(a loop command, a goal flag, a supervisor script, a contract file). Is the
mechanism part of the harness's core or a layer on top? That is the band-aid
test.

**16.3** What does Loop Engine do natively that the harnesses do with a layer
on top: typed ports, recorded relationships, mode per unit, verified
acceptance, reuse harvesting, hash-chained history? For each, cite the code
and the probe.

**16.4** What do the harnesses do better today: repository orientation,
editing protocols, sandboxing, speed to first useful edit, resumable
sessions? Say it plainly with numbers from 16.1.

**16.5** Can Loop Engine supervise a harness as a remote Loop with the same
evidence contract it applies to itself? Show the normalized events and the
unmapped count.

**16.6** Can a harness call Loop Engine as a tool or skill, and does that
placement preserve the Loop invariant on the Loop Engine side?

**16.7** Is "Human Harness" a configurable brand or a hardcoded string?

---

## 17. Question bank: safety and honesty under the abstraction

**17.1** Can a Loop report ACCEPTED while its only step failed? Decide
whether that is a bug or a semantics and cite where the semantics is
documented. If undocumented, it is CONTRADICTED.

**17.2** Can any code path label a structural boundary `complete`?

**17.3** Can a model's output become trusted state without a verifier?

**17.4** Can a remote effect be replayed silently?

**17.5** Can host execution happen without explicit authority when Docker is
absent, and is the weaker isolation labelled in Run History?

**17.6** Can a copy into Run History follow a symlink outside the workspace?

**17.7** Can a TLS skip be used without being recorded in the run?

**17.8** Can a missing credential be misclassified in a way that blocks
failover?

**17.9** Can a generated command run with an infinite timeout or an
unreviewed pip option?

**17.10** Can a saved run id traverse the filesystem?

**17.11** Do any of the above have a regression test that fails on the
pre-fix tree? Cite each test.

---

## 18. Required probes

Run every probe below in a scratch directory with `PYTHONPATH=src` or the
repository's virtual environment. Save each script and its output with the
report. A probe that cannot run is reported NOT_EXECUTED with the blocker.

- **PR-01 Function equivalence.** Pure function versus one-shot deterministic
  Loop over 1,000 inputs. Outputs, exceptions, events, bytes, microseconds.
- **PR-02 Identical failure churn.** `accepted_success`, no ceiling, identical
  failing handler. Iterations, events, terminal code.
- **PR-03 Runaway spawn.** No `max_depth`. Depth reached, error type, error
  text.
- **PR-04 Coercion visibility.** Coerced role or mode; read init and spawn
  events.
- **PR-05 Fabricated recovery.** Failed model-led step with deterministic
  fallback. Outcome text, terminal code, accepted-success count.
- **PR-06 Kernel structure.** One Practitioner pass. Loops created, steps
  labelled, steps executed without Loop identity.
- **PR-07 Atomic overhead.** String join through the atomic path versus
  native. Events, bytes, ratio. Fusion flag consumer present or absent.
- **PR-08 Context boundary.** Route with a declared context of N. Requests at
  N minus one and N plus one estimated tokens. Which refuses, where, and with
  what error code.
- **PR-09 Packet duplication.** On a saved multi-call run, byte-identical
  content across packets before and after bounding. Trim events present.
- **PR-10 Warm zero-model reuse.** Cold build, harvest, qualify, promote,
  paraphrased warm task. Model calls on the warm path.
- **PR-11 Elbow distillation.** Non-deterministic choice of k, then
  deterministic realization of the same contract. Same contract identity or
  not.
- **PR-12 Summer shortcut.** Solved region with a precondition fact. Second
  task with the fact unchanged (shortcut taken, zero calls) and with the fact
  changed (shortcut refused, reasoning resumed). Negative evidence recorded.
- **PR-13 Canvas edit from incumbent.** Existing solution plus injected error.
  Does the packet carry the incumbent; is the edit a candidate; is the
  incumbent untouched on rejection.
- **PR-14 Hook and tool parity.** One deterministic tool invoked from a
  deterministic Loop and from a model-led Loop. Diff the receipts.
- **PR-15 Supervisor.** A child that stalls. Detection, context injection,
  restart, stop, all recorded.
- **PR-16 Two-process handoff.** Serialize an activation, execute in a second
  process, merge the ledger. Chain intact or not.
- **PR-17 Crash mid-lease.** Kill a reactive worker holding a lease. Recovery
  behavior and duplicate-effect check.
- **PR-18 Portfolio P2 and P8.** Two deterministic candidates with zero
  model calls; synthetic micro competition with at least three branches.
  Lineage from candidate to graph version to context pack present or absent.
- **PR-19 Token curve.** Three repeats of one task region. Calls and input
  tokens per repeat.
- **PR-20 Harness benchmark.** Section 16.1 fixture across every available
  harness.
- **PR-21 Passive-data scan.** Every record class with an executing method.
- **PR-22 Alias and version-string scan.** Every hand-spelled version string
  and every alias compared for behavior.
- **PR-23 Default copies scan.** Every default value spelled in more than one
  place.
- **PR-24 Second-loop scan.** Every `while`, retry, and sleep outside a Loop
  step, classified.
- **PR-25 SIGINT binding.** Cancel a live or mocked solve mid-call; terminal
  record bound in Run History.

---

## 19. Report format

Produce, in this order, as one Markdown file plus a JSON sidecar:

1. **Commit and environment.** Hash, dirty files, Python, Docker, providers
   by reference (never a key value), harnesses installed with versions.
2. **The thesis as you found it.** Your version of section 1 with citations,
   two pages at most, naming which analogy the code earns and what is new
   against each lineage in 1.4.
3. **Scorecard.** One row per question: id, verdict, severity, evidence, one
   sentence. Sorted by severity then section.
4. **Probe results.** One block per probe with command, exit status, and the
   numbers.
5. **Top ten invariant violations** with the exact code and the smallest
   repair that preserves one runtime.
6. **Top ten missing abstractions** from section 15, each with the passive
   record or Loop profile that would satisfy it and the authority that owns
   it.
7. **Cost table.** Every number from sections 13 and 3.8 and 3.9 and 11.11.
8. **Harness comparison table** from 16.1, with NOT_EXECUTED rows.
9. **Fabric readiness table** from 11.15: implemented, planned, out of scope.
10. **The honest sentence.** One paragraph answering: is "everything is a
    Loop" true at this commit, where is it true only on paper, and what
    single change would move the most questions from ABSENT to PROVEN.
11. **Files changed** if Phase B ran, each with purpose, symbols, test.
12. **Next increment.** One, chosen from the evidence, mapped to the P0 to
    P10 proof ladder.

JSON sidecar: `{"commit":..., "questions":[{"id":..., "verdict":...,
"severity":..., "evidence":[...], "note":...}], "probes":[...],
"counts":{...}}`. Unknown numbers are `null` with a reason, never zero.

---

## 20. Anti-goals for the auditor

- Do not soften a CONTRADICTED verdict because the intent is good.
- Do not credit documentation, comments, prompts, ADRs, or this file as
  evidence.
- Do not credit a test you did not read.
- Do not create a `LoopNode`, a second runtime, a registry, a settings
  authority, or a fourth mode to "fix" a finding.
- Do not rewrite the system. Phase B is bounded repair with regression
  tests.
- Do not paste this whole file into every model call.
- Do not report unknown as zero.
- Do not declare a benchmark winner from one fixture; call it a smoke test.
- Do not expose credentials, private reasoning, or raw authorization headers
  in any output.
- Do not commit, push, publish, or change billing.
- Do not confuse Turing completeness with usefulness, or a slogan with a
  probe.

---

## 21. Closing instruction

Begin with section 0.3. Bind the authorities. Run PR-01 through PR-07 before
answering a single question in section 3, because those seven probes decide
whether the runtime is honest enough for the rest of the audit to mean
anything. Then work the banks in order, one at a time, loading only the bank
you are answering. Finish with the honest sentence. If the thesis holds, the
report will show it in numbers. If it does not, the report will show exactly
where, and that is the more useful outcome.
