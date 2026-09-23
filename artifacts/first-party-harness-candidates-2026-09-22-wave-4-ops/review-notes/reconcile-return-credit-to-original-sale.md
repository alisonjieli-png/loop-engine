# Candidate review: reconcile-return-credit-to-original-sale

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `2589`, occupation `43-4051.00` (Customer Service Representatives), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Original wording; no agency endorsement or test.
- Applicability: returns specialist checking a proposed credit against one original transaction. Model performance unmeasured.
- Conceptual typed input: `OriginalSaleLine`, `DeliveredQuantity`, `ReturnReceipt`, `PriorAndPendingCreditLedger`, `ReturnPolicy`.
- Conceptual typed output: `ReturnCreditReconciliation` with independent unit and monetary headroom bridges.
- Effect class: read-only proposal; no refund, credit issuance or customer contact.
- Good case: A single eligible unit sold for 100 currency units has a prior 40-unit partial refund linked to its sale line. Quantity headroom is one unit; monetary headroom is 60. A full return proposes no more than 60 additional units of currency under the supplied policy.
- Known-wrong case: Propose 100 more for the same unit because no full-unit return was previously recorded, bringing total credits to 140 against an original eligible amount of 100. The monetary cap rejects it. A missing prior-credit-to-sale-line link holds the proposal rather than treating the amount as zero.
- Nearest starter item: `check_a_table_join_before_trusting_it.md` tests identity joins; this method reconciles sale, shipment, receipt and prior credit identities with quantity and value caps.
- Nearest earlier candidate: `reconcile-order-fulfillment-quantities` explains outgoing quantities; this method governs the reverse flow and original-sale credit value.
- Limits: Effective policy for condition, tax, fees and deadlines must be supplied. A quantity check cannot replace the line-level monetary cap; missing historical credit linkage blocks the result. A human or authorized service owns issuance.
- Customer search phrasings: "Does this return credit exceed what the customer actually bought and returned?"; "Check the refund amount against prior credits and original discounts."
