# Candidate review: audit-sampling-frame-coverage

Status: candidate only. These exact bytes have no independent approval, native-use result, or measured customer benefit.

- Source and rights: Original candidate wording prompted by task ID `21825`, occupation `15-2051.00` (Data Scientists), in the [O*NET® 31.0 Database](https://www.onetcenter.org/database.html) by the U.S. Department of Labor, Employment and Training Administration. The applicable database file is offered under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). The pinned local ZIP has SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. The method and examples are newly written; no O*NET task prose is copied into the skill. O*NET and the Department of Labor have not endorsed or tested it.
- Job, company, and project facets: survey methodologist or data scientist; service provider or research organization; pre-publication coverage audit for one study population.
- Model applicability: general text-capable harnesses; performance with any model is unmeasured.
- Conceptual typed input: `TargetPopulation`, `SamplingFrame`, `SelectionRule`, `Invitations`, `ResponseDispositions`.
- Conceptual typed output: `FrameCoverageAudit` with stage counts, excluded groups, nonresponse, and supported inference scope.
- Effect class: read-only analysis. No sampling, messaging, or recruitment action.
- Good fixture: The target has 1,000 known members, including 200 offline members. An online-only frame has 800 members. The method records 80% frame coverage before counting invitations or responses, and limits the direct evidence to reachable members.
- Known-wrong fixture: An analyst generalizes responses to all 1,000 members without acknowledging that 200 were absent from the frame. Reject the population claim even if every framed member responded.
- Nearest starter item: `audit_data_splits_for_errors_and_leakage.md` checks model train and test partitions; this method checks target-to-frame-to-response coverage for inference.
- Nearest wave 1 item: `screen-a-study-for-a-product-decision` screens an external study's transfer to a decision; this method audits the original study's own sampling stages.
- Nearest wave 2 item: `synthesize-discovery-interviews-with-counterexamples` names qualitative recruitment limits; this method reconciles quantitative frame, selection, invitation, and response counts.
- Limits: Target population totals may be unknown, and missing members' outcomes cannot be inferred. Independent review should test duplicate frame identities, changed eligibility, unknown dispositions, and complete enumeration mislabeled as full response.
- Customer search phrasings: "Who could never have received our survey link?"; "Can these responses support a claim about all users, including people without online access?"
