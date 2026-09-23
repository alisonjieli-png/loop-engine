---
name: reconcile-inventory-availability
description: Reconcile physical stock, reservations, holds, and available quantity at one cutoff. Use when inventory appears sellable twice or a displayed availability exceeds usable stock.
---

# Reconcile inventory availability

## When to use

Use this for a declared item, location, stock status, and time cutoff. Physical stock and available-to-promise stock answer different questions.

## Inputs

- Item and location identities, unit of measure, cutoff, physical or posted on-hand observations, and stock status definitions.
- Active reservations and holds with identity, quantity, effective interval, and release or expiry evidence.
- The supplied rule for which stock statuses and commitments reduce availability, including transfer and in-transit treatment.

## Procedure

1. Fix one counting grain: item, location, eligible stock status, unit, and cutoff. Separate observations from later postings or corrections.
2. Classify each quantity as eligible on-hand, excluded physical stock, active reservation, active hold, or in-transit. Deduplicate repeated commitment identities only under the supplied identity rule.
3. Apply the supplied availability equation to quantities valid at the cutoff. Keep reservations and holds separate so the same commitment cannot be subtracted twice.
4. Reconcile the displayed availability to the computed figure by identity. Flag negative, overcommitted, expired-but-still-active, and unlocated quantities.
5. Report whether stock at another location is transferable under a supplied rule; do not silently pool locations.

## Completion check

Return the cutoff, grain, eligible on-hand, excluded stock, active commitments, calculated availability, displayed value, and a keyed difference ledger. Every included quantity must have an identity and category.

## Stop conditions

Stop before declaring stock available if the stock status, reservation lifecycle, location, unit conversion, or inclusion rule is unknown. Do not create reservations, release holds, or change inventory.
