# Building a self-tuning Loop-node solver: what actually goes wrong

This is guidance for building the universal Loop-node solver — a network of
LLM-reasoned Loops that can meet an unfamiliar task, construct its own
approach, recover from its own failures, and get cheaper over time by
learning which of its own moves worked.

It is written from building it, not from designing it. The architecture is
the easy half and is described elsewhere. What follows is the half that only
appears once the code runs: a set of failure modes that each looked like
correct engineering, each passed review, and each would have quietly
destroyed the evidence the system exists to collect.

Every one of these was found in this repository, in work done deliberately
and defended at the time.

---

## The one-sentence thesis

LLM reasoning owns every task-conditioned decision; deterministic code owns
mechanics, safety, and evidence; and the system earns the right to replace
reasoning with rules only by first recording what reasoning did and whether
it worked.

Everything below is in service of the last clause, because that is the clause
that fails silently.

---

## Part I — The failure modes

### 1. The developer writes the intelligence into a table and calls it infrastructure

**What it looks like.** Recovery policy as constants: which errors retry, how
many attempts each earns, how long to wait, how far to compact context, what
output floor to keep.

**Why it is wrong.** Every one of those is a task-conditioned decision. Is
another sample from this model likely to help? Should the context shrink or
the responsibility split? Those depend on the task, and a constant answers
them identically forever, from however many runs its author had seen.

**The incident.** All five constants were written in one morning from a
handful of failures. Later, asked the same question through a typed choice
interface with the same mechanical facts, the model chose a *different model
on the same provider*, lowered temperature, named an exit condition, and kept
compaction in reserve. The table said: retry the same route six times.

**The rule.** A constant that answers "what should happen next" is a
hypothesis with no expiry date. Deterministic code may state what is
*possible* — this route has no credential, that window cannot hold the
request. It should not state what is *wise*.

### 2. Instrumentation that can fail the thing it observes

**The incident.** A decision recorder referenced an out-of-scope variable and
raised `NameError` from inside orientation. Two passing fixture solves became
unsolved runs. The observer changed the observed.

**The rule.** Every recording path swallows its own errors and continues.
Non-negotiable.

### 3. …and the defensive wrapper then hides your own bugs

**The incident.** Having applied rule 2, stage persistence was wrapped so it
could never fail a run. It was then wired into the success path only, and
three failure exits returned before reaching it. Runs that died wrote
nothing — and the wrapper swallowed the *absence* exactly as readily as it
would have swallowed an error. The runs most worth learning from, the ones
where recovery and model demand are actually tested, left no trace.

**The rule.** A defensive boundary protects the run and conceals your
mistakes with equal enthusiasm. Count what it swallows. A store must be able
to say "I lost three writes" — because "no prior evidence" and "the recorder
broke" call for opposite responses and otherwise look identical.

### 4. A control arm that controls for nothing

**The incident.** To distinguish real convergence from convergence the system
had suggested, a share of stages was answered with no template offered. The
arm was assigned by hashing the stage signature — so a stage *region* landed
in the same arm permanently. Treated and control could never contain the same
kind of work. The one question worth asking was unanswerable by construction,
and the design looked rigorous while controlling for nothing.

**The rule.** Randomise on the *occurrence*, not the *class*. Hash the
experiment, the signature, the occurrence identity, and a campaign seed: then
independent occurrences of one region fall on both sides, while retries of a
single occurrence stay put so a failing run cannot walk itself across.

### 5. Believing convergence you caused

**The shape.** Offer a template. Calls adopt it. The record fills with
agreement. Concentration rises, entropy falls, and it reads as discovery. Fit
a shortcut to that record and you encode the suggestion, then keep encoding
it as the corpus grows.

**The rule.** The control arm has to exist *before* the data does. A record
collected without one cannot be repaired afterwards. Measure concentration
and entropy per arm, and say plainly when there is no control arm that
nothing separates convergence from suggestion.

### 6. Asking a model for a verdict instead of an observation

**The incident.** An LLM judge was asked whether a criterion was met. Given a
patch that *concealed* a defect rather than fixing it, it described the
concealment precisely in its own evidence — and answered that the criterion
was met. A second pass asked whether that evidence supported that conclusion;
it explained that it did not, and answered that it did. The prose was right
both times; the boolean was wrong both times.

**The rule.** A judgement field invites agreement. Ask which of several
neutrally-worded options matches what was read, and derive the verdict from
the answer. The model keeps the part it is good at — reading — and is left
nothing to be agreeable about. Measured against a keyword grader on two
adversarial cases: keywords 0 of 2, observation-derived 2 of 2.

### 7. Keyword-matching a semantic question

**The incident.** A grader accepted a root cause only if it contained
"exclusive", "inclusive", "off-by-one", "end" or "last". A run writing "the
upper limit is one too small" was marked wrong for saying the right thing in
unenumerated words. It also read the run's self-report rather than the code,
so it graded a claim rather than a change.

**And then it happened again.** In the *replacement*, a check for whether a
generated task gave away its own answer worked by looking for the answer's
longer words in the task text. It rejected a meeting-notes case for
containing the word "meeting".

**The rule.** If the question is semantic, matching strings will be wrong in
both directions. This one is easy to criticise and easy to rewrite by
accident.

### 8. Telling the model a constraint is enforced when it is not

**The incident.** A choice interface rendered `SETTINGS YOU MAY ADJUST
(bounds are enforced)` above ranges written as prose — `"between 512 and
65536"` — while admission checked only that the setting's *name* had been
offered. Any value was accepted. The sentence was false, written in the same
commit that argued for typed contracts.

**The rule.** A bound shown to a model is a value, not a sentence. Refuse
out-of-range proposals with the reason; never clamp, because clamping is the
silent substitution the contract exists to prevent. Settings that genuinely
cannot be checked must render as explicitly unenforced.

### 9. Exact-set validation on anything a model produces

**The incident.** Typed records rejected any answer carrying a field the
schema did not name. An optional reporting field, documented
`affects_validation: False`, was returned in a shape the contract invited but
the stripper did not cover. Runs ended at orientation having produced
nothing. Four competitions died this way, and the refusal named the record
rather than the field, so two attempts to explain it were wrong.

**The rule.** Absence is a defect; surplus is information. A caller with more
to say than the form allows should not have its whole reply discarded. And
every refusal must name what it refused — that message is the entire guidance
the repair attempt receives.

### 10. Run-level credit for stage-level decisions

**The shape.** A run succeeds, so every decision in it is marked as having
helped. A successful run contains wasted loops, redundant loops, and locally
correct work that changed nothing. A failed run contains correct orientation,
a good diagnosis, and a valid experiment.

**The rule.** A boolean `helped` at run granularity is not a training target.
Record the granularity you actually have and say so, so a rate computed from
run-level joins is read as describing *chains* of decisions rather than
individual ones. This repository currently has exactly that limitation and
labels it.

### 11. A name that promises identity and delivers similarity

**The incident.** A lookup channel called `BY_EXACT` matched the same
*normalised situation*, not the same *activation*. Two runs meeting one
situation are separate occurrences. The name invited reading the match as
identity and would have corrupted deduplication and credit later.

**The rule.** Keep four identities apart and name them so they cannot be
confused: occurrence (this activation), signature (this situation), shape
(this unit of work), motif (this kind of problem).

### 12. A closed vocabulary presented as an open one

**The incident.** Cross-domain retrieval turned on "motifs" — four
hand-written rules, asked in order so the first match won, with everything
unanticipated collapsing to `unclassified`. The vocabulary was whatever its
author had thought of that day, and it decided all cross-domain matching.

**The rule.** Derive the vocabulary from the record's own structure. Motifs
computed from which fields carry content name *every* combination, including
ones nobody anticipated; adding a field widens the vocabulary with no list to
update; and there is no unclassified bucket, because a situation the
vocabulary cannot describe is exactly the one worth finding again.

### 13. The same list, written down twice

**The incident, repeatedly.** A 30-field schema shown to the model and the
`required` set enforced on its answer. Selection keys in three copies. Two
builders of the same result record — the ownership tally was added to the one
that is not persisted, so it never reached disk.

**The rule.** Derive, never restate. Where a second copy is genuinely needed
(a schema example documents a type per field), add a test that parses both
and fails when they drift.

### 14. Reasoning that looks fine because the record was never read back

**The shape.** A store that is written and never loaded. Every run begins as
though nothing has been done. It passes every test, produces plausible
artifacts, and learns nothing.

**The incident.** Stage records were keyed to each run's own directory, so
every run read only what it had written — the same as reading nothing. Three
runs produced three isolated files.

**The rule.** Test the *second* run. A learning system's first run proves
nothing about it.

---

## Part II — The invariants these imply

1. Every task-conditioned decision is owned by an LLM-reasoned Loop or an
   explicit human instruction, and carries a record of who owned it.
2. Deterministic code states what is possible, enforces what is safe, and
   records what happened. It does not state what is wise.
3. When reasoning is unavailable, the system waits, restores a route, asks
   for authority, preserves its incumbent, or returns a precise blocker. It
   does not quietly become a different kind of system.
4. Instrumentation cannot fail a run, and cannot hide that it failed.
5. Advice derived from history is recorded and not obeyed until an experiment
   says it should be. Acting on it early makes the experiment impossible,
   because the record then only confirms what it already said.
6. Below its evidence floor, every estimator declines to estimate and says
   why. Silence is a finding; a confident number from four observations is a
   guess wearing provenance.
7. Ask models for observations; derive verdicts.
8. Bounds shown are bounds enforced.
9. Absence is a defect; surplus is information.
10. Randomise experiments on occurrences, never on classes.

---

## Part III — Where the cheap-model work actually starts

The instinct to stop paying frontier prices for every step is right, and the
order matters. The first savings are not in replacing the answer.

**What is safe to reuse first** — these change the *starting point* without
touching the decision:

- which response shape suits this kind of stage
- which questions usually matter here
- what context is worth retrieving
- what verification usually follows
- which model capabilities have sufficed before

**What is dangerous to reuse first**: the semantic decision itself, and any
cached prior answer.

**Small models belong at the stage, not the task.** A single task can use a
strong reasoner to orient, a small structured-output model to extract, a
code model to implement, and an independent stronger model to verify.
Choosing per task is the mistake; choosing per stage is the point of having
stages at all.

**The ladder, not the pick.** Order routes cheapest-first where the evidence
supports it and escalate on failure, so being wrong costs a retry rather than
a wrong answer. A ladder that starts too low degrades into a slower correct
answer; one that starts too high overpays silently, forever.

**The maturity ladder for any shortcut** — n-gram, embedding, LSH, decision
tree, or small tuned model:

```text
L0  reasoning decides, from scratch
L1  prior stages retrieved as advisory evidence
L2  one strong candidate prefilled; reasoning accepts or modifies
L3  a shortcut predicts in shadow; reasoning never sees it
L4  the shortcut proposes; reasoning confirms or overrides
L5  narrow qualified regions select automatically, with escalation
```

Nothing skips a rung. The gate between L3 and L4 is an experiment, not a
threshold: agreement between shortcut and reasoning is not evidence the
shortcut is right, only that it has learned to imitate.

**Evidence maturity, honestly.** Hundreds of observations characterise a
mechanism. Thousands support a regional hypothesis. Broad automatic policy
needs a corpus that is *varied*, not merely large — a million activations of
one repeated template is one observation with a large exponent.

---

## Part IV — Reading a claim about this system

When this system, or an agent working on it, reports progress, these are the
questions that separate a working mechanism from a plausible one:

- Did the *second* run read what the first wrote?
- Does the estimator refuse when it has too little? Show the refusal.
- Can the control arm contain the same kind of work as the treated arm?
- Can a failing run's evidence be distinguished from a store that broke?
- Does the ladder's advice change what the run did, or is it recorded only?
  (Either is fine; claiming the wrong one is not.)
- What is the granularity of the credit, and does the record say so?
- Which numbers came from fixtures and which from live runs?

The most common failure in reporting this work is a true statement about
machinery presented as a statement about capability. "The loop is closed" was
one such: cross-run recording and shadow consultation were connected;
operational use, stage-level credit, and assisted-versus-fresh comparison
were not, and saying so plainly would have been both shorter and true.
