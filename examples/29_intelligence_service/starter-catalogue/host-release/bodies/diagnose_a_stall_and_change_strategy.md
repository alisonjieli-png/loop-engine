# Diagnose a stall and change the strategy

When progress stops, find the smallest evidenced cause before trying again. A third failure of the same shape forbids another attempt of that shape.

## When to use it

Use it when the same error returns, when several attempts produce no new information, or when a check keeps failing after a repair.

## Steps

1. State the exact evidence that progress stopped.
2. Observe the failure again before changing anything, so the repair can be shown to address it and not only to coincide with it.
3. Classify the cause: understanding of the task, missing context, choice of method, behaviour of a tool, drift in the verification, integration, or routing of the work.
4. Count how often this exact failure has returned. After the third failure of the same shape, change the family of strategy, ask, or abstain.
5. State plainly what was learned from the last failure. A next action without a stated lesson is not selectable.
6. Propose changed strategies that address the diagnosed cause: configure, modify, compose, research, reframe or delegate. For each proposal, name the measurable change that the next attempt must show and the repeated action that is now forbidden.
7. Let a reviewer who did not produce the proposals compare them against the evidence, the progress, the authority, the cost, the reversibility and the original acceptance contract.
8. List the safe analytical work that remains possible even when the original effect is unavailable.

## Checks

- The new strategy differs in kind from the old one. The failed method is not repeated under different wording.
- The repeated action is named and forbidden.
- The next attempt has a measurable target.
- The diagnosis cites evidence and not a guess.

## Known-wrong example

A test fails three times with the same import error. After each failure the agent rewrites the same function and runs the test again. The error never concerned that function. A dependency is missing from the environment. Counting the repeats and classifying the cause as the environment would have ended the series after the second attempt.

## What to record

- The evidence of the stall and the classified cause.
- The number of repeats and the action that is now forbidden.
- The proposals, the chosen strategy and its measurable target.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the questions of the diagnose, propose recovery and adjudicate recovery steps, and the guidance records about recurrence, reflection before repeating, and reproducing before repairing.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work function for diagnosing and changing strategy.
- `src/loop_engine/strings/question_engine.py`: the question form named `repetition_circuit_breaker`.

Licence: MIT. Compiled from revision 565e133.
