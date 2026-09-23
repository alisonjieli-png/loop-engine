---
name: screen-payable-for-document-mismatch
description: Screen an invoice against order, receipt and supplied payment policy. Use before an invoice is marked payable when quantity, price or identity may disagree.
---

# Screen a payable for document mismatch

## When to use

Use for one supplier invoice or credit and its linked order and receipt records. Produce an exception packet; do not authorize or execute payment.

## Inputs

- Invoice identity, supplier, legal entity, line items, units, currency, dates, taxes and any credit linkage.
- Approved purchase order and amendments, received or accepted quantity, prior invoice and payment identities.
- Effective tolerance, tax, duplicate-payment and partial-receipt rules supplied by the buyer.

## Procedure

1. Match supplier, legal entity, order and invoice identities. Check whether this invoice or underlying charge was already processed, including corrected versions.
2. Compare each invoiced item and unit to the effective order line. Convert units or currency only under a supplied rule and dated rate.
3. Compare invoice quantity with independently accepted receipt quantity, accounting for prior invoices and permitted advances. A delivery notification alone is not accepted receipt.
4. Compute price, quantity, tax and total differences separately. Apply supplied tolerances without treating a within-tolerance amount as proof of supplier or receipt identity.
5. Return pass, exception or indeterminate per line, with the document and owner needed to resolve each exception.

## Completion check

Return document identities, effective policy, line-level match ledger, prior settlement links, exceptions and unresolved evidence. The invoice total must bridge to its lines and allowed adjustments.

## Known-wrong case and stop

An invoice bills 100 units, while only 80 were accepted and 20 are merely expected. Marking all 100 payable from the order quantity is wrong unless a supplied advance rule permits it. Hold when order revision, receipt evidence, duplicate history or tolerance rule is missing. Do not approve, post or pay.
