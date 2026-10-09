# Operational log completeness and order audit

Audit an operational log for missing required fields, unreadable or out-of-order timestamps, repeated ids, sequence gaps and repeats, and missing days or hours per group against a period, with coverage shares.

## What it does

Records are grouped by an optional field (site, machine, vehicle). Within each group the helper checks time order, a numeric sequence that should rise by one, and coverage: the share of expected day or hour slots in the period that hold at least one record. Runs of missing slots are reported as time gaps. Required fields and ids are checked across the whole log.

## Run it

As a library:

```python
from record_log_auditor import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 record_log_auditor.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `records` (array of object, required): log records as objects
- `timestamp_field` (string, required): field holding a YYYY-MM-DD date or an ISO 8601 date and time
- `required_fields` (array of string): fields every record must fill
- `id_field` (string): field whose values must not repeat
- `sequence_field` (string): integer field expected to rise by 1 per group
- `group_field` (string): field that splits the log, such as site or machine
- `expected_interval` (one of day, hour): one record expected per day or per hour
- `period` (object): YYYY-MM-DD range the log should cover, inclusive
- `max_issues` (integer): issues listed (default 200); counts are always complete

## Output

- `summary` (object, required): counts per issue kind and overall coverage share
- `issues` (array of object, required): first issues with record index (0-based), group, kind, detail
- `coverage` (array of object, required): per group: first and last time, expected and present slots

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `field_absent`: the timestamp, id, sequence or group field appears in no record
- `invalid_period`: the period dates are not real dates or end before they start

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `record_log_auditor.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 101 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.3.b.6.h.5` | Maintain operational records. | 47 | 6 |
| `4.A.3.b.6.h.11` | Document operational activities. | 22 | 69 |
| `4.A.3.b.6.h.21` | Maintain operational records or records systems. | 17 | 92 |
| `4.A.3.b.6.h.19` | Record operational details of travel. | 16 | 220 |

Occupations with the most of these activities: First-Line Supervisors of Security Workers (`33-1091.00`); Public Relations Managers (`11-2032.00`); Biomass Power Plant Managers (`11-3051.04`); Purchasing Managers (`11-3061.00`); Transportation, Storage, and Distribution Managers (`11-3071.00`); Farmers, Ranchers, and Other Agricultural Managers (`11-9013.00`).

Example O*NET task statements linked to these activities:

- "Write reports of activities, and maintain files of impoundments and dispositions of animals." (Animal Control Workers, task `7968`)
- "Record information about pesticide applications, such as the type used and amount applied." (Pesticide Handlers, Sprayers, and Applicators, Vegetation, task `24043`)
- "Identify, analyze, and document problems with program function, output, online screen, or content." (Software Quality Assurance Analysts and Testers, task `14642`)
- "Record names, types, and destinations of vessels passing through bridge openings or locks, and numbers of trains or vehicles crossing bridges." (Bridge and Lock Tenders, task `7151`)

## Limits

Timestamps are YYYY-MM-DD dates or ISO 8601 date-times; offsets are converted to UTC before slots are counted, so local midnight can shift a record to another day. One record per slot counts as covered; the helper does not check how many records a slot should have. Sequence values must be integers; other values are skipped.

This kit is a candidate component. Generating it did not approve or qualify it.
