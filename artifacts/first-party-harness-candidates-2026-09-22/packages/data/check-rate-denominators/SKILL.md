---
name: check-rate-denominators
description: Verify that a rate's numerator and denominator use a compatible eligible population and observation window. Use before comparing conversions, defects, or service rates.
---

# Check rate denominators

## When to use

Use this when a percentage or rate is calculated from events and a population. A count of events is not automatically a count of people or objects.

## Inputs

- The rate's plain-language definition and intended counting unit.
- Numerator and denominator records with identity, eligibility or cohort window, outcome observation window, and counting rules.
- Exclusion rules and the treatment of zero or unknown denominators.

## Procedure

1. Write the numerator and denominator as sets or measured quantities with explicit units. Identify whether the result is a share, an incidence rate, or another measure.
2. Form the denominator from the declared eligible population or cohort. Count only qualifying numerator outcomes from that population inside its declared observation window, which may follow the cohort-entry window. For a share of entities, deduplicate repeated events by entity before counting the numerator.
3. Check that every numerator entity is eligible for the denominator. Report unmatched identities and exclusions rather than silently discarding them.
4. Recompute the numerator, denominator, and rate. Compare any two rates only after their cohort definitions, observation horizons, maturity, and counting units are compatible; flag censored or not-yet-observed cohorts.
5. Keep the counts beside the rate so a change in the population is visible.

## Completion check

Return the definition, counting unit, cohort-entry window, outcome observation window, numerator count, denominator count, exclusions, unmatched count, calculated rate, and comparison caveats. A zero denominator is reported as undefined, not as zero percent.

## Stop conditions

Stop if eligibility, identity, cohort or outcome window, or counting unit is missing. Do not invent a denominator from whichever table is easiest to query.
