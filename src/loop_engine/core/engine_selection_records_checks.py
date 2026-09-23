"""Offline checks for the engine selection records and every engine record's reader.

Covers engine_selection_policy/v1, engine_selection_override/v1 and
engine_selection_decision/v1, and the two rules every one of the ten engine
records keeps: its reader refuses unknown fields and unsupported versions
before any effect, and it round-trips with an identical digest. Each check
names its known-wrong case; each removed-guard control deletes one guard and
passes only when its check would then fail. No engine, model or network is
touched.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import replace
import json
from unittest.mock import patch

from . import engine_decision_records as decision_records
from . import engine_host_records as host_records
from . import engine_records as records
from . import engine_selection_records as selection_records
from .configuration_capabilities import digest
from .configuration_preferences import (
    ExistingOrderPreference, MetaPreferencePolicy, PreferenceCandidate, PreferenceEngineBinding,
    PreferenceSelectionRequest, PreferenceSnapshot, resolve_preference)
from .engine_decision_records import (
    ConsumedAuthority, EligibilityEntry, EligibilityRefusal, EngineSelectionDecision, EvidenceUse,
    FallbackTransition, PolicySource, Propensity, SelectedEngine, SelectionScope, UniverseEntry,
    require_parent_when_nested)
from .engine_host_records import EngineBindingsReport, EngineInstallation, EngineSlotConfiguration, ServiceHostEngines
from .engine_records import EngineDescriptor, EngineQualification, EngineRetirement
from .engine_records_checks import (
    NOW, accepted, bindings_report, descriptor, fact, goose_installation, installation, policy, qualification,
    refused, retirement, service_host_engines, slot_configuration)
from .engine_selection_records import (
    DECLARED_ORDER_ENGINE_REF, EngineEvidenceBinding, EngineSelectionOverride, OverrideSender, EngineSelectionPolicy)

LOOP = OverrideSender("loop", "fixture.loop1", None, None)
HARNESS = OverrideSender("harness", "fixture.loop1", "opencode@1.2.3", "fixture.loop1.attempt1")


def override(**changes) -> EngineSelectionOverride:
    base = EngineSelectionOverride("step_executor", "default", "prefer", ("goose",), None, "run_override", LOOP)
    return replace(base, **changes)


def ranking_record(candidates=("opencode",)) -> dict:
    """A real configuration_preference_decision/v1 from the existing boundary."""
    binding = PreferenceEngineBinding(
        DECLARED_ORDER_ENGINE_REF, ExistingOrderPreference(), fact("available"), ("engine_installation",),
        "loop_engine.core.configuration_preferences.ExistingOrderPreference", digest("existing order"),
        fact("qualified"))
    snapshot = PreferenceSnapshot("engine_installation", digest("scope"),
                                  tuple(PreferenceCandidate(item) for item in candidates))
    return resolve_preference(PreferenceSelectionRequest(
        snapshot, MetaPreferencePolicy((DECLARED_ORDER_ENGINE_REF,)), (binding,), NOW))


def trace() -> dict:
    return {"source_kind": "deployment_configuration", "source_ref": "host.json#engines.step_executor",
            "source_version": "1", "precedence_rank": 6, "requested_state": "PROVIDED",
            "disposition": "SELECTED", "reason": "the host declares the initial choice"}


def decision(**changes) -> EngineSelectionDecision:
    opencode, goose = descriptor(), descriptor(engine_id="goose", engine_version="1.0.0")
    base = EngineSelectionDecision(
        slot_id="step_executor", slot_digest=digest("slot record"), scope_key="default", phase="initial",
        scope=SelectionScope("step_run_request/v1", "practitioner.code_execution@1.0.0", "fixture.loop1",
                             "response_admission/v1", {}, {"owning_definition": digest("definition")}),
        policy_digest=policy().content_digest, policy_source=PolicySource("declared", (trace(),)),
        configuration_digest=digest("host configuration"),
        universe=(UniverseEntry("opencode", opencode.engine_ref, opencode.content_digest,
                                installation().installation_digest),
                  UniverseEntry("goose", goose.engine_ref, goose.content_digest,
                                goose_installation().installation_digest)),
        eligibility=(EligibilityEntry("opencode", ()), EligibilityEntry("goose", ())),
        declared_order=("opencode",), override=(), order_without_override=("opencode",), ranking=ranking_record(),
        evidence=EvidenceUse("not_requested", False, "not_computed", None, (), None),
        selected=SelectedEngine("opencode", opencode.engine_ref, opencode.content_digest),
        propensity=Propensity(1, 1), fallbacks=("goose",), no_fallback=False, transition=None,
        consumed=ConsumedAuthority(0, 0, 0, 0.0, "known", 0.0), status="selected",
        selection_loop_id="fixture.loop2", as_of="2026-09-22T12:00:00Z", binding_site="runtime_context_internal",
        parent_decision_digest="")
    return replace(base, **changes)


def fallback_decision(**transition_changes) -> EngineSelectionDecision:
    goose = descriptor(engine_id="goose", engine_version="1.0.0")
    transition = replace(FallbackTransition(
        "opencode", "opencode@1.2.3", "engine_unavailable", "fixture.loop3", False,
        "the step runs on the next declared engine", ("model_access",)), **transition_changes)
    return decision(phase="fallback", ranking=None, fallbacks=(), transition=transition,
                    selected=SelectedEngine("goose", goose.engine_ref, goose.content_digest),
                    consumed=ConsumedAuthority(1, 120, 40, 2.5, "known", 0.01))


def every_record() -> tuple:
    """One valid instance of each of the ten engine record types."""
    return ((EngineDescriptor, descriptor()), (EngineInstallation, installation()),
            (EngineSlotConfiguration, slot_configuration()), (EngineQualification, qualification()),
            (EngineRetirement, retirement()), (ServiceHostEngines, service_host_engines()),
            (EngineBindingsReport, bindings_report()), (EngineSelectionPolicy, policy()),
            (EngineSelectionOverride, override()), (EngineSelectionDecision, decision()))


def rich_records() -> tuple:
    """Each record again with every optional part filled, so a reader that drops one is caught."""
    from .configuration_capabilities import ConfigurationFact
    from .engine_host_records import (
        BoundEngine, FamilyPolicyInForce, FileReference, QualificationSource)
    from .engine_records import EngineCostBasis, EngineLocality, EvidenceReference, QualificationScope
    engine = descriptor(
        cost_basis=EngineCostBasis("price_record", "pricing/fixture-prices.json", digest("prices"), "2026-09-20"),
        data_recipients=("https://models.example.test",), effects=("pure",), supported_modes=(),
        locality=EngineLocality("core.model_routes.LOCALITIES", "cloud"), lifecycle="candidate",
        implementation_location="checkpoint@a3bd0f1", availability=ConfigurationFact(), checks=())
    installed = goose_installation(
        enabled=False, settings={"placement": "fresh_process", "limits": {"wall_time_seconds": 600}},
        declaration=FileReference("/data/embodiments/goose/harness.json", digest("goose declaration"), absolute=True),
        qualification=QualificationSource("engine_qualification/v1", "artifacts/fixture/goose-q.json", digest("q")))
    reviewed = qualification(
        scope=QualificationScope("step_run_request/v1", None, ()), proof_level="operational_drill",
        ladder_rung=None, decision="rejected",
        evidence=(EvidenceReference("artifacts/fixture/a.json", digest("a")),
                  EvidenceReference("artifacts/fixture/b.json", digest("b"))))
    retired_version = retirement(engine_id="opencode", engine_version="1.0.0", stage="deprecated",
                                 replacement="opencode@2.0.0")
    deprecated_goose = retirement(engine_id="goose", stage="deprecated", replacement="opencode")
    ranked = policy(
        fallback_on=("engine_unavailable", "engine_reported_failure"), allow_unqualified=True,
        ranking=MetaPreferencePolicy(("evidence-ranker", DECLARED_ORDER_ENGINE_REF), ("engine_unavailable",)),
        evidence=EngineEvidenceBinding({"record_type": "engine_evidence_rule/v1", "method": "fixture"},
                                       "snapshots/fixture.json", digest("snapshot")),
        comparison={"record_type": "engine_comparison_policy/v1", "allowance_ref": "grants/fixture.json"},
        retired=(deprecated_goose, retired_version))
    harness_exclude = override(sender=HARNESS, source_kind="intelligence_proposal", kind="exclude")
    objective = override(kind="objective", installations=(), objective="elapsed_seconds")
    outside = EligibilityEntry("cline", (EligibilityRefusal("engine_not_installed", "not in the host file"),))
    evidenced = decision(
        override=(override(kind="prefer", installations=("opencode",)),),
        eligibility=decision().eligibility + (outside,), propensity=Propensity(1, 20),
        evidence=EvidenceUse("ranked_matched_reviewed_evidence", True, {"loss_upper_bound": 0.04, "tail": 0.01},
                             digest("snapshot"), ("history/run-1", "history/run-2"), "adoption/fixture.json"),
        consumed=ConsumedAuthority(3, None, None, 1.5, "unknown", None), parent_decision_digest=digest("parent"))
    return ((EngineDescriptor, engine), (EngineInstallation, installed), (EngineQualification, reviewed),
            (EngineRetirement, retired_version), (EngineSelectionPolicy, ranked),
            (EngineSelectionOverride, harness_exclude), (EngineSelectionOverride, objective),
            (EngineSelectionDecision, evidenced),
            (EngineSlotConfiguration, slot_configuration(
                selection={"default": policy(), "offline": policy(scope_key="offline", retired=(deprecated_goose,))},
                source="projected:models.tiers")),
            (ServiceHostEngines, ServiceHostEngines({"step_executor": slot_configuration(),
                                                    "workspace_backend": slot_configuration(
                                                        slot_id="workspace_backend", selection={"default": policy(
                                                            slot_id="workspace_backend")})})),
            (EngineBindingsReport, EngineBindingsReport(
                digest("host"), {"record_store": BoundEngine(digest("store"), "local.sqlite", "local.sqlite@1.0.0"),
                                 "account_email_delivery": BoundEngine(digest("mail"), "resend", "resend@1.0.0")},
                {"payment_provider": "not_declared", "usage_export": "no_eligible_engine"},
                FamilyPolicyInForce("service_host_family_policy/v1", digest("family"), "declared by the host"))))


def _changed(record: dict, **changes) -> dict:
    value = json.loads(json.dumps(record))
    value.update(changes)
    return value


# Scenarios: each returns True only when its known-wrong cases are refused.

def readers_refuse_unknown_fields_and_versions() -> bool:
    """Known wrong: a policy with an extra key; engine_selection_policy/v2 read by the v1 parser."""
    for kind, value in every_record():
        record = value.to_dict()
        name, _, _ = record["record_type"].rpartition("/")
        first = next(key for key in record if key != "record_type")
        missing = {key: item for key, item in record.items() if key != first}
        if not (refused(lambda: kind.from_dict(_changed(record, unexpected=1)), "unknown_record_fields")
                and refused(lambda: kind.from_dict(_changed(record, record_type=name + "/v2")),
                            "unsupported_record_version")
                and refused(lambda: kind.from_dict(_changed(record, record_type="engine_unknown/v1")),
                            "unknown_record_type")
                and refused(lambda: kind.from_dict(missing), "missing_record_fields")):
            return False
    nested_policy = _changed(policy().to_dict())
    nested_policy["ranking"]["weights"] = [1]
    nested_decision = _changed(decision().to_dict())
    nested_decision["scope"]["owning_team"] = "fixture"
    return (refused(lambda: EngineSelectionPolicy.from_dict(nested_policy), "unknown_record_fields")
            and refused(lambda: EngineSelectionDecision.from_dict(nested_decision), "unknown_record_fields"))


def records_round_trip() -> bool:
    """Known wrong: a record whose digest changes after to_dict and from_dict."""
    for kind, value in every_record() + rich_records() + ((EngineSelectionDecision, fallback_decision()),):
        again = kind.from_dict(json.loads(json.dumps(value.to_dict())))
        if again.content_digest != value.content_digest or again.to_dict() != value.to_dict():
            return False
    return True


def forged_derived_values_are_refused() -> bool:
    """Known wrong: a stored digest, reference or flag edited so it no longer matches the record's content."""
    def forged(kind, value, path, replacement):
        record = _changed(value.to_dict())
        target = record
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        return refused(lambda: kind.from_dict(record), "derived_value_mismatch")
    wrong = digest("edited")
    return (forged(EngineInstallation, installation(), ("installation_digest",), wrong)
            and forged(EngineInstallation, installation(), ("settings_digest",), wrong)
            and forged(EngineDescriptor, descriptor(), ("engine_ref",), "opencode@9.9.9")
            and forged(EngineDescriptor, descriptor(), ("capability_record_digest",), wrong)
            and forged(EngineSelectionDecision, decision(), ("scope", "scope_digest"), wrong)
            and forged(EngineSelectionDecision, decision(), ("eligibility", 0, "eligible"), False)
            and forged(EngineSelectionDecision, decision(), ("evidence", "used"), True))


def policy_states_an_explicit_fallback_choice() -> bool:
    """Known wrong: empty fallbacks with no_fallback false."""
    return (refused(lambda: policy(fallbacks=(), no_fallback=False), "no_fallback_rule")
            and refused(lambda: policy(no_fallback=True), "no_fallback_rule")
            and refused(lambda: policy(initial=()), "no_fallback_rule")
            and refused(lambda: policy(fallback_on=()), "no_fallback_rule")
            and refused(lambda: policy(fallbacks=(), no_fallback=True), "no_fallback_rule")
            and accepted(lambda: policy(fallbacks=(), no_fallback=True, fallback_on=())))


def policy_lists_each_engine_once_and_no_retired_engine() -> bool:
    """Known wrong: an engine in both initial and fallbacks; a retired engine listed;
    an engine the slot configuration does not install."""
    archived = retirement(engine_id="goose", stage="archived", replacement="opencode")
    deprecated_goose = retirement(engine_id="goose", stage="deprecated", replacement="opencode")
    deprecated_first = retirement(engine_id="opencode", stage="deprecated", replacement="goose")
    only_initial = dict(fallbacks=(), no_fallback=True, fallback_on=())
    return (refused(lambda: policy(fallbacks=("opencode",)), "engine_listed_twice")
            and refused(lambda: slot_configuration(selection={"default": policy(retired=(archived,))}),
                        "engine_retired")
            and refused(lambda: slot_configuration(selection={"default": policy(retired=(deprecated_first,))}),
                        "engine_retired")
            and refused(lambda: slot_configuration(selection={"default": policy(**only_initial, retired=(archived,))}),
                        "engine_retired")
            and refused(lambda: slot_configuration(installed=(installation(), goose_installation(enabled=False)),
                                                   selection={"default": policy(retired=(archived,))}),
                        "engine_retired")
            and accepted(lambda: slot_configuration(
                installed=(installation(), goose_installation(enabled=False)),
                selection={"default": policy(**only_initial, retired=(archived,))}))
            and accepted(lambda: slot_configuration(selection={"default": policy(retired=(deprecated_goose,))}))
            and refused(lambda: slot_configuration(selection={"default": policy(fallbacks=("cline",))}),
                        "engine_not_installed"))


def ranking_ends_with_the_declared_order() -> bool:
    """Known wrong: engine_order [evidence-ranker] alone."""
    return (refused(lambda: policy(ranking=MetaPreferencePolicy(("evidence-ranker",))), "declared_order_last")
            and refused(lambda: policy(ranking=MetaPreferencePolicy((DECLARED_ORDER_ENGINE_REF, "evidence-ranker"))),
                        "declared_order_last")
            and accepted(lambda: policy(ranking=MetaPreferencePolicy(("evidence-ranker", DECLARED_ORDER_ENGINE_REF)))))


def decision_flags_stay_false() -> bool:
    """Known wrong: a decision with execution_authority_granted, task_accepted or
    model_call_performed_by_boundary set to true."""
    record = decision().to_dict()
    return all(refused(lambda: EngineSelectionDecision.from_dict(_changed(record, **{name: True})),
                       "constant_flag_changed")
               for name in decision_records.CONSTANT_FALSE_FLAGS) and accepted(
        lambda: EngineSelectionDecision.from_dict(record))


def decision_records_every_refusal_and_propensity() -> bool:
    """Known wrong: a decision listing only the winner; a decision without propensity."""
    winner_only = dict(eligibility=(EligibilityEntry("opencode", ()),), fallbacks=(), no_fallback=True)
    outside = EligibilityEntry("cline", (EligibilityRefusal("engine_not_installed", "not in the host file"),))
    disabled_member = EligibilityEntry("goose", (EligibilityRefusal("engine_disabled", ""),))
    return (refused(lambda: decision(**winner_only), "eligibility_incomplete")
            and refused(lambda: decision(propensity=None), "propensity_required")
            and refused(lambda: decision(status="no_eligible_engine", selected=None, declared_order=(),
                                         order_without_override=(), fallbacks=(), no_fallback=True,
                                         ranking=None), "propensity_required")
            and refused(lambda: decision(eligibility=(EligibilityEntry("opencode", ()), disabled_member),
                                         fallbacks=(), no_fallback=True), "eligibility_incomplete")
            and accepted(lambda: decision(eligibility=decision().eligibility + (outside,))))


def override_records_source_kind_and_sender() -> bool:
    """Known wrong: an override whose source kind is outside ParameterSourceKind, or without its sender."""
    return (refused(lambda: override(source_kind="operator_whim"), "invalid_source_kind")
            and refused(lambda: override(sender=None), "sender_required")
            and accepted(lambda: override(source_kind="loop_profile")))


def override_claims_only_its_senders_precedence() -> bool:
    """Known wrong: a harness preference recorded as a run override; a Loop override
    recorded as deployment configuration; a harness preference that sets an objective."""
    lowest = "intelligence_proposal"
    return (refused(lambda: override(sender=HARNESS), "sender_precedence_exceeded")
            and refused(lambda: override(source_kind="deployment_configuration"), "sender_precedence_exceeded")
            and refused(lambda: override(sender=HARNESS, source_kind=lowest, kind="objective", installations=(),
                                         objective="tokens"), "harness_kind_not_permitted")
            and accepted(lambda: override(sender=HARNESS, source_kind=lowest, kind="exclude")))


def nested_decision_names_its_parent() -> bool:
    """Known wrong: a decision for a nested slot with an empty parent_decision_digest."""
    parent = digest("the step executor decision")
    return (refused(lambda: require_parent_when_nested(decision(), nested=True), "parent_decision_required")
            and refused(lambda: require_parent_when_nested(decision(parent_decision_digest=parent), nested=False),
                        "parent_decision_required")
            and accepted(lambda: require_parent_when_nested(decision(parent_decision_digest=parent), nested=True))
            and accepted(lambda: require_parent_when_nested(decision(), nested=False)))


def decision_orders_only_eligible_installations() -> bool:
    """Known wrong: a declared order naming an engine the host did not install;
    a pin that fails while another engine is selected."""
    pinned = override(kind="pin", installations=("goose",))
    return (refused(lambda: decision(declared_order=("opencode", "cline"),
                                     order_without_override=("opencode", "cline")), "ineligible_engine_ordered")
            and refused(lambda: decision(override=(pinned,)), "pin_substituted")
            and accepted(lambda: decision(override=(override(kind="pin", installations=("opencode",)),),
                                          fallbacks=())))


def fallback_follows_only_a_declared_failure() -> bool:
    """Known wrong: a fallback selected after an uncertain effect or with uncertain accounting."""
    terminal = FallbackTransition("opencode", "opencode@1.2.3", "effects_uncertain", "fixture.loop3", False,
                                  "stop until the effect is reconciled", ())
    return (refused(lambda: fallback_decision(failure_kind="effects_uncertain"), "fallback_not_permitted")
            and refused(lambda: fallback_decision(accounting_uncertain=True), "fallback_not_permitted")
            and accepted(fallback_decision)
            and accepted(lambda: decision(phase="fallback", status="terminal_failure", selected=None,
                                          propensity=None, ranking=None, fallbacks=(), transition=terminal)))


def an_initial_selection_keeps_its_ranking() -> bool:
    """Known wrong: an initial selection recorded without its ranking record."""
    return (refused(lambda: decision(ranking=None), "ranking_required")
            and accepted(decision) and accepted(fallback_decision))


def unknown_consumption_stays_unknown() -> bool:
    """Known wrong: an unknown cost written as zero; a known cost with no amount."""
    return (refused(lambda: ConsumedAuthority(0, 0, 0, 0.0, "unknown", 0.0), "unknown_kept_unknown")
            and refused(lambda: ConsumedAuthority(0, 0, 0, 0.0, "known", None), "unknown_kept_unknown")
            and accepted(lambda: ConsumedAuthority(None, None, None, None, "unknown", None)))


#: Parts whose keys are data rather than fields (maps keyed by slot, scope key,
#: sender or setting), and records whose fields another reader owns: an engine's
#: own capability record, its typed settings, the evidence rule, the comparison
#: policy, the named uncertainty numbers and, in a decision, the embedded ranking.
MAP_PARTS = ("joined_settings", "fingerprint", "bound", "unbound", "selection", "slots", "overrides_permitted")
OPAQUE_PARTS = ("capability_record", "settings", "rule", "comparison", "uncertainty")


def _field_parts(value, path, record_type):
    """The path of every nested object in a serialized record whose keys are fields."""
    if type(value) is list:
        for index, item in enumerate(value):
            yield from _field_parts(item, path + (index,), record_type)
        return
    if type(value) is not dict:
        return
    record_type = value.get("record_type", record_type)
    if path:
        yield path
    for key, item in value.items():
        if key in OPAQUE_PARTS or (key == "ranking" and record_type == decision_records.DECISION_RECORD_TYPE):
            continue
        members = item.items() if key in MAP_PARTS and type(item) is dict else ((None, item),)
        for name, member in members:
            yield from _field_parts(member, path + ((key,) if name is None else (key, name)), record_type)


def every_part_of_every_record_refuses_unknown_fields() -> bool:
    """Known wrong: an unknown field inside any part of any engine record, such as a
    locality, a cost basis, a sender, a declaration file, a bound engine, a refusal
    or the consumed authority, read as if it were not there."""
    parts = 0
    for kind, value in rich_records() + ((EngineSelectionDecision, fallback_decision()),):
        record = json.loads(json.dumps(value.to_dict()))
        for path in _field_parts(record, (), record["record_type"]):
            changed = json.loads(json.dumps(record))
            target = changed
            for key in path:
                target = target[key]
            target["unexpected"] = 1
            parts += 1
            if not refused(lambda: kind.from_dict(changed)):
                return False
    return parts >= 60


def senders_stay_within_their_override_kinds() -> bool:
    """Known wrong: a policy that lets a harness choose an objective, or omits or adds a sender;
    a pin of two installations; an objective named by a preference, or an objective
    override without one; a retirement filed under another slot; a Loop sender that
    names an engine; an evidence rule or a comparison of another record type."""
    loop_kinds = ("pin", "exclude", "prefer")
    return (refused(lambda: policy(overrides_permitted={"loop": loop_kinds, "harness": ("objective",)}),
                    "invalid_vocabulary")
            and refused(lambda: policy(overrides_permitted={"loop": loop_kinds}), "invalid_field")
            and refused(lambda: policy(overrides_permitted={"loop": loop_kinds, "harness": ("prefer",),
                                                            "operator": ("pin",)}), "invalid_field")
            and refused(lambda: override(kind="pin", installations=("opencode", "goose")), "invalid_override")
            and refused(lambda: override(objective="tokens"), "invalid_override")
            and refused(lambda: override(kind="objective", installations=()), "invalid_override")
            and refused(lambda: policy(retired=(retirement(slot_id="workspace_backend"),)), "invalid_field")
            and refused(lambda: OverrideSender("loop", "fixture.loop1", "opencode@1.2.3", None), "invalid_field")
            and refused(lambda: EngineEvidenceBinding({"record_type": "engine_comparison_policy/v1"},
                                                      "snapshots/fixture.json", digest("snapshot")),
                        "invalid_vocabulary")
            and refused(lambda: policy(comparison={"record_type": "engine_evidence_rule/v1"}), "invalid_vocabulary")
            and accepted(lambda: override(kind="pin", installations=("opencode",)))
            and accepted(lambda: override(kind="objective", installations=(), objective="tokens")))


def an_initial_choice_is_the_first_ranked_eligible_engine() -> bool:
    """Known wrong: an initial choice that is not the first engine its ranking ordered,
    or whose ranking abstained or ordered other engines; a choice that eligibility
    refused, or named with another descriptor digest than its universe entry; a choice
    listed as its own fallback; an excluded installation still ordered or chosen."""
    both = dict(declared_order=("opencode", "goose"), order_without_override=("opencode", "goose"),
                fallbacks=(), no_fallback=True)
    goose, opencode = descriptor(engine_id="goose", engine_version="1.0.0"), descriptor()
    to_goose = SelectedEngine("goose", goose.engine_ref, goose.content_digest)
    abstained = {**ranking_record(), "status": "abstained", "ordered_ids": [], "selected_engine_ref": ""}
    goose_refused = (EligibilityEntry("opencode", ()),
                     EligibilityEntry("goose", (EligibilityRefusal("engine_unavailable", ""),)))
    excluded = override(kind="exclude", installations=("opencode",))
    return (refused(lambda: decision(**both, ranking=ranking_record(("opencode", "goose")), selected=to_goose),
                    "invalid_ranking")
            and refused(lambda: decision(**both, ranking=abstained, selected=to_goose), "invalid_ranking")
            and refused(lambda: decision(ranking=abstained), "invalid_ranking")
            and refused(lambda: decision(ranking=ranking_record(("opencode", "goose"))), "invalid_ranking")
            and refused(lambda: replace(fallback_decision(), eligibility=goose_refused), "ineligible_engine_selected")
            and refused(lambda: decision(selected=SelectedEngine("opencode", opencode.engine_ref, digest("other"))),
                        "ineligible_engine_selected")
            and refused(lambda: decision(fallbacks=("opencode",)), "invalid_field")
            and refused(lambda: decision(override=(excluded,)), "excluded_engine_ordered")
            and accepted(lambda: decision(**both, ranking=ranking_record(("opencode", "goose"))))
            and accepted(lambda: decision(override=(override(kind="exclude", installations=("goose",)),),
                                          fallbacks=(), no_fallback=True)))


def a_decision_keeps_its_phase_evidence_propensity_and_parts_consistent() -> bool:
    """Known wrong: an explicit no-fallback beside a fallback chain; a transition outside
    the fallback phase, or a fallback without one; a terminal failure outside a
    fallback; no eligible engine while one is eligible; evidence use that contradicts
    its reason, snapshot or history; an uncertainty that is not a number; a propensity
    outside (0, 1]; a parametrized refusal without its detail; an owning profile that is
    not role.profile@x.y.z; a trace from an unknown source or with a claimed precedence;
    an override for another slot; an embedded ranking that grants anything or has
    another record type; an installation named twice; a negative count."""
    moved = fallback_decision().transition
    snapshot, history = digest("snapshot"), ("history/run-1",)
    ranking = ranking_record()
    universe = decision().universe
    return all(refused(action, code) for action, code in (
        (lambda: decision(no_fallback=True), "no_fallback_rule"),
        (lambda: decision(transition=moved), "invalid_transition"),
        (lambda: replace(fallback_decision(), transition=None), "invalid_transition"),
        (lambda: decision(status="terminal_failure", selected=None, propensity=None), "invalid_transition"),
        (lambda: decision(status="no_eligible_engine", selected=None, propensity=None), "invalid_status"),
        (lambda: EvidenceUse("not_requested", False, "not_computed", snapshot, (), None), "invalid_evidence_use"),
        (lambda: EvidenceUse("not_requested", False, "not_computed", None, history, None), "invalid_evidence_use"),
        (lambda: EvidenceUse("ranked_matched_reviewed_evidence", True, "not_computed", snapshot, (), None),
         "invalid_evidence_use"),
        (lambda: EvidenceUse("insufficient_matched_reviewed_evidence", True, "not_computed", snapshot, history, None),
         "invalid_evidence_use"),
        (lambda: EvidenceUse("insufficient_matched_reviewed_evidence", False, {"tail": True}, snapshot, history, None),
         "invalid_field"),
        (lambda: Propensity(0, 1), "invalid_propensity"),
        (lambda: Propensity(2, 1), "invalid_propensity"),
        (lambda: EligibilityRefusal("permission_not_granted", ""), "invalid_text"),
        (lambda: EligibilityRefusal("incompatible_with_selected", "Model Access"), "invalid_identifier"),
        (lambda: SelectionScope("step_run_request/v1", "code_execution", "fixture.loop1", "response_admission/v1",
                                {}, {}), "invalid_field"),
        (lambda: PolicySource("declared", ({**trace(), "source_kind": "operator_whim"},)), "invalid_vocabulary"),
        (lambda: PolicySource("declared", ({**trace(), "precedence_rank": 1},)), "claimed_precedence"),
        (lambda: decision(override=(override(slot_id="workspace_backend"),)), "invalid_field"),
        (lambda: decision(ranking={**ranking, "task_accepted": True}), "constant_flag_changed"),
        (lambda: decision(ranking={**ranking, "record_type": "configuration_preference_decision/v9"}),
         "invalid_vocabulary"),
        (lambda: decision(universe=universe + universe[:1]), "repeated_value"),
        (lambda: ConsumedAuthority(-1, 0, 0, 0.0, "known", 0.0), "invalid_field"),
    )) and accepted(decision) and accepted(fallback_decision)


CHECKS = (
    ("every_engine_record_refuses_unknown_keys_and_unsupported_versions",
     readers_refuse_unknown_fields_and_versions,
     (("removed_unknown_key_refusal_is_detected", ((records, "_refuse_unknown_fields"),)),
      ("removed_unsupported_version_refusal_is_detected", ((records, "_refuse_unsupported_version"),)))),
    ("records_round_trip_with_identical_digests", records_round_trip, ()),
    ("a_stored_derived_value_that_disagrees_with_its_record_is_refused", forged_derived_values_are_refused,
     (("removed_derived_value_check_is_detected",
       ((records, "require_derived"), (host_records, "require_derived"), (decision_records, "require_derived"))),)),
    ("every_slot_policy_states_an_initial_choice_and_ordered_fallbacks_or_an_explicit_no_fallback",
     policy_states_an_explicit_fallback_choice,
     (("removed_no_fallback_rule_is_detected", ((selection_records, "_require_explicit_fallback_choice"),)),)),
    ("a_policy_lists_an_engine_once_and_never_a_retired_one", policy_lists_each_engine_once_and_no_retired_engine,
     (("removed_repeated_listing_rule_is_detected", ((selection_records, "_refuse_repeated_listing"),)),
      ("removed_retired_listing_rule_is_detected", ((host_records, "_refuse_retired_listing"),)),
      ("removed_uninstalled_listing_rule_is_detected", ((host_records, "_refuse_uninstalled_listing"),)))),
    ("ranking_policy_must_end_with_the_declared_order", ranking_ends_with_the_declared_order,
     (("removed_declared_order_rule_is_detected", ((selection_records, "_require_declared_order_last"),)),)),
    ("decision_flags_are_constant", decision_flags_stay_false,
     (("removed_constant_flag_rule_is_detected", ((decision_records, "_refuse_granting_flags"),)),)),
    ("selection_decision_records_every_rejection_reason_and_its_propensity",
     decision_records_every_refusal_and_propensity,
     (("removed_rejection_coverage_rule_is_detected", ((decision_records, "_require_complete_eligibility"),)),
      ("removed_propensity_rule_is_detected", ((decision_records, "_require_propensity"),)))),
    ("an_override_records_its_source_kind_and_sender", override_records_source_kind_and_sender,
     (("removed_override_source_rule_is_detected", ((selection_records, "_require_override_source"),)),)),
    ("an_override_claims_only_the_precedence_of_its_sender", override_claims_only_its_senders_precedence,
     (("removed_sender_precedence_rule_is_detected", ((selection_records, "_bound_sender_precedence"),)),)),
    ("a_nested_decision_names_its_parent", nested_decision_names_its_parent,
     (("removed_parent_decision_rule_is_detected", ((decision_records, "_require_parent_link"),)),)),
    ("a_decision_orders_and_pins_only_eligible_installations", decision_orders_only_eligible_installations,
     (("removed_eligible_order_rule_is_detected", ((decision_records, "_refuse_widening_order"),)),)),
    ("a_fallback_decision_follows_only_a_declared_failure_with_certain_accounting",
     fallback_follows_only_a_declared_failure,
     (("removed_terminal_fallback_rule_is_detected", ((decision_records, "_refuse_fallback_after_terminal"),)),)),
    ("an_initial_selection_embeds_its_ranking_record", an_initial_selection_keeps_its_ranking,
     (("removed_ranking_record_rule_is_detected", ((decision_records, "_require_ranking_for_an_initial_selection"),)),)),
    ("consumed_authority_keeps_unknown_apart_from_zero", unknown_consumption_stays_unknown,
     (("removed_unknown_cost_rule_is_detected", ((decision_records, "_keep_unknown_cost_unknown"),)),)),
    ("an_initial_choice_is_the_first_ranked_eligible_engine", an_initial_choice_is_the_first_ranked_eligible_engine,
     (("removed_first_ranked_rule_is_detected", ((decision_records, "_require_first_ranked_selection"),)),
      ("removed_exclusion_rule_is_detected", ((decision_records, "_refuse_excluded_order"),)))),
    ("a_decision_keeps_its_phase_evidence_propensity_and_parts_consistent",
     a_decision_keeps_its_phase_evidence_propensity_and_parts_consistent,
     (("removed_claimed_precedence_rule_is_detected", ((decision_records, "_refuse_claimed_precedence"),)),)),
    # Rules written inline in the readers and records: source mutants confirm
    # that removing each one fails the check.
    ("every_part_of_every_engine_record_refuses_unknown_fields", every_part_of_every_record_refuses_unknown_fields,
     ()),
    ("a_policy_and_an_override_stay_within_the_kinds_their_sender_may_use", senders_stay_within_their_override_kinds,
     ()),
)


def run_checks() -> dict:
    tests = []

    def check(name, passed):
        tests.append({"name": name, "passed": bool(passed)})

    for name, scenario, controls in CHECKS:
        check(name, _observe(scenario))
        for control, removed in controls:
            with ExitStack() as stack:
                for module, guard in removed:
                    stack.enter_context(patch.object(module, guard, lambda *args, **kwargs: None))
                check(control, _observe(scenario) is False)
    return {"tests": tests, "passed": sum(t["passed"] for t in tests), "total": len(tests),
            "all_passed": all(t["passed"] for t in tests)}


def _observe(scenario) -> bool:
    try:
        return bool(scenario())
    except Exception:
        return False


def self_test() -> dict:
    return run_checks()
