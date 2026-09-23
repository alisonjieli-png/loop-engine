# Candidate review: screen a study for a product decision

Status: candidate only. No independent approval, native-load test, or task
evaluation has occurred.

- Original source basis: first-party decision-transfer procedure. It does
  not copy any paper, published summary, or benchmark text.
- Job, company, and project facets: research engineer, product manager, or
  technical founder; target user and environment are supplied by the company;
  product research or evidence review stage.
- Search phrasings: "Does this coding-agent study justify using the method
  for our data team?"; "Which results in this paper apply to the product
  choice we are considering, and which do not?"
- Typed input/output concept: `StudyVersion`, `DecisionClaim`,
  `TargetSetting`, and `LocalBaseline?` to `EvidenceScreen`,
  `TransferMismatch[]`, `Unknown[]`, and `LocalTestProposal`.
- Effects: read a supplied study and draft analysis. No experiment launch,
  paper download beyond granted access, public claim, or product change.
- Good fixture: a study measures agent performance on repository coding
  tasks; the proposed decision concerns data cleanup for noncoders. Report
  the result as potentially informative but not direct proof of the target.
- Known-wrong fixture: use a reported coding-task improvement to claim the
  product improves every data-cleaning task by the same percentage.
- Overlap search: starter `reproduce_the_evidence_a_report_claims` checks
  reproducibility, while `report_observed_derived_assumed_and_unknown`
  governs claims generally. This candidate tests transfer from one study
  population and intervention to one proposed product decision.
- Limits: an abstract or restricted excerpt can support only a narrow
  screen. The skill does not independently reproduce the study.
