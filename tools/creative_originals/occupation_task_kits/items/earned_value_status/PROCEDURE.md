# Procedure: Earned value status with performance indices and forecasts

Follow this procedure to do the activity with the helper `earned_value_status.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. What is the budget at completion of each work package, and has it changed since the baseline?
2. How is earned percent measured: completed deliverables, weighted milestones or estimates?
3. Which actual costs are booked to each package up to the status date, including accruals?
4. What index values count as amber and red for this project?

## Steps

1. Take the planned percent for the status date from the baseline schedule.
2. Take earned percent from measured progress rules agreed in advance.
3. Take actual cost from the ledger up to the same date.
4. Run the helper; read package and total indices.
5. For red packages, compare TCPI with CPI: a TCPI far above CPI means the budget is unlikely to hold.
6. Report EAC and VAC with the assumption that current efficiency continues.

## Decision points

### How to measure earned percent

- 0 and 100: choose when packages are short (under a month)
- 50 and 50: choose when packages are medium; half at start, half at finish
- weighted milestones: choose when packages are long with clear intermediate deliverables

Default when nothing settles it: weighted milestones agreed before work starts

Evidence that settles it: package length and deliverable structure

### Thresholds

- 0.95 and 0.85: choose when general projects
- 0.98 and 0.9: choose when fixed-price work with thin margins

Default when nothing settles it: 0.95 and 0.85

Evidence that settles it: contract type and margin

## Quality checks

- Planned, earned and actual values use the same cut-off date.
- EV never exceeds budget; earned percent is at most 100.
- CPI and SPI are null only where their denominators are zero.
- Total EAC is close to the sum of package EACs when CPIs are similar; large gaps mean one package dominates.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: project total only; thorough: every work package | packages locate the problem |
| Tools | free: this helper, a spreadsheet; paid: project control suites | same formulas |
| Contract | time and materials or fixed price | fixed price needs tighter thresholds |

## Stop and ask, or hand to a person

- Approving changes to the budget at completion: a change board decides.
- Accruals and cost allocation rules: finance confirms the actual costs.
