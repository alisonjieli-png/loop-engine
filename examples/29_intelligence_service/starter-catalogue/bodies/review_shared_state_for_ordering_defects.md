# Review shared state for ordering defects

Find the places where two workers can touch the same value at the same time, and decide what happens when they do.

## When to use it

Use it for any code with more than one thread, more than one process, a queue, a scheduled job, or more than one copy of a service behind a balancer.

## Steps

1. List every piece of state two workers can reach: a database row, a cache entry, a file, a counter, a module level variable.
2. For each one, ask whether a read and a later write can be separated in time by another worker's write.
3. Find every read then modify then write sequence. These are the usual defects. Replace them with one atomic operation, a conditional update on the value you read, or a lock.
4. Check that any lock has a timeout, is always released, and is taken in the same order everywhere.
5. Check that a queue consumer can process the same message twice without harm, because delivery is rarely exactly once.
6. Check for work started in the background after a response was returned, and decide who waits for it.
7. Write a test that runs the operation from two workers at once and asserts the final value.

## Checks

- Every read then modify then write sequence is either atomic or protected.
- Locks are ordered, bounded in time and released on every path.
- Repeating a message leaves the same result as processing it once.
- A test exercises two workers at once and passes repeatedly.

## Known-wrong example

A stock counter is decreased by reading the current value, subtracting one and writing it back. Under light traffic it is correct. On a sale day two orders read the same value, both write the same lower number, and the shop sells one more item than it holds. A conditional update that only writes when the value is still the one that was read would have refused the second write.

## What to record

- The list of shared state and the protection chosen for each.
- The lock order, if locks are used.
- The result of the test that runs two workers at once.

## Source

- `src/loop_engine/catalog/protocol.py`: this repository applies a group of writes with explicit preconditions, so a write that expected a record to be absent fails rather than overwriting what another writer created.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 381efec.
