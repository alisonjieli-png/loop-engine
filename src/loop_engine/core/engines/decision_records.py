"""The engine selection decision: the record written before any dispatch.

Owns engine_selection_decision/v1 (architecture 6.4): the slot, scope and
policy a selection used, every installed and enabled engine with its digests,
every refusal with its detail, the declared order with any override and the
order without it, the embedded ranking record, the evidence used, the
selected engine with its propensity, the fallback chain or the explicit
no-fallback, the transition and the authority already consumed. Belongs to
the shared engine framework (roadmap S-6.30). Never a dispatch, an acceptance
or a grant: its three constant flags record that no execution authority was
granted, no task was accepted and no model call was made.
"""
from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields
import re
from types import MappingProxyType

from ..configuration_capabilities import digest
from .records import (
    EngineRecordError, contract, declaration_source, exact_engine_ref, flag, identifier, identifiers, instant,
    json_object, member, optional, pattern, plain, read_part, read_record, require_derived, sequence, sha256, text)
from .selection_records import (
    EXCLUDE, FALLBACK_ELIGIBLE_FAILURE_KINDS, PIN, PREFER, TERMINAL_FAILURE_KINDS, EngineSelectionOverride,
    embedded_record)
from ..parameter_resolution import SOURCE_PRECEDENCE, ParameterResolutionTrace, ParameterSourceKind

DECISION_RECORD_TYPE = "engine_selection_decision/v1"
DECISION_PHASES = ("initial", "fallback", "reuse")
INITIAL_PHASE, FALLBACK_PHASE, REUSE_PHASE = DECISION_PHASES
DECISION_STATUSES = ("selected", "no_eligible_engine", "refused_policy", "terminal_failure")
SELECTED, NO_ELIGIBLE_ENGINE, REFUSED_POLICY, TERMINAL_FAILURE = DECISION_STATUSES
#: The embedded ranking record of the existing preference boundary; version 2
#: is the encoding it uses only when the fallback class insufficient_evidence appears.
PREFERENCE_DECISION_RECORD_TYPES = ("configuration_preference_decision/v1",
                                    "configuration_preference_decision/v2")
EVIDENCE_REASONS = ("ranked_matched_reviewed_evidence", "insufficient_matched_reviewed_evidence",
                    "evaluation_scope_mismatch", "not_requested")
NOT_REQUESTED = EVIDENCE_REASONS[3]
#: Eligibility refusal codes (architecture 8.3), plus the two codes for an
#: installation named by a policy or an override but outside the installed,
#: enabled universe.
ELIGIBILITY_REFUSAL_CODES = (
    "engine_retired", "engine_not_active", "engine_deprecated_as_initial", "engine_rejected",
    "engine_kind_not_allowed", "edge_version_unsupported", "engine_unavailable", "engine_unqualified",
    "qualification_expired", "qualification_scope_mismatch", "capability_requirement_unsatisfied",
    "permission_not_granted", "budget_requirement_unsatisfied", "incompatible_with_selected",
    "engine_disabled", "engine_not_installed")
DETAIL_REQUIRED_REFUSALS = ("capability_requirement_unsatisfied", "permission_not_granted",
                            "budget_requirement_unsatisfied", "incompatible_with_selected")
OUTSIDE_UNIVERSE_REFUSALS = ("engine_disabled", "engine_not_installed")
INCOMPATIBLE_WITH_SELECTED = DETAIL_REQUIRED_REFUSALS[3]
#: The flags every decision carries with the value False; the last keeps the
#: name configuration_preference_decision/v1 already uses.
CONSTANT_FALSE_FLAGS = ("execution_authority_granted", "task_accepted", "model_call_performed_by_boundary")
EVIDENCE_USED = EVIDENCE_REASONS[0]
NOT_COMPUTED = "not_computed"
COST_STATES = ("known", "unknown")
KNOWN_COST, UNKNOWN_COST = COST_STATES

# Scope and the decision's parts.

_PROFILE = re.compile(
    r"^(?:practitioner|intelligence|solution)\.[A-Za-z0-9_.-]+@[0-9]+\.[0-9]+\.[0-9]+$")


def _digest_map(value, name, key_rule):
    if type(value) not in (dict, MappingProxyType):
        raise EngineRecordError("invalid_field", name + " must be a mapping")
    for key, item in value.items():
        key_rule(key, name + " key")
        sha256(item, name)
    return MappingProxyType(dict(sorted(value.items())))


@dataclass(frozen=True)
class SelectionScope:
    """The exact step a decision was made for; the owning Loop is recorded but
    never fingerprinted, so evidence can match the same step in another run."""

    operation_contract_ref: str
    owning_profile_ref: str
    owning_loop_ref: str
    evaluation_contract_ref: str
    joined_settings: object
    fingerprint: object

    def __post_init__(self):
        contract(self.operation_contract_ref, "operation contract")
        pattern(self.owning_profile_ref, "owning profile", _PROFILE, "an exact role.profile@x.y.z")
        text(self.owning_loop_ref, "owning Loop")
        text(self.evaluation_contract_ref, "evaluation contract")
        object.__setattr__(self, "joined_settings", _digest_map(self.joined_settings, "joined_settings", identifier))
        object.__setattr__(self, "fingerprint", _digest_map(self.fingerprint, "fingerprint", identifier))

    def _fingerprinted(self) -> dict:
        return {"operation_contract_ref": self.operation_contract_ref,
                "owning_profile_ref": self.owning_profile_ref,
                "evaluation_contract_ref": self.evaluation_contract_ref,
                "joined_settings": dict(self.joined_settings), "fingerprint": dict(self.fingerprint)}

    @property
    def scope_digest(self) -> str:
        return digest(self._fingerprinted())

    def to_dict(self):
        return {**self._fingerprinted(), "owning_loop_ref": self.owning_loop_ref,
                "scope_digest": self.scope_digest}

    @classmethod
    def from_dict(cls, value):
        value = read_part(value, "scope", SCOPE_FIELDS)
        scope = cls(**{name: value[name] for name in SCOPE_FIELDS if name != "scope_digest"})
        require_derived(value, scope.to_dict(), ("scope_digest",))
        return scope


SCOPE_FIELDS = ("operation_contract_ref", "owning_profile_ref", "owning_loop_ref", "evaluation_contract_ref",
                "joined_settings", "fingerprint", "scope_digest")


@dataclass(frozen=True)
class PolicySource:
    """Where the policy came from, with the parameter resolution trace."""

    source: str
    trace: tuple[object, ...]

    def __post_init__(self):
        declaration_source(self.source, "policy source")
        if type(self.trace) not in (tuple, list):
            raise EngineRecordError("invalid_field", "the parameter resolution trace is a sequence")
        object.__setattr__(self, "trace", tuple(_trace_entry(item) for item in self.trace))

    def to_dict(self):
        return {"source": self.source, "trace": [plain(item) for item in self.trace]}

    @classmethod
    def from_dict(cls, value):
        value = read_part(value, "policy source", ("source", "trace"))
        return cls(value["source"], value["trace"])


TRACE_FIELDS = tuple(item.name for item in dataclass_fields(ParameterResolutionTrace))
_SOURCE_KINDS = tuple(kind.value for kind in ParameterSourceKind)


def _trace_entry(value):
    value = read_part(plain(value) if type(value) is MappingProxyType else value, "trace entry", TRACE_FIELDS)
    member(value["source_kind"], "trace source kind", _SOURCE_KINDS)
    if type(value["precedence_rank"]) is not int or any(
            type(value[name]) is not str for name in TRACE_FIELDS if name != "precedence_rank"):
        raise EngineRecordError("invalid_field", "a trace entry keeps the ParameterResolutionTrace field types")
    _refuse_claimed_precedence(value)
    return json_object(value, "trace entry")


def _refuse_claimed_precedence(entry):
    """A trace entry's rank is the existing precedence of its source kind, never a rank it claims."""
    if entry["precedence_rank"] != SOURCE_PRECEDENCE[ParameterSourceKind(entry["source_kind"])]:
        raise EngineRecordError("claimed_precedence",
                                "a trace entry's precedence rank is the one SOURCE_PRECEDENCE gives its source kind")


@dataclass(frozen=True)
class UniverseEntry:
    """One installed and enabled engine the decision considered."""

    installation_id: str
    engine_ref: str
    descriptor_digest: str
    installation_digest: str

    def __post_init__(self):
        identifier(self.installation_id, "installation_id")
        exact_engine_ref(self.engine_ref, "engine_ref")
        sha256(self.descriptor_digest, "descriptor_digest")
        sha256(self.installation_digest, "installation_digest")

    def to_dict(self):
        return {"installation_id": self.installation_id, "engine_ref": self.engine_ref,
                "descriptor_digest": self.descriptor_digest, "installation_digest": self.installation_digest}


@dataclass(frozen=True)
class EligibilityRefusal:
    """One refusal code with its detail; a parametrized code needs a detail."""

    code: str
    detail: str

    def __post_init__(self):
        member(self.code, "refusal code", ELIGIBILITY_REFUSAL_CODES)
        if type(self.detail) is not str:
            raise EngineRecordError("invalid_field", "a refusal detail is text")
        if self.code in DETAIL_REQUIRED_REFUSALS or self.detail:
            text(self.detail, "refusal detail")
        if self.code == INCOMPATIBLE_WITH_SELECTED:
            identifier(self.detail, "the slot an engine is incompatible with")

    def to_dict(self):
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class EligibilityEntry:
    """Eligible, or every refusal with its detail, for one installation."""

    installation_id: str
    refusals: tuple[EligibilityRefusal, ...]

    def __post_init__(self):
        identifier(self.installation_id, "installation_id")
        refusals = tuple(self.refusals) if type(self.refusals) in (tuple, list) else None
        if refusals is None or any(not isinstance(item, EligibilityRefusal) for item in refusals) \
                or len(set(refusals)) != len(refusals):
            raise EngineRecordError("invalid_field", "refusals are unique EligibilityRefusal values")
        object.__setattr__(self, "refusals", refusals)

    @property
    def eligible(self) -> bool:
        return not self.refusals

    def to_dict(self):
        return {"installation_id": self.installation_id, "eligible": self.eligible,
                "refusals": [item.to_dict() for item in self.refusals]}

    @classmethod
    def from_dict(cls, value):
        value = read_part(value, "eligibility entry", ("installation_id", "eligible", "refusals"))
        if type(value["refusals"]) is not list:
            raise EngineRecordError("invalid_field", "refusals must be a list")
        refusals = []
        for item in value["refusals"]:
            item = read_part(item, "refusal", ("code", "detail"))
            refusals.append(EligibilityRefusal(item["code"], item["detail"]))
        entry = cls(value["installation_id"], tuple(refusals))
        require_derived(value, entry.to_dict(), ("eligible",))
        return entry


@dataclass(frozen=True)
class EvidenceUse:
    """Whether evidence ranked this decision, why, and what it computed."""

    reason: str
    changed_order: bool
    uncertainty: object
    snapshot_digest: str | None
    history_refs: tuple[str, ...]
    heuristic_adoption_ref: str | None

    def __post_init__(self):
        member(self.reason, "evidence reason", EVIDENCE_REASONS)
        flag(self.changed_order, "changed_order")
        if self.uncertainty != NOT_COMPUTED:
            uncertainty = json_object(self.uncertainty, "uncertainty")
            if not uncertainty or any(type(v) not in (int, float) or type(v) is bool for v in uncertainty.values()):
                raise EngineRecordError("invalid_field", "uncertainty is not_computed or named numbers")
            object.__setattr__(self, "uncertainty", uncertainty)
        optional(self.snapshot_digest, sha256, "evidence snapshot digest")
        object.__setattr__(self, "history_refs", sequence(self.history_refs, "history_refs", text))
        optional(self.heuristic_adoption_ref, text, "heuristic adoption reference")
        if (self.reason == NOT_REQUESTED) != (self.snapshot_digest is None) \
                or (self.changed_order and not self.used) or (self.used and not self.history_refs) \
                or (self.reason == NOT_REQUESTED and self.history_refs):
            raise EngineRecordError("invalid_evidence_use", "the evidence reason, snapshot and order disagree")

    @property
    def used(self) -> bool:
        return self.reason == EVIDENCE_USED

    def to_dict(self):
        return {"used": self.used, "reason": self.reason, "changed_order": self.changed_order,
                "uncertainty": self.uncertainty if self.uncertainty == NOT_COMPUTED else plain(self.uncertainty),
                "snapshot_digest": self.snapshot_digest, "history_refs": list(self.history_refs),
                "heuristic_adoption_ref": self.heuristic_adoption_ref}

    @classmethod
    def from_dict(cls, value):
        names = tuple(item.name for item in dataclass_fields(cls))
        value = read_part(value, "evidence", ("used",) + names)
        use = cls(**{name: value[name] for name in names})
        require_derived(value, use.to_dict(), ("used",))
        return use


@dataclass(frozen=True)
class SelectedEngine:
    """The installation chosen, with the engine version and descriptor it names."""

    installation_id: str
    engine_ref: str
    descriptor_digest: str

    def __post_init__(self):
        identifier(self.installation_id, "installation_id")
        exact_engine_ref(self.engine_ref, "engine_ref")
        sha256(self.descriptor_digest, "descriptor_digest")

    def to_dict(self):
        return {"installation_id": self.installation_id, "engine_ref": self.engine_ref,
                "descriptor_digest": self.descriptor_digest}


@dataclass(frozen=True)
class Propensity:
    """The exact probability of this choice: 1/1 under the declared order."""

    numerator: int
    denominator: int

    def __post_init__(self):
        if type(self.numerator) is not int or type(self.denominator) is not int \
                or not 1 <= self.numerator <= self.denominator:
            raise EngineRecordError("invalid_propensity", "propensity is a fraction in (0, 1]")

    def to_dict(self):
        return {"numerator": self.numerator, "denominator": self.denominator}


@dataclass(frozen=True)
class FallbackTransition:
    """The typed failure that moved selection to a fallback, and what stays fixed."""

    previous_installation_id: str
    previous_engine_ref: str
    failure_kind: str
    attempt_loop_ref: str
    accounting_uncertain: bool
    expected_effect: str
    fixed_settings: tuple[str, ...]

    def __post_init__(self):
        identifier(self.previous_installation_id, "previous installation")
        exact_engine_ref(self.previous_engine_ref, "previous engine")
        member(self.failure_kind, "failure kind", FALLBACK_ELIGIBLE_FAILURE_KINDS + TERMINAL_FAILURE_KINDS)
        text(self.attempt_loop_ref, "attempt Loop")
        flag(self.accounting_uncertain, "accounting_uncertain")
        text(self.expected_effect, "expected effect of the change")
        object.__setattr__(self, "fixed_settings", identifiers(self.fixed_settings, "fixed settings"))

    def to_dict(self):
        return {"previous_installation_id": self.previous_installation_id,
                "previous_engine_ref": self.previous_engine_ref, "failure_kind": self.failure_kind,
                "attempt_loop_ref": self.attempt_loop_ref, "accounting_uncertain": self.accounting_uncertain,
                "expected_effect": self.expected_effect, "fixed_settings": list(self.fixed_settings)}


@dataclass(frozen=True)
class ConsumedAuthority:
    """Authority already spent and carried forward; unknown stays unknown, never zero."""

    model_calls: int | None
    input_tokens: int | None
    output_tokens: int | None
    elapsed_seconds: float | None
    cost_state: str
    cost: float | None

    def __post_init__(self):
        for name in ("model_calls", "input_tokens", "output_tokens"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise EngineRecordError("invalid_field", name + " is a count or unknown")
        for name in ("elapsed_seconds", "cost"):
            value = getattr(self, name)
            if value is not None and (type(value) not in (int, float) or not 0 <= value < float("inf")):
                raise EngineRecordError("invalid_field", name + " is finite and nonnegative, or unknown")
        member(self.cost_state, "cost state", COST_STATES)
        _keep_unknown_cost_unknown(self)

    def to_dict(self):
        return {name: getattr(self, name) for name in CONSUMED_FIELDS}


CONSUMED_FIELDS = ("model_calls", "input_tokens", "output_tokens", "elapsed_seconds", "cost_state", "cost")


def _keep_unknown_cost_unknown(consumed):
    if (consumed.cost_state == UNKNOWN_COST) != (consumed.cost is None):
        raise EngineRecordError("unknown_kept_unknown", "an unknown cost has no amount and a known cost has one")


# The decision (architecture 6.4).

DECISION_FIELDS = (
    "slot_id", "slot_digest", "scope_key", "phase", "scope", "policy_digest", "policy_source",
    "configuration_digest", "universe", "eligibility", "declared_order", "override", "order_without_override",
    "ranking", "evidence", "selected", "propensity", "fallbacks", "no_fallback", "transition", "consumed",
    "status", "selection_loop_id", "as_of", "binding_site", "parent_decision_digest") + CONSTANT_FALSE_FLAGS


@dataclass(frozen=True)
class EngineSelectionDecision:
    """One selection, fallback transition or reuse, recorded before any dispatch.

    It lists every installed and enabled engine, every refusal with its
    detail, the order with and without any override, and the propensity of
    the choice. It never grants execution authority, never accepts a task
    and never calls a model. The binding site names where the slot record
    (plan package F2) says the chosen engine is bound."""

    slot_id: str
    slot_digest: str
    scope_key: str
    phase: str
    scope: SelectionScope
    policy_digest: str
    policy_source: PolicySource
    configuration_digest: str
    universe: tuple[UniverseEntry, ...]
    eligibility: tuple[EligibilityEntry, ...]
    declared_order: tuple[str, ...]
    override: tuple[EngineSelectionOverride, ...]
    order_without_override: tuple[str, ...]
    ranking: object
    evidence: EvidenceUse
    selected: SelectedEngine | None
    propensity: Propensity | None
    fallbacks: tuple[str, ...]
    no_fallback: bool
    transition: FallbackTransition | None
    consumed: ConsumedAuthority
    status: str
    selection_loop_id: str
    as_of: str
    binding_site: str
    parent_decision_digest: str

    def __post_init__(self):
        set_ = object.__setattr__
        identifier(self.slot_id, "slot_id")
        sha256(self.slot_digest, "slot_digest")
        identifier(self.scope_key, "scope_key")
        member(self.phase, "phase", DECISION_PHASES)
        member(self.status, "status", DECISION_STATUSES)
        for name, kind in (("scope", SelectionScope), ("policy_source", PolicySource),
                           ("evidence", EvidenceUse), ("consumed", ConsumedAuthority)):
            if not isinstance(getattr(self, name), kind):
                raise EngineRecordError("invalid_field", f"{name} must be a {kind.__name__}")
        sha256(self.policy_digest, "policy_digest")
        sha256(self.configuration_digest, "configuration_digest")
        for name, kind in (("universe", UniverseEntry), ("eligibility", EligibilityEntry),
                           ("override", EngineSelectionOverride)):
            values = getattr(self, name)
            if type(values) not in (tuple, list) or any(not isinstance(item, kind) for item in values):
                raise EngineRecordError("invalid_field", f"{name} must be a sequence of {kind.__name__}")
            set_(self, name, tuple(values))
        for name in ("universe", "eligibility"):
            ids = [item.installation_id for item in getattr(self, name)]
            if len(set(ids)) != len(ids):
                raise EngineRecordError("repeated_value", name + " names each installation once")
        for name in ("declared_order", "order_without_override", "fallbacks"):
            set_(self, name, identifiers(getattr(self, name), name))
        if any(item.slot_id != self.slot_id or item.scope_key != self.scope_key for item in self.override):
            raise EngineRecordError("invalid_field", "an applied override names this slot and scope key")
        if self.ranking is not None:
            ranking = embedded_record(self.ranking, "ranking", PREFERENCE_DECISION_RECORD_TYPES)
            if any(ranking.get(name) is not False for name in CONSTANT_FALSE_FLAGS):
                raise EngineRecordError("constant_flag_changed", "the embedded ranking grants nothing either")
            set_(self, "ranking", ranking)
        for name, kind in (("selected", SelectedEngine), ("propensity", Propensity),
                           ("transition", FallbackTransition)):
            value = getattr(self, name)
            if value is not None and not isinstance(value, kind):
                raise EngineRecordError("invalid_field", f"{name} must be a {kind.__name__} or null")
        flag(self.no_fallback, "no_fallback")
        text(self.selection_loop_id, "selection Loop")
        set_(self, "as_of", instant(self.as_of, "as_of"))
        identifier(self.binding_site, "binding_site")
        if type(self.parent_decision_digest) is not str:
            raise EngineRecordError("invalid_field", "parent_decision_digest is text, empty at the top of a tree")
        if self.parent_decision_digest:
            sha256(self.parent_decision_digest, "parent_decision_digest")
        _require_complete_eligibility(self)
        _require_propensity(self)
        _refuse_widening_order(self)
        _refuse_excluded_order(self)
        _refuse_fallback_after_terminal(self)
        _require_ranking_for_an_initial_selection(self)
        self._check_consistency()

    def _check_consistency(self):
        eligible = {item.installation_id for item in self.eligibility if item.eligible}
        universe = {item.installation_id: item for item in self.universe}
        if self.no_fallback and self.fallbacks:
            raise EngineRecordError("no_fallback_rule", "an explicit no-fallback lists no fallback")
        if (self.phase == FALLBACK_PHASE) != (self.transition is not None):
            raise EngineRecordError("invalid_transition", "a fallback decision, and only one, names its transition")
        if self.status == TERMINAL_FAILURE and self.phase != FALLBACK_PHASE:
            raise EngineRecordError("invalid_transition", "a terminal failure ends a fallback sequence")
        if self.status == NO_ELIGIBLE_ENGINE and (eligible & set(universe) or self.declared_order):
            raise EngineRecordError("invalid_status", "no eligible engine means none is eligible")
        if self.selected is not None:
            entry = universe.get(self.selected.installation_id)
            if self.selected.installation_id not in eligible or entry is None \
                    or (entry.engine_ref, entry.descriptor_digest) != (self.selected.engine_ref,
                                                                      self.selected.descriptor_digest):
                raise EngineRecordError("ineligible_engine_selected", "the selected engine is eligible and listed")
            if self.selected.installation_id in self.fallbacks:
                raise EngineRecordError("invalid_field", "the selected engine is not its own fallback")
            if self.phase == INITIAL_PHASE:
                _require_first_ranked_selection(self)

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": DECISION_RECORD_TYPE, "slot_id": self.slot_id, "slot_digest": self.slot_digest,
                "scope_key": self.scope_key, "phase": self.phase, "scope": self.scope.to_dict(),
                "policy_digest": self.policy_digest, "policy_source": self.policy_source.to_dict(),
                "configuration_digest": self.configuration_digest,
                "universe": [item.to_dict() for item in self.universe],
                "eligibility": [item.to_dict() for item in self.eligibility],
                "declared_order": list(self.declared_order),
                "override": [item.to_dict() for item in self.override],
                "order_without_override": list(self.order_without_override),
                "ranking": None if self.ranking is None else plain(self.ranking),
                "evidence": self.evidence.to_dict(),
                "selected": None if self.selected is None else self.selected.to_dict(),
                "propensity": None if self.propensity is None else self.propensity.to_dict(),
                "fallbacks": list(self.fallbacks), "no_fallback": self.no_fallback,
                "transition": None if self.transition is None else self.transition.to_dict(),
                "consumed": self.consumed.to_dict(), "status": self.status,
                "selection_loop_id": self.selection_loop_id, "as_of": self.as_of,
                "binding_site": self.binding_site, "parent_decision_digest": self.parent_decision_digest,
                **{name: False for name in CONSTANT_FALSE_FLAGS}}

    @classmethod
    def from_dict(cls, record) -> "EngineSelectionDecision":
        record = read_record(record, DECISION_RECORD_TYPE, DECISION_FIELDS)
        _refuse_granting_flags(record)
        for name in ("universe", "eligibility", "override"):
            if type(record[name]) is not list:
                raise EngineRecordError("invalid_field", name + " must be a list")
        universe = tuple(UniverseEntry(**read_part(item, "universe entry", UNIVERSE_FIELDS))
                         for item in record["universe"])
        selected, propensity, transition = record["selected"], record["propensity"], record["transition"]
        return cls(
            record["slot_id"], record["slot_digest"], record["scope_key"], record["phase"],
            SelectionScope.from_dict(record["scope"]), record["policy_digest"],
            PolicySource.from_dict(record["policy_source"]), record["configuration_digest"], universe,
            tuple(EligibilityEntry.from_dict(item) for item in record["eligibility"]), record["declared_order"],
            tuple(EngineSelectionOverride.from_dict(item) for item in record["override"]),
            record["order_without_override"], record["ranking"], EvidenceUse.from_dict(record["evidence"]),
            None if selected is None else SelectedEngine(**read_part(selected, "selected", SELECTED_FIELDS)),
            None if propensity is None else Propensity(**read_part(propensity, "propensity",
                                                                  ("numerator", "denominator"))),
            record["fallbacks"], record["no_fallback"],
            None if transition is None else FallbackTransition(**read_part(transition, "transition",
                                                                          TRANSITION_FIELDS)),
            ConsumedAuthority(**read_part(record["consumed"], "consumed", CONSUMED_FIELDS)), record["status"],
            record["selection_loop_id"], record["as_of"], record["binding_site"], record["parent_decision_digest"])


UNIVERSE_FIELDS = tuple(item.name for item in dataclass_fields(UniverseEntry))
SELECTED_FIELDS = tuple(item.name for item in dataclass_fields(SelectedEngine))
TRANSITION_FIELDS = tuple(item.name for item in dataclass_fields(FallbackTransition))


def require_parent_when_nested(decision: EngineSelectionDecision, *, nested: bool) -> EngineSelectionDecision:
    """A decision made inside another engine's envelope names its parent decision.

    The selection procedure knows whether it was asked from inside an
    envelope (architecture 4.6); a nested decision without the parent's
    digest, or a top-level decision that claims a parent, is refused."""
    if not isinstance(decision, EngineSelectionDecision) or type(nested) is not bool:
        raise EngineRecordError("invalid_field", "the nesting rule reads a decision and an explicit Boolean")
    _require_parent_link(decision, nested)
    return decision


def _refuse_granting_flags(record):
    changed = [name for name in CONSTANT_FALSE_FLAGS if record[name] is not False]
    if changed:
        raise EngineRecordError("constant_flag_changed", f"a selection decision never sets {changed}")


def _require_complete_eligibility(decision):
    universe = {item.installation_id for item in decision.universe}
    listed = {item.installation_id: item for item in decision.eligibility}
    missing = sorted(universe - set(listed))
    if missing:
        raise EngineRecordError("eligibility_incomplete", f"every installed and enabled engine is screened: {missing}")
    for installation_id, entry in listed.items():
        codes = {refusal.code for refusal in entry.refusals}
        if installation_id not in universe:
            if entry.eligible or not codes <= set(OUTSIDE_UNIVERSE_REFUSALS):
                raise EngineRecordError("eligibility_incomplete",
                                        "an installation outside the universe is refused as disabled or not installed")
        elif codes & set(OUTSIDE_UNIVERSE_REFUSALS):
            raise EngineRecordError("eligibility_incomplete", "an installed, enabled engine is not disabled")


def _require_propensity(decision):
    chosen = decision.status == SELECTED
    if chosen != (decision.selected is not None) or chosen != (decision.propensity is not None):
        raise EngineRecordError("propensity_required", "a selected engine is named with its propensity, and only then")


def _refuse_widening_order(decision):
    """Only eligible members of the universe are ordered, preferred or pinned, and a pin is never substituted."""
    eligible = ({item.installation_id for item in decision.eligibility if item.eligible}
                & {item.installation_id for item in decision.universe})
    named = set(decision.declared_order) | set(decision.order_without_override) | set(decision.fallbacks)
    pins = set()
    for item in decision.override:
        if item.kind in (PIN, PREFER):
            named |= set(item.installations)
        if item.kind == PIN:
            pins |= set(item.installations)
    if not named <= eligible:
        raise EngineRecordError("ineligible_engine_ordered",
                                f"only eligible installed engines are ordered: {sorted(named - eligible)}")
    chosen = set(decision.declared_order) | set(decision.fallbacks) | (
        {decision.selected.installation_id} if decision.selected is not None else set())
    if pins and (len(pins) > 1 or not chosen <= pins):
        raise EngineRecordError("pin_substituted", "a pinned engine is never replaced by another")


def _refuse_excluded_order(decision):
    """An applied exclusion removes its installations from the order, the fallbacks and the choice;
    only the order without the override may still name them."""
    excluded = {name for item in decision.override if item.kind == EXCLUDE for name in item.installations}
    chosen = set(decision.declared_order) | set(decision.fallbacks) | (
        {decision.selected.installation_id} if decision.selected is not None else set())
    if excluded & chosen:
        raise EngineRecordError("excluded_engine_ordered",
                                f"an excluded installation is still ordered or chosen: {sorted(excluded & chosen)}")


def _require_first_ranked_selection(decision):
    """An initial choice is the first engine its embedded ranking ordered, over exactly the declared
    order. A ranking that ordered nothing (it abstained) or ordered other engines selects nothing."""
    ordered = decision.ranking.get("ordered_ids") if decision.ranking is not None else None
    ordered = list(ordered) if type(ordered) in (list, tuple) else []
    if not ordered or set(ordered) != set(decision.declared_order) \
            or ordered[0] != decision.selected.installation_id:
        raise EngineRecordError("invalid_ranking", "the first ranked eligible engine is selected")


def _refuse_fallback_after_terminal(decision):
    transition = decision.transition
    if decision.phase == FALLBACK_PHASE and decision.status == SELECTED and transition is not None and (
            transition.failure_kind not in FALLBACK_ELIGIBLE_FAILURE_KINDS or transition.accounting_uncertain):
        raise EngineRecordError("fallback_not_permitted",
                                "a fallback follows only a declared failure kind with certain accounting")


def _require_ranking_for_an_initial_selection(decision):
    """Ranking always runs for an initial choice, ending with the declared order,
    so the decision embeds that record with every ranking attempt."""
    if decision.phase == INITIAL_PHASE and decision.status == SELECTED and decision.ranking is None:
        raise EngineRecordError("ranking_required", "an initial selection embeds its ranking record")


def _require_parent_link(decision, nested):
    if nested != bool(decision.parent_decision_digest):
        raise EngineRecordError("parent_decision_required",
                                "a nested decision names its parent decision, and a top-level one names none")


def self_test():
    """Run the engine selection record checks."""
    from .selection_records_checks import self_test as run_engine_selection_record_checks
    return run_engine_selection_record_checks()
