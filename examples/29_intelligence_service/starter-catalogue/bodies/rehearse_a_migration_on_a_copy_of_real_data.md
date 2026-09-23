# Rehearse a migration on a copy of real data

Run the change against a copy of production before you run it against production, and measure what it does.

## When to use it

Use it for any migration that changes many rows, holds a lock, or cannot be undone easily. Use it whenever the test database is much smaller than the real one.

## Steps

1. Take a recent copy of the real database, in an environment that cannot reach real customers or real services.
2. Remove or replace personal data you do not need for the rehearsal, and record what you removed.
3. Record the size and shape before: row counts per table, index sizes, disk used.
4. Run the migration exactly as it will run in production, with the same runner and the same settings.
5. Measure the time, the lock duration, the log growth and the delay of any following copy.
6. Compare the result with the expected final state, row by row for a sample and by counts for the whole.
7. Run the previous version of the application against the migrated copy, to prove the release order works.
8. Rehearse the rollback as well, and measure how long it takes.

## Checks

- The copy is recent enough that its shape matches production.
- The measured time and lock duration fit inside the window you have.
- The previous application version still works against the migrated copy.
- The rollback was rehearsed and its duration is known.

## Known-wrong example

A migration takes four seconds on a test database with a thousand rows. On production it adds an index to a table of ninety million rows, holds a lock for twenty minutes and takes the shop offline during the evening peak. A rehearsal on a copy would have shown the twenty minutes and moved the work to a quiet window, or to a method that does not hold the lock.

## What to record

- The copy taken, its date and what was removed from it.
- The measured times, lock duration and growth.
- The comparison result and the rehearsed rollback duration.

## Source

- `src/loop_engine/code_nodes/database_copy.py`: this repository applies corrections by writing a new target rather than changing the source, refuses a target that already exists or that is the source itself, and records digests of what it read and wrote.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 565e133.
