# Shift roster builder with skills, hours and rest limits

Assign staff to shifts while respecting required skills, unavailable dates, overlapping shifts, minimum rest, weekly hour limits and shift count limits, and explain every unfilled position.

## What it does

Shifts are filled in start order. For each position the eligible person with the fewest hours so far is chosen, so work spreads evenly. Overnight shifts end the next day. Weekly hours follow the ISO week of the shift start. Each unfilled shift lists how many people each blocker excluded: missing skill, unavailable, overlap or rest, weekly hours or shift limit.

## Run it

As a library:

```python
from shift_roster_builder import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 shift_roster_builder.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `shifts` (array of object, required): shifts with a date, start and end (an end at or before the start ends the next day), the number of people required and an optional skill
- `staff` (array of object, required): people with skills, a weekly hour limit, optional unavailable dates and a shift count limit
- `min_rest_hours` (number): minimum hours between two shifts of one person (default 10)

## Output

- `assignments` (array of object, required): staff ids per shift, in shift start order
- `unfilled` (array of object, required): shifts short of people, with the count and the main blocker
- `hours` (array of object, required): assigned hours and shifts per person, in input order
- `filled_share` (number, required): positions filled divided by positions required

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_id`: two shifts or two staff members share an id
- `invalid_date_or_time`: a date is not a real calendar date or a time is not HH:MM
- `shift_too_long`: a shift lasts more than 24 hours or no time at all

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `shift_roster_builder.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 39 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.4.b.1.f.6` | Assign duties or work schedules to employees. | 20 | 65 |
| `4.A.4.b.1.f.4` | Prepare employee work schedules. | 9 | 229 |
| `4.A.4.b.1.f.2` | Prepare staff schedules or work assignments. | 12 | 255 |

Occupations with the most of these activities: First-Line Supervisors of Gambling Services Workers (`39-1013.00`); First-Line Supervisors of Personal Service Workers (`39-1022.00`); Chief Executives (`11-1011.00`); General and Operations Managers (`11-1021.00`); Administrative Services Managers (`11-3012.00`); Education Administrators, Postsecondary (`11-9033.00`).

Example O*NET task statements linked to these activities:

- "Monitor employees' work schedules and attendance for payroll purposes." (Postmasters and Mail Superintendents, task `20842`)
- "Prepare daily work and run schedules." (Dispatchers, Except Police, Fire, and Ambulance, task `2727`)
- "Prepare employee work schedules." (Postmasters and Mail Superintendents, task `5264`)
- "Assign tasks such as feeding and treatment of animals, and cleaning and maintenance of animal quarters." (First-Line Supervisors of Farming, Fishing, and Forestry Workers, task `23340`)

## Limits

Greedy, not optimal: an early assignment can make a later shift impossible that another assignment would have filled. Labour law, union rules, pay rates, preferences and requests for days off beyond unavailable dates are not modelled. Rest is checked between assigned shifts only, not against shifts worked before the roster period.

This kit is a candidate component. Generating it did not approve or qualify it.
