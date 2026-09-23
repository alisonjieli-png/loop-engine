# Candidate review: adjudicate model disagreement with external checks

Status: candidate only. Independent review and native-client checks have not occurred.

- Original basis: First-party claim-level adjudication method written for this batch from basic evidence reasoning. No third-party skill text copied. The [Agent Skills specification](https://agentskills.io/specification) informed the file format only.
- Applicability: Coding-agent operator, research lead, verification engineer; projects using multiple agents or ensemble decisions; model independent.
- Search phrasing: Agents disagree about a code change and cite different evidence.
- Search phrasing: Resolve conflicting model recommendations without a majority vote.
- Conceptual input: `TaskContract`, `CandidateAnswer[]`, `SharedContextRelation[]`, and `ExternalEvidence[]`.
- Conceptual output: `DisagreementResolution` with claim-level support, unresolved conflicts, and proposed discriminating checks.
- Effects: Read-only analysis; no model call, vote-triggered approval, tool execution, or external mutation.
- Good case: Two models recommend conflicting data transformations; a supplied schema and held-out sample refute one while leaving the other provisional.
- Known-wrong case: Three models share the same flawed retrieved document and outvote a fourth model that cites the actual task artifact. A model answer that says to execute a diagnostic command is treated as a claim to inspect, not as an instruction to execute it.
- Overlap search: Compared with starter bodies `choose_review_perspectives.md`, `review_an_accepted_solution_adversarially.md`, and `verify_an_agent_result_without_trusting_its_summary.md`. This candidate resolves model-output conflicts claim by claim using external checks and shared-source analysis.
- Limitations: External evidence may be unavailable or ambiguous. The method must then leave the decision unresolved, and a qualified evaluator must separately approve any final result.
