"""Offline mutations for public assignment-folder provisioning.

Mutations replace in-memory functions and are always restored. The fixture
model never contacts a provider and all writes stay in temporary folders.
"""
import inspect
import json
import textwrap

from loop_engine.code_nodes import solve_provisioning_checks, solve_request_adaptation, solve_runtime
from loop_engine.core import adaptive_practitioner_scope, spawned_provisioning
from loop_engine.core.practitioner_runtime import provisioning


def helper_suite():
    return spawned_provisioning.self_test()["tests"]


def public_suite():
    return solve_provisioning_checks.run_checks()


def scope_suite():
    return adaptive_practitioner_scope.self_test()["tests"]


def changed(function, module, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(before) != 1:
        raise RuntimeError("mutation target must occur once")
    namespace = dict(vars(module))
    exec(compile(source.replace(before, after), "<provisioning-mutant>", "exec"), namespace)
    return namespace[function.__name__]


def observe(name, owner, attribute, replacement, suite):
    original = getattr(owner, attribute)
    setattr(owner, attribute, replacement)
    try:
        try:
            failures = [item.get("test", item.get("name")) for item in suite() if not item["passed"]]
            return {"mutant": name, "detected": bool(failures), "failed_checks": failures}
        except Exception as error:
            return {"mutant": name, "detected": True, "check_exception": type(error).__name__,
                    "detail": str(error)[:200]}
    finally:
        setattr(owner, attribute, original)


if __name__ == "__main__":
    if not all(item["passed"] for item in (*helper_suite(), *public_suite(), *scope_suite())):
        raise RuntimeError("unchanged owning checks must pass before mutation")
    targets = (
        ("omit_public_dependency_wiring", solve_runtime, "solve_dependencies", solve_runtime,
         "harness_provisioning=request.harness_provisioning", "harness_provisioning=None", public_suite),
        ("omit_request_identity_binding", solve_runtime, "build_adaptive_request", solve_request_adaptation,
         "harness_provisioning_digest=(request.harness_provisioning.content_digest", "harness_provisioning_digest=(\"\"", public_suite),
        ("grant_preparation_without_authority", spawned_provisioning, "provision_spawned", spawned_provisioning,
         "if configuration.preparation_writes_authorized is not True:", "if False:", helper_suite),
        ("infer_behavior_from_write_permission", spawned_provisioning, "provision_spawned", spawned_provisioning,
         "kind=choice.kind", "kind=('build' if request.allow_workspace_writes else 'reason')", helper_suite),
        ("skip_exact_resource_pin", provisioning.HarnessProvisioningConfiguration, "catalogue_for", provisioning,
         "if item is None or HarnessResourceBinding.from_item(item) != binding:", "if item is None:", helper_suite),
        ("offer_unselected_catalogue_entries", provisioning.HarnessProvisioningConfiguration, "catalogue_for", provisioning,
         "return selected", "for extra in entries:\n        selected.register(replace(extra, default_exposure='metadata_only'))\n    return selected", helper_suite),
        ("retain_reason_assignment_write_authority", adaptive_practitioner_scope, "fork_services", adaptive_practitioner_scope,
         "reason_only = choice is not None and choice.kind == \"reason\"", "reason_only = False", scope_suite),
        ("drop_guardrails_before_preparation", spawned_provisioning, "provision_spawned", spawned_provisioning,
         "guardrails=configuration.guardrail_set()", "guardrails=None", helper_suite),
        ("claim_native_loading_from_a_folder", spawned_provisioning, "_decision", spawned_provisioning,
         '"native_loading_observed": False', '"native_loading_observed": True', helper_suite),
        ("grant_model_authority_without_a_session", spawned_provisioning, "provision_spawned", spawned_provisioning,
         'getattr(services, "model_session", None) is not None', 'True', helper_suite),
        ("ignore_exact_assignment_override", provisioning.HarnessProvisioningConfiguration, "assignment_for", provisioning,
         'return dict(self.assignment_overrides).get(assignment_id, self.assignment)', 'return self.assignment', public_suite),
        ("skip_request_configuration_revalidation", spawned_provisioning, "configuration_for", spawned_provisioning,
         'if getattr(services.request, "harness_provisioning_digest", "") != expected:', 'if False:', helper_suite),
        ("silently_accept_unimplemented_guardrail_points", provisioning.HarnessProvisioningConfiguration, "__post_init__", provisioning,
         'if field_name == "guardrails_json" and any(', 'if False and any(', helper_suite),
        ("present_guidance_as_enforcement", provisioning.HarnessProvisioningConfiguration, "to_dict", provisioning,
         '"dispatch_or_publication_guardrails_installed": False', '"dispatch_or_publication_guardrails_installed": True', helper_suite),
    )
    observations = [observe(name, owner, attribute,
        changed(getattr(owner, attribute), module, before, after), suite)
        for name, owner, attribute, module, before, after, suite in targets]
    print(json.dumps({"record_type": "provisioning_mutants/v1", "provider_calls": 0,
                      "mutants": observations, "all_detected": all(item["detected"] for item in observations)}, indent=2))
    raise SystemExit(0 if all(item["detected"] for item in observations) else 1)
