"""Passive selection inputs for engine slots: the host's policy and an engine preference.

Owns engine_selection_policy/v1 (a host's initial choice, ordered fallbacks
or an explicit no-fallback, ranking, evidence, permitted overrides and host
retirements, architecture 6.3) and engine_selection_override/v1 (a narrowing
preference from a Loop or a harness, with its existing ParameterSourceKind
and its sender, architecture 8.4), and the failure-kind vocabulary of
architecture 8.9. The decision these inputs lead to is
core.engines.decision_records. Belongs to the shared engine framework
(roadmap S-6.30). Never the selection procedure itself, a ranking, an
evaluator or a grant: a policy cannot enable an engine the registry does not
hold, and an override can only narrow or reorder eligible installations.
"""
from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields
from types import MappingProxyType

from ..configuration_capabilities import ConfigurationCapabilityError, digest
from ..configuration_preferences import MetaPreferencePolicy
from .records import (
    EngineRecordError, EngineRetirement, exact_engine_ref, flag, identifier, identifiers, json_object, member,
    optional, plain, read_part, read_record, sequence, sha256, slot_version, text)
from ..parameter_resolution import ParameterSourceKind

POLICY_RECORD_TYPE = "engine_selection_policy/v1"
OVERRIDE_RECORD_TYPE = "engine_selection_override/v1"
#: Records owned by the evidence records (plan package F4). A policy binds
#: their exact type and digest here; their fields are read by their own reader.
EVIDENCE_RULE_RECORD_TYPE = "engine_evidence_rule/v1"
COMPARISON_POLICY_RECORD_TYPE = "engine_comparison_policy/v1"
#: The reserved ranking engine reference that every ranking order ends with. It
#: names a binding of the existing ExistingOrderPreference (plan package F3).
DECLARED_ORDER_ENGINE_REF = "declared-order"

#: Engine failure kinds (architecture 8.9). The first five may trigger a
#: declared fallback; the terminal kinds never do.
FALLBACK_ELIGIBLE_FAILURE_KINDS = ("engine_unavailable", "capability_requirement_unsatisfied",
                                   "engine_reported_failure", "output_validation_failed",
                                   "semantic_response_rejected")
TERMINAL_FAILURE_KINDS = ("engine_changed_after_selection", "effects_uncertain", "accounting_uncertain",
                          "shared_provider_failure", "evaluation_inconclusive", "authority_exhausted",
                          "policy_refused")
EVIDENCE_OBJECTIVES = ("tokens", "elapsed_seconds", "priced_cost")

OVERRIDE_KINDS = ("pin", "exclude", "prefer", "declared_order_only", "objective")
PIN, EXCLUDE, PREFER, DECLARED_ORDER_ONLY, OBJECTIVE = OVERRIDE_KINDS
LOOP_SENDER, HARNESS_SENDER = "loop", "harness"
OVERRIDE_SENDER_KINDS = (LOOP_SENDER, HARNESS_SENDER)
#: Each sender maps to existing ParameterSourceKind values only (architecture
#: 8.4): a harness preference is output from inside an engine, untrusted data,
#: and enters at the lowest existing precedence.
SENDER_SOURCE_KINDS = MappingProxyType({
    LOOP_SENDER: (ParameterSourceKind.EXPLICIT_INVOCATION.value, ParameterSourceKind.RUN_OVERRIDE.value,
                  ParameterSourceKind.LOOP_PROFILE.value),
    HARNESS_SENDER: (ParameterSourceKind.INTELLIGENCE_PROPOSAL.value,)})
HARNESS_OVERRIDE_KINDS = (PIN, EXCLUDE, PREFER)


# Policy (architecture 6.3).

@dataclass(frozen=True)
class EngineEvidenceBinding:
    """An evidence rule plus the approved snapshot a policy ranks from."""

    rule: object
    snapshot_ref: str
    snapshot_digest: str

    def __post_init__(self):
        object.__setattr__(self, "rule", embedded_record(self.rule, "evidence rule", (EVIDENCE_RULE_RECORD_TYPE,)))
        text(self.snapshot_ref, "evidence snapshot")
        sha256(self.snapshot_digest, "evidence snapshot digest")

    def to_dict(self):
        return {"rule": plain(self.rule), "snapshot_ref": self.snapshot_ref,
                "snapshot_digest": self.snapshot_digest}

    @classmethod
    def from_dict(cls, value):
        value = read_part(value, "evidence", ("rule", "snapshot_ref", "snapshot_digest"))
        return cls(value["rule"], value["snapshot_ref"], value["snapshot_digest"])


def embedded_record(value, name, record_types):
    """An embedded record of an exact type whose fields its own reader owns."""
    value = json_object(value, name)
    member(value.get("record_type"), name + " record type", record_types)
    return value


POLICY_FIELDS = ("slot_id", "slot_version", "scope_key", "initial", "fallbacks", "no_fallback", "fallback_on",
                 "ranking", "evidence", "overrides_permitted", "comparison", "retired", "allow_unqualified")
RANKING_FIELDS = tuple(item.name for item in dataclass_fields(MetaPreferencePolicy))


@dataclass(frozen=True)
class EngineSelectionPolicy:
    """A host's declared order for one slot and scope key; it grants nothing.

    It names an initial choice and ordered fallbacks, or an explicit
    no-fallback, so missing configuration never masquerades as a deliberate
    empty set. Ranking always ends with the declared order."""

    slot_id: str
    slot_version: str
    scope_key: str
    initial: tuple[str, ...]
    fallbacks: tuple[str, ...]
    no_fallback: bool
    fallback_on: tuple[str, ...]
    ranking: MetaPreferencePolicy
    evidence: EngineEvidenceBinding | None
    overrides_permitted: object
    comparison: object
    retired: tuple[EngineRetirement, ...]
    allow_unqualified: bool

    def __post_init__(self):
        set_ = object.__setattr__
        identifier(self.slot_id, "slot_id")
        slot_version(self.slot_version, "slot_version")
        identifier(self.scope_key, "scope_key")
        set_(self, "initial", identifiers(self.initial, "initial"))
        set_(self, "fallbacks", identifiers(self.fallbacks, "fallbacks"))
        flag(self.no_fallback, "no_fallback")
        set_(self, "fallback_on", sequence(self.fallback_on, "fallback_on",
             lambda v, n: member(v, n, FALLBACK_ELIGIBLE_FAILURE_KINDS)))
        _require_explicit_fallback_choice(self)
        _refuse_repeated_listing(self)
        if not isinstance(self.ranking, MetaPreferencePolicy):
            raise EngineRecordError("invalid_field", "ranking must be a MetaPreferencePolicy")
        _require_declared_order_last(self.ranking)
        if self.evidence is not None and not isinstance(self.evidence, EngineEvidenceBinding):
            raise EngineRecordError("invalid_field", "evidence must be an EngineEvidenceBinding or null")
        set_(self, "overrides_permitted", _overrides_permitted(self.overrides_permitted))
        if self.comparison is not None:
            set_(self, "comparison", embedded_record(self.comparison, "comparison", (COMPARISON_POLICY_RECORD_TYPE,)))
        retired = tuple(self.retired) if type(self.retired) in (tuple, list) else None
        if retired is None or any(not isinstance(item, EngineRetirement) or item.slot_id != self.slot_id
                                  for item in retired):
            raise EngineRecordError("invalid_field", "retired lists this slot's engine retirements")
        if len({(item.engine_id, item.engine_version) for item in retired}) != len(retired):
            raise EngineRecordError("repeated_value", "an engine is retired once per policy")
        set_(self, "retired", retired)
        flag(self.allow_unqualified, "allow_unqualified")

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": POLICY_RECORD_TYPE, "slot_id": self.slot_id, "slot_version": self.slot_version,
                "scope_key": self.scope_key, "initial": list(self.initial), "fallbacks": list(self.fallbacks),
                "no_fallback": self.no_fallback, "fallback_on": list(self.fallback_on),
                "ranking": _ranking_dict(self.ranking),
                "evidence": None if self.evidence is None else self.evidence.to_dict(),
                "overrides_permitted": {key: list(value) for key, value in self.overrides_permitted.items()},
                "comparison": None if self.comparison is None else plain(self.comparison),
                "retired": [item.to_dict() for item in self.retired], "allow_unqualified": self.allow_unqualified}

    @classmethod
    def from_dict(cls, record) -> "EngineSelectionPolicy":
        record = read_record(record, POLICY_RECORD_TYPE, POLICY_FIELDS)
        ranking = read_part(record["ranking"], "ranking", RANKING_FIELDS)
        try:
            ranking = MetaPreferencePolicy(**{name: _as_tuple(ranking[name]) for name in RANKING_FIELDS})
        except (ConfigurationCapabilityError, TypeError) as exc:
            raise EngineRecordError("invalid_ranking_policy", str(exc)) from exc
        if type(record["retired"]) is not list:
            raise EngineRecordError("invalid_field", "retired must be a list")
        evidence = record["evidence"]
        return cls(record["slot_id"], record["slot_version"], record["scope_key"], record["initial"],
                   record["fallbacks"], record["no_fallback"], record["fallback_on"], ranking,
                   None if evidence is None else EngineEvidenceBinding.from_dict(evidence),
                   record["overrides_permitted"], record["comparison"],
                   tuple(EngineRetirement.from_dict(item) for item in record["retired"]),
                   record["allow_unqualified"])


def _as_tuple(value):
    """A serialized ranking list; text is never split into characters."""
    if type(value) is bool:
        return value
    if type(value) is not list:
        raise EngineRecordError("invalid_ranking_policy", "ranking engine lists are JSON lists")
    return tuple(value)


def _ranking_dict(ranking: MetaPreferencePolicy) -> dict:
    return {name: list(value) if type(value) is tuple else value
            for name, value in ((item, getattr(ranking, item)) for item in RANKING_FIELDS)}


def _overrides_permitted(value):
    if type(value) not in (dict, MappingProxyType) or set(value) != set(OVERRIDE_SENDER_KINDS):
        raise EngineRecordError("invalid_field", "overrides_permitted names the loop and harness senders exactly")
    permitted = {}
    for sender in OVERRIDE_SENDER_KINDS:
        allowed = HARNESS_OVERRIDE_KINDS if sender == HARNESS_SENDER else OVERRIDE_KINDS
        permitted[sender] = sequence(value[sender], "overrides permitted to " + sender,
                                     lambda v, n: member(v, n, allowed))
    return MappingProxyType(permitted)


def _require_explicit_fallback_choice(policy):
    if not policy.initial:
        raise EngineRecordError("no_fallback_rule", "a policy states an initial choice")
    if bool(policy.fallbacks) == policy.no_fallback:
        raise EngineRecordError("no_fallback_rule",
                                "state ordered fallbacks or an explicit no_fallback, exactly one of the two")
    if bool(policy.fallback_on) != bool(policy.fallbacks):
        raise EngineRecordError("no_fallback_rule",
                                "fallback_on names the failures that use the fallbacks, and is empty without them")


def _refuse_repeated_listing(policy):
    repeated = sorted(set(policy.initial) & set(policy.fallbacks))
    if repeated:
        raise EngineRecordError("engine_listed_twice", f"{repeated} appear in both initial and fallbacks")


def _require_declared_order_last(ranking):
    if not ranking.engine_order or ranking.engine_order[-1] != DECLARED_ORDER_ENGINE_REF:
        raise EngineRecordError("declared_order_last",
                                "ranking ends with declared-order, so it never abstains silently")


# Override (architecture 8.4).

@dataclass(frozen=True)
class OverrideSender:
    """Who sent an override: a Loop, or a harness attempt inside an owning Loop."""

    sender_kind: str
    loop_ref: str
    engine_ref: str | None
    attempt_ref: str | None

    def __post_init__(self):
        member(self.sender_kind, "sender kind", OVERRIDE_SENDER_KINDS)
        text(self.loop_ref, "sending or owning Loop")
        harness = self.sender_kind == HARNESS_SENDER
        for name in ("engine_ref", "attempt_ref"):
            value = getattr(self, name)
            if harness:
                (exact_engine_ref if name == "engine_ref" else text)(value, "harness " + name)
            elif value is not None:
                raise EngineRecordError("invalid_field", "a Loop sender names no engine or attempt")

    def to_dict(self):
        return {"sender_kind": self.sender_kind, "loop_ref": self.loop_ref, "engine_ref": self.engine_ref,
                "attempt_ref": self.attempt_ref}

    @classmethod
    def from_dict(cls, value):
        names = ("sender_kind", "loop_ref", "engine_ref", "attempt_ref")
        value = read_part(value, "sender", names)
        return cls(*(value[name] for name in names))


OVERRIDE_FIELDS = ("slot_id", "scope_key", "kind", "installations", "objective", "source_kind", "sender")


@dataclass(frozen=True)
class EngineSelectionOverride:
    """A typed request to pin, exclude or prefer eligible installations, or to
    keep the declared order or choose a permitted objective.

    It can only narrow or reorder eligible installations; it cannot add an
    engine, change an evaluator, raise a budget or start a comparison, because
    this record has no field that could say so."""

    slot_id: str
    scope_key: str
    kind: str
    installations: tuple[str, ...]
    objective: str | None
    source_kind: str
    sender: OverrideSender

    def __post_init__(self):
        identifier(self.slot_id, "slot_id")
        identifier(self.scope_key, "scope_key")
        member(self.kind, "override kind", OVERRIDE_KINDS)
        installations = identifiers(self.installations, "override installations")
        object.__setattr__(self, "installations", installations)
        counted = {PIN: len(installations) == 1, EXCLUDE: bool(installations), PREFER: bool(installations)}
        if not counted.get(self.kind, not installations):
            raise EngineRecordError("invalid_override", "the override kind and its installations disagree")
        if (self.kind == OBJECTIVE) != (self.objective is not None):
            raise EngineRecordError("invalid_override", "only an objective override names an objective")
        optional(self.objective, lambda v, n: member(v, n, EVIDENCE_OBJECTIVES), "objective")
        _require_override_source(self)
        _bound_sender_precedence(self)

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": OVERRIDE_RECORD_TYPE, "slot_id": self.slot_id, "scope_key": self.scope_key,
                "kind": self.kind, "installations": list(self.installations), "objective": self.objective,
                "source_kind": self.source_kind, "sender": self.sender.to_dict()}

    @classmethod
    def from_dict(cls, record) -> "EngineSelectionOverride":
        record = read_record(record, OVERRIDE_RECORD_TYPE, OVERRIDE_FIELDS)
        return cls(record["slot_id"], record["scope_key"], record["kind"], record["installations"],
                   record["objective"], record["source_kind"], OverrideSender.from_dict(record["sender"]))


_SOURCE_KIND_VALUES = tuple(kind.value for kind in ParameterSourceKind)


def _require_override_source(override):
    if type(override.source_kind) is not str or override.source_kind not in _SOURCE_KIND_VALUES:
        raise EngineRecordError("invalid_source_kind", "an override names an existing ParameterSourceKind")
    if not isinstance(override.sender, OverrideSender):
        raise EngineRecordError("sender_required", "an override names its sender")


def _bound_sender_precedence(override):
    """A sender claims only its own existing precedence; a harness also only its kinds."""
    sender = override.sender
    if override.source_kind not in SENDER_SOURCE_KINDS[sender.sender_kind]:
        raise EngineRecordError("sender_precedence_exceeded",
                                f"a {sender.sender_kind} sender cannot claim {override.source_kind}")
    if sender.sender_kind == HARNESS_SENDER and override.kind not in HARNESS_OVERRIDE_KINDS:
        raise EngineRecordError("harness_kind_not_permitted", "a harness may only prefer, exclude or pin")


def self_test():
    """Run the engine selection record checks."""
    from .selection_records_checks import self_test as run_engine_selection_record_checks
    return run_engine_selection_record_checks()
