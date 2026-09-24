"""Engine selection for any slot: one effect-free procedure, recorded before any dispatch.

Owns the typed selection request (EngineCandidate, SelectionAuthority,
EngineSelectionRequest), the check that a host policy stays within its slot
record, the eligibility screens in their fixed order, the application of Loop
and harness preferences within the sender's permitted kinds, ranking through
the existing preference boundary (the declared order always last, the matched
evidence ranking only above the slot's floor), and the assembly of one
engine_selection_decision/v2 with its selection basis (pinned, preferred or
automatic), its selection path and the digest of this request. Also owns
select_engine_as_loop (the decision made inside a deterministic Practitioner
Loop and written to the owning Loop's ledger before any dispatch),
require_prior_decision and revalidate_binding (design sections 8.2 to 8.8;
functional component standard LE-SELECT-001 to 020). Belongs to the shared
engine framework (roadmap S-6.30). Generic: a slot adds nothing here but its
own requirement screen.
Does not own: discovery or projection of engines (each slot's registry), the
attempt assessment and fallback (core.engines.fallback), dispatch, or any
permission. Selection never calls a model, starts a process, probes a
provider, accepts a task or grants authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from types import MappingProxyType

from ..configuration_capabilities import ConfigurationFact, digest
from ..configuration_preferences import (
    ExistingOrderPreference, MetaPreferencePolicy, PreferenceCandidate, PreferenceEngineBinding,
    PreferenceSelectionRequest, PreferenceSnapshot, resolve_preference)
from ..facets import EFFECTS
from ..harness_execution_contracts import ISOLATIONS, LIMITS
from ..parameter_resolution import SOURCE_PRECEDENCE, ParameterSourceKind
from .decision_records import (
    AUTOMATIC_BASIS, EVIDENCE_REORDERED_PATH, FALLBACK_AFTER_PATH, FALLBACK_PHASE, FIRST_CHOICE_PATH,
    INITIAL_PHASE, NO_CHOICE_PATH, NO_ELIGIBLE_ENGINE, OVERRIDE_PIN_PATH, OVERRIDE_PREFER_PATH, PINNED_BASIS,
    PREFERRED_BASIS, REFUSED_POLICY, SELECTED, ConsumedAuthority, EligibilityEntry, EligibilityRefusal,
    EngineSelectionDecision, EvidenceUse, FallbackTransition, PolicySource, Propensity, SelectedEngine,
    SelectionScope, UniverseEntry)
from .evidence import MATCHED_EVIDENCE_ENGINE_REF, EngineEvidenceSnapshot, MatchedEvidenceRanking, RankedCandidate
from .host_records import EngineInstallation, EngineSlotConfiguration
from .records import (
    ARCHIVED_LIFECYCLE, ARCHIVED_STAGE, DEPRECATED_LIFECYCLE, DEPRECATED_STAGE, PURE_EFFECT, QUALIFIED_STATE,
    REJECTED_LIFECYCLE, TRIAL_ONLY_LIFECYCLES, UNKNOWN, EngineDescriptor, EngineQualification, EngineRecordError,
    slot_major)
from .selection_records import (
    DECLARED_ORDER_ENGINE_REF, DECLARED_ORDER_ONLY, EXCLUDE, OBJECTIVE, PIN, PREFER, EngineSelectionOverride)
from .slots import NO_FALLBACK, EngineSlot

#: The ranking engines the release ships. Nothing else can order a slot.
RANKING_ENGINE_REFS = (MATCHED_EVIDENCE_ENGINE_REF, DECLARED_ORDER_ENGINE_REF)
RANKING_TARGET_KIND = "engine_installation"
#: The source of the release's ranking engines' facts: their checks are collected.
RANKING_FACT_SOURCE = "loop_engine.core.engines.selection_checks"
EDGE_CONTEXTS = ("engine_side", "hosted_service")
#: A path taken when no initial engine is eligible and the policy falls back on
#: an unavailable engine: the first eligible fallback, before any dispatch.
FALLBACK_BEFORE_DISPATCH = "engine_unavailable"


class EngineSelectionError(EngineRecordError):
    """A selection request that is not well formed; nothing was decided."""


@dataclass(frozen=True)
class EngineCandidate:
    """One installed engine as selection sees it: the host's installation, the
    descriptor its registry projected, and its one qualification, if any."""

    installation: EngineInstallation
    descriptor: EngineDescriptor
    qualification: "EngineQualification | None" = None

    def __post_init__(self):
        if not isinstance(self.installation, EngineInstallation) or not isinstance(self.descriptor, EngineDescriptor):
            raise EngineSelectionError("invalid_candidate", "a candidate is an installation and its descriptor")
        if self.qualification is not None and not isinstance(self.qualification, EngineQualification):
            raise EngineSelectionError("invalid_candidate", "a qualification is an EngineQualification")
        if (self.descriptor.engine_id, self.descriptor.engine_kind) != (self.installation.engine_id,
                                                                        self.installation.engine_kind):
            raise EngineSelectionError("candidate_projection_mismatch",
                                       "the descriptor names another engine or kind than the installation")

    def to_dict(self) -> dict:
        return {"installation_digest": self.installation.installation_digest,
                "enabled": self.installation.enabled, "descriptor_digest": self.descriptor.content_digest,
                "availability": _fact(self.descriptor.availability),
                "lifecycle": self.descriptor.lifecycle,
                "qualification_digest": None if self.qualification is None else self.qualification.content_digest}


def _fact(value) -> dict:
    return {"state": value.state, "source_digest": value.source_digest, "expires_at": value.expires_at}


def _names(values, name, vocabulary=None) -> tuple:
    values = tuple(values) if type(values) in (tuple, list) else None
    if values is None or len(set(values)) != len(values) or any(type(item) is not str for item in values) or (
            vocabulary is not None and not set(values) <= set(vocabulary)):
        raise EngineSelectionError("invalid_authority", f"{name} is a unique sequence of known names")
    return values


@dataclass(frozen=True)
class SelectionAuthority:
    """The owning Loop's grants and budget as eligibility reads them. Selection
    only narrows by them; nothing here is ever widened by a choice."""

    granted_effects: tuple = ()
    allowed_isolations: tuple = ()
    allowed_data_recipients: tuple = ()
    required_preemptive_limits: tuple = ()
    spending_bounded: bool = True
    allowed_engine_kinds: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, "granted_effects", _names(self.granted_effects, "granted_effects", EFFECTS))
        object.__setattr__(self, "allowed_isolations",
                           _names(self.allowed_isolations, "allowed_isolations", ISOLATIONS))
        object.__setattr__(self, "allowed_data_recipients",
                           _names(self.allowed_data_recipients, "allowed_data_recipients"))
        object.__setattr__(self, "required_preemptive_limits",
                           _names(self.required_preemptive_limits, "required_preemptive_limits", LIMITS))
        object.__setattr__(self, "allowed_engine_kinds", _names(self.allowed_engine_kinds, "allowed_engine_kinds"))
        if type(self.spending_bounded) is not bool:
            raise EngineSelectionError("invalid_authority", "spending_bounded is an explicit Boolean")

    def to_dict(self) -> dict:
        return {"granted_effects": list(self.granted_effects), "allowed_isolations": list(self.allowed_isolations),
                "allowed_data_recipients": list(self.allowed_data_recipients),
                "required_preemptive_limits": list(self.required_preemptive_limits),
                "spending_bounded": self.spending_bounded, "allowed_engine_kinds": list(self.allowed_engine_kinds)}


NO_CONSUMPTION = ConsumedAuthority(0, 0, 0, 0.0, "known", 0.0)


@dataclass(frozen=True)
class EngineSelectionRequest:
    """Everything one selection reads, as one frozen and digested object.

    ``requirement_screen`` is the slot's own requirement comparison bound to
    this request (an object with ``screen(candidate)`` returning refusals and
    ``to_dict()``); a slot without one passes None. ``attempted`` names the
    installations already tried in this sequence."""

    slot: EngineSlot
    configuration: EngineSlotConfiguration
    scope_key: str
    scope: SelectionScope
    candidates: tuple
    authority: SelectionAuthority
    edge_contract: str
    as_of: datetime
    policy_source: PolicySource
    overrides: tuple = ()
    evidence: "EngineEvidenceSnapshot | None" = None
    requirement_screen: object = None
    phase: str = INITIAL_PHASE
    transition: "FallbackTransition | None" = None
    attempted: tuple = ()
    consumed: ConsumedAuthority = NO_CONSUMPTION
    parent_decision_digest: str = ""
    binding_context: str = "engine_side"
    selection_loop_id: str = "selection.unbound"
    candidate_map: object = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.slot, EngineSlot) or not isinstance(self.configuration, EngineSlotConfiguration):
            raise EngineSelectionError("invalid_request", "a request names a typed slot and its host configuration")
        if (self.configuration.slot_id != self.slot.slot_id
                or slot_major(self.configuration.slot_version) != slot_major(self.slot.slot_version)):
            raise EngineSelectionError("slot_version_mismatch", "the host configuration names another slot or major")
        for name, kind in (("scope", SelectionScope), ("authority", SelectionAuthority),
                           ("policy_source", PolicySource), ("consumed", ConsumedAuthority)):
            if not isinstance(getattr(self, name), kind):
                raise EngineSelectionError("invalid_request", f"{name} must be a {kind.__name__}")
        if not isinstance(self.as_of, datetime) or self.as_of.tzinfo is None:
            raise EngineSelectionError("invalid_request", "as_of is a time with a timezone")
        if self.phase not in (INITIAL_PHASE, FALLBACK_PHASE) or (self.phase == FALLBACK_PHASE) != (
                self.transition is not None):
            raise EngineSelectionError("invalid_request", "a fallback request, and only one, carries its transition")
        if self.binding_context not in EDGE_CONTEXTS:
            raise EngineSelectionError("invalid_request", "the binding context is engine_side or hosted_service")
        if self.evidence is not None and not isinstance(self.evidence, EngineEvidenceSnapshot):
            raise EngineSelectionError("invalid_request", "evidence is an EngineEvidenceSnapshot or null")
        candidates = tuple(self.candidates) if type(self.candidates) in (tuple, list) else None
        if candidates is None or any(not isinstance(item, EngineCandidate) for item in candidates):
            raise EngineSelectionError("invalid_request", "candidates are EngineCandidate values")
        installed = {item.installation_id: item for item in self.configuration.installed}
        by_id = {}
        for item in candidates:
            name = item.installation.installation_id
            if name in by_id or installed.get(name) != item.installation or item.descriptor.slot_id != self.slot.slot_id:
                raise EngineSelectionError("candidate_installation_mismatch",
                                           f"{name} is offered twice, for another slot, or unlike its installation")
            by_id[name] = item
        overrides = tuple(self.overrides)
        if any(not isinstance(item, EngineSelectionOverride) for item in overrides):
            raise EngineSelectionError("invalid_request", "overrides are EngineSelectionOverride values")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "overrides", overrides)
        object.__setattr__(self, "attempted", tuple(self.attempted))
        object.__setattr__(self, "candidate_map", MappingProxyType(by_id))
        if self.requirement_screen is not None and not (callable(getattr(self.requirement_screen, "screen", None))
                                                        and callable(getattr(self.requirement_screen, "to_dict", None))):
            raise EngineSelectionError("invalid_request", "a requirement screen offers screen() and to_dict()")

    @property
    def policy(self):
        policy = self.configuration.selection.get(self.scope_key)
        if policy is None:
            raise EngineSelectionError("no_policy_for_scope_key", self.scope_key)
        return policy

    def to_dict(self) -> dict:
        """The request as data, so the decision can name exactly what the selector read."""
        return {"record_type": "engine_selection_request/v1", "slot_digest": self.slot.content_digest,
                "configuration_digest": self.configuration.content_digest, "scope_key": self.scope_key,
                "scope": self.scope.to_dict(), "candidates": {name: item.to_dict()
                                                              for name, item in sorted(self.candidate_map.items())},
                "authority": self.authority.to_dict(), "edge_contract": self.edge_contract,
                "as_of": self.as_of.isoformat(), "policy_source": self.policy_source.to_dict(),
                "overrides": [item.to_dict() for item in self.overrides],
                "evidence_digest": None if self.evidence is None else self.evidence.content_digest,
                "requirement_screen": None if self.requirement_screen is None else self.requirement_screen.to_dict(),
                "phase": self.phase, "transition": None if self.transition is None else self.transition.to_dict(),
                "attempted": list(self.attempted), "consumed": self.consumed.to_dict(),
                "parent_decision_digest": self.parent_decision_digest, "binding_context": self.binding_context}

    @property
    def request_digest(self) -> str:
        return digest(self.to_dict())


# The host policy, read against its slot record (LE-SELECT-002).

def policy_widening(slot: EngineSlot, configuration: EngineSlotConfiguration, policy) -> tuple:
    """Every way a host policy asks for more than its slot record allows; empty when it fits."""
    problems = []
    kinds = {item.installation_id: item.engine_kind for item in configuration.installed}
    if policy.fallbacks and slot.fallback_ceiling == NO_FALLBACK:
        problems.append("fallbacks declared although the slot's fallback ceiling is none")
    outside = sorted(set(policy.fallback_on) - set(slot.failure_kinds))
    if outside:
        problems.append(f"fallback_on names failure kinds the slot does not report: {outside}")
    foreign = sorted(name for name in policy.initial + policy.fallbacks if kinds.get(name) not in slot.engine_kinds)
    if foreign:
        problems.append(f"installations of kinds the slot does not declare: {foreign}")
    order = policy.ranking.engine_order
    unknown = sorted(set(order) - set(RANKING_ENGINE_REFS))
    if unknown:
        problems.append(f"ranking engines this release does not ship: {unknown}")
    wants_evidence = MATCHED_EVIDENCE_ENGINE_REF in order
    if wants_evidence != (policy.evidence is not None):
        problems.append("the matched evidence ranking and an evidence binding are declared together or not at all")
    if wants_evidence and "insufficient_evidence" not in policy.ranking.fallback_on:
        problems.append("an evidence ranking falls back to the declared order on insufficient_evidence")
    if policy.evidence is not None:
        rule = policy.evidence.rule
        if not slot.ranking_objectives:
            problems.append("evidence ranking on a slot with no ranking objectives")
        elif rule.get("objective") not in slot.ranking_objectives:
            problems.append("an evidence objective the slot does not declare")
        minimum = rule.get("minimum_matched_records")
        if slot.evidence_minimum_floor is not None and (type(minimum) is not int
                                                        or minimum < slot.evidence_minimum_floor):
            problems.append("a minimum sample below the slot's evidence floor")
    return tuple(problems)


def _refusal(code, detail="") -> EligibilityRefusal:
    return EligibilityRefusal(code, detail)


def _retirement_refusals(request, candidate, initial_listed) -> list:
    descriptor, refusals = candidate.descriptor, []
    retired = [item for item in request.policy.retired
               if item.covers(descriptor.engine_id, descriptor.engine_version)]
    if descriptor.engine_id in request.slot.retired_engines or any(
            item.stage == ARCHIVED_STAGE for item in retired):
        refusals.append(_refusal("engine_retired"))
    elif any(item.stage == DEPRECATED_STAGE for item in retired) and initial_listed:
        refusals.append(_refusal("engine_deprecated_as_initial"))
    return refusals


def _lifecycle_refusals(request, candidate, initial_listed) -> list:
    lifecycle, trial = candidate.descriptor.lifecycle, request.policy.allow_unqualified
    if lifecycle == REJECTED_LIFECYCLE:
        return [_refusal("engine_rejected")]
    if lifecycle == ARCHIVED_LIFECYCLE:
        return [_refusal("engine_retired")]
    if lifecycle in TRIAL_ONLY_LIFECYCLES and not trial:
        return [_refusal("engine_not_active", lifecycle + " outside a declared trial")]
    if lifecycle == DEPRECATED_LIFECYCLE and initial_listed:
        return [_refusal("engine_deprecated_as_initial")]
    return []


def _qualification_refusals(request, candidate) -> list:
    if request.policy.allow_unqualified:
        return []
    qualification = candidate.qualification
    if qualification is None:
        return [_refusal("engine_unqualified", "no qualification record binds this installation")]
    try:
        fact = qualification.fact_for(candidate.descriptor, candidate.installation.installation_digest,
                                      source_ref="engine_qualification:" + qualification.content_digest[:16])
    except EngineRecordError:
        return [_refusal("qualification_scope_mismatch", "bound to another descriptor or installation")]
    if qualification.scope.edge_contract != request.edge_contract:
        return [_refusal("qualification_scope_mismatch", "qualified for " + qualification.scope.edge_contract)]
    state = fact.current_state(request.as_of)
    if state == UNKNOWN:
        return [_refusal("qualification_expired")]
    return [] if state == QUALIFIED_STATE else [_refusal("engine_unqualified", "the reviewer rejected it")]


def _permission_refusals(request, candidate) -> list:
    descriptor, authority, refusals = candidate.descriptor, request.authority, []
    effects = sorted(set(descriptor.effects) - {PURE_EFFECT} - set(authority.granted_effects))
    if effects:
        refusals.append(_refusal("permission_not_granted", "effects " + ",".join(effects)))
    if authority.allowed_isolations and descriptor.isolation not in authority.allowed_isolations:
        refusals.append(_refusal("permission_not_granted", "isolation " + descriptor.isolation))
    recipients = sorted(set(descriptor.data_recipients) - set(authority.allowed_data_recipients))
    if recipients:
        refusals.append(_refusal("permission_not_granted", "data recipients " + ",".join(recipients)))
    return refusals


def _budget_refusals(request, candidate) -> list:
    descriptor, authority, refusals = candidate.descriptor, request.authority, []
    missing = sorted(set(authority.required_preemptive_limits) - set(descriptor.enforced_limits))
    if missing:
        refusals.append(_refusal("budget_requirement_unsatisfied", "preemptive limits " + ",".join(missing)))
    # cost_class is a declared adjective, never read here: only the cost basis
    # (how cost becomes known) and an enforced spend limit count.
    if (authority.spending_bounded and descriptor.cost_basis.kind == UNKNOWN
            and "cost" not in descriptor.enforced_limits):
        refusals.append(_refusal("budget_requirement_unsatisfied", "unknown cost under a bounded spending budget"))
    return refusals


def screen_candidate(request: EngineSelectionRequest, candidate: EngineCandidate) -> tuple:
    """Every refusal for one installed, enabled engine, in the fixed screen order.

    Screens remove and never reorder; every refusal is kept, not only the first."""
    descriptor, policy = candidate.descriptor, request.policy
    initial_listed = request.phase == INITIAL_PHASE and candidate.installation.installation_id in policy.initial
    refusals = _retirement_refusals(request, candidate, initial_listed)
    refusals += [item for item in _lifecycle_refusals(request, candidate, initial_listed)
                 if item.code not in {refusal.code for refusal in refusals}]
    allowed_kinds = request.authority.allowed_engine_kinds or request.slot.engine_kinds
    if descriptor.engine_kind not in request.slot.engine_kinds or descriptor.engine_kind not in allowed_kinds:
        refusals.append(_refusal("engine_kind_not_allowed"))
    if request.edge_contract not in descriptor.supported_edge_contracts:
        refusals.append(_refusal("edge_version_unsupported"))
    if descriptor.availability.current_state(request.as_of) != "available":
        refusals.append(_refusal("engine_unavailable"))
    refusals += _qualification_refusals(request, candidate)
    if request.requirement_screen is not None:
        refusals += [item for item in request.requirement_screen.screen(candidate) if item not in refusals]
    refusals += _permission_refusals(request, candidate)
    refusals += _budget_refusals(request, candidate)
    return tuple(dict.fromkeys(refusals))


# Overrides (design 8.4): only narrow or reorder eligible installations.

def _precedence(item) -> int:
    return SOURCE_PRECEDENCE[ParameterSourceKind(item.source_kind)]


def _override_problems(request, installed_ids) -> list:
    permitted = request.policy.overrides_permitted
    problems = []
    for item in request.overrides:
        if (item.slot_id, item.scope_key) != (request.slot.slot_id, request.scope_key):
            problems.append("an override names another slot or scope key")
        if item.kind not in permitted[item.sender.sender_kind]:
            problems.append(f"the host does not permit {item.sender.sender_kind} overrides of kind {item.kind}")
        if item.kind == OBJECTIVE and item.objective not in request.slot.ranking_objectives:
            problems.append("an objective the slot does not rank by")
        unknown = sorted(set(item.installations) - set(installed_ids))
        if unknown:
            problems.append(f"an override names installations the host did not install: {unknown}")
    pins = {name for item in request.overrides if item.kind == PIN for name in item.installations}
    if len(pins) > 1:
        problems.append("two pins name different installations")
    return problems


def _usable_pin(pinned, eligible, excluded) -> bool:
    """A pin serves only an eligible, unexcluded installation; nothing is substituted for it."""
    return pinned in eligible and pinned not in excluded


def _apply_overrides(request, order, eligible) -> tuple:
    """Return (order, applied overrides, pinned installation or '')."""
    applied, excluded = [], set()
    for item in sorted(request.overrides, key=_precedence):
        if item.kind == EXCLUDE:
            excluded |= set(item.installations)
            applied.append(item)
    order = tuple(name for name in order if name not in excluded)
    pins = [item for item in request.overrides if item.kind == PIN]
    if pins:
        pinned = pins[0].installations[0]
        return ((pinned,) if _usable_pin(pinned, eligible, excluded) else ()), tuple(applied) + (pins[0],), pinned
    # The highest precedence preference is applied last, so it ends in front.
    for item in sorted((item for item in request.overrides if item.kind == PREFER), key=_precedence, reverse=True):
        members = tuple(name for name in item.installations if name in order)
        if members:
            order = members + tuple(name for name in order if name not in members)
            applied.append(item if members == item.installations else replace(item, installations=members))
    applied += [item for item in request.overrides if item.kind in (DECLARED_ORDER_ONLY, OBJECTIVE)]
    return order, tuple(sorted(applied, key=lambda item: (_precedence(item), item.content_digest))), ""


# Ranking through the existing preference boundary.

def _ranking_facts(ref, as_of):
    source = digest({"ranking_engine": ref, "checks": RANKING_FACT_SOURCE})
    expiry = (as_of + timedelta(hours=1)).isoformat()
    return (ConfigurationFact("available", RANKING_FACT_SOURCE, source, expiry),
            ConfigurationFact("qualified", RANKING_FACT_SOURCE, source, expiry))


def _binding(ref, adapter, implementation, as_of) -> PreferenceEngineBinding:
    availability, qualification = _ranking_facts(ref, as_of)
    return PreferenceEngineBinding(ref, adapter, availability, (RANKING_TARGET_KIND,), implementation,
                                   digest({"implementation": implementation}), qualification)


def _rank(request, order, *, evidence_open, objective):
    """Order the declared engines; return (ranking record, evidence use)."""
    policy = request.policy
    candidates = request.candidate_map
    snapshot = PreferenceSnapshot(RANKING_TARGET_KIND, request.scope.scope_digest, tuple(
        PreferenceCandidate(name, digest_attributes(candidates[name])) for name in order))
    bindings = [_binding(DECLARED_ORDER_ENGINE_REF, ExistingOrderPreference(),
                         "loop_engine.core.configuration_preferences.ExistingOrderPreference", request.as_of)]
    ranking_policy, ranker, reason = MetaPreferencePolicy((DECLARED_ORDER_ENGINE_REF,)), None, "not_requested"
    if policy.evidence is not None and evidence_open:
        reason = "evaluation_scope_mismatch"
        if request.evidence.scope_digest == request.scope.scope_digest:
            ranker = MatchedEvidenceRanking(request.evidence, tuple(RankedCandidate(
                name, candidates[name].descriptor.engine_ref, candidates[name].installation.installation_digest)
                for name in order), scope_digest=request.scope.scope_digest, as_of=request.as_of,
                objective=objective)
            bindings.append(_binding(MATCHED_EVIDENCE_ENGINE_REF, ranker,
                                     "loop_engine.core.engines.evidence.MatchedEvidenceRanking", request.as_of))
            ranking_policy = policy.ranking
    ranking = resolve_preference(PreferenceSelectionRequest(snapshot, ranking_policy, tuple(bindings),
                                                            request.as_of))
    if ranker is None:
        snapshot_digest = None if reason == "not_requested" else request.evidence.content_digest
        return ranking, EvidenceUse(reason, False, "not_computed", snapshot_digest, (), None)
    ranked = ranking.get("selected_engine_ref") == MATCHED_EVIDENCE_ENGINE_REF
    changed = ranked and tuple(ranking["ordered_ids"]) != tuple(order)
    return ranking, EvidenceUse(
        "ranked_matched_reviewed_evidence" if ranked else "insufficient_matched_reviewed_evidence", changed,
        "not_computed", request.evidence.content_digest, ranker.used_history_refs if ranked else (), None)


def digest_attributes(candidate: EngineCandidate) -> str:
    """A ranking candidate's attributes: the exact engine and installation, nothing more."""
    from ..configuration_capabilities import canonical
    return canonical({"engine_ref": candidate.descriptor.engine_ref,
                      "installation_digest": candidate.installation.installation_digest})


# The decision.

def _binding_site(request) -> str:
    for item in request.slot.bindings:
        if item.context == request.binding_context:
            return item.binding_site
    raise EngineSelectionError("no_binding_for_context", request.binding_context)


def _universe_and_eligibility(request):
    universe, eligibility, eligible = [], [], []
    for installation in request.configuration.installed:
        name = installation.installation_id
        candidate = request.candidate_map.get(name)
        if candidate is None or not installation.enabled:
            continue
        universe.append(UniverseEntry(name, candidate.descriptor.engine_ref, candidate.descriptor.content_digest,
                                      installation.installation_digest))
        refusals = screen_candidate(request, candidate)
        eligibility.append(EligibilityEntry(name, refusals))
        if not refusals:
            eligible.append(name)
    listed = set(request.policy.initial + request.policy.fallbacks) | {
        name for item in request.overrides for name in item.installations}
    installed = {item.installation_id: item for item in request.configuration.installed}
    for name in sorted(listed - {entry.installation_id for entry in universe}):
        if name in installed and not installed[name].enabled:
            eligibility.append(EligibilityEntry(name, (_refusal("engine_disabled"),)))
        else:
            detail = ("the native registry holds no engine for this installation" if name in installed
                      else "not in the host's installations")
            eligibility.append(EligibilityEntry(name, (_refusal("engine_not_installed", detail),)))
    return tuple(universe), tuple(eligibility), tuple(eligible)


def _decision(request, universe, eligibility, **parts) -> EngineSelectionDecision:
    """Assemble one decision; every part the record requires is named here."""
    values = dict(declared_order=(), override=(), order_without_override=(), ranking=None,
                  evidence=EvidenceUse("not_requested", False, "not_computed", None, (), None), selected=None,
                  propensity=None, fallbacks=(), no_fallback=request.policy.no_fallback,
                  selection_basis=PREFERRED_BASIS, selection_path=NO_CHOICE_PATH)
    values.update(parts)
    return EngineSelectionDecision(
        slot_id=request.slot.slot_id, slot_digest=request.slot.content_digest, scope_key=request.scope_key,
        phase=request.phase, scope=request.scope, policy_digest=request.policy.content_digest,
        policy_source=request.policy_source, configuration_digest=request.configuration.content_digest,
        universe=universe, eligibility=eligibility, transition=request.transition, consumed=request.consumed,
        status=values.pop("status"), selection_loop_id=request.selection_loop_id,
        as_of=request.as_of.isoformat(), binding_site=_binding_site(request),
        parent_decision_digest=request.parent_decision_digest, request_digest=request.request_digest, **values)


def _declared_order(request, eligible) -> tuple:
    """(order, remaining fallback chain, path) before overrides and ranking.

    The initial phase starts from the policy's initial engines; when none is
    eligible and the policy falls back on an unavailable engine, the first
    eligible fallback serves before any dispatch. A fallback phase starts
    from the fallbacks not yet attempted."""
    policy, attempted = request.policy, set(request.attempted)
    chain = tuple(name for name in policy.fallbacks if name in eligible and name not in attempted)
    if request.phase == FALLBACK_PHASE:
        return chain, (), FALLBACK_AFTER_PATH + ":" + request.transition.failure_kind
    base = tuple(name for name in policy.initial if name in eligible)
    if not base and chain and FALLBACK_BEFORE_DISPATCH in policy.fallback_on:
        return chain, (), FALLBACK_AFTER_PATH + ":" + FALLBACK_BEFORE_DISPATCH
    return base, chain, FIRST_CHOICE_PATH


def select_engine(request: EngineSelectionRequest) -> EngineSelectionDecision:
    """Decide one engine for one slot and scope, with every reason, before any dispatch."""
    if not isinstance(request, EngineSelectionRequest):
        raise EngineSelectionError("invalid_request", "selection reads a typed EngineSelectionRequest")
    universe, eligibility, eligible = _universe_and_eligibility(request)
    policy = request.policy
    problems = list(policy_widening(request.slot, request.configuration, policy))
    installed = {item.installation_id for item in request.configuration.installed}
    problems += _override_problems(request, installed)
    if policy.evidence is not None and (request.evidence is None
                                        or request.evidence.content_digest != policy.evidence.snapshot_digest
                                        or request.evidence.rule.to_dict() != dict(policy.evidence.rule)):
        problems.append("the evidence snapshot is not the one the policy binds")
    refused = dict(status=REFUSED_POLICY, fallbacks=(), no_fallback=True)
    if problems:
        return _decision(request, universe, eligibility, **refused)
    if not eligible:
        return _decision(request, universe, eligibility, status=NO_ELIGIBLE_ENGINE, fallbacks=(), no_fallback=True)
    base, chain, path = _declared_order(request, eligible)
    order, applied, pinned = _apply_overrides(request, base, eligible)
    excluded = {name for item in applied if item.kind == EXCLUDE for name in item.installations}
    chain = tuple(name for name in chain if name not in excluded)
    if not order or (pinned and (request.phase != INITIAL_PHASE or path != FIRST_CHOICE_PATH)):
        # A pin to an ineligible engine, or in a fallback, refuses: nothing is substituted.
        return _decision(request, universe, eligibility, **refused)
    kinds = {item.kind for item in applied}
    objective = next((item.objective for item in applied if item.kind == OBJECTIVE), "")
    evidence_open = (not pinned and DECLARED_ORDER_ONLY not in kinds and request.phase == INITIAL_PHASE
                     and path == FIRST_CHOICE_PATH)
    ranking, evidence = (None, EvidenceUse("not_requested", False, "not_computed", None, (), None))
    if request.phase == INITIAL_PHASE:
        ranking, evidence = _rank(request, order, evidence_open=evidence_open, objective=objective)
        if ranking.get("status") != "recommended":
            return _decision(request, universe, eligibility, **refused)
        ordered = tuple(ranking["ordered_ids"])
    else:
        ordered = order
    chosen = ordered[0]
    remaining = chain if request.phase == INITIAL_PHASE and path == FIRST_CHOICE_PATH else ordered[1:]
    fallbacks = () if pinned else tuple(name for name in remaining if name != chosen)
    if request.phase == INITIAL_PHASE and path == FIRST_CHOICE_PATH:
        path = (OVERRIDE_PIN_PATH if pinned else EVIDENCE_REORDERED_PATH if evidence.changed_order
                else OVERRIDE_PREFER_PATH if PREFER in kinds and base[:1] != (chosen,) else FIRST_CHOICE_PATH)
    host_pin = (len(policy.initial) == 1 and policy.no_fallback and not evidence.used
                and policy.ranking.engine_order == (DECLARED_ORDER_ENGINE_REF,))
    basis = (AUTOMATIC_BASIS if evidence.used else PINNED_BASIS if pinned or host_pin else PREFERRED_BASIS)
    candidate = request.candidate_map[chosen]
    return _decision(
        request, universe, eligibility, status=SELECTED, declared_order=order, override=applied,
        order_without_override=base, ranking=ranking, evidence=evidence,
        selected=SelectedEngine(chosen, candidate.descriptor.engine_ref, candidate.descriptor.content_digest),
        propensity=Propensity(1, 1), fallbacks=fallbacks, no_fallback=bool(pinned) or policy.no_fallback,
        selection_basis=basis, selection_path=path)


# Recording and revalidation.

#: The existing raw event kinds a selection is recorded in, with their families:
#: the request (capability.search.started), the full decision
#: (capability.search.completed) and the bound engine (capability.selected).
#: Every refusal travels inside the decision. No new event kind is added, so
#: the event vocabulary, whose bytes the starter catalogue pins, is unchanged.
SELECTION_EVENTS = ("capability.search.started", "capability.search.completed", "capability.selected")
REQUESTED_EVENT, COMPLETED_EVENT, SELECTED_EVENT = SELECTION_EVENTS
#: The one value of the ``component`` field that marks these events as engine selection.
SELECTION_COMPONENT = "engine_selection"


def record_decision(ledger, loop_id: str, request: EngineSelectionRequest,
                    decision: EngineSelectionDecision) -> None:
    """Write the decision into the owning Loop's ledger, in the existing event families."""
    # The kinds are written as literals so the vocabulary scan can check each one.
    marker = {"component": SELECTION_COMPONENT, "slot_id": request.slot.slot_id}
    ledger.record(loop_id=loop_id, event="capability.search.started", **marker,
                  scope_digest=request.scope.scope_digest, policy_digest=request.policy.content_digest,
                  request_digest=request.request_digest)
    ledger.record(loop_id=loop_id, event="capability.search.completed", **marker, decision=decision.to_dict(),
                  decision_digest=decision.content_digest)
    if decision.selected is not None:
        ledger.record(loop_id=loop_id, event="capability.selected", **marker,
                      installation_id=decision.selected.installation_id, engine_ref=decision.selected.engine_ref,
                      decision_digest=decision.content_digest, binding_site=decision.binding_site)


def select_engine_as_loop(request: EngineSelectionRequest, *, parent=None, ledger=None) -> EngineSelectionDecision:
    """Decide inside one deterministic Practitioner Loop and record before any dispatch.

    With a parent, the selection Loop is Spawned by the owning Loop and the
    decision lands on the shared ledger; without one it is a Starting Loop."""
    from ...loop.loop_role import LoopRoleIdentity
    from ...loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
    config = LoopConfig(framework="custom", custom_steps=("select",), allowable_modes=("deterministic",),
                        preferred_modes=("deterministic",), delegated_modes=("deterministic",),
                        exit_condition="steps_complete")
    identity = LoopRoleIdentity("practitioner", "practitioner.code_execution")
    goal = f"select an eligible engine for the {request.slot.slot_id} slot"
    owner = (parent.spawn(goal, config, identity=identity) if parent is not None
             else Loop(goal, config, ledger=ledger if ledger is not None else LoopLedger(), identity=identity))
    holder = {}

    def handler(active, step, context):
        holder["decision"] = select_engine(replace(request, selection_loop_id=owner.loop_id))
        return StepOutcome(output=holder["decision"].status, mode="deterministic", confidence=1.0)

    owner.run(handler=handler, max_steps=1)
    decision = holder["decision"]
    record_decision(owner.ledger, parent.loop_id if parent is not None else owner.loop_id,
                    replace(request, selection_loop_id=owner.loop_id), decision)
    return decision


def require_prior_decision(ledger, decision_digest: str) -> dict:
    """The recorded decision a dispatch names; a dispatch without one is refused."""
    for event in reversed(getattr(ledger, "events", ())):
        if (event.get("event") == COMPLETED_EVENT and event.get("component") == SELECTION_COMPONENT
                and event.get("decision_digest") == decision_digest):
            return event["decision"]
    raise EngineSelectionError("no_prior_decision", "every dispatch names an earlier recorded selection decision")


def revalidate_binding(decision: EngineSelectionDecision, candidate: EngineCandidate) -> str:
    """Empty when the bound engine is unchanged at use; else engine_changed_after_selection."""
    if decision.selected is None:
        return "no_selected_engine"
    entry = next((item for item in decision.universe
                  if item.installation_id == decision.selected.installation_id), None)
    unchanged = (entry is not None and isinstance(candidate, EngineCandidate)
                 and candidate.installation.installation_id == entry.installation_id
                 and candidate.descriptor.engine_ref == entry.engine_ref
                 and candidate.descriptor.content_digest == entry.descriptor_digest
                 and candidate.installation.installation_digest == entry.installation_digest)
    return "" if unchanged else "engine_changed_after_selection"


def self_test():
    """Run the selection checks."""
    from .selection_checks import self_test as run_selection_checks
    return run_selection_checks()
