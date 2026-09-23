# Candidate review: diagnose-process-constraint-from-flow

Status: candidate only. These exact bytes have no independent approval, native-use result, or measured customer benefit.

- Source and rights: Original candidate wording prompted by task ID `7285`, occupation `13-1111.00` (Management Analysts), in the [O*NET® 31.0 Database](https://www.onetcenter.org/database.html) by the U.S. Department of Labor, Employment and Training Administration. The applicable database file is offered under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). The pinned local ZIP has SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. The method and examples are newly written; no O*NET task prose is copied into the skill. O*NET and the Department of Labor have not endorsed or tested it.
- Job, company, and project facets: operations analyst; service desk, production cell, or fulfillment flow; baseline throughput diagnosis before a process change.
- Model applicability: general text-capable harnesses; performance with any model is unmeasured.
- Conceptual typed input: `StageMap`, `FlowWindow`, `Arrivals`, `Completions`, `QueueObservations`, optional `CapacityEvidence`.
- Conceptual typed output: `ConstraintDiagnosis` with reconciled stage balances, candidate constraint, competing explanations, and next observation.
- Effect class: read-only analysis. No staffing, work routing, queue, or schedule mutation.
- Good fixture: In each comparable hour, stage A receives and completes ten cases, while stage B receives ten and completes eight. The queue before B rises by two per hour and the balance reconciles. B is a candidate constraint, subject to routing and downtime checks.
- Known-wrong fixture: Stage A has the longest average handling time but no accumulating queue; an analyst calls it the bottleneck solely from that duration. Reject the diagnosis and inspect the observed queue and throughput path.
- Nearest starter item: `read_a_profile_and_find_the_dominant_cost.md` finds a costly code path from a profile; this candidate diagnoses work flow from arrivals, departures, and queue balances.
- Nearest wave 1 item: `rebuild-state-from-ordered-events` reconstructs one entity's state; this method reconciles aggregate stage flow and tests a constraint hypothesis.
- Nearest wave 2 item: `audit-resource-capacity-by-interval` checks whether a proposed assignment fits capacity; this method diagnoses an observed process before changing the schedule.
- Limits: Queues may move because of batching, priority, downstream blocking, or a changed case mix. Independent review should test rework loops, censored completions, and mismatched stage boundaries.
- Customer search phrasings: "Where is work actually piling up in this intake process?"; "The team blames the slowest step, but which station limits completed cases?"
