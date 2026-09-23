# Turn an incident into a check that would have caught it

Convert a lesson into something that runs by itself, and prove that it fails on the case it was written for.

## When to use it

Use it at the end of every incident review, and whenever a manual check keeps finding the same kind of problem.

## Steps

1. Write the failure as one sentence: this condition held, and nothing noticed for this long.
2. Decide where the check belongs: a test that runs before merging, a check in the build, a validation at the boundary, or an alarm on a running system. Earlier is cheaper.
3. Write the check so it would have failed on the exact case. Take the values from the timeline, not from an invented example.
4. Run it against the state before the repair, or reconstruct that state, and require it to fail.
5. Run it after the repair and require it to pass.
6. Check its cost: how often it runs, how long it takes and how often it will report something that is not a problem. A check that cries wolf gets turned off.
7. Give it an owner and a note saying which incident it came from, so a later reader does not delete it as unexplained.
8. Resist turning one incident into a general rule for everything. One case is evidence for one check, not for a policy.

## Checks

- The check fails on the reconstructed case from the incident.
- It passes after the repair.
- Its cost and its rate of false reports are measured, not assumed.
- It names the incident it came from and has an owner.

## Known-wrong example

After an outage caused by a full disk, a team adds an alarm at ninety percent. It fires every week during normal growth, everyone silences it, and the next full disk goes unnoticed. An alarm on the time remaining until the disk fills, tested against the recorded growth from the incident, would have fired once and meant something.

## What to record

- The failure sentence and the case taken from the timeline.
- The check, where it runs, and the evidence that it fails on that case.
- Its cost, its false report rate and its owner.

## Source

- `src/loop_engine/core/heuristic_adoption.py`: this repository refuses to adopt a general rule before a declared number of recorded runs supports it, while still allowing an exact fix for a known case.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9cec9d7.
