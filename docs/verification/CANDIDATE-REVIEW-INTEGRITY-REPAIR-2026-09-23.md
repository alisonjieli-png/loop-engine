# Candidate review integrity repair, September 23, 2026

Status: local repair on detached worktree
`/home/username/.le-codex-build/review-integrity`, based on
`9c57c9a4c813578bffa504108ef9d785b308bb86`. No model/provider calls, catalogue
approval changes, publication, commit or deployment were made by this task.
The integrating session owns the repository checks, merge, roadmap and release.

## Findings and repairs

The [library integration handoff](HANDOFF-LIBRARY-LS1-LS2-2026-09-23.md)
recorded all three main defects. Existing typed requests, pre-check results,
reviewer attempts and usage records were sufficient for a bounded repair.

| Finding | Repair | Known-wrong evidence |
| --- | --- | --- |
| Candidate body digest and size were recomputed without comparing the selected reference | The fixed pre-check entry validates the selected reference's digest and exact integer byte size before any replaceable engine or reviewer. A failure is a typed format refusal, with no call reservation. | Same-length body mutation, wrong/missing digest, wrong size, `true`, fractional/string sizes and a panel fixture that otherwise approves |
| Codex JSONL responses were attributed to the requested model without reported identity | The reader preserves unknown identity and emits `model_identity_mismatch`; its availability probe refuses the protocol for review before a doomed call can be spent. CLI version remains observed, model version remains unknown. | A completed answer with real-shaped usage and no answering-model identity; removed guard restores the false attribution |
| Claude no-model errors overwrote missing usage with zero | Preserve the usage fields actually present, including unknown and partial counts. Explicit zeros remain zeros. | Missing usage, partial output count, and explicit complete zero usage |

The identity repair also requires Claude's reported model set to be exactly
the requested model. A result containing that model and an additional model
cannot establish a single configured reviewer and is refused. Genuine matched
Claude identity and existing matched gateway identity continue to pass.

## Why the body check belongs at the fixed edge

Adding the check only to the catalogue file reader would miss directly
constructed requests and calibration requests. Adding it only to one selected
format engine would let another engine omit the invariant. The existing
`run_prechecks` edge now validates identity first and emits the existing
`candidate_precheck_result/v1` shape. No runtime type, engine setting,
record field or approval source was added.

The request's original bytes and declaration remain unchanged. The check
does not repair a bad digest automatically. Existing calibration generation
already explicitly binds each planted defect's new bytes. Test fixtures for
semantic defects now do the same, preserving the earlier independent checks
for licensing, safety, format, effects and duplication. Deliberately mismatched
fixtures remain mismatched in the new integrity tests.

## Requested model versus reported model

`ReviewerAttempt.reported_model` is an existing field. The Codex reader can no
longer fill it from `ReviewerInstallation.model`. No unqualified new event
field, stderr interpretation or alias was invented to obtain model identity.
Codex remains configured but unavailable as a panel reviewer until a protocol
that reports the answering model is qualified. Other eligible families remain
available under their current configuration and authority.

The current ledger's `model` field names the requested installation. It does
not serialize `ReviewerAttempt.reported_model`; model-version information is
from the availability probe. The component guide now states this limitation.
A broader contract change needs a new record version and belongs to the
separate review-record work. Old ledger and pilot bytes were not changed or
retroactively qualified. Their identity evidence needs independent
adjudication before any approval carry.

No-model physical-call reporting and token usage are separate facts. A known
zero physical-call count cannot replace an absent token count. The existing
budget mechanism continues charging a reservation when usage is incomplete.

## Verification

The [evidence directory](../../artifacts/candidate-review-integrity-2026-09-23/README.md)
keeps failed checks and successors. The final owning-component run completed
235 tests with one existing optional `datasketch` skip and no failures. Six
removed-guard controls were detected, covering body digest, byte size, Codex
reported identity, Codex availability, Claude unknown usage and mixed Claude
identity. Both newly authored Python files pass Ruff; existing changed files
introduce zero new Ruff diagnostics. Component documentation passes Markdown
lint. All model behavior in these tests is a fixture or parsed synthetic
output. These are contract checks, not provider-integration or model-quality
claims.

No service runtime, starter body, catalogue approval, review policy, provider
route, credential or historical review file changed. Before integration, run
the full repository checks on the composed tree and retain these exact source
and test changes alongside the recorded negative cases.
