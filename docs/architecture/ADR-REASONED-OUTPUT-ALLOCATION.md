# Reasoned output allocation within source-backed capacity

Date: 2026-09-05. Status: bounded implementation, offline verification.

## Decision

Separate the provider's capacity from the requested allowance and the run's
resource authority. `ModelOutputCapability` records the source-backed capacity.
`ModelOutputAllocation` is a passive, immutable class object containing that
capacity snapshot, exact provider/model/route identity, requested tokens, and
decision provenance. The request carries that object, not a collection of
unrelated numeric overrides.

Without an allocation, the provider request uses the full known capacity.
An explicit user or reasoning-Loop allocation may select a different allowance
within it. A bare lower scalar is not that decision, and unknown capacity cannot
be replaced with an invented ceiling. No default output floor or automatic
halving policy is introduced.

The existing Practitioner recovery path supplies bounded current-task,
response-contract, failure, capacity and history-reference evidence to a
counted reasoning call. That call shares the failing task's model session and
budget. Only implemented recovery operations may execute. Model output cannot
grant route, model, source-disclosure or spending authority.

## Mechanical safeguards

The gateway rechecks the allocation against exact route identity and the
unchanged capacity snapshot. Native adapters receive both facts through the
typed allocation. Their wire field still contains a numeric allowance because
provider APIs require one; the field is not a hardcoded policy.

Strict total-token requests additionally need a qualified bound for the exact
provider request. Character-based estimates are diagnostics, not hard bounds.
An unknown bound refuses dispatch. A source-backed bound must cover framing
and every provider-reported input/output token, including charged reasoning.

The first shared-session implementation is single-flight. Public result-list
mutation cannot refund its private counters. Uncertain usage, interruption,
or a violated bound prevents further bounded work until the uncertainty is
resolved. This is not cross-process transactionality or a billing guarantee
against a provider violating its own contract.

## Scope

This decision permits explicit reasoned allocations, replacing the earlier
unconditional exact-maximum wire rule only when such an allocation exists.
It does not install a new runtime, turn each number into an LLM call, or remove
real provider constraints. The [verification report](../verification/REASONED-OUTPUT-AND-MODE-POLICY-2026-09-05.md)
separates the tested path from live qualification and remaining work.
