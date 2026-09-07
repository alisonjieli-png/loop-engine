"""Offline conformance checks for optional host-owned completion gates.

These trusted fixtures use the canonical host path with no network or model.
They test admission and acceptance, not the semantic quality of arbitrary
host callbacks or statistical completeness of a property-test generator.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import tempfile


def _add(fixture, replies):
    from ..loop.effect_approval import EffectClass, EffectSpec
    from .capability_directory import CapabilityHandshake, Endpoint
    from .host_runtime import HostOperationBinding

    checks = []
    for index, reply in enumerate(replies):
        name = "fixture_completion_" + str(index)

        def callback(*, request, response=reply, label=name):
            fixture.calls.append((label, request))
            if isinstance(response, Exception):
                raise response
            return response(request) if callable(response) else deepcopy(response)

        fixture.binding.directory.register(CapabilityHandshake(
            name, "static_component", "Independently check one bounded host condition.",
            ("validate",), effects=("reads_fs",), max_response_bytes=8192),
            (Endpoint("validate", callback),))
        checks.append(HostOperationBinding(
            name, "validate", {"type": "object"}, {"type": "object"},
            lambda request, label=name: EffectSpec(EffectClass.LOCAL_READ, label, request.scope_ref),
            name + "@1.0.0"))
    fixture.binding = replace(fixture.binding, completion_verifiers=tuple(checks))
    return fixture


def _reply(passed=True, complete=True):
    return {"passed": passed, "task_complete": complete,
            "observations": {"property": "fixture-independent-condition", "counterexample": not passed},
            "notes": "Source-bound fixture check."}


def run_checks():
    from ..loop.effect_approval import ApprovalDecision
    from ..loop.kernel import ResultPacket
    from .adaptive_host_runtime_checks import _fixture, _services
    from .adaptive_host_verification import require_host_checks
    from .host_runtime import (
        HostOperationRequest, HostRuntimeError, invoke_host_operation,
        validate_host_verification, verify_host_result,
    )

    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "offline host callbacks, zero provider calls"})

    def exercise(fixture, root):
        services, owner = _services(root, fixture)
        result = invoke_host_operation(HostOperationRequest(fixture.action.capability_ref, {}),
                                       services, owner)
        report = verify_host_result(services.request.task, result, services, owner)
        accepted = True
        try:
            require_host_checks({"evaluation": {"best_index": 0},
                "host_checks": [{"result_index": 0, "report": report}]},
                (ResultPacket("fixture result", result=result),), services, owner,
                task_complete=True)
        except (ValueError, KeyError, TypeError):
            accepted = False
        return services, owner, result, report, accepted

    for label, replies, status, accepted in (
            ("all_pass", (_reply(), _reply()), "passed", True),
            ("counterexample", (_reply(False, False),), "failed", False),
            ("incomplete", (_reply(True, False),), "passed", False),
            ("missing_completion", ({"passed": True, "observations": {}, "notes": "missing"},),
             "unavailable", False),
            ("non_boolean", ({**_reply(), "passed": 1},), "unavailable", False),
            ("unavailable", (ValueError("checker unavailable"),), "unavailable", False),
            ("partial_then_unavailable", (_reply(False, False), ValueError("second unavailable")),
             "unavailable", False)):
        with tempfile.TemporaryDirectory(prefix="host-completion-") as root:
            fixture = _add(_fixture(), replies)
            _, _, _, report, actual = exercise(fixture, root)
            check("completion_gate_" + label + "_controls_final_acceptance",
                  actual is accepted and report["status"] == status
                  and report["task_complete"] is accepted
                  and report["record_type"] == "host_verification_report/v2")
            if label == "all_pass":
                check("completion_gates_are_separate_registered_non_model_tools",
                      len(fixture.approvals) == 4
                      and len(report["completion_checks"]) == 2
                      and all(not fixture.binding.supports(spec.capability_ref)
                              for spec in fixture.binding.completion_verifiers)
                      and len(fixture.binding.descriptors()) == 1)
            if label == "partial_then_unavailable":
                check("completed_negative_gate_survives_later_checker_failure",
                      len(report.get("completion_checks", ())) == 1
                      and report["completion_checks"][0]["passed"] is False
                      and report["observations"]["completion_checks"][0]["passed"] is False)

    for label, primary in (("intermediate", {"complete": False}),
                           ("failed", {"passed": False})):
        with tempfile.TemporaryDirectory(prefix="host-primary-short-circuit-") as root:
            fixture = _add(_fixture(**primary), (_reply(),))
            _, _, _, report, accepted = exercise(fixture, root)
            check("primary_" + label + "_does_not_invoke_completion_gates",
                  not accepted and report["task_complete"] is False
                  and [kind for kind, _ in fixture.calls] == ["operation", "verifier"]
                  and report["completion_checks"] == [])

    with tempfile.TemporaryDirectory(prefix="host-legacy-completion-") as root:
        fixture = _fixture()
        _, _, _, report, accepted = exercise(fixture, root)
        check("unconfigured_completion_gates_leave_legacy_manifest_and_call_count_unchanged",
              accepted and fixture.binding.summary()["record_type"] == "host_runtime_binding/v1"
              and "completion_verifiers" not in fixture.binding.summary()
              and report["record_type"] == "host_verification_report/v1"
              and "completion_checks" not in report and len(fixture.calls) == 2)

    with tempfile.TemporaryDirectory(prefix="host-completion-drift-") as root:
        fixture = _fixture()

        def drift(_request):
            fixture.state["revision"] += 1
            return _reply()

        fixture = _add(fixture, (drift,))
        _, _, _, report, accepted = exercise(fixture, root)
        check("completion_gate_state_drift_cannot_certify_old_source",
              not accepted and report["status"] == "unavailable"
              and report["task_complete"] is False)

    with tempfile.TemporaryDirectory(prefix="host-completion-denial-") as root:
        fixture = _add(_fixture(), (_reply(),))
        original = fixture.binding.authorize
        fixture.binding = replace(fixture.binding, authorize=lambda request:
            ApprovalDecision.reject(request.request_id, "fixture_host_authority")
            if request.effect.operation.startswith("fixture_completion") else original(request))
        _, _, _, report, accepted = exercise(fixture, root)
        check("completion_check_requires_its_own_exact_effect_approval",
              not accepted and report["status"] == "unavailable"
              and len(fixture.calls) == 2)

    with tempfile.TemporaryDirectory(prefix="host-completion-tamper-") as root:
        fixture = _add(_fixture(), (_reply(),))
        services, owner, result, report, accepted = exercise(fixture, root)
        forged = deepcopy(report)
        forged["completion_checks"] = []
        try:
            validate_host_verification(forged, services.request.task, result, services, owner)
            refused = False
        except HostRuntimeError:
            refused = True
        check("completion_evidence_cannot_be_removed_from_an_issued_report", accepted and refused)
        spec = fixture.binding.completion_verifiers[0]
        fixture.binding.directory._ep[(spec.surface, spec.operation)].fn = lambda **_: _reply()
        try:
            validate_host_verification(report, services.request.task, result, services, owner)
            refused = False
        except HostRuntimeError:
            refused = True
        check("completion_callback_drift_invalidates_previous_acceptance", refused)

    fixture = _add(_fixture(), (_reply(),))
    check("completion_policy_changes_the_bound_manifest_identity",
          fixture.binding.summary()["record_type"] == "host_runtime_binding/v2"
          and fixture.binding.summary()["binding_digest"] !=
          replace(fixture.binding, completion_verifiers=()).summary()["binding_digest"])
    for label, specs in (
            ("duplicate", (fixture.binding.verifier,)),
            ("producer", (fixture.action,)),
            ("untyped", ({"name": "not authority"},)),
            ("mutable_container", list(fixture.binding.completion_verifiers))):
        try:
            replace(fixture.binding, completion_verifiers=specs)
            refused = False
        except (HostRuntimeError, ValueError, TypeError):
            refused = True
        check("completion_binding_refuses_" + label, refused)

    return tests
