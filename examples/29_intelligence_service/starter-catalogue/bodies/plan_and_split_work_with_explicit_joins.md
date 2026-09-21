# Plan and split work with explicit dependencies and joins

Break a task into parts that can each be checked alone. Give every part its own goal, contract and authority. Write down what depends on what before anything is dispatched.

## When to use it

Use it when a task is too large for one step, when parts could run in parallel, or when parts will be given to separate agents or people.

## Steps

1. Give a short outline first. Expand each part into detailed steps, and name the first action that can be executed.
2. Break the task into its smallest parts that can be solved independently, and number them.
3. Give each independently governed assignment its own goal, its own contract, its own authority and the place where its result returns.
4. Make the dependencies and the join conditions explicit before dispatch. Choose serial or parallel execution for each group.
5. Check that the output of each part fits the input of the part that uses it.
6. Check that the parts together hold no more authority than the whole task was given.
7. Ask three decomposition questions:
   - Would the problem become easier when split into parts that each have an output that can be verified alone?
   - Would several diverse simple approaches, combined, beat one strong approach? Test a vote or a stack against the single best approach.
   - Is there a natural order in which a cheap early stage filters or narrows the work of a later expensive stage? Measure the cost of each stage.

## Checks

- No part has a hidden dependency on another part.
- Each part has a contract that can be checked without the other parts.
- The inputs and outputs of connected parts are compatible.
- The cumulative authority is preserved.

## Known-wrong example

A database migration is split into three parts that run in parallel. Part two silently needs a table that part one creates. On a fast machine part one finishes first and everything passes. On the production machine part two starts first and fails halfway, after it has already changed data. One written dependency and one join condition would have ordered the parts.

## What to record

- The parts, with the goal, contract, authority and return place of each.
- The dependency list and the join conditions.
- The choice between serial and parallel execution, with the reason.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work function for planning, decomposing and coordinating.
- `src/loop_engine/strings/interrogation.py`: the decomposition questions about parts, ensembles and staging.
- `src/loop_engine/strings/question_engine.py`: the question forms named `decompose` and `outline_to_detail`.

Licence: MIT. Compiled from revision eb757bc.
