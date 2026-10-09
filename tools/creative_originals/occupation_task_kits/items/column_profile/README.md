# Column profile of a CSV table

Summarize each column of a CSV without declared rules: missing values, distinct values, inferred type, frequent values, value shapes, lengths, quartiles, mean, standard deviation, outliers, date ranges, duplicate rows and constant or mostly empty columns.

## What it does

The inferred type is the narrowest that every present value fits: boolean, integer, number, ISO date or string. Shapes replace digits with 9 and letters with A or a, which shows mixed formats quickly. Number columns get quartiles by linear interpolation, the population standard deviation and a count of values outside the interquartile fences. Table checks find exact duplicate rows, constant columns and columns more than half empty.

## Run it

As a library:

```python
from column_profile import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 column_profile.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `csv_text` (string, required): CSV with a header row
- `top_values` (integer): most frequent values listed per column (default 5)
- `outlier_factor` (number): interquartile range multiple for outlier fences (default 1.5)
- `missing_markers` (array of string): cell values treated as missing besides empty text (default NA, N/A, null)

## Output

- `table` (object, required): row and column counts and table-level findings
- `columns` (array of object, required): one profile per column in header order

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `header_missing`: the CSV text has no header row
- `duplicate_column_name`: two columns share a name
- `ragged_rows`: a row has a different number of cells than the header

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `column_profile.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 60 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.2.a.2.a.6` | Evaluate data quality. | 9 | 164 |
| `4.A.3.b.6.h.18` | Record research or operational data. | 22 | 43 |
| `4.A.2.a.2.c.3` | Compile data or documentation. | 31 | 7 |

Occupations with the most of these activities: Remote Sensing Technicians (`19-4099.03`); Dietitians and Nutritionists (`29-1031.00`); Legislators (`11-1031.00`); Appraisers of Personal and Business Property (`13-2022.00`); Data Warehousing Specialists (`15-1243.01`); Geographic Information Systems Technologists and Technicians (`15-1299.02`).

Example O*NET task statements linked to these activities:

- "Perform quality control analyses to ensure accuracy of test results." (Medical and Clinical Laboratory Technicians, task `24036`)
- "Document patient information including session notes, progress notes, recommendations, and treatment plans." (Clinical and Counseling Psychologists, task `22165`)
- "Keep records and prepare reports detailing findings, investigative methods, and laboratory techniques." (Forensic Science Technicians, task `18478`)
- "Compile, sort, and verify the accuracy of data before it is entered." (Data Entry Keyers, task `11402`)

## Limits

Type inference is strict: one stray text value makes a number column a string column, which is itself a finding. Dates are recognized only in YYYY-MM-DD form. Outlier fences assume a single group; mixed populations need splitting first. Values are trimmed before counting.

This kit is a candidate component. Generating it did not approve or qualify it.
