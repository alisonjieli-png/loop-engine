# Procedure: Column profile of a CSV table

Follow this procedure to do the activity with the helper `column_profile.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. What does one row represent, and which column should identify it?
2. Which markers mean missing in this source (NA, -, 0, 999)?
3. Which columns do you expect to be numbers, dates and codes?

## Steps

1. Run the helper with the source's missing markers.
2. Compare inferred types with the expected types; a string where a number was expected means stray text values; the shapes list shows them.
3. Check missing_share per column against what the process should capture.
4. Look at outliers and top values for data entry errors versus real extremes.
5. Record findings, then write validation rules for record_entry_validator.

## Decision points

### Outlier treatment

- keep: choose when the value is real and verified
- correct: choose when a source document shows a typing error
- exclude from analysis: choose when the value belongs to another population; say so in the report

Default when nothing settles it: keep and flag until the owner confirms

Evidence that settles it: the source record behind the value

### Duplicate rows

- drop exact copies: choose when the rows came from a repeated export
- keep: choose when repeated events are real (two identical sales)

Default when nothing settles it: ask the data owner

Evidence that settles it: whether the source has its own row id

## Quality checks

- rows matches the source line count minus the header and blank lines.
- present plus missing equals rows for every column.
- Inferred types agree with the data dictionary, or the difference is explained.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: table checks and types; thorough: read every column's shapes and outliers | same output |
| Tools | free: this helper, OpenRefine, pandas; paid: data catalog or quality suites | same statistics |
| Outlier factor | 1.5 standard, 3 for skewed data | fewer flags with 3 |

## Stop and ask, or hand to a person

- Deciding what a field means: the data owner defines it.
- Statistical tests between groups.
