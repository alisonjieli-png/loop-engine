# Procedure: Program capacity, staffing and break-even budget

Follow this procedure to do the activity with the helper `program_capacity_budget.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. How many sessions, how long, and in which venue with what capacity?
2. How many participants do you expect per session, and from what evidence?
3. What staffing ratio and minimum staff do safety or quality rules require?
4. What are the fixed costs per session and for the whole program, and the cost per participant?
5. What fee is charged, and is there a grant or subsidy?

## Steps

1. Fill the program fields; mark which numbers are quotes and which are guesses.
2. Add scenarios for the main uncertainty: low and high attendance, another venue, another fee.
3. Run the helper and compare net and break-even across scenarios.
4. If the base case loses money, test the cheapest change first: fee, venue, or session count.
5. Report the break-even attendance next to the expected attendance so the margin is visible.

## Decision points

### Fee level

- cost-recovery fee: choose when use break_even_fee from the expected-attendance scenario
- subsidized fee: choose when access matters more than recovery; size the subsidy from net
- free: choose when a funder covers all costs; check the subsidy covers the total

Default when nothing settles it: the break-even fee of a cautious attendance scenario

Evidence that settles it: past attendance and the funder's conditions

### Venue size

- larger venue: choose when turned_away is high and the extra fixed cost is covered
- more sessions: choose when the venue is fixed; add sessions instead

Default when nothing settles it: keep the venue unless turned away exceeds 15 percent of seats

Evidence that settles it: turned_away_per_session across scenarios

## Quality checks

- Staff per session meets the minimum and the ratio.
- cost.total equals staff plus fixed plus variable (within a cent).
- Break-even attendance is not above venue capacity; null means it cannot break even.
- Each scenario changes only the fields named.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: base case only; thorough: three attendance scenarios and two fees | more scenarios show risk |
| Tools | free: this helper or a spreadsheet; paid: event management software | same numbers |
| Funding | fee-funded, subsidized or free | changes revenue lines only |

## Stop and ask, or hand to a person

- Insurance, licences and safety plans for the venue.
- Signing contracts with venues or staff: a person approves.
