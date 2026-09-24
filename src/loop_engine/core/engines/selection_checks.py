"""Offline checks for engine selection and attempt assessment in any slot.

Each check names its known-wrong case and passes only when that case is
refused or kept in the declared order; each removed-guard control deletes one
guard and passes only when its check would then fail. Fixture engines are
records: nothing here imports, probes or starts an engine, calls a model or
opens a network connection, and one check proves selection cannot.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from unittest.mock import patch

from . import evidence as evidence_module
from . import fallback as fallback_module
from . import selection
from ..configuration_capabilities import digest
from ..configuration_preferences import MetaPreferencePolicy
from .decision_records import ConsumedAuthority, PolicySource, require_parent_when_nested
from .evidence import EngineEvidenceReview, EngineEvidenceRule, EngineEvidenceSnapshot, EngineTrialEvidence
from .fallback import EngineAttemptOutcome, assess_engine_attempt, fallback_request
from .host_records import EngineInstallation, EngineSlotConfiguration
from .records import EngineCostBasis, EngineRecordError, QualificationScope
from .records_checks import (
    NOW, descriptor, fact, goose_installation, installation, policy, qualification, retirement, slot_configuration)
from .selection import EngineCandidate, EngineSelectionRequest, SelectionAuthority, select_engine, select_engine_as_loop
from .selection_records import EngineEvidenceBinding, EngineSelectionOverride, OverrideSender
from .slots import load_engine_slot_catalog

GRANTS = ("reads_fs", "writes_fs", "spawns_process")
EDGE = "step_run_request/v1"
LOOP = OverrideSender("loop", "fixture.loop1", None, None)
HARNESS = OverrideSender("harness", "fixture.loop1", "opencode@1.2.3", "fixture.loop1.attempt1")


@lru_cache(maxsize=None)
def _slot(slot_id):
    return next(item for item in load_engine_slot_catalog().slots if item.slot_id == slot_id)


def _scope():
    from .selection_records_checks import decision
    return decision().scope


def _trace():
    from .selection_records_checks import trace
    return trace()


def goose(**changes):
    return descriptor(engine_id="goose", engine_version="1.0.0", **changes)


def candidate(installed, engine, qualified=True, **qualification_changes):
    record = qualification(engine, installed, **qualification_changes) if qualified else None
    return EngineCandidate(installed, engine, record)


def two_engines(opencode_engine=None, goose_engine=None):
    return (candidate(installation(), opencode_engine or descriptor()),
            candidate(goose_installation(), goose_engine or goose()))


def request(**changes) -> EngineSelectionRequest:
    base = EngineSelectionRequest(
        slot=_slot("step_executor"), configuration=slot_configuration(), scope_key="default", scope=_scope(),
        candidates=two_engines(), authority=SelectionAuthority(granted_effects=GRANTS), edge_contract=EDGE,
        as_of=NOW, policy_source=PolicySource("declared", (_trace(),)))
    return replace(base, **changes)


def with_policy(**changes) -> EngineSlotConfiguration:
    return slot_configuration(selection={"default": policy(**changes)})


def both_initial(**changes):
    return with_policy(initial=("opencode", "goose"), fallbacks=(), no_fallback=True, fallback_on=(), **changes)


def override(kind, installations=(), sender=LOOP, **changes) -> EngineSelectionOverride:
    source = "intelligence_proposal" if sender is HARNESS else "run_override"
    return replace(EngineSelectionOverride("step_executor", "default", kind, tuple(installations),
                                           changes.pop("objective", None), source, sender), **changes)


def codes(decision, installation_id) -> list:
    entry = next(item for item in decision.eligibility if item.installation_id == installation_id)
    return [item.code for item in entry.refusals]


def chosen(decision) -> str:
    return decision.selected.installation_id if decision.selected is not None else ""


# A record store slot: its fallback ceiling is none and it ranks by nothing.

def store_request(**policy_changes) -> EngineSelectionRequest:
    installed = (EngineInstallation("sqlite", "sqlite", "embedded_database", True, {"path": "records.db"}, None, None),
                 EngineInstallation("memory", "memory", "reference_memory", True, {}, None, None))
    engines = []
    for item, kind in zip(installed, ("embedded_database", "reference_memory")):
        engine = descriptor(slot_id="record_store", engine_id=item.engine_id, engine_version="1.0.0",
                            engine_kind=kind, supported_edge_contracts=("catalog_atomic_write_batch/v1",),
                            effects=("writes_fs",))
        engines.append(candidate(item, engine, slot_id="record_store",
                                 scope=QualificationScope("catalog_atomic_write_batch/v1", None, ())))
    permitted = {"loop": ("pin", "exclude", "prefer", "objective"), "harness": ("prefer",)}
    stated = dict(slot_id="record_store", initial=("sqlite",), fallbacks=(), no_fallback=True, fallback_on=(),
                  overrides_permitted=permitted)
    stated.update(policy_changes)
    configuration = EngineSlotConfiguration("record_store", "1.0.0", installed, {"default": policy(**stated)},
                                            "declared", digest("record store host block"))
    return request(slot=_slot("record_store"), configuration=configuration, candidates=tuple(engines),
                   edge_contract="catalog_atomic_write_batch/v1", authority=SelectionAuthority(granted_effects=GRANTS))


# Evidence fixtures.

RULE = EngineEvidenceRule("matched_quality_then_efficiency", "tokens", 10, "fixture.evaluator@1.0.0",
                          digest("fixture evaluator"), 30, 200)


def trial(engine_ref, installed, number, successes, *, tokens=100, scope_digest="", population="population-a",
          recorded_at="2026-09-21T12:00:00Z"):
    return EngineTrialEvidence(
        f"{engine_ref}#{number}", "step_executor", engine_ref, installed.installation_digest,
        scope_digest or _scope().scope_digest, digest(population), RULE.evaluator_ref, RULE.evaluator_digest,
        digest(f"subject {number}"), f"history/{engine_ref}/{number}", digest(f"history {engine_ref} {number}"),
        "comparison_arm", successes, 2, tokens // 2, tokens - tokens // 2, 3.0, None, recorded_at)


def reviewed(item, decision="approved"):
    return (item, EngineEvidenceReview(item.content_digest, "independent-reviewer@fixture",
                                       "reviews/" + item.trial_id, digest("review " + item.trial_id), decision))


def snapshot(count=10, *, opencode_successes=1, goose_successes=2, opencode_tokens=100, goose_tokens=100,
             scope_digest=""):
    pairs = []
    for number in range(count):
        pairs.append(reviewed(trial("opencode@1.2.3", installation(), number, opencode_successes,
                                    tokens=opencode_tokens, scope_digest=scope_digest)))
        pairs.append(reviewed(trial("goose@1.0.0", goose_installation(), number, goose_successes,
                                    tokens=goose_tokens, scope_digest=scope_digest)))
    return EngineEvidenceSnapshot("step_executor", scope_digest or _scope().scope_digest, RULE, tuple(pairs),
                                  "2026-09-22T00:00:00Z")


def evidence_request(evidence_snapshot, **changes) -> EngineSelectionRequest:
    ranking = MetaPreferencePolicy(("matched-evidence", "declared-order"), ("insufficient_evidence",))
    binding = EngineEvidenceBinding(RULE.to_dict(), "snapshots/fixture.json", evidence_snapshot.content_digest)
    permitted = {"loop": ("pin", "exclude", "prefer", "declared_order_only"), "harness": ("prefer",)}
    configuration = both_initial(ranking=ranking, evidence=binding, overrides_permitted=permitted)
    return request(configuration=configuration, evidence=evidence_snapshot, **changes)


# Scenarios: each returns True only when its known-wrong cases are refused.

def the_declared_first_choice_is_selected_with_its_fallbacks() -> bool:
    """Known wrong: a decision that names no fallback chain, no basis or path, or
    a request digest other than the request it read."""
    stated = request()
    decided = select_engine(stated)
    again = type(decided).from_dict(decided.to_dict())
    return (decided.status == "selected" and chosen(decided) == "opencode" and decided.fallbacks == ("goose",)
            and (decided.selection_basis, decided.selection_path) == ("preferred", "first_choice")
            and decided.request_digest == stated.request_digest and again.content_digest == decided.content_digest
            and not any(decided.to_dict()[name] for name in ("execution_authority_granted", "task_accepted",
                                                             "model_call_performed_by_boundary")))


def selection_never_considers_an_engine_outside_the_installed_enabled_universe() -> bool:
    """Known wrong: an engine offered by a registry but not installed by the host is a
    candidate; a disabled installation named by the policy is ordered."""
    disabled = slot_configuration(installed=(installation(), goose_installation(enabled=False)))
    decided = select_engine(request(configuration=disabled, candidates=(candidate(installation(), descriptor()),)))
    stray = EngineInstallation("cline", "cline", "agent_protocol_harness", True, {}, None, None)
    refused_stray = _refused(lambda: request(candidates=two_engines() + (candidate(stray, descriptor(
        engine_id="cline", engine_version="1.0.0")),)), "candidate_installation_mismatch")
    return (refused_stray and [item.installation_id for item in decided.universe] == ["opencode"]
            and codes(decided, "goose") == ["engine_disabled"] and decided.fallbacks == ())


def a_policy_stays_within_its_slot_record() -> bool:
    """Known wrong (LE-SELECT-002, LE-SELECT-017): a record store policy with an ordered
    fallback although the slot's ceiling is none; an objective override naming
    priced_cost for a slot that ranks by nothing; an evidence minimum below the
    slot's floor; a ranking engine the release does not ship."""
    low = dict(RULE.to_dict(), minimum_matched_records=5)
    below_floor = both_initial(ranking=MetaPreferencePolicy(("matched-evidence", "declared-order"),
                                                            ("insufficient_evidence",)),
                               evidence=EngineEvidenceBinding(low, "snapshots/fixture.json", digest("snapshot")))
    unknown_ranker = both_initial(ranking=MetaPreferencePolicy(("learned-router", "declared-order")))
    objective = override("objective", objective="priced_cost", slot_id="record_store")
    return (select_engine(store_request(fallbacks=("memory",), no_fallback=False,
                                        fallback_on=("engine_unavailable",))).status == "refused_policy"
            and select_engine(replace(store_request(), overrides=(objective,))).status == "refused_policy"
            and select_engine(request(configuration=below_floor, evidence=snapshot())).status == "refused_policy"
            and select_engine(request(configuration=unknown_ranker)).status == "refused_policy"
            and chosen(select_engine(store_request())) == "sqlite")


def a_narrower_source_can_reorder_but_never_widen() -> bool:
    """Known wrong: a preference that names an engine the host did not install is ignored
    instead of refused; an exclusion that leaves the excluded engine chosen; a preference
    that promotes a fallback into the initial choice."""
    reordered = select_engine(request(configuration=both_initial(), overrides=(override("prefer", ("goose",)),)))
    excluded = select_engine(request(configuration=both_initial(), overrides=(override("exclude", ("opencode",)),)))
    uninstalled = select_engine(request(overrides=(override("prefer", ("cline",)),)))
    promoted = select_engine(request(overrides=(override("prefer", ("goose",)),)))
    return (chosen(reordered) == "goose" and reordered.selection_path == "override_prefer"
            and reordered.order_without_override == ("opencode", "goose")
            and chosen(excluded) == "goose" and "opencode" not in excluded.declared_order
            and uninstalled.status == "refused_policy"
            and chosen(promoted) == "opencode" and promoted.selection_path == "first_choice")


def a_harness_preference_is_applied_only_within_its_authority() -> bool:
    """Known wrong: a harness pin applied although the host permits harness senders only
    to prefer; a harness preference that changes the evaluator is not expressible."""
    preferred = select_engine(request(configuration=both_initial(),
                                      overrides=(override("prefer", ("goose",), sender=HARNESS),)))
    pinned = select_engine(request(configuration=both_initial(),
                                   overrides=(override("pin", ("goose",), sender=HARNESS),)))
    return (chosen(preferred) == "goose" and preferred.override[0].sender.sender_kind == "harness"
            and pinned.status == "refused_policy" and pinned.selected is None)


def a_pin_to_an_ineligible_engine_refuses_without_substitution() -> bool:
    """Known wrong (LE-SELECT-006): a pin on an unavailable engine served by another engine."""
    unavailable = two_engines(goose_engine=goose(availability=fact("unavailable")))
    refused = select_engine(request(configuration=both_initial(), candidates=unavailable,
                                    overrides=(override("pin", ("goose",)),)))
    pinned = select_engine(request(overrides=(override("pin", ("opencode",)),)))
    return (refused.status == "refused_policy" and refused.selected is None
            and codes(refused, "goose") == ["engine_unavailable"]
            and chosen(pinned) == "opencode" and pinned.selection_basis == "pinned"
            and pinned.selection_path == "override_pin" and pinned.fallbacks == () and pinned.no_fallback)


def eligibility_records_every_refusal_in_the_fixed_screen_order() -> bool:
    """Known wrong: only the first refusal recorded; a screen skipped; an unknown cost or a
    missing preemptive limit accepted under a bounded budget; an effect the Loop
    does not grant accepted because a policy or trial allows the engine."""
    faulty = goose(lifecycle="candidate", supported_edge_contracts=("harness_request_identity/v3",),
                   availability=fact("unavailable"), effects=("reads_fs", "network"),
                   enforced_limits=("model_calls",), cost_basis=EngineCostBasis("unknown", None, None, None))
    decided = select_engine(request(candidates=(candidate(installation(), descriptor()),
                                                candidate(goose_installation(), faulty, qualified=False)),
                                    authority=SelectionAuthority(granted_effects=GRANTS,
                                                                 required_preemptive_limits=("wall_time",))))
    return (chosen(decided) == "opencode" and codes(decided, "goose") == [
        "engine_not_active", "edge_version_unsupported", "engine_unavailable", "engine_unqualified",
        "permission_not_granted", "budget_requirement_unsatisfied", "budget_requirement_unsatisfied"])


def unavailable_unqualified_or_expired_engine_is_ineligible_by_default() -> bool:
    """Known wrong: an expired, rejected, foreign or other-edge qualification read as
    qualified; an expired availability observation read as available."""
    opencode = descriptor()
    cases = (
        (candidate(installation(), opencode, issued_at="2026-09-01T00:00:00Z", expires_at="2026-09-10T00:00:00Z"),
         "qualification_expired"),
        (candidate(installation(), opencode, decision="rejected"), "engine_unqualified"),
        (EngineCandidate(installation(), opencode, qualification(opencode, goose_installation())),
         "qualification_scope_mismatch"),
        (candidate(installation(), opencode, scope=QualificationScope("harness_request_identity/v3", None, ())),
         "qualification_scope_mismatch"),
        (candidate(installation(), descriptor(availability=fact("available", "2026-09-20T00:00:00Z"))),
         "engine_unavailable"))
    for first, code in cases:
        decided = select_engine(request(candidates=(first, candidate(goose_installation(), goose()))))
        if code not in codes(decided, "opencode") or chosen(decided) != "goose":
            return False
    trial_policy = with_policy(allow_unqualified=True)
    trialled = select_engine(request(configuration=trial_policy, candidates=(
        candidate(installation(), opencode, qualified=False), candidate(goose_installation(), goose()))))
    return chosen(trialled) == "opencode"


def retired_deprecated_and_candidate_engines_keep_their_place() -> bool:
    """Known wrong: an archived engine version selected although listed; a deprecated
    engine as the initial choice; a release-retired engine; a candidate outside a trial."""
    archived = retirement(engine_id="opencode", engine_version="1.2.3", stage="archived", replacement="goose")
    retired = select_engine(request(configuration=with_policy(retired=(archived,))))
    deprecated_goose = retirement(engine_id="goose", engine_version="1.0.0", stage="deprecated",
                                  replacement="opencode")
    still_fallback = select_engine(request(configuration=with_policy(retired=(deprecated_goose,))))
    release_retired = select_engine(request(slot=replace(_slot("step_executor"), retired_engines=("opencode",))))
    initial_deprecated = select_engine(request(candidates=two_engines(descriptor(lifecycle="deprecated"))))
    candidate_engine = select_engine(request(candidates=two_engines(descriptor(lifecycle="candidate"))))
    return (codes(retired, "opencode") == ["engine_retired"] and chosen(retired) == "goose"
            and retired.selection_path == "fallback_after:engine_unavailable"
            and still_fallback.fallbacks == ("goose",)
            and codes(release_retired, "opencode") == ["engine_retired"]
            and codes(initial_deprecated, "opencode") == ["engine_deprecated_as_initial"]
            and codes(candidate_engine, "opencode") == ["engine_not_active"])


def evidence_orders_only_at_or_above_the_floor_for_the_exact_scope() -> bool:
    """Known wrong: nine matched records reorder a slot whose floor is ten; evidence
    measured on another scope ranks this one; a declared order only override still
    ranks by evidence; ranking restores an ineligible engine; a snapshot other than
    the one the policy binds is read."""
    enough = select_engine(evidence_request(snapshot()))
    thin = select_engine(evidence_request(snapshot(9)))
    foreign_scope = digest("another step")
    foreign = select_engine(evidence_request(snapshot(scope_digest=foreign_scope)))
    closed = select_engine(evidence_request(snapshot(), overrides=(override("declared_order_only"),)))
    ineligible = select_engine(evidence_request(snapshot(), candidates=two_engines(
        goose_engine=goose(availability=fact("unavailable")))))
    stale = replace(evidence_request(snapshot()), evidence=snapshot(11))
    return (chosen(enough) == "goose" and enough.selection_basis == "automatic"
            and enough.selection_path == "evidence_reordered" and enough.evidence.changed_order
            and chosen(thin) == "opencode" and thin.selection_basis == "preferred"
            and thin.evidence.reason == "insufficient_matched_reviewed_evidence"
            and thin.ranking["record_type"] == "configuration_preference_decision/v2"
            and chosen(foreign) == "opencode" and foreign.evidence.reason == "evaluation_scope_mismatch"
            and chosen(closed) == "opencode" and closed.evidence.reason == "not_requested"
            and chosen(ineligible) == "opencode" and select_engine(stale).status == "refused_policy")


def selection_performs_no_probe_no_network_and_no_model_call() -> bool:
    """Known wrong: a selection that starts a process, opens a socket or makes a request.

    The targets are named, not imported, so this check module itself holds no
    process or network capability."""
    def forbidden(*args, **kwargs):
        raise AssertionError("selection touched the outside world")
    targets = ("subprocess.Popen", "subprocess.run", "socket.socket", "socket.create_connection",
               "urllib.request.urlopen", "os.system")
    with ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, forbidden))
        decisions = (select_engine(request()), select_engine(evidence_request(snapshot())),
                     select_engine(store_request()))
    return all(item.status == "selected" for item in decisions)


def a_decision_exists_before_every_dispatch() -> bool:
    """Known wrong: a dispatch naming a decision the ledger does not hold; a selection
    whose decision is returned but never recorded in the owning Loop's ledger."""
    parent = _owning_loop()
    decided = select_engine_as_loop(request(), parent=parent)
    try:
        selection.require_prior_decision(parent.ledger, digest("a decision nobody recorded"))
        return False
    except EngineRecordError as exc:
        missing = exc.code == "no_prior_decision"
    return missing and selection.require_prior_decision(parent.ledger, decided.content_digest)["status"] == "selected"


def every_selection_is_recorded_in_existing_event_families() -> bool:
    """Known wrong: a selection event projected outside the declared families, a refusal
    recorded nowhere, or an event kind the canonical vocabulary does not hold."""
    from ..run_history import to_canonical_events
    parent = _owning_loop()
    unavailable = two_engines(goose_engine=goose(availability=fact("unavailable")))
    select_engine_as_loop(request(candidates=unavailable), parent=parent)
    events = [event for event in parent.ledger.events if event.get("component") == selection.SELECTION_COMPONENT]
    projected = to_canonical_events(events)
    families = [item.get("type") or item.get("family") or item.get("event_family") for item in projected]
    completed = next(event for event in events if event["event"] == selection.COMPLETED_EVENT)
    refused = [entry for entry in completed["decision"]["eligibility"] if entry["refusals"]]
    return (families == ["capability.search.started", "capability.search.completed", "capability.selected"]
            and [entry["installation_id"] for entry in refused] == ["goose"])


def bound_engine_is_revalidated_at_use() -> bool:
    """Known wrong: a harness binary replaced between selection and launch is invoked."""
    decided = select_engine(request())
    same = candidate(installation(), descriptor())
    replaced = candidate(installation(), descriptor(implementation_digest=digest("replaced binary")))
    resettled = candidate(installation(settings={"placement": "long_lived_session"}), descriptor())
    return (selection.revalidate_binding(decided, same) == ""
            and selection.revalidate_binding(decided, replaced) == "engine_changed_after_selection"
            and selection.revalidate_binding(decided, resettled) == "engine_changed_after_selection")


def _outcome(**changes) -> EngineAttemptOutcome:
    base = EngineAttemptOutcome("opencode", "opencode@1.2.3", "engine_unavailable", False, "none", False,
                                ConsumedAuthority(1, 120, 40, 2.5, "known", 0.01), "fixture.loop3")
    return replace(base, **changes)


def fallback_only_on_declared_failure_kinds() -> bool:
    """Known wrong: a fallback after a failure kind the policy does not name; after a
    terminal kind; from a pinned choice; beyond the slot's ceiling."""
    stated = request()
    decided = select_engine(stated)
    slot, rules = stated.slot, stated.policy
    pinned = select_engine(request(overrides=(override("pin", ("opencode",)),)))

    def action(**changes):
        return assess_engine_attempt(changes.pop("slot", slot), rules, changes.pop("decision", decided),
                                     _outcome(**changes)).action
    return (action() == "fallback"
            and action(failure_kind="engine_reported_failure") == "terminal"
            and action(failure_kind="shared_provider_failure") == "terminal"
            and action(decision=pinned) == "terminal"
            and action(slot=_slot("record_store")) == "terminal"
            and action(slot=_slot("workspace_backend"), started=True) == "terminal"
            and action(effects="committed") == "terminal")


def uncertain_effect_or_accounting_blocks_fallback() -> bool:
    """Known wrong: a second engine started after an attempt whose effects or accounting
    are uncertain."""
    stated = request()
    decided = select_engine(stated)
    effects = assess_engine_attempt(stated.slot, stated.policy, decided, _outcome(effects="uncertain"))
    accounting = assess_engine_attempt(stated.slot, stated.policy, decided, _outcome(accounting_uncertain=True))
    return ((effects.action, effects.failure_kind) == ("terminal", "effects_uncertain")
            and (accounting.action, accounting.failure_kind) == ("terminal", "accounting_uncertain"))


def fallback_carries_consumed_authority() -> bool:
    """Known wrong: a fallback decision that resets the authority the failed attempt consumed,
    or selects the engine that already failed."""
    stated = request()
    outcome = _outcome()
    moved = select_engine(fallback_request(stated, outcome, expected_effect="the next engine runs the step",
                                           fixed_settings=("model_access",)))
    return (moved.phase == "fallback" and chosen(moved) == "goose" and moved.consumed == outcome.consumed
            and moved.selection_path == "fallback_after:engine_unavailable"
            and moved.transition.previous_installation_id == "opencode" and "opencode" not in moved.fallbacks)


def a_nested_selection_names_its_parent_decision_and_never_widens_it() -> bool:
    """Known wrong: a nested decision without its parent's digest."""
    parent_digest = select_engine(request()).content_digest
    nested = select_engine(request(parent_decision_digest=parent_digest))
    try:
        require_parent_when_nested(select_engine(request()), nested=True)
        return False
    except EngineRecordError:
        pass
    return (nested.parent_decision_digest == parent_digest
            and require_parent_when_nested(nested, nested=True) is nested)


def selection_runs_inside_a_deterministic_practitioner_loop() -> bool:
    """Known wrong: a selection that runs outside a Loop or starts a model-led Loop."""
    parent = _owning_loop()
    decided = select_engine_as_loop(request(), parent=parent)
    spawned = parent.ledger.tree().get(parent.loop_id, [])
    spawn = next((event for event in parent.ledger.events if event.get("event") == "spawn"
                  and event.get("loop_id") == decided.selection_loop_id), {})
    return (decided.selection_loop_id in spawned and spawn.get("profile_id", "practitioner.code_execution")
            == "practitioner.code_execution" and not any(event.get("event") in ("model_led", "model_escalation")
                                                         for event in parent.ledger.events))


def the_request_digest_binds_every_input() -> bool:
    """Known wrong: two requests that differ in an override, the time or a qualification
    sharing one request digest."""
    base = request()
    changed = (request(overrides=(override("prefer", ("opencode",)),)),
               request(as_of=NOW + timedelta(minutes=1)),
               request(candidates=two_engines(goose_engine=goose(availability=fact("unavailable")))))
    return (select_engine(base).request_digest == base.request_digest
            and len({base.request_digest, *(item.request_digest for item in changed)}) == 4)


def engine_selection_needs_no_selection_to_start() -> bool:
    """Known wrong (design 8.2, base case): a policy whose ranking engine is not one the
    release ships, so it would itself have to be chosen by another selection."""
    chosen_ranker = both_initial(ranking=MetaPreferencePolicy(("learned-router", "declared-order"),
                                                              ("engine_unavailable",)))
    return (select_engine(request(configuration=chosen_ranker)).status == "refused_policy"
            and selection.RANKING_ENGINE_REFS == ("matched-evidence", "declared-order"))


def _owning_loop():
    from ...loop.recursive_loop import Loop, LoopConfig
    return Loop("own one step", LoopConfig(framework="custom", custom_steps=("act",),
                                            allowable_modes=("deterministic",), preferred_modes=("deterministic",),
                                            delegated_modes=("deterministic",)))


def _refused(action, code) -> bool:
    try:
        action()
    except EngineRecordError as exc:
        return exc.code == code
    except Exception:
        return False
    return False


def _no_refusals(*_args, **_kwargs):
    return []


def _unchanged(*_args, **_kwargs):
    return ""


CHECKS = (
    ("the_declared_first_choice_is_selected_with_its_fallbacks", the_declared_first_choice_is_selected_with_its_fallbacks,
     ()),
    ("selection_never_considers_an_engine_outside_the_installed_enabled_universe",
     selection_never_considers_an_engine_outside_the_installed_enabled_universe, ()),
    ("a_policy_stays_within_its_slot_record", a_policy_stays_within_its_slot_record,
     (("removed_slot_policy_bound_is_detected", ((selection, "policy_widening", lambda *a, **k: ()),)),)),
    ("a_narrower_source_can_reorder_but_never_widen", a_narrower_source_can_reorder_but_never_widen,
     (("removed_override_admission_is_detected", ((selection, "_override_problems", _no_refusals),)),)),
    ("a_harness_preference_is_applied_only_within_its_authority",
     a_harness_preference_is_applied_only_within_its_authority,
     (("removed_harness_preference_bound_is_detected", ((selection, "_override_problems", _no_refusals),)),)),
    ("a_pin_to_an_ineligible_engine_refuses_without_substitution",
     a_pin_to_an_ineligible_engine_refuses_without_substitution,
     (("removed_pin_eligibility_rule_is_detected", ((selection, "_usable_pin", lambda *a, **k: True),)),)),
    ("eligibility_records_every_refusal_in_the_fixed_screen_order",
     eligibility_records_every_refusal_in_the_fixed_screen_order,
     (("removed_lifecycle_screen_is_detected", ((selection, "_lifecycle_refusals", _no_refusals),)),
      ("removed_permission_screen_is_detected", ((selection, "_permission_refusals", _no_refusals),)),
      ("removed_budget_screen_is_detected", ((selection, "_budget_refusals", _no_refusals),)))),
    ("unavailable_unqualified_or_expired_engine_is_ineligible_by_default",
     unavailable_unqualified_or_expired_engine_is_ineligible_by_default,
     (("removed_qualification_screen_is_detected", ((selection, "_qualification_refusals", _no_refusals),)),)),
    ("retired_engine_is_never_selected_even_when_listed", retired_deprecated_and_candidate_engines_keep_their_place,
     (("removed_retirement_screen_is_detected", ((selection, "_retirement_refusals", _no_refusals),)),)),
    ("below_the_minimum_sample_the_declared_order_stands", evidence_orders_only_at_or_above_the_floor_for_the_exact_scope,
     (("removed_evidence_minimum_is_detected", ((evidence_module, "_require_minimum", lambda *a, **k: None),)),)),
    ("selection_performs_no_probe_no_network_and_no_model_call",
     selection_performs_no_probe_no_network_and_no_model_call, ()),
    ("a_decision_exists_before_every_dispatch", a_decision_exists_before_every_dispatch,
     (("removed_decision_recording_is_detected", ((selection, "record_decision", lambda *a, **k: None),)),)),
    ("every_selection_is_recorded_in_existing_event_families", every_selection_is_recorded_in_existing_event_families,
     ()),
    ("bound_engine_is_revalidated_at_use", bound_engine_is_revalidated_at_use,
     (("removed_revalidation_is_detected", ((selection, "revalidate_binding", _unchanged),)),)),
    ("fallback_only_on_declared_failure_kinds", fallback_only_on_declared_failure_kinds,
     (("removed_declared_fallback_rule_is_detected",
       ((fallback_module, "_declared_fallback", lambda *a, **k: True),)),
      ("removed_fallback_ceiling_is_detected", ((fallback_module, "_ceiling_refusal", lambda *a, **k: ""),)))),
    ("uncertain_effect_or_accounting_blocks_fallback", uncertain_effect_or_accounting_blocks_fallback,
     (("removed_uncertainty_stop_is_detected", ((fallback_module, "_uncertainty", lambda *a, **k: ""),)),)),
    ("fallback_carries_consumed_authority", fallback_carries_consumed_authority, ()),
    ("a_nested_selection_names_its_parent_decision_and_never_widens_it",
     a_nested_selection_names_its_parent_decision_and_never_widens_it, ()),
    ("selection_runs_inside_a_deterministic_practitioner_loop", selection_runs_inside_a_deterministic_practitioner_loop,
     ()),
    ("the_request_digest_binds_every_input", the_request_digest_binds_every_input, ()),
    ("engine_selection_needs_no_selection_to_start", engine_selection_needs_no_selection_to_start,
     (("removed_shipped_ranking_engine_rule_is_detected",
       ((selection, "policy_widening", lambda *a, **k: ()),)),)),
)


def run_checks() -> dict:
    tests = []
    for name, scenario, controls in CHECKS:
        tests.append({"name": name, "passed": _observe(scenario)})
        for control, removed in controls:
            with ExitStack() as stack:
                for module, guard, replacement in removed:
                    stack.enter_context(patch.object(module, guard, replacement))
                tests.append({"name": control, "passed": _observe(scenario) is False})
    return {"tests": tests, "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


def _observe(scenario) -> bool:
    try:
        return bool(scenario())
    except Exception:
        return False


def self_test() -> dict:
    return run_checks()
