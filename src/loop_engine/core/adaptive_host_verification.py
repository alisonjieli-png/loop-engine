"""Bind host observations to the adaptive Practitioner's acceptance gates.

Host endpoints own their physical capabilities and task checks. This helper
routes their issued verification reports through the existing pass record;
an accepted observation does not imply that the user's task is complete.
"""
from __future__ import annotations

from dataclasses import replace


def bind_host_request(request, dependencies):
    """Freeze the host declaration before an adaptive run admits any work."""
    manifest = (dependencies.host_runtime.summary()
                if dependencies.host_runtime is not None else {})
    if request.host_runtime_manifest and request.host_runtime_manifest != manifest:
        raise ValueError("host runtime manifest differs from the supplied binding")
    return (replace(request, host_runtime_manifest=manifest)
            if request.host_runtime_manifest != manifest else request)


def create_adaptive_owner(request, dependencies, config, ledger):
    """Bind the host port to the same resolved canonical Practitioner baseline."""
    from ..loop.loop_definition import LoopDefinition, LoopStartRequest
    from ..loop.loop_doctrine import baseline_for_practitioner
    from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from ..loop.recursive_loop import Loop
    from ..loop.runtime_context import LoopRuntimeContext

    identity = LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.reference_nine_step")
    relationship = LoopRelationship.starting()
    if dependencies.host_runtime is None:
        return Loop(request.task, config, ledger=ledger, identity=identity,
                    relationship=relationship)
    definition = LoopDefinition.from_runtime(
        identity=identity,
        contract=baseline_for_practitioner(request.task, output_roles=("result",)),
        config=config, installed_executor_modes=config.allowable_modes, compatibility=True)
    base = LoopRuntimeContext.compatibility(
        capabilities=definition.required_capabilities, permissions=definition.permissions,
        executor_modes=definition.installed_executor_modes)
    return Loop(LoopStartRequest(request.task, definition, relationship,
                                dependencies.host_runtime.runtime_context(base), ledger))


def validate_action_permissions(decision, services):
    """Admit declared host intent without expanding the core effect authority."""
    if decision.action_kind == "REQUEST_AUTHORITY":
        return
    host = getattr(services.dependencies, "host_runtime", None)
    selected = tuple(decision.required_capabilities)
    if selected and host is not None and all(host.supports(ref) for ref in selected):
        granted = {name for ref in selected for name in host.permissions_for(ref)}
    else:
        from .practitioner_runtime_facts import granted_permissions
        granted = set(granted_permissions(services.request))
    if set(decision.permissions) - granted:
        raise PermissionError("NextActionDecision requests permission outside selected capability authority")


def _host_results(results):
    return tuple((index, item.result) for index, item in enumerate(results)
                 if isinstance(item.result, dict)
                 and item.result.get("record_type") == "host_operation_result/v1")


def verify_host_results(results, services, owner_loop):
    """Ask the configured host verifier about each actual host observation."""
    hosts = _host_results(results)
    if not hosts:
        return []
    from .host_runtime import verify_host_result
    entries = []
    for index, result in hosts:
        entry = {"result_index": index, "report": None}
        try:
            if result.get("ok") is not True:
                raise ValueError("host operation did not complete successfully")
            entry["report"] = verify_host_result(
                services.request.task, result, services, owner_loop)
        except Exception as exc:  # noqa: BLE001 - a host callback failure cannot grant acceptance
            entry["error"] = f"Host verification unavailable: {type(exc).__name__}: {str(exc)[:300]}"
            services.diagnostic("host_verification_unavailable", {
                "result_index": index, "error_type": type(exc).__name__})
        entries.append(entry)
    return entries


def require_host_checks(record, results, services, owner_loop, *, task_complete=False):
    """Require issued current-state evidence; completion is a separate gate."""
    hosts = _host_results(results)
    if not hosts:
        return
    from .host_runtime import validate_host_verification
    entries = record.get("host_checks")
    if not isinstance(entries, list) or len(entries) != len(hosts):
        raise ValueError("every host result requires its issued verification")
    selected = record.get("evaluation", {}).get("best_index")
    for index, result in hosts:
        matches = [entry for entry in entries if isinstance(entry, dict)
                   and type(entry.get("result_index")) is int
                   and entry["result_index"] == index]
        if len(matches) != 1:
            raise ValueError("host verification result selection is ambiguous")
        entry, report = matches[0], matches[0].get("report")
        if (entry.get("error") or not isinstance(report, dict)
                or report.get("status") != "passed"):
            raise ValueError(str(entry.get("error") or "host observation verification has not passed"))
        validate_host_verification(report, services.request.task, result, services, owner_loop)
        if task_complete and index == selected and report.get("task_complete") is not True:
            raise ValueError("host verification confirms an observation, but the task is incomplete")
    if task_complete and selected not in {index for index, _result in hosts}:
        raise ValueError("final host acceptance requires one selected verified host result")


def self_test():
    from .adaptive_host_runtime_checks import run_checks
    return run_checks()
