# Candidate review: trace-statement-line-to-ledger

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `21514`, occupation `13-2011.00` (Accountants and Auditors), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Original method wording; no agency endorsement or test.
- Applicability: reporting analyst checking one statement line against a versioned chart and ledger extract. Model performance unmeasured.
- Conceptual typed input: `StatementLine`, `LineMapping`, `LedgerBalance`, `Adjustment`, `Period`.
- Conceptual typed output: `StatementLineageBridge` with recomputed total and mapping exceptions.
- Effect class: read-only trace; no ledger or report edit, certification or opinion.
- Good case: Every included account appears once with correct sign; posted and consolidation adjustments are separated, and the line difference is shown.
- Known-wrong case: A duplicated account is offset by a manual adjustment, so the displayed total matches; falsely mark lineage complete from numeric equality alone.
- Nearest starter item: `reproduce_the_evidence_a_report_claims.md` checks report evidence broadly; this method traces exact financial account-to-line mapping and adjustments.
- Nearest earlier candidate: `reconcile-account-difference-to-postings` traces one account to transactions; this method traces a statement line across accounts and consolidation rules.
- Limits: Reporting and currency rules vary. A trace is not an independent audit opinion.
- Customer search phrasings: "Which ledger balances make up this balance-sheet line?"; "The reported total matches, but could a mapping duplicate be hidden?"
