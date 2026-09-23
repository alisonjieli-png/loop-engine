# Candidate review: reconcile-snapshot-changes

Status: candidate only. The exact `packages/data/reconcile-snapshot-changes/SKILL.md` bytes need independent review before admission.

- Original authoring and source basis: Written for this batch by a Codex research subagent from general set-reconciliation reasoning. The [Agent Skills specification](https://agentskills.io/specification) informed the file structure. No third-party prose was copied. License and originality remain review decisions.
- Applicability facets: periodic exports, inventory captures, customer lists, configuration snapshots, analytical datasets; cross-occupation.
- Search phrasings (author-supplied discovery aids, not evaluation queries): "What changed between Monday's and Tuesday's inventory exports?"; "Did these accounts disappear, or was the latest export incomplete?"
- Typed input and output concept: Inputs are `SnapshotBefore`, `SnapshotAfter`, `StableKey`, `ComparisonFields`, and `CompletenessDeclaration`. Output is `SnapshotDelta` with keyed additions, removals, changes, unchanged records, unresolved records, and reconciled counts.
- Declared effects: read-only analysis of supplied snapshots. No mutation, deletion, network access, or credential use.
- Known-good example: Complete old keys `{A, B}` and complete new keys `{B, C}` produce removed `A`, added `C`, and unchanged `B` if B's selected fields match.
- Known-wrong example: The new export was cut short after B, but the agent reports A as deleted without checking completeness.
- Overlap search: Inspected starter catalogue filenames and searched their bodies for `snapshot`. `make_a_data_pipeline_safe_to_run_again.md` mentions an atomic production snapshot, but does not classify keyed deltas or require completeness before a removal claim. `check_a_table_join_before_trusting_it.md` checks join cardinality, not two-capture reconciliation.
- Limitations to check: Identity remapping, duplicate keys, partial captures, and schema drift need explicit handling. A reviewer should test each as a hold case.
