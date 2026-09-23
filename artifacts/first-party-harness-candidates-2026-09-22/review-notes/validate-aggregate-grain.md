# Candidate review: validate-aggregate-grain

Status: candidate only. The exact `packages/data/validate-aggregate-grain/SKILL.md` bytes need independent review before admission.

- Original authoring and source basis: Written for this batch by a Codex research subagent from general measure-additivity reasoning. The [Agent Skills specification](https://agentskills.io/specification) informed the file structure. No external procedure was copied. License and originality remain review decisions.
- Applicability facets: reporting, business intelligence, inventories, cohort summaries, financial or operational measures; any grouping change.
- Search phrasings (author-supplied discovery aids, not evaluation queries): "Why does summing daily inventory show twice the stock we actually have?"; "Can we roll these customer rows up by region without double-counting?"
- Typed input and output concept: Inputs are `SourceGrain`, `TargetGrain`, `MeasureDefinition`, `SourceRows`, and optional `AllocationRule`. Output is `GrainAudit` with contributing records, rule, sample reconciliation, and unresolved overlap.
- Declared effects: read-only analysis. No warehouse query is required by the skill and no materialized table is changed.
- Known-good example: Stock is five units at the end of day one and five at the end of day two. A request for end-of-day-two stock returns five, with the chosen instant stated.
- Known-wrong example: Add the two snapshots and report ten units as stock at the end of day two.
- Overlap search: `check_a_table_join_before_trusting_it.md` checks join cardinality and orphan rows. This candidate checks whether the resulting measure is additive across the dimensions removed by aggregation, even without a join.
- Limitations to check: Weighted ratios, allocated measures, overlapping entities, and slowly changing dimension records. A reviewer should require clear source grain and measure semantics.
