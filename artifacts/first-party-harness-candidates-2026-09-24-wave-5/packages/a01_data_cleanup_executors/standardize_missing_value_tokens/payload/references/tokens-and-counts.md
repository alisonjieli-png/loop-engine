# Tokens, matching and report fields

Read this file when you choose an option or read a report field you do not know.

## Options

| Option | Meaning |
|---|---|
| `--column NAME` | one column to clean; repeat it for more columns |
| `--all-columns` | clean every column; use it only when the task says every column uses these tokens |
| `--token TEXT` | one declared token; repeat it; write `--token=-` for a lone dash and `--token=--` for two dashes |
| `--ignore-case` | `N/A` then matches the token `n/a` |
| `--blank-whitespace-cells` | also empty cells that hold only spaces or tabs |
| `--allow-value-token TEXT` | confirm a declared token that looks like a real value |
| `--output PATH` | write a new copy; an existing file is never replaced |

`--root` (default `.`) is the folder that every path must stay inside. `--delimiter` is comma, semicolon, pipe or tab.

Every row must have as many cells as the header. In a file with more than one column, one blank line, even at the end, refuses the run as `row_width_differs`: a stray line break cannot be told apart from a lost row, and `detail` names the blank line. In a one-column file, a blank line is one empty cell.

## Matching rule

A cell is trimmed of outer spaces and compared with each token, exactly or, with `--ignore-case`, in any letter case. A token must match the whole cell: `n/a` does not match `n/a pending`. A token with a digit, or one of the words true, false, yes, no, y, n, t, f, on and off, is refused as `token_looks_like_a_value` unless `--allow-value-token` names it too. So `0`, `-999` and `1900-01-01` need that second declaration.

## Look-alikes

A kept cell is listed in `undeclared_lookalikes` when it equals, in any case, a declared token or one of these common spellings: `n/a`, `na`, `n.a.`, `n.a`, `null`, `nil`, `none`, `nan`, `-`, `--`, `---`, `.`, `?`, `??`, `missing`, `unknown`, `not known`, `not available`, `not applicable`, `no data`, `#n/a`, `#null!`, `(blank)`, `blank`, `empty`, `undefined`, `tbd`. A look-alike is never changed. In a country column, `NA` is a real code, and it stays safe only while NA is not declared for that column. Every declared token applies to every column the run cleans, so `--all-columns` with the token NA also blanks the code NA; `columns[].blanked_by_token` shows where. Run once for each group of columns that share the same tokens.

## Refusal reasons

Exit 2 prints `reason` and `detail`. Nothing is written.

`arguments_invalid`, `delimiter_invalid`, `root_missing`, `path_invalid`, `path_outside_root`, `input_missing`, `input_not_a_file`, `input_too_large`, `input_not_text`, `input_not_utf8`, `csv_malformed`, `header_missing`, `row_width_differs`, `column_missing`, `column_repeated`, `columns_not_declared`, `token_invalid`, `token_repeated`, `token_looks_like_a_value`, `allow_value_token_not_declared`, `output_exists`, `output_is_input`, `output_folder_missing`, `internal_error`.

## Report fields

- `columns`: one entry per cleaned column with `cells`, `blanked`, `blanked_by_token`, `whitespace_blanked`, `whitespace_kept`, `already_empty` and `kept`. The five counts after `cells` add up to `cells`.
- `totals`: the same counts summed, plus `data_rows`.
- `undeclared_lookalikes`: column, value, count and up to five data row numbers. Data row 1 is the first row after the header. Values are copied from the file as data; values longer than 120 characters end in `...[cut]`.
- `undeclared_lookalikes_complete`: false when more than 200 look-alikes are listed.
- `output`: the copy path, its SHA-256 and its size. The copy keeps every column, the delimiter and the line ending; cells are quoted only when needed.
