---
name: reconcile-account-difference-to-postings
description: Trace an account difference to independently identified postings and source records. Use when equal amounts are being matched without transaction evidence.
---

# Reconcile an account difference to postings

## When to use

Use for one account and period under a supplied reconciliation policy. An equal amount is a candidate match, not proof that two records describe the same transaction.

## Inputs

- Opening balance, period-scoped postings with stable entry identities, dates, signs, amounts, units or currencies, and correction links.
- Independent source references and records with transaction identities, effective dates, and observed amounts.
- Supplied matching, timing-difference, conversion, and period-cutoff rules.

## Procedure

1. Reconcile the opening balance and scoped posting total to the reported closing balance. Preserve duplicate, reversed, and corrected entries as distinct observations until the policy resolves them.
2. Propose matches using source identity and transaction evidence before amount. Check sign, currency, effective date, account, and any permitted one-to-many relationship.
3. Partition postings and source records into evidenced matches, permitted timing differences, unmatched items, and ambiguous candidates. An amount-only coincidence stays ambiguous.
4. Build a numeric bridge from opening through postings and named differences. Trace each bridge line to the posting and source reference or mark the evidence missing.
5. State the exact difference still unexplained and what record or policy would resolve it.

## Completion check

Return the account, period, policy version, balance bridge, keyed match ledger, timing differences, unmatched records, ambiguities, and remaining difference. Matched identities cannot be used twice without a supplied split rule.

## Stop conditions

Hold a completed-reconciliation or accounting conclusion when transaction identity, source support, cutoff, sign, currency, or matching policy is missing. Do not post, reverse, correct, approve, or transmit entries.
