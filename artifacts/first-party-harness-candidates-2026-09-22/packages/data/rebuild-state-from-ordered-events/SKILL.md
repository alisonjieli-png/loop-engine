---
name: rebuild-state-from-ordered-events
description: Reconstruct an entity's state from its ordered event history. Use when a current-status table disagrees with an append-only event log.
---

# Rebuild state from ordered events

## When to use

Use this to explain a status at a named cutoff from recorded changes. The owner must supply what each event means and which transitions are valid.

## Inputs

- Event records with entity identity, event identity, and the fields used by the authoritative replay order. Keep effective, commit, and observation times distinct when supplied.
- Initial state, event meanings, transition rules, the authoritative replay ordering rule, and cutoff rule.
- A tie-breaking rule when the authoritative order can have ties.
- The log's rule for repeated event identities, including whether identical repeats are idempotent.

## Procedure

1. Select events for the entity and cutoff under the supplied cutoff rule. Compare repeated event identities and their payloads. Collapse identical repeats only when the supplied log rule declares them idempotent; hold conflicting duplicates. Identify missing ordering fields.
2. Order events by the supplied authoritative replay rule, which may use a commit sequence, effective time, or another declared field. Apply the supplied tie breaker where needed. Preserve other timestamps separately to explain delay; their presence does not make them replay order.
3. Apply each event to the prior state under the supplied transition rules. Record an invalid transition rather than guessing its effect.
4. Compare the reconstructed state with a materialized status record for the same cutoff, if one was supplied. Explain discrepancies with the exact event identities and timestamps. Do not compare a historical replay with a present-day status as if they shared a cutoff.
5. Repeat at a second cutoff when the task asks when a discrepancy began.

## Completion check

Return the initial state, cutoff and its inclusion rule, authoritative replay order, ordered event identities, resulting state after each event, final state, and unresolved anomalies. A replay with the same input and rules must produce the same result.

## Stop conditions

Stop on an unknown initial state, undefined event meaning, missing authoritative order or cutoff rule, unresolved ordering tie, or conflicting duplicate identity. Hold repeated identities when no idempotency rule is supplied. Do not repair the log or overwrite a current-status table.
