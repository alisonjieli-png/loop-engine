# Candidate review: compare model and context pairs on frozen cases

Status: candidate only. Independent review and native-client checks have not occurred.

- Original basis: First-party paired-factor experiment design written for this batch from general evaluation principles. No third-party skill text was copied. The [Agent Skills specification](https://agentskills.io/specification) informed the file format only.
- Applicability: Model-evaluation engineer, harness maintainer, small-model user; model-conditioned skill projects; applicable to any route with recorded model version and usage.
- Search phrasing: A shorter prompt helps one model but hurts another.
- Search phrasing: Plan an affordable crossed trial of model and skill variants.
- Conceptual input: `FrozenCaseSet`, `ModelRoute[]`, `ContextPackage[]`, `Evaluator`, `AuthorityPolicy`, and `CallCeiling`.
- Conceptual output: `PairedTrialDesign` with an affordable grid, fixed controls, interaction analysis, and decision rule, or a hold if the minimum grid exceeds the ceiling.
- Effects: Read-only experiment design. It does not run models or spend tokens.
- Good case: A concise context helps a small model but harms a larger one; the paired grid exposes the interaction before routing all users to the concise form.
- Known-wrong case: Comparing small model plus short context against large model plus long context and attributing the whole difference to model size.
- Overlap search: Compared with starter bodies `compare_a_smaller_model_against_the_larger_one.md`, `assemble_the_context_for_one_step.md`, and `freeze_the_success_metric_before_measuring.md`. This candidate isolates the joint model-context interaction with a paired grid; the first starter deliberately holds context fixed for a model-only comparison.
- Limitations: A planned grid does not establish a performance gain. Real, authorized model calls and an independent evaluator are required, with actual costs reported only when present.
