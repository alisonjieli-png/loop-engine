# Native review calibration: independent QA

September 23, 2026. Reviewer: Codex `interop_standards`, separate from the
calibration implementation/label author. This review grants no intelligence
admission. No provider calls, real candidate approvals or publication occurred.

**Initial result: two enforcement blockers require repair before relying on this
calibration in a real review campaign.** Twelve focused author tests pass. An
independent replay supports the five intended algorithm/contract/effect/source
observations, with the benign-label qualification caveat below.

## Reproduced blockers

### 1. Persisted exclusion can be removed while failure evidence remains

The current record reader compares `calibration.excluded` with calibration
reasons in `ineligible_reviewers`. It does not derive that exclusion from the
retained installation decisions, false approvals or status.

The fixture reviewer `a` approved all four known-wrong controls. The original
record, which also contains a candidate decision from `a`, correctly refuses
with `excluded_calibration_reviewer_decided`. Removing **only** the two exclusion
list entries makes the record reader accept. `installations.a.status` still says
`failed_calibration`; all four false approvals and the candidate decision remain.

[Reproducer](../../artifacts/native-review-calibration-independent-qa-2026-09-23/check_persisted_exclusion.py),
[observed result](../../artifacts/native-review-calibration-independent-qa-2026-09-23/persisted-exclusion-counterexample-1.json).

Required successor: reconstruct/validate installation decisions and calibration
status from bound control evidence, then require exact exclusion consistency.
Changing a derived list must not erase a failed result. Validate package subject,
installation/model identity, request, label set, accepted verdict and applicable
criteria/instructions bindings; do not substitute an editable status field for
those facts. This is a record consistency counterexample using explicit fixture
records, not a claim that a real malicious record was admitted.

### 2. An unmeasured control author can enter the candidate phase

All five controls declare an OpenAI-family producer. The panel correctly refuses
to let an OpenAI reviewer judge them. `calibration.evaluate` then omits that
reviewer, because it is in the run's ineligible map. The resulting `excluded`
map is empty for it.

In the following phase an Anthropic-produced fixture is eligible for that OpenAI
reviewer. It makes one review call and contributes to a three-family approval,
having made zero calibration calls. The controls' producer-family protection
must remain; the missing calibration is the gap.

[Reproducer](../../artifacts/native-review-calibration-independent-qa-2026-09-23/check_uncalibrated_producer_family.py),
[observed result](../../artifacts/native-review-calibration-independent-qa-2026-09-23/uncalibrated-producer-family-2.json).

Required successor: any installation eligible for the candidate phase needs a
completed qualifying calibration for the exact applicable configuration, or an
explicit incomplete/excluded state. Independently authored alternate controls
can later provide coverage for otherwise excluded families. Do not qualify an
installation merely because calibration never asked it anything.

## Exact-package and label findings

The native reader verifies canonical package documents, complete file inventory,
per-file digest/size and pinned cited source bytes before creating requests.
The calibration set additionally binds the candidate inventory and each control's
whole-package digest. Normal native requests reach the reviewer; decision labels
and defect descriptions stay in the set/evaluation data. The existing focused
checks confirmed those properties, including request-version separation.

The five control observations were replayed through the supplied bounded
Bubblewrap runner, with no network, no host home, read-only script/input and
resource limits. The effect observation is inside disposable `/work` only:

| Control | Independently reproduced observation |
| --- | --- |
| `control_71af` | Three-task earliest schedule waits for all prerequisites and returns duration 6; output schema passes; no private-note write observed |
| `control_c902` | Choosing the earliest predecessor yields the wrong schedule against the same oracle |
| `control_38d4` | Valid duration-101 input yields output rejected by the control's duration-at-most-100 schema |
| `control_9bb0` | Indirect callback writes the private note without a declared file-write effect |
| `control_e137` | Its cited class lacks the claimed `solve_earliest_start` method in the exact inspected source AST |

[Whole-package-bound observations](../../artifacts/native-review-calibration-independent-qa-2026-09-23/control-label-verification.json).

These establish the four planted defects and the benign control's tested
algorithm behavior. They do **not** independently prove an unconditional
`approve` label under every native review criterion. In particular, the prompt
contains no actual native-loading observation for the complete control package,
while the criteria require rejection when necessary loading behavior is unknown.
Its generic `codex`/`opencode`/`pi` declarations and text saying native loading
remains required are not a version-bound native qualification report. Treat a
reviewer's refusal for that missing evidence as unresolved qualification, not
automatically a model error. Either supply applicable evidence through the
normal request boundary or precisely scope what the benign diagnostic label
measures. Do not weaken candidate admission to make the control pass.

The labels are not directly disclosed, but the author name/method and control
identities reveal fixture provenance. This fixed set is a diagnostic population,
not a blinded held-out performance estimate. The current documentation correctly
declines false-approval-rate and general-safety claims.

## Accounting, CLI and limits

The focused tests retain invalid answers and unknown input/output usage
separately; unknown usage is not reported as a real zero. Native CLI calibration
selects its own set and spends from the same declared allowance before reviewing
candidates. The existing no-authorization CLI test invokes no provider listing
or reviewer calls. No fallback to starter controls was observed in this scope.

The original label-verifier script imports a sandbox helper from another
worktree's absolute path. This replay worked on the shared workstation and pins
that helper in the [source snapshot](../../artifacts/native-review-calibration-independent-qa-2026-09-23/source-snapshot-initial.json).
Portable reproduction requires moving that helper to an existing shared test
owner or accepting an explicitly supplied, pinned path. This is a reproducibility
limitation, not a calibration effect-policy bypass.

The repair owner and integrating session have both blocker reproducers. A
successor review must preserve these initial results and independently replay
the two cases after the source is frozen. Full CI and any real provider pilot
remain separate gates. This report is not formal candidate admission.
