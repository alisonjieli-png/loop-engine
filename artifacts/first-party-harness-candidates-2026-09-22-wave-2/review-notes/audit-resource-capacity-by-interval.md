# Candidate review: audit-resource-capacity-by-interval

Status: candidate only. No admission, licence, native-use result, or benefit claim is attached to these bytes.

- Original source basis: Written in original words for this batch from general scheduling and interval-accounting reasoning after inspecting the 123 starter bodies and first 24 packages. The [Agent Skills specification](https://agentskills.io/specification) informed layout only. No copied scheduling policy or external taxonomy.
- Job, company archetype, and project facets: operations planner or project coordinator; a service team, workshop, or lab; staffing a proposed schedule or checking a delivery plan.
- Model applicability: general text-capable harnesses; no model-specific qualification.
- Conceptual typed input: `Jobs`, `ResourceCalendars`, `Qualifications`, `CapacityUnits`, `SchedulingRules`, and optional `ProposedAssignment` or separately authorized `FeasibilityResult` for a feasible verdict.
- Conceptual typed output: `IntervalCapacityAudit` with eligible capacity, demand, overloads, assignment conflicts, unknown constraints, and a verdict of infeasible, no interval overload found, or assignment-verified feasible.
- Effect intent: read-only schedule analysis. It does not authorize moving assignments or booking resources.
- Positive fixture: One qualified technician is available from 09:00 to 17:00. Jobs requiring that technician overlap from 09:30 to 10:00, each needing full capacity. The audit flags a one-technician deficit in that interval despite eight available daily hours.
- Known-wrong fixture: A planner adds two one-hour jobs and observes that two hours fit within an eight-hour shift, then declares a schedule feasible even though both require the only qualified technician at the same time.
- Known-wrong fixture for a false feasible verdict: Two jobs each need two continuous hours within 09:00 to 12:00. Two qualified workers are available, so four job-hours fit within six worker-hours and no simple capacity total is overloaded. The supplied precedence rule requires the second job to start after the first finishes. A concurrent assignment violates precedence; a sequential assignment needs four elapsed hours and misses the window. The result must not call this feasible without a valid assignment.
- Nearest overlap: Starter `plan_and_split_work_with_explicit_joins.md` describes task dependencies. First-batch `define-time-zone-reporting-window` resolves reporting boundaries. This candidate tests resource eligibility and concurrency for each scheduled interval.
- Limitations: An interval overload can prove infeasibility, while no overload does not prove feasibility for indivisible, precedence-constrained, or multiply qualified work. The skill is not an optimizer and does not propose a new schedule. A reviewer should test breaks, a job spanning a time-zone transition, and non-interchangeable qualifications.
- Customer search phrasings: "Do these jobs fit the actual shifts, or are we double-booking the only qualified person?"; "We have enough weekly hours; why does Tuesday's plan still fail?"
