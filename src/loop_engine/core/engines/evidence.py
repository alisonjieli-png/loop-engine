"""Engine evidence: the declared rule, reviewed trials, the snapshot and the matched ranking.

Owns engine_evidence_rule/v1 (the method, the objective, the minimum matched
records, the evaluator and the window, with no default in code),
engine_trial_evidence/v1 (one frozen, measured trial of one engine
installation for one exact scope), engine_evidence_review/v1 (an independent
review bound to the exact trial), engine_evidence_snapshot/v1 (the approved
trials and reviews that selection reads at one moment, never a live query) and
MatchedEvidenceRanking, the ranking engine of design section 8.5, method 1
(matched_quality_then_efficiency, lifted from core.harness_selection). It
orders eligible installations by verified outcome and only then by the rule's
objective, and raises InsufficientEvidence when any eligible installation has
fewer matched, reviewed records than the rule's minimum, so the declared order
decides. Belongs to the shared engine framework (roadmap S-6.30).
Does not own: the paired efficiency method (method 2, planned, refused here
with its own code), comparison traffic, the evidence compiler, or any grant.
Evidence reorders one decision; it never rewrites a host policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction

from ..configuration_capabilities import digest
from ..configuration_preferences import InsufficientEvidence, PreferenceProposal
from ..harness_selection_records import APPROVED, REVIEW_DECISIONS
from .records import (
    EngineRecordError, exact_engine_ref, identifier, instant, member, read_part, read_record, sequence, sha256,
    text)
from .slots import LOWEST_PERMITTED_EVIDENCE_FLOOR, RANKING_OBJECTIVES

RULE_RECORD_TYPE = "engine_evidence_rule/v1"
TRIAL_RECORD_TYPE = "engine_trial_evidence/v1"
REVIEW_RECORD_TYPE = "engine_evidence_review/v1"
SNAPSHOT_RECORD_TYPE = "engine_evidence_snapshot/v1"
EVIDENCE_METHODS = ("matched_quality_then_efficiency", "paired_efficiency_within_loss_margin")
MATCHED_METHOD, PAIRED_METHOD = EVIDENCE_METHODS
#: Only attempts sampled for comparison count: first-choice attempts compare
#: nothing, fallback attempts saw only the hard cases, pinned ones were chosen.
RANKING_SELECTION_PATHS = ("comparison_arm", "frozen_population")
#: The reserved reference of the ranking engine this module provides.
MATCHED_EVIDENCE_ENGINE_REF = "matched-evidence"

RULE_FIELDS = ("method", "objective", "minimum_matched_records", "evaluator_ref", "evaluator_digest",
               "maximum_age_days", "maximum_records")


def _count(value, name, *, least=0):
    if type(value) is not int or value < least:
        raise EngineRecordError("invalid_field", f"{name} must be an integer of at least {least}")
    return value


def _known_number(value, name):
    if value is not None and (type(value) not in (int, float) or not 0 <= value < float("inf")):
        raise EngineRecordError("invalid_field", name + " is finite and nonnegative, or unknown")
    return value


@dataclass(frozen=True)
class EngineEvidenceRule:
    """A host's declared evidence rule; every threshold is a declared value."""

    method: str
    objective: str
    minimum_matched_records: int
    evaluator_ref: str
    evaluator_digest: str
    maximum_age_days: int
    maximum_records: int

    def __post_init__(self):
        member(self.method, "evidence method", EVIDENCE_METHODS)
        if self.method == PAIRED_METHOD:
            raise EngineRecordError("evidence_method_not_built",
                                    "the paired efficiency method is designed, not built; declare method 1")
        member(self.objective, "evidence objective", RANKING_OBJECTIVES)
        _count(self.minimum_matched_records, "minimum_matched_records", least=LOWEST_PERMITTED_EVIDENCE_FLOOR)
        text(self.evaluator_ref, "evaluator_ref")
        sha256(self.evaluator_digest, "evaluator_digest")
        _count(self.maximum_age_days, "maximum_age_days", least=1)
        _count(self.maximum_records, "maximum_records", least=self.minimum_matched_records)

    def to_dict(self) -> dict:
        return {"record_type": RULE_RECORD_TYPE, **{name: getattr(self, name) for name in RULE_FIELDS}}

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, record) -> "EngineEvidenceRule":
        record = read_record(dict(record) if type(record) is not dict else record, RULE_RECORD_TYPE, RULE_FIELDS)
        return cls(*(record[name] for name in RULE_FIELDS))


TRIAL_FIELDS = ("trial_id", "slot_id", "engine_ref", "installation_digest", "scope_digest", "population_digest",
                "evaluator_ref", "evaluator_digest", "subject_digest", "history_ref", "history_digest",
                "selection_path", "successes", "observations", "input_tokens", "output_tokens",
                "elapsed_seconds", "priced_cost", "recorded_at")


@dataclass(frozen=True)
class EngineTrialEvidence:
    """One measured trial of one installation on one exact scope; unknown stays unknown."""

    trial_id: str
    slot_id: str
    engine_ref: str
    installation_digest: str
    scope_digest: str
    population_digest: str
    evaluator_ref: str
    evaluator_digest: str
    subject_digest: str
    history_ref: str
    history_digest: str
    selection_path: str
    successes: int
    observations: int
    input_tokens: "int | None"
    output_tokens: "int | None"
    elapsed_seconds: "float | None"
    priced_cost: "float | None"
    recorded_at: str

    def __post_init__(self):
        text(self.trial_id, "trial_id")
        identifier(self.slot_id, "slot_id")
        exact_engine_ref(self.engine_ref, "engine_ref")
        for name in ("installation_digest", "scope_digest", "population_digest", "evaluator_digest",
                     "subject_digest", "history_digest"):
            sha256(getattr(self, name), name)
        text(self.evaluator_ref, "evaluator_ref")
        text(self.history_ref, "history_ref")
        member(self.selection_path, "trial selection path", RANKING_SELECTION_PATHS)
        _count(self.successes, "successes")
        _count(self.observations, "observations", least=1)
        if self.successes > self.observations:
            raise EngineRecordError("invalid_field", "successes cannot exceed observations")
        for name in ("input_tokens", "output_tokens"):
            if getattr(self, name) is not None:
                _count(getattr(self, name), name)
        _known_number(self.elapsed_seconds, "elapsed_seconds")
        _known_number(self.priced_cost, "priced_cost")
        object.__setattr__(self, "recorded_at", instant(self.recorded_at, "recorded_at"))

    def to_dict(self) -> dict:
        return {"record_type": TRIAL_RECORD_TYPE, **{name: getattr(self, name) for name in TRIAL_FIELDS}}

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def metric(self, objective: str):
        """The trial's value for one objective, or None when any part is unknown."""
        if objective == "tokens":
            known = self.input_tokens is not None and self.output_tokens is not None
            return self.input_tokens + self.output_tokens if known else None
        return self.elapsed_seconds if objective == "elapsed_seconds" else self.priced_cost

    @classmethod
    def from_dict(cls, record) -> "EngineTrialEvidence":
        record = read_record(record, TRIAL_RECORD_TYPE, TRIAL_FIELDS)
        return cls(*(record[name] for name in TRIAL_FIELDS))


REVIEW_FIELDS = ("trial_digest", "reviewer_ref", "review_evidence_ref", "review_evidence_digest", "decision")


@dataclass(frozen=True)
class EngineEvidenceReview:
    """An independent review of one exact trial; it performs no review itself."""

    trial_digest: str
    reviewer_ref: str
    review_evidence_ref: str
    review_evidence_digest: str
    decision: str

    def __post_init__(self):
        sha256(self.trial_digest, "trial_digest")
        text(self.reviewer_ref, "reviewer_ref")
        text(self.review_evidence_ref, "review_evidence_ref")
        sha256(self.review_evidence_digest, "review_evidence_digest")
        member(self.decision, "review decision", REVIEW_DECISIONS)

    def to_dict(self) -> dict:
        return {"record_type": REVIEW_RECORD_TYPE, **{name: getattr(self, name) for name in REVIEW_FIELDS}}

    @classmethod
    def from_dict(cls, record) -> "EngineEvidenceReview":
        record = read_record(record, REVIEW_RECORD_TYPE, REVIEW_FIELDS)
        return cls(*(record[name] for name in REVIEW_FIELDS))


def _refuse_self_review(trial: EngineTrialEvidence, review: EngineEvidenceReview):
    """A producer never approves its own work: not the engine, not the trial's producer."""
    producers = {trial.engine_ref, trial.engine_ref.partition("@")[0], trial.trial_id, trial.history_ref}
    if review.reviewer_ref in producers:
        raise EngineRecordError("self_review", "an engine or its trial never reviews itself")
    if review.trial_digest != trial.content_digest:
        raise EngineRecordError("review_binds_another_trial", "the review names another trial")


SNAPSHOT_FIELDS = ("slot_id", "scope_digest", "rule", "reviewed", "published_at")


@dataclass(frozen=True)
class EngineEvidenceSnapshot:
    """The reviewed trials of one slot and scope at one moment; each publication is one look."""

    slot_id: str
    scope_digest: str
    rule: EngineEvidenceRule
    reviewed: tuple
    published_at: str

    def __post_init__(self):
        identifier(self.slot_id, "slot_id")
        sha256(self.scope_digest, "scope_digest")
        if not isinstance(self.rule, EngineEvidenceRule):
            raise EngineRecordError("invalid_field", "rule must be an EngineEvidenceRule")
        pairs = tuple(self.reviewed) if type(self.reviewed) in (tuple, list) else None
        if pairs is None or any(type(pair) is not tuple or len(pair) != 2
                                or not isinstance(pair[0], EngineTrialEvidence)
                                or not isinstance(pair[1], EngineEvidenceReview) for pair in pairs):
            raise EngineRecordError("invalid_field", "reviewed holds (trial, review) pairs")
        for trial, review in pairs:
            _refuse_self_review(trial, review)
            if trial.slot_id != self.slot_id:
                raise EngineRecordError("invalid_field", "a snapshot holds trials of its own slot")
        for name in ("trial_id", "history_ref"):
            values = [getattr(trial, name) for trial, _ in pairs]
            if len(set(values)) != len(values):
                raise EngineRecordError("repeated_value", f"one {name} cannot count as several trials")
        object.__setattr__(self, "reviewed", pairs)
        object.__setattr__(self, "published_at", instant(self.published_at, "published_at"))

    def to_dict(self) -> dict:
        return {"record_type": SNAPSHOT_RECORD_TYPE, "slot_id": self.slot_id, "scope_digest": self.scope_digest,
                "rule": self.rule.to_dict(),
                "reviewed": [{"trial": trial.to_dict(), "review": review.to_dict()}
                             for trial, review in self.reviewed],
                "published_at": self.published_at}

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, record) -> "EngineEvidenceSnapshot":
        record = read_record(record, SNAPSHOT_RECORD_TYPE, SNAPSHOT_FIELDS)
        if type(record["reviewed"]) is not list:
            raise EngineRecordError("invalid_field", "reviewed must be a list")
        pairs = []
        for item in record["reviewed"]:
            item = read_part(item, "reviewed trial", ("trial", "review"))
            pairs.append((EngineTrialEvidence.from_dict(item["trial"]),
                          EngineEvidenceReview.from_dict(item["review"])))
        return cls(record["slot_id"], record["scope_digest"], EngineEvidenceRule.from_dict(record["rule"]),
                   tuple(pairs), record["published_at"])


@dataclass(frozen=True)
class RankedCandidate:
    """What the ranking needs to know about one eligible installation."""

    installation_id: str
    engine_ref: str
    installation_digest: str


def _matches(trial, review, candidate, rule, window) -> bool:
    """An approved trial of this exact installation, scope and evaluator, inside the window."""
    scope_digest, oldest = window
    return (review.decision == APPROVED and trial.engine_ref == candidate.engine_ref
            and trial.installation_digest == candidate.installation_digest and trial.scope_digest == scope_digest
            and (trial.evaluator_ref, trial.evaluator_digest) == (rule.evaluator_ref, rule.evaluator_digest)
            and datetime.fromisoformat(trial.recorded_at) >= oldest)


def _require_minimum(counts: dict, minimum: int) -> None:
    """Below the declared minimum for any eligible engine, the evidence ranks nothing."""
    if any(count < minimum for count in counts.values()):
        raise InsufficientEvidence("an eligible engine has fewer matched reviewed records than the rule's minimum")


class MatchedEvidenceRanking:
    """Method 1 as a ranking engine: verified outcome first, the objective only to break ties.

    One instance serves one selection. ``rank`` raises InsufficientEvidence
    when any eligible installation has fewer distinct matched, reviewed Run
    History references than the rule's minimum; ``used_history_refs`` then
    names what was read. The instance holds no authority and calls nothing."""

    def __init__(self, snapshot: EngineEvidenceSnapshot, candidates, *, scope_digest: str, as_of: datetime,
                 objective: str = ""):
        if not isinstance(snapshot, EngineEvidenceSnapshot):
            raise EngineRecordError("invalid_field", "the ranking reads a typed evidence snapshot")
        self._snapshot, self._scope_digest, self._as_of = snapshot, sha256(scope_digest, "scope"), as_of
        self._objective = member(objective or snapshot.rule.objective, "objective", RANKING_OBJECTIVES)
        self._candidates = {item.installation_id: item for item in candidates}
        self.used_history_refs: tuple = ()
        self.assessments: tuple = ()

    def descriptor(self) -> dict:
        return {"method": MATCHED_METHOD, "objective": self._objective,
                "rule_digest": self._snapshot.rule.content_digest,
                "snapshot_digest": self._snapshot.content_digest, "scope_digest": self._scope_digest}

    def _matched(self, candidate: RankedCandidate) -> list:
        rule = self._snapshot.rule
        oldest = self._as_of - timedelta(days=rule.maximum_age_days)
        trials = [trial for trial, review in self._snapshot.reviewed
                  if _matches(trial, review, candidate, rule, (self._scope_digest, oldest))]
        trials.sort(key=lambda trial: trial.recorded_at, reverse=True)
        return trials[:rule.maximum_records]

    def rank(self, preference_snapshot) -> PreferenceProposal:
        order = tuple(item.candidate_id for item in preference_snapshot.candidates)
        found = {name: self._matched(self._candidates[name]) for name in order}
        # One population is one comparison unit; unmatched populations are never pooled.
        common = set.intersection(*({trial.population_digest for trial in found[name]} for name in order))
        matched = {name: [trial for trial in found[name] if trial.population_digest in common] for name in order}
        self.used_history_refs = tuple(sorted({trial.history_ref for trials in matched.values() for trial in trials}))
        counts = {name: len({trial.history_ref for trial in matched[name]}) for name in order}
        self.assessments = tuple({"installation_id": name, "matched_reviewed_records": counts[name]}
                                 for name in order)
        _require_minimum(counts, self._snapshot.rule.minimum_matched_records)
        keys = []
        for index, name in enumerate(order):
            trials = matched[name]
            quality = Fraction(sum(t.successes for t in trials), sum(t.observations for t in trials))
            values = [trial.metric(self._objective) for trial in trials]
            metric = sum(values) / len(values) if all(value is not None for value in values) else None
            # An unknown metric never wins and is never read as zero.
            keys.append((-quality, metric is None, metric if metric is not None else 0, index, name))
        return PreferenceProposal(preference_snapshot.content_digest, tuple(key[-1] for key in sorted(keys)),
                                  MATCHED_EVIDENCE_ENGINE_REF + "@1.0.0", self.used_history_refs)


def self_test():
    """Run the evidence checks."""
    from .evidence_checks import self_test as run_evidence_checks
    return run_evidence_checks()
