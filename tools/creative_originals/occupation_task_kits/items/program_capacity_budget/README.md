# Program capacity, staffing and break-even budget

Compute seats, people turned away, staff per session, cost, revenue, net, cost per participant, break-even fee and break-even attendance for a session-based program, with named scenarios.

## What it does

Each session seats expected participants up to the venue capacity. Staff per session is the larger of the minimum and participants divided by the ratio, rounded up. Costs are staff hours, fixed costs per session and per program, and a variable cost per participant. Revenue is fees plus subsidy. Break-even attendance is the smallest seats per session whose revenue covers cost. Scenarios change named fields and are compared side by side.

## Run it

As a library:

```python
from program_capacity_budget import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 program_capacity_budget.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `program` (object, required)
- `scenarios` (array of object): named overrides of program fields

## Output

- `scenarios` (array of object, required): base first, then each scenario in input order

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `unknown_scenario_field`: a scenario changes a field the program does not have
- `duplicate_scenario_name`: two scenarios share a name, or a scenario is named base
- `scenario_value_invalid`: a scenario sets a field to a value the program schema refuses

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `program_capacity_budget.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 48 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.2.b.6.a.4` | Plan community programs or activities for the general public. | 42 | 25 |
| `4.A.2.b.6.a.2` | Plan conferences, programs, or special events. | 3 | 772 |
| `4.A.2.b.6.a.1` | Plan special events. | 4 | 763 |

Occupations with the most of these activities: Entertainment and Recreation Managers, Except Gambling (`11-9072.00`); Park Naturalists (`19-1031.03`); Anthropologists and Archeologists (`19-3091.00`); Clergy (`21-2011.00`); Directors, Religious Activities and Education (`21-2021.00`); Business Teachers, Postsecondary (`25-1011.00`).

Example O*NET task statements linked to these activities:

- "Plan programs of events or schedules of activities." (Entertainment and Recreation Managers, Except Gambling, task `21408`)
- "Plan and organize public events at the park." (Park Naturalists, task `20866`)
- "Plan, organize, or lead group activities for customers, such as exercise routines, athletic events, or arts and crafts." (Entertainment and Recreation Managers, Except Gambling, task `21409`)
- "Schedule special events, such as camps, conferences, meetings, seminars, or retreats." (Directors, Religious Activities and Education, task `12983`)

## Limits

Every session is identical; attendance is an input, not a forecast. Staff are paid only for session hours. Taxes, refunds, no-shows and price elasticity are not modelled. Money is rounded to two decimals per line, so totals can differ from summed lines by a cent.

This kit is a candidate component. Generating it did not approve or qualify it.
