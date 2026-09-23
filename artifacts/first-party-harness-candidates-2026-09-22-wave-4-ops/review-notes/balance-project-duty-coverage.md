# Candidate review: balance-project-duty-coverage

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `21462`, occupation `13-1082.00` (Project Management Specialists), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Original wording; no agency endorsement or test.
- Applicability: project coordinator with a phase-specific responsibility map and supplied separation rule. No employee assessment. Model performance unmeasured.
- Conceptual typed input: `Duty`, `Qualification`, `AssignmentProposal`, `AvailabilityInterval`, `RolePolicy`.
- Conceptual typed output: `DutyCoverageMap` with gaps and role conflicts.
- Effect class: read-only planning; no reassignment or staff communication.
- Good case: A work package has a qualified preparer and separately eligible reviewer available during the needed interval.
- Known-wrong case: Fill preparer and required independent approver cells with the same person, then call the matrix complete.
- Nearest starter item: `plan_and_split_work_with_explicit_joins.md` splits parallel work; this method checks responsibility, eligibility and independent review coverage for time-scoped duties.
- Nearest earlier candidate: `audit-resource-capacity-by-interval` counts resource availability; this method checks role authority and separation in addition to capacity.
- Limits: A name on a plan does not prove acceptance of an assignment. Role policy and qualification evidence must be supplied.
- Customer search phrasings: "Who owns each project duty, and are any approvals assigned to their own preparer?"; "Show coverage gaps in our responsibility matrix."
