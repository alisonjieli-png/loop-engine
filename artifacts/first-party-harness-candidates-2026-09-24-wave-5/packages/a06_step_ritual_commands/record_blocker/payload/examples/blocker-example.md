# Blocker: T-101

## Ticket
T-101: Monthly report drops rows dated on the last day of the month

## Step
fix-month-end-filter

## What was tried
- Ran `python3 -m unittest tests.test_month_filter`; it stopped while importing the test fixture helper.
- Followed the test setup notes, pointed the helper path at `tests/fixtures`, and ran it again; the same import error came back.

## Exact error
```text
ModuleNotFoundError: No module named 'report_fixtures'
```

## Needed
- The `report_fixtures` test helper, or a note that says how the tests are meant to get it.

## From whom
The ticket author, or the person who maintains the test setup.
