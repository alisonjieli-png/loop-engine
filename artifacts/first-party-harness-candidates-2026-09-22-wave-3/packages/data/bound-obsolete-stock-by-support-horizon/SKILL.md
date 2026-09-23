---
name: bound-obsolete-stock-by-support-horizon
description: Classify revision-specific stock exposure using supplied compatibility and support rules. Use when older parts are being called obsolete without checking supported demand.
---

# Bound obsolete stock by support horizon

## When to use

Use this for one item family and a declared decision horizon. An older revision is not automatically unusable, and a demand forecast is not a firm allocation.

## Inputs

- Stock identities, quantities, units, locations, revision identifiers, and a dated stock cutoff.
- Versioned compatibility and support rules, product or service end dates, and any restriction on substituting revisions.
- Approved demand or allocation evidence through the horizon, with uncertainty and shared-demand rules where supplied.

## Procedure

1. Reconcile each stock quantity to one revision and cutoff. Keep unknown or mixed revisions separate.
2. For each revision, list supported uses and effective dates under the supplied rules. Compatibility identifies a possible use; it does not establish that all units will be consumed.
3. Build a quantity-allocation ledger from firm demand identities to compatible stock revisions within the horizon. Use only the supplied allocation rule when demand can take more than one revision. Each demand quantity may cover stock once, and firm-covered quantity for a revision cannot exceed either its stock or uniquely assigned compatible demand.
4. Separate firm-covered quantity, quantity with no permitted supported use, compatible but uncovered quantity at risk, and quantity unresolved because demand or compatibility evidence is missing. Keep estimated demand apart from firm coverage. Give exposure bounds only when the supplied demand range and allocation rule support them.
5. Reconcile those quantities to stock by revision and show the rule, demand identity, date, or assumption behind each classification. One supported use cannot cover an entire stock quantity without enough uniquely assigned demand.

## Completion check

Return a revision-level exposure table and demand-allocation ledger with cutoff, horizon, stock quantity, supported uses, uniquely assigned firm-covered quantity, uncovered quantity, unsupported quantity, and unresolved quantity. The categories must reconcile to scoped stock without counting demand twice.

## Stop conditions

Hold a write-off, disposal, or firm obsolete-stock conclusion when support dates, compatibility, inventory identity, or allocation policy is missing. Do not move, reserve, sell, write off, or dispose of stock.
