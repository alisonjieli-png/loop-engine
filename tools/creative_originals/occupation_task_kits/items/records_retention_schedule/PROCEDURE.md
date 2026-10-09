# Procedure: Records retention and disposition date calculator

Follow this procedure to do the activity with the helper `records_retention_schedule.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Which retention schedule applies, and who approved its current version?
2. Which records are under legal hold or audit, and who maintains the hold list?
3. Which event starts the clock for each class (creation, closure, termination, project end)?
4. Who must approve destruction, and how is it documented?

## Steps

1. Map each record to a schedule class; list records that fit no class and ask the owner.
2. Collect trigger dates and the legal hold flag from the record system.
3. Run the helper with the review window the approval cycle needs.
4. Send due records for approval with the schedule citation; keep the approval record.
5. Fix file names that break the pattern before archiving.
6. Rerun before each disposition batch, since holds change.

## Decision points

### Due records

- destroy: choose when the schedule says destroy, no hold, approval given
- archive: choose when the schedule says archive or historical value exists
- extend: choose when a claim, audit or request is expected; apply a hold first

Default when nothing settles it: send for approval; never act on the helper's output alone

Evidence that settles it: the hold list and the approver's decision

## Quality checks

- Every record class in the records is in the schedule.
- Legal hold records are never in the due list.
- Spot check three disposition dates by hand, including one end-of-month case.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: one class; thorough: the whole file plan | same rules |
| Tools | free: this helper with a spreadsheet; paid: records management systems | same dates |
| Window | 30, 90 or 180 days | longer windows give approvers more notice |

## Stop and ask, or hand to a person

- Legal advice on retention periods.
- Destroying or moving records: a person does it after approval.
