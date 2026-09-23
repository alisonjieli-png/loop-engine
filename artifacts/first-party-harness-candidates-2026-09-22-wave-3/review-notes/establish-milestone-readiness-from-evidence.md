# Candidate review: establish milestone readiness from evidence

Status: candidate only. No independent approval, native-load check, customer licence, or measured benefit. Review the exact `packages/project/establish-milestone-readiness-from-evidence/SKILL.md` bytes before admission.

- Source and original basis: O*NET® 31.0 Database, occupation `13-1082.00`, task ID `21470`, supplied by the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/); [database and licence](https://www.onetcenter.org/database.html), [pinned source inventory](../../occupation-grid-research-2026-09-22/README.md). The task reference suggested the opportunity. The method and wording are original first-party drafting, not copied task prose or an endorsed O*NET method. Source ZIP SHA-256: `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`.
- Facets: project manager or delivery lead; any project with versioned dependencies and acceptance artifacts; milestone review before a handoff. Company, model, and harness labels are applicability facets, not separate methods.
- Typed concept: `MilestoneRef`, `PlanVersion`, `DependencyEdge[]`, `AcceptanceRule[]`, `ArtifactCheck[]`, `Cutoff` to `ReadinessMap`, `BlockingPredecessor[]`, `EvidenceGap[]`.
- Effect class: read-only assessment; no milestone approval or project mutation.
- Good fixture: all predecessor acceptance checks and exact deliverable versions are present at the cutoff. The map marks the target ready and cites each check.
- Known-wrong fixture: every task is closed but one required signed acceptance artifact is absent. A ready result must fail.
- Nearest overlap: starter `write_acceptance_criteria_a_reviewer_can_check` authors criteria; wave one `map-independent-acceptance-evidence` traces proof independence for general claims; wave two `gate-a-product-launch-across-teams` judges an end-to-end customer launch. This method checks one project milestone's predecessor graph and exact acceptance artifacts against supplied criteria.
- Limits: stale checks, ambiguous edges, or missing acceptance rules leave readiness unresolved. The candidate has no authority to accept a deliverable.
- Search phrasings: "Can we mark this project milestone done when the tickets are closed?"; "Which predecessor or deliverable is blocking our next handoff?"
