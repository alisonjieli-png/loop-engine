# Review the error paths and the partial failures

Check what the code does when one of several steps fails, because that is where data is left in a state nobody designed.

## When to use it

Use it for any change that writes to more than one place, calls more than one service, or does work after it has already told the caller that the work succeeded.

## Steps

1. List every step in the operation that can fail: each write, each call, each parse, each timeout.
2. For each step, ask what has already happened when it fails, and what state that leaves behind.
3. Decide for each operation whether all steps must happen together or whether partial completion is acceptable. Write the decision down.
4. If they must happen together, check that they share one transaction, or that a repair path exists and is tested.
5. If partial completion is acceptable, check that the caller is told exactly which parts completed.
6. Check that failures are not swallowed: an empty catch block, a default value on error, or a return that reports success anyway.
7. Check that an error carries enough to act on: which step, which record, whether repeating is safe.
8. Write one test for each failure point that leaves work behind.

## Checks

- Every failure point has a written expected state.
- No error path returns a value that a caller can mistake for success.
- Operations that must happen together share a transaction or a tested repair path.
- Each partial result tells the caller which parts completed.

## Known-wrong example

A payment service charges the card, then writes the order, then sends the confirmation. The order write fails once a day when the database is busy, and the code catches the failure and continues so that the customer still gets a confirmation. Customers are charged for orders that do not exist, and support has no way to find them. Writing down the expected state after each failure would have made the missing repair path obvious.

## What to record

- The list of failure points and the expected state after each.
- The decision for each operation: all together or partial with a report.
- The tests added for each failure point.

## Source

- `src/loop_engine/catalog/protocol.py`: this repository writes a group of records as one batch with preconditions and an acknowledgement, and an adapter that cannot support an operation refuses it instead of quietly doing something weaker.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 7ed4e85.
