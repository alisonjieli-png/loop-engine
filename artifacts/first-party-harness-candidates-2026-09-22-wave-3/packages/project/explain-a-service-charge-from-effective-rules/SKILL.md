---
name: explain-a-service-charge-from-effective-rules
description: Reconstruct a proposed service charge from supplied price rules, eligibility, effective time, quantity, and rounding.
---

# Explain a service charge from effective rules

## Use

Use to explain or challenge a quoted service charge using the supplied schedule and case evidence. Produce an internal read-only calculation. Do not collect payment or certify a legal obligation.

## Inputs

- Requested service and account eligibility facts needed by the supplied rule.
- Price-schedule versions with effective dates, currency, units, and rounding rule.
- Service time, quantity or duration evidence, quote lines, and any approved adjustments.

## Procedure

1. Identify the rule governing the service and the event time that selects its version. Resolve the time zone if versions change near the service time.
2. Test eligibility and unit definitions before arithmetic. Mark a missing tier, quantity, or effective-time fact as unknown.
3. Calculate each supported line from rate, quantity, adjustments, and rounding in the specified order. Show intermediate values and the exact rule used for each line.
4. Compare the reconstructed lines with the quote. Classify differences as rate-version, unit, quantity, adjustment, rounding, or unresolved.
5. Return an itemized explanation with source references, selected schedule version, disputed facts, and questions for the billing owner.

## Completion check

Each explained amount traces to an effective rule and quantity record. If the supplied schedule selects the rate at service time, a quote using a later rate cannot pass without an authorized exception.

## Stop

If the controlling schedule, eligibility, effective time, currency, or required rounding rule is missing, hold the amount conclusion. Do not issue an invoice, debit an account, promise a price, or decide contractual liability.
