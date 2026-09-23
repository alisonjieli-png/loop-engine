# Candidate review: qualify an invited pilot cohort

Status: candidate only. No independent approval, native-load test, or measured benefit.

- Original basis: first-party method for a bounded pilot selection decision. No third-party cohort rubric or occupation text was copied.
- Facets: product manager, founder, or customer success lead; early product or business-to-business service; invited pilot stage; company-specific eligibility and capacity are inputs, not public rules.
- Search phrasings: "Which of these interested accounts should join the small beta first?"; "Help choose pilot users without promising features we have not shipped."
- Typed input/output concept: `PilotObjective`, `CandidateRecord[]`, `EligibilityRule[]`, `CurrentCapability`, and `SupportCapacity` to `ProposedCohort`, `Hold[]`, `Exclusion[]`, and `CoverageGap[]`.
- Effects: read-only recommendation. No invitations, entitlements, accounts, or customer contact.
- Positive fixture: four interested teams, two meet the documented eligibility rules and current task path, one requires an unbuilt feature, one has unknown data-use permission; support capacity is two. Propose the two eligible teams and hold the others with reasons.
- Known-wrong fixture: the most enthusiastic team cannot use the current client and needs a promised future connector. Selecting it because its logo is attractive must fail the current-capability gate. Treating unknown consent as eligible must fail too.
- Nearest overlap and distinction: batch-one `design-a-bounded-product-experiment` defines assignment, exposure, metrics, and guardrails for a treatment comparison. This method selects suitable invited participants under support and readiness limits, without assignment to experiment arms.
- Limits: a small pilot is not a representative market sample. The skill cannot infer support capacity, legal permission, or product readiness; independent review should challenge whether hard rules are truly supplied.
