# Prove a check can fail by removing the behaviour it guards

Show that a new check would catch the mistake it exists for, by taking the behaviour away for one run and watching the check fail.

## When to use it

Use it whenever you add a check, a guard, an assertion or an alarm that has never been seen to fail. A check that has only ever passed is an unproven claim.

## Steps

1. Name the exact behaviour the check protects, in one sentence.
2. Name the check that must report the problem, by its file and its name.
3. Make one small change that removes the behaviour. Return the wrong value, skip the guard or delete the validation call.
4. Run the named check alone and require that it fails.
5. Read the failure text. It must point at the removed behaviour, not at something unrelated such as an import error.
6. Put the behaviour back and run the check again. It must pass.
7. Keep the removal as a written case beside the check, so a later reader can repeat it.
8. Repeat for each separate behaviour the check claims to protect.

## Checks

- With the behaviour removed, the named check fails and no other cause explains the failure.
- With the behaviour restored, the same check passes.
- The removal was made in the code, not in the check.
- Each claimed behaviour has its own removal.

## Known-wrong example

A team adds a check that a settings file holds no plain text password. It passes on every run. A year later a password is added and the check still passes, because the check read a file path that no longer exists and treated the missing file as clean. Removing the guard once, or putting an invented password in the file once, would have shown that the check could never fail.

## What to record

- The behaviour, the check and the exact removal.
- The failing output with the behaviour removed.
- The passing output with the behaviour restored.

## Source

- `src/loop_engine/core/independent_failure_review.py`: this repository requires a revised check to fail on a deliberately emptied subject before the revision is accepted, so a weakened check cannot pass as a repair.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 1700841.
