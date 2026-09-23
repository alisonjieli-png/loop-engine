# Split a large request into assignable parts

Break work into pieces that can each be finished and checked on their own, with the dependencies between them written down.

## When to use it

Use it when a request is too large for one attempt, when several workers can help at once, or when an earlier attempt failed somewhere nobody can identify.

## Steps

1. Write the whole goal and its acceptance conditions first. The pieces must add up to it.
2. Cut along outputs, not along activities. Each piece ends in something that exists and can be checked.
3. For each piece, write its inputs, its output and the condition that says it is finished.
4. Draw the dependencies. A piece may start when its inputs exist, and no piece may depend on something later.
5. Mark the pieces that can run at the same time, and the point where their outputs are brought together.
6. Make the joining an explicit piece of work with its own condition, because that is where mismatches appear.
7. Keep each piece small enough to be judged in one reading. If you cannot state its finishing condition, it is still too large.
8. Check that the pieces together satisfy the whole goal, and name anything that no piece covers.

## Checks

- Every piece has named inputs, one output and a finishing condition.
- The dependencies form no circle.
- The joining step exists and has its own condition.
- Nothing in the whole goal is left uncovered by the pieces.

## Known-wrong example

A request is split into design, build and test as three assignments. The build finishes without a checkable output, the test assignment cannot start because nothing says what correct means, and the design turns out to have assumed a field the database does not have. Splitting by output, with each piece ending in something that can be checked, would have found the missing field in the first piece.

## What to record

- The pieces with their inputs, outputs and conditions.
- The dependency order and the pieces that ran at the same time.
- Anything in the goal that no piece covers.

## Source

- `src/loop_engine/code_nodes/solution_graph_validation.py`: this repository validates a stored work graph by checking that the connections match their declared input and output types, that the graph has no circle, and that an execution order exists.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 390643e.
