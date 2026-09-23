# Profile one CSV without changing it

This file is a step template. If any required input remains unfilled, stop and report
`unrendered_step_input`. These instructions do not grant file, shell, network,
model, or spending authority.

## Assignment

Read `{{INPUT_CSV_PATH}}` and prepare a data-quality report at
`{{OUTPUT_REPORT_PATH}}` within the authorized workspace. Use at most
`{{SCAN_ROW_CAP}}` data rows. The optional schema is
`{{SCHEMA_REFERENCE_PATH_OR_NONE}}`; the optional uniqueness key is
`{{KEY_COLUMNS_OR_NONE}}`. Report disclosure level is
`{{DISCLOSURE_LEVEL}}`.

## Method

1. Confirm the input is a readable CSV. Determine its encoding and dialect
   from available evidence. If uncertain, state the assumption or stop rather
   than silently misparse it.
2. Count scanned rows and fields; report header duplication, inconsistent row
   widths, and blank cells. Interpret other missing-value markers only when
   the supplied schema defines them. Check duplicate keys only when key
   columns are supplied and present.
3. Distinguish a full scan from a capped scan. For a capped scan, do not infer
   a total row count or whole-file error rate from the sample. Record parse
   errors without copying row values into the report.
4. Write the report only if the runtime separately authorizes that exact
   output path. Do not modify the input. Include the file identity, scanned
   denominator, checks performed, exclusions, errors, and unresolved questions.
   Follow `{{DISCLOSURE_LEVEL}}`: `aggregates_only` uses column ordinals and no
   row values; `column_names_allowed` may include column names but no row
   values. Do not send data to an external endpoint.
