"""The tracking layer of an envelope Loop: an attempt journal by request identity, replay, reconciliation, resync.

```text
Tracking layer (envelope_journal_entry/v1, kept in the owning component's existing store)
├── intended    written before dispatch: the attempt, and whether a resume may repeat its effect
├── committed   written after: request outcome, task outcome and effect state as three fields
├── reconciled  an observation of the effect's owner that settles a pending or unknown effect
└── journal_decision(entries, identity), from the entries of one request identity alone
    ├── answer_from_first_result   the effect is confirmed: answer with the first result, never again
    ├── first_result_not_held      the effect is confirmed but its answer is gone: refuse, never repeat
    ├── reconcile_first            an effect is pending or unknown, or an attempt stopped mid-way
    │                              without declaring its effect repeatable
    └── dispatch                   nothing was tried, or every earlier attempt wrote nothing
resync_decision(observation, backoff)   desired against observed state: in sync, resync now, or wait
                                        out the capped backoff of a desired state that was rejected
```

The semantics follow ``code_nodes/overnight_journal.py`` (intended, committed and unknown, and a repeat
only where the effect was declared repeatable when it was intended) and the record of LE-INSTANCE-023
(request outcome, task outcome and effect state as separate fields). Every function here is pure: it
takes the entries the owning store already holds and returns a new entry or a decision; storing an
entry is the owner's own write, under the owner's own authority. The request identity is kept only as
its digest. No journal store, scheduler or runtime type is added.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..configuration_capabilities import digest
from .envelope import EnvelopeError, _flag, _identifier, _member, _read
from .records import EngineRecordError, instant

JOURNAL_ENTRY_RECORD_TYPE = "envelope_journal_entry/v1"
PHASE_INTENDED, PHASE_COMMITTED, PHASE_RECONCILED = "intended", "committed", "reconciled"
JOURNAL_PHASES = (PHASE_INTENDED, PHASE_COMMITTED, PHASE_RECONCILED)
#: The three outcome fields of LE-INSTANCE-023, each in its own vocabulary.
REQUEST_ANSWERED, REQUEST_CANCELLED = "answered", "cancelled"
REQUEST_OUTCOMES = (REQUEST_ANSWERED, "deadline_exceeded", REQUEST_CANCELLED, "refused")
TASK_COMPLETED, TASK_FAILED = "completed", "failed"
TASK_OUTCOMES = (TASK_COMPLETED, TASK_FAILED, "cancelled", "unknown")
EFFECT_STATE_NONE, EFFECT_STATE_PENDING, EFFECT_STATE_CONFIRMED, EFFECT_STATE_UNKNOWN = (
    "none", "pending", "confirmed", "unknown")
EFFECT_STATES = (EFFECT_STATE_NONE, EFFECT_STATE_PENDING, EFFECT_STATE_CONFIRMED, EFFECT_STATE_UNKNOWN)
UNCERTAIN_EFFECT_STATES = (EFFECT_STATE_PENDING, EFFECT_STATE_UNKNOWN)
#: What an observation can settle an uncertain effect to: it happened, or it did not.
OBSERVED_EFFECT_STATES = (EFFECT_STATE_NONE, EFFECT_STATE_CONFIRMED)
DISPATCH, ANSWER_FROM_FIRST_RESULT, FIRST_RESULT_NOT_HELD, RECONCILE_FIRST = (
    "dispatch", "answer_from_first_result", "first_result_not_held", "reconcile_first")
JOURNAL_DECISIONS = (DISPATCH, ANSWER_FROM_FIRST_RESULT, FIRST_RESULT_NOT_HELD, RECONCILE_FIRST)
RESYNC_IN_SYNC, RESYNC_NOW, RESYNC_WAIT = "in_sync", "resync_now", "wait_for_backoff"
RESYNC_DECISIONS = (RESYNC_IN_SYNC, RESYNC_NOW, RESYNC_WAIT)

_SHA256 = re.compile(r"[0-9a-f]{64}")
_STATE_IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:@+-]{0,159}")
_ENTRY_FIELDS = ("component", "request_identity", "sequence", "attempt", "phase", "request_outcome",
                 "task_outcome", "effect_state", "repeatable", "result_digest", "at", "previous_entry_digest",
                 "entry_digest")
_DIGESTED_FIELDS = _ENTRY_FIELDS[:-1]


def request_identity_digest(value) -> str:
    """The digest the journal keeps for a caller's request identity; the identity itself is never kept."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise EnvelopeError("request_identity_required", "an effect is journalled under a request identity")
    return digest({"request_identity": value})


def _sha256(value, name: str, *, empty: bool = False) -> str:
    if type(value) is not str or not (_SHA256.fullmatch(value) or (empty and value == "")):
        raise EnvelopeError("invalid_digest", f"{name} must be a SHA-256 digest" + (" or empty" if empty else ""))
    return value


def _whole(value, name: str, lowest: int) -> int:
    if type(value) is not int or value < lowest:
        raise EnvelopeError("invalid_count", f"{name} must be a whole number of at least {lowest}")
    return value


def _at(value, name: str) -> str:
    try:
        return instant(value, name)
    except EngineRecordError as error:
        raise EnvelopeError(error.code, str(error)) from None


@dataclass(frozen=True)
class EnvelopeJournalEntry:
    """One ``envelope_journal_entry/v1``: a step of one attempt of one request identity.

    The entry digest covers every other field and the previous entry's digest, so an edited, dropped or
    reordered entry breaks the chain of its request identity and is refused when the chain is read."""

    component: str
    request_identity: str
    sequence: int
    attempt: int
    phase: str
    request_outcome: str
    task_outcome: str
    effect_state: str
    repeatable: bool
    result_digest: str
    at: str
    previous_entry_digest: str
    entry_digest: str
    record_type: str = JOURNAL_ENTRY_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != JOURNAL_ENTRY_RECORD_TYPE:
            raise EnvelopeError("unsupported_record_version", f"{self.record_type} is not {JOURNAL_ENTRY_RECORD_TYPE}")
        _identifier(self.component, "component")
        _sha256(self.request_identity, "request_identity")
        _whole(self.sequence, "sequence", 1)
        _whole(self.attempt, "attempt", 1)
        _member(self.phase, "phase", JOURNAL_PHASES)
        _flag(self.repeatable, "repeatable")
        _sha256(self.result_digest, "result_digest", empty=True)
        object.__setattr__(self, "at", _at(self.at, "at"))
        _sha256(self.previous_entry_digest, "previous_entry_digest", empty=True)
        if (self.sequence == 1) != (self.previous_entry_digest == ""):
            raise EnvelopeError("journal_chain_broken", "only the first entry of an identity has no previous entry")
        if self.phase == PHASE_INTENDED:
            if self.request_outcome or self.task_outcome or self.effect_state != EFFECT_STATE_PENDING \
                    or self.result_digest:
                raise EnvelopeError("invalid_journal_entry", "an intended entry has a pending effect and no outcome")
        else:
            _member(self.request_outcome, "request_outcome", REQUEST_OUTCOMES)
            _member(self.task_outcome, "task_outcome", TASK_OUTCOMES)
            _member(self.effect_state, "effect_state", EFFECT_STATES)
            if self.phase == PHASE_RECONCILED and self.effect_state not in OBSERVED_EFFECT_STATES:
                raise EnvelopeError("reconciliation_needs_an_observation",
                                    "a reconciliation settles the effect as none or confirmed")
            if self.result_digest and self.effect_state != EFFECT_STATE_CONFIRMED:
                raise EnvelopeError("invalid_journal_entry", "only a confirmed effect names its result")
        if self.entry_digest != _entry_digest({name: getattr(self, name) for name in _DIGESTED_FIELDS}):
            raise EnvelopeError("journal_entry_digest_mismatch", "the entry digest must cover every other field")

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, **{name: getattr(self, name) for name in _ENTRY_FIELDS}}

    @classmethod
    def from_dict(cls, record) -> "EnvelopeJournalEntry":
        value = _read(record, JOURNAL_ENTRY_RECORD_TYPE, _ENTRY_FIELDS)
        return cls(**{name: value[name] for name in _ENTRY_FIELDS})


def _entry_digest(values: dict) -> str:
    return digest({"record_type": JOURNAL_ENTRY_RECORD_TYPE, **{name: values[name] for name in _DIGESTED_FIELDS}})


def _entry(fields: dict) -> EnvelopeJournalEntry:
    values = {**fields, "at": _at(fields["at"], "at")}
    return EnvelopeJournalEntry(**values, entry_digest=_entry_digest(values))


def journal_chain(entries, request_identity: str) -> tuple:
    """The entries of one request identity, in order, with their chain checked."""
    _sha256(request_identity, "request_identity")
    chain = []
    for entry in entries:
        if not isinstance(entry, EnvelopeJournalEntry):
            raise EnvelopeError("invalid_journal_entry", "a journal holds envelope_journal_entry/v1 records")
        if entry.request_identity == request_identity:
            chain.append(entry)
    for position, entry in enumerate(chain):
        previous = chain[position - 1] if position else None
        if entry.sequence != position + 1 or entry.previous_entry_digest != (
                previous.entry_digest if previous else "") or (previous and entry.component != previous.component):
            raise EnvelopeError("journal_chain_broken", f"entry {position + 1} of the identity does not follow "
                                                        "the one before it")
    return tuple(chain)


def _next_fields(chain, component: str, request_identity: str, at: str) -> dict:
    last = chain[-1] if chain else None
    return {"component": _identifier(component, "component"), "request_identity": request_identity,
            "sequence": len(chain) + 1, "previous_entry_digest": last.entry_digest if last else "", "at": at}


def journal_intent(entries, *, component: str, request_identity: str, repeatable: bool,
                   at: str) -> EnvelopeJournalEntry:
    """The entry written before one dispatch. Refused while an earlier attempt's effect is unsettled."""
    chain = journal_chain(entries, request_identity)
    decision = journal_decision(chain, request_identity)
    if decision.decision != DISPATCH:
        raise EnvelopeError("dispatch_refused_by_the_journal", f"the journal answers {decision.decision}")
    return _entry({**_next_fields(chain, component, request_identity, at), "attempt": decision.attempt,
                   "phase": PHASE_INTENDED, "request_outcome": "", "task_outcome": "",
                   "effect_state": EFFECT_STATE_PENDING, "repeatable": repeatable, "result_digest": ""})


def journal_outcome(entries, *, component: str, request_identity: str, request_outcome: str, task_outcome: str,
                    effect_state: str, result_digest: str = "", at: str) -> EnvelopeJournalEntry:
    """The entry written after one dispatch, for the attempt its intent opened."""
    chain = journal_chain(entries, request_identity)
    if not chain or chain[-1].phase != PHASE_INTENDED:
        raise EnvelopeError("outcome_without_an_intent", "an outcome follows the intent of its attempt")
    return _entry({**_next_fields(chain, component, request_identity, at), "attempt": chain[-1].attempt,
                   "phase": PHASE_COMMITTED, "request_outcome": request_outcome, "task_outcome": task_outcome,
                   "effect_state": effect_state, "repeatable": chain[-1].repeatable, "result_digest": result_digest})


def journal_reconciliation(entries, *, component: str, request_identity: str, observed_effect_state: str,
                           result_digest: str = "", at: str) -> EnvelopeJournalEntry:
    """The entry that records an observation of the effect's owner settling an uncertain effect.

    The observation is the caller's, made through the owner (a provider read, a store read); the journal
    never assumes an outcome. An observation that still cannot tell is no reconciliation."""
    chain = journal_chain(entries, request_identity)
    last = chain[-1] if chain else None
    if last is None or not (last.phase == PHASE_INTENDED or last.effect_state in UNCERTAIN_EFFECT_STATES):
        raise EnvelopeError("nothing_to_reconcile", "only a pending, unknown or interrupted effect is reconciled")
    # An effect that happened answered its request; one that did not ended its attempt without an answer.
    happened = observed_effect_state == EFFECT_STATE_CONFIRMED
    outcome, task = (REQUEST_ANSWERED, TASK_COMPLETED) if happened else (REQUEST_CANCELLED, TASK_FAILED)
    return _entry({**_next_fields(chain, component, request_identity, at), "attempt": last.attempt,
                   "phase": PHASE_RECONCILED, "request_outcome": outcome, "task_outcome": task,
                   "effect_state": observed_effect_state, "repeatable": last.repeatable,
                   "result_digest": result_digest})


@dataclass(frozen=True)
class EnvelopeJournalDecision:
    """What the tracking layer does with one request identity before any dispatch."""

    decision: str
    attempt: int
    result_digest: str
    reason: str

    def to_dict(self) -> dict:
        return {"decision": self.decision, "attempt": self.attempt, "result_digest": self.result_digest,
                "reason": self.reason}


def journal_decision(entries, request_identity: str) -> EnvelopeJournalDecision:
    """Dispatch, answer from the first result, refuse a confirmed effect whose answer is gone, or reconcile."""
    chain = journal_chain(entries, request_identity)
    if not chain:
        return EnvelopeJournalDecision(DISPATCH, 1, "", "no_earlier_attempt")
    confirmed = [entry for entry in chain if entry.phase != PHASE_INTENDED
                 and entry.effect_state == EFFECT_STATE_CONFIRMED]
    if confirmed:
        first = confirmed[0]
        if first.result_digest:
            return EnvelopeJournalDecision(ANSWER_FROM_FIRST_RESULT, first.attempt, first.result_digest,
                                           "the_effect_is_confirmed")
        return EnvelopeJournalDecision(FIRST_RESULT_NOT_HELD, first.attempt, "", "the_effect_is_confirmed")
    last = chain[-1]
    if last.phase == PHASE_INTENDED:
        if last.repeatable:
            return EnvelopeJournalDecision(DISPATCH, last.attempt + 1, "", "the_interrupted_effect_is_repeatable")
        return EnvelopeJournalDecision(RECONCILE_FIRST, last.attempt, "", "an_attempt_stopped_mid_way")
    if last.effect_state in UNCERTAIN_EFFECT_STATES:
        return EnvelopeJournalDecision(RECONCILE_FIRST, last.attempt, "", "the_effect_is_" + last.effect_state)
    return EnvelopeJournalDecision(DISPATCH, last.attempt + 1, "", "every_earlier_attempt_wrote_nothing")


@dataclass(frozen=True)
class EnvelopeResyncObservation:
    """Desired against observed state of one component, and the last desired state it could not prepare."""

    desired: str
    observed: str
    last_rejected: str = ""
    rejected_attempts: int = 0
    seconds_since_last_attempt: float = 0.0


@dataclass(frozen=True)
class EnvelopeResyncBackoff:
    """How long an unchanged rejected desired state waits before it is prepared again, doubling to a cap."""

    first_wait_seconds: float
    longest_wait_seconds: float


def resync_decision(observation: EnvelopeResyncObservation, backoff: EnvelopeResyncBackoff) -> str:
    """In sync, resync now, or wait: a changed desired state is prepared at once, an unchanged rejected one
    only after its capped backoff (LE-STATUS-008), and the previous state keeps serving meanwhile."""
    if not isinstance(observation, EnvelopeResyncObservation) or not isinstance(backoff, EnvelopeResyncBackoff):
        raise EnvelopeError("invalid_resync_input", "resync takes an observation and a backoff")
    for name in ("desired", "observed"):
        value = getattr(observation, name)
        if type(value) is not str or not _STATE_IDENTITY.fullmatch(value):
            raise EnvelopeError("invalid_state_identity", f"{name} names one exact state identity")
    if observation.last_rejected and not _STATE_IDENTITY.fullmatch(observation.last_rejected):
        raise EnvelopeError("invalid_state_identity", "last_rejected names one exact state identity")
    _whole(observation.rejected_attempts, "rejected_attempts", 0)
    seconds = observation.seconds_since_last_attempt
    first, longest = backoff.first_wait_seconds, backoff.longest_wait_seconds
    if any(type(value) not in (int, float) or value < 0 for value in (seconds, first, longest)) or not 0 < first <= longest:
        raise EnvelopeError("invalid_backoff", "waits are positive, the longest no shorter than the first")
    if observation.desired == observation.observed:
        return RESYNC_IN_SYNC
    if observation.desired != observation.last_rejected or observation.rejected_attempts == 0:
        return RESYNC_NOW
    wait = min(longest, first * 2 ** (observation.rejected_attempts - 1))
    return RESYNC_NOW if seconds >= wait else RESYNC_WAIT
