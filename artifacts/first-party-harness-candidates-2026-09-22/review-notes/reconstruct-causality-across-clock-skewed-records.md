# Candidate review: reconstruct causality across clock-skewed records

Status: candidate only. Independent review and native-client checks have not occurred.

- Original basis: Written for this batch from the general distinction between partial order and wall-clock order. No external instructions were copied. The [Agent Skills specification](https://agentskills.io/specification) informed the file format only.
- Applicability: Site reliability engineer, incident responder, distributed-system developer; outage analysis in a multi-service project; model independent.
- Search phrasing: A background job appears to finish before the request that created it.
- Search phrasing: Trace which service action preceded a delayed queue event.
- Conceptual input: `IncidentRecord[]` with timestamp semantics, `ClockOffsetBound[]`, `LoggingDelayBound[]`, and one `TargetEvent`.
- Conceptual output: `CausalOrdering` with source references, confirmed and unresolved edges, competing explanations, and evidence gaps.
- Effects: Read-only analysis of already authorized records; no service query, shell command, correction, or incident mutation is instructed.
- Good case: A queue receive has an explicit message identifier linking it to a send even though the receiving host clock is five seconds behind.
- Known-wrong case: Sorting two hosts' raw timestamps makes a downstream failure appear to precede its triggering request, then assigns a cause from the false order. In an adversarial fixture, event A occurs before event B but A's log line is buffered and written after B's; non-overlapping log-write times cannot establish the event order without a delay bound.
- Overlap search: Compared with starter bodies `build_an_incident_timeline_from_evidence.md` and `carry_one_correlation_identifier_across_services.md`. This candidate addresses uncertain clock bounds and partial order of existing records; it does not prescribe how to collect an incident timeline or propagate identifiers.
- Limitations: Partial order may be sparse; a causal edge between events does not by itself identify the defect. A domain reviewer must assess the proposed cause and the quality of clock, timestamp, and logging-delay bounds.
