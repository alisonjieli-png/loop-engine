---
name: allocate-scarce-stock-by-promised-service
description: Propose a bounded allocation of scarce stock to competing orders under supplied service promises. Use when available units cannot cover all committed demand.
---

# Allocate scarce stock by promised service

## When to use

Use for one item and decision cutoff when verified available units are fewer than the units requested by eligible orders. This method proposes an allocation; it does not reserve stock or change an order.

## Inputs

- Item identity, location and cutoff; gross usable on-hand quantity, holds, and active reservations linked to exact orders and stock lots.
- Order identities, item and revision, fulfillable location, ordered, fulfilled and cancelled quantities, promised times, and per-order hold, release and priority status as of the cutoff. Include the effective eligibility, handling, transit, partial-shipment and priority policies.
- Any confirmed inbound lot, quantity and evidenced stock-ready time after receipt and quality gates. The policy must explicitly permit planning with future supply.

## Procedure

1. Compute free on-hand stock as gross usable on-hand minus holds and **all** active reservations against that on-hand pool. Reconcile the reservation ledger to exact orders and lots. A negative free balance or unlinked reservation is a hold, not extra supply.
2. Reject duplicate order identities. Before ranking, check each order against the effective policy: exact requested item and revision, fulfillable location, active customer or order holds, release status, priority class or status, and any other required eligibility field at the cutoff. Exclude a mismatched or held order from **new** allocation. An unknown hold, release or priority status is unresolved and also excludes the order; do not infer release or rank from a due date or free stock. If an unresolved order could outrank another, hold a final lower-priority proposal unless the supplied policy explicitly permits skipping it. Keep existing reservations committed and blocked until separately authorized release.
3. For each order compute unfilled demand as ordered minus fulfilled minus cancelled, then incremental demand as unfilled demand minus its active reservation. Do not subtract fulfillment twice when an input is already a remaining balance. Refuse negative or ambiguous quantities and reservations that exceed unfilled demand. Quantity headroom does not override the eligibility result from step 2.
4. Keep each permitted inbound lot in a separate, time-stamped future pool. Subtract holds and active reservations against that lot before proposing its free quantity. Derive the order's required stock-ready time from its promise and supplied handling or transit lead time. Check **existing reservations too**: a reservation against a lot ready after that time does not cover the on-time promise, although its units remain committed until an authorized release. A future lot can support an on-time proposal only when its evidenced stock-ready time is no later than the requirement; a later lot is a separate late option, never current free stock.
5. Apply the supplied priority and tie-break rules only to incremental demand of orders proven eligible and releasable in step 2. Allocate each free or future unit once within its own pool and time, observing lot and partial-shipment constraints. Preserve existing reservations as already committed, not new allocations.
6. Compute remaining unfilled demand and pool balances. Show affected promises and the evidence or decision needed to resolve each conflict. Do not silently move a reserved unit or one promised to a higher-priority order.

## Completion check

Return the cutoff and eligibility policy version; gross-to-free bridge; reservation-to-order links; on-hand and future pools with stock-ready times; per-order item, location, hold, release and priority-status decision with evidence; existing reservation, incremental proposal, unresolved priority blocker, and unfilled balance. For each pool, new allocations plus unallocated units equal its free quantity. For each order, fulfilled plus cancelled plus active reservations plus new allocations cannot exceed ordered quantity. A new allocation requires proven item and location match, a releasable, unheld order and a resolved priority status. Count only time-eligible reservations and proposals for releasable orders toward on-time coverage; keep reservations on held orders blocked. Mark every future allocation conditional and never call it on time when stock becomes ready after the order's required stock-ready time.

## Known-wrong case and stop

If gross usable on-hand is 12 and 4 units are already reserved for order A, the free pool is 8. When A and B each ordered 10 with nothing fulfilled or cancelled, A's incremental demand is 6 and B's is 10. If A is releasable and its A-first priority is evidenced, at most 6 **new** units go to A and 2 to B; proposing 10 new for A double commits 4. If A instead has an active order hold while B is releasable, priority cannot allocate new units to A: propose 0 new for A and at most 8 for B. A's 4 reserved units remain blocked, not available to B or counted as fulfilled. A confirmed inbound lot stock-ready on the 12th cannot satisfy a promise requiring ready stock on the 10th. Hold when an order's identity, item, location, hold, release or priority status, reservation links, quantity basis, stock-ready time, handling lead time or priority rule is missing. Do not release a hold, move a reservation, ship or notify customers without separate authority.
