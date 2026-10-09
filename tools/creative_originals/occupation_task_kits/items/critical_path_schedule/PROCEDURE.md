# Procedure: Critical path schedule from tasks and dependencies

Follow this procedure to do the activity with the helper `critical_path_schedule.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Which deliverable ends the plan, and is there a fixed deadline or only a start date?
2. Are durations in working days or calendar days, and which dates are holidays or shutdowns?
3. For each task, what must be finished before it can start? Are any links softer than that (can overlap, needs a lag)?
4. Who does each task, and can two tasks with the same person run at the same time?
5. How sure are the durations: firm quotes, estimates, or guesses?

## Steps

1. List tasks at a level where one owner can finish each in 1 to 15 working days; split longer ones.
2. Give each task a short id, a name and a duration in one unit. Convert weeks to days first.
3. Record dependencies as the ids that must finish first. Leave out links that are only preferences.
4. Run the helper without a start date first and read project_duration and critical_path.
5. Check the critical path with the user: does it match where they expect the schedule pressure?
6. Add start_date, calendar and holidays and run again to get dates.
7. Compare project_finish_date with the deadline. If it is late, shorten critical tasks or remove dependencies, not tasks with float.
8. Check people: list critical tasks that share an owner and overlap in dates; resolve by moving the one with more float or adding a person.
9. Publish the schedule with critical tasks marked and float shown for the rest.

## Decision points

### Which calendar to use

- working_days: choose when the people doing the work keep a Monday to Friday week
- calendar_days: choose when work runs every day (shifts, vendors, curing or shipping time) or durations were already converted

Default when nothing settles it: working_days with the organization's published holidays

Evidence that settles it: the work week of the people or vendors on the critical path

### How to shorten a late plan

- crash a critical task: choose when more people or overtime shorten it and the cost is acceptable
- overlap tasks: choose when a dependency is not strict and partial output can start the next task; record the risk
- cut scope: choose when the deadline is fixed and neither of the above is possible

Default when nothing settles it: overlap tasks only after the owner confirms the dependency is soft

Evidence that settles it: rerun the helper after each change and compare project_duration

### Duration certainty

- single estimate: choose when durations come from quotes or repeated work
- three-point estimate first: choose when durations are uncertain; use cost_estimate_rollup to get expected durations, then schedule them

Default when nothing settles it: single estimate with the uncertainty noted next to each critical task

Evidence that settles it: how many critical tasks have been done before by the same team

## Quality checks

- Every task except start tasks has at least one dependency, and every task except the final ones has a successor; a task with neither is usually a missing link.
- The critical path is continuous: each critical task starts when the previous one finishes.
- No task has negative float. Negative float cannot occur here without a deadline; if the user imposes one, compare dates by hand.
- Dates skip weekends and every listed holiday on the working_days calendar.
- The finish date is the last working day of the last task, not the day after.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: schedule the top 10 to 20 tasks; thorough: every task an owner can finish | fast plans hide float; thorough plans take longer to keep current |
| Tools | free: this helper, a spreadsheet, GanttProject; paid: Microsoft Project, Smartsheet | the helper output imports into any of them as rows |
| Calendar | calendar_days or working_days with holidays | changes dates, not float |
| Harness | coding agent runs the helper; a business user pastes rows into a spreadsheet | same arithmetic, different hand-off |

## Stop and ask, or hand to a person

- Resource levelling across shared people or equipment: list conflicts and ask the owner.
- Contractual deadlines with penalties: a person approves the plan before it is shared.
- Lags, leads and start-to-start links: model them by splitting tasks or ask for a scheduling tool.
