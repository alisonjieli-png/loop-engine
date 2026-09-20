# Focused repair of the first frozen verification attempt

Date: 2026-09-19. Revision: `48cc954322691e492aad69a465ba470a112730e7`
with the current uncommitted source. No commit or provider call was made.

The original [verification attempt](verification-attempt-1.json) remains
unchanged: 5,531 of 5,535 executed checks passed, with fifteen separately
recorded untested checks. This report covers the three causes assigned to
this agent. It is not a replacement full-suite result.

## Test record producer

`core.harness_remaining_recipe_checks.self_test` returned a mapping from
names to Booleans. The current aggregate deliberately requires an explicit,
nonempty sequence of identified test records. The producer now returns all
35 existing checks as records with their original Boolean values and counts.
The collector was not changed or relaxed.

The unchanged `_module_test_records` accepts all 35 passing records. An
in-memory mutation restoring the old return shape raises its expected
`ValueError`. A separate known-wrong output extractor still fails four
positive recipe checks. A formatting correction did not convert wrong
behavior into passing evidence.

## Public request fixture

`code_nodes.data_quality_surfaces.self_test` supplied an incomplete
`SimpleNamespace` to `solve_dependencies`. The newly required
`harness_provisioning` field exposed that test-fixture drift. Both dependency
assembly checks now use one real `SolveRequest` built from typed intake.
The existing family-surface assertions and the coordinating session's
`LearningEventCollector` checks are preserved.

All ten records pass through the unchanged collector. Restoring the old
fixture produces the original missing-`harness_provisioning` `AttributeError`.
No production fallback, invented default, or public behavior was added.

## The conformance discrepancy was not test pollution

A fresh interpreter importing the frozen source snapshot
`.loop-engine-dev/continuation-20260919-jjAX0K` reproduced all nineteen
`retired_source_nomenclature` findings before running any prior tests.
They were new metering uses of `receipt` in `provisioning_server.py` and
`provisioning_server_checks.py`.

The working tree had eighteen findings because the coordinating session had
already corrected one module-description occurrence. Running the 28 preceding
`_conformance_test` checks left both the eighteen findings and the cached
policy value unchanged.

The standalone public report and the package scanner measure different things.
`conformance_report._public_retired_nomenclature` selects the configured
decision-spine terms containing `what` and its explicit public-file scope.
`_conformance_scan.scan_retired_source_nomenclature` checks all configured
terms against package source. The former correctly returned zero while the
latter correctly returned eighteen. Neither result justified a waiver.

After explicit ownership transfer, the current unlaunched metering contract
was cleaned up: `acknowledgment_ref`, `_acknowledgments`, and matching local
names replace the old first-party vocabulary. Current consumers were updated
atomically; no forwarding property or old-field alias was retained. The paid
read check now asserts the exact serialized acknowledgment field set and its
match to the meter record. The protocol checks contained no old field
references and required no edit.

The source scanner now passes all five checks, including its planted
counterexamples and live zero-tolerance scan. Source and public-language
findings are both empty before and after the preceding conformance checks.
The scanner and policy were not edited.

## Verification and retained evidence

| Check | Result |
|---|---|
| Remaining harness recipes through the collector | 35/35 |
| Data-quality surfaces through the collector | 10/10 |
| Preceding conformance checks | 28/28 |
| Source scanner | 5/5 |
| Provisioning domain | 40/40 |
| Provisioning protocol | 19/19 |
| Provisioning access runner, eight overlapping module suites | 101/101 |
| Code asset owning suite | 27/27 |
| Focused regression mutants | 3/3 detected |
| Provisioning access mutants | 14/14 detected |
| Current-only Code asset schema mutant | Detected |

The current mutation runners were retargeted to the coordinating session's
`QUALIFICATION_APPROVED` and `SPEC_RECORD_TYPE` constants and the new
acknowledgment field. Historical result files were not rewritten. A diagnostic
command initially looked for a nonexistent `provisioning_mcp.self_test`; it
was corrected to the existing `provisioning_mcp_checks.self_test`, which
passed. This command error was not a product failure.

[runtime-regression-probes.py](runtime-regression-probes.py) preserves the
reproducers and in-memory mutants. [runtime-regression-results.json](runtime-regression-results.json)
records the counts, scope, and exact changed-file hashes. The source scanner
hash remains `a1a74de8b556b911744a9d6120c814322595a688b9fe36c996100a8c1a29129b`,
the same value recorded in the first frozen attempt.

Changed source files in this repair are exactly:

- `core/harness_remaining_recipe_checks.py`
- `code_nodes/data_quality_surfaces.py`
- `core/provisioning_server.py`
- `core/provisioning_server_checks.py`

The other changes are current artifact runners and this report. Verification
used local temporary folders and the existing loopback service fixture, not
external services. Full frozen-tree verification remains with the
coordinating session. Source edits are settled for its next snapshot.
