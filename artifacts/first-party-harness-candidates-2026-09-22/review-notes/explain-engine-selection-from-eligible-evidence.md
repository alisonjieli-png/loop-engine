# Candidate review: explain engine selection from eligible evidence

Status: candidate only. Independent review and native-client checks have not occurred.

- Original basis: First-party staged decision method written for this batch from typed component-selection principles. No external skill body copied. The [Agent Skills specification](https://agentskills.io/specification) informed the file format only.
- Applicability: Agent-platform engineer, runtime operator, evaluator; projects with interchangeable search, execution, or provider adapters; model independent.
- Search phrasing: Why did the runtime choose this adapter despite a spending limit?
- Search phrasing: Trace which registered engine remained eligible after fallback.
- Conceptual input: `TaskContract`, `EngineRegistration[]`, `PreferenceOrder`, and `EvidenceRecord[]`.
- Conceptual output: `EngineSelectionTrace` with eligibility exclusions, ranking basis, selection, and permitted fallback.
- Effects: Read-only audit; no engine invocation, configuration change, or spending.
- Good case: A fast adapter is excluded because it cannot preserve a required output field, so the next eligible adapter is selected with the reason recorded.
- Known-wrong case: A preferred engine with no sandbox support is chosen for untrusted code because its latency score is best. A second wrong case has two eligible model engines and a hard remaining allowance of 2 dollars: one has unknown cost and wins on latency, so selecting it silently treats unknown spending as within the allowance. It must remain unresolved unless a conservative bound fits.
- Overlap search: Compared with starter bodies `decide_whether_a_step_needs_a_model.md`, `choose_a_smaller_model_for_a_bounded_decision.md`, and `classify_a_failure_before_deciding_to_retry.md`. This candidate traces a full registered component-engine selection and rechecks fallback eligibility.
- Limitations: The method relies on truthful registration and relevant evidence. It cannot qualify an engine or prove the selected implementation works.
