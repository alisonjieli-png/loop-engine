"""Prepare a Spawned Practitioner's assignment folder under exact authority.

The immutable host configuration chooses behavior, metadata references, and
guardrails. Preparation writes are separate from worker permissions. This
connector installs no resource bodies, launches no harness, and claims no
native loading or independent admission from catalogue membership.
"""
from __future__ import annotations

from pathlib import Path

from .harness_intelligence import HarnessIntelligenceCatalogue
from .node_provisioning import BUILD, NodeAssignment, NodeProvisioningError, provision
from .practitioner_runtime.provisioning import (
    HarnessProvisioningConfiguration, ProvisioningConfigurationError,
)

RECORD_TYPE = "spawned_provisioning/v2"


class SpawnedProvisioningError(NodeProvisioningError):
    """Preparation was refused; the decision is retained for the owning Loop."""

    def __init__(self, reason, record):
        super().__init__(reason)
        self.record = {**record, "reason": reason, "status": "refused"}


def configuration_for(services):
    """Check the immutable dependency against the request's admitted identity."""
    configuration = getattr(services.dependencies, "harness_provisioning", None)
    if configuration is not None and not isinstance(configuration, HarnessProvisioningConfiguration):
        raise ProvisioningConfigurationError("provisioning requires its immutable configuration")
    expected = configuration.content_digest if configuration is not None else ""
    if getattr(services.request, "harness_provisioning_digest", "") != expected:
        raise ProvisioningConfigurationError("provisioning configuration changed after request admission")
    return configuration


def effects_for(request, choice) -> tuple[str, ...]:
    """Narrow worker workspace effects; assignment kind never grants writes."""
    if choice.workspace_effects is not None:
        if "writes_fs" in choice.workspace_effects and request.allow_workspace_writes is not True:
            raise ProvisioningConfigurationError("assignment writes exceed the owning task authority")
        return choice.workspace_effects
    return (("reads_fs", "writes_fs")
            if choice.kind == BUILD and request.allow_workspace_writes is True
            else ("reads_fs",))


def runtime_permissions_for(request, choice) -> tuple[bool, bool]:
    """Resolve workspace and command permissions before constructing a worker."""
    if choice is None:
        return request.allow_workspace_writes, request.allow_sandbox_commands
    writes = "writes_fs" in effects_for(request, choice)
    commands = choice.allow_sandbox_commands
    inherited_commands = getattr(request, "allow_sandbox_commands", False) is True
    if commands is True and not inherited_commands:
        raise ProvisioningConfigurationError("assignment commands exceed the owning task authority")
    if commands is None:
        commands = choice.kind == BUILD and writes
    return writes, bool(commands and inherited_commands)


def _decision(node_id, configuration):
    return {"record_type": RECORD_TYPE, "node_id": node_id, "provisioned": False,
            "status": "not_configured", "reason": "not_configured", "files_written": [],
            "configuration_digest": configuration.content_digest if configuration is not None else None,
            "catalogue_available": bool(configuration is not None and configuration.catalogue_json),
            "guardrails_available": bool(configuration is not None and configuration.guardrails_json),
            "resource_bodies_installed": 0, "resource_admission_established": False,
            "native_loading_observed": False}


def provision_spawned(services, *, node_id: str, objective: str,
                      output_contract_refs=(), dependency_ids=()) -> dict:
    """Prepare one folder or retain an explicit absence/refusal decision.

    An absent catalogue means no intelligence references, not a populated default.
    A supplied empty catalogue is distinct. Guardrails still apply to assignment
    preparation in both cases, and a refusal prevents the assignment from running.
    """
    configuration = configuration_for(services)
    decision = _decision(node_id, configuration)
    if configuration is None:
        return decision
    if configuration.preparation_writes_authorized is not True:
        raise SpawnedProvisioningError("preparation_writes_not_authorized", decision)
    workspace = getattr(services, "workspace_base", None)
    if workspace is None:
        raise SpawnedProvisioningError("no_workspace", decision)
    choice = configuration.assignment_for(node_id)
    request = services.request
    _writes, commands = runtime_permissions_for(request, choice)
    assignment_effects = effects_for(request, choice) + (("spawns_process",) if commands else ())
    assignment = NodeAssignment(
        node_id=node_id, kind=choice.kind, objective=objective,
        output_contract_refs=tuple(output_contract_refs), dependency_ids=tuple(dependency_ids),
        effects=assignment_effects, harness_style=choice.harness_style,
        model_calls_authorized=(getattr(services, "model_session", None) is not None
                                and request.mode in ("hybrid", "non_deterministic")),
        mode=request.mode)
    decision["assignment_configuration"] = choice.to_dict()
    folder = Path(workspace)
    try:
        from .adaptive_practitioner_scope import validate_scope_workspace
        validate_scope_workspace(services)
        if not folder.is_absolute() or folder.resolve() != folder:
            raise NodeProvisioningError("assignment folder must be an absolute path without symbolic links")
        folder.mkdir(parents=True, exist_ok=True)
        catalogue = configuration.catalogue_for(choice)
        placed = provision(
            assignment, catalogue=catalogue if catalogue is not None else HarnessIntelligenceCatalogue(),
            root=folder, guardrails=configuration.guardrail_set(), tags=choice.tag_set(),
            reporting=("Return the result named by the output contract. No worker file writes are authorized. "
                       "The owning Loop independently checks acceptance."
                       if "writes_fs" not in assignment.effects else ""))
    except (ValueError, OSError, RuntimeError) as exc:
        raise SpawnedProvisioningError(str(exc), decision) from exc
    return {**placed.to_dict(), **decision, "provisioned": True,
            "status": "provisioned", "reason": "", "files_written": list(placed.files_written)}


def self_test() -> dict:
    from .spawned_provisioning_checks import run_checks
    return run_checks()
