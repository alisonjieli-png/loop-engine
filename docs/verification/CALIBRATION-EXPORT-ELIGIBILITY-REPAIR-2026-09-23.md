# Calibration eligibility and export reconstruction repair

September 23, 2026. Successor to the native calibration lane, following independent
QA. This patch is relative to the integrated native lane plus the import/class
adapter repair. The exact before/after hashes are in the
[evidence index](../../artifacts/calibration-export-integrity-2026-09-23/README.md).
No model or provider calls, catalogue approvals, publication or deployment occurred.

## Reproduced failures

1. The old export reader compared two editable exclusion projections. Removing a
   failed reviewer's entry from both allowed a record to retain four false approvals
   on controls and a candidate decision by that reviewer, then pass validation.
2. The live evaluator omitted installations in `result.ineligible`. An OpenAI
   reviewer skipped because the controls were OpenAI authored was unmeasured, yet
   could be asked about an Anthropic-produced candidate in the following phase.
3. The first successor checked request/package identities and review-key consistency,
   but did not reconstruct the prompt. Independent QA changed a call's prompt digest
   and recomputed its review key, then updated the matching verdict; the reader
   still accepted that record. A separate named before-failing check records this.

The first two reproductions and **11 before-repair assertion failures** are preserved.
The initial successor patch was frozen separately before repairing prompt binding.

## Live eligibility repair

The evaluator covers every installation in availability or ineligible state, plus
those represented by calls or verdicts. An installation without a valid verdict on
**every control** is incomplete. Approving any known-wrong control is a calibration
failure. This includes producer-family-skipped, unavailable, disabled and zero-call
installations. A calibration exclusion takes precedence in the following phase,
while the original disabled metadata remains recorded.

Producer-family exclusion is preserved: a reviewer never reviews a control it
produced. The fix does not invent calibration results for that reviewer. It prevents
an unmeasured reviewer from becoming eligible for unrelated candidate work.

Expected-approve control refusals remain separately recorded and do not approve
anything. Invalid answers and unknown usage remain distinct in the existing ledger.
Missing a benign control verdict also makes the run incomplete.

## Export repair and version boundaries

| Component | Active contract and change |
|---|---|
| Panel artifact | `starter_catalogue_panel_review/v3`: includes the existing typed `PanelConfiguration`, so every installation, family, model and policy can be checked. Version-two exports remain historical and are refused. |
| Calibration result | `candidate_review_calibration_result/v2`: includes the complete existing typed verdict records, call evidence, installation outcomes and exclusion projections. Unversioned/older calibration results are refused. |
| Worker ledger | Call, verdict, dispatch and run versions stay at v2; no reinterpretation or migration. |
| Hosted approval source | `starter_catalogue_independent_review/v2` is unchanged. The live historical approval source is not revoked by this worker-format change. |

The strict reader loads trusted default control sets from deployment-owned resources.
An alternate set requires separate, explicit `CalibrationInputs` supplied by the host,
including exact requests and reviewer instructions. A reviewer or persisted record
cannot supply its own authoritative labels. Unknown set digests and changed labels,
control populations, package digests, criteria or instruction bindings are refused.

Each calibration call is checked against the exact trusted request. The configured
reviewer installation and instructions reconstruct the actual prompt, and its digest
must match. The review key must also bind that installation, request and prompt.
Full typed verdicts must match their calls and pass the existing verdict parser
against the applicable control criteria. Missing, duplicate, unknown, invalid or
contradictory call/verdict records cannot be treated as valid answers. Producer-family
and disabled installations cannot provide control evidence.

The reader then recomputes every installation's result and exclusions using the same
pure eligibility rule as live evaluation. Both saved exclusion projections must
agree with that reconstruction. Candidate reviewers must have complete qualification
from the same installation, model and engine version. Deleting summary/list entries
cannot change these facts. These checks validate consistency of recorded evidence;
they are not a cryptographic authenticity claim about an operator who rewrites all
source evidence.

## Verification

- The coherent new-format reproduction retains four false approvals and the failed
  reviewer's candidate decision. Its original record is refused; deleting both
  exclusion projections is refused with `calibration_inconsistent`.
- The independently supplied producer-family reproduction now records OpenAI as
  `calibration_incomplete`, with **zero control calls and zero candidate calls**.
  Three other measured families can still complete the fixture candidate.
- A legitimate complete native calibration/candidate record roundtrips successfully.
- Changed prompt bytes cannot be hidden by recomputing the review key.
- **281 component tests** pass, with one optional duplicate-index dependency skip.
  The requested combined generation/factory/calibration/provider suite passes
  **79 tests**. Six in-memory guard mutations are detected. New modules and the
  mutation runner pass Ruff; changed existing modules introduce no diagnostics.

All executions use fixture engines. Counts of fixture decisions are not model calls
or independent approvals. Intermediate failures and successive results remain in the
evidence folder. Independent reviewer replay is recorded separately by that reviewer.

## Native control qualification gap

Independent sandbox replay supports the four planted defects and the benign scheduling
algorithm on its tested cases. The benign package does not yet carry applicable native
harness loading evidence. Its expected-approve label is therefore provisional under
the unchanged `native_loading` admission criterion. The `false_refusals` field records
label disagreements here, not an empirical false-refusal estimate. The result's limits
text and the control README state that distinction.

**Hold the real native calibration pilot** until applicable loading evidence or a
separately approved control scope exists. Do not weaken admission, add a self-certified
loading claim, or infer qualification from static package format checks. The small
fixed set supplies no general review error-rate estimate.
