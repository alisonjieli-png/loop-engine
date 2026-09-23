# Candidate review: check-rate-denominators

Status: candidate only. The exact `packages/data/check-rate-denominators/SKILL.md` bytes need independent review before admission.

- Original authoring and source basis: Written for this batch by a Codex research subagent from elementary set and rate definitions. The [Agent Skills specification](https://agentskills.io/specification) informed the file structure. No external procedure was copied. License and originality remain review decisions.
- Applicability facets: product analytics, quality analysis, operations, service reports; any task presenting a share or event rate.
- Search phrasings (author-supplied discovery aids, not evaluation queries): "Did January signups convert within 30 days, or are we counting February newcomers?"; "Our defect percentage jumped after eligibility changed; can you check who was counted?"
- Typed input and output concept: Inputs are `MetricDefinition`, `EligiblePopulation`, `ObservedEvents`, `CohortWindow`, and `OutcomeWindow`. Output is `RateAudit` with numerator, denominator, exclusions, unmatched identities, maturity status, and calculated or undefined rate.
- Declared effects: read-only analysis of supplied data. No data change, network call, credential, or external mutation.
- Known-good example: Among 100 users who joined a January cohort, 20 distinct users have at least one qualifying event by the end of the declared February observation window. Report `20/100 = 20%`, both counts, and the cohort and outcome windows.
- Known-wrong example: Those 20 users generated 30 events; report `30/100 = 30%` as the share of users who converted. Another wrong count includes February newcomers in the January cohort numerator.
- Overlap search: `freeze_the_success_metric_before_measuring.md` covers metric selection; `reproduce_the_evidence_a_report_claims.md` asks for a denominator. Neither checks identity deduplication, population inclusion, or a zero-denominator result for a specific rate.
- Limitations to check: A true incidence rate may count repeated events and person-time instead of distinct entities. A valid cohort rate can use a later outcome window than its entry window; immature cohorts must be flagged. The skill requires the measure to be defined before applying entity-share logic.
