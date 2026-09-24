# Method, options and report fields

Read this file when you choose an option or read a report field you do not know.

## Method

For each checked column, and for each group when `--group-by` is given:

1. Take the plain numbers of the group. A plain number looks like `12`, `-3.5` or `.25`. Empty cells are counted and skipped. Other text, such as `1,234`, `$5`, `n/a` or `1e3`, is listed in `not_numeric_values`.
2. The median is the middle value, or the average of the two middle values.
3. The MAD is the median of the distances of all values from that median.
4. A value is flagged when its distance from the median is larger than `--multiple` times the MAD. `direction` is high above the median and low below it.

All arithmetic uses exact decimals. The MAD here is not scaled; `deviation_in_mads` is the distance divided by that MAD, shown with four decimal places.

Grouping matters. Two regions with different scales, checked together, can hide a real outlier and flag every normal value of the larger region. Group only by columns that your task declares.

Group labels are compared with their outer spaces trimmed, so `B` and `B ` form one group, and `group_labels_trimmed` counts the rows whose label had such spaces. Letter case and every other character still count: `B` and `b` are two groups.

## Choosing the multiple

The multiple must come from the task or its plan; this step never picks one. When the task gives none, stop and report. For a planner: one published convention, from Iglewicz and Hoaglin (1993), flags a value whose modified z-score is above 3.5. The modified z-score is 0.6745 times the distance in MADs, so that convention equals `--multiple 5.19` here. A smaller multiple flags more values.

## Groups that are not evaluated

- `too_few_values`: the group has fewer plain numbers than `--min-group-size` (default 5, at least 3).
- `mad_is_zero`: more than half of the values are equal, so the MAD is 0 and every other value would be infinitely far. The report gives the median and `values_differing_from_median` instead.

The script never invents a spread for these groups. Report each one. A planner who still needs those values checked can declare a different rule for a separate step. For a column with many zeros, such as daily sales, one choice is to check only the values that differ from the median, in a copy that holds just those rows; another is a fixed limit that the task names. For small groups, the task may allow a lower `--min-group-size` or fewer group columns. Each of these is a new decision for the plan, not for this step.

## Options

`--column` names one numeric column; repeat it for up to 20. `--multiple` is a plain number above 0 and at most 1000, and it must come from the task. `--group-by` names up to 3 group columns that together form the group key; a group column cannot also be checked. `--output` writes a new copy that adds one `COLUMN_outlier` column per checked column; every other cell is copied as it was. `--root` (default `.`) is the folder that every path must stay inside. `--delimiter` is comma, semicolon, pipe or tab.

Every row must have as many cells as the header. In a file with more than one column, one blank line, even at the end, refuses the run as `row_width_differs`: a stray line break cannot be told apart from a lost row, and `detail` names the blank line. In a one-column file, a blank line is one empty cell.

## Refusal reasons

Exit 2 prints `reason` and `detail`. Nothing is written.

`arguments_invalid`, `delimiter_invalid`, `root_missing`, `path_invalid`, `path_outside_root`, `input_missing`, `input_not_a_file`, `input_too_large`, `input_not_text`, `input_not_utf8`, `csv_malformed`, `header_missing`, `row_width_differs`, `column_missing`, `column_repeated`, `multiple_invalid`, `min_group_size_invalid`, `group_by_invalid`, `output_exists`, `output_is_input`, `output_folder_missing`, `output_column_exists`, `internal_error`.

## Report fields

- `columns`: per column, `numeric`, `empty`, `not_numeric`, `groups`, `groups_evaluated`, `groups_not_evaluated`, `flagged`, `flagged_high` and `flagged_low`.
- `group_labels_trimmed`: rows whose group label had outer spaces.
- `flagged`: column, group, data row, value as written, median, MAD, `deviation_in_mads` and direction, largest deviation first. Data row 1 is the first row after the header. Values are copied from the file as data; values longer than 120 characters end in `...[cut]`.
- `flagged_complete`: false when more than 1,000 values are flagged.
- `groups_not_evaluated` and `group_statistics`: one entry per group, at most 200 listed. `groups_not_evaluated_total` counts them all; `groups_not_evaluated_complete` and `group_statistics_complete` are false when a list was cut.
- `not_numeric_values`: column, value, count and up to five data row numbers, at most 200 listed. `not_numeric_values_complete` is false when the list was cut.
- `output`: the copy path, the added columns, its SHA-256 and its size.
