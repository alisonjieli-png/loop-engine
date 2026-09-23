# Native package calibration controls

These evaluation fixtures contribute **zero library items**. Four packages
deliberately contain incorrect behavior, a conflicting contract, an undeclared
effect or an unsupported source claim. Use them only through the calibration
workflow and its bounded test environment.

`calibration-set.json` holds the decision labels and exact package digests.
Those labels stay outside the package files and reviewer prompt. The normal
native candidate reader verifies the complete inventory in `catalogue/`.
The review command selects this set for `native-original --calibrate` and
refuses to reinterpret a starter-body set as a native set.

The related source package is the independently checked version-two scheduling
candidate named by the set. One fixture preserves correct scheduling; four
separate mutations supply discriminating controls. The source package and
control files keep separate identities. The declared base and related controls
are excluded from their calibration duplicate comparison; unrelated candidate
material is retained. A changed base under the same identity is refused.

The existing calibration evaluator records false approvals, expected-approve
label refusals, and controls without a valid verdict. Calls keep invalid responses
and unknown usage separately in the existing ledger. Approval of a known-wrong
control or any unanswered control excludes that reviewer from the
following candidate phase. Reviewers skipped for control authorship, disabled,
or unavailable also remain unmeasured and excluded. An expected-approve label
refusal remains separately recorded.
The small fixed set supplies no population error-rate estimate or general
safety guarantee. Real candidate admission still needs the existing independent
family rule and exact-package review.

**Pilot hold:** the correct scheduling control has no applicable native-loading
evidence attached to its review request. Its approve label is provisional, and
a refusal cannot yet be called an empirical false refusal. The real pilot needs
that evidence or a separately reviewed control scope. Do not weaken the native
admission criterion or add a self-certified loading claim to this package.

The [verification report](../../../../docs/verification/NATIVE-REVIEW-CALIBRATION-2026-09-23.md)
records the five control labels, their sandbox observations and the tests.
