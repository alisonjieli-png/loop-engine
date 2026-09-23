# Copy a table with corrections, never in place

Apply corrections and an approved dedupe proposal while copying a table to a new target. The source is never changed, and a manifest shows that it did not change.

## When to use it

Use it when cleaned data must be produced from a delimited file or a SQLite table and the original must stay available for review and for rollback.

## Steps

1. Declare the source and the target as typed locations: a delimited file, or a table inside a SQLite database file. Accept only plain table and column names made of letters, digits and underscores.
2. Refuse a target that is the source. Refuse a target that already exists. A copy never overwrites.
3. Declare each correction as a column, an operation and two thresholds. The operation returns a proposed output, a confidence and whether the value changed.
4. Refuse the copy when a corrected column is absent from the source.
5. Compute the digest of the source file before reading it.
6. For each row, skip it when the dedupe proposal lists its identity as merged. Otherwise apply only the corrections whose outcome is applied. Copy held and escalated values unchanged and count them.
7. Write the target, then compute the source digest again. When it differs from the first digest, fail. The manifest cannot vouch for a source that changed during the copy.
8. Return the manifest: source and target with their digests, the columns, the rows in, the rows out, the dropped identities, the outcome counts for each corrected column, and the statement that the copy was not in place.

## Checks

- For each corrected column, the counts of applied, held, escalated and unchanged cells add up to the rows out. The rows in equal the rows out plus the dropped identities.
- The merged row is absent from the target and named in the dropped identities.
- A second copy to the same target is refused.
- A copy without corrections and without a proposal reproduces every row.

## Known-wrong example

A cleanup runs `UPDATE` statements on the production table and keeps no copy. A wrong rule is found a week later, and the original values are gone. With a copy to a new target, the source digest proves that the original is intact, and a repaired rule can run again from it.

## What to record

- The manifest with both digests.
- The thresholds of each correction and the identity of the dedupe proposal.

## Source

- `src/loop_engine/code_nodes/database_copy.py`: `TableLocation`, `ColumnCorrection`, `copy_table` and `read_rows`.

Licence: MIT. Compiled from revision 379c271. The module uses the Python standard library modules `csv`, `sqlite3` and `hashlib`, and the threshold function of the text operations module beside it.
