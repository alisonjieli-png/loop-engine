# Multi-source table merge with provenance and conflicts

Compile one table from several CSV sources by mapping columns to target fields, converting units, matching on key fields, taking values by source priority, recording which source gave each value and listing disagreements.

## What it does

Each source declares a priority, a mapping from target field to its own column and optional unit multipliers. Rows are matched on the key fields. For each field the merged row takes the first non-empty value in priority order and records the source. Different non-empty values (numbers beyond the relative tolerance, text after case folding) are listed as conflicts with every value. Rows without a full key are skipped.

## Run it

As a library:

```python
from multi_source_table_merge import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 multi_source_table_merge.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `target_fields` (array of string, required): fields of the merged table, in output order
- `key_fields` (array of string, required): target fields that identify a row across sources
- `sources` (array of object, required): sources with a name, CSV text, a priority (1 wins), a mapping of target field to source column and optional unit multipliers per target field
- `numeric_tolerance` (number): relative difference below which numbers agree (default 0)

## Output

- `rows` (array of object, required): merged rows in first-seen key order with values and provenance
- `conflicts` (array of object, required): fields where sources disagree, with every value
- `summary` (object, required): rows per source, keys, conflicts, filled share per field

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `header_missing`: a source's CSV text has no header row
- `mapping_column_absent`: a source maps a target field to a column its CSV does not have
- `key_not_mapped`: a source does not map every key field
- `unknown_target_field`: a mapping or unit names a field that is not a target field
- `duplicate_key_in_source`: one source holds two rows with the same key
- `duplicate_source_name`: two sources share a name
- `unit_on_text_value`: a unit multiplier applies to a value that is not a number

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `multi_source_table_merge.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 63 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.2.a.2.c.3` | Compile data or documentation. | 31 | 7 |
| `4.A.2.a.2.c.2` | Compile technical information or documentation. | 10 | 195 |
| `4.A.3.b.6.h.18` | Record research or operational data. | 22 | 43 |

Occupations with the most of these activities: Legislators (`11-1031.00`); Environmental Compliance Inspectors (`13-1041.01`); Regulatory Affairs Specialists (`13-1041.07`); Appraisers of Personal and Business Property (`13-2022.00`); Software Quality Assurance Analysts and Testers (`15-1253.00`); Digital Forensics Analysts (`15-1299.06`).

Example O*NET task statements linked to these activities:

- "Document patient information including session notes, progress notes, recommendations, and treatment plans." (Clinical and Counseling Psychologists, task `22165`)
- "Organize material and complete writing assignment according to set standards regarding order, clarity, conciseness, style, and terminology." (Technical Writers, task `3966`)
- "Keep records and prepare reports detailing findings, investigative methods, and laboratory techniques." (Forensic Science Technicians, task `18478`)
- "Compile, sort, and verify the accuracy of data before it is entered." (Data Entry Keyers, task `11402`)

## Limits

Keys must match exactly after trimming; fuzzy matching belongs to duplicate_record_finder. One row per key per source; repeated keys are refused. Unit conversion is a multiplier only, so offsets such as temperature scales are not supported. Text values are compared after case folding, so a change of capital letters is not a conflict.

This kit is a candidate component. Generating it did not approve or qualify it.
