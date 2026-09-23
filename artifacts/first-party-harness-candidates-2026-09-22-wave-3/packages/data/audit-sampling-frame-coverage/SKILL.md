---
name: audit-sampling-frame-coverage
description: Audit whether a sampling frame and response set cover the intended population. Use before generalizing survey or observational results beyond reachable groups.
---

# Audit sampling frame coverage

## When to use

Use before drawing a population conclusion from a selected or invited set. Frame coverage, selection, and response are separate stages with different missingness.

## Inputs

- Target population definition, period, segment definitions, and known population counts or an explicit unknown count.
- Frame records, identity and deduplication rule, selection rule, invitation records, and response dispositions.
- The result and population claim being assessed, including any supplied weighting or complete-enumeration rule.

## Procedure

1. Fix the intended population and time. Compare it with the frame's eligibility, reachability, and known exclusions; separate missing groups from duplicate or out-of-scope frame entries.
2. Reconcile counts by segment from population, frame, selection, invitation, and response. Where a population count is unknown, mark coverage unknown rather than computing a false percentage.
3. Check whether selection probabilities or quotas follow the supplied rule. Report unreachable or uninvited groups separately from invited nonrespondents.
4. Compare known segment composition at each stage. Show whether a claimed inference depends on an uncovered group or an unmeasured nonresponse outcome.
5. State the narrowest population the evidence directly describes and the additional frame or response evidence needed for a wider claim.

## Completion check

Return the population and period, stage-by-segment count ledger, known coverage gaps, selection and nonresponse rates where denominators exist, and a verdict on the proposed population claim. Every generalization must name its supported scope.

## Stop conditions

Hold a population-wide claim when target membership, frame completeness, identity, selection rule, or response dispositions are unknown. Do not contact people, change a sample, or infer nonrespondents' answers.
