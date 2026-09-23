---
name: propagate-a-plan-change-through-commitments
description: Trace a proposed project-plan change through linked dates, resources, acceptance checks, and handoffs before an owner decides on it.
---

# Propagate a plan change through commitments

## Use

Use before deciding whether to accept a proposed schedule, scope, or resource change. Compare a stated proposal with one versioned baseline. Produce a read-only impact map; do not enact the change.

## Inputs

- Baseline plan version and the proposed field-level change.
- Directed dependency links, dated commitments, resource reservations, acceptance checks, and handoff owners.
- Any supplied rules for slack, lead time, fixed dates, and who may revise each commitment.

## Procedure

1. Record the proposal as a delta from the baseline. Keep unchanged baseline facts separate from proposed values.
2. Follow each outgoing dependency from the changed item. For every linked commitment, test whether the delta changes its required start, finish, input, capacity, acceptance window, or owner handoff.
3. Continue through downstream links until no new affected item appears. Record cycles, missing edges, and links whose direction or rule is unknown.
4. Classify each effect as `must change under supplied rule`, `may change pending a decision`, or `unresolved`. Preserve a zero-impact finding only when the relevant links and constraints actually support it.
5. Return the affected-item map with baseline value, proposed value, dependency path, impact reason, decision owner, and unanswered question. Include commitments checked and found unaffected.

## Completion check

Every affected commitment is traceable to the original proposed delta. A moved date with linked test access and customer handoff left at old dates cannot be called zero impact without an explicit rule or evidence.

## Stop

If baseline version or dependency semantics are missing, report the partial map and hold an approval recommendation. Do not edit the plan, notify customers, reserve resources, or approve the proposal.
