# Choose one bounded next action

From the possible actions, choose one bounded action, or one group that is explicitly safe to run in parallel. Say beforehand what would finish the approach and what would end it.

## When to use it

Use it at every decision point in multi step work, and above all after new information or a failure.

## Steps

1. List the actions that could move the task toward a verified result.
2. Name the simplest approach that could work, and keep it as the comparison for anything more elaborate.
3. Compare the actions by expected value after cost, risk, reversibility and information gain.
4. Prefer the observation that would separate the live possibilities to one that would leave them all standing.
5. Check whether this exact approach has already failed, and what that failure forbids.
6. Say in advance what would mean that this approach is finished and what would mean that it should be abandoned.
7. Select one action. State the exact change that it should create and the observation that would show movement in the intended direction. Name the fallback for a failure.
8. Record what was considered, selected, deferred and omitted, and why the other options were set aside.
9. For a delegated choice, state the criteria, the hard constraints, the tradeoffs, the uncertainty and the tie break rule. A preference or a confidence score is never authority.

## Checks

- One action, or one group that is safe to run in parallel, is selected.
- The expected change and its observation were written before the action.
- The hard constraints are preserved and the uncertainty is visible.
- The options that were not chosen can be found later.

## Known-wrong example

After a failing build, an agent changes the compiler flags, upgrades two libraries and rewrites a module in one step. The build passes. Nobody knows which change mattered, and one of the upgrades breaks another project a week later. One bounded action with one expected observation would have found the cause and left the other two changes out.

## What to record

- The candidate actions and the comparison.
- The selected action, its expected change, its finishing rule and its abandoning rule.
- The options that were set aside, with reasons.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the questions of the step that decides the next action, and the guidance records about one next action, the baseline, the cheapest discriminating test, the stopping rule and the options not chosen.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work functions for allocating attention and for exercising judgment.

Licence: MIT. Compiled from revision 40fce69.
