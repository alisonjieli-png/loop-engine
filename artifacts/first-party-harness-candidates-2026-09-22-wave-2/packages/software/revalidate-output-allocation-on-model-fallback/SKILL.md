---
name: revalidate-output-allocation-on-model-fallback
description: Review output capacity and remaining allowance for a proposed model route fallback without carrying limits or context eligibility across providers.
---

# Revalidate output allocation on model fallback

## Use case

Use after a model route fails or becomes unavailable and another route is proposed for the same step. Produce an eligibility decision before any fallback call.

## Required inputs

- Primary route and failure class, proposed provider and exact model revision, and source-backed output capacity for each relevant route.
- The step's output contract, any explicit typed per-call allocation and its route binding, remaining total authority, prior physical usage, and permitted fallback order.
- Selected context or model-specific material variants, if any, with their eligibility records.

## Procedure

1. Determine whether the failure permits fallback at all. Keep a formatting repair, same-route retry, provider failover, and task replanning as distinct actions.
2. Resolve the proposed route's own maximum output capacity from a source that names its provider, interface, and exact model revision. Unknown is unknown; do not copy the primary route's limit.
3. If an explicit typed output allocation is authorized for the proposed route, check it against that route's known capacity and decision evidence. Otherwise the proposed call requests that route's full known output capacity. Do not derive a smaller allowance from an estimate of answer length or carry the primary route's allocation across the fallback. Keep capacity, chosen allowance, and remaining total-run authority separate.
4. Include prior physical calls and unresolved usage in the remaining-allowance decision. Missing provider usage is not zero, and an uncertain earlier call is not a free retry.
5. Recheck context fit, approved model-specific material, recipient permissions, and any spending bound for this route. A compatible friendly model name does not qualify a previous variant.
6. Return `eligible`, `ineligible`, or `unknown`, with source identities, allocation, remaining-authority state, and the first blocking condition.

## Completion check

No fallback uses the primary route's capacity, allowance, variant, or cost assumption without a separate check. In the absence of a new explicit allocation, the requested allowance equals the fallback route's full known output capacity. Unknown capacity or insufficient remaining authority produces no proposed physical call.

## Stop or hold

Hold when fallback authority, exact model capacity, previous usage, variant eligibility, or enough authority for the selected allowance is missing. Do not make a model call, change the route, or invent a smaller output ceiling.
