# AGI LoopNode Network: a self-orienting food-for-thought prompt

Here is some more information to consider in light of the recent failures and
our desire to create an AGI LoopNode Network.

This is a supplemental steering prompt, not another implementation mandate.
Nothing below is a requirement. Every operator, cycle, transition, format and
task family is a **candidate to compare against what your repository already
has**, and the most valuable outcome of reading it may be discovering that
something here is unnecessary, already present under another name, or wrong.

> **Read this differently from the last one.** The previous version handed you
> a catalog and asked you to consider it. This one asks you to orient first,
> answer a short set of questions about your own runtime, and only then decide
> which parts of the catalog are worth your attention. A catalog read before
> orientation becomes a checklist. A catalog read after it becomes a menu.

## 0. Orient before you read the rest

Do not begin at section 1. Begin by answering these about **your** repository,
from the code and the run records rather than from documentation or memory.
Write the answers down. They determine which of the later sections are worth
reading at all.

### 0.1 What vocabulary do you already have?

1. How many distinct operations can your runtime actually perform? Count them
   from the live sources, not from a list someone maintains by hand.
2. Where does each live: a fixed step, a selectable action, a capability, a
   tool, an external harness?
3. Which of them has never been selected in any recorded run?
4. Which was selected in every run that succeeded?
5. If you cannot answer 3 and 4, **stop reading and go build that record.**
   Everything downstream in this document is unfalsifiable without it.

### 0.2 What is fixed and what is chosen?

1. Which parts of your cycle are constitutional, and which are one profile
   that nobody has ever compared against another?
2. What would it cost — in code, not in principle — to run a different
   profile? If the answer is "a rewrite", that is the finding.
3. Can a model propose an operation your vocabulary does not contain?
4. When it does, where does that proposal go?
5. If the answer to 9 is "nowhere", you have the failure described in §1.1
    and you should fix it before adding anything.

### 0.3 What do your failures actually say?

1. Take your three most recent failed runs. For each, name the layer that
    failed: task understanding, context, transport, request format, response
    format, semantic reasoning, action, verification, graph, state, or
    cognitive control.
2. How many were the same layer?
3. For each, would any addition from this document have prevented it?
4. For each, would a **removal** have prevented it?
5. Which failures were invisible to every gate you already run?

### 0.4 Where does the cost actually go?

1. Measure one real model packet. What fraction of it is repeated content?
2. What fraction is menus of options versus facts about this task?
3. How many physical model calls does one logical step cost?
4. Which of your steps make no model call at all?
5. If a step makes no model call, what does skipping it save? Measure it
    before designing profiles around it.

### 0.5 The orienting question

1. **Is your problem that the cycle is too short, or that the vocabulary has
    a hole, or that each call carries too much, or that nothing is recorded?**
    These have different fixes and only one of them is "add more steps".

Once you have written those answers, read on selectively.

## 1. What recent failures may be telling us

### 1.1 A missing operator looks exactly like bad reasoning

The most instructive failure shape is not a model that reasons poorly. It is a
model that reasons **correctly** toward an operation the runtime cannot
perform, and then repeats that correct conclusion until a budget runs out.

Watch for the signature:

- the diagnosis is right and stable across passes;
- the proposed next step is right and stable across passes;
- every attempt is refused, and each refusal is individually correct;
- the recovery ladder fires on schedule and changes nothing;
- the transcript reads like a model that cannot think, and is in fact a model
  that cannot act.

Ask:

1. Would your record distinguish this from a model that reasons badly?
2. If not, what would you have concluded from the transcript?
3. How many of your past "the model got stuck" diagnoses were this?
4. Does anything let a run say *the operation I need does not exist*?
5. Where does that report land, and who reads it?

A system that intends to improve needs the difference between "this model is
weak" and "this catalog has a hole" more than it needs any new operator,
because that difference tells it which to build.

### 1.2 Two correct boundaries can leave a hole between them

Refusals are usually right individually and wrong collectively. An input
boundary that admits only supplied files, and an execution boundary that
admits only reviewed code, are each defensible; together they may leave no way
to observe what the run itself produced.

Ask:

1. List your boundaries. For each, what does it admit and what does it refuse?
2. Take any two. Is there an operation that both refuse and neither owns?
3. Does any boundary refuse something *the run itself created*?
4. When a boundary refuses, does the message name what would be admitted?
5. Could a run enumerate what it is allowed to do, right now, in this state?

### 1.3 The cycle may be the wrong place to look

Before adding steps, establish where the cost and the failures actually are.

1. Do your failures cluster in a step, or in the content of every step?
2. Does the same failure survive a longer cycle? Try it before assuming.
3. Does it survive a shorter one?
4. Which is more likely: the model needed another stage, or it needed a
    different fact in the stage it had?

### 1.4 Context may be doing the damage

1. Is the same content rendered under more than one heading?
2. Does a label predict its contents, or must the reader check?
3. What fraction of a packet is the task, and what fraction is scaffolding?
4. Is any invalidated branch still being replayed?
5. Is a summary present whose source is gone, so a claim cannot be challenged?

### 1.5 Failure classes should not share a recovery

1. Can you distinguish provider-unavailable from request-invalid?
2. Truncated response from wrong schema?
3. Unusable content from content that violates authority?
4. Action failed from action succeeded and verification failed?
5. Does each of those trigger a different response, or the same retry?

## 2. The hypothesis, stated so it can fail

> A sufficiently expressive, typed, stateful, inspectable, recursively
> composable LoopNode can represent any bounded unit of cognition or action a
> universal solutioning system needs, and a network of them can represent
> open-ended problem solving, verification, recovery and learning.

Where "LoopNode" means the operational Loop as a vertex in a graph. If your
constitution says the runtime class is `Loop` and forbids a second hierarchy,
keep that rule. The thesis is "everything operational is Loop-owned", not
"add a class".

**Falsifying questions.** Representable is not the same as useful:

1. Name one operation that is representable this way and worse for it.
2. Name one that becomes harder to verify when wrapped.
3. Where does the abstraction cost more than it explains?
4. Does it make failure localization easier or harder? Measure, do not assume.
5. Does it encourage fragmentation into units too small to reason about?
6. Can several logical nodes be physically fused without losing history?
7. What evidence would make you abandon the thesis?

If question 7 has no answer, the thesis is not yet doing work.

## 3. A cycle grammar, not a cycle

`Orient → Question → Plan → Act → Observe → Verify → Critique → Revise` is
useful and is one profile. So are these; treat them as fragments to compose,
compare, or reject:

```text
Sense → Interpret → Predict → Act → Observe → Correct
Goal → Decompose → Select → Execute → Verify → Integrate
Question → Retrieve → Compare → Answer → Challenge → Update
Hypothesis → Experiment → Measurement → Interpretation → Revision
Generate → Critique → Repair → Re-evaluate → Select
Attempt → Fail → Diagnose → Reframe → Retry
Baseline → Challenger → Tournament → Incumbent → Continue
Observe anomaly → Localize → Test explanation → Repair → Resume
Recall prior work → Test applicability → Adapt → Compare to novel
Context request → Retrieval → Compression → Call → Context audit
```

Reference cycles at many lengths — 3, 5, 7, 10, 12, 15, 18, 24, 32, 40, 48,
56, 64 operations, and one adaptive cycle with no fixed length — are worth
sketching for your own domain. But sketch them **after** answering §0.4,
because if your optional steps make no model calls, cycle length is not your
cost and profiles are not your lever.

Ask:

1. On what should profile selection depend: task family, phase, model size,
   provider reliability, uncertainty, prior failure, branch role?
2. Can a branch use a different profile from its parent?
3. Can the profile change after a failure?
4. How do you prevent a proliferation of near-identical profiles?
5. Can you measure that a profile helped, or only that it ran?

## 4. Scales worth separating

Consider whether these deserve different treatment rather than one cycle:

- **Nano** — one bounded semantic decision, possibly part of one transaction.
- **Micro** — one short cognitive-action cycle, seconds to minutes.
- **Meso** — one coherent work unit: a ticket, an EDA branch, a pipeline.
- **Macro** — one complete solution branch with its own evidence.
- **Portfolio** — comparison across branches; incumbent and challengers.
- **Supervisor** — the task-level situation, horizons, budgets, no-progress.
- **Learning** — what this run showed, staged rather than promoted.
- **Evolution** — what many runs show about the system itself.

No Evolution Loop should approve its own change.

## 5. Operator vocabulary: derive it, do not restate it

A catalog of candidate operators across intake, orientation, questioning,
memory, hypothesis, planning, graph shaping, context compilation, action,
observation, verification, critique, recovery, integration, portfolio and
learning is useful to read once. It is dangerous to copy.

**The rule that matters more than the list**: derive your catalog from the
live sources — the steps your kernel runs, the actions your model may select,
the capabilities your runtime registers. A hand-maintained second list
describes the runtime as it was when someone last edited the list, and the
drift is silent.

Ask:

1. Is your catalog derived or restated?
2. If restated, what has already drifted?
3. Which entries are distinct operations and which are the same operation
   named twice?
4. Which are model-internal reasoning that should not be an operator at all?
5. What is the smallest unit that deserves its own identity and receipt?

## 6. A transition algebra, honestly mapped

Candidate transitions: `NEXT`, `REPEAT`, `REVISIT`, `GOTO`, `SPAWN`, `QUERY`,
`RETRIEVE`, `FORK`, `JOIN`, `RACE`, `TOURNAMENT`, `VOTE`, `ENSEMBLE`,
`DELEGATE`, `ESCALATE`, `DEESCALATE`, `PAUSE`, `RESUME`, `BACKTRACK`,
`ROLLBACK`, `REPLAN`, `RECONTEXTUALIZE`, `CHALLENGE`, `REPAIR`, `ABSTAIN`,
`TERMINATE_BRANCH`, `RETURN_INCUMBENT`, `TERMINATE_TASK`.

The useful exercise is not adding them. It is **mapping which you already
have, which you do not, and why not** — and keeping that map where it can be
read. A named transition with no mechanism realizes nothing, and a map that
does not say so is decoration.

A transition proposal should carry its source state, target, reason, evidence,
what it invalidates, expected cost, required authority, and confidence. The
model may propose; the runtime validates state freshness, graph validity,
authority, and budget.

Ask:

1. Which of the 28 do you have? Which would you actually use next week?
2. For each you lack: is it absent because it is hard, or because nobody
   needed it? Those are different.
3. Which of yours has never been proposed by a model?
4. Does any transition carry hidden behavior not visible in its record?

## 7. Logical steps versus physical calls

A person makes many small decisions while reading one page. That does not
imply many provider calls.

1. Are you making one call per named step because it is semantically right,
   or because the step list exists?
2. Can one transaction record several logical steps?
3. Does fusion reduce tokens and harm observability? Measure both.
4. Does splitting improve correction and amplify drift? Measure both.
5. Are failed transport attempts counted as completed cognitive steps?
6. Do small models do better with one narrow operation per call?
7. Do larger models do better with several related ones?
8. Can this be learned per task family, model and context size rather than
   decided once?

## 8. Test on a wide variety of tasks, not one competition

**This is the most important adjustment in this document.** A universal
solutioning system evaluated on one task family learns that family. The
failures that matter are the ones a second family exposes.

Run the same unmodified engine across families that stress different things,
and hold the engine constant while the task varies.

### 8.1 A task-family matrix

For each family, the column that matters is *what it tests that the others do
not*.

| Family | Stresses | Failure it exposes |
|---|---|---|
| Tabular ML competition | contract discovery, validation design, leakage | trained on the wrong column, well-formed |
| Text/NLP competition | representation choice, tokenization, class imbalance | metric computed on data that shaped it |
| Time-series competition | temporal splits, horizon, shift | random split that leaks the future |
| Ranking / recommendation | pairwise objectives, group structure | pointwise metric on a ranking task |
| Image competition | preprocessing cost, memory, batching | materializing what should stream |
| Synthetic Jira ticket | reproduction before repair, blast radius | patch that passes its own new test only |
| Flaky-test ticket | distinguishing intermittent from broken | "fixed" by re-running |
| Dependency-bump ticket | compatibility reasoning, regression scope | green tests, changed behavior |
| Incident postmortem | causal ordering, evidence from logs | plausible story, unsupported |
| Email triage | intent, urgency, authority, privacy | acting on a request the sender cannot make |
| Email → commitments | extracting obligations and owners | inventing a commitment nobody made |
| Text → to-do list | decomposition granularity, implicit steps | one vague item or forty trivial ones |
| To-do prioritization | dependency, cost, materiality | ordering by wording rather than by blocking |
| Meeting notes → actions | speaker attribution, tentative vs decided | recording a suggestion as a decision |
| Document QA / research | citation, contradiction, freshness | fluent synthesis with no source |
| Data cleaning | missingness semantics, encoding | filling a blank that meant something |
| Spreadsheet transform | contract inference from examples | rule that fits the sample only |
| Code review | maintainability, compatibility | approving a change nobody can revert |
| Support triage | classification under ambiguity, escalation | confident routing of an unclear case |

Ask, for your own system:

1. Which of these families have you actually run?
2. Which one would most likely break you, and why have you not run it?
3. Which failure in the right column have you already shipped once?
4. Which families share a failure mode? That shared mode is worth a gate.
5. Which family needs a cycle your current profile cannot express?

### 8.2 Generating synthetic tasks that actually test something

A synthetic task that is merely small tests nothing. Build each one around a
**known trap and an independent rubric**, and keep the rubric out of the
engine's input.

For a **synthetic Jira ticket**, vary deliberately:

- ticket clarity: precise, vague, contradictory, missing the actual ask;
- whether the described symptom is the real defect;
- whether a reproduction exists, is wrong, or is absent;
- whether the fix is one line, structural, or "do not fix, it is intended";
- whether tests exist, are wrong, or would pass on a broken fix;
- whether the blast radius is local or crosses a module boundary;
- whether the ticket asks for something the authority does not permit.

For an **email task**, vary:

- one request or several buried in prose;
- explicit deadline, implied urgency, or none;
- sender authority present or absent;
- a request that should be refused;
- personal data that must not travel;
- a thread where the latest message reverses an earlier one.

For **text → to-do**, vary:

- implicit steps a person would infer;
- items that are actually one item;
- items that depend on each other;
- an item that is already done, stated in passing;
- an item nobody can do, and should be surfaced rather than listed.

For **to-do prioritization**, vary:

- a cheap item that unblocks an expensive one;
- an urgent item with no consequence;
- two items in conflict;
- an item whose priority depends on a fact not supplied.

The rubric per task should state the trap and the correct answer, and be read
**independently of the run**, exactly as a competition's contract should be
read from its files rather than from what a run claimed about them.

### 8.3 What to measure across families

Hold the engine constant and report per family:

1. Did it discover the contract, separately from whether it produced output?
2. Did it fall into the known trap?
3. Which operators did it draw on, and did they differ by family?
4. Which cycle profile suited it, if you can run more than one?
5. Where did the cost go?
6. Which failure class occurred?
7. Did a lesson learned on one family transfer to another, or mislead?

**Discovery and execution must be counted apart.** A run that identified the
right target and failed to execute has shown something different from one that
ran cleanly on the wrong column, and pass/fail destroys the distinction that
matters most when the question is generalization.

## 9. State as a product, not a transcript

Consider separating: immutable task; situation; question frontier; work
frontier; evidence ledger with observed / inferred / assumed / disputed /
rejected / superseded; graph state and versions; branch state; solution
portfolio; runtime state; learning state; user feedback.

Ask:

1. Is the model reconstructing the task from a transcript each turn?
2. Is your frontier a living structure the model updates, or a projection
   rebuilt after the fact? They are not interchangeable, and describing the
   second as the first is the kind of drift worth catching.
3. Can one branch update its state without contaminating another?
4. Can a verifier inspect evidence without reading private reasoning?
5. Can the system name which prior decision is now invalid?
6. Can it detect that no material state changed across attempts?

## 10. Context compilation as its own responsibility

A context pack is a compiled input for one cognitive responsibility, not a
truncated transcript. Consider layering: task identity; situation; the active
question; evidence and contracts; minimal causal history; selected deep
artifacts; full source only when justified.

Ask:

1. What is the minimum for each operator? Do you know, or do you guess?
2. Can the model request another layer rather than receiving all of them?
3. Do you record why each item was included, and why a relevant-looking item
   was excluded?
4. Do you reserve output budget explicitly?
5. After the call, do you evaluate which items were used, unused, or
   misleading? If not, your context policy cannot improve.

## 11. Multiple solutions as the normal case

For open-ended work, one answer hides both uncertainty and trade-offs.

Ask at checkpoints: is this merely the first plausible approach? Is there a
simpler baseline, a materially different challenger, a cheaper option, a lower
risk one, a more interpretable one? Are the candidates diverse or reworded?
Does an ensemble improve verified performance or merely average errors? Is the
incumbent good enough to return now while exploration continues?

A bounded **sprout** — an alternative exploration — should carry a diversity
objective, a budget, a comparison target, a stopping condition, and an
expected value. A sprout that differs cosmetically is spend without evidence.

## 12. Learning, and the discipline it requires

Record at call, step, Loop, branch, run, and cross-run level. Then ask the
hard questions:

1. Can you distinguish a useful prompt from an easy task?
2. A useful context item from one merely present when things went well?
3. A useful cycle from a strong model?
4. Are provider and model effects confounded in every measurement you have?
5. Can you run an ablation, or only observe?
6. How many runs before a lesson transfers? What is your threshold, and is it
   written down?
7. Can a later run invalidate an earlier lesson, and does anything check?

Stage lessons as candidates with scope, evidence, and uncertainty. Do not
promote them to rules during a model-led phase.

## 13. A gradual proof campaign, ordered by information value

Do not begin with a full competition or a broad repository change.

P0 orient to your own architecture · P1 one structured orientation call ·
P2 compare two orientation formats · P3 one next-action decision ·
P4 dynamic operator selection · P5 batched logical steps in one call ·
P6 the same work split across calls · P7 one read-only tool action ·
P8 one tiny code action · P9 a recoverable format failure ·
P10 an action failure requiring diagnosis · P11 one-level backtrack ·
P12 multi-level backtrack and a new graph version · P13 baseline plus
challenger · P14 async challenger · P15 context overflow prevention ·
P16 context ablation · P17 provider failure and resume · P18 model variation ·
P19 cycle-profile comparison · P20 micro data analysis · P21 micro ML ·
P22 small ticket repair · P23 small research task · P24 resume and replay ·
P25 cross-run learning candidate.

**Then, before any large competition:** P26 one task from each of at least
five families in §8.1, with independent rubrics, reported side by side.

Ask: which of these gates would fail today? Run that one first. A gate you are
confident about carries no information.

## 14. What to report

For each material failure: run and event references, failure layer, failure
class, observed cause, inferred contributing causes, what remains unknown,
recovery attempted, result, architectural implication.

For the architecture: what is fixed, what is selectable, what transitions
exist, what state objects exist, how logical steps relate to physical calls,
and what is missing with the reason.

For experiments: the independent variable, what was held constant, the
measure, the result, and the limitations that bound the conclusion. **Report
negative results.** An intervention that changed nothing measurable is worth
more than an untested intuition, and dropping it quietly is how a system
convinces itself that adding things helps.

Separate honestly: proven; partially proven; implemented but untested live;
failed; still conceptual; and the AGI-scale claims that remain unproven
because nothing has tested distribution, addressing at scale, backpressure,
permission attenuation, or protocol evolution.

Then name **the next smallest experiment with the highest information value**,
and prefer the one that resolves several unknowns at once.

## 15. Closing

The existing cycle should not be discarded. It should stop being the only one,
and stop being the first place you look when something fails.

The deeper shape may be:

```text
A typed task
    ↓ a versioned situation
    ↓ a living frontier of questions and work
    ↓ a model-led choice of cognitive operator
    ↓ a runtime-validated transition
    ↓ finite Loop activations
    ↓ actions, observations, verification
    ↓ trusted state transitions and graph versions
    ↓ competing solution branches
    ↓ run history and playback
    ↓ candidate learning across calls, Loops, branches, runs, and models
```

The goal is not to make every task long. A one-line transformation needs one
activation. A repair needs reproduce, diagnose, patch, test, critique,
integrate. A competition may need thousands. A research problem may need an
anytime network that never quite finishes.

Begin by studying your failures, answering §0 from your own code, testing
across families rather than depth-first on one, and letting evidence decide
which cycles become defaults, which stay specialized, which fuse, and which go.
