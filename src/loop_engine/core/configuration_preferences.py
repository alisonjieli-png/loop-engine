"""Validated preference and meta-selector composition over admitted choices.

Model and harness hard screens remain in their existing selectors. This
boundary can reorder their eligible choices using existing order, explicit
priorities, host-supplied agent proposals, or a registered custom adapter.
The same contract can rank selector engines. It never grants effects or
executes a model merely because a proposal says it came from an agent.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

from .configuration_capabilities import (
    AVAILABILITY_STATES, QUALIFICATION_STATES,
    ConfigurationCapabilityError, ConfigurationFact, canonical, digest, exact_digest, exact_text)
from .record_operations_records import parse_json


@dataclass(frozen=True)
class PreferenceCandidate:
    candidate_id: str
    attributes_json: str = "{}"

    def __post_init__(self):
        exact_text(self.candidate_id, "preference candidate")
        attributes = parse_json(self.attributes_json)
        if not isinstance(attributes, dict):
            raise ConfigurationCapabilityError("candidate attributes must be a JSON object")
        object.__setattr__(self, "attributes_json", canonical(attributes))

    def to_dict(self):
        return {"candidate_id": self.candidate_id, "attributes": parse_json(self.attributes_json)}


@dataclass(frozen=True)
class PreferenceSnapshot:
    """Exact task/configuration scope and already eligible candidates."""

    target_kind: str
    scope_digest: str
    candidates: tuple[PreferenceCandidate, ...]
    version: str = "1.0.0"

    def __post_init__(self):
        exact_text(self.target_kind, "preference target kind")
        exact_digest(self.scope_digest, "preference scope digest")
        values = tuple(self.candidates)
        if (any(not isinstance(v, PreferenceCandidate) for v in values)
                or len({v.candidate_id for v in values}) != len(values) or self.version != "1.0.0"):
            raise ConfigurationCapabilityError("preference snapshot needs unique typed candidates")
        object.__setattr__(self, "candidates", values)

    @property
    def content_digest(self):
        return digest({"target_kind": self.target_kind, "scope_digest": self.scope_digest,
                       "candidates": [v.to_dict() for v in self.candidates], "version": self.version})


@dataclass(frozen=True)
class PreferenceProposal:
    """A complete proposed ordering bound to one snapshot, not an approval."""

    snapshot_digest: str
    ordered_ids: tuple[str, ...]
    producer_ref: str
    evidence_refs: tuple[str, ...] = ()
    origin: str = "deterministic"

    def __post_init__(self):
        exact_digest(self.snapshot_digest, "ranked snapshot digest")
        exact_text(self.producer_ref, "preference producer")
        for name in ("ordered_ids", "evidence_refs"):
            values = tuple(getattr(self, name))
            for value in values:
                exact_text(value, name)
            if len(set(values)) != len(values):
                raise ConfigurationCapabilityError(name + " cannot repeat")
            object.__setattr__(self, name, values)
        if self.origin not in ("deterministic", "agentic_proposal", "custom_proposal"):
            raise ConfigurationCapabilityError("unknown preference proposal origin")
        if self.origin != "deterministic" and not self.evidence_refs:
            raise ConfigurationCapabilityError("non-deterministic proposals need their source evidence references")


@dataclass(frozen=True)
class ExistingOrderPreference:
    """Keep the existing qualified selector's order."""

    def rank(self, snapshot):
        return PreferenceProposal(snapshot.content_digest,
            tuple(v.candidate_id for v in snapshot.candidates), "existing-selector-order@1.0.0")

    def descriptor(self):
        return {"method": "existing_order"}


@dataclass(frozen=True)
class ExplicitOrderPreference:
    """Prefer named eligible choices while retaining every other alternative."""

    preferred_ids: tuple[str, ...]

    def __post_init__(self):
        values = tuple(self.preferred_ids)
        if len(set(values)) != len(values):
            raise ConfigurationCapabilityError("explicit preference priorities cannot repeat")
        object.__setattr__(self, "preferred_ids", values)

    def rank(self, snapshot):
        eligible = tuple(v.candidate_id for v in snapshot.candidates)
        if set(self.preferred_ids) - set(eligible):
            raise ConfigurationCapabilityError("explicit priorities name an ineligible or unknown choice")
        ordered = self.preferred_ids + tuple(v for v in eligible if v not in self.preferred_ids)
        return PreferenceProposal(snapshot.content_digest, ordered, "explicit-preference-order@1.0.0")

    def descriptor(self):
        return {"method": "explicit_order", "preferred_ids": list(self.preferred_ids)}


@dataclass(frozen=True)
class SuppliedAgentPreference:
    """Admit a separately produced agent proposal without inventing a call."""

    proposal: PreferenceProposal

    def __post_init__(self):
        if not isinstance(self.proposal, PreferenceProposal) or self.proposal.origin != "agentic_proposal":
            raise ConfigurationCapabilityError("agent preference needs a typed agentic proposal")

    def rank(self, snapshot):
        return self.proposal

    def descriptor(self):
        return {"method": "supplied_agent_proposal", "proposal_digest": digest(asdict(self.proposal))}


@dataclass(frozen=True)
class PreferenceEngineBinding:
    """One host-registered adapter binding, not a parallel engine registry."""

    engine_ref: str
    adapter: object = field(repr=False)
    availability: ConfigurationFact
    target_kinds: tuple[str, ...]
    implementation_ref: str
    implementation_digest: str
    qualification: ConfigurationFact = ConfigurationFact()
    descriptor_json: str = field(init=False)

    def __post_init__(self):
        exact_text(self.engine_ref, "preference engine")
        exact_text(self.implementation_ref, "preference implementation")
        exact_digest(self.implementation_digest, "preference implementation digest")
        if not all(callable(getattr(self.adapter, name, None)) for name in ("rank", "descriptor")):
            raise ConfigurationCapabilityError("preference adapter must implement rank and descriptor")
        if (not isinstance(self.availability, ConfigurationFact)
                or self.availability.state not in AVAILABILITY_STATES):
            raise ConfigurationCapabilityError("preference availability needs its separate fact state")
        if (not isinstance(self.qualification, ConfigurationFact)
                or self.qualification.state not in QUALIFICATION_STATES):
            raise ConfigurationCapabilityError("preference qualification needs its separate fact state")
        kinds = tuple(self.target_kinds)
        if not kinds or len(set(kinds)) != len(kinds):
            raise ConfigurationCapabilityError("preference adapter target kinds must be explicit")
        for kind in kinds:
            exact_text(kind, "preference target kind")
        object.__setattr__(self, "target_kinds", kinds)
        object.__setattr__(self, "descriptor_json", canonical(self.adapter.descriptor()))

    def to_dict(self):
        return {"engine_ref": self.engine_ref, "target_kinds": list(self.target_kinds),
            "implementation_ref": self.implementation_ref, "implementation_digest": self.implementation_digest,
            "configuration": parse_json(self.descriptor_json), "availability": asdict(self.availability),
            "qualification": asdict(self.qualification)}


@dataclass(frozen=True)
class MetaPreferencePolicy:
    """Initial engine and ordered fallbacks; no unbounded selector recursion."""

    engine_order: tuple[str, ...]
    fallback_on: tuple[str, ...] = ()
    active_engine_refs: tuple[str, ...] = ()
    allow_unqualified: bool = False

    def __post_init__(self):
        for name in ("engine_order", "fallback_on", "active_engine_refs"):
            values = tuple(getattr(self, name))
            if len(set(values)) != len(values):
                raise ConfigurationCapabilityError(name + " cannot repeat")
            for value in values:
                exact_text(value, name)
            object.__setattr__(self, name, values)
        if (not self.engine_order or not set(self.fallback_on)
                <= {"engine_unavailable", "engine_unqualified", "target_kind_unsupported", "engine_failed", "invalid_proposal"}
                or type(self.allow_unqualified) is not bool):
            raise ConfigurationCapabilityError("meta preference policy needs an order and known failure classes")


@dataclass(frozen=True)
class PreferenceSelectionRequest:
    snapshot: PreferenceSnapshot
    policy: MetaPreferencePolicy
    engines: tuple[PreferenceEngineBinding, ...]
    as_of: datetime

    def __post_init__(self):
        values = tuple(self.engines)
        if (not isinstance(self.snapshot, PreferenceSnapshot) or not isinstance(self.policy, MetaPreferencePolicy)
                or any(not isinstance(v, PreferenceEngineBinding) for v in values)
                or len({v.engine_ref for v in values}) != len(values)
                or not isinstance(self.as_of, datetime) or self.as_of.tzinfo is None):
            raise ConfigurationCapabilityError("preference selection requires typed scope, bindings, policy, and time")
        object.__setattr__(self, "engines", values)


def resolve_preference(request: PreferenceSelectionRequest) -> dict:
    """Reorder eligible choices and record every failed engine attempt."""
    if not isinstance(request, PreferenceSelectionRequest):
        raise ConfigurationCapabilityError("preference request must be typed")
    engines = {v.engine_ref: v for v in request.engines}
    ids = tuple(v.candidate_id for v in request.snapshot.candidates)
    result = {"record_type": "configuration_preference_decision/v1",
        "snapshot_digest": request.snapshot.content_digest, "target_kind": request.snapshot.target_kind,
        "scope_digest": request.snapshot.scope_digest, "as_of": request.as_of.isoformat(),
        "eligible_candidates": [v.to_dict() for v in request.snapshot.candidates],
        "ordered_ids": [], "selected_engine_ref": "", "attempts": [],
        "policy": asdict(request.policy), "engines": [v.to_dict() for v in request.engines],
        "status": "abstained", "model_call_performed_by_boundary": False,
        "execution_authority_granted": False, "task_accepted": False}
    if not ids:
        result["status"] = "no_eligible_choices"
        return result
    for name in request.policy.engine_order:
        engine, reason, proposal = engines.get(name), "", None
        if name in request.policy.active_engine_refs:
            reason = "selector_cycle"
        elif engine is None or engine.availability.current_state(request.as_of) != "available":
            reason = "engine_unavailable"
        elif not request.policy.allow_unqualified and engine.qualification.current_state(request.as_of) != "qualified":
            reason = "engine_unqualified"
        elif request.snapshot.target_kind not in engine.target_kinds:
            reason = "target_kind_unsupported"
        else:
            try:
                if canonical(engine.adapter.descriptor()) != engine.descriptor_json:
                    raise ConfigurationCapabilityError("preference configuration changed after binding")
                proposal = engine.adapter.rank(request.snapshot)
                if canonical(engine.adapter.descriptor()) != engine.descriptor_json:
                    raise ConfigurationCapabilityError("preference configuration changed during ranking")
            except Exception:
                reason = "engine_failed"
            if not reason and (not isinstance(proposal, PreferenceProposal)
                    or proposal.snapshot_digest != request.snapshot.content_digest
                    or len(proposal.ordered_ids) != len(ids) or set(proposal.ordered_ids) != set(ids)):
                reason = "invalid_proposal"
        result["attempts"].append({"engine_ref": name, "result": reason or "valid_ordering"})
        if reason:
            if reason not in request.policy.fallback_on:
                break
            continue
        result.update(status="recommended", selected_engine_ref=name,
                      ordered_ids=list(proposal.ordered_ids), proposal=asdict(proposal))
        break
    return result


def resolve_preference_as_loop(request: PreferenceSelectionRequest, *, parent=None):
    from ..loop.encapsulate import as_practitioner_loop
    return as_practitioner_loop("resolve a capability-constrained preference",
                                lambda: resolve_preference(request), parent=parent)


def self_test():
    from .configuration_preference_checks import run_checks
    return run_checks()
