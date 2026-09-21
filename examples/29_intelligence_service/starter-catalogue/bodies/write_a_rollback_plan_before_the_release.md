# Write the way back before the release

Decide how you would undo the change, and who decides, before you make the change rather than during the outage.

## When to use it

Use it for every release that is not trivially reversible, and for every database or settings change that goes out with one.

## Steps

1. Write down what going back means for this change: the previous version, the previous settings and the state of the data.
2. Check whether the change is reversible at all. A removed column, a sent message and a deleted file are not.
3. For anything not reversible, split the release so that the irreversible part comes last and separately.
4. Write the exact steps to go back, with the commands and the identifiers filled in, not a description.
5. Write the condition that triggers going back, as a number and a period, and decide it before the release.
6. Name the person who decides, and make sure that person can act without waiting for anyone.
7. Measure how long going back takes, by rehearsing it in a test environment.
8. After going back, keep the failed version and its evidence. Investigate afterwards, not during.

## Checks

- The way back is written as exact steps, not as an intention.
- The trigger condition is a number and a period, agreed before the release.
- The rehearsal gives a measured duration.
- An irreversible step is in its own release, after the reversible ones.

## Known-wrong example

A release goes out with a migration that drops a column. Errors appear, and the team tries to go back. The previous version selects the dropped column, so it cannot start, and the data is gone. They spend three hours restoring from a backup taken that morning and lose the day's orders. Keeping the removal for a later separate release would have made going back one command.

## What to record

- The exact steps and identifiers for going back.
- The trigger condition and the named decider.
- The measured duration from the rehearsal.

## Source

- `src/loop_engine/core/recovery.py`: this repository decides what should happen after a failure from the situation in front of it rather than from a fixed table, and records the decision together with the reason for it.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 381efec.
