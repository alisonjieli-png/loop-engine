"""Local mutation checks for deadline honesty and explicit failover authority."""
from dataclasses import fields, replace
import inspect
import json
import textwrap

from loop_engine.loop import spawned_deadline, spawned_deadline_checks
from loop_engine.core import model_gateway


def deadline_suite():
    return spawned_deadline_checks.run_deadline_checks()


def gateway_suite():
    return model_gateway.self_test()["tests"]


def observe(name, owner, attribute, replacement, suite):
    original = getattr(owner, attribute)
    setattr(owner, attribute, replacement)
    try:
        tests = suite()
        failures = [item["test"] for item in tests if not item["passed"]]
        return {"mutant": name, "detected": bool(failures), "failed_checks": failures}
    finally:
        setattr(owner, attribute, original)


def changed_function(function, module, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(before) != 1:
        raise RuntimeError("mutation target is not unique")
    namespace = dict(vars(module))
    if module is spawned_deadline:
        namespace["monotonic"] = lambda: spawned_deadline.monotonic()
    exec(compile(source.replace(before, after), "<deadline-failover-mutant>", "exec"), namespace)
    return namespace[function.__name__]


if __name__ == "__main__":
    if not all(item["passed"] for item in (*deadline_suite(), *gateway_suite())):
        raise RuntimeError("the unchanged owning checks must pass before mutation")
    original_retain = spawned_deadline.retain_deadline_result
    original_assessment = spawned_deadline.SpawnedDeadlineAssessment.to_dict
    replay = changed_function(spawned_deadline.execute_synchronous_spawned, spawned_deadline,
        "        value = manager._executor(manager._request(record))",
        "        manager._executor(manager._request(record))\n"
        "        value = manager._executor(manager._request(record))")
    unsupported = changed_function(spawned_deadline.execute_synchronous_spawned, spawned_deadline,
        "    if require_preemptive_deadline:", "    if False:")
    suppress_explicit = changed_function(model_gateway.ModelGateway._routes, model_gateway,
        "    if not config.allow_failover:", "    if True:")
    default_values = list(model_gateway.ModelGatewayConfig.__init__.__defaults__)
    field_names = [item.name for item in fields(model_gateway.ModelGatewayConfig)]
    if len(default_values) != len(field_names):
        raise RuntimeError("gateway default mutation needs the complete generated signature")
    default_values[field_names.index("allow_failover")] = True
    observations = [
        observe("accept_a_late_synchronous_result", spawned_deadline,
                "retain_deadline_result", lambda result, assessment: result, deadline_suite),
        observe("discard_late_returned_outputs", spawned_deadline,
                "retain_deadline_result", lambda result, assessment:
                replace(original_retain(result, assessment), outputs=())
                if assessment.exceeded else result, deadline_suite),
        observe("claim_physical_cancellation_from_a_deadline", spawned_deadline.SpawnedDeadlineAssessment,
                "to_dict", lambda self: {**original_assessment(self),
                                        "physical_cancellation_confirmed": True}, deadline_suite),
        observe("replay_the_synchronous_callback", spawned_deadline,
                "execute_synchronous_spawned", replay, deadline_suite),
        observe("allow_unsupported_preemption_requirement", spawned_deadline,
                "execute_synchronous_spawned", unsupported, deadline_suite),
        observe("restore_implicit_provider_failover", model_gateway.ModelGatewayConfig.__init__,
                "__defaults__", tuple(default_values), gateway_suite),
        observe("ignore_explicit_failover_authority", model_gateway.ModelGateway,
                "_routes", suppress_explicit, gateway_suite),
    ]
    print(json.dumps({"record_type": "deadline_failover_mutants/v1", "provider_calls": 0,
                      "mutants": observations,
                      "all_detected": all(item["detected"] for item in observations)}, indent=2))
    raise SystemExit(0 if all(item["detected"] for item in observations) else 1)
