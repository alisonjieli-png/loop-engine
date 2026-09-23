# Candidate review: reconcile-account-difference-to-postings

Status: candidate only. These exact bytes have no independent approval, native-use result, or measured customer benefit.

- Source and rights: Original candidate wording prompted by task ID `21516`, occupation `13-2011.00` (Accountants and Auditors), in the [O*NET® 31.0 Database](https://www.onetcenter.org/database.html) by the U.S. Department of Labor, Employment and Training Administration. The applicable database file is offered under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). The pinned local ZIP has SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. The method and examples are newly written; no O*NET task prose is copied into the skill. O*NET and the Department of Labor have not endorsed or tested it.
- Job, company, and project facets: accounting analyst; any organization with a period close; one account reconciliation before independent accounting review.
- Model applicability: general text-capable harnesses; performance with any model is unmeasured.
- Conceptual typed input: `AccountPeriod`, `OpeningBalance`, `Postings`, `SourceRecords`, `ReconciliationPolicy`.
- Conceptual typed output: `PostingReconciliation` with a balance bridge, supported matches, timing differences, unmatched items, and ambiguities.
- Effect class: read-only analysis. No journal entry, approval, bank transfer, or accounting certification.
- Good fixture: A posting for transaction A has the same amount, sign, date basis, and source identity as the independent source record for A. It is matched once; a second posting with the same amount but transaction B remains unmatched until B's source evidence appears.
- Known-wrong fixture: A reviewer pairs transaction B with A's source record because both show 500 units of currency, then declares the account fully reconciled. Reject the amount-only pairing and keep the true unmatched posting visible.
- Nearest starter item: `check_a_table_join_before_trusting_it.md` checks key cardinality in a table join; this method requires independent transaction support and a period balance bridge.
- Nearest wave 1 item: `reconcile-snapshot-changes` classifies before-and-after records; this method reconciles postings and external source evidence under a supplied account policy.
- Nearest wave 2 item: `reconcile-record-flow-across-stages` follows pipeline identities; this method matches account postings to independent transaction evidence and timing rules.
- Limits: Accounting policy and controls vary. Independent review should test sign reversal, currency mismatch, period cutoff, and a permitted split settlement. The method makes no tax, audit, or financial-statement conclusion.
- Customer search phrasings: "Why does this account still have a difference after we matched equal amounts?"; "Which postings have real source support for this month's balance?"
