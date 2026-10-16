"""Envelope layers: the ordered work an envelope Loop does between an edge contract and its engine slot.

The owner asked on October 16, 2026 for functional components wrapped in layers: flexible edges whose
objects and pointers can change, a compatibility and handshake layer, tracking and resync of handshakes,
updates and ideas, account checks, triggers and resyncs, frustration avoidance, and self troubleshooting
and self resolving before the functional engine, with the same layers around an engine that is itself
made of components. docs/architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md maps those words onto the
envelope layers below, and section 14 of docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md states
their rules as LE-LAYER statements.

```text
Envelope Loop of one functional component, for one request, outermost first
├── frustration_avoidance  every refusal leaves as envelope_refusal/v1 (code, what happened, next
│                          action, retry rule and statement); bounded recovery never repeats an effect
├── carrier                exact name/vN records; flexible fields read only through a declared schema;
│                          pointers resolved only by their owner, with the digest checked
├── handshake              envelope_handshake_verdict/v1 computed from declarations; unknown fails closed
├── account                principal and entitlement from the service's own records; events applied once
├── tracking               envelope_journal_entry/v1, replay, reconciliation and resync (envelope_tracking.py)
├── preflight              declared effect-free checks and bounded self-repairs (envelope_preflight.py)
└── the engine slot        selection, binding and one engine; a nested slot is entered through
                           enter_nested with the same allowance and deadline, never fresh ones
```

This module holds the layer vocabulary, the handshake verdict and its negotiation, the refusal record
with its recovery policy and allowance, the nesting frame, and the trace of the layers one request
passed. It is not a Loop, a runtime type, a registry, a store or a scheduler. Every function is pure
except RecoveryAllowance, an in-memory counter that the envelopes of one request share. Nothing here
imports an engine, opens a file or a connection, starts a process or calls a model, and no record
grants model, file, network, secret, spending or external-effect authority.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType

from ...catalog.handshake import (
    COMPATIBLE, COMPATIBLE_EXPORT_ONLY, COMPATIBLE_READ_ONLY, COMPATIBLE_WITH_DEGRADATION,
    COMPATIBLE_WITH_MIGRATION, INCOMPATIBLE, REFUSED_BY_POLICY, UNKNOWN_COMPATIBILITY, VERDICTS)
from ..facets import EFFECTS
from .records import EngineRecordError, read_record

LAYER_FRUSTRATION_AVOIDANCE, LAYER_CARRIER, LAYER_HANDSHAKE, LAYER_ACCOUNT, LAYER_TRACKING, LAYER_PREFLIGHT = (
    "frustration_avoidance", "carrier", "handshake", "account", "tracking", "preflight")
#: The envelope layers of one envelope Loop, outermost first. A request passes the inbound layers in this
#: order and a layer runs only after every layer outside it accepted the request; frustration avoidance
#: shapes every answer on the way out.
ENVELOPE_LAYERS = (LAYER_FRUSTRATION_AVOIDANCE, LAYER_CARRIER, LAYER_HANDSHAKE, LAYER_ACCOUNT, LAYER_TRACKING,
                   LAYER_PREFLIGHT)
INBOUND_LAYERS = ENVELOPE_LAYERS[1:]
#: The rule that applies the same envelope layers around each nested slot, declared beside the layers.
NESTED_ENVELOPES = "nested_envelopes"
COVERAGE_LAYERS = ENVELOPE_LAYERS + (NESTED_ENVELOPES,)
#: Where a refusal came from: one inbound layer, or the engine after dispatch.
ENGINE_SOURCE = "engine"
REFUSAL_SOURCES = INBOUND_LAYERS + (ENGINE_SOURCE,)

HANDSHAKE_VERDICT_RECORD_TYPE = "envelope_handshake_verdict/v1"
REFUSAL_RECORD_TYPE = "envelope_refusal/v1"
RECOVERY_POLICY_RECORD_TYPE = "envelope_recovery_policy/v1"
FRAME_RECORD_TYPE = "envelope_frame/v1"
TRACE_RECORD_TYPE = "envelope_trace/v1"

#: The store handshake verdicts that let a request go on. Each one needs a declared match.
PROCEEDING_VERDICTS = (COMPATIBLE, COMPATIBLE_WITH_MIGRATION, COMPATIBLE_WITH_DEGRADATION, COMPATIBLE_READ_ONLY,
                       COMPATIBLE_EXPORT_ONLY)
#: The effect that means none at all; every other declared effect needs a grant.
PURE_EFFECT = EFFECTS[0]
#: The effect classes a declaration or a self-repair may name: the facet vocabulary and the three classes of
#: the effects rule that it lacks.
ENVELOPE_EFFECTS = EFFECTS + ("model_call", "spending", "external_effect")

RETRY_NOW_SAME_IDENTITY, RETRY_AFTER_WAIT, RETRY_AFTER_FIX, RECONCILE_BEFORE_RETRY, DO_NOT_RETRY = (
    "retry_now_same_identity", "retry_after_wait", "retry_after_fix", "reconcile_before_retry", "do_not_retry")
RETRY_RULES = (RETRY_NOW_SAME_IDENTITY, RETRY_AFTER_WAIT, RETRY_AFTER_FIX, RECONCILE_BEFORE_RETRY, DO_NOT_RETRY)
#: The retry statement of each rule, word for word, so that a person can read it and an agent can act on it.
RETRY_STATEMENTS = MappingProxyType({
    RETRY_NOW_SAME_IDENTITY: "Send the same request again with the same request identity, and nothing is done twice.",
    RETRY_AFTER_WAIT: "Wait the seconds this refusal names, then send the same request with the same identity.",
    RETRY_AFTER_FIX: "Change what the next action names first, then send the corrected request.",
    RECONCILE_BEFORE_RETRY: "Do not send this request again until its earlier outcome has been reconciled.",
    DO_NOT_RETRY: "Sending the same request again will be refused in the same way.",
})
EFFECT_NONE, EFFECT_NOT_ASSERTED, EFFECT_DURABLE_PENDING, EFFECT_UNKNOWN = (
    "none", "not_asserted", "durable_pending", "unknown")
#: What a refusal says about effects: none happened; the answer does not assert either way (the hosted
#: service's word, safe to repeat under the same request identity); one is durably pending; or unknown.
EFFECT_COMMITMENTS = (EFFECT_NONE, EFFECT_NOT_ASSERTED, EFFECT_DURABLE_PENDING, EFFECT_UNKNOWN)
UNCERTAIN_EFFECTS = (EFFECT_DURABLE_PENDING, EFFECT_UNKNOWN)
CALLER, ACCOUNT_OWNER, OPERATOR = "caller", "account_owner", "operator"
#: Who acts on a next action, so that no refusal leaves its reader without someone to turn to.
NEXT_ACTION_BY = (CALLER, ACCOUNT_OWNER, OPERATOR)

#: The most automatic attempts one request may make, shared by every envelope it passes through. Three is
#: the bound the billing webhook already uses for a delivery that lost a race (BEGIN_ATTEMPTS).
MAXIMUM_AUTOMATIC_ATTEMPTS = 3
#: The deepest nesting below the first envelope of one request. The catalogue's deepest chain is three
#: levels below its root today (step_executor, model_call_strategy, model_access, local_credential_source);
#: four leaves one level for a composite engine before the bound refuses.
MAXIMUM_ENVELOPE_DEPTH = 4

LAYER_ACCEPTED, LAYER_REFUSED, LAYER_ANSWERED, LAYER_NOT_APPLICABLE = (
    "accepted", "refused", "answered", "not_applicable")
#: What one inbound layer did with one request. Answered means the layer gave the answer itself from a
#: record, as the tracking layer does when a retry repeats a request whose effect is confirmed.
LAYER_RESULTS = (LAYER_ACCEPTED, LAYER_REFUSED, LAYER_ANSWERED, LAYER_NOT_APPLICABLE)
#: The results after which no inner layer and no engine runs.
LAYER_ENDINGS = (LAYER_REFUSED, LAYER_ANSWERED)

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,95}")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:+-]{0,95}")
_CAPABILITY = re.compile(r"[a-z][a-z0-9_.:-]{0,95}")
_CODE = re.compile(r"[a-z][a-z0-9_]{1,79}")
_REASON = re.compile(r"[a-z][a-z0-9_]{1,79}(?::[A-Za-z0-9_.:/@-]{1,160})?")
_SENTENCE_WORDS, _SENTENCE_LIMIT = 5, 400


class EnvelopeError(EngineRecordError):
    """An envelope record or step was refused before any effect, with a stable code."""


def _refuse(code: str, detail: str):
    raise EnvelopeError(code, detail)


def _identifier(value, name: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        _refuse("invalid_identifier", f"{name} must match {_IDENTIFIER.pattern}")
    return value


def _names(values, name: str, pattern, *, allow_none: bool = False):
    """A tuple of unique names, each matching its pattern; None only where a declaration may be absent."""
    if values is None and allow_none:
        return None
    if type(values) not in (tuple, list) or any(type(item) is not str or not pattern.fullmatch(item)
                                                for item in values):
        _refuse("invalid_name_list", f"{name} must be a list of names matching {pattern.pattern}")
    if len(set(values)) != len(values):
        _refuse("repeated_value", f"{name} must not repeat a name")
    return tuple(values)


def _effects(values, name: str, *, allow_none: bool = False):
    values = _names(values, name, _CAPABILITY, allow_none=allow_none)
    if values is not None and any(item not in ENVELOPE_EFFECTS for item in values):
        _refuse("invalid_effect", f"{name} must name effects from {list(ENVELOPE_EFFECTS)}")
    return values


def sentence(value, name: str) -> str:
    """A plain sentence: trimmed, at least five words, ending with a full stop, at most 400 characters."""
    if (type(value) is not str or value != value.strip() or not value.endswith(".")
            or len(value.split()) < _SENTENCE_WORDS or len(value) > _SENTENCE_LIMIT):
        _refuse("invalid_sentence", f"{name} must be one plain sentence of at least {_SENTENCE_WORDS} words")
    return value


def _member(value, name: str, allowed) -> str:
    if type(value) is not str or value not in allowed:
        _refuse("invalid_vocabulary", f"{name} must be one of {list(allowed)}")
    return value


def _flag(value, name: str) -> bool:
    if type(value) is not bool:
        _refuse("invalid_boolean", f"{name} must be an explicit Boolean")
    return value


def _count(value, name: str, lowest: int, highest: int) -> int:
    if type(value) is not int or not lowest <= value <= highest:
        _refuse("invalid_count", f"{name} must be a whole number from {lowest} to {highest}")
    return value


def _read(record, record_type: str, fields: tuple) -> dict:
    """The shared strict reader, with its refusal kept as an envelope refusal of the same code."""
    try:
        return read_record(record, record_type, fields)
    except EnvelopeError:
        raise
    except EngineRecordError as error:
        raise EnvelopeError(error.code, str(error)) from None


def _listed(value):
    return list(value) if isinstance(value, tuple) else value


# The handshake layer: one verdict for one caller and one engine, computed from declarations.

@dataclass(frozen=True)
class EnvelopeHandshakeRequest:
    """What one caller asks: versions in its order of preference, required and advisory capabilities, grants."""

    component: str
    requested_versions: tuple
    required_capabilities: tuple = ()
    advisory_capabilities: tuple = ()
    granted_effects: tuple = ()


@dataclass(frozen=True)
class EnvelopeHandshakeDeclaration:
    """What one engine or component declares. None means it declared nothing, which is never compatible."""

    engine: str
    supported_versions: "tuple | None"
    capabilities: "tuple | None"
    effects: "tuple | None"


def _judge(requested, supported, required, advisory, declared, effects, granted) -> tuple:
    """(verdict, selected version, reasons, degraded behaviour) from declarations alone.

    A missing declaration is unknown, never a guess. A version is selected only by equality with an
    entry of the caller's preference order: no version order, prefix or range ever decides."""
    undeclared = [name for name, value in (("supported_versions_undeclared", supported),
                                           ("capabilities_undeclared", declared),
                                           ("effects_undeclared", effects)) if value is None]
    if undeclared:
        return UNKNOWN_COMPATIBILITY, "", tuple(undeclared), ()
    selected = next((version for version in requested if version in supported), "")
    reasons = [] if selected else ["no_mutually_supported_version"]
    reasons += [f"capability_missing:{name}" for name in required if name not in declared]
    if reasons:
        return INCOMPATIBLE, "", tuple(reasons), ()
    ungranted = [name for name in effects if name != PURE_EFFECT and name not in granted]
    if ungranted:
        return REFUSED_BY_POLICY, "", tuple(f"effect_not_granted:{name}" for name in ungranted), ()
    degraded = tuple(f"advisory_capability_ignored:{name}" for name in advisory if name not in declared)
    return (COMPATIBLE_WITH_DEGRADATION if degraded else COMPATIBLE), selected, (), degraded


_VERDICT_FIELDS = ("component", "engine", "requested_versions", "supported_versions", "required_capabilities",
                   "advisory_capabilities", "declared_capabilities", "declared_effects", "granted_effects",
                   "verdict", "selected_version", "reasons", "degraded_behavior")


@dataclass(frozen=True)
class EnvelopeHandshakeVerdict:
    """One ``envelope_handshake_verdict/v1``: a store handshake verdict that follows from its own fields.

    The record recomputes its verdict from the declarations it carries, so a verdict that claims
    compatibility without a declared match is refused when it is built or read, whoever wrote it."""

    component: str
    engine: str
    requested_versions: tuple
    supported_versions: "tuple | None"
    required_capabilities: tuple
    advisory_capabilities: tuple
    declared_capabilities: "tuple | None"
    declared_effects: "tuple | None"
    granted_effects: tuple
    verdict: str
    selected_version: str
    reasons: tuple
    degraded_behavior: tuple
    record_type: str = HANDSHAKE_VERDICT_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != HANDSHAKE_VERDICT_RECORD_TYPE:
            _refuse("unsupported_record_version", f"{self.record_type} is not {HANDSHAKE_VERDICT_RECORD_TYPE}")
        _identifier(self.component, "component")
        if self.engine:
            _identifier(self.engine, "engine")
        names = {
            "requested_versions": _names(self.requested_versions, "requested_versions", _VERSION),
            "supported_versions": _names(self.supported_versions, "supported_versions", _VERSION, allow_none=True),
            "required_capabilities": _names(self.required_capabilities, "required_capabilities", _CAPABILITY),
            "advisory_capabilities": _names(self.advisory_capabilities, "advisory_capabilities", _CAPABILITY),
            "declared_capabilities": _names(self.declared_capabilities, "declared_capabilities", _CAPABILITY,
                                            allow_none=True),
            "declared_effects": _effects(self.declared_effects, "declared_effects", allow_none=True),
            "granted_effects": _effects(self.granted_effects, "granted_effects"),
            "reasons": _names(self.reasons, "reasons", _REASON),
            "degraded_behavior": _names(self.degraded_behavior, "degraded_behavior", _REASON)}
        for name, value in names.items():
            object.__setattr__(self, name, value)
        if not self.requested_versions:
            _refuse("invalid_name_list", "requested_versions names at least one version")
        _member(self.verdict, "verdict", VERDICTS)
        if type(self.selected_version) is not str:
            _refuse("invalid_field", "selected_version must be text")
        expected = _judge(self.requested_versions, self.supported_versions, self.required_capabilities,
                          self.advisory_capabilities, self.declared_capabilities, self.declared_effects,
                          self.granted_effects)
        if self.verdict in PROCEEDING_VERDICTS and expected[0] not in PROCEEDING_VERDICTS:
            _refuse("inferred_compatibility_refused",
                    f"{self.verdict} without a declared match; the declarations give {expected[0]}")
        if (self.verdict, self.selected_version, self.reasons, self.degraded_behavior) != expected:
            _refuse("handshake_verdict_does_not_follow_from_its_declarations",
                    f"the declarations give {expected[0]} with {list(expected[2] or expected[3])}")

    @property
    def proceeds(self) -> bool:
        return self.verdict in PROCEEDING_VERDICTS

    def to_dict(self) -> dict:
        return {"record_type": self.record_type,
                **{name: _listed(getattr(self, name)) for name in _VERDICT_FIELDS}}

    @classmethod
    def from_dict(cls, record) -> "EnvelopeHandshakeVerdict":
        value = _read(record, HANDSHAKE_VERDICT_RECORD_TYPE, _VERDICT_FIELDS)
        return cls(**{name: value[name] for name in _VERDICT_FIELDS})


def negotiate_handshake(request: EnvelopeHandshakeRequest,
                        declaration: EnvelopeHandshakeDeclaration) -> EnvelopeHandshakeVerdict:
    """The handshake verdict for one caller and one engine, before any effect."""
    if not isinstance(request, EnvelopeHandshakeRequest) or not isinstance(declaration,
                                                                           EnvelopeHandshakeDeclaration):
        _refuse("invalid_handshake_input", "negotiation takes a handshake request and a declaration")
    supported = None if declaration.supported_versions is None else tuple(declaration.supported_versions)
    capabilities = None if declaration.capabilities is None else tuple(declaration.capabilities)
    effects = None if declaration.effects is None else tuple(declaration.effects)
    verdict, selected, reasons, degraded = _judge(
        tuple(request.requested_versions), supported, tuple(request.required_capabilities),
        tuple(request.advisory_capabilities), capabilities, effects, tuple(request.granted_effects))
    return EnvelopeHandshakeVerdict(
        request.component, declaration.engine, tuple(request.requested_versions), supported,
        tuple(request.required_capabilities), tuple(request.advisory_capabilities), capabilities, effects,
        tuple(request.granted_effects), verdict, selected, reasons, degraded)


# The frustration avoidance layer: one refusal record, and a recovery bound that never repeats an effect.

_REFUSAL_FIELDS = ("code", "message", "next_action", "next_action_by", "retry", "retry_statement",
                   "retry_after_seconds", "effect_commitment", "automatic_retry")


@dataclass(frozen=True)
class EnvelopeRefusal:
    """One ``envelope_refusal/v1``: a stable code, what happened, the next action and the retry rule.

    The message and the next action are plain sentences, never a bare code; the retry statement is the
    rule's own sentence; an uncertain effect always reconciles before any retry; and only a refusal that
    wrote nothing may be retried automatically."""

    code: str
    message: str
    next_action: str
    next_action_by: str
    retry: str
    retry_statement: str
    retry_after_seconds: "int | None"
    effect_commitment: str
    automatic_retry: bool
    record_type: str = REFUSAL_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != REFUSAL_RECORD_TYPE:
            _refuse("unsupported_record_version", f"{self.record_type} is not {REFUSAL_RECORD_TYPE}")
        if type(self.code) is not str or not _CODE.fullmatch(self.code):
            _refuse("invalid_refusal_code", f"code must match {_CODE.pattern}")
        sentence(self.message, "message")
        if self.code.replace("_", " ") in self.message.lower():
            _refuse("message_only_restates_the_code", "the message says what happened in plain words")
        if not isinstance(self.next_action, str) or not self.next_action.strip():
            _refuse("refusal_without_a_next_action", "every refusal names what to do next")
        sentence(self.next_action, "next_action")
        _member(self.next_action_by, "next_action_by", NEXT_ACTION_BY)
        _member(self.retry, "retry", RETRY_RULES)
        if self.retry_statement != RETRY_STATEMENTS[self.retry]:
            _refuse("retry_statement_does_not_match_its_rule", f"the {self.retry} rule has its own statement")
        waits = self.retry == RETRY_AFTER_WAIT
        if waits != (self.retry_after_seconds is not None) or (
                waits and (type(self.retry_after_seconds) is not int or self.retry_after_seconds <= 0)):
            _refuse("retry_wait_refused", "only a wait rule names a positive whole number of seconds")
        _member(self.effect_commitment, "effect_commitment", EFFECT_COMMITMENTS)
        if (self.effect_commitment in UNCERTAIN_EFFECTS) != (self.retry == RECONCILE_BEFORE_RETRY):
            _refuse("an_uncertain_effect_reconciles_before_any_retry",
                    "a pending or unknown effect, and only such an effect, reconciles before any retry")
        _flag(self.automatic_retry, "automatic_retry")
        if self.automatic_retry and (self.effect_commitment != EFFECT_NONE
                                     or self.retry not in (RETRY_NOW_SAME_IDENTITY, RETRY_AFTER_WAIT)):
            _refuse("automatic_retry_needs_no_effect", "only a refusal that wrote nothing is retried automatically")

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, **{name: getattr(self, name) for name in _REFUSAL_FIELDS}}

    @classmethod
    def from_dict(cls, record) -> "EnvelopeRefusal":
        value = _read(record, REFUSAL_RECORD_TYPE, _REFUSAL_FIELDS)
        return cls(**{name: value[name] for name in _REFUSAL_FIELDS})


def envelope_refusal(code: str, message: str, next_action: str, *, retry: str,
                     effect_commitment: str = EFFECT_NONE, next_action_by: str = CALLER,
                     retry_after_seconds: "int | None" = None, automatic_retry: bool = False) -> EnvelopeRefusal:
    """Build one refusal with its rule's retry statement; the record refuses anything incomplete."""
    statement = RETRY_STATEMENTS.get(retry, "") if isinstance(retry, str) else ""
    return EnvelopeRefusal(code, message, next_action, next_action_by, retry, statement, retry_after_seconds,
                           effect_commitment, automatic_retry)


_RECOVERY_FIELDS = ("component", "maximum_automatic_attempts", "recoverable_codes")


@dataclass(frozen=True)
class EnvelopeRecoveryPolicy:
    """One ``envelope_recovery_policy/v1``: which refusals an envelope may retry itself, and how often.

    A recoverable code names a failure that wrote nothing, such as a commit refused because another
    writer committed first. Zero attempts is the explicit statement that an envelope never retries."""

    component: str
    maximum_automatic_attempts: int
    recoverable_codes: tuple
    record_type: str = RECOVERY_POLICY_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != RECOVERY_POLICY_RECORD_TYPE:
            _refuse("unsupported_record_version", f"{self.record_type} is not {RECOVERY_POLICY_RECORD_TYPE}")
        _identifier(self.component, "component")
        _count(self.maximum_automatic_attempts, "maximum_automatic_attempts", 0, MAXIMUM_AUTOMATIC_ATTEMPTS)
        object.__setattr__(self, "recoverable_codes", _names(self.recoverable_codes, "recoverable_codes", _CODE))
        if self.maximum_automatic_attempts == 0 and self.recoverable_codes:
            _refuse("recovery_codes_without_attempts", "a code is recoverable only with at least one attempt")

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, **{name: _listed(getattr(self, name))
                                                     for name in _RECOVERY_FIELDS}}


class RecoveryAllowance:
    """The automatic attempts left to one request, shared by every envelope that request passes through.

    It is the only state in this module: in-memory counts, never stored and never refilled. A nested
    envelope receives the same object as its parent, so nesting cannot multiply attempts, and the count
    each component took is kept so that one envelope's own bound holds as well."""

    def __init__(self, attempts: int = MAXIMUM_AUTOMATIC_ATTEMPTS):
        self._remaining = _count(attempts, "automatic attempts", 0, MAXIMUM_AUTOMATIC_ATTEMPTS)
        self._taken: dict = {}

    @property
    def remaining(self) -> int:
        return self._remaining

    def taken_by(self, component: str) -> int:
        return self._taken.get(component, 0)

    def take(self, component: str) -> bool:
        """Spend one attempt for one component; False, and nothing spent, when none is left."""
        _identifier(component, "component")
        if self._remaining <= 0:
            return False
        self._remaining -= 1
        self._taken[component] = self._taken.get(component, 0) + 1
        return True


def may_recover(policy: EnvelopeRecoveryPolicy, refusal: EnvelopeRefusal, allowance: RecoveryAllowance) -> bool:
    """Whether the envelope may send the same step again itself, spending one shared attempt if so.

    Only a declared recoverable code whose refusal wrote nothing and allows an automatic retry qualifies,
    and only while both the policy's own count and the request's shared allowance last."""
    if not isinstance(policy, EnvelopeRecoveryPolicy) or not isinstance(refusal, EnvelopeRefusal) or not isinstance(
            allowance, RecoveryAllowance):
        _refuse("invalid_recovery_input", "recovery takes a policy, a refusal and the request's allowance")
    if (refusal.code not in policy.recoverable_codes or refusal.effect_commitment != EFFECT_NONE
            or not refusal.automatic_retry
            or allowance.taken_by(policy.component) >= policy.maximum_automatic_attempts):
        return False
    return allowance.take(policy.component)


# The nesting rule: the same envelope around each nested slot, within a depth and cost bound.

@dataclass(frozen=True)
class EnvelopeFrame:
    """Where one envelope sits for one request: the path from the first envelope, the bound and the budget.

    The deadline is the caller's monotonic clock reading at which the whole request must end; a nested
    envelope inherits it unchanged, and the allowance object itself, never fresh ones."""

    path: tuple
    maximum_depth: int
    allowance: RecoveryAllowance = field(compare=False)
    deadline_at: "float | None" = None
    record_type: str = FRAME_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != FRAME_RECORD_TYPE:
            _refuse("unsupported_record_version", f"{self.record_type} is not {FRAME_RECORD_TYPE}")
        if type(self.path) is not tuple or not self.path:
            _refuse("invalid_frame", "a frame names the path from the first envelope")
        for item in self.path:
            _identifier(item, "path")
        if len(set(self.path)) != len(self.path):
            _refuse("envelope_cycle", f"{list(self.path)} passes one component twice")
        _count(self.maximum_depth, "maximum_depth", 0, MAXIMUM_ENVELOPE_DEPTH)
        if len(self.path) - 1 > self.maximum_depth:
            _refuse("envelope_depth_exceeded", f"depth {len(self.path) - 1} is past the bound {self.maximum_depth}")
        if not isinstance(self.allowance, RecoveryAllowance):
            _refuse("invalid_frame", "a frame carries the request's recovery allowance")
        if self.deadline_at is not None and type(self.deadline_at) not in (int, float):
            _refuse("invalid_frame", "a deadline is a monotonic clock reading")

    @property
    def component(self) -> str:
        return self.path[-1]

    @property
    def depth(self) -> int:
        return len(self.path) - 1

    def remaining_seconds(self, now: float) -> "float | None":
        return None if self.deadline_at is None else max(0.0, self.deadline_at - now)

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, "path": list(self.path), "depth": self.depth,
                "maximum_depth": self.maximum_depth, "remaining_automatic_attempts": self.allowance.remaining,
                "deadline_at": self.deadline_at}


def root_frame(component: str, *, automatic_attempts: int = MAXIMUM_AUTOMATIC_ATTEMPTS,
               deadline_at: "float | None" = None, maximum_depth: int = MAXIMUM_ENVELOPE_DEPTH) -> EnvelopeFrame:
    """The frame of the first envelope a request reaches."""
    return EnvelopeFrame((component,), maximum_depth, RecoveryAllowance(automatic_attempts), deadline_at)


def enter_nested(frame: EnvelopeFrame, component: str, *, now: "float | None" = None) -> EnvelopeFrame:
    """The frame of a nested slot's envelope: one level deeper, with the parent's allowance and deadline.

    Refused before any layer runs when the slot is already on the path, when the depth bound would be
    passed, or when the inherited deadline has gone by."""
    if not isinstance(frame, EnvelopeFrame):
        _refuse("invalid_frame", "a nested envelope is entered from its parent's frame")
    _identifier(component, "component")
    if component in frame.path:
        _refuse("envelope_cycle", f"{component} is already on the path {list(frame.path)}")
    if frame.depth + 1 > frame.maximum_depth:
        _refuse("envelope_depth_exceeded", f"{component} would sit at depth {frame.depth + 1}, past the bound "
                                           f"{frame.maximum_depth}")
    if now is not None and frame.deadline_at is not None and now >= frame.deadline_at:
        _refuse("envelope_deadline_passed", f"the request's deadline passed before {component} was entered")
    return EnvelopeFrame(frame.path + (component,), frame.maximum_depth, frame.allowance, frame.deadline_at)


def nesting_depths(slots) -> dict:
    """Each catalogued slot's depth below its root, read from ``nested_under``; a cycle counts as unbounded."""
    parents = {slot.slot_id: tuple(slot.nested_under) for slot in slots}
    depths: dict = {}

    def depth(slot_id, seen):
        if slot_id in depths:
            return depths[slot_id]
        if slot_id in seen:
            return MAXIMUM_ENVELOPE_DEPTH + len(parents) + 1
        known = [name for name in parents.get(slot_id, ()) if name in parents]
        found = 0 if not known else 1 + max(depth(name, seen | {slot_id}) for name in known)
        depths[slot_id] = found
        return found
    for slot_id in parents:
        depth(slot_id, frozenset())
    return dict(sorted(depths.items()))


# The trace of one request: which inbound layers it passed, where it was refused, and whether it reached
# the engine.

@dataclass(frozen=True)
class EnvelopeTrace:
    """One ``envelope_trace/v1``. The steps follow the declared layer order; a refused or answered step is
    the last one, and such a request never reaches the engine. A request reaches the engine only after
    every inbound layer accepted it or did not apply."""

    component: str
    steps: tuple
    engine_dispatched: bool
    refused_by: str
    refusal: "EnvelopeRefusal | None"
    record_type: str = TRACE_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != TRACE_RECORD_TYPE:
            _refuse("unsupported_record_version", f"{self.record_type} is not {TRACE_RECORD_TYPE}")
        _identifier(self.component, "component")
        steps = tuple(tuple(item) for item in self.steps)
        object.__setattr__(self, "steps", steps)
        if any(len(item) != 2 for item in steps):
            _refuse("invalid_trace", "each step is one layer and its result")
        for layer, result in steps:
            _member(layer, "layer", INBOUND_LAYERS)
            _member(result, "result", LAYER_RESULTS)
        order = [INBOUND_LAYERS.index(layer) for layer, _result in steps]
        if order != sorted(set(order)):
            _refuse("envelope_layers_out_of_order", f"{[layer for layer, _result in steps]} is not the order "
                                                    f"{list(INBOUND_LAYERS)}")
        _flag(self.engine_dispatched, "engine_dispatched")
        if self.refused_by:
            _member(self.refused_by, "refused_by", REFUSAL_SOURCES)
        if (self.refusal is None) != (not self.refused_by) or (
                self.refusal is not None and not isinstance(self.refusal, EnvelopeRefusal)):
            _refuse("invalid_trace", "a refusal and its source are named together, and only together")
        endings = [(layer, result) for layer, result in steps if result in LAYER_ENDINGS]
        if endings and (len(endings) != 1 or steps[-1] != endings[0]):
            _refuse("a_refused_layer_ends_the_trace", "a refused or answered layer is the last step")
        if endings and self.engine_dispatched:
            _refuse("a_refused_request_reached_the_engine", f"{endings[0][0]} ended the request yet it was dispatched")
        refused = [layer for layer, result in endings if result == LAYER_REFUSED]
        if bool(self.refused_by and self.refused_by != ENGINE_SOURCE) != bool(refused) or (
                refused and self.refused_by != refused[0]):
            _refuse("invalid_trace", "a layer refusal names its refused step, and a refused step its refusal")
        if self.engine_dispatched and [layer for layer, _result in steps] != list(INBOUND_LAYERS):
            _refuse("the_engine_ran_before_every_layer", "every inbound layer runs before the engine")
        if self.refused_by == ENGINE_SOURCE and not self.engine_dispatched:
            _refuse("invalid_trace", "an engine refusal follows a dispatch")

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, "component": self.component,
                "steps": [{"layer": layer, "result": result} for layer, result in self.steps],
                "engine_dispatched": self.engine_dispatched, "refused_by": self.refused_by,
                "refusal": None if self.refusal is None else self.refusal.to_dict()}


def self_test() -> dict:
    """Run the envelope checks, which live in envelope_checks."""
    from .envelope_checks import self_test as run_envelope_checks
    return run_envelope_checks()
