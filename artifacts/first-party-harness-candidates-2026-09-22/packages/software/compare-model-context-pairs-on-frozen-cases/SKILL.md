---
name: compare-model-context-pairs-on-frozen-cases
description: Design a paired evaluation of model choice and context package together. Use when a shorter skill or smaller model may help only in combination with the other.
---

# Compare model and context pairs on frozen cases

## Use

Use to plan an evaluation before choosing a model-specific context variant. Produce a comparison design from supplied material; this skill does not call a model or claim an improvement.

## Inputs

- The task population and acceptance rule, including an unseen holdout.
- At least two eligible model routes and two approved or candidate context packages.
- The fixed authority, trial and model-call ceiling, output shape, allowed retries, and usage-recording method.

## Procedure

1. Freeze representative cases and the independent evaluator before looking at results. Keep failures, refusals, and malformed outputs in the population.
2. Check that every model and context package is eligible for the same task and authority. A package with different tool rights is a different policy, not a context comparison.
3. Count the planned model calls, including permitted retries and the final holdout comparison, before choosing the grid. If the full paired grid exceeds the supplied ceiling, preregister a smaller representative case set that still crosses at least two models with two contexts. If even that cannot fit, hold the experiment. Never treat this plan as call authority.
4. Plan the affordable paired grid: every selected case receives every selected eligible model and context combination under the same output contract and retry rule.
5. Specify the exact model version, context digest, route settings, and case identifier for each planned cell. Provide fields for later observed tokens, time, and cost state. Unknown usage must remain unknown.
6. Compare the context effect within each model, then compare model effects within each context. Identify interactions rather than reporting only the best overall pair.
7. Reserve the holdout for one final check of the selected pair against the baseline. State how failed or unavailable cells affect the conclusion.
8. Return a trial matrix, call ceiling, evaluator rule, reporting fields, and a decision rule that can reject the new pair.

## Completion check

The baseline, case population, evaluator, comparison grid, call ceiling, and failure accounting are fixed before outcomes. The plan can distinguish a model effect, a context effect, and an interaction within the registered cases.

## Stop

If packages are unapproved for real execution, label the design candidate-only. Do not infer quality from shorter text, cheaper model labels, or a single demonstration.
