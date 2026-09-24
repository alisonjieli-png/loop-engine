# Marks, options and report fields

Read this file when you choose an option or read a report field you do not know.

## Declared marks

| Option | Values | Notes |
|---|---|---|
| `--decimal-mark` | `period`, `comma` | required |
| `--grouping-mark` | `comma`, `period`, `space`, `apostrophe`, `underscore`, `none` | required; `space` also accepts the no-break and narrow no-break spaces; `apostrophe` also accepts the typographic apostrophe |
| `--group-style` | `thousands` (default), `indian` | thousands: 1,234,567; indian: 12,34,567 |
| `--currency` | one spelling, repeatable | spellings of the column's one currency, such as `$`, `USD` and `US$`; letters match in any case |
| `--percent-sign` | `hold` (default), `strip`, `divide` | strip: 12.5% gives 12.5; divide: 12.5% gives 0.125 and a value without % is held |
| `--negative-parentheses` | flag | (12.50) gives -12.50 |
| `--allow-leading-zeros` | flag | 007 gives 7 instead of a hold |
| `--hold-convention-sensitive` | flag | holds values that the swapped marks read differently even in a column with no value written the other way |

A currency spelling has 1 to 8 characters and no digit, space, sign, mark or percent sign. Grouping marks may appear only before the decimal mark. A value may start with `.5` but not end with `5.`. A sign may stand before or after a leading currency, as in `-$5` and `$-5`, but not after the number. A space may follow a leading currency, as in `USD 7` and `$ -5`, but not a sign, so `- $5` is held. With `--negative-parentheses`, `($1,234.56)` is read, but the accounting layout `$(1,234.56)`, with the currency outside the parentheses, is held as `parentheses_misplaced`.

## The swapped reading

When the declared marks are the period and comma pair, each value is also read with the two marks swapped. A value that only the swapped reading accepts is held as `other_convention`, with `other_reading`. One such value is evidence that the column mixes conventions: `column_mixes_conventions` is then true, and every value that both readings accept with different results, such as 2,500 (2500 or 2.500), is held as `convention_sensitive` with `declared_reading` and `other_reading`. It stays empty in the copy. Without that evidence these values are parsed and counted in `convention_sensitive_parsed`, unless `--hold-convention-sensitive` is given. Other declared marks have no swapped reading, so a stray mark is held as `undeclared_character`.

## Hold reasons

- `no_digits`: the value has no digit, such as `abc` or `$`.
- `undeclared_character`: a character is not a digit or a declared mark; `characters` lists it. When the value holds a whole declared currency spelling in a place the rules do not read, the reason is `currency_misplaced` instead.
- `other_convention`: only the swapped marks read the value.
- `convention_sensitive`: both readings accept the value with different results, and the column mixes conventions or `--hold-convention-sensitive` is given.
- `grouping_mismatch`: group sizes do not follow the group style.
- `grouping_after_decimal_mark`: a grouping mark stands after the decimal mark.
- `decimal_mark_repeated`: two decimal marks.
- `decimal_mark_without_digits`: nothing follows the decimal mark.
- `leading_zero`: a zero starts a longer whole number.
- `sign_repeated`: more than one sign, or a sign with parentheses.
- `space_after_sign`: a space follows a sign, as in `- $5` or `- 5`.
- `parentheses_not_declared`: parentheses without `--negative-parentheses`.
- `parentheses_misplaced`: with the flag, parentheses that do not wrap the whole value once, such as `-(5)` and `$(5)`.
- `currency_repeated`: a currency at both ends.
- `currency_misplaced`: a declared currency stands where the rules do not read it, such as `1$000`.
- `currency_with_percent`: a currency and a percent sign together.
- `percent_sign_not_declared`: a percent sign under `hold`.
- `percent_sign_missing`: no percent sign under `divide`.
- `too_long`: more than 60 characters or 40 digits.

## Refusal reasons

Exit 2 prints `reason` and `detail`. Nothing is written.

`arguments_invalid`, `delimiter_invalid`, `root_missing`, `path_invalid`, `path_outside_root`, `input_missing`, `input_not_a_file`, `input_too_large`, `input_not_text`, `input_not_utf8`, `csv_malformed`, `header_missing`, `row_width_differs`, `column_missing`, `column_repeated`, `marks_conflict`, `currency_invalid`, `output_exists`, `output_is_input`, `output_folder_missing`, `output_column_exists`, `internal_error`.

Every row must have as many cells as the header. In a file with more than one column, one blank line, even at the end, refuses the run as `row_width_differs`: a stray line break cannot be told apart from a lost row, and `detail` names the blank line. In a one-column file, a blank line is one empty value.

## Report fields

- `counts`, `held_by_reason`, `convention_sensitive_parsed`, `currency_seen`, `percent_values_parsed` and `parentheses_values_parsed` count data rows.
- `column_mixes_conventions`: true when at least one value is held as `other_convention`.
- `held_values`: one entry per distinct held value with its count and up to five data row numbers. Data row 1 is the first row after the header. Values are copied from the file as data; values longer than 120 characters end in `...[cut]`.
- `held_values_complete`: false when more than 500 distinct values are held.
- `output`: the copy path, the added column, its SHA-256 and its size. Numbers use a period decimal mark, no grouping and the scale as written; negative zero is written as zero.

`--root` (default `.`) is the folder that every path must stay inside. `--delimiter` is comma, semicolon, pipe or tab. `--output-column` renames the added column.
