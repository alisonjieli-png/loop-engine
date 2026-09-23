# Candidate review: explain-work-package-cost-variance

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `21469`, occupation `13-1082.00` (Project Management Specialists), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Original method wording; no agency endorsement or test.
- Applicability: project controller at a cutoff with versioned work packages. Any model result requires arithmetic checking; measured model benefit is absent.
- Conceptual typed input: `BaselineVersion`, `ApprovedChange`, `CostEventLink`, `PostedActual`, `AccrualAndReversal`, `CommitmentBalance`, `Forecast`, `Cutoff`.
- Conceptual typed output: `WorkPackageVarianceBridge` with posted actual, valid open accrual and residual commitment as distinct reconciled buckets.
- Effect class: read-only cost explanation; no posting, spending or budget approval.
- Good case: A purchase order for 8,000 is received and accrued for 8,000. At the next cutoff, an 8,000 invoice posts and the accrual reverses for 8,000. Posted actual 8,000 plus open accrual 0 plus residual commitment 0 equals known exposure 8,000.
- Known-wrong case: Add purchase order 8,000, accrual 8,000 and paid invoice 8,000 to report 24,000; or add an unreversed accrual to a posted invoice without a clearing link. Reject duplicate exposure and hold a final total when the reversal or settlement evidence is missing.
- Nearest starter item: `read_a_profile_and_find_the_dominant_cost.md` identifies a performance cost; this method reconciles financial baseline, actual and commitment categories over project work packages.
- Nearest earlier candidate: `bridge-forecast-driver-changes` explains changes between forecasts; this method explains variance to an approved project baseline while separating settled commitments.
- Limits: Accrual reversal, commitment-balance, currency and allocation rules are organization-specific and must be supplied. A missing invoice-to-accrual link blocks a final figure. No financial certification.
- Customer search phrasings: "Why is this work package over budget when a purchase order already became an invoice?"; "Separate spent and still-committed costs by project task."
