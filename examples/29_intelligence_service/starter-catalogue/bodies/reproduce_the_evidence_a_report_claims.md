# Reproduce the evidence a report claims

Run the numbers again yourself from the stated inputs, rather than accepting a table you cannot rebuild.

## When to use it

Use it before you rely on a benchmark, a measurement, an accuracy claim or a cost figure, whether it came from an agent, a colleague or another project.

## Steps

1. Ask for the exact inputs: the data set, the revision, the commands, the settings and the environment.
2. Check that the claim names its denominator. A percentage without the number of cases cannot be checked.
3. Run the stated commands yourself, in a clean environment, and record what you get.
4. Compare your numbers with the claim. A small difference needs an explanation; a large one needs the work stopped.
5. Check what was excluded. Failed runs, timed out cases and unparseable answers removed from a denominator change the result silently.
6. Check that the comparison is fair: the same cases, the same grader, the same settings on both sides.
7. Look for the measurement that was taken on a different thing from the one being claimed, such as a component check reported as a whole system result.
8. Record what you could reproduce, what you could not, and what you did not try.

## Checks

- The inputs were stated exactly enough to run again.
- Your numbers and the claim agree, or the difference is explained.
- Exclusions are counted and reported.
- The measured thing and the claimed thing are the same thing.

## Known-wrong example

A report says a change made the importer forty percent faster. Rebuilt, the measurement used a data set with the largest customer removed, because those runs failed. The failures were the slow cases. With them included the change is slightly slower. Asking for the exclusions would have shown it before the change was adopted.

## What to record

- The stated inputs and the commands you ran.
- Your numbers beside the claimed numbers.
- What you could not reproduce and what you did not attempt.

## Source

- `src/loop_engine/core/independent_verification.py`: in this repository the exact comparisons of a check run in the controlling process, outside the code being judged, so a claim is not confirmed by the thing that made it.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 40fce69.
