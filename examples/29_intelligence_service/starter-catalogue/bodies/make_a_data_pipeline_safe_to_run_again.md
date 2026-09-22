# Make a data pipeline safe to run again

A pipeline will be run again: after a failure, for a backfill or by mistake. Design each step so that a second run with the same input gives the same output, and so that readers never see a half written state.

## When to use it

Use it when writing or reviewing any scheduled job, load script or transformation that writes to a table or a partition.

## Steps

1. Ask the rerun question: when this pipeline runs again with the same input, will the output be identical byte for byte, or only identical in its row count? Only the first answer is safe.
2. Read the statements of the pipeline and list every statement that is not idempotent, such as an append or an overwrite without a declared scope.
3. Propose a rewrite for each of them with an upsert on a declared key, or with a replacement of the full partition.
4. Write to a staging partition first. Then swap it into production in one atomic step. Never update in place, so that readers always see a consistent snapshot.
5. Treat a backfill over a live partition as dangerous unless it replaces the partition in full. Use a temporary table and a swap, or a delete followed by an insert.

## Checks

- A second run of each step with the same input leaves the target unchanged. The comparison uses a checksum of the content and not only a row count.
- No step appends to a target without a key that prevents duplicates.
- Readers can query the target during a run and see either the old state or the new state.
- A backfill names the partitions that it replaces.

## Known-wrong example

A daily job appends the rows of the day to a table. It fails after the insert and before it marks the run as done. The scheduler runs it again, and the rows of that day are now in the table twice. The row count check passes on both runs, because each run inserted the expected number of rows. A replacement of the partition of that day would give the same table after one run or after five runs.

## What to record

- The list of statements that are not idempotent, with the proposed rewrite for each.
- The key of each upsert and the scope of each partition replacement.
- The result of the rerun test, with the checksums of both runs.

## Source

- `src/loop_engine/governance/candidates/part-00000.jsonl`: four candidate statements for the data engineer position, with the digests `12ad368bd931250d`, `3ec05e8681b71131`, `609e32f1daafd4d9` and `b4c5790b1fb0c283`.

Licence state: needs review. A language model generated the four source statements during work in this repository on 23 August 2026, and no person has reviewed them. The example is an illustration that was added during compilation. Compiled from revision f29bddc.
