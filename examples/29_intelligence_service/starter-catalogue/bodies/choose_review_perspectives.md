# Choose review perspectives for a piece of work

Review work through several named perspectives, each with one instruction, and not through one general request for feedback. Choose the perspectives that fit the stage of the work.

## When to use it

Use it when a plan, a change or a result needs review and one reviewer would only confirm what the author already believes.

## Steps

1. Identify the stage of the work: understanding the task, planning, building, verifying, handing over or recovering from a stall.
2. Choose three to five perspectives for that stage:
   - understanding: the domain expert checks meaning and usefulness. The affected user checks whether the result is understandable. The assumption finder names what is relied on without being stated and marks it as observed, derived or assumed. The contrarian argues that the wrong question is being answered.
   - planning: the reuse specialist searches for prior work. The scale reasoner asks what changes when the input grows by three orders of magnitude. The baseline advocate states the simplest approach that could work. The experiment designer names the cheapest observation that separates the live hypotheses. The cost forecaster predicts time, calls and memory.
   - building: the software engineer checks interfaces, dependencies, tests and failure handling. The numerical analyst watches precision, overflow, empty cases and placeholder values. The simplifier names what can be removed. The reproducibility engineer names every source of variation that is not pinned. The operator asks what a person sees when this fails unattended.
   - verifying: the independent verifier tries to falsify completion claims with evidence that does not come from the producer. The adversary looks for ambiguous interpretation, unsafe inputs, bypasses and false success. The statistician asks whether a difference is larger than the noise. The error analyst reads individual failures. The leakage hunter looks for information that would not exist when the result is needed.
   - handing over: the future maintainer, the documentation author, the provenance reviewer and the privacy reviewer.
   - recovering: the failure diagnostician, the strategy changer and an adjudicator who compares recovery proposals.
3. Run each perspective as its own pass with its single instruction.
4. Collect the findings for each perspective. Keep a finding that only one perspective raised.
5. Resolve the findings against the acceptance criteria of the task.

## Checks

- At least one perspective is independent of the producer of the work.
- Each finding names the perspective that raised it and the evidence behind it.
- A perspective that found nothing says what it checked.

## Known-wrong example

An author asks one reviewer whether the work is good. The answer is general praise and two style remarks. No one asked what happens at a thousand times the input size, or what fails silently at night. A named perspective turns a vague request into a question that has an answer.

## What to record

- The stage, the chosen perspectives and the reason for the choice.
- The findings by perspective, and how each was resolved.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the list of perspectives and the perspectives assigned to each step.

Licence: MIT. Compiled from revision 0cf19eb.
