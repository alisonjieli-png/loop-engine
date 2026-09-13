"""Controls for the layering configuration target: settings, allowed values
from the availability projection, facts bound to its digest, inspection
through the setters' view, and refusals of untyped input.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json

from .configuration_capabilities import ConfigurationCapabilityError, ConfigurationFact, digest
from .harness_fallback import HarnessFailureKind, HarnessFallbackPolicy
from .harness_layering import HarnessLayeringError, WrapperLayer
from .harness_layering_availability import EXECUTABLE_NOW, classify_address
from .harness_layering_configuration import (
    AVAILABILITY_SOURCE_REF, COMPOSITION_SETTING, LAYERING_CONFIGURATION_RECORD_TYPE,
    POLICY_SETTING, LayeringConfiguration, describe_layering_configuration,
    layering_configuration_record, layering_configuration_target)
from .harness_layering_space import CompositionSpace, ControlPolicySpace, LayeringSpace

NOW = datetime(2026, 9, 13, 20, 0, tzinfo=timezone.utc)


def fixtures(*, harness="codex"):
    prep = WrapperLayer("prep", "1", ("instruction_preparation",))
    meter = WrapperLayer("meter", "1", ("accounting",))
    compositions = CompositionSpace(harness, (prep, meter), 2)
    policies = ControlPolicySpace(("goal_management",))
    outer = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,))
    return LayeringSpace("assignment:layering-configuration", compositions, policies, outer)


def _refused(operation, error=(HarnessLayeringError, ConfigurationCapabilityError)) -> bool:
    try:
        operation()
    except error:
        return True
    return False


def run_checks():
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:160]})

    space = fixtures()
    source = ("assignment:layering-configuration@1.0.0", digest("assignment"))
    target = layering_configuration_target(space, source_ref=source[0], source_digest=source[1])
    by_id = {setting.parameter_id: setting for setting in target.settings}
    check("the_target_carries_the_two_layering_settings",
          set(by_id) == {POLICY_SETTING, COMPOSITION_SETTING}
          and by_id[POLICY_SETTING].target_field == "control_policy_index"
          and by_id[COMPOSITION_SETTING].target_field == "composition_index"
          and target.target_ref == "harness_layering:assignment:layering-configuration")
    executable_policies = sorted({space.decode(index)[1] for index in range(space.size)
                                  if classify_address(space, index)["state"] == EXECUTABLE_NOW})
    policy = by_id[POLICY_SETTING].parameter()
    composition = by_id[COMPOSITION_SETTING].parameter()
    check("allowed_values_are_exactly_the_policies_whose_direct_adapter_executes_today",
          policy.constraints["allowed_values"] == executable_policies
          and len(executable_policies) == 2 ** 8
          and policy.constraints["maximum"] == space.policies.size - 1
          and composition.constraints["allowed_values"] == [0]
          and composition.constraints["maximum"] == space.compositions.size - 1)
    check("facts_are_supported_and_available_and_cite_the_projection",
          all(s.support.state == "supported" and s.availability.state == "available"
              and s.qualification.state == "unknown"
              and s.support.source_ref == AVAILABILITY_SOURCE_REF
              and len(s.support.source_digest) == 64
              and s.availability.source_digest == s.support.source_digest
              for s in target.settings)
          and all(set(s.run_modes) == {"hybrid", "non_deterministic"} for s in target.settings))
    refused_everywhere = fixtures(harness="opencode")
    unavailable = layering_configuration_target(refused_everywhere, source_ref=source[0],
                                                source_digest=source[1])
    check("a_space_the_outer_policy_refuses_everywhere_is_unavailable_with_no_allowed_values",
          all(s.availability.state == "unavailable" for s in unavailable.settings)
          and all(s.parameter().constraints["allowed_values"] == [] for s in unavailable.settings))
    declared = layering_configuration_target(space, source_ref=source[0], source_digest=source[1],
                                             adapter_native_controls=("goal_management",))
    check("declaring_a_native_control_changes_the_projection_and_the_target_digest",
          declared.content_digest != target.content_digest
          and declared.settings[0].support.source_digest != target.settings[0].support.source_digest)
    qualified = ConfigurationFact("qualified", "independent-evidence@1.0.0", digest("evidence"))
    with_evidence = layering_configuration_target(space, source_ref=source[0], source_digest=source[1],
                                                  qualification=qualified)
    check("a_supplied_qualification_fact_is_carried_and_never_invented",
          all(s.qualification.state == "qualified" for s in with_evidence.settings)
          and all(s.qualification.state == "unknown" for s in target.settings))
    configuration = LayeringConfiguration(0, 0)
    view = describe_layering_configuration(space, configuration, at=NOW,
                                           source_ref=source[0], source_digest=source[1])
    rows = {row["parameter_id"]: row for row in view["settings"]} if "settings" in view else {}
    check("the_direct_adapter_configuration_is_inspected_through_the_setters_view",
          isinstance(view, dict)
          and (rows.get(POLICY_SETTING, {}).get("availability") == "available"
               if rows else any("available" in json.dumps(v) for v in view.values())),
          json.dumps(view)[:150])
    binding = configuration.binding(space)
    check("a_configuration_round_trips_through_its_binding",
          binding.initial.is_direct_adapter
          and LayeringConfiguration.from_binding(space, binding) == configuration
          and LayeringConfiguration.from_binding(space, space.candidate_at(space.encode(1, 3)))
          == LayeringConfiguration(3, 1))
    record = layering_configuration_record(space, source_ref=source[0], source_digest=source[1])
    check("the_joined_record_is_portable_and_keeps_the_declared_remainder_visible",
          record["record_type"] == LAYERING_CONFIGURATION_RECORD_TYPE
          and json.loads(json.dumps(record)) == record
          and record["availability"]["counts"]["composition_without_executor"] > 0
          and record["target"]["target_digest"] == target.content_digest)
    check("untyped_input_is_refused",
          _refused(lambda: layering_configuration_target({}, source_ref=source[0], source_digest=source[1]))
          and _refused(lambda: LayeringConfiguration(-1, 0))
          and _refused(lambda: LayeringConfiguration(True, 0))
          and _refused(lambda: layering_configuration_target(
              space, source_ref=source[0], source_digest=source[1], qualification="qualified"))
          and _refused(lambda: describe_layering_configuration(
              space, {"control_policy_index": 0}, at=NOW, source_ref=source[0], source_digest=source[1])))
    return {"module": "core.harness_layering_configuration", "tests": tests,
            "passed": sum(1 for item in tests if item["passed"]), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
