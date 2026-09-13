"""Controls for the layering availability projection: one state per
address, exact reasons shared with the semantic binding, summary counts
that agree with a brute-force walk, and refusals of malformed input.
"""
from __future__ import annotations

import json

from .harness_fallback import HarnessFailureKind, HarnessFallbackPolicy
from .harness_layering import (ControlOwnership, HarnessLayeringError, NativeControl,
                               NativeControlPolicy, WrapperLayer)
from .harness_layering_availability import (ADAPTER_DOES_NOT_DECLARE, COMPOSITION_WITHOUT_EXECUTOR,
                                            DECLARED_WITHOUT_EXECUTOR, EXECUTABLE_NOW,
                                            OUTER_POLICY_REFUSES, STATES, availability_summary,
                                            classify_address, executor_refusal)
from .harness_layering_space import CompositionSpace, ControlPolicySpace, LayeringSpace


def _policy(**owned) -> NativeControlPolicy:
    ownership = dict(NativeControlPolicy.owning_loop_for_everything().ownership)
    for control, owner in owned.items():
        ownership[NativeControl[control]] = ControlOwnership[owner]
    return NativeControlPolicy(ownership)


def fixtures(*, allow_native_retry=False, controls=("goal_management", "retry_and_fallback")):
    prep = WrapperLayer("prep", "1", ("instruction_preparation",))
    meter = WrapperLayer("meter", "1", ("accounting",))
    compositions = CompositionSpace("codex", (prep, meter), 2)
    policies = ControlPolicySpace(controls)
    outer = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,),
                                  allow_native_retry=allow_native_retry)
    return LayeringSpace("assignment:availability", compositions, policies, outer)


def _refused(operation) -> bool:
    try:
        operation()
    except HarnessLayeringError:
        return True
    return False


def run_checks():
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:160]})

    space = fixtures()
    goal = space.policies.index_of(_policy(GOAL="DELEGATED"))
    retry = space.policies.index_of(_policy(RETRY="DELEGATED"))
    first = classify_address(space, 0)
    check("address_zero_executes_now_with_no_reason",
          first["state"] == EXECUTABLE_NOW and first["reason"] == "")
    layered = classify_address(space, space.encode(1, 0))
    check("a_layered_composition_has_no_executor_and_says_so",
          layered["state"] == COMPOSITION_WITHOUT_EXECUTOR
          and "no executor is registered for a layered composition" in layered["reason"])
    undeclared = classify_address(space, space.encode(0, goal))
    check("a_natively_owned_control_the_adapter_does_not_declare_is_named",
          undeclared["state"] == ADAPTER_DOES_NOT_DECLARE
          and "does not support native ownership" in undeclared["reason"]
          and "goal_management" in undeclared["reason"] and "'codex'" in undeclared["reason"])
    declared = classify_address(space, space.encode(0, goal), ("goal_management",))
    check("a_declared_control_without_an_executor_is_distinct_from_an_undeclared_one",
          declared["state"] == DECLARED_WITHOUT_EXECUTOR
          and "no executor hands it to the harness yet" in declared["reason"])
    refused = classify_address(space, space.encode(0, retry), ("retry_and_fallback",))
    check("the_outer_policy_refuses_native_retry_before_any_executor_question",
          refused["state"] == OUTER_POLICY_REFUSES and "allow_native_retry" in refused["reason"])
    permitted = fixtures(allow_native_retry=True)
    allowed = classify_address(permitted, permitted.encode(0, retry), ("retry_and_fallback",))
    check("with_the_outer_permission_native_retry_is_a_declared_control_awaiting_an_executor",
          allowed["state"] == DECLARED_WITHOUT_EXECUTOR)
    check("a_layered_composition_is_refused_before_its_control_policy_is_judged",
          classify_address(space, space.encode(1, goal))["state"] == COMPOSITION_WITHOUT_EXECUTOR)

    for name, walk in (("without_permission", space), ("with_permission", permitted)):
        summary = availability_summary(walk, ("goal_management",))
        brute = {state: 0 for state in STATES}
        executable = []
        for index in range(walk.size):
            row = classify_address(walk, index, ("goal_management",))
            brute[row["state"]] += 1
            if row["state"] == EXECUTABLE_NOW:
                executable.append(index)
        check(f"summary_counts_{name}_agree_with_a_brute_force_walk",
              summary["counts"] == brute and summary["executable_now_indices"] == executable
              and sum(brute.values()) == walk.size, json.dumps(summary["counts"]))
    summary = availability_summary(space, ("goal_management",))
    non_native = [space.encode(0, index) for index in range(space.policies.size)
                  if space.policies.policy_at(index).natively_owned() == ()]
    check("executable_addresses_are_exactly_the_direct_adapter_under_non_native_policies",
          summary["executable_now_indices"] == non_native
          and len(non_native) == 2 ** len(NativeControl)
          and all(space.policies.policy_at(space.decode(i)[1]).owner_of(NativeControl.GOAL)
                  in (ControlOwnership.OWNING_LOOP, ControlOwnership.DISABLED) for i in non_native))
    check("the_summary_record_is_portable_and_names_its_space",
          json.loads(json.dumps(summary)) == summary
          and summary["layering_space_digest"] == space.content_digest
          and summary["size"] == space.size and summary["harness_id"] == "codex"
          and summary["executors_registered"] == {"direct_adapter": True, "wrapper_layers": False,
                                                  "native_controls": []})
    wide = LayeringSpace("assignment:availability",
                         CompositionSpace("codex", tuple(WrapperLayer(f"w{i}", "1", ("instruction_preparation",))
                                                         for i in range(9)), 3),
                         ControlPolicySpace(), space.fallback_policy)
    total = availability_summary(wide)
    check("a_wide_composition_space_is_summarised_without_walking_it",
          wide.compositions.size == 1 + 9 + 72 + 504 and total["size"] == wide.size
          and total["counts"][COMPOSITION_WITHOUT_EXECUTOR] == 256 * (wide.compositions.size - 1)
          and total["counts"][EXECUTABLE_NOW] == 256
          and total["counts"][ADAPTER_DOES_NOT_DECLARE] == 0)
    mismatched = LayeringSpace("assignment:availability", space.compositions, space.policies,
                               HarnessFallbackPolicy(("opencode", "codex"),
                                                     (HarnessFailureKind.UNAVAILABLE,)))
    check("a_space_whose_harness_is_not_the_outer_primary_is_refused_everywhere",
          availability_summary(mismatched)["counts"][OUTER_POLICY_REFUSES] == mismatched.size)
    check("an_unknown_control_name_is_refused",
          _refused(lambda: classify_address(space, 0, ("telepathy",)))
          and _refused(lambda: availability_summary(space, "goal_management")))
    check("an_address_outside_the_space_is_an_error_not_a_state",
          _refused(lambda: classify_address(space, space.size))
          and _refused(lambda: classify_address(space, True)))
    check("a_binding_is_required_for_a_refusal_verdict",
          _refused(lambda: executor_refusal({}, "codex")))
    return {"module": "core.harness_layering_availability", "tests": tests,
            "passed": sum(1 for item in tests if item["passed"]), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
