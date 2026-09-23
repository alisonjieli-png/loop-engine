# Candidate review: audit-measurement-units

Status: candidate only. The exact `packages/data/audit-measurement-units/SKILL.md` bytes need independent review before admission.

- Original authoring and source basis: Written for this batch by a Codex research subagent from general dimensional-analysis reasoning. The [Agent Skills specification](https://agentskills.io/specification) informed the file structure. No third-party procedure was copied. License and originality remain review decisions.
- Applicability facets: data analysis, data engineering, laboratory exports, logistics, reporting; any occupation using numeric measurements. No company-specific rule is assumed.
- Search phrasings (author-supplied discovery aids, not evaluation queries): "These exports mix pounds and kilograms; can you check the total?"; "Why is this lab report off by a factor of a thousand after we combined readings?"
- Typed input and output concept: Inputs are `MeasurementField[]`, `TargetUnit`, `ConversionReference[]`, and `Calculation`. Output is `UnitAudit` with converted samples, compatibility status, and unresolved rows.
- Declared effects: read-only analysis of supplied records and definitions. No source writes, network calls, credentials, or external effects are requested by the skill.
- Known-good example: A source has 1.5 kilograms and 500 grams. With an approved grams-to-kilograms rule, both become kilograms and sum to 2 kilograms.
- Known-wrong example: Add 1.5 and 500 directly, label the result kilograms, and report 501.5 kilograms.
- Overlap search: Inspected all filenames in `examples/29_intelligence_service/starter-catalogue/bodies/` and searched their bodies for `unit conversion`. `write_a_data_contract_for_a_table_or_feed.md` asks producers to state units; `review_a_change_for_correctness.md` asks whether units are stated. Neither gives a field-by-field conversion audit and stop rule.
- Limitations to check: Conversion references may change over time. Affine scales cannot use only a multiplier. A reviewer should test missing units and incompatible dimensions.
