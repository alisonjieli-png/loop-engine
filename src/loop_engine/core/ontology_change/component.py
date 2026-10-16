"""The envelope of ontology change planning: read, bind, select, dispatch, check and write the plan.

```text
plan_change(request, host)
├── read: ontology_change_request/v1 strictly; the ontology parsed; its digest must equal the request's
│   base_digest (base_digest_mismatch, before any engine runs); every removed triple held by the base
│   and no added triple already held (change_invalid)
├── select: every installed engine screened (enabled, available, profile and blank-node capability, a
│   passing conformance report for its exact descriptor when the host requires evidence), then the
│   declared order of engine_selection_policy/v1, recorded as engine_selection_decision/v1 before dispatch
├── dispatch: one engine; a declared failure kind moves to the next eligible engine with a fallback
│   decision; a closure past the bound stops the request
├── check: both closures hold their asserted graphs, every derived triple has a derivation, and the
│   trace of every listed new or lost consequence is accepted by the independent trace checker
└── write: ontology_change_plan/v1 bound to the base and proposed digests, with plan_digest
```

The envelope layers (docs/architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md) are recorded on the outcome,
``ontology_change_outcome/v2``: the read is the carrier layer, the screen gives one handshake verdict for
each installation, the account and tracking layers do not apply to planning, the preflight checks the
selected engine again just before each dispatch, and every failure carries its envelope refusal with the
next action and the retry rule. The trace records which layers the request passed.

The plan is a proposal; it changes nothing. Apply and rollback are in
``store.py`` and need an approval naming this plan's digest.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import lru_cache
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping

from ..configuration_capabilities import ConfigurationFact, digest
from ..configuration_preferences import (
    ExistingOrderPreference, MetaPreferencePolicy, PreferenceCandidate, PreferenceEngineBinding,
    PreferenceSelectionRequest, PreferenceSnapshot, resolve_preference)
from ..engines.decision_records import (
    ConsumedAuthority, EligibilityEntry, EligibilityRefusal, EngineSelectionDecision, EvidenceUse,
    FallbackTransition, PolicySource, Propensity, SelectedEngine, SelectionScope, UniverseEntry)
from ..engines.envelope import (
    ENGINE_SOURCE, LAYER_ACCEPTED, LAYER_ACCOUNT, LAYER_CARRIER, LAYER_HANDSHAKE, LAYER_NOT_APPLICABLE,
    LAYER_PREFLIGHT, LAYER_REFUSED, LAYER_TRACKING, REFUSED_BY_POLICY, EnvelopeTrace)
from ..engines.envelope_preflight import run_preflight
from ..engines.selection_records import DECLARED_ORDER_ENGINE_REF
from ..engines.slots import load_engine_slot_catalog
from . import engines as table
from .contract import (
    CLOSURE_CEILING, CONSERVATIVE, NOT_CONSERVATIVE, PLAN_FIELDS, PLAN_RECORD_TYPE, REQUEST_RECORD_TYPE,
    RULE_TABLES, SLOT_ID, EngineFailure, OntologyChangeRefused, PlanningInput, PlanRequest, plan_digest,
    triples_list)
from .guidance import PREFLIGHT_CHECKS, handshake_for, refusal_for
from .rdf_terms import VOCABULARY_NAMESPACES, RdfSyntaxError, graph_digest, is_iri, parse_graph, user_terms, writable
from .trace_checker import check_trace

DEFAULT_PROFILE_REF = "practitioner.code_execution@1.0.0"
OUTCOME_RECORD_TYPE = "ontology_change_outcome/v2"
#: The effects a host grants the engines of this slot unless it states otherwise: what the two declared
#: engines need, which is the behaviour before the handshake layer named it. A host narrows the grant to
#: refuse the adapter by policy; a Loop that owns the slot will grant from its own authority instead.
HOST_GRANTED_EFFECTS = tuple(sorted({effect for item in table.DECLARED_ENGINES for effect in item.effects}))
#: The inbound layers that do not apply to planning: no account reaches the slot, and a plan changes
#: nothing, so there is no effect to journal, replay or reconcile.
_NOT_APPLICABLE_TO_PLANNING = (LAYER_ACCOUNT, LAYER_TRACKING)
MAXIMUM_TRACE_STEPS = 10_000
_SEQUENCE_FAILURES = {"engine_unavailable": "engine_unavailable", "engine_reported_failure": "engine_failed",
                      "capability_requirement_unsatisfied": "engine_unavailable"}


@dataclass(frozen=True)
class SelectionContext:
    """Who asked: the owning profile and Loop recorded in every selection decision."""

    owning_profile_ref: str = DEFAULT_PROFILE_REF
    owning_loop_ref: str = "ontology_change.direct_call"


@dataclass(frozen=True)
class HostEngines:
    """A host's engines for this slot: installations, the declared order, and the recorded evidence."""

    installations: tuple
    policy: object
    evidence: Mapping = field(default_factory=dict)
    require_evidence: bool = True
    policy_source: str = "projected:core.ontology_change.engines.DECLARED_ORDER"
    granted_effects: tuple = HOST_GRANTED_EFFECTS


def default_host(binary_path=None, *, evidence=None, require_evidence: bool = True, work_root=None) -> HostEngines:
    """Both engines installed in the declared order; evidence maps descriptor digests to kit reports."""
    return HostEngines(table.default_installations(binary_path, work_root=work_root), table.default_policy(),
                       MappingProxyType(dict(evidence or {})), require_evidence)


@dataclass(frozen=True)
class PlanOutcome:
    """The plan or one failure, every selection decision, and what each envelope layer recorded.

    A failure carries its envelope refusal (code, what happened, next action and retry rule); the
    handshake holds one verdict for each screened installation and the preflight one report for each
    dispatch. The trace records the layers of the final attempt; an earlier attempt that fell back is
    recorded by its fallback decision and its own preflight report."""

    plan: "dict | None"
    failure: "dict | None"
    decisions: tuple = ()
    refusal: "dict | None" = None
    handshake: tuple = ()
    preflight: tuple = ()
    trace: "dict | None" = None

    def to_dict(self) -> dict:
        return {"record_type": OUTCOME_RECORD_TYPE, "plan": self.plan, "failure": self.failure,
                "refusal": self.refusal, "decisions": list(self.decisions), "handshake": list(self.handshake),
                "preflight": list(self.preflight), "trace": self.trace}


def read_request(request) -> tuple:
    """(PlanRequest, base graph, proposed graph), or OntologyChangeRefused naming what is wrong."""
    plan_request = PlanRequest.from_dict(request)
    try:
        base = parse_graph(plan_request.ontology_text, plan_request.ontology_format,
                           maximum_triples=CLOSURE_CEILING)
    except RdfSyntaxError as error:
        raise OntologyChangeRefused("unsupported_syntax", str(error)) from None
    if len(base) > plan_request.maximum_closure:
        raise OntologyChangeRefused("limit_exceeded", f"the ontology holds {len(base)} triples, more than the "
                                                      f"closure bound {plan_request.maximum_closure}")
    found = graph_digest(base)
    if found != plan_request.base_digest:
        raise OntologyChangeRefused("base_digest_mismatch",
                                    f"the ontology's digest is {found}, the request names {plan_request.base_digest}")
    missing = [triple for triple in plan_request.removed if triple not in base]
    present = [triple for triple in plan_request.added if triple in base]
    if missing:
        raise OntologyChangeRefused("change_invalid", f"removes a triple the base does not hold: {missing[0]}")
    if present:
        raise OntologyChangeRefused("change_invalid", f"adds a triple the base already holds: {present[0]}")
    proposed = (base - set(plan_request.removed)) | set(plan_request.added)
    return plan_request, base, frozenset(proposed)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _instant(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


@lru_cache(maxsize=1)
def _slot_digest() -> str:
    for slot in load_engine_slot_catalog().slots:
        if slot.slot_id == SLOT_ID:
            return slot.content_digest
    return digest({"slot_id": SLOT_ID, "state": "not_catalogued"})


def _screen(host: HostEngines, planning_input: PlanningInput, now: datetime) -> tuple:
    """(universe, eligibility, descriptors, engines, handshake verdicts) for every installation of the host.

    Each enabled installation gets one handshake verdict from its declaration and the host's granted
    effects; a verdict refused by policy is also an eligibility refusal, so an engine whose effects the
    host does not grant is never selected."""
    universe, eligibility, descriptors, engines, verdicts = [], [], {}, {}, []
    for installation in host.installations:
        if not installation.enabled:
            eligibility.append(EligibilityEntry(installation.installation_id,
                                                (EligibilityRefusal("engine_disabled", ""),)))
            continue
        engine = table.create_engine(installation.engine_id, installation.settings)
        descriptor = table.describe_engine(installation.engine_id, installation.settings, now=now)
        engines[installation.installation_id], descriptors[installation.installation_id] = engine, descriptor
        universe.append(UniverseEntry(installation.installation_id, descriptor.engine_ref, descriptor.content_digest,
                                      installation.installation_digest))
        refusals = []
        available, reason = engine.availability()
        if not available:
            refusals.append(EligibilityRefusal("engine_unavailable", reason[:300]))
        for need in table.unmet_requirements(engine.declaration, planning_input):
            refusals.append(EligibilityRefusal("capability_requirement_unsatisfied", need))
        verdict = handshake_for(installation, engine.declaration, descriptor, planning_input, host.granted_effects)
        verdicts.append(verdict)
        if verdict.verdict == REFUSED_BY_POLICY:
            refusals.append(EligibilityRefusal("permission_not_granted", "; ".join(verdict.reasons)[:300]))
        report = host.evidence.get(descriptor.content_digest)
        if host.require_evidence and not (isinstance(report, dict) and report.get("passed") is True):
            refusals.append(EligibilityRefusal(
                "capability_requirement_unsatisfied",
                f"conformance_kit: no passing ontology_change conformance report for descriptor "
                f"{descriptor.content_digest}"))
        eligibility.append(EligibilityEntry(installation.installation_id, tuple(refusals)))
    return tuple(universe), tuple(eligibility), descriptors, engines, tuple(verdicts)


def _ranking(order: tuple, now: datetime) -> dict:
    """The declared-order ranking record of the existing preference boundary over ``order``."""
    available = ConfigurationFact("available", "core.ontology_change.component:declared_order",
                                  digest("declared order ranking"), "")
    # The declared order is the identity ordering of the existing preference boundary, held qualified the way
    # the shared engine records' own checks hold it; it reorders nothing.
    qualified = ConfigurationFact("qualified", "core.configuration_preferences:ExistingOrderPreference",
                                  digest("existing order is the declared order"), "")
    binding = PreferenceEngineBinding(
        DECLARED_ORDER_ENGINE_REF, ExistingOrderPreference(), available, ("engine_installation",),
        "loop_engine.core.configuration_preferences.ExistingOrderPreference", digest("existing order"), qualified)
    snapshot = PreferenceSnapshot("engine_installation", digest({"slot": SLOT_ID, "order": list(order)}),
                                  tuple(PreferenceCandidate(item) for item in order))
    return resolve_preference(PreferenceSelectionRequest(
        snapshot, MetaPreferencePolicy((DECLARED_ORDER_ENGINE_REF,)), (binding,), now))


class _Selector:
    """Records one decision before each dispatch, over one screening of the host's engines."""

    def __init__(self, host: HostEngines, planning_input: PlanningInput, context: SelectionContext):
        self.host, self.context, self.now = host, context, _now()
        self.universe, self.eligibility, self.descriptors, self.engines, self.verdicts = _screen(
            host, planning_input, self.now)
        eligible = {entry.installation_id for entry in self.eligibility if entry.eligible}
        policy = host.policy
        self.declared = tuple(item for item in policy.initial if item in eligible) or tuple(
            item for item in policy.fallbacks if item in eligible)[:1]
        self.fallbacks = tuple(item for item in policy.fallbacks if item in eligible and item not in self.declared)
        self.sequence = self.declared[:1] + self.fallbacks
        self.decisions: list = []

    def _record(self, **fields) -> EngineSelectionDecision:
        settings = {item.installation_id: item.settings_digest for item in self.host.installations}
        base = dict(
            slot_id=SLOT_ID, slot_digest=_slot_digest(), scope_key="default",
            scope=SelectionScope(REQUEST_RECORD_TYPE, self.context.owning_profile_ref, self.context.owning_loop_ref,
                                 PLAN_RECORD_TYPE, {}, {"execution_settings": digest(settings)}),
            policy_digest=self.host.policy.content_digest,
            policy_source=PolicySource(self.host.policy_source, ({
                "source_kind": "repository_default", "source_ref": "core.ontology_change.engines.DECLARED_ORDER",
                "source_version": table.SLOT_VERSION, "precedence_rank": 7, "requested_state": "PROVIDED",
                "disposition": "SELECTED", "reason": "the slot's declared order, unless the host states another"},)),
            configuration_digest=digest([item.to_dict() for item in self.host.installations]),
            universe=self.universe, eligibility=self.eligibility, declared_order=self.declared, override=(),
            order_without_override=self.declared, evidence=EvidenceUse("not_requested", False, "not_computed", None,
                                                                      (), None),
            no_fallback=self.host.policy.no_fallback, selection_loop_id=self.context.owning_loop_ref + ".selection",
            as_of=_instant(self.now), binding_site="runtime_context_internal", parent_decision_digest="")
        base.update(fields)
        decision = EngineSelectionDecision(**base)
        self.decisions.append(decision.to_dict())
        return decision

    def _selected(self, installation_id: str) -> SelectedEngine:
        descriptor = self.descriptors[installation_id]
        return SelectedEngine(installation_id, descriptor.engine_ref, descriptor.content_digest)

    def first(self) -> "str | None":
        if not self.sequence:
            eligible = any(entry.eligible for entry in self.eligibility)
            self._record(phase="initial", ranking=None, selected=None, propensity=None, fallbacks=(),
                         transition=None, consumed=ConsumedAuthority(0, 0, 0, 0.0, "known", 0.0),
                         status="refused_policy" if eligible else "no_eligible_engine", declared_order=(),
                         order_without_override=())
            return None
        ranking = _ranking(self.declared, self.now)
        chosen = ranking["ordered_ids"][0]
        self._record(phase="initial", ranking=ranking, selected=self._selected(chosen), propensity=Propensity(1, 1),
                     fallbacks=self.fallbacks, transition=None, status="selected",
                     consumed=ConsumedAuthority(0, 0, 0, 0.0, "known", 0.0))
        return chosen

    def after_failure(self, previous: str, kind: str, elapsed: float) -> "str | None":
        position = self.sequence.index(previous) + 1
        if kind not in self.host.policy.fallback_on or position >= len(self.sequence):
            return None
        chosen = self.sequence[position]
        transition = FallbackTransition(previous, self.descriptors[previous].engine_ref, kind,
                                        self.context.owning_loop_ref + ".attempt", False,
                                        "the same planning input goes to the next declared engine",
                                        ("execution_settings",))
        self._record(phase="fallback", ranking=None, selected=self._selected(chosen), propensity=Propensity(1, 1),
                     fallbacks=self.sequence[position + 1:], transition=transition, status="selected",
                     consumed=ConsumedAuthority(0, 0, 0, round(elapsed, 3), "known", 0.0))
        return chosen

    def refusal_summary(self) -> str:
        return "; ".join(f"{entry.installation_id}: " + ", ".join(
            f"{refusal.code} {refusal.detail}".strip() for refusal in entry.refusals)
            for entry in self.eligibility if entry.refusals)[:400]


def trace_for(conclusion, derivations, asserted) -> list:
    """The steps that derive ``conclusion`` from ``asserted``, premises before conclusions."""
    steps, done, active, stack = [], set(), set(), [(tuple(conclusion), False)]
    while stack:
        triple, expanded = stack.pop()
        if expanded:
            active.discard(triple)
            done.add(triple)
            rule, premises = derivations[triple]
            steps.append({"rule": rule, "conclusion": list(triple), "premises": [list(item) for item in premises]})
            if len(steps) > MAXIMUM_TRACE_STEPS:
                raise ValueError(f"a trace passes {MAXIMUM_TRACE_STEPS} steps")
            continue
        if triple in asserted or triple in done:
            continue
        if triple in active:
            raise ValueError("the derivations hold a cycle")
        if triple not in derivations:
            raise ValueError(f"no derivation for {triple}")
        active.add(triple)
        stack.append((triple, True))
        stack.extend((tuple(premise), False) for premise in reversed(derivations[triple][1]))
    return steps


def _bounded(items, limit: int) -> dict:
    ordered = sorted(items)
    return {"count": len(ordered), "listed": [list(item) if isinstance(item, tuple) else item
                                              for item in ordered[:limit]], "truncated": len(ordered) > limit}


def _admit(outcome, plan_request: PlanRequest, base: frozenset, proposed: frozenset, descriptor) -> dict:
    """The plan, or ValueError naming why the engine's outcome cannot be admitted."""
    table_used = RULE_TABLES[plan_request.profile]
    if outcome.engine_ref != descriptor.engine_ref or tuple(outcome.rule_table) != table_used:
        raise ValueError("the outcome names another engine or rule table")
    for name, asserted, closure, derivations in (("base", base, outcome.base_closure, outcome.base_derivations),
                                                 ("proposed", proposed, outcome.proposed_closure,
                                                  outcome.proposed_derivations)):
        if not asserted <= closure:
            raise ValueError(f"the {name} closure does not hold its asserted graph")
        if len(closure) > plan_request.maximum_closure or not all(writable(item) for item in closure):
            raise ValueError(f"the {name} closure is unbounded or holds a triple RDF cannot write")
        if not (closure - asserted) <= set(derivations):
            raise ValueError(f"a derived {name} triple has no derivation")
    added, removed = set(plan_request.added), set(plan_request.removed)
    new = outcome.proposed_closure - outcome.base_closure - added
    lost = outcome.base_closure - outcome.proposed_closure - removed
    signature = {term for triple in base for term in triple}

    def known(term: str) -> bool:
        return term in signature or (is_iri(term) and term[1:].startswith(VOCABULARY_NAMESPACES))

    over_signature = [triple for triple in new if all(known(term) for term in triple)]
    limit, traces, checked = plan_request.maximum_listed, {"new": [], "lost": []}, 0
    for kind, triples, graph, derivations in (("new", new, proposed, outcome.proposed_derivations),
                                              ("lost", lost, base, outcome.base_derivations)):
        for triple in sorted(triples)[:limit]:
            steps = trace_for(triple, derivations, graph)
            verdict = check_trace(graph, steps, rule_table=table_used)
            if not verdict.ok or not steps or tuple(steps[-1]["conclusion"]) != triple:
                raise ValueError(f"the trace of {kind} {triple} is refused: {verdict.reason}")
            checked += 1
            traces[kind].append({"conclusion": list(triple), "steps": steps})
    affected = {term for triple in (*added, *removed, *new, *lost) for term in user_terms(triple)}
    touched = []
    for term in plan_request.locked_terms:
        how = [label for label, triples in (("asserted", (*added, *removed)), ("entailed", (*new, *lost)))
               if any(term in triple for triple in triples)]
        if how:
            touched.append({"term": term, "how": how})
    plan = {
        "record_type": PLAN_RECORD_TYPE, "base_digest": plan_request.base_digest,
        "proposed_digest": graph_digest(proposed),
        "profile": plan_request.profile, "rule_table": list(table_used),
        "engine": {"engine_ref": descriptor.engine_ref, "descriptor_digest": descriptor.content_digest},
        "change": {"added": triples_list(added), "removed": triples_list(removed)},
        "asserted": {"added": len(added), "removed": len(removed)},
        "entailed": {"new": {**_bounded(new, limit), "over_base_signature": len(over_signature)},
                     "lost": _bounded(lost, limit)},
        "affected_terms": _bounded(affected, limit),
        "locks": {"checked": list(plan_request.locked_terms), "touched": touched},
        "verdict": NOT_CONSERVATIVE if over_signature or lost else CONSERVATIVE,
        "closure": {"base": len(outcome.base_closure), "proposed": len(outcome.proposed_closure)},
        "traces": {"included": plan_request.include_traces, "checked": checked,
                   "checker": "core.ontology_change.trace_checker",
                   "new": traces["new"] if plan_request.include_traces else [],
                   "lost": traces["lost"] if plan_request.include_traces else []},
    }
    plan["plan_digest"] = plan_digest(plan)
    if tuple(plan) != PLAN_FIELDS:
        raise ValueError("the plan's fields drifted from the contract")
    return plan


def _trace(refused_by: str, refusal, *, dispatched: bool, preflight_result: str = LAYER_ACCEPTED) -> dict:
    """The envelope trace of one planning request, in the declared layer order."""
    if refused_by == LAYER_CARRIER:
        steps = [(LAYER_CARRIER, LAYER_REFUSED)]
    elif refused_by == LAYER_HANDSHAKE:
        steps = [(LAYER_CARRIER, LAYER_ACCEPTED), (LAYER_HANDSHAKE, LAYER_REFUSED)]
    else:
        steps = [(LAYER_CARRIER, LAYER_ACCEPTED), (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                 *((layer, LAYER_NOT_APPLICABLE) for layer in _NOT_APPLICABLE_TO_PLANNING),
                 (LAYER_PREFLIGHT, preflight_result)]
    return EnvelopeTrace(SLOT_ID, tuple(steps), dispatched, refused_by, refusal).to_dict()


def _refused_outcome(refused: OntologyChangeRefused, refused_by: str, selector=None, preflight=(), *,
                     dispatched: bool = False) -> PlanOutcome:
    """One failure with its envelope refusal, the decisions and verdicts so far, and the trace."""
    refusal = refusal_for(refused.code)
    preflight_result = LAYER_REFUSED if refused_by == LAYER_PREFLIGHT else LAYER_ACCEPTED
    return PlanOutcome(None, refused.to_record(), tuple(selector.decisions) if selector else (), refusal.to_dict(),
                       tuple(verdict.to_dict() for verdict in selector.verdicts) if selector else (),
                       tuple(preflight), _trace(refused_by, refusal, dispatched=dispatched,
                                                preflight_result=preflight_result))


def plan_change(request, host: "HostEngines | None" = None, *, context: "SelectionContext | None" = None
                ) -> PlanOutcome:
    """Plan one change: the plan or one typed failure, with every selection decision and envelope record."""
    try:
        plan_request, base, proposed = read_request(request)
    except OntologyChangeRefused as refused:
        return _refused_outcome(refused, LAYER_CARRIER)
    planning_input = PlanningInput(base, proposed, plan_request.profile, plan_request.maximum_closure)
    selector = _Selector(host or default_host(), planning_input, context or SelectionContext())
    chosen = selector.first()
    if chosen is None:
        failure = OntologyChangeRefused("no_eligible_engine", selector.refusal_summary(), "selection")
        return _refused_outcome(failure, LAYER_HANDSHAKE, selector)
    reports = []
    while chosen is not None:
        started = time.monotonic()
        # The preflight checks the selected engine again just before it runs; a failed check is the
        # engine_unavailable failure kind, so the declared order moves on exactly as if the engine said so.
        report = run_preflight(SLOT_ID, PREFLIGHT_CHECKS, (), {"engine": selector.engines[chosen]})
        reports.append(report.to_dict())
        source = LAYER_PREFLIGHT
        try:
            if not report.ready:
                raise EngineFailure("engine_unavailable", f"preflight refused {chosen}: {report.refusal.code}")
            source = ENGINE_SOURCE
            outcome = selector.engines[chosen].plan(planning_input)
            plan = _admit(outcome, plan_request, base, proposed, selector.descriptors[chosen])
            return PlanOutcome(plan, None, tuple(selector.decisions), None,
                               tuple(verdict.to_dict() for verdict in selector.verdicts), tuple(reports),
                               _trace("", None, dispatched=True))
        except EngineFailure as failure:
            if failure.kind == "limit_exceeded":
                refused = OntologyChangeRefused("limit_exceeded", failure.detail, "engine")
                return _refused_outcome(refused, ENGINE_SOURCE, selector, reports, dispatched=True)
            kind, code, detail = failure.kind, _SEQUENCE_FAILURES[failure.kind], failure.detail
        except ValueError as error:
            kind, code, detail = "output_validation_failed", "result_invalid", str(error)
        next_choice = selector.after_failure(chosen, kind, time.monotonic() - started)
        if next_choice is None:
            stage = "result" if code == "result_invalid" else "engine"
            refused = OntologyChangeRefused(code, f"{chosen}: {detail}", stage)
            return _refused_outcome(refused, source, selector, reports, dispatched=source == ENGINE_SOURCE)
        chosen = next_choice
    raise AssertionError("unreachable")
