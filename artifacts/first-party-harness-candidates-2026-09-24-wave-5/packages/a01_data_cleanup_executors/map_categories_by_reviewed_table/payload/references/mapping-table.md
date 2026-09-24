# Mapping table, matching rule and report fields

Read this file when a table is refused or a report field is unclear. The file `examples/mapping-table.json` shows the shape with synthetic labels; it is reviewed for the column `example_status` only.

## Table format

The table is one strict JSON object with exactly these keys:

| Key | Value |
|---|---|
| `record_type` | `category_mapping_table/v1` |
| `columns` | the column names this table was reviewed for |
| `reviewed_by` | the person or step that reviewed it |
| `reviewed_on` | the review date, written YYYY-MM-DD |
| `targets_map_to_themselves` | `true` when a value that already equals a target keeps that target |
| `entries` | a list of objects with `from`, `to` and an optional `note` |

Repeated JSON keys and non-numbers such as `NaN` are refused. Each `from` and `to` is nonempty text of at most 200 characters.

The script reads only this JSON record. A CSV mapping sheet, a plain list or prose is refused as `table_invalid`. The person or step that reviews the mapping writes the record, with its `reviewed_by` and `reviewed_on`; that is a separate step, never the step that maps the column.

## What the script can and cannot check

The script cannot see a review. `reviewed_by` and `reviewed_on` hold what the table's author wrote. The guarantee comes from the host that supplies the table: it keeps the file out of reach of this step's edits, and it can pass the reviewed table's SHA-256 with `--table-sha256`. Any other table bytes are then refused as `table_digest_differs`, before any value is mapped. Letter case in the digest does not matter.

## Matching rule

A value and each `from` are compared by one key: Unicode NFC form, letter case folded one letter at a time, runs of spaces collapsed to one space, ends trimmed. So ` SHIPPED `, `shipped` and `Shipped` share the key `shipped`. A letter is folded only to one lower-case letter: the German sharp s stays one letter and does not match `ss`, and a one-character ligature such as fi does not match the two letters f and i. Nothing else is folded: hyphens, accents and spelling differences stay different. A cell that is empty or holds only spaces counts as empty. The mapped value is the `to` text exactly as the table writes it.

## Table checks

The table is refused before any value is mapped when:

- `table_digest_differs`: `--table-sha256` is given and the table's bytes have another SHA-256.
- `table_invalid`: the shape above is broken, or the file is not JSON.
- `table_not_reviewed`: `reviewed_by` is blank or `reviewed_on` is not a real date.
- `table_not_for_this_column`: `columns` does not list `--column`.
- `table_empty`: `entries` is empty.
- `table_conflicting_entries`: two entries give one key two targets, or an entry sends a target elsewhere while targets map to themselves.
- `table_chained_entries`: one entry's target is another entry's source with a different target, so a second pass would change the result.
- `table_targets_collide`: two targets differ only in case or spacing.

An entry repeated with the same target is counted in `table.duplicate_entries` and is not refused.

## Other refusal reasons

Exit 2 prints `reason` and `detail`. Nothing is written.

`arguments_invalid`, `delimiter_invalid`, `root_missing`, `path_invalid`, `path_outside_root`, `input_missing`, `input_not_a_file`, `input_too_large`, `input_not_text`, `input_not_utf8`, `csv_malformed`, `header_missing`, `row_width_differs`, `column_missing`, `column_repeated`, `output_exists`, `output_is_input`, `output_folder_missing`, `output_column_exists`, `internal_error`. The input limit is 64 MiB and the table limit is 8 MiB.

Every row must have as many cells as the header. In a file with more than one column, one blank line, even at the end, refuses the run as `row_width_differs`: a stray line break cannot be told apart from a lost row, and `detail` names the blank line. In a one-column file, a blank line is one empty value.

## Report fields

- `counts`: data rows, empty cells, mapped values and unmapped values.
- `mapped_by`: how many values matched an entry and how many matched a target directly.
- `mapped_values_changed`: mapped values whose text differs from the input text.
- `target_counts`: rows per target.
- `unused_entries`: entries no value used, at most 200 listed; review them, they may be stale. `unused_entries_total` counts them all.
- `unmapped_values`: one entry per key with its count, up to five spellings as written and up to five data row numbers. Data row 1 is the first row after the header. Keys and spellings are copied from the file as data; text longer than 120 characters ends in `...[cut]`.
- `unmapped_values_complete`: false when more than 1,000 keys are unmapped.
- `table`: the table path, its SHA-256, `sha256_pinned` (true when `--table-sha256` was given and matched), its reviewer and date, and its sizes.

`--root` (default `.`) is the folder that every path must stay inside, including the table. `--delimiter` is comma, semicolon, pipe or tab. `--output-column` renames the added column.
