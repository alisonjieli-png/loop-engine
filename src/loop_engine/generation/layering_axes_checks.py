"""Offline controls for layering axes: address agreement, decoding, space
binding, admissibility reporting, composition with other axes, and the
proposal filter. Fixtures are authored; no wrapper or native control runs.
"""
from __future__ import annotations

import json

from ..core.harness_fallback import HarnessFailureKind, HarnessFallbackPolicy
from ..core.harness_layering import (ControlOwnership, NativeControl, NativeControlPolicy,
                                     WrapperLayer)
from ..core.harness_layering_space import (CompositionSpace, ControlPolicySpace,
                                           LayeringSpace)
from .layering_axes import (COMPOSITION_DIMENSION, FILTER_RECORD_TYPE, INADMISSIBLE_RULE,
                            POLICY_DIMENSION, SPACE_DIGEST_FIELD, address_availability,
                            iter_admissible,
                            layering_axes, layering_binding, layering_configuration_space,
                            layering_exclusions, layering_fields, layering_index,
                            refuse_inadmissible_proposals)
from .model.fragments import GenerationError
from .search import GridSearchAdapter, propose_configurations
from .search_records import SearchObjective, SearchRequest, SearchServices, SearchTask
from .space import ConfigurationAxis, content_digest


def fixtures():
    prep = WrapperLayer("prep", "1", ("instruction_preparation",))
    bridge = WrapperLayer("bridge", "1", ("native_session_bridge", "accounting"),
                          depends_on=("prep",))
    meter = WrapperLayer("meter", "1", ("accounting",))
    transport = WrapperLayer("transport", "1", ("transport",))
    compositions = CompositionSpace("codex", (prep, bridge, meter, transport), 3)
    policies = ControlPolicySpace(("goal_management", "planning_and_continuation"))
    outer = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,))
    return LayeringSpace("assignment:layering-axes", compositions, policies, outer)


def retry_fixtures():
    compositions = fixtures().compositions
    policies = ControlPolicySpace(("retry_and_fallback",))
    outer = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,))
    permitted = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,),
                                      allow_native_retry=True)
    delegated = NativeControlPolicy(
        {**NativeControlPolicy.owning_loop_for_everything().ownership,
         NativeControl.RETRY: ControlOwnership.DELEGATED})
    return (LayeringSpace("assignment:layering-axes", compositions, policies, outer),
            LayeringSpace("assignment:layering-axes", compositions, policies, permitted),
            policies.index_of(delegated))


def _refused(operation) -> bool:
    try:
        operation()
    except GenerationError:
        return True
    return False


def run_checks():
    tests = []

    def check(name, value):
        tests.append({"name": name, "passed": bool(value)})

    layering = fixtures()
    policy_axis, composition_axis = layering_axes(layering)
    check("axes_are_integer_ranges_sized_by_the_layering_spaces",
          policy_axis.value_kind == composition_axis.value_kind == "integer_range"
          and policy_axis.cardinality == layering.policies.size
          and composition_axis.cardinality == layering.compositions.size)
    two_axis = layering_configuration_space(layering, "layering-only")
    check("a_two_axis_space_has_exactly_the_layering_size",
          two_axis.cardinality == layering.size)
    sampled = range(0, layering.size, 7)
    check("every_sampled_address_agrees_with_the_layering_space_arithmetic",
          all(layering_index(layering, two_axis.configuration_at(index)) == index
              and two_axis.index_of(two_axis.configuration_at(index)) == index
              for index in sampled))
    first = layering_binding(layering, two_axis.configuration_at(0))
    check("address_zero_is_the_direct_adapter_owned_by_the_loop",
          first.initial.is_direct_adapter and first.control_policy.natively_owned() == ()
          and first.fallback_policy is layering.fallback_policy)
    last = layering_binding(layering, two_axis.configuration_at(layering.size - 1))
    check("the_last_address_names_a_binding_the_layering_space_also_names",
          last.content_digest == layering.candidate_at(layering.size - 1).content_digest)
    check("the_fields_of_a_decoded_binding_round_trip_to_the_same_address",
          all(two_axis.index_of(layering_fields(layering, layering.candidate_at(index))) == index
              for index in sampled))
    foreign = dict(two_axis.configuration_at(3))
    foreign[SPACE_DIGEST_FIELD] = content_digest("another layering space")
    check("a_configuration_addressed_in_another_layering_space_is_refused",
          _refused(lambda: layering_index(layering, foreign))
          and _refused(lambda: layering_exclusions(layering, foreign)))
    for name, broken in (("missing_axis", {k: v for k, v in two_axis.configuration_at(3).items()
                                           if k != COMPOSITION_DIMENSION}),
                         ("boolean_index", {**two_axis.configuration_at(3), POLICY_DIMENSION: True}),
                         ("out_of_range", {**two_axis.configuration_at(3),
                                           COMPOSITION_DIMENSION: layering.compositions.size})):
        check(f"a_{name}_configuration_is_refused", _refused(lambda: layering_index(layering, broken)))
    check("the_digest_field_cannot_be_supplied_as_caller_context",
          _refused(lambda: layering_configuration_space(
              layering, "x", context={SPACE_DIGEST_FIELD: "mine"})))

    without, with_permission, delegated_policy = retry_fixtures()
    plain = layering_configuration_space(without, "retry-space")
    allowed = layering_configuration_space(with_permission, "retry-space")
    delegated = plain.configuration_at(without.encode(0, delegated_policy))
    permitted = allowed.configuration_at(with_permission.encode(0, delegated_policy))
    check("a_native_retry_address_is_reported_inadmissible_without_the_outer_permission",
          layering_exclusions(without, delegated) == (INADMISSIBLE_RULE,)
          and layering_exclusions(with_permission, permitted) == ()
          and _refused(lambda: layering_binding(without, delegated)))
    check("the_outer_permission_changes_the_space_digest_so_addresses_do_not_cross",
          plain.digest != allowed.digest and _refused(lambda: layering_index(without, permitted)))
    walked = [index for index, _ in iter_admissible(without, plain, start=0, stride=1)]
    check("the_lazy_walk_skips_only_the_refused_addresses_and_keeps_identity",
          without.encode(0, delegated_policy) not in walked
          and 0 in walked and len(walked) == sum(1 for i in range(without.size)
                                                  if without.admissible(i)))

    composed = layering_configuration_space(layering, "layering-with-model", extra_axes=(
        ConfigurationAxis("model", "categorical", ('"local"', '"cloud"')),),
        context={"task_family": "tabular"})
    check("other_axes_and_context_compose_around_the_layering_axes",
          composed.cardinality == layering.size * 2
          and composed.configuration_at(1)["model"] == "cloud"
          and composed.configuration_at(1)["task_family"] == "tabular"
          and layering_index(layering, composed.configuration_at(2 * 5 + 1)) == 5)
    check("space_records_are_portable_json",
          json.loads(json.dumps(composed.to_dict())) == composed.to_dict())

    task = SearchTask("layering-task", content_digest("task"), "task/layering@1.0.0",
                      "evaluator@1.0.0")
    request = SearchRequest(plain, task, (SearchObjective("loss@1.0.0", "minimize"),),
                            batch_size=plain.cardinality, draw_limit=plain.cardinality, seed=1)
    batch = propose_configurations(request, SearchServices(GridSearchAdapter()))["value"]
    filtered = refuse_inadmissible_proposals(without, batch)
    proposed = {item["configuration_index"] for item in batch["proposals"]}
    check("exact_enumeration_proposes_every_layering_address_before_admissibility",
          proposed == set(range(plain.cardinality)))
    check("the_filter_separates_refused_addresses_without_altering_the_search_record",
          filtered["record_type"] == FILTER_RECORD_TYPE
          and filtered["admissible_count"] + filtered["refused_count"] == len(batch["proposals"])
          and filtered["refused_count"] == sum(1 for i in range(without.size)
                                                if not without.admissible(i))
          and all(item["layering_reasons"] == [INADMISSIBLE_RULE]
                  for item in filtered["refused_proposals"])
          and "layering_reasons" not in batch["proposals"][0]
          and filtered["layering_space_digest"] == without.content_digest
          and not filtered["task_execution_performed"] and not filtered["promotion_performed"])
    check("the_filter_refuses_a_batch_from_another_space",
          _refused(lambda: refuse_inadmissible_proposals(layering, batch)))
    states = {index: address_availability(without, plain.configuration_at(index))["state"]
              for index in range(plain.cardinality)}
    runnable = [without.encode(0, p) for p in range(without.policies.size)
                if without.policies.policy_at(p).natively_owned() == ()]
    check("every_address_reports_one_availability_state_and_only_the_direct_adapter_runs_today",
          states[0] == "executable_now"
          and [i for i, s in states.items() if s == "executable_now"] == runnable
          and all(without.decode(i)[0] == 0 for i in runnable)
          and states[without.encode(0, delegated_policy)] == "outer_policy_refuses"
          and states[without.encode(1, 0)] == "composition_without_executor"
          and _refused(lambda: address_availability(without, delegated, ("telepathy",))))
    return {"tests": tests}
