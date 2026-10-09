# Record entry validator with normalization rules

Check rows of records (CSV or objects) against declared field rules for type, required, allowed values, pattern, bounds, length and unique keys, after normalizing case, spaces, digits and dates, and list each error by row.

## What it does

Each field rule names a type (string, integer, number, date, boolean, email, phone) and optional checks. Normalization steps run first (trim, collapse_spaces, upper, lower, title, digits_only, iso_date with accepted date formats), then type and rule checks. Unique keys are checked across rows. Counts by rule and field are always complete; the error list stops at max_errors. A required field with no column at all is refused rather than reported row by row.

## Run it

As a library:

```python
from record_entry_validator import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 record_entry_validator.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `csv_text` (string): CSV with a header row
- `rows` (array of object): records as objects, used when csv_text is absent
- `fields` (array of object, required): rules: name, type, required, allowed, pattern, minimum, maximum, max_length, normalize steps
- `unique` (array of array): lists of field names whose combined values must not repeat
- `date_formats` (array of string): strftime formats the iso_date step accepts (default %Y-%m-%d)
- `allow_extra_columns` (boolean): accept columns without a rule (default true)
- `max_errors` (integer): how many error rows to list (default 200); counts are always complete
- `return_rows` (boolean): include normalized rows in the result (default true)

## Output

- `summary` (object, required): row and error counts
- `columns` (object, required): missing optional columns and extra columns
- `errors` (array of object, required): first errors: data row number (1 is the first data row), field, rule and value
- `rows` (array of object): normalized rows

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `header_missing`: the CSV text has no header row
- `duplicate_field_rule`: two field rules name the same field
- `invalid_pattern`: a field pattern is not a valid regular expression
- `missing_required_column`: a required field has no column at all
- `unknown_unique_field`: a unique key names a field without a rule
- `invalid_date_format`: a date format is not a strftime format with year, month and day

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `record_entry_validator.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 52 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.3.b.1.f.6` | Enter information into databases or software programs. | 25 | 21 |
| `4.A.3.b.6.h.14` | Maintain data in information systems or databases. | 18 | 117 |
| `4.A.3.b.1.f.5` | Update computer database information. | 5 | 382 |
| `4.A.3.b.1.f.10` | Enter codes or other information into computers. | 9 | 322 |

Occupations with the most of these activities: Appraisers of Personal and Business Property (`13-2022.00`); Judicial Law Clerks (`23-1012.00`); Title Examiners, Abstractors, and Searchers (`23-2093.00`); Pharmacy Technicians (`29-2052.00`); Buyers and Purchasing Agents, Farm Products (`13-1021.00`); Purchasing Agents, Except Wholesale, Retail, and Farm Products (`13-1023.00`).

Example O*NET task statements linked to these activities:

- "Record symbols on computer storage media and use computer aided transcription to translate and display them as text." (Court Reporters and Simultaneous Captioners, task `8663`)
- "Scan labels on letters or parcels to confirm receipt." (Postal Service Mail Carriers, task `20906`)
- "Enter prescription information into computer databases." (Pharmacy Technicians, task `23924`)
- "Locate and record data on sales of comparable property using specialized software, internet searches, or personal records." (Appraisers of Personal and Business Property, task `21541`)

## Limits

Email and phone checks are format checks only; they do not prove an address or number exists. Title case lowercases the rest of each word, so names such as McDonald need a correction list afterwards. Date parsing uses the formats given, so 03/04/2026 is read by the first format that fits. Values are treated as text; numbers with thousands separators fail the number check.

This kit is a candidate component. Generating it did not approve or qualify it.
