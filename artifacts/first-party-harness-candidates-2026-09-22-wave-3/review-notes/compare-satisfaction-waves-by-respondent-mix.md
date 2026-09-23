# Candidate review: compare-satisfaction-waves-by-respondent-mix

Status: candidate only. These exact bytes have no independent approval, native-use result, or measured customer benefit.

- Source and rights: Original candidate wording prompted by task ID `5435`, occupation `13-1161.00` (Market Research Analysts and Marketing Specialists), in the [O*NET® 31.0 Database](https://www.onetcenter.org/database.html) by the U.S. Department of Labor, Employment and Training Administration. The applicable database file is offered under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). The pinned local ZIP has SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. The method and examples are newly written; no O*NET task prose is copied into the skill. O*NET and the Department of Labor have not endorsed or tested it.
- Job, company, and project facets: survey analyst or customer researcher; service company or software vendor; recurring satisfaction report before a product decision.
- Model applicability: general text-capable harnesses; performance with any model is unmeasured.
- Conceptual typed input: `SurveyWaves`, `QuestionVersion`, `InvitationFrames`, `SegmentCounts`, optional `ReferenceWeights`.
- Conceptual typed output: `SatisfactionComparabilityReview` with response counts, within-segment and overall rates, mix changes, and claim limits.
- Effect class: read-only analysis of supplied survey data. No respondent contact or survey change.
- Good fixture: Two segments have unchanged positive-response rates of 90% and 50%. Their respondent mix changes from equal shares to 80% and 20%, so the overall rate moves from 70% to 82%. The method reports a composition change, not evidence of within-segment improvement.
- Known-wrong fixture: A dashboard calls the 12-point overall increase a like-for-like rise without showing the changed respondent mix. Reject that inference; unknown nonrespondent attitudes remain unknown.
- Nearest starter item: `check_that_a_result_is_stable_and_generalizes.md` tests a finding across samples; this method audits repeated survey instrument, invitation, response, and segment comparability.
- Nearest wave 1 item: `check-rate-denominators` validates a rate's eligible population; this method additionally compares wave-specific respondent mix and optionally supplied fixed weights.
- Nearest wave 2 item: `synthesize-discovery-interviews-with-counterexamples` handles qualitative interviews; this method analyzes quantitative survey-wave composition and nonresponse.
- Limits: Fixed weighting cannot repair unknown within-segment nonresponse or a changed question meaning. Independent review should test sparse cells, changed recruitment mode, and repeated respondents.
- Customer search phrasings: "Did satisfaction really improve, or did more of our happy customers answer this time?"; "Can we compare this quarter's survey score with last quarter after the invitation list changed?"
