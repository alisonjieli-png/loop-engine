# Candidate review: classify-ambiguous-posting-account

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `21517`, occupation `13-2011.00` (Accountants and Auditors), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Original wording; no agency endorsement or test.
- Applicability: accounts team reviewing ambiguous classification under its own policy. No tax or audit conclusion; model performance unmeasured.
- Conceptual typed input: `TransactionEvidence`, `EffectiveChart`, `AccountingPolicy`, `EntityScope`.
- Conceptual typed output: `PostingAccountProposal` with alternatives and reviewer question.
- Effect class: read-only proposal; no posting, recoding or approval.
- Good case: A hardware seller's mixed invoice is checked by line purpose and authorized split rule, rather than assigning every line to equipment.
- Known-wrong case: Map the full mixed invoice to equipment solely because the vendor name contains a hardware term.
- Nearest starter item: `check_a_table_join_before_trusting_it.md` checks mapping keys; this method must reason from the economic purpose and effective chart definitions.
- Nearest earlier candidate: `reconcile-account-difference-to-postings` matches existing entries to independent evidence; this method proposes a classification before or during review of an entry.
- Limits: Economic-purpose interpretation can require a qualified accountant. Ambiguity remains a hold for human review.
- Customer search phrasings: "Which account should this mixed vendor invoice go to?"; "Our ledger label fits two accounts. Prepare a classification decision."
