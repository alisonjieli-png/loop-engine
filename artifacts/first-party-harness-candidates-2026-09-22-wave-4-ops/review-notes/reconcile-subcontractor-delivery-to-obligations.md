# Candidate review: reconcile-subcontractor-delivery-to-obligations

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `8950`, occupation `13-1081.00` (Logisticians), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Original wording; no agency endorsement or test.
- Applicability: vendor manager for a project subcontract, with approved terms and acceptance records. Model performance unmeasured.
- Conceptual typed input: `SubcontractVersion`, `Obligation`, `Submission`, `AcceptanceDecision`, `Cutoff`.
- Conceptual typed output: `ObligationEvidenceLedger` with open acceptance gaps.
- Effect class: read-only comparison; no acceptance, rejection, payment or contractual notice.
- Good case: Submitted test report is listed as received, but a required signed inspection remains open, so the deliverable is not accepted.
- Known-wrong case: Treat a vendor's self-reported complete status or uploaded report as the organization's acceptance decision.
- Nearest starter item: `write_acceptance_criteria_a_reviewer_can_check.md` drafts criteria; this method applies already effective, versioned subcontract criteria to particular evidence.
- Nearest earlier candidate: `qualify-a-partner-integration-proposal` screens a potential partner; this method checks performance against an executed subcontract.
- Limits: Breach, payment and waiver decisions require terms and authorized humans. The method cannot infer legal effect from a missing file.
- Customer search phrasings: "Our subcontractor says the deliverable is done. What acceptance proof is still missing?"; "Map contract obligations to vendor submissions."
