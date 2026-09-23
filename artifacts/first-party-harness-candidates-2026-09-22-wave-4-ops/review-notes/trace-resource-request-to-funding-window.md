# Candidate review: trace-resource-request-to-funding-window

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `21467`, occupation `13-1082.00` (Project Management Specialists), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Original wording; no agency endorsement or test.
- Applicability: project lead requesting staff, equipment or external service for one scheduled work package. Model performance unmeasured.
- Conceptual typed input: `ResourceRequest`, `ScheduleDependency`, `CapacityInterval`, `FundingWindow`, `ApprovalPath`.
- Conceptual typed output: `ResourceFeasibilityMap` with blocking interval or approval.
- Effect class: read-only planning; no booking, hire, procurement or spending.
- Good case: Available engineering time next week is shown separately from funding that begins the following month; the request remains uncommitted.
- Known-wrong case: A free engineer is labeled secured despite no approved funding in the needed interval.
- Nearest starter item: `supply_the_files_and_facts_an_assignment_needs.md` identifies missing inputs; this method intersects resource, dependency, funding and approval time windows.
- Nearest earlier candidate: `audit-resource-capacity-by-interval` checks capacity; this method adds effective funding and lead-time authority before treating a resource as secured.
- Limits: Cost and approval terms are customer-specific. The output is conditional, not a reservation.
- Customer search phrasings: "We have a free person, but does the funded project window cover them?"; "Will the procurement lead time miss the milestone?"
