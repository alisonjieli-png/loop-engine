# Fill a large table in bounded batches

Update millions of rows without locking the table, filling the log or making the service slow for everyone else.

## When to use it

Use it when a schema change leaves existing rows to fill, when a repair must touch many rows, or when a new field must be computed for history.

## Steps

1. Count the rows to change and measure how long a small batch takes on production-like data.
2. Choose a batch size from that measurement, not from habit. Start small and raise it while you watch.
3. Order the work by a stable key, such as the primary key, and remember the last key you finished.
4. Commit after each batch. Never hold one transaction over the whole job.
5. Pause between batches, and make the pause longer when the database is busy. Watch the delay of any copy that follows the main database.
6. Make each batch safe to repeat, so a restart continues from the recorded key without redoing work incorrectly.
7. Provide a way to stop the job that takes effect between batches, and a way to resume it.
8. Report progress: rows done, rows left, current rate and the estimated finish.

## Checks

- One batch was timed on real sized data before the full run.
- The job can be stopped and resumed without loss or repetition.
- The delay of the following copy of the database stayed inside its limit during the run.
- The final count of changed rows matches the count of rows that needed changing.

## Known-wrong example

An engineer runs a single update over forty million rows in one transaction. The table is locked for eleven minutes, requests time out, the transaction log fills the disk, and the database refuses new writes. The rollback then takes longer than the update. Batches of a few thousand rows with a pause between them would have finished in an hour with nobody noticing.

## What to record

- The measured time for one batch and the chosen batch size.
- The last completed key, kept while the job runs.
- The final counts and the time the job took.

## Source

- `src/loop_engine/core/night_budget.py`: this repository grants each step a share of the time that remains instead of a fixed limit, so a long job cannot consume the whole window, and every grant is reported with the reason for its size.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9a483df.
