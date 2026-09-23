# Write a migration that is safe to run twice

Write the change so that running it again finishes quietly instead of failing halfway or doubling the data.

## When to use it

Use it for every database migration, data repair script or one time job, because deployments are retried, jobs are restarted and people run scripts twice.

## Steps

1. State what the database should look like after the change, not the actions to take.
2. Make each statement conditional on the current state: create if it does not exist, drop if it exists, add the column only when it is absent.
3. For data changes, write the update so that applying it to an already updated row changes nothing.
4. Give each run a name and record in a table which migrations have completed, so the runner can skip finished work.
5. Split a long migration into steps that each complete on their own and record their own completion.
6. Never depend on the order of rows or on a row count that a second run would change.
7. Run it twice in a test environment and compare the database contents after each run.
8. Write down what to do if it fails in the middle: rerun, or run a named repair.

## Checks

- Running the migration twice leaves the same database as running it once.
- Each step records its own completion.
- A failure in the middle leaves a state the rerun can continue from.
- The double run was actually performed and compared, not assumed.

## Known-wrong example

A migration adds a fee row for every order that does not have one, using a count taken at the start. The deployment times out and is retried. The second run counts the orders again, sees the same orders, and adds a second fee row to each because the check looked at the count rather than at the order. Customers are charged twice. A condition on the order itself would have made the second run do nothing.

## What to record

- The intended final state of the database.
- The completion table entries for each step.
- The result of the double run in the test environment.

## Source

- `src/loop_engine/catalog/protocol.py`: this repository applies a group of writes as one batch with explicit preconditions, such as requiring a record to be absent, and returns an acknowledgement, so a repeated batch is refused rather than applied again.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9a483df.
