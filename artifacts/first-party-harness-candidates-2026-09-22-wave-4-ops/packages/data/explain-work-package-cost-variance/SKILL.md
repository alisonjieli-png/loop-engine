---
name: explain-work-package-cost-variance
description: Explain project cost variance by work package, period and committed versus incurred amounts. Use when a single total hides timing or scope changes.
---

# Explain work-package cost variance

## When to use

Use for a versioned project baseline and a reporting cutoff. Explain differences; do not approve spending or alter a budget.

## Inputs

- Baseline work-package amounts, currency, period and scope; approved changes with effective dates.
- Posted actuals, original accruals, signed accrual reversals or clearing entries, commitments and forecast-to-complete records with exact cost-event, order, receipt, accrual and invoice links.
- Supplied allocation, exchange-rate and reporting rules, including the source's balance basis, settlement treatment, cutoff and shared charges.

## Procedure

1. Reconcile the original baseline through approved changes to the current authorized baseline. Keep unapproved requests outside that bridge.
2. Assign each actual, accrual and commitment to one work package and cutoff period using source identity; keep ambiguous charges unassigned rather than split by guess. Link each cost event through its commitment, receipt, accrual, clearing entry and posted invoice where they exist.
3. For each event, compute open accrual as original accrual plus signed adjustments and reversals through the cutoff. A posted actual replacing an accrual needs an exact settlement link and reversal or policy-defined clearing evidence. If both remain positive for the same event, hold the final incurred figure rather than adding them. Reject negative open accrual unless an evidenced correction explains it.
4. Compute incurred-to-date as posted actuals **excluding accrual postings** plus valid open accruals. Compute residual commitment as committed value minus the portions already represented by actuals or open accruals, using the supplied commitment balance basis only once. Known exposure is incurred-to-date plus residual commitment; forecast beyond those covered amounts stays separate. Reconcile each amount to its source instead of adding a full purchase order, accrual and invoice together.
5. Show incurred variance, remaining committed exposure and forecast-at-completion variance separately. Classify supported differences as timing, quantity, rate, scope or unresolved. Name decisions needed when evidence shows the remaining allowance cannot cover scope; do not invent a causal explanation or certainty from an incomplete forecast.

## Completion check

Return the baseline bridge; per-work-package cost-event links; posted actual, original and reversed accrual, valid open accrual and residual commitment balances; incurred and exposure formulas; unresolved allocations, cutoff and forecast assumptions. The bridge must reconcile without counting a settled commitment or accrual twice. If an actual and accrual appear for the same event without a clearing link, report the conflict and withhold a final variance or exposure total.

## Known-wrong case and stop

A purchase order for 8,000 units of currency is accrued for 8,000 after receipt. Later an 8,000 invoice posts and the 8,000 accrual reverses. The event's known exposure is 8,000, not 24,000: posted actual 8,000 plus open accrual 0 plus residual commitment 0. Counting the invoice and unreversed accrual together, or also counting the full purchase order, is wrong. Hold a final variance when the baseline, cutoff, posting-to-accrual clearing link, reversal, or commitment settlement basis is missing. Do not post costs or approve a budget change.
