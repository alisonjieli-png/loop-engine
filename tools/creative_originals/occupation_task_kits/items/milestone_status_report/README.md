# Milestone status report with slippage and dependency conflicts

Classify each milestone as complete on time, complete late, green, amber, red or overdue from baseline, forecast and actual dates, flag forecasts that precede a predecessor, and write status lines.

## What it does

Slip is the forecast or actual date minus the baseline date in calendar days. Open milestones are green, amber or red by slip thresholds, and overdue when the baseline or forecast has passed without completion. A forecast earlier than a predecessor's date is a dependency conflict. The overall status is the worst open status, and each milestone that is not complete on time gets one plain sentence.

## Run it

As a library:

```python
from milestone_status_report import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 milestone_status_report.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `as_of` (string, required): report date, YYYY-MM-DD
- `milestones` (array of object, required): milestones with a baseline date and, when known, a forecast or actual date, an owner and predecessor ids
- `amber_slip_days` (integer): slip in days that makes an open milestone amber (default 5)
- `red_slip_days` (integer): slip in days that makes an open milestone red (default 15)

## Output

- `as_of` (string, required)
- `overall` (one of green, amber, red, complete, required): worst status of open milestones
- `counts` (object, required): milestones per status
- `milestones` (array of object, required): one row per milestone in input order
- `lines` (array of string, required): one plain sentence per milestone that is not complete on time

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_id`: two milestones share an id
- `unknown_dependency`: a milestone depends on an id that is not listed
- `invalid_date`: a date is not a real YYYY-MM-DD calendar date
- `actual_in_future`: an actual completion date is after the report date
- `thresholds_out_of_order`: the red threshold is not above the amber threshold

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `milestone_status_report.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 35 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.3.b.6.o.6` | Prepare operational progress or status reports. | 15 | 185 |
| `4.A.4.a.3.c.6` | Inform individuals or organizations of status or findings. | 10 | 245 |
| `4.A.4.b.4.e.7` | Manage information technology projects or system activities. | 10 | 120 |

Occupations with the most of these activities: Chief Executives (`11-1011.00`); Chief Sustainability Officers (`11-1011.03`); Administrative Services Managers (`11-3012.00`); Facilities Managers (`11-3013.00`); Computer and Information Systems Managers (`11-3021.00`); Financial Managers (`11-3031.00`).

Example O*NET task statements linked to these activities:

- "Provide information concerning the circumstances of death to relatives of the deceased." (Coroners, task `8923`)
- "Arrange for the next of kin to be notified of deaths." (Coroners, task `8928`)
- "Send notices to taxpayers when accounts are delinquent." (Tax Examiners and Collectors, and Revenue Agents, task `5293`)
- "Impose payment deadlines on delinquent taxpayers and monitor payments to ensure that deadlines are met." (Tax Examiners and Collectors, and Revenue Agents, task `5301`)

## Limits

Calendar-day slip, not working days. Status thresholds are inputs; the helper does not judge whether a slip matters to the customer. It does not reschedule successors; use critical_path_schedule for that. The status lines are plain facts, not an explanation of causes.

This kit is a candidate component. Generating it did not approve or qualify it.
