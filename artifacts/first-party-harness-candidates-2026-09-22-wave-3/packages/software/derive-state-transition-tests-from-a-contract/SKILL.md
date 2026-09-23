---
name: derive-state-transition-tests-from-a-contract
description: Derive positive, forbidden, repeated-event, and interrupted-transition tests from an explicit state contract. Use when an application has lifecycle states and events.
---

# Derive state-transition tests from a contract

## When to use

Use when an application behavior is defined by states and events, such as an order, job, account, or approval. This skill proposes tests; it does not execute them or declare the implementation correct.

## Inputs

- The versioned state set, event types, allowed transitions, guards, invariants, and authoritative event order.
- The input and output contract for each transition, including effect permissions and any external action.
- Existing checks and known repair, retry, or cancellation behavior.

## Procedure

1. Draw the allowed state-event-state edges and list events that should be refused in each state. Do not invent an undocumented transition.
2. Choose one ordinary case for every required edge and one case that violates each guard or invariant. State the expected result, including whether no external effect occurs.
3. Add repeated-event, out-of-order, and unknown-completion cases where the contract defines idempotency or retry. Hold those cases if the contract does not define their meaning.
4. Identify interruption points before and after durable state change and before and after any external effect. Specify what evidence should distinguish a committed transition from a candidate or unknown one.
5. Compare proposed tests with existing coverage. Return uncovered edges and forbidden paths, with the smallest fixture needed to exercise each.

## Completion check

Every required transition and important refusal has an expected observable state and effect result. The test set includes at least one forbidden edge and one interrupted or repeated event when the contract permits such an event.

## Stop

Hold a coverage claim when state meanings, event order, guards, idempotency, or effect identity are unknown. Do not write fixtures, run tests, change application state, or infer approval from a passing happy path.
