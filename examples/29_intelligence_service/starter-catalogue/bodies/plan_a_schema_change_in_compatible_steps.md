# Plan a schema change in compatible steps

Change a database shape in separate releases so that the old code and the new code can both run while the change is in flight.

## When to use it

Use it whenever more than one copy of the service runs at a time, whenever a rollback must stay possible, or whenever another system reads the same tables.

## Steps

1. Write down which readers and writers touch the table, including reports, exports and other teams.
2. Add first. Create the new column, table or index as optional, with a default or nothing at all. Release and observe.
3. Write to both the old and the new shape in the next release. Do not read the new one yet.
4. Fill the existing rows in bounded batches, outside the request path.
5. Read from the new shape, with the old one still present, and compare the two for a period you decide in advance.
6. Stop writing the old shape.
7. Remove the old shape only after every reader has been released and observed, and after the period in which you might roll back has passed.
8. Never rename in one step. A rename is an add, a copy, a switch and a remove.

## Checks

- At every step, the previous release still runs correctly against the changed database.
- The change can be rolled back at each step without data loss.
- Every reader was found before the removal step, including reports and other teams.
- The comparison between the old and the new shape ran on real rows and agreed.

## Known-wrong example

A release renames a column and deploys the new code at the same time. During the rollout half of the servers run the old code, which selects a column that no longer exists, and every request from them fails. The rollback cannot restore the column contents because the rename already moved them. Adding, copying, switching and removing over four releases keeps every step reversible.

## What to record

- The reader and writer list for the table.
- The step plan with the release that carries each step.
- The comparison result before the old shape was removed.

## Source

- `src/loop_engine/core/service_runtime/http_entrypoint.py`: the host settings and the served manifest each carry an exact record version, and loading refuses a record whose version it does not support rather than reading it loosely.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision eb757bc.
