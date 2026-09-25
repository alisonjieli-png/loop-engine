"""Offline preference, meta-selection, and existing-search composition controls.

Authored proposals test admission only. They are not real model calls, learned
policies, or evidence that one selector solves tasks better than another.
"""
from dataclasses import replace

from .configuration_capabilities import ConfigurationFact, canonical, digest
from .configuration_preferences import (
    ExistingOrderPreference, ExplicitOrderPreference, MetaPreferencePolicy,
    PreferenceCandidate, PreferenceEngineBinding, PreferenceProposal,
    PreferenceSelectionRequest, PreferenceSnapshot, SuppliedAgentPreference,
    resolve_preference, resolve_preference_as_loop)
from .configuration_setter_checks import NOW, fact


def engine(name, adapter, **changes):
    return replace(PreferenceEngineBinding(name, adapter, fact("available"),
        ("configuration", "preference_engine", "search_adapter", "harness", "model_route"),
        "offline-preference-fixture@1.0.0", digest("fixture:" + name), fact("qualified")), **changes)


def run_checks():
    tests = []
    def check(name, passed):
        tests.append({"name": name, "passed": bool(passed)})
    def refuses(name, fn):
        try:
            fn()
        except (ValueError, TypeError):
            check(name, True)
        else:
            check(name, False)
    snapshot = PreferenceSnapshot("configuration", digest("task-and-setting-scope"),
        tuple(PreferenceCandidate(name) for name in ("first", "second", "third")))
    existing = engine("existing@1.0.0", ExistingOrderPreference())
    explicit = engine("explicit@1.0.0", ExplicitOrderPreference(("second",)))
    base = PreferenceSelectionRequest(snapshot, MetaPreferencePolicy((explicit.engine_ref, existing.engine_ref)),
                                      (explicit, existing), NOW)
    run = resolve_preference_as_loop(base)
    check("configuration_preference_uses_canonical_loop", run["model_calls"] == 0
          and run["loop_id"].startswith("loop") and run["loop_definition_id"])
    selected = run["value"]
    check("explicit_preference_retains_every_eligible_choice", selected["ordered_ids"] == ["second", "first", "third"])
    check("preference_does_not_execute_or_accept_a_task", not selected["task_accepted"]
          and not selected["execution_authority_granted"] and not selected["model_call_performed_by_boundary"])
    supplied = PreferenceProposal(snapshot.content_digest, ("third", "first", "second"),
        "offline-agent-proposal@1.0.0", ("fixture-proposal-record@1.0.0",), "agentic_proposal")
    agent = engine("agent-proposal@1.0.0", SuppliedAgentPreference(supplied))
    chosen = replace(base, policy=MetaPreferencePolicy((agent.engine_ref,)), engines=(agent,))
    admitted = resolve_preference_as_loop(chosen)
    check("supplied_agent_proposal_is_admitted_without_a_fabricated_call",
          admitted["value"]["ordered_ids"] == ["third", "first", "second"] and admitted["model_calls"] == 0)
    for name, changed in (
        ("stale_scope", replace(supplied, snapshot_digest=digest("different-scope"))),
        ("invented_choice", replace(supplied, ordered_ids=("third", "first", "unregistered"))),
        ("omitted_choice", replace(supplied, ordered_ids=("third", "first")))):
        bad = engine("bad@1.0.0", SuppliedAgentPreference(changed))
        rejected = resolve_preference(replace(base, policy=MetaPreferencePolicy((bad.engine_ref,)), engines=(bad,)))
        check(name + "_cannot_change_eligibility", rejected["status"] == "abstained"
              and rejected["attempts"][0]["result"] == "invalid_proposal")
    unavailable = replace(explicit, availability=fact("unavailable"))
    refused = resolve_preference(replace(base, engines=(unavailable, existing)))
    check("engine_failure_does_not_enable_implicit_fallback", refused["status"] == "abstained" and len(refused["attempts"]) == 1)
    policy = replace(base.policy, fallback_on=("engine_unavailable", "engine_unqualified", "target_kind_unsupported"))
    recovered = resolve_preference(replace(base, policy=policy, engines=(unavailable, existing)))
    check("explicit_engine_fallback_preserves_failed_attempt", recovered["ordered_ids"] == ["first", "second", "third"]
          and [r["result"] for r in recovered["attempts"]] == ["engine_unavailable", "valid_ordering"])
    for name, bad in (
        ("unknown_availability", replace(explicit, availability=ConfigurationFact())),
        ("expired_availability", replace(explicit, availability=fact("available", expires_at="2026-09-12T00:00:00Z"))),
        ("unqualified", replace(explicit, qualification=fact("unqualified"))),
        ("wrong_target", replace(explicit, target_kinds=("harness",)))):
        decided = resolve_preference(replace(base, policy=policy, engines=(bad, existing)))
        check(name + "_uses_only_authorized_fallback", decided["selected_engine_ref"] == existing.engine_ref
              and len(decided["attempts"]) == 2)
    unqualified = replace(base, policy=replace(base.policy, allow_unqualified=True),
        engines=(replace(explicit, qualification=ConfigurationFact()), existing))
    check("host_can_allow_an_unqualified_proposal_experiment",
          resolve_preference(unqualified)["selected_engine_ref"] == explicit.engine_ref)
    cycle = resolve_preference(replace(base, policy=replace(policy, active_engine_refs=(explicit.engine_ref,))))
    check("active_selector_cycle_refuses_without_fallback", cycle["status"] == "abstained"
          and cycle["attempts"] == [{"engine_ref": explicit.engine_ref, "result": "selector_cycle"}])
    empty = resolve_preference(replace(base, snapshot=replace(snapshot, candidates=())))
    check("empty_eligible_set_is_not_a_recommendation", empty["status"] == "no_eligible_choices" and not empty["attempts"])
    unknown = resolve_preference(replace(base, policy=MetaPreferencePolicy(("unknown@1.0.0",))))
    check("unregistered_engine_is_unavailable", unknown["attempts"][0]["result"] == "engine_unavailable")
    class MutableAdapter:
        def __init__(self):
            self.bias = "first"
            self.calls = 0
        def descriptor(self):
            return {"method": "offline_mutation_fixture", "bias": self.bias}
        def rank(self, snapshot):
            self.calls += 1
            raise ValueError("private provider diagnostic must not enter public report")
    mutable = MutableAdapter()
    bound = engine("mutable@1.0.0", mutable)
    mutable.bias = "third"
    failed = resolve_preference(replace(base, policy=MetaPreferencePolicy((bound.engine_ref,)), engines=(bound,)))
    check("changed_engine_settings_refuse_before_callback", mutable.calls == 0
          and failed["attempts"][0]["result"] == "engine_failed")
    mutable.bias = "first"
    failed = resolve_preference(replace(base, policy=MetaPreferencePolicy((bound.engine_ref,)), engines=(bound,)))
    check("adapter_failure_text_is_not_exported", mutable.calls == 1 and "private provider" not in canonical(failed))
    refuses("duplicate_engine_priorities_are_refused", lambda: MetaPreferencePolicy(("same", "same")))
    refuses("unknown_fallback_triggers_are_refused", lambda: MetaPreferencePolicy(("same",), ("anything",)))
    refuses("agent_ordering_needs_proposal_evidence", lambda: replace(supplied, evidence_refs=()))
    refuses("duplicate_choice_in_proposal_is_refused", lambda: replace(supplied, ordered_ids=("first", "first")))
    refuses("opaque_candidate_attributes_are_refused", lambda: PreferenceCandidate("first", '{"x":NaN}'))
    _meta_checks(check, base, existing, explicit)
    _search_checks(check)
    _harness_checks(check)

    class RepeatingAdapter:
        def descriptor(self):
            return {"method": "offline_repeating_fixture"}

        def rank(self, snapshot):
            first = snapshot.candidates[0].candidate_id
            return PreferenceProposal(snapshot.content_digest, (first, first), "repeating@1.0.0")
    repeating = engine("repeating@1.0.0", RepeatingAdapter())
    invalid = resolve_preference(replace(base, policy=MetaPreferencePolicy((repeating.engine_ref,)),
                                         engines=(repeating,)))
    check("an_invalid_proposal_from_rank_is_not_an_engine_crash",
          invalid["attempts"][0]["result"] == "invalid_proposal" and invalid["status"] == "abstained")
    import json
    check("the_decision_record_is_json_plain", json.loads(json.dumps(invalid)) == invalid)
    return {"tests": tests, "passed": sum(t["passed"] for t in tests), "total": len(tests),
            "all_passed": all(t["passed"] for t in tests)}


def _meta_checks(check, base, existing, explicit):
    from ..loop.recursive_loop import Loop
    owner = Loop("offline meta preference control")
    engine_snapshot = PreferenceSnapshot("preference_engine", base.snapshot.content_digest,
        tuple(PreferenceCandidate(e.engine_ref, canonical(e.to_dict())) for e in (existing, explicit)))
    chooser = engine("meta-choice@1.0.0", ExplicitOrderPreference((explicit.engine_ref,)))
    meta_request = PreferenceSelectionRequest(engine_snapshot, MetaPreferencePolicy((chooser.engine_ref,)),
                                              (chooser,), NOW)
    meta = resolve_preference_as_loop(meta_request, parent=owner)
    downstream = resolve_preference_as_loop(replace(base, policy=MetaPreferencePolicy(
        tuple(meta["value"]["ordered_ids"]), active_engine_refs=(chooser.engine_ref,))), parent=owner)
    check("meta_selector_selects_an_engine_before_configuration_ranking",
          meta["value"]["ordered_ids"][0] == explicit.engine_ref
          and downstream["value"]["ordered_ids"][0] == "second"
          and meta["loop_id"] != downstream["loop_id"])
    other = replace(chooser, adapter=ExplicitOrderPreference((existing.engine_ref,)))
    next_meta = resolve_preference(replace(meta_request, engines=(other,)))
    next_downstream = resolve_preference(replace(base, policy=MetaPreferencePolicy(tuple(next_meta["ordered_ids"]))))
    check("changing_meta_selector_configuration_changes_the_downstream_choice",
          next_downstream["ordered_ids"][0] == "first")
    check("meta_selection_retains_exact_engine_descriptors",
          meta["value"]["engines"][0]["configuration"]["preferred_ids"] == [explicit.engine_ref]
          and downstream["value"]["snapshot_digest"] == base.snapshot.content_digest)


def _search_checks(check):
    from ..generation.search import GridSearchAdapter, RandomSearchAdapter, propose_configurations
    from ..generation.search_records import SearchObjective, SearchRequest, SearchServices, SearchTask
    from ..generation.space import ConfigurationAxis, ConfigurationSpace
    space = ConfigurationSpace("preference-control", "1.0.0",
        (ConfigurationAxis("setting", "integer_range", minimum=0, maximum=999),))
    task = SearchTask("offline-meta-control", digest("fixture-task"), "task/fixture@1.0.0", "fixture-evaluator@1.0.0")
    request = SearchRequest(space, task, (SearchObjective("fixture-loss@1.0.0", "minimize"),),
                            batch_size=2, draw_limit=4, seed=42)
    adapters = (GridSearchAdapter(), RandomSearchAdapter())
    candidates = tuple(PreferenceCandidate(a.adapter_ref, canonical(a.settings())) for a in adapters)
    snapshot = PreferenceSnapshot("search_adapter", request.digest, candidates)
    outputs = []
    for adapter in adapters:
        chooser = engine("search-choice@1.0.0", ExplicitOrderPreference((adapter.adapter_ref,)))
        selection = resolve_preference_as_loop(PreferenceSelectionRequest(snapshot,
            MetaPreferencePolicy((chooser.engine_ref,)), (chooser,), NOW))
        selected = next(a for a in adapters if a.adapter_ref == selection["value"]["ordered_ids"][0])
        batch = propose_configurations(request, SearchServices(selected))
        outputs.append(batch)
    check("selected_search_adapter_reaches_existing_proposal_boundary",
          [r["value"]["adapter_ref"] for r in outputs] == [a.adapter_ref for a in adapters]
          and all(len(r["value"]["proposals"]) == 2 for r in outputs)
          and outputs[0]["value"]["proposals"][0]["configuration_index"] == 0
          and outputs[1]["value"]["proposals"][0]["configuration_index"] != 0)
    check("meta_search_control_does_not_claim_task_execution", all(
        not r["value"]["task_execution_performed"] and r["model_calls"] == 0 for r in outputs))


def _harness_checks(check):
    from .external_harness import HarnessAdapterInfo
    from .harness_execution_contracts import HarnessExecutionCapabilities, HarnessExecutionRequirements
    from .harness_selection import select_harness
    from .harness_selection_records import HarnessSelectionPolicy, HarnessSelectionScope
    scope = HarnessSelectionScope("fixture.answer/v1", digest("response"), "practitioner.solver@1.0.0",
        digest("resources"), digest("settings"), digest("definition"),
        requirements=HarnessExecutionRequirements(required_features=("model_routes",)))
    registrations = tuple(HarnessAdapterInfo(name, "1.0.0", "offline_fixture", available=True,
        execution_capabilities=HarnessExecutionCapabilities(supported_features=features))
        for name, features in (("first", ("model_routes",)), ("second", ("model_routes",)), ("unsupported", ())))
    decision = select_harness(HarnessSelectionPolicy(scope.resource_profile_digest, (), 1), scope, registrations,
                              provider_id="fixture", model_id="fixture-model")
    snapshot = PreferenceSnapshot("harness", digest(decision.to_dict()),
                                  tuple(PreferenceCandidate(i) for i in decision.ordered_harness_ids))
    chooser = engine("harness-preference@1.0.0", ExplicitOrderPreference(("second",)))
    selected = resolve_preference(PreferenceSelectionRequest(snapshot, MetaPreferencePolicy((chooser.engine_ref,)),
                                                              (chooser,), NOW))
    check("existing_harness_screen_precedes_preference", selected["ordered_ids"] == ["second", "first"]
          and "unsupported" not in decision.ordered_harness_ids)
    forged = replace(chooser, adapter=ExplicitOrderPreference(("unsupported",)))
    refused = resolve_preference(PreferenceSelectionRequest(snapshot, MetaPreferencePolicy((forged.engine_ref,)),
                                                             (forged,), NOW))
    check("preference_cannot_restore_a_hard_rejected_harness", refused["status"] == "abstained")
