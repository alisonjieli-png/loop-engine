# Procedure: Shift roster builder with skills, hours and rest limits

Follow this procedure to do the activity with the helper `shift_roster_builder.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Which shifts exist for the period, with start, end and how many people each needs?
2. Which skills or certificates does each shift require, and who holds them?
3. What are each person's weekly hour limit, maximum shifts and dates off?
4. What minimum rest applies between shifts, and does it come from a contract or law?
5. Which shifts were worked just before this period (for rest at the boundary)?

## Steps

1. Build the shift list with dates, start and end times, required counts and skills.
2. Build the staff list from the current skills register; take certificates from training_compliance_matrix when expiry matters.
3. Run the helper and read unfilled with its blockers.
4. For each blocker type decide a fix: hire or borrow a skilled person, relax a limit with consent, or move the shift.
5. Check hours per person for fairness; swap shifts by hand where the spread is uneven.
6. Publish the roster and keep the input file so the next change reruns from the same data.

## Decision points

### Who fills a gap the helper could not fill

- overtime for an existing person: choose when rest and hour limits allow it after consent
- agency or float staff: choose when the skill is scarce and budget allows
- leave unfilled and escalate: choose when safety rules forbid working short

Default when nothing settles it: escalate to the manager with the blocker counts

Evidence that settles it: the blockers object for the shift

### Minimum rest value

- contract or legal value: choose when one is published for the role or place
- organization default: choose when none is published; record the value used

Default when nothing settles it: 10 hours, stated in the roster notes

Evidence that settles it: the employment contract, collective agreement or local labour rules

## Quality checks

- No person appears on two overlapping shifts.
- Rest between any two of a person's shifts is at least the minimum.
- No person exceeds the weekly hour limit in any ISO week.
- Every shift with a skill is covered only by people holding that skill.
- filled_share matches positions filled divided by positions required.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: one week; thorough: the full roster period with boundary shifts added | longer periods catch rest problems at week edges |
| Tools | free: this helper with a spreadsheet; paid: workforce management suites | same rows |
| Fairness | least hours first (built in) or manual swaps afterwards | hours table shows spread |

## Stop and ask, or hand to a person

- Pay calculation and overtime premiums.
- Legal advice on working time rules: a person confirms the limits used.
- Individual preferences beyond unavailable dates.
