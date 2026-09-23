---
name: reconcile-order-fulfillment-quantities
description: Reconcile accepted order-line quantity with cancellations, partial shipments, returns, and open obligation. Use when orders look complete from one shipment or duplicate events inflate fulfillment.
---

# Reconcile order fulfillment quantities

## When to use

Use this at an order-line grain and declared cutoff. An order may be partly shipped, cancelled, returned, or still open; a shipment count alone cannot determine completion.

## Inputs

- Accepted order lines with stable identities, original quantity, unit, and cutoff.
- Shipment, cancellation, return, and adjustment records with event identities and their links to order lines.
- Supplied business rules for recognition, substitution, return treatment, and whether a return reopens an obligation.

## Procedure

1. Confirm that every event belongs to one order line or has a supplied allocation. Keep accepted, cancelled, shipped, returned, and open quantities in separate columns.
2. Deduplicate repeated event identities under the supplied event rule. Preserve conflicting duplicates and cross-order references as exceptions.
3. Apply only effective cancellations and shipments by the cutoff. Treat returns and substitutions according to the supplied obligation rule, without assuming they undo or satisfy an order.
4. Reconcile each line's accepted quantity to its recognized dispositions and open balance. Flag over-shipments, unallocated shipments, negative balances, and unmatched events.
5. Summarize across lines only after each line has a supported disposition and compatible units.

## Completion check

Return a per-line quantity ledger with cutoff, event references, accepted and recognized dispositions, open balance, and unresolved exceptions. The ledger must balance under the stated business rule.

## Stop conditions

Stop a completion claim if line identity, cancellation status, return treatment, or unit conversion is missing. Do not issue orders, shipments, refunds, or corrections.
