# The troubleshooting ladder

Every error gets these seven questions, in this order, before a fix is
written. The order matters: it forces the cheap, local explanations to be
considered and *ruled out* rather than skipped, and it forces the honest
answer when the cheap explanation is not available.

0. **Preserve and validate the evidence.** Before asking why the system
   failed, prove what actually happened. Classify the run with
   `core.run_validity`: did the intended experiment execute at all? A run that
   never reached the model cannot support a claim about prompts, context,
   cycles, or task difficulty, and using it that way attributes an
   infrastructure fault to a strategy.
1. **What was the error?** The observed behaviour, the layer it occurred in,
   and the exact message. Not a paraphrase.
2. **Can better prompts, intelligence, context, tool calling, skills, plugins,
   or other LLM/harness functionality solve it** without regressing other
   tasks?
3. **Can a better serial order of steps, or more flexible templates, solve
   it** without regressing other tasks?
4. **Could a Loop-node, mode, step order, receipt, plane, subnode, supervisor,
   or other object solve it** without regressing other tasks?
5. **What is the most generalizable fix** that addresses this instance and any
   unseen task that could reasonably be imagined?
6. **What should we avoid doing?**
7. **How does this align with the AGI fabric?**

## Why step 0 comes first

On 2026-09-02, six live runs were used to reason about behaviour before this
gate existed. Every one had transport failures. Three had **zero completed
model calls** and were still read as evidence about task difficulty. Under
`core.run_validity` the verdict is: 6 of 6 eligible for infrastructure
analysis, 3 of 6 for semantic analysis, and **0 of 6 for comparison**.

That is the honest answer to "why are we having issues": some of the issues
were real defects, and some were conclusions drawn from runs that were never
eligible to support them. Nothing recorded said so, so nothing stopped it.

An invalid run is not worthless — it is first-class evidence about
infrastructure. It is excluded only from the questions it cannot answer, and
every exclusion is recorded with its reason, because a filter nobody can see
is how a corpus quietly becomes the runs that happened to agree.

## Answering 2, 3 and 4 honestly

These three ask whether the fix belongs in the model-facing layer, the cycle
layer, or the architecture layer. For a large share of real errors the answer
to all three is **no, and we could not know otherwise yet**.

A claim that a prompt, a context policy, or a cycle is better is a claim about
a distribution of tasks. It cannot be established from one run, or ten, or a
hundred. Until there is evidence across many thousands of runs on genuinely
novel tasks, "better prompting would fix this" is a hypothesis, not a fix, and
acting on it changes behaviour for every task on the basis of one.

**Infrastructure defects are exempt from that constraint and should be fixed
first.** A boundary that admits nothing, a terminal code that names the wrong
layer, a capacity that was declared rather than measured, a refusal that does
not say what it would accept: these are wrong on every task and every data
shape, and no volume of runs is needed to establish it. Fixing them also makes
the eventual prompt and cycle comparisons interpretable, because until they
are fixed the noise they inject is confounded with everything else.

So: if the error is infrastructure, answer 2, 3 and 4 with "no", say why, and
go to 5.

## Question 5 is the one that does the work

"Most generalizable" means the fix holds under different data shapes, inputs,
results, providers, models and task families. Test a candidate fix against:

- a different task family;
- an input an order of magnitude larger or smaller;
- a provider that fails halfway;
- a result shape nobody has produced yet.

A fix that needs a new special case for each of those is not the fix.

## Question 6: what to avoid

- Concluding that a prompt, context policy, or cycle is better from a handful
  of runs.
- Fixing the symptom named in the report rather than the cause the evidence
  supports.
- Adding a step, an operator, or a profile because the failure was confusing.
  Confusion is usually missing evidence, not missing structure.
- Hardcoding a number that could be measured.
- Widening a boundary to admit one case.
- Taking an exception to a gate to accommodate one's own change.
- Reporting a run's self-description as evidence of what it did.

## Question 7: alignment with the fabric

A fix aligns when it makes the runtime describe itself more accurately, keeps
every operation Loop-owned, leaves the model's semantic authority intact, and
records what happened in a form a later run or reader can use. A fix that
narrows what the model may choose, or that adds a rule the runtime cannot
justify from its own measurements, is pulling the other way.

---

## Worked examples from 2026-09-02

These are real errors from live runs, put through the ladder.

### A. A run reported `VERIFICATION_FAILED` having verified nothing

1. **Error.** Three runs terminated `VERIFICATION_FAILED`. Their own records
   said `verification.method` was `"not completed"`, and every recorded
   failure was `timeout`, `network_unreachable`, or `output_validation_failed`
   at the transport layer. Zero model calls completed.
2. **Prompting/context/tools?** No. The model was never reached. No prompt
   changes a terminal code computed after the run.
3. **Step order or templates?** No. The sequence was correct; it never got to
   run.
4. **Loop-node, mode, receipt, supervisor?** No. Nothing was missing from the
   architecture. The runtime already held the evidence — it simply did not
   consult it before naming the failure.
5. **Most generalizable fix.** A terminal code may name only a layer the run
   has evidence of having reached. `core.terminal_layer` derives that from the
   run's own record: orientations and decisions mean semantic work happened,
   project attempts mean execution happened, a verdict or a completed method
   means verification happened. Absent all of it, the run reached transport
   and the code says so. This holds for any task, data shape, provider or
   model, and an explicit failure code still wins over the inference.
6. **Avoided.** Special-casing the three observed error strings; adding a
   `TRANSPORT_FAILED` code when `PROVIDER_UNAVAILABLE` already existed;
   taking a size-cap exception when the module went over — the logic was
   extracted to its own module with its tests instead.
7. **Fabric.** The runtime describes itself more accurately, which is the
   property every later diagnosis depends on.

### B. Six concurrent solves saturated one provider

1. **Error.** Six solves were launched against one route. All three of the
   later ones failed at `orient` with transport errors and zero completed
   calls.
2. **Prompting/context/tools?** No.
3. **Step order or templates?** No.
4. **Loop-node, mode, supervisor?** Possibly — a supervisor that observed
   transport failures and reduced concurrency would address it. Not yet
   built, and not yet justified by evidence about where the real limit is.
5. **Most generalizable fix.** Unknown, and deliberately left unfixed. The
   generalizable version measures what the route sustains rather than
   declaring a number, which is the same rule `core.runtime_capacity` already
   applies to memory and disk. Writing a concurrency constant would be the
   defect this repository has fixed twice already.
6. **Avoided.** A hardcoded concurrency limit. Concluding from this one
   incident that concurrency is unsafe in general.
7. **Fabric.** Recorded as an open infrastructure item with its evidence,
   rather than closed with a number.

### C. A run could not read the file it had just written

1. **Error.** A generated file had a syntax error at line 131. The model
   diagnosed it correctly and could not read the file.
   `core.source.inspect` refused (not in the supplied manifest);
   `core.generated_project` refused a `cat` (commands must run the registered
   Python executable over reviewed files). Twenty passes, same conclusion.
2. **Prompting/context/tools?** Yes, in part — but not prompting. The gap was
   a missing capability, which question 2 covers under "tool calling". The
   model's reasoning was correct throughout.
3. **Step order or templates?** No. More steps would have produced more
   passes of the same correct conclusion.
4. **Loop-node, mode, receipt?** No new plane was needed.
5. **Most generalizable fix.** `core.workspace.read`: a run may read back
   anything it produced, with interpreter line numbers so a reported line can
   be looked up directly, bounded by the measured evidence allowance, refusing
   by name any path outside the workspace. Supplied inputs stay with
   `core.source.inspect`. This holds for any generated artifact in any task
   family, not only Python and not only syntax errors.
6. **Avoided.** Widening `core.source.inspect` to admit workspace paths, which
   would have blurred the input boundary for every task to fix one case.
7. **Fabric.** A run that cannot observe its own output cannot verify itself,
   and self-verification is the fabric's central claim.
