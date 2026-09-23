# Check a table join before trusting its output

Count the keys before a join, state the expected relationship, and reconcile the rows after it. A join that silently multiplies or drops rows is one of the most common causes of wrong numbers.

## When to use it

Use it for every join between tables in a query, a notebook or a pipeline, and after every transformation that should keep the number of rows.

## Steps

1. Before joining, count the distinct keys on both sides. When the counts do not match the expectation, investigate duplicates and null keys before going on.
2. State the expected relationship of the join explicitly: one to one, or one to many. Treat many to many as a defect, unless the fan out is deliberate and written down.
3. After each transformation, compare the row counts and the checksums with the expectation. Any difference ends the run. A note in a log is not enough.
4. Reconcile: show that every source row maps to exactly one output row. When that is not the case, list the orphans, which are the source rows without an output row, and the rows that were multiplied.

## Checks

- The distinct key counts of both sides are on record before the join runs.
- The expected relationship is written next to the join.
- The number of output rows equals the expected number, for example the number of rows on the many side of a one to many join.
- The list of orphans is empty, or every orphan is explained.

## Known-wrong example

An orders table is joined to a customers table to add the region. The customers table holds two rows for some customers, because an address change created a second row. Each order of those customers now appears twice, and the revenue by region is too high. The row count after the join was higher than the number of orders, and nobody compared them. A count of distinct customer keys would have shown the duplicates before the join.

## What to record

- The distinct key counts, the null key counts and the duplicate key counts of both sides.
- The expected relationship and the row counts before and after.
- The orphans and the multiplied rows, with the decision for each.

## Source

- `src/loop_engine/governance/candidates/part-00000.jsonl`: four candidate statements for the data engineer position, with the digests `cd39358d35120bb3`, `806a1b741fc1f7b2`, `802963b5aaf69d15` and `78fdf498d6a705cd`.

Licence state: needs review. A language model generated the four source statements during work in this repository on 23 August 2026, and no person has reviewed them. The example is an illustration that was added during compilation. Compiled from revision 9cec9d7.
