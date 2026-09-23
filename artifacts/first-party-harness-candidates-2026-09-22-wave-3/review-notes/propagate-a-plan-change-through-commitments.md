# Candidate review: propagate a plan change through commitments

Status: candidate only. No independent approval, native-load check, customer licence, or measured benefit. Review the exact `packages/project/propagate-a-plan-change-through-commitments/SKILL.md` bytes before admission.

- Source and original basis: O*NET® 31.0 Database, occupation `13-1082.00`, task ID `21476`, supplied by the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/); [database and licence](https://www.onetcenter.org/database.html), [pinned source inventory](../../occupation-grid-research-2026-09-22/README.md). The task reference suggested the opportunity. The impact-propagation method and wording are original first-party drafting, not copied task prose or an endorsed O*NET method. Source ZIP SHA-256: `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`.
- Facets: project manager, technical lead, or delivery owner; schedule, scope, or capacity proposal; versioned baseline and cross-team handoff. Named company rules must be supplied privately.
- Typed concept: `BaselinePlan`, `ProposedDelta`, `DependencyEdge[]`, `Commitment[]`, `ConstraintRule[]` to `ImpactMap`, `DecisionPoint[]`, `UnresolvedEdge[]`.
- Effect class: read-only proposal analysis; no plan edit, booking, approval, or notice.
- Good fixture: a test date moves seven days; the linked access reservation and customer handoff are identified, with owners and conditional impact.
- Known-wrong fixture: the same date moves while both linked commitments retain their old dates, yet the report says no downstream impact. The zero-impact conclusion must fail.
- Nearest overlap: starter `plan_and_split_work_with_explicit_joins` records dependencies before dispatch; wave one `build-a-project-decision-provenance-map` reconstructs what was decided; wave two `carry-a-sales-promise-into-delivery` tracks accepted customer commitments into a handoff. This method propagates a proposed change through existing plan links before it is approved.
- Limits: an incomplete dependency graph cannot establish that no impact exists. A proposed effect is not authority to revise a commitment.
- Search phrasings: "If we push this date, what else needs to move?"; "Trace the ripple effects before we approve this project-plan change."
