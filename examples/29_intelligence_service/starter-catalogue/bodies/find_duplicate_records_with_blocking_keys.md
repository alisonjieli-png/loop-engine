# Find duplicate records with declared blocking keys

Compare rows only inside groups that share a blocking key. The number of comparisons stays small, and any group that was too large to compare is reported.

## When to use it

Use it to find duplicate customers, companies or contacts in one table with name, address, email or phone columns. Use it when comparing every row with every other row is too slow.

## Steps

1. Declare which column holds which kind of value: name, address, email, phone. Declare at least one. Declare an identity column when the table has one. Otherwise rows are identified by position.
2. Refuse a table where a row identity repeats.
3. Build a comparison key for every declared field of every row.
4. Put each row into blocks by the declared blocking keys:
   - the first token of the name;
   - the sorted initials of the name tokens;
   - the leading house number of the address;
   - the exact email;
   - the last seven digits of the phone.
5. Skip a block that is larger than the block size ceiling. The default ceiling is 500. Record the blocking key, the value and the size of every skipped block.
6. Compare each pair of rows inside a block once, even when the two rows share several blocks.
7. Report every compared pair with its outcome and the blocking key that brought the rows together.

## Checks

- In the six row example of the reference implementation, 6 comparisons run in place of 15.
- The pair count equals the comparison count, and the outcome counts add up to it.
- The report says whether it is exhaustive within its blocks. A skipped block makes that statement false.

## Known-wrong example

A deduplication job drops every block above its limit without a trace. One very common first token, such as `The`, hides thousands of rows from comparison, and the report still looks complete. Here a skipped block is named in the report. The reader can add a narrower blocking key or raise the ceiling.

## What to record

- The field declaration, the blocking keys and the block size ceiling.
- For each blocking key, the number of blocks and the largest block.
- The number of rows, the number of comparisons, the outcome counts and every skipped block.

## Source

- `src/loop_engine/code_nodes/duplicate_detection.py`: `DuplicateFieldSpec`, `DuplicatePolicy`, `find_duplicates` and `summarize`.

Licence: MIT. Compiled from revision 381efec. The module imports the text operations module beside it and the typed decision module of the same package. Everything else comes from the Python standard library.
