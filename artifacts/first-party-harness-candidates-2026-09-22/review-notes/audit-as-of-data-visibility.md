# Candidate review: audit-as-of-data-visibility

Status: candidate only. The exact `packages/data/audit-as-of-data-visibility/SKILL.md` bytes need independent review before admission.

- Original authoring and source basis: Written for this batch by a Codex research subagent from general effective-time and recorded-time reasoning. The [Agent Skills specification](https://agentskills.io/specification) informed the file structure. No third-party wording was copied. License and originality remain review decisions.
- Applicability facets: corrected reports, late data, audits, historical dashboards, versioned records; any occupation comparing historical and revised views.
- Search phrasings (author-supplied discovery aids, not evaluation queries): "What did our dashboard show at month end before the late correction arrived?"; "Why did last quarter's numbers change after we closed the report?"
- Typed input and output concept: Inputs are `BusinessPeriod`, historical `KnowledgeCutoff`, revised `KnowledgeCutoff` or immutable snapshot identity, `VersionedRecord[]`, `ReportingVisibilityRule`, and `SupersessionRule`. Output is `AsOfComparison` with known-then result, revised-as-of result, and record-level differences.
- Declared effects: read-only analysis of supplied history. No update to source records or public report.
- Known-good example: A January value of 100 was visible in the reporting system on January 31. A correction to 80 carries a January 30 source timestamp but reached that system on February 2. The January 31 known-then view is 100; a revised view fixed at February 3 is 80.
- Known-wrong example: Show 80 as what the January 31 analyst knew by filtering only on the correction's January 30 source timestamp.
- Overlap search: `write_a_data_contract_for_a_table_or_feed.md` mentions how far back data can change. It does not reconstruct a historical knowledge view or distinguish it from a later corrected business period.
- Limitations to check: A source timestamp is not proof of reporting-system availability. Both views need a frozen knowledge cutoff or immutable snapshot for reproducibility. Missing visibility evidence or correction links can prevent a known-then claim. The reviewer should test delayed receipt, contradictory versions, and incomplete history.
