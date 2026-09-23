---
name: classify-ambiguous-posting-account
description: Propose an account classification for a transaction using the supplied chart and transaction purpose. Use when a plausible amount fits several accounts.
---

# Classify an ambiguous posting account

## When to use

Use before posting one transaction or reviewing an ambiguous existing classification. The result is a proposed account with evidence and unresolved alternatives, not an accounting approval.

## Inputs

- Transaction identity, dated source document, economic purpose, item or service description, entity, currency and amount.
- Versioned chart of accounts, account definitions, effective accounting policy, project or cost-center rules and authorized reviewer path.
- Any prior classification and correction history for this same source identity.

## Procedure

1. Establish what occurred from the source document and delivery or service evidence. Treat a memo line or supplier name as a clue, not the transaction's economic purpose.
2. Filter accounts by entity, effective date, transaction type and mandatory dimensions. Do not choose a retired or blocked account because its label sounds close.
3. Compare remaining accounts against the supplied definitions and recognition rule. State the decisive facts and any facts still missing.
4. Flag conflicting instructions or a transaction spanning multiple purposes. Propose a split only when the policy permits it and the source supports allocable amounts.
5. Prepare a reviewer packet with the suggested account, alternatives, source references and the exact policy clause or unresolved question.

## Completion check

Return the source identity, policy version, candidate accounts considered, evidence for inclusion and exclusion, proposed mapping or hold, and reviewer needed. Repeated identical supplier names do not by themselves create a reusable mapping rule.

## Known-wrong case and stop

An invoice from a hardware vendor includes a subscription service; coding the full amount as equipment solely from the vendor name is wrong. Hold when the transaction purpose, effective account definition or permitted split is unclear. Do not post, recode, certify or transmit an entry.
