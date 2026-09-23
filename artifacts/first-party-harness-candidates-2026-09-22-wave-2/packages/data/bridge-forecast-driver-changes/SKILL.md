---
name: bridge-forecast-driver-changes
description: Explain the movement between two forecast versions through named driver changes and a residual. Use when a revised demand, revenue, or workload forecast needs an auditable change explanation.
---

# Bridge forecast driver changes

## When to use

Use this to explain a forecast revision over the same target, horizon, population, and unit. An explanation of a revision is not proof that either forecast will be accurate.

## Inputs

- Baseline and revised forecast identities, values, horizons, units, and populations.
- Driver values and model or calculation versions for both forecasts.
- A supplied attribution method, including its ordering or interaction rule when drivers are not additive.

## Procedure

1. Confirm the two forecasts refer to comparable targets. Report any horizon, population, unit, or definition change separately before calculating a driver bridge.
2. List each driver value before and after, with its source and whether it was observed, estimated, or assumed.
3. Apply the supplied attribution method to calculate each driver's contribution. State the order for sequential replacement or the interaction allocation for a nonlinear model.
4. Reconcile baseline plus attributed changes and any explicit interaction term to the revised value. Keep the remaining residual visible.
5. Check one changed driver with a small worked example and flag an attribution that reverses under a plausible alternative order.

## Completion check

Return the comparable forecast definitions, driver changes, attribution method and order, contributions, interactions, residual, and unresolved assumptions. The bridge must arithmetically reconcile or name the unexplained difference.

## Stop conditions

Stop a causal or complete-driver claim if a model version, driver definition, attribution rule, or comparable baseline is missing. Do not invent contributions to force a zero residual.
