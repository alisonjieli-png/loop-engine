# Candidate review: verify resolution against original symptom

Status: candidate only. No independent approval, native-load check, customer licence, or measured benefit. Review the exact `packages/project/verify-resolution-against-original-symptom/SKILL.md` bytes before admission.

- Source and original basis: O*NET® 31.0 Database, occupation `43-4051.00`, task ID `2580`, supplied by the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/); [database and licence](https://www.onetcenter.org/database.html), [pinned source inventory](../../occupation-grid-research-2026-09-22/README.md). The task reference suggested the opportunity. The symptom-to-observation method and wording are original first-party drafting, not copied task prose or an endorsed O*NET method. Source ZIP SHA-256: `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`.
- Facets: support follow-up or service owner; consented account or release scope; after-change review. Customer account facts remain within authorized access.
- Typed concept: `CaseSymptom`, `AcceptanceRule`, `BeforeObservation`, `RemediationRef`, `AfterObservation[]` to `ResolutionFinding`, `ComparisonGap[]`, `NextCheck`.
- Effect class: read-only assessment of supplied observations; no live reproduction, ticket closure, or customer message.
- Good fixture: the exact prior failing operation succeeds on the affected account and release after the fix, with a matching observation and no contrary result in scope. Report resolved only on the tested path.
- Known-wrong fixture: a patch is deployed, but the customer's original path still returns an error. A closure recommendation must fail.
- Nearest overlap: starter `verify_the_requested_output` checks an artifact; wave one `triage-support-requests-against-approved-policy` proposes an initial support disposition under supplied policy; wave two `prepare-a-support-escalation-packet` assembles investigation input. This method tests the original support symptom after a proposed remediation.
- Limits: a successful internal path does not prove every affected account or environment; access to customer data and any new test require separate authority.
- Search phrasings: "Can we close this ticket after the patch shipped?"; "Check whether the customer's original failure is actually fixed."
