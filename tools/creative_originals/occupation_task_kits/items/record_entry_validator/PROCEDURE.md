# Procedure: Record entry validator with normalization rules

Follow this procedure to do the activity with the helper `record_entry_validator.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Which system will receive these records, and what does it reject (types, lengths, codes)?
2. Which fields are required, and which code lists apply (status, country, unit)?
3. In which date formats do the source files arrive?
4. Which field or field combination must be unique?
5. Should invalid rows be fixed by hand, sent back to the source, or loaded with a flag?

## Steps

1. Profile the file first with column_profile to see real types and shapes.
2. Write one rule per target field with the receiving system's limits.
3. Choose normalization steps that are safe: trim and case changes, digits_only for phone, iso_date with the source formats.
4. Run the helper and read summary.errors_by_rule to see the dominant problem.
5. Fix rules that are too strict, then fix data. Record every fix.
6. Load only rows without errors, or follow the rejection decision below.

## Decision points

### What happens to invalid rows

- reject and return to the source: choose when the source can correct and resend
- fix by hand: choose when few rows and the correct value is known
- load with a flag: choose when the receiving system has a quarantine status

Default when nothing settles it: reject and return with the error list

Evidence that settles it: the share of invalid rows and who owns the source

### Ambiguous dates such as 03/04/2026

- month first: choose when the source is United States formatted
- day first: choose when the source uses day/month order
- ask: choose when both appear in one file

Default when nothing settles it: ask the data owner and record the answer in date_formats

Evidence that settles it: values above 12 in the first or second position

## Quality checks

- The rule set was run on a sample with known errors and found them.
- valid_rows plus invalid_rows equals rows.
- Normalized rows keep every input column.
- No error value is printed into shared logs when it holds personal data; use personal_data_masker.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: required, type and unique only; thorough: add allowed lists, patterns and bounds | thorough rules catch code-list errors |
| Tools | free: this helper, OpenRefine, Python csv; paid: data quality suites | same rules |
| Harness | coding agent runs the helper on files; business user pastes CSV text | same result |

## Stop and ask, or hand to a person

- Checking that an email or phone works: needs a sending or calling step with consent.
- Changing source systems: report errors to their owners.
