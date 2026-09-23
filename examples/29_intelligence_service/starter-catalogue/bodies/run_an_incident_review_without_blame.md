# Run an incident review without blame

Look for the conditions that let a mistake become an outage, because the person who pressed the key is the least useful thing you can find.

## When to use it

Use it after any unplanned interruption, data loss, security event or near miss, while the memory is fresh and before the next one.

## Steps

1. Hold the review within a few days, with the people who were there and one person to run it who was not.
2. State the rule out loud: nobody is named as a cause. Actions are described by role.
3. Build the timeline from evidence first: log entries, messages, deployments, alarms, with times.
4. For each decision in the timeline, ask what that person knew at that moment. Judging with later knowledge teaches nothing.
5. Ask why the system allowed it: which check was absent, which signal was missing, which surface made the wrong action easy.
6. Ask why it took so long to notice and so long to recover, as two separate questions.
7. Write actions that change the system, each with one owner and a date. An action that says be more careful is not an action.
8. Publish the review where the whole organisation can read it, and check the actions at a later date.

## Checks

- The timeline is built from evidence with times, not from memory alone.
- Every decision is judged by what was known at that moment.
- Each action changes a system, has an owner and has a date.
- The review is readable by people who were not involved.

## Known-wrong example

A review concludes that an engineer ran the wrong command and should be more careful. Four months later a different engineer runs the same command with the same result, because the tool still accepted it without a confirmation, in an environment whose name looked like the test one. The finding pointed at a person, so nothing about the system changed.

## What to record

- The timeline with evidence and times.
- The conditions that allowed the event, and the gaps in noticing and recovering.
- The actions with owners, dates and their state at the later check.

## Source

- `src/loop_engine/core/independent_failure_review.py`: when a check fails here, a separate review decides whether the work or the check was wrong before any repair, using a closed set of classifications and evidence quoted from the subject.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 390643e.
