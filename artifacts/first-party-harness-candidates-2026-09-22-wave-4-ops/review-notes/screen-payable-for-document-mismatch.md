# Candidate review: screen-payable-for-document-mismatch

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `21533`, occupation `13-2011.00` (Accountants and Auditors), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Original wording; no agency endorsement or test.
- Applicability: payable analyst reviewing one invoice against approved purchase and receipt records. Model performance unmeasured.
- Conceptual typed input: `SupplierInvoice`, `PurchaseOrder`, `AcceptedReceipt`, `PaymentHistory`, `PayablePolicy`.
- Conceptual typed output: `InvoiceExceptionPacket` with line-level match and holds.
- Effect class: read-only screen; no payable posting, approval or payment.
- Good case: Invoice quantity 100, accepted quantity 80 and no advance rule lead to an 80-unit supported maximum and 20-unit exception.
- Known-wrong case: Approve 100 units from the order quantity alone while the other 20 have merely been shipped, not accepted.
- Nearest starter item: `check_a_table_join_before_trusting_it.md` catches bad joins; this method enforces invoice-order-receipt identities, quantities and settlement history under a buyer policy.
- Nearest earlier candidate: `reconcile-order-fulfillment-quantities` bridges order and delivery amounts; this method adds invoice, price, tolerance and duplicate-payment controls.
- Limits: Tax and tolerance rules vary and must be supplied. Human authorization owns payment.
- Customer search phrasings: "Does this supplier invoice match what we actually received?"; "Flag overbilling and duplicate invoice risks before payment."
