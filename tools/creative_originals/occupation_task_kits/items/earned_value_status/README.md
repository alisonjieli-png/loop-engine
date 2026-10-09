# Earned value status with performance indices and forecasts

Compute planned value, earned value, schedule and cost variance, SPI, CPI, estimate at completion, estimate to complete, variance at completion and TCPI per work package and in total, with a status.

## What it does

For each work package: PV = budget x planned percent, EV = budget x earned percent, SV = EV - PV, CV = EV - AC, SPI = EV / PV, CPI = EV / AC, EAC = budget / CPI, ETC = EAC - AC, VAC = budget - EAC and TCPI = (budget - EV) / (budget - AC). Indices are null when undefined. Status is red or amber when SPI or CPI falls below the thresholds, and not_started when nothing is planned, earned or spent.

## Run it

As a library:

```python
from earned_value_status import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 earned_value_status.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `work_packages` (array of object, required): packages with budget at completion, planned and earned percent at the status date and actual cost to date
- `amber_index` (number): an SPI or CPI below this is amber (default 0.95)
- `red_index` (number): an SPI or CPI below this is red (default 0.85)

## Output

- `packages` (array of object, required): one row per package in input order, with its id
- `total` (object, required): the same measures for the summed values

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_package_id`: two work packages share an id
- `thresholds_out_of_order`: the red index threshold is not below the amber threshold

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `earned_value_status.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 27 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.4.b.4.j.12` | Manage operations, research, or logistics projects. | 11 | 147 |
| `4.A.4.b.4.e.7` | Manage information technology projects or system activities. | 10 | 120 |
| `4.A.4.b.4.h.5` | Manage organizational or project budgets. | 10 | 282 |

Occupations with the most of these activities: Advertising and Promotions Managers (`11-2011.00`); Computer and Information Systems Managers (`11-3021.00`); Clinical Research Coordinators (`11-9121.01`); Project Management Specialists (`13-1082.00`); Public Relations Managers (`11-2032.00`); Fundraising Managers (`11-2033.00`).

Example O*NET task statements linked to these activities:

- "Participate in financial activities, such as the setting of room rates, the establishment of budgets, and the allocation of funds to departments." (Lodging Managers, task `1108`)
- "Manage project execution to ensure adherence to budget, schedule, and scope." (Information Technology Project Managers, task `16169`)
- "Determine allocations of funds for staff, supplies, materials, and equipment and authorize purchases." (Education and Childcare Administrators, Preschool and Daycare, task `5197`)
- "Coordinate monitoring of networks or systems for security breaches or intrusions." (Information Security Engineers, task `21769`)

## Limits

EAC assumes future work continues at the current CPI; other forecasting formulas are not offered. Earned percent must come from measured progress, not from spending. Schedule variance is in money, not time. Totals sum the packages, which weights large packages more.

This kit is a candidate component. Generating it did not approve or qualify it.
