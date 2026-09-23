# Candidate review: synthesize discovery interviews with counterexamples

Status: candidate only. No independent approval, native-load test, or measured benefit.

- Original basis: first-party synthesis of general interview-analysis reasoning. No O*NET text, third-party interview script, or external taxonomy was used.
- Facets: customer researcher or product manager; developer-tool or service company; discovery stage; any harness that supports the Agent Skills format. Named-company policy is supplied privately, never inferred.
- Search phrasings: "Three interviews mention this pain point; what can we actually conclude?"; "Pull user needs from these calls without counting one person's repeated comments as several customers."
- Typed input/output concept: `InterviewSet` with participant identities, source references, consent scope, recruitment context, and per-theme question opportunity, plus `DecisionQuestion` to `EvidenceMatrix`, `EligibleDenominator[]`, `NeedHypothesis[]`, `Counterexample[]`, and `FollowUpQuestion[]`.
- Effects: read-only analysis of authorized material. No outreach, publication, enrollment, or data export.
- Positive fixture: four people were interviewed; three had a documented opportunity to discuss the same task. Two describe a workaround, one succeeds without it, and the fourth was never asked. The output reports two of three eligible participants, one unasked, a total sample of four, and the contrary case.
- Known-wrong fixture: one participant mentions the same difficulty six times. An output claiming "six customers requested this" must fail distinct-person counting. An output treating the unasked fourth participant as a negative response, or claiming market prevalence from a convenience sample, must also fail.
- Nearest overlap and distinction: starter `report_observed_derived_assumed_and_unknown` marks evidence status generally; batch-one `map-observed-customer-journey-friction` maps consented sessions in a journey. This method synthesizes interview accounts across people, preserves negative cases, and controls repeated mentions and sample claims.
- Limits: source notes can misstate what happened, and the sample may be selected. A reviewer should challenge each quoted account, consent scope, deduplication, and whether the skill adds value against no skill.
