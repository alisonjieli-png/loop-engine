---
name: radar-check-support-window
description: Answer whether a runtime, framework, database or operating system version is supported on a given day, and how many days of support remain, from the dated support calendar this package carries (built from endoflife.date). Use before choosing a version for a new project, before pinning a dependency, and before a release. It reads only its own files and makes no network call.
license: MIT
metadata:
  asset_version: "1.0.0"
  data_file: "references/support-calendar.json"
---

# Check a version's support window

## What it returns

For one product and version, the support state on the day you name:
`supported`, `support_ending_soon` (within the warning window, 90 days unless
you set another), `unsupported`, `supported_no_end_date_published` or
`unknown_version`. A version the calendar does not hold is unknown, never
supported. After the calendar's valid-until day the helper answers
`calendar_expired`, because an old calendar must not look current.

## How to call it

Pass one JSON object as the only argument, or `-` to read it from standard input:

```text
python scripts/check_support_window.py '{"product": "python", "version": "3.12.4", "on": "2027-01-15"}'
```

A full version is matched to the longest release cycle it starts with, so
3.12.4 is cycle 3.12 and 3.1 never matches 3.13. The fields are in
[contracts/input.schema.json](contracts/input.schema.json).

## Output fields

The cycle, the end of support day, the end of active support day, the days
left on the day asked about, the latest version in the cycle, the long-term
support flag and the source address. The full contract is in
[contracts/output.schema.json](contracts/output.schema.json).

## Effects

It reads [references/support-calendar.json](references/support-calendar.json)
from this package and starts one Python process. It makes no network call and
writes nothing.

## Source and attribution

The calendar is built by the Baltor knowledge radar from endoflife.date,
whose data is published under the MIT licence. Each row keeps its source
address and dates.

## Limits

- Vendor extended support contracts are not included.
- Projects sometimes extend or cut support; read the project's own page before a release.

## How to check it

Run `python scripts/test_check_support_window.py` from the package folder. It
uses the fixed calendar in [verification/fixture-calendar.json](verification/fixture-calendar.json)
and the cases in [verification/cases.json](verification/cases.json), including
known-wrong answers the helper must not give, and needs no network.
