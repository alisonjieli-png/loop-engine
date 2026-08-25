# Loop Engine constitution and autonomous campaign charter

> Historical design record from before the current Loop Engine documentation
> hierarchy. Use the root README, component guides, Product Nomenclature, and
> Universal Loop standard for current behavior and names.

## Everything is a loop · the baseline every loop inherits · and the standing order to run for days

Status: historical design input.
Paste this whole file into OpenCode, Codex, Claude Code, or any terminal-capable
harness. It is self-orienting: it tells you what the architecture IS, what you
must never break, and what to do for the next several days without being asked
again.

---

# PART I — THE CONSTITUTION

## Article 1. Everything is a loop

There is one live operational object. Each loop is a node. "Node" describes
the loop's place in a graph; it does not name a second runtime type.

```
Everything that crosses an operational boundary is a loop node.
```

A boundary is crossed whenever something is independently **discoverable,
selectable, configurable, invokable, observable, retryable, replaceable,
composable, versioned, governed, or visible in the Studio**. If any of those
words applies, it is a loop. Private helper functions inside a loop's body are
not boundaries — they are implementation, and they stay implementation.

**There is no direct cross-boundary resource access.** (Owner ruling,
2026-08-24, which SUPERSEDES an earlier refinement adopted here from an
external addendum. That refinement said "data is not a loop"; it was too
permissive, because it could be read as licensing a direct store read. The
owner's stricter form is the law.)

Even reading one fixed sentence is a loop:

```
initialize -> validate request -> return the versioned sentence ->
validate output -> record -> stop after one successful deterministic iteration
```

The sentence may be **stored internally as data** — that part survives — but
no product-level caller consumes it directly. It invokes the loop that owns
and returns it. So:

```
EVERY STRING ACCESS IS A LOOP.      EVERY GUIDANCE ACCESS IS A LOOP.
EVERY CODE EXECUTION IS A LOOP.     EVERY HISTORICAL ACCESS IS A LOOP.
EVERY SEARCH IS A LOOP.             EVERY CONTRACT ACCESS AND CHECK IS A LOOP.
EVERY CACHE ACCESS IS A LOOP.       EVERY MODEL AND TOOL CALL IS A LOOP.
SEARCH RETURNS LOOPS.               SERVING MEANS RUNNING LOOPS.
```

Forbidden, at any product-level boundary:

```python
text    = string_store.get("question.residuals")      # direct resource read
history = chronicle.search_similar(task)              # direct history query
result  = code_registry["collinearity"](features)     # direct capability call
```

**The regress stops at the kernel.** Beneath every boundary is the private
loop runtime kernel and its implementation primitives. The kernel is not a
catalog resource another loop must discover and invoke — it is the machinery
that executes the loop abstraction. That is the base case, not an exception.

Three corollaries, each of which has already been violated once in this
project and repaired:

1. **Every Solution Canvas node is a loop.** A solution is a tree of loops,
   usually deterministic, each with a stop condition and a fallback seam.
   There is no separate operational node type.
2. **An API endpoint is a loop.** It is externally invokable, observable, and
   governed, so it gets an envelope. *(Violated by a flat `build_projection`
   dispatcher. Fixed.)*
3. **A DAG node is a loop.** A deterministic pipeline is not an exception to
   the law — it is the most common instance of it. Each node inherits the loop
   baseline, gets its own stop condition, and gains a fallback it did not have
   as a bare function.

## Article 2. Every loop has the same baseline

Every loop — practitioner, solution, stage, API, tool, check — is built on one
baseline. It declares, before it runs:

```
identity          who this loop is, and who started it
goal              what it must achieve, in one sentence
inputs            what it was GIVEN
output contract   what it must PRODUCE, and how that is checked
mode policy       allowed modes + the waterfall it prefers
stop condition    when it is done — see Article 4
budget            iterations, semantic calls, cost, wall time
authority         permissions and effects, never exceeding its parent's
fallbacks         what to try when the primary arm fails
```

A loop that cannot state its goal, its inputs, and how its output is checked
is not ready to run. That is not bureaucracy; it is the precondition for every
other property in this document — you cannot verify, retry, replace, advise,
or fall back without it.

## Article 3. Three modes, one order, per loop

```
Deterministic  →  Hybrid  →  Model-backed
```

Always shown and stored in that order. **Mode is per loop and never
inherited**: a model-backed parent routinely spawns deterministic children,
and a deterministic solution may contain one hybrid repair loop.

- **Deterministic** — resolved by code, rules, search, or a tested capability.
  Zero semantic calls, and that zero is *asserted*, not hoped for.
- **Hybrid** — deterministic primary; a model assists only after a **typed
  insufficiency**, and a deterministic check decides whether to accept what
  the model returned. The model passes by producing something the checker
  validates, never by being persuasive.
- **Model-backed** — the model guides the semantic reasoning while the runtime
  keeps state, budget, ordering, permissions, and evidence.

The waterfall is the default, not a law: a loop may declare model-first,
deterministic-only, or a portfolio that runs modes in parallel and compares.
What is required is that the policy is **explicit and measurable**.

**A mode is a policy preset, not a reproducibility claim.** Determinism is a
vector, recorded on seven independent axes: `control_determinism`,
`computation_determinism`, `effect_semantics`, `environment_identity`,
`observation_semantics`, `verifier_determinism`, and `replay_guarantee`. A
loop declares which of four guarantees it actually offers — **exact**,
**event-equivalent**, **evidence-equivalent**, or **non-replayable** — rather
than leaving a reader to infer one. And note the trap: **a seed, or a
temperature of zero, is not a proof of determinism.** Reproducibility varies
by library release, platform, and device. State the guarantee you can keep.

**Mode does not gate intelligence.** All four planes are available to all
three modes. A deterministic loop pulls String Intelligence, reuses Code
Intelligence, warm-starts from prior runs, and consults User Intelligence
exactly as a model-backed one does. Retrieval is not a model feature.

## Article 4. Every loop has a stop condition, and one iteration is a valid one

This is the article that makes the law cheap enough to be universal.

```
A loop runs until its stop condition is met.
The most common stop condition is: succeed once.
```

A deterministic validation is a loop whose stop condition is *"one successful
iteration"*. It costs one function call. It is still a loop, and that is what
buys it identity, evidence, failure attribution, a fallback seam, and a place
on the canvas. Declaring a stop condition of "once" is not a downgrade — it is
the correct configuration for most of the system.

Valid stop conditions include: succeed once · N successes · until the checker
passes · until confidence ≥ x · until the budget is spent · until no candidate
improves on the incumbent · until an external gate answers · abstain when
uncertain.

**A loop with no declared stop condition must not run.** Unbounded is not a
stop condition.

## Article 5. Self-correcting by construction

Because every loop declares a goal, inputs, an output contract, and a fallback
seam, every loop can notice its own failure and try something else — including
escalating to a model as its last arm.

```
primary arm fails
   → next declared arm
   → still failing, and the loop is permitted a model
   → a model-assisted child, its output checked by the same contract
   → still failing → abstain with a typed failure, never a plausible guess
```

This is what makes the loop packaging worth the trouble. Self-correcting code
has been attempted many times as a language feature or a framework trick. As a
*loop with a contract*, it is simply the ordinary case: the fallback ladder is
data, the check is deterministic, and the escalation is budgeted and visible.

**Abstention is a success state.** A loop that stops and says "I could not do
this, here is why" is behaving correctly. A loop that returns something
plausible instead is the failure mode this whole architecture exists to
prevent.

**Acceptance is not invocation.** Four outcomes, never used as synonyms:

```
attempt succeeded    the capability returned a well-formed output
iteration converged  the loop's state no longer requires another cycle
result accepted      completion predicate AND independent verification passed
run terminated       the machine reached any terminal state, success or not
```

A successful return is an *attempt* outcome. A loop completes successfully
only when an independent completion and verification policy accepts the
result. Terminal states are typed, not boolean: `ACCEPTED`, `INVALID_SPEC`,
`POLICY_DENIED`, `BLOCKED`, `EXHAUSTED`, `BUDGET_EXHAUSTED`,
`DEADLINE_EXCEEDED`, `CANCELED`, `VERIFICATION_REJECTED`, `EFFECT_FAILED`,
`COMPENSATION_FAILED`, `INTERNAL_PROTOCOL_ERROR`.

## Article 6. Loops compose without limit

A loop may start child loops. A child may start grandchildren. There is one
loop class at every depth.

- A child gets a **spawn reason**, a **return destination**, its own budget,
  and a **permission ceiling that never exceeds its parent's**.
- Power raises effort, never authority. `max` power buys more iterations, not
  more permissions.
- Every child must reach a terminal disposition before its parent closes.
  A spawned-but-never-finished child is an orphan and is a defect.
- Depth is bounded and impasse is detected: the same question returning with
  no material state change means change lane, not loop harder.

## Article 7. Templates, not literals

The nine-step reference loop — Orient · Reconcile · Assess · Decide · Determine
How · Act · Verify · Integrate · Route — is **the default, not the only
topology**, and it is itself a loop of nine loops: each stage is a loop that
may finish deterministically, spawn research, escalate, abstain, or return.

Any other ordering is a **registered template**, never an inline list of step
names. A generated template starts as a candidate and cannot configure a loop
until it is admitted through the evidence gate. The runtime must never quietly
normalize a custom ordering back into nine steps.

**Nine is a starting point, not a size.** Smaller and larger loops are
first-class, and the range is shipped rather than promised: 14 registered
templates spanning **1 to 9 steps** today, from `atomic_code_only` (one beat)
to `reference_nine_step`. A longer template is equally legitimate. The only
requirements are that it is registered, bounded, and carries a stop
condition — maximum flexibility is the point.

## Article 8. Four intelligence pillars, one Runtime Memory

```
String Intelligence · Code Intelligence ·
Previous Run & Solution Intelligence · User Intelligence
```

Each exists for a distinct benefit, and cost reduction is a consequence of
all four rather than the purpose of any:

- **String Intelligence is the diversity engine.** Prompting in different
  patterns — persona, question, constraint, timeframe, criterion — reaches
  solutions a single framing never finds. It accumulates *ways to ask*, so
  the explored solution space widens as the library grows.
- **Code Intelligence** makes a verified capability findable instead of
  rebuilt.
- **Previous Run & Solution Intelligence** turns prior runs into warm starts.
- **User Intelligence** lets a person steer the practitioner graph **and**
  the solution graph without either being rewritten.

Runtime Memory is separate: the current run's shared notebook. It may be
curated into a pillar later; it never auto-promotes.

Prior runs are **priors, never proof**. User Intelligence is human-authored,
attributable, and ranked by declared strength — never by how forcefully it is
worded — and it can never outrank platform safety, organization policy, or a
project hard constraint.

## Article 9. One Chronicle, one vocabulary

All observability derives from one append-only Chronicle with one closed event
vocabulary. The console, the browser, the stream, playback, profiling, and
export are **projections of the same events**, never separate counters.

A live run and a replayed run must describe the same history in the same
words. *(Violated once, when saved runs projected through the raw map and came
back as `x.loop_init`. Fixed, and gated.)*

## Article 10. Honesty rules that outrank convenience

- No component approves its own candidate. Generation and promotion are
  separate loops.
- `NOT RUN` and `BLOCKED` are never `PASS`. The suite never silently shrinks.
- A locally graded replica is labeled as such; smoke evidence is labeled smoke
  evidence.
- A dated count names the command that recomputes it.
- Declaring something is not claiming it: coverage reports separate
  "has an emitter" from "declared with none yet".
- **No premature judgment.** Whether model calls pay, whether a template wins,
  whether an iteration plateau exists — none of these are settled until the
  corpus is large. Tens of thousands of solutions, not tens.

## Article 11. Three loop levels, named on every spec

One protocol, three meanings. A shared protocol does not erase the
distinction, and collapsing them would put a search loop and an execution
loop under the same authority.

| Level (`logical_kind`) | Purpose | Authority boundary |
|---|---|---|
| `execution` | govern one runnable unit: attempt, verify, retry, fall back, compensate, stop | may not alter a frozen plan; amendments go through a separate authorized path |
| `task_semantic` | repetition the problem itself requires: converge, paginate, refine to a stated condition | part of the semantic graph, compiled like other control structure |
| `search_improvement` | generate and evaluate alternative graphs, routes, policies, capabilities | outside the executed graph, and **cannot self-admit or self-promote** |

Every loop spec names its level. The third row is the one that matters most:
an improvement loop may propose, stage, and compare — it may never accept its
own candidate. That is the same separation as Article 10's "no component
approves its own candidate", stated where it is easiest to violate.

---

---

# PART II — INFRASTRUCTURE RULES

These are the rules that keep Article 1 true when nobody is watching.

**R1 — One runtime.** One canonical loop implementation. A second live
runtime is a conformance failure, not an alternative.

**R2 — The baseline is inherited, not re-implemented.** Every loop is built
from the one baseline (Article 2). A subsystem that grows its own private
notion of "goal" and "stop" has forked the architecture in fact if not in
folder layout.

**R3 — Wrapping is one call.** Universality only survives if it is cheap.
Turning a callable into a loop must be a single call with deterministic-only
settings pinned, no children, no model budget. Encapsulation is universal;
autonomy is earned.

**R4 — Fusion is allowed, identity is not negotiable.** The compiler may
inline, cache, batch, or fuse adjacent deterministic loops **only if** logical
identity, lineage, inputs/outputs, permissions, failure attribution, events,
playback, per-loop metrics, and canvas identity all survive.

**R5 — Every boundary is scanned.** A conformance scanner fails the build on:
a second runtime · direct capability invocation outside a loop · a model call
outside the gateway · an event kind with no canonical family · a candidate
that promoted itself · a module without context · a secret · a stale current
doc · a custom loop normalized to nine steps · a canvas box with no loop.

**R6 — Every invariant has an adversarial test.** A positive test proves the
thing works. An adversarial test proves the guard *bites*. Only the pair
counts.

**R7 — Prove the live path.** "Scaffolded", "registered", "wired",
"documented", and "green in isolation" are not done. A declared event is not
an execution. A handler-declared model-backed step is not a model call.

**R8 — Counted generation is cloud-only.** Provider-reported tokens only.
Local small models may decide or label; they are never the generation
workhorse for measured work.

**R9 — Commits stay local.** Push, publish, submit, deploy, and go-live are
owner-gated. Never infer authorization.

**R10 — Another session's work is not yours.** Read freely, never rerun,
clean, or overwrite. If a shared file breaks the tree, make the minimal
additive repair and say so.

---

# PART III — THE STANDING CAMPAIGN ORDER

This part is addressed to the harness reading it. It is a standing order, not
a single task. Work it for hours or days.

## How to run

Run the cycle continuously:

```
ORIENT → pick the highest-value gap → IMPLEMENT →
focused tests → conformance → ADVERSARIALLY ATTACK YOUR OWN CHANGE →
repair → full suite → live canary → inspect evidence →
compare against baseline → update docs + dev memory → commit locally →
pick the next gap → repeat
```

Never stop after orienting. Never stop at a plan. If you find yourself with
nothing to do, you have not read `dev_memory/ARCHITECTURE-DRIFT.md`.

## Spin out agents, and make them argue

You are encouraged to fan out aggressively. Useful shapes:

- **Councils.** Three independent agents attack the same claim from different
  lenses — correctness, security, does-it-reproduce. Majority refutation
  kills the claim. Diversity of lens beats redundancy of reviewer.
- **Adversarial pairs.** One agent implements; a second is rewarded only for
  breaking it. Both write notes.
- **Loop-until-dry discovery.** Keep spawning finders until K consecutive
  rounds surface nothing new. Simple counters miss the tail.
- **Judge panels.** Generate N independent designs from different angles,
  score them with parallel judges, synthesize from the winner while grafting
  the best ideas from the runners-up.
- **Completeness critics.** A final agent whose only job is "what is missing —
  which modality was not run, which claim is unverified, which source unread?"
  What it finds becomes the next round.

Agents must **write notes and communicate**: findings, disagreements, dead
ends, and decisions go into `dev_memory/`. A disagreement is preserved, never
erased — deleting the losing side destroys the reason the winner won.

## What to work on, in priority order

1. **Close the drift list.** `dev_memory/ARCHITECTURE-DRIFT.md` is the
   authoritative open-work register. Each entry names the check that closes it.
2. **Make the baseline universal.** Audit every operational boundary and
   produce a table: boundary → loop → template → stop condition → positive
   test → adversarial bypass test. Anything unbound is the next task.
3. **Emitters for declared-but-silent event families.** Only where a live path
   genuinely exists. Never emit an event to improve a coverage number.
4. **The routed Studio over real streams.** Loop tree, inspector, console —
   three projections of one Chronicle, agreeing on every count.
5. **Then go solve real problems.** OpenML and Kaggle, on the ladder below.

## The problem ladder

Prove mechanics first, then difficulty. Label every result honestly.

```
1. a local deterministic fixture           — plumbing
2. an archived playground task             — end-to-end
3. a live playground task                  — real submission path
4. a task needing leakage, residual,
   stability, and ensemble loops           — depth
5. a warm related run                      — does reuse actually pay?
```

Rules: a locally graded replica is never called a leaderboard result. Smoke
evidence is never called benchmark evidence. And per Article 10, **do not
conclude anything about whether model calls pay** from the first hundred runs.
Collect, label, and keep going.

## Reporting

Every gate is exactly one of **PASS · FAIL · NOT RUN · BLOCKED**.

Report what changed, what you attacked and how it survived, what you could not
do and why, and what you would do next. Lead with what is true, not with what
is impressive. If the numbers are unflattering, they are still the numbers.

---

# PART IV — THE OPEN DESIGN QUESTIONS

Real questions, honestly open. Do not resolve them by assertion; resolve them
with an experiment and a receipt.

1. **One baseline class, or one baseline contract?** Inheritance gives
   guarantees cheaply and couples everything to one class. A declarative
   contract that many implementations satisfy is looser and more portable.
   *Current lean: contract, with one reference implementation — but this is a
   lean, not a finding.*
2. **How thin can a thin loop get?** A one-iteration deterministic loop should
   cost approximately a function call. Measure the real overhead at 10⁴–10⁶
   invocations before declaring universality affordable.
3. **What is the canonical template set?** There is one per intelligence
   type, one per solution shape, one per DAG node class — or there are far
   fewer than that and the rest are parameters. Fewer templates with sharper
   parameters usually beats a template per case.
4. **When does a portfolio beat a waterfall?** Running modes in parallel and
   comparing costs more and learns more. Which loops deserve it?
5. **Does the fallback-to-model arm actually pay?** It is the most attractive
   claim in this document and therefore the one most in need of evidence.
   Instrument it, and hold the verdict until the corpus is large.

---

# PART V — THE ONE-SCREEN SUMMARY

```
EVERYTHING THAT CROSSES A BOUNDARY IS A LOOP.
PRIVATE HELPERS INSIDE A LOOP ARE NOT BOUNDARIES.

EVERY LOOP INHERITS ONE BASELINE:
IDENTITY · GOAL · INPUTS · OUTPUT CONTRACT · MODE POLICY ·
STOP CONDITION · BUDGET · AUTHORITY · FALLBACKS.

EVERY LOOP HAS A STOP CONDITION.
THE MOST COMMON ONE IS: SUCCEED ONCE.

DETERMINISTIC → HYBRID → MODEL-BACKED, ALWAYS IN THAT ORDER,
PER LOOP, NEVER INHERITED.

A DAG NODE IS A LOOP. A CANVAS BOX IS A LOOP.
AN API ENDPOINT IS A LOOP. A CHECK IS A LOOP.

NINE STEPS ARE THE REFERENCE, AND THEY ARE NINE LOOPS.
EVERY OTHER ORDERING IS A REGISTERED TEMPLATE.

A LOOP THAT CANNOT STATE ITS GOAL, INPUTS, AND CHECK
IS NOT READY TO RUN.

ABSTENTION IS A SUCCESS STATE.
A PLAUSIBLE GUESS IS THE FAILURE THIS ARCHITECTURE PREVENTS.

ONE CHRONICLE. ONE VOCABULARY.
LIVE AND REPLAYED RUNS SAY THE SAME WORDS.

FAN OUT. ARGUE. WRITE NOTES. PRESERVE DISAGREEMENTS.
ATTACK YOUR OWN WORK BEFORE REPORTING IT.

NOT RUN IS NOT PASS.
NO UNIVERSAL JUDGEMENT FROM A SMALL SAMPLE.

BUILD, TEST, BREAK, REPAIR, PROVE, RECORD, REPEAT.
```
