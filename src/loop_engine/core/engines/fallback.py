"""Attempt assessment and fallback for any engine slot.

Owns EngineAttemptOutcome (what an envelope observed about one attempt: its
failure kind, whether the engine started, its effects and whether accounting
is certain), FallbackAssessment, assess_engine_attempt and fallback_request
(design section 8.9). The assessment generalizes
core.harness_fallback.assess_harness_attempt: it fails closed on uncertain
accounting, uncertain effects, a shared provider failure and exhausted
authority; a pinned choice never falls back; otherwise it moves to the next
engine only on a failure kind the host's policy names, within the slot's
fallback ceiling. The next request carries the consumed authority forward and
never replenishes it. Belongs to the shared engine framework (roadmap S-6.30).
Does not own: selection (core.engines.selection), dispatch, retry of the same
engine, provider failover or task replanning, which stay separate decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .decision_records import FALLBACK_PHASE, PINNED_BASIS, ConsumedAuthority, FallbackTransition
from .records import EngineRecordError, exact_engine_ref, flag, identifier, member, text
from .slots import FALLBACK_CEILINGS, FAILURE_KINDS, TERMINAL_FAILURE_KINDS

ATTEMPT_EFFECTS = ("none", "committed", "uncertain")
NO_EFFECTS, COMMITTED_EFFECTS, UNCERTAIN_EFFECTS = ATTEMPT_EFFECTS
ASSESSMENT_ACTIONS = ("completed", "fallback", "terminal")
COMPLETED_ACTION, FALLBACK_ACTION, TERMINAL_ACTION = ASSESSMENT_ACTIONS
BEFORE_DISPATCH_ONLY, AFTER_FAILURE_WITHOUT_EFFECTS = FALLBACK_CEILINGS[1], FALLBACK_CEILINGS[2]


@dataclass(frozen=True)
class EngineAttemptOutcome:
    """What the envelope observed about one attempt; the engine's own claims are not read here."""

    installation_id: str
    engine_ref: str
    failure_kind: str
    started: bool
    effects: str
    accounting_uncertain: bool
    consumed: ConsumedAuthority
    attempt_loop_ref: str

    def __post_init__(self):
        identifier(self.installation_id, "installation_id")
        exact_engine_ref(self.engine_ref, "engine_ref")
        if self.failure_kind:
            member(self.failure_kind, "failure kind", FAILURE_KINDS)
        flag(self.started, "started")
        member(self.effects, "attempt effects", ATTEMPT_EFFECTS)
        flag(self.accounting_uncertain, "accounting_uncertain")
        if not isinstance(self.consumed, ConsumedAuthority):
            raise EngineRecordError("invalid_field", "consumed must be a ConsumedAuthority")
        text(self.attempt_loop_ref, "attempt Loop")


@dataclass(frozen=True)
class FallbackAssessment:
    """Completed, fall back to the next engine, or stop; with the reason."""

    action: str
    failure_kind: str
    reason: str

    def __post_init__(self):
        member(self.action, "assessment action", ASSESSMENT_ACTIONS)

    def to_dict(self) -> dict:
        return {"action": self.action, "failure_kind": self.failure_kind, "reason": self.reason}


def _stop(kind, reason) -> FallbackAssessment:
    return FallbackAssessment(TERMINAL_ACTION, kind, reason)


def _uncertainty(outcome) -> str:
    """The terminal kind an uncertain attempt forces, or empty: nothing moves past uncertainty."""
    if outcome.accounting_uncertain:
        return "accounting_uncertain"
    return "effects_uncertain" if outcome.effects == UNCERTAIN_EFFECTS else ""


def _ceiling_refusal(slot, outcome) -> str:
    """Why the slot's fallback ceiling forbids a second engine after this attempt, or empty."""
    if slot.fallback_ceiling not in (BEFORE_DISPATCH_ONLY, AFTER_FAILURE_WITHOUT_EFFECTS):
        return "the slot never falls back"
    if slot.fallback_ceiling == BEFORE_DISPATCH_ONLY and outcome.started:
        return "the slot falls back only before an engine starts"
    if outcome.effects == COMMITTED_EFFECTS:
        return "the failed attempt committed effects"
    return ""


def _declared_fallback(policy, kind) -> bool:
    """Only a failure kind the host's policy names moves to the next engine."""
    return kind in policy.fallback_on


def assess_engine_attempt(slot, policy, decision, outcome: EngineAttemptOutcome) -> FallbackAssessment:
    """Decide what follows one attempt; every stop names its reason."""
    if not isinstance(outcome, EngineAttemptOutcome):
        raise EngineRecordError("invalid_field", "the assessment reads a typed EngineAttemptOutcome")
    kind = outcome.failure_kind
    if not kind:
        return FallbackAssessment(COMPLETED_ACTION, "", "the attempt completed; acceptance is judged elsewhere")
    if kind not in slot.failure_kinds:
        return _stop(kind, "a failure kind the slot does not declare")
    uncertain = _uncertainty(outcome)
    if uncertain:
        return _stop(uncertain, "uncertain effects or accounting stop the sequence until reconciled")
    if kind in TERMINAL_FAILURE_KINDS:
        return _stop(kind, "a terminal failure kind never triggers a fallback")
    if decision.selection_basis == PINNED_BASIS:
        return _stop(kind, "a pinned choice runs exactly one engine")
    ceiling = _ceiling_refusal(slot, outcome)
    if ceiling:
        return _stop(kind, ceiling)
    if not _declared_fallback(policy, kind):
        return _stop(kind, "the host's policy does not fall back on this failure kind")
    if not [name for name in decision.fallbacks if name != outcome.installation_id]:
        return _stop(kind, "no eligible fallback remains")
    return FallbackAssessment(FALLBACK_ACTION, kind, "the next declared engine may attempt the same assignment")


def fallback_request(request, outcome: EngineAttemptOutcome, *, expected_effect: str, fixed_settings=()):
    """The next selection request: phase fallback, the transition, consumption carried forward."""
    transition = FallbackTransition(
        outcome.installation_id, outcome.engine_ref, outcome.failure_kind, outcome.attempt_loop_ref,
        outcome.accounting_uncertain, expected_effect, tuple(fixed_settings))
    return replace(request, phase=FALLBACK_PHASE, transition=transition,
                   attempted=tuple(request.attempted) + (outcome.installation_id,), consumed=outcome.consumed)


def self_test():
    """Run the selection checks, which cover the assessment."""
    from .selection_checks import self_test as run_selection_checks
    return run_selection_checks()
