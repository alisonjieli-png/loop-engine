---
name: reconcile-return-credit-to-original-sale
description: Reconcile a proposed return credit to the original sale, delivered quantity and received return. Use when a credit request may exceed eligible units or the original price.
---

# Reconcile a return credit to the original sale

## When to use

Use for one return request and original sale under the seller's effective return policy. This method calculates eligibility and unresolved differences; it does not issue a refund or credit.

## Inputs

- Original order line, shipment, invoice and settlement identities with delivered quantity, currency, unit price, allocated discounts and original net consideration eligible under policy.
- Return authorization, physical receipt or inspection evidence, plus all prior issued and approved-pending credits, refunds, exchanges and returns linked to exact sale lines with both quantities and amounts. Distinguish a partial price concession from a fully credited returned unit.
- Effective policy for time window, condition, fees, taxes, exchanges and approval path.

## Procedure

1. Bind each requested unit and every earlier monetary adjustment to the exact original sale line. Distinguish requested, authorized, physically received and accepted-for-credit quantities. An unlinked historical credit is a hold, not zero.
2. Compute remaining quantity as eligible delivered units minus prior fully credited or exchanged units and units reserved by approved pending returns. A partial price concession does not silently consume a full unit, but it reduces the separate monetary headroom.
3. Reconstruct the original line's eligible refundable net consideration from its actual sale price and allocated discounts, with taxes and fees handled under the supplied policy. Compute remaining monetary headroom as that original eligible amount minus **all** prior issued and approved-pending monetary credits against the same line, including partial concessions. Refuse a negative headroom or unknown currency conversion.
4. Cap a proposed credit by both the remaining eligible quantity at its original per-unit value and the remaining monetary headroom. Show line-level quantity and value bridges; a current catalogue price is not the original sale price. Keep taxes, fees and exchanges separately reconciled under the policy, never as an unexplained extra credit.
5. Record condition and time-window evidence, exceptions and missing links. Route unresolved cases to the named approver with a concise packet rather than assuming prior credit history is complete.

## Completion check

Return exact sale-line and prior-adjustment links, quantity bridge, original eligible net amount, prior issued and pending monetary credits, remaining monetary headroom, proposed amount, policy version and decision needed. Every proposed unit must be delivered, eligible and not previously fully credited; proposed amount plus prior and pending credits cannot exceed the original eligible refundable amount for that line.

## Known-wrong case and stop

One eligible returned unit originally sold for 100 units of currency and already received a 40-unit partial credit. The unit-count cap still permits one return, but the monetary cap permits at most 60 more, not 100. A second full-unit credit already issued also reduces the available quantity; do not credit it again. Hold when the original sale-line amount, prior or pending credit amounts, their exact line links, return receipt or effective policy is missing. Do not create invoices, issue credits, refund or message the customer.
