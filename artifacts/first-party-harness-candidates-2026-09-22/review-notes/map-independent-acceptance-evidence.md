# Candidate review: map independent acceptance evidence

Status: candidate only. Independent review and native-client checks have not occurred.

- Original basis: First-party procedure based on tracing evidence dependencies, drafted without copied third-party instructions. The [Agent Skills specification](https://agentskills.io/specification) informed the file format only.
- Applicability: Quality engineer, coding-agent operator, auditor; projects with agent-generated code, reports, or benchmark claims; model independent.
- Search phrasing: Two green reports seem to share the same skipped fixture.
- Search phrasing: Find an independent check for an agent-produced artifact.
- Conceptual input: `AcceptanceCondition[]`, `ClaimedEvidence[]`, and `ProvenanceRelation[]`.
- Conceptual output: `EvidenceIndependenceMap` and proposed verification actions.
- Effects: Read-only analysis of supplied records. The skill neither runs tests nor grants an approval.
- Good case: Two green dashboards trace to one skipped test suite; the map exposes their common origin and asks for an independent execution record.
- Known-wrong case: A producer creates the output, writes its own grader, and quotes the grader's green result as independent acceptance.
- Overlap search: Compared with starter bodies `verify_an_agent_result_without_trusting_its_summary.md`, `choose_review_perspectives.md`, and `reproduce_the_evidence_a_report_claims.md`. This candidate explicitly analyzes dependency among evidence sources and proposes a condition-by-condition independence map.
- Limitations: A provenance map can identify circular evidence but cannot itself establish behavioral correctness. The final verdict requires an independent authorized evaluator.
