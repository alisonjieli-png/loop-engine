"""Evidence about reuse: what a verified outcome says about the records a step read.

The owner asked that Loop Engine converge on the most efficient solutions
from historical runs. That needs a rule for how one outcome changes what a
reused record is worth, and the rule must not be "success multiplies by a
constant": a generic record read in every run would climb to certainty, a
record retried around a failure would never be charged, and one noisy
failure would discredit a long-validated procedure.

This module owns a recency-weighted Beta posterior over the outcomes that
cited a record:

```text
posterior = (prior_strength * prior + E_s) / (prior_strength + E_s + E_f)
weight    = severity(outcome) * causal_confidence / cited * (1 + |target - posterior|)
```

The evidence masses decay on every update so the last few outcomes dominate.
The last factor is surprise: a failure on a record trusted at 0.95 counts
nearly twice as much as one on a record at 0.5. Dividing by the number of
cited records is the credit split: one outcome cannot hand each of eight
records a full unit. A first failure on a record with several successes and
no failure yet is weighed without surprise, so it is contested, not
discredited; a second failure discredits it. A regime shift is a windowed
event: a validated record that has just stopped working.

Design input: the evidence model described in the raia-live/amfs repository
at commit b9547b4 (Apache 2.0, read on 2026-09-18), re-expressed in Loop
Engine's typed records; no code was copied. The label (validated, contested,
discredited) is evidence about reuse. It is separate from the lifecycle
status (candidate, qualified, retired), which only an independent process
changes, and it never promotes a record.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

OUTCOMES = ("verified", "failed")
LABELS = ("untested", "validated", "contested", "discredited")
UNTESTED, VALIDATED, CONTESTED, DISCREDITED = LABELS
#: A derived record written by the engine, never by the model; excluded from
#: training and from grading as if the model had authored it.
SYNTHETIC_MARKER = "derived:contrast"


class ReuseEvidenceError(ValueError):
    """A policy, an evidence record, or an outcome is invalid."""


@dataclass(frozen=True)
class ReuseEvidencePolicy:
    """The declared numbers of the update rule; a versioned policy, not code."""

    prior_strength: float = 2.0
    decay: float = 0.8
    failure_severity: float = 2.0
    success_severity: float = 1.0
    discredit_threshold: float = 0.5
    first_strike_min_wins: int = 3
    validated_min_posterior: float = 0.7
    validated_min_outcomes: int = 2
    validated_min_wins: int = 4
    validated_max_losses_with_wins: int = 1
    regime_min_successes: int = 3
    regime_window_seconds: float = 7 * 86400.0
    version: str = "1.0.0"

    def __post_init__(self):
        for name in ("prior_strength", "failure_severity", "success_severity"):
            if not getattr(self, name) > 0:
                raise ReuseEvidenceError(f"{name} must be positive")
        if not 0 < self.decay <= 1:
            raise ReuseEvidenceError("decay must be in (0, 1]")
        for name in ("discredit_threshold", "validated_min_posterior"):
            if not 0 <= getattr(self, name) <= 1:
                raise ReuseEvidenceError(f"{name} must be in [0, 1]")
        for name in ("first_strike_min_wins", "validated_min_outcomes", "validated_min_wins",
                     "validated_max_losses_with_wins", "regime_min_successes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ReuseEvidenceError(f"{name} must be a non-negative integer")
        if not self.regime_window_seconds > 0:
            raise ReuseEvidenceError("regime window must be positive")

    def to_dict(self) -> dict:
        return {"record_type": "reuse_evidence_policy/v1", **{
            name: getattr(self, name) for name in self.__dataclass_fields__}}


DEFAULT_POLICY = ReuseEvidencePolicy()


@dataclass(frozen=True)
class ReuseEvidence:
    """The outcome record of one reused record; the claim's evidence, not the row's."""

    record_ref: str
    prior: float
    evidence_success: float = 0.0
    evidence_failure: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_outcome: str = ""
    last_outcome_at: "float | None" = None
    discredited_at: "float | None" = None

    def __post_init__(self):
        if not isinstance(self.record_ref, str) or not self.record_ref:
            raise ReuseEvidenceError("evidence needs the reference of the record it is about")
        if not 0 <= self.prior <= 1:
            raise ReuseEvidenceError("the prior is the confidence the author wrote, in [0, 1]")
        if self.evidence_success < 0 or self.evidence_failure < 0:
            raise ReuseEvidenceError("evidence masses cannot be negative")
        if self.last_outcome and self.last_outcome not in OUTCOMES:
            raise ReuseEvidenceError(f"an outcome is one of {OUTCOMES}")

    @property
    def outcome_count(self) -> int:
        return self.success_count + self.failure_count

    def posterior(self, policy: ReuseEvidencePolicy = DEFAULT_POLICY) -> float:
        return ((policy.prior_strength * self.prior + self.evidence_success)
                / (policy.prior_strength + self.evidence_success + self.evidence_failure))

    def label(self, policy: ReuseEvidencePolicy = DEFAULT_POLICY) -> str:
        """Judge the record, not the last event."""
        if self.outcome_count == 0:
            return UNTESTED
        if self.discredited_at is not None:
            return DISCREDITED
        if self.failure_count == 0:
            return VALIDATED
        posterior = self.posterior(policy)
        if (self.outcome_count >= policy.validated_min_outcomes
                and posterior >= policy.validated_min_posterior):
            return VALIDATED
        if (self.success_count >= policy.validated_min_wins
                and self.failure_count <= policy.validated_max_losses_with_wins):
            return VALIDATED
        return CONTESTED

    def to_dict(self, policy: ReuseEvidencePolicy = DEFAULT_POLICY) -> dict:
        return {"record_type": "reuse_evidence/v1", "record_ref": self.record_ref,
                "prior": self.prior, "evidence_success": self.evidence_success,
                "evidence_failure": self.evidence_failure,
                "success_count": self.success_count, "failure_count": self.failure_count,
                "last_outcome": self.last_outcome, "last_outcome_at": self.last_outcome_at,
                "discredited_at": self.discredited_at, "posterior": self.posterior(policy),
                "label": self.label(policy)}


@dataclass(frozen=True)
class EvidenceUpdate:
    """What one outcome did to one record's evidence, kept for the run's records."""

    record_ref: str
    outcome: str
    weight: float
    surprise_applied: bool
    posterior_before: float
    posterior_after: float
    label_before: str
    label_after: str

    def to_dict(self) -> dict:
        return {"record_type": "reuse_evidence_update/v1", **{
            name: getattr(self, name) for name in self.__dataclass_fields__}}


def first_strike(evidence: ReuseEvidence, outcome: str, policy: ReuseEvidencePolicy) -> bool:
    """A first failure against a run of successes is weighed without surprise."""
    return (outcome == OUTCOMES[1] and evidence.failure_count == 0
            and evidence.success_count >= policy.first_strike_min_wins)


def apply_outcome(evidence: ReuseEvidence, outcome: str, *, at: float, cited: int = 1,
                  causal_confidence: float = 1.0,
                  policy: ReuseEvidencePolicy = DEFAULT_POLICY) -> tuple[ReuseEvidence, EvidenceUpdate]:
    """Fold one verified outcome into the evidence and return the new record and the update.

    ``cited`` is how many records the same outcome cited (the credit split) and
    ``causal_confidence`` is how sure the caller is that this record informed
    the outcome; both scale the weight down, never up.
    """
    if outcome not in OUTCOMES:
        raise ReuseEvidenceError(f"an outcome is one of {OUTCOMES}")
    if type(cited) is not int or cited < 1:
        raise ReuseEvidenceError("cited counts the records the outcome cited, at least one")
    if not 0 <= causal_confidence <= 1:
        raise ReuseEvidenceError("causal confidence is in [0, 1]")
    before = evidence.posterior(policy)
    success = outcome == OUTCOMES[0]
    severity = policy.success_severity if success else policy.failure_severity
    target = 1.0 if success else 0.0
    strike = first_strike(evidence, outcome, policy)
    surprise = 1.0 if strike else 1.0 + abs(target - before)
    weight = severity * causal_confidence / cited * surprise
    decayed_success = evidence.evidence_success * policy.decay
    decayed_failure = evidence.evidence_failure * policy.decay
    updated = replace(
        evidence,
        evidence_success=decayed_success + (weight if success else 0.0),
        evidence_failure=decayed_failure + (0.0 if success else weight),
        success_count=evidence.success_count + (1 if success else 0),
        failure_count=evidence.failure_count + (0 if success else 1),
        last_outcome=outcome, last_outcome_at=at)
    after = updated.posterior(policy)
    if not success and after < policy.discredit_threshold:
        updated = replace(updated, discredited_at=at)
    elif success and evidence.discredited_at is not None and after >= policy.discredit_threshold:
        updated = replace(updated, discredited_at=None)
    return updated, EvidenceUpdate(
        record_ref=evidence.record_ref, outcome=outcome, weight=weight,
        surprise_applied=not strike, posterior_before=before, posterior_after=after,
        label_before=evidence.label(policy), label_after=updated.label(policy))


def regime_shifted(evidence: ReuseEvidence, *, now: float,
                   policy: ReuseEvidencePolicy = DEFAULT_POLICY) -> bool:
    """Whether a record that used to work has just stopped: a windowed event."""
    if (evidence.success_count < policy.regime_min_successes or evidence.failure_count < 1
            or evidence.last_outcome != OUTCOMES[1] or evidence.last_outcome_at is None):
        return False
    if now - evidence.last_outcome_at > policy.regime_window_seconds:
        return False
    return evidence.label(policy) != VALIDATED


def inherit_evidence(new_ref: str, current: "ReuseEvidence | None", *, same_claim: bool,
                     prior: float) -> ReuseEvidence:
    """A restated claim keeps its evidence; a changed claim starts untested."""
    if current is not None and same_claim:
        return replace(current, record_ref=new_ref)
    return ReuseEvidence(new_ref, prior)


def contrast_lesson(failed_attempts: tuple[tuple[str, ...], ...], final_refs: tuple[str, ...],
                    outcome: str) -> "dict | None":
    """The derived lesson of a fail-then-succeed run, or None when there is none.

    Only when at least one failed attempt cited a record and the final outcome
    is verified: those records led to a failed attempt, and the task was
    resolved without them. The lesson carries the synthetic marker.
    """
    if outcome != OUTCOMES[0] or not failed_attempts:
        return None
    avoid = []
    for refs in failed_attempts:
        for ref in refs:
            if ref not in avoid:
                avoid.append(ref)
    if not avoid:
        return None
    resolved_with = [ref for ref in final_refs if ref not in avoid]
    return {"record_type": "reuse_contrast_lesson/v1", "marker": SYNTHETIC_MARKER,
            "failed_attempts": len(failed_attempts), "avoid": avoid,
            "resolved_with": resolved_with,
            "lesson": (f"{len(avoid)} reused record(s) led to a failed attempt before the "
                       f"task was verified" + (f" using {len(resolved_with)} other record(s)"
                                               if resolved_with else "") + ".")}


def self_test() -> dict:
    """The documented behaviors of the rule, reproduced from its formulas."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def near(value, expected, tolerance=0.01):
        return abs(value - expected) <= tolerance

    def refuses(action):
        try:
            action()
        except ReuseEvidenceError:
            return True
        return False

    fresh = ReuseEvidence("record:a", 0.7)
    failed_once, update = apply_outcome(fresh, "failed", at=1.0)
    succeeded_once, _ = apply_outcome(fresh, "verified", at=1.0)
    check("a_fresh_record_moves_far_on_its_first_outcome",
          near(failed_once.posterior(), 0.26) and near(succeeded_once.posterior(), 0.82)
          and update.surprise_applied and failed_once.label() == DISCREDITED
          and succeeded_once.label() == VALIDATED,
          f"failed {failed_once.posterior():.3f}, succeeded {succeeded_once.posterior():.3f}")
    validated = fresh
    for step in range(4):
        validated, _ = apply_outcome(validated, "verified", at=float(step))
    first_failure, strike = apply_outcome(validated, "failed", at=10.0)
    second_failure, _ = apply_outcome(first_failure, "failed", at=11.0)
    # Four wins and one loss is still a record worth acting on: the label
    # judges the record, and only the second failure in a row discredits it.
    check("a_long_validated_record_survives_one_failure_and_not_two",
          near(validated.posterior(), 0.89) and not strike.surprise_applied
          and near(first_failure.posterior(), 0.62) and first_failure.label() == VALIDATED
          and near(second_failure.posterior(), 0.40) and second_failure.label() == DISCREDITED
          and ReuseEvidence("record:b", 0.7, success_count=1, failure_count=1,
                            evidence_success=1.0, evidence_failure=2.0).label() == CONTESTED,
          f"{validated.posterior():.3f} -> {first_failure.posterior():.3f} -> {second_failure.posterior():.3f}")
    split, _ = apply_outcome(fresh, "verified", at=1.0, cited=3)
    solo, _ = apply_outcome(fresh, "verified", at=1.0)
    check("credit_is_split_across_the_records_one_outcome_cited",
          split.evidence_success < solo.evidence_success
          and near(split.evidence_success * 3, solo.evidence_success, 1e-9))
    weak, _ = apply_outcome(fresh, "verified", at=1.0, causal_confidence=0.5)
    check("causal_confidence_scales_the_weight_down_never_up",
          weak.evidence_success < solo.evidence_success
          and refuses(lambda: apply_outcome(fresh, "verified", at=1.0, causal_confidence=1.5)))
    # The failure the label forgives is not a shift; the second one is, and
    # only while it is recent.
    check("a_regime_shift_is_a_recent_second_failure_after_a_validated_run",
          not regime_shifted(first_failure, now=10.0 + 3600)
          and regime_shifted(second_failure, now=11.0 + 3600)
          and not regime_shifted(second_failure, now=11.0 + 8 * 86400)
          and not regime_shifted(validated, now=10.0)
          and not regime_shifted(failed_once, now=2.0))
    recovered, _ = apply_outcome(second_failure, "verified", at=12.0)
    recovered, _ = apply_outcome(recovered, "verified", at=13.0)
    check("a_discredited_record_can_earn_its_way_back",
          recovered.discredited_at is None and recovered.posterior() >= DEFAULT_POLICY.discredit_threshold)
    check("a_restated_claim_keeps_its_evidence_and_a_changed_claim_starts_untested",
          inherit_evidence("record:a2", validated, same_claim=True, prior=0.7).success_count == 4
          and inherit_evidence("record:a2", validated, same_claim=False, prior=0.7).label() == UNTESTED)
    lesson = contrast_lesson((("record:x", "record:y"), ("record:x",)), ("record:z", "record:x"),
                             "verified")
    check("a_fail_then_succeed_run_writes_a_marked_contrast_lesson",
          lesson is not None and lesson["avoid"] == ["record:x", "record:y"]
          and lesson["resolved_with"] == ["record:z"] and lesson["marker"] == SYNTHETIC_MARKER
          and contrast_lesson((), ("record:z",), "verified") is None
          and contrast_lesson((("record:x",),), (), "failed") is None)
    check("the_policy_and_evidence_are_validated_records",
          all(refuses(action) for action in (
              lambda: ReuseEvidencePolicy(decay=0),
              lambda: ReuseEvidencePolicy(first_strike_min_wins=-1),
              lambda: ReuseEvidence("", 0.5),
              lambda: ReuseEvidence("record:a", 1.5),
              lambda: apply_outcome(fresh, "maybe", at=1.0),
              lambda: apply_outcome(fresh, "verified", at=1.0, cited=0)))
          and fresh.to_dict()["label"] == UNTESTED
          and DEFAULT_POLICY.to_dict()["version"] == "1.0.0")
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "reuse_evidence_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
