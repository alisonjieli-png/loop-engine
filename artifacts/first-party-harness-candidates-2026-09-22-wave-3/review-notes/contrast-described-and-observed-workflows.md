# Candidate review: contrast described and observed workflows

Status: candidate only. No independent approval, native-load check, customer licence, or measured benefit. Review the exact `packages/project/contrast-described-and-observed-workflows/SKILL.md` bytes before admission.

- Source and original basis: O*NET® 31.0 Database, occupations `13-1111.00` / task ID `7281` and `15-1211.00` / task ID `3471`, supplied by the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/); [database and licence](https://www.onetcenter.org/database.html), [pinned source inventory](../../occupation-grid-research-2026-09-22/README.md). Two occupations suggest one reusable method. The comparison procedure and wording are original first-party drafting, not copied task prose or an endorsed O*NET method. Source ZIP SHA-256: `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`.
- Facets: management or systems analyst; consented internal operations study; current approved workflow version and observation period. Occupation labels do not create two packages.
- Typed concept: `ProcessVersion`, `AllowedRoute[]`, `ObservationScope`, `CaseEvent[]` to `ObservedRouteMap`, `Deviation[]`, `UnknownCase[]`.
- Effect class: read-only analysis of supplied authorized records; no monitoring, policy edit, or personnel judgment.
- Good fixture: eight of ten consented cases include a manual approval omitted from the approved route; two cases lack an end event. The output names the extra path and keeps the two unknowns visible.
- Known-wrong fixture: the official happy path is presented as actual practice despite repeated observed manual approvals. Equivalence must fail.
- Nearest overlap: starter `build_an_incident_timeline_from_evidence` orders one incident's observations; wave one `map-observed-customer-journey-friction` studies customer interface attempts; wave two `reconcile-record-flow-across-stages` follows record identities. This method aligns multiple internal case paths with an approved operations route and classifies exception paths.
- Limits: supplied observations may be unrepresentative; do not infer a person's motive or compliance from an incomplete path.
- Search phrasings: "Does the team actually follow the process map?"; "Find the manual steps people use that are missing from our documented workflow."
