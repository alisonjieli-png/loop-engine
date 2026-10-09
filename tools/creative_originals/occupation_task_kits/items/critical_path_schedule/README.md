# Critical path schedule from tasks and dependencies

Compute earliest and latest start and finish, total and free float, the critical path and optional calendar dates from a task list with durations and finish-to-start dependencies.

## What it does

The helper runs the forward pass (earliest start and finish), the backward pass (latest start and finish), computes total and free float, marks zero-float tasks as critical and returns one critical chain. With a start date it maps day offsets to dates on a calendar-day or working-day calendar with holidays. It refuses repeated ids, unknown or self dependencies and cycles.

## Run it

As a library:

```python
from critical_path_schedule import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 critical_path_schedule.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `tasks` (array of object, required): tasks with an id, a duration in days and the ids they depend on (finish to start)
- `start_date` (string): optional YYYY-MM-DD project start for calendar dates
- `calendar` (value): count every day, or Monday to Friday without holidays (default calendar_days)
- `holidays` (array of string): YYYY-MM-DD dates skipped by the working_days calendar

## Output

- `project_duration` (number, required): days from project start to the last finish
- `critical_path` (array of string, required): one chain of zero-float tasks from start to finish
- `critical_tasks` (array of string, required): every task with zero total float
- `order` (array of string, required): a dependency-respecting order
- `schedule` (array of object, required): one row per task, in input order
- `project_start_date` (string)
- `project_finish_date` (string)

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_task_id`: two tasks share an id
- `unknown_dependency`: a task depends on an id that is not in the task list
- `self_dependency`: a task lists itself as a dependency
- `dependency_cycle`: the dependencies form a cycle, so no schedule exists
- `fractional_duration_with_dates`: calendar dates were requested but a duration is not a whole number of days
- `invalid_date`: the start date or a holiday is not a real calendar date

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `critical_path_schedule.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 49 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.2.b.6.b.7` | Prepare detailed work plans. | 24 | 54 |
| `4.A.2.b.6.b.8` | Develop detailed project plans. | 9 | 157 |
| `4.A.2.b.5.b.7` | Schedule operational activities. | 20 | 38 |

Occupations with the most of these activities: Transportation Engineers (`17-2051.01`); Marine Engineers and Naval Architects (`17-2121.00`); Mining and Geological Engineers, Including Mining Safety Engineers (`17-2151.00`); Environmental Engineering Technologists and Technicians (`17-3025.00`); Project Management Specialists (`13-1082.00`); Database Administrators (`15-1242.00`).

Example O*NET task statements linked to these activities:

- "Schedule or dispatch workers, work crews, equipment, or service vehicles to appropriate locations, according to customer requests, specifications, or needs, using radios or telephones." (Dispatchers, Except Police, Fire, and Ambulance, task `2723`)
- "Prepare work orders and instructions for grinding lenses and fabricating eyeglasses." (Opticians, Dispensing, task `4203`)
- "Develop final construction plans that include aesthetic representations of the structure or details for its construction." (Architects, Except Landscape and Naval, task `20483`)
- "Create plans for solar energy system development, monitoring, and evaluation activities." (Solar Energy Systems Engineers, task `16571`)

## Limits

Finish-to-start dependencies only, without lags, leads or start-to-start links. Durations are deterministic; there is no resource levelling, so two critical tasks may need the same person at once. Working days are Monday to Friday; other work weeks need a calendar_days run with durations already converted. A zero-duration milestone is dated on the working day it becomes due. When several critical chains exist, critical_path shows one and critical_tasks lists all.

This kit is a candidate component. Generating it did not approve or qualify it.
