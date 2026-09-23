# Candidate review: reconcile-record-flow-across-stages

Status: candidate only. No admission, licence, native-use result, or benefit claim is attached to these bytes.

- Original source basis: Written in original words for this batch from general pipeline-accounting reasoning after inspecting the 123 starter bodies and the first 24 packages. The [Agent Skills specification](https://agentskills.io/specification) informed layout only. No occupation taxonomy or third-party procedure was imported.
- Job, company archetype, and project facets: data engineer or operations analyst; a company processing scheduled feeds; an ingest-to-report migration or a recurring batch incident. The method does not depend on the employer's name.
- Model applicability: any model or harness able to follow a short, read-only reconciliation method; comparative value remains unmeasured.
- Conceptual typed input: `RunIdentity`, `StageDefinitions`, `LogicalRecordIdentities`, `StageObservations`, `TransitionRules`, `Cutoff`.
- Conceptual typed output: `StageFlowReconciliation` with per-edge counts, identity dispositions, and unexplained exceptions.
- Effect intent: read-only analysis of supplied records. No rerun, warehouse write, network call, or customer-data access is authorized by this package.
- Positive fixture: Of 100 distinct source identities, 96 pass validation and four are explicitly rejected. Of the 96, 95 are published and one remains pending at the declared cutoff. The report shows no unexplained identity and does not call publication complete.
- Known-wrong fixture: The publisher shows 96 attempts, including one retry of an already published identity and one missing identity. Reporting 96 published records is wrong; distinct identities are 95 and the missing identity stays unresolved.
- Nearest overlap: Starter `check_a_table_join_before_trusting_it.md` checks cardinality at a join. First-batch `reconcile-snapshot-changes` compares two population snapshots. This candidate follows identities through a declared sequence of processing stages, including rejects, retries, and pending outcomes.
- Limitations: Fan-out, collapse, re-entry, and partial-run rules must be supplied. A reviewer should test duplicate event identities and a stage that reports only aggregate counts.
- Customer search phrasings: "We ingested 100 rows but only 95 appeared in the published feed; where did the others go?"; "Did our retry count make this batch look complete when one record never reached the report?"
