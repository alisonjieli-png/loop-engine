# Format tokens, options and report fields

Read this file when you write a format or read a report field you do not know.

## Tokens

Tokens are upper case. Every other character in a format must match exactly.

| Token | Matches | Example value |
|---|---|---|
| `YYYY` | a four-digit year | 2025 |
| `YY` | a two-digit year; needs `--two-digit-year-base` | 25 |
| `MM` | a two-digit month, 01 to 12 | 04 |
| `M` | a month of one or two digits | 4 |
| `DD` | a two-digit day | 03 |
| `D` | a day of one or two digits | 3 |
| `MON` | an English three-letter month name, any case | Apr |
| `MONTH` | a full English month name, any case | April |

A format has one year, one month and one day token. `M` and `D` need a separator between them and any other digit, so `YYYYMD` is refused and `YYYYMMDD` is accepted. A `%` directive such as `%d/%m/%Y` is refused. Values are trimmed of spaces at both ends before matching.

Upper-case `D` and `M` always start a token, and so does `YY`, even inside a word. There is no escape. A format therefore cannot hold literal text with these letters, such as the time zone `MDT` in `DD/MM/YYYY MDT` or the weekday `Day` in `Day DD/MM/YYYY`. Such a format has too many tokens and is refused as `format_invalid`; `detail` lists the tokens it read, for example `reads DD, MM, YYYY, M, D`. Lower-case letters and other characters are literal and must match exactly. Values that carry a time zone or a weekday are held as `no_declared_format_matches`, and removing that text is a separate, planned step.

With `--two-digit-year-base 1950`, a `YY` value falls in 1950 to 2049: 49 becomes 2049 and 50 becomes 1950.

## How one value is decided

Every declared format is tried. A value is parsed when at least one format gives a real calendar date and every format that gives one gives the same date. The first such format in the declared order is credited in `parsed_by_format`. Order never settles a disagreement.

## Hold reasons

- `ambiguous`: two formats give different real dates. `readings` shows each.
- `invalid_calendar_date`: a format matched the shape, but the date does not exist, such as 2025-02-30.
- `no_declared_format_matches`: no format matched the value.
- `outside_declared_range`: the date is before `--earliest` or after `--latest`.

## Refusal reasons

Exit 2 prints `reason` and `detail`. Nothing is written.

`arguments_invalid`, `delimiter_invalid`, `root_missing`, `path_invalid`, `path_outside_root`, `input_missing`, `input_not_a_file`, `input_too_large`, `input_not_text`, `input_not_utf8`, `csv_malformed`, `header_missing`, `row_width_differs`, `column_missing`, `column_repeated`, `format_invalid`, `format_repeated`, `too_many_formats`, `two_digit_year_base_missing`, `two_digit_year_base_invalid`, `range_invalid`, `output_exists`, `output_is_input`, `output_folder_missing`, `output_column_exists`, `internal_error`.

## Report fields

- `counts`: data rows, empty cells, parsed values and held values.
- `mixed_conventions`: format pairs that read some value differently while each also reads values the other cannot. The column then holds two conventions, and a person must decide.
- `held_values`: one entry per distinct held value with its count and up to five data row numbers. Data row 1 is the first row after the header. Values are copied from the file as data; values longer than 120 characters end in `...[cut]`.
- `held_values_complete`: false when more than 500 distinct values are held.
- `output`: the copy path, the added column, its SHA-256 and its size.

## Options

`--root` (default `.`) is the folder that every path must stay inside. `--delimiter` is comma, semicolon, pipe or tab. `--output-column` renames the added column. The copy keeps the input's delimiter and line ending, and quotes cells only when needed.

Every row must have as many cells as the header. In a file with more than one column, one blank line, even at the end, refuses the run as `row_width_differs`: a stray line break cannot be told apart from a lost row, and `detail` names the blank line. In a one-column file, a blank line counts as one empty value.
