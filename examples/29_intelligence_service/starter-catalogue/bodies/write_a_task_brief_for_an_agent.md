# Write a task brief for an agent

Write the assignment so that a capable worker who knows nothing about your project can finish it and you can check the result.

## When to use it

Use it whenever you hand work to an automated agent, a separate process or a new team member, and whenever the last attempt came back almost right.

## Steps

1. State the goal as the finished thing, not as the activity. Say what will exist when it is done.
2. Give the context the work needs: where the code lives, which part of it matters, and what has already been tried and rejected.
3. Name the exact inputs by path or identifier, and say which of them may be changed and which may not.
4. State the acceptance conditions as checks, with the command to run and the expected result.
5. State the limits: what may be written, what may be run, what may be reached over the network, what may be spent, and what must never happen.
6. State how to report back: what to return, in what shape, and what to do with a partial result.
7. Say what to do when blocked: which questions to ask, which decisions to make alone, and when to stop.
8. Read the brief once as if you knew nothing else about the work, and repair anything you could only answer from memory.

## Checks

- The goal names a finished thing, not an activity.
- Every input is named exactly and marked changeable or not.
- The acceptance conditions are commands with expected results.
- The limits and the reporting shape are stated.

## Known-wrong example

A brief says to improve error handling in the payments module. The agent wraps every call in a catch block that logs and continues, which removes the failures that a caller relied on and turns a refused payment into a silent success. The brief never said which behaviour mattered or how the result would be checked. Two acceptance conditions would have prevented all of it.

## What to record

- The brief as given, unchanged.
- The acceptance conditions and their results.
- The questions the worker had to ask, which show what the brief left out.

## Source

- `src/loop_engine/core/external_harness.py`: when this repository hands work to a separately started agent process, the goal, the authority, the evaluation and the record of what happened stay with the caller, and the outside process supplies only the mechanics.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 40fce69.
