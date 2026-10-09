# Records retention and disposition date calculator

Apply a retention schedule to records: find each trigger date, add the retention period, and mark records due, due soon, on legal hold, waiting for their trigger or retained, with file names checked against a naming pattern.

## What it does

Each schedule row gives a record class, a period in years and months, the trigger (created, closed or event) and the action (destroy, archive, review). The disposition date is the trigger date plus the period, with month ends clipped (29 February plus a year gives 28 February). Legal hold always wins. Records whose trigger has not happened are listed as trigger_missing. A naming pattern check lists file names that break the convention.

## Run it

As a library:

```python
from records_retention_schedule import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 records_retention_schedule.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `as_of` (string, required): evaluation date, YYYY-MM-DD
- `schedule` (array of object, required): record classes with retention years and months, the trigger (created, closed, event) and the action (destroy, archive, review)
- `records` (array of object, required): records with id, class, created date and when known closed or event date, legal hold and name
- `review_window_days` (integer): days ahead that count as due soon (default 90)
- `naming_pattern` (string): regular expression file names must match

## Output

- `as_of` (string, required)
- `records` (array of object, required): one row per record in input order
- `summary` (object, required): records per status and per action among due records
- `naming_violations` (array of string, required): ids whose file name breaks the naming pattern

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_record_class`: two schedule rows share a record class
- `unknown_record_class`: a record names a class the schedule does not have
- `duplicate_record_id`: two records share an id
- `invalid_date`: a date is not a real YYYY-MM-DD calendar date
- `invalid_pattern`: the naming pattern is not a valid regular expression

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `records_retention_schedule.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 42 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.4.c.1.a.2` | File documents or records. | 17 | 80 |
| `4.A.3.b.6.h.9` | Maintain records, documents, or other files. | 17 | 71 |
| `4.A.3.b.6.n.4` | Maintain regulatory or compliance documentation. | 9 | 338 |

Occupations with the most of these activities: Court Reporters and Simultaneous Captioners (`27-3092.00`); Administrative Services Managers (`11-3012.00`); Financial Managers (`11-3031.00`); Industrial Production Managers (`11-3051.00`); Compensation and Benefits Managers (`11-3111.00`); Farmers, Ranchers, and Other Agricultural Managers (`11-9013.00`).

Example O*NET task statements linked to these activities:

- "File a legible transcript of records of a court case with the court clerk's office." (Court Reporters and Simultaneous Captioners, task `8658`)
- "Preserve and maintain digital forensic evidence for analysis." (Digital Forensics Analysts, task `21799`)
- "Maintain student records, including special education reports, confidential records, records of services provided, and behavioral data." (School Psychologists, task `5455`)
- "Maintain records and files of work and revisions." (Technical Writers, task `3967`)

## Limits

The helper computes dates; it does not decide the retention periods, which come from law, contracts and policy. It never deletes anything. Time zones are ignored because all dates are calendar dates. Event triggers need the event date in each record.

This kit is a candidate component. Generating it did not approve or qualify it.
