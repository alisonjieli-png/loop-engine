# Step handoff: fix-month-end-filter

## Objective
Make the monthly report include rows dated on the last day of the month.

## Status
partial

## Done
- Reproduced the bug with a failing test in `tests/test_month_filter.py`.
- Fixed the end date in `src/report/month_filter.py`; the saved test run is `.baltor/evidence/fix-month-end-filter-tests.txt`.

## Remaining
- The same end-date rule is copied in `src/report/quarter_filter.py` and is not fixed yet.

## Open questions
- none

## First action for the next harness
Run `python3 -m unittest tests.test_month_filter -v` and confirm that it passes before any other edit.
