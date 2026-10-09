# Procedure: Requirements traceability matrix and coverage gaps

Follow this procedure to do the activity with the helper `requirements_traceability.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Where are the requirements kept, and do they have stable ids?
2. Which priority scheme applies (must, should, could), and who set it?
3. Where are design elements and tests recorded, and do they reference requirement ids?
4. Which test run counts as the latest result?

## Steps

1. Export requirements with ids and priorities.
2. Export design elements and tests with the requirement ids they reference.
3. Run the helper; read gaps first.
4. For each must requirement without a pass, find or write a test, or record why none is possible.
5. For links to nothing, remove the element or test, or add the missing requirement.
6. Attach the matrix to the design or release review record.

## Decision points

### Release readiness

- ready: choose when must_without_a_pass and failing are empty
- ready with waivers: choose when a named approver accepts each open must requirement
- not ready: choose when open must requirements have no waiver

Default when nothing settles it: not ready until must requirements pass or carry a waiver

Evidence that settles it: the gaps object and the waiver list

## Quality checks

- Every requirement id appears once in the matrix.
- No design element or test references an unknown requirement.
- pass_share equals passed divided by requirements.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: must requirements only; thorough: all priorities | same method |
| Tools | free: this helper with CSV exports; paid: requirements management tools | same links |
| Harness | coding agent reads ids from code and tests; business user uses a spreadsheet export | same input |

## Stop and ask, or hand to a person

- Judging whether a test is adequate: a reviewer reads it.
- Writing the missing tests.
