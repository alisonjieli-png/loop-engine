# Procedure: Operational log completeness and order audit

Follow this procedure to do the activity with the helper `record_log_auditor.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. What is one log record, and how often should one be written (each shift, day or hour)?
2. Which fields must every record fill to meet the procedure or regulation?
3. Is there a running number that must not skip, and is it per site or machine?
4. Which period does the audit cover, and what time zone are the timestamps in?

## Steps

1. Export the log for the period with every field.
2. Run the helper with the group, sequence and interval settings.
3. Sort issues by kind; deal first with sequence gaps and time gaps, which suggest lost records.
4. Ask the record owners about each gap and record the explanation.
5. Report coverage per group and the corrective actions.

## Decision points

### Expected interval

- day: choose when the procedure requires a daily entry
- hour: choose when continuous monitoring or hourly rounds
- none: choose when entries happen on events only; skip coverage and check order and fields

Default when nothing settles it: the interval the written procedure states

Evidence that settles it: the operating procedure or permit condition

### Late entries

- accept with note: choose when the entry was written late but describes the right time
- treat as gap: choose when the procedure requires real-time entries

Default when nothing settles it: accept with a note naming who confirmed it

Evidence that settles it: the procedure's wording on timeliness

## Quality checks

- The period start and end match the audit scope.
- Every time gap was explained or escalated.
- Counts in summary equal the number of issues of each kind when max_issues was not reached.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: one group and one month; thorough: all groups and the full retention period | same method |
| Tools | free: this helper with CSV exports; paid: computerized maintenance or quality systems | same checks |
| Interval | day or hour | changes coverage only |

## Stop and ask, or hand to a person

- Judging whether a missing record means the work was not done: the owner confirms.
- Editing records after the fact: corrections follow the organization's records procedure.
