# Procedure: Milestone status report with slippage and dependency conflicts

Follow this procedure to do the activity with the helper `milestone_status_report.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Which milestones does the audience care about, and what was each baseline date?
2. Who owns each forecast, and when was it last confirmed?
3. What slip is amber and what is red for this project or contract?
4. Who reads the report, and what decision should it support?

## Steps

1. Collect baseline, forecast and actual dates from the plan and owners.
2. Set the report date to the data cut-off, not the send date.
3. Run the helper; read overall, counts and lines.
4. Resolve dependency conflicts with owners before sending.
5. Add causes and recovery actions for red and overdue items in your own words.
6. Send the report with the input data attached so readers can check it.

## Decision points

### Thresholds

- 5 and 15 days: choose when a project of several months
- 1 and 5 days: choose when a short project or a contractual date
- percent of remaining duration: choose when milestones are far apart; convert to days per milestone

Default when nothing settles it: 5 and 15 calendar days

Evidence that settles it: contract penalties and stakeholder tolerance

### Overdue without forecast

- ask the owner for a forecast: choose when the owner can be reached before the report
- report as overdue: choose when no forecast exists by the cut-off

Default when nothing settles it: report as overdue and name the owner

Evidence that settles it: date of the last owner update

## Quality checks

- Every red or overdue milestone has an owner and a recovery action in the narrative.
- No actual date is after the report date.
- Dependency conflicts are resolved or explained.
- counts add up to the number of milestones.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: helper lines only; thorough: lines plus causes and recovery plan | same statuses |
| Tools | free: this helper, a spreadsheet; paid: project portfolio software | same dates |
| Audience | team or executive | executives get overall and red items only |

## Stop and ask, or hand to a person

- Deciding to re-baseline: the sponsor approves a new baseline.
- Explaining causes: owners provide them.
