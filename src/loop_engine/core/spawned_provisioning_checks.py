"""Offline contracts for exact assignment-folder provisioning.

The checks use temporary folders and body-free catalogue snapshots. They do
not launch a native harness, qualify code, or prove provider integration.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from .guardrail_intelligence import Guardrail, GuardrailSet
from .harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceDraft, item_from_body
from .intelligence_tagging import TagSet
from .node_provisioning import ASSIGNMENT_FILE, PROVISIONING_FILE, NodeAssignment
from .practitioner_runtime.provisioning import (
    HarnessAssignmentConfiguration, HarnessProvisioningConfiguration,
    HarnessResourceBinding, ProvisioningConfigurationError,
)
from .spawned_provisioning import SpawnedProvisioningError, configuration_for, effects_for, provision_spawned


def fixture_catalogue():
    catalogue = HarnessIntelligenceCatalogue()
    for draft, body in (
            (HarnessIntelligenceDraft("skill.read_source", "skill", "Read the source",
                "context_intelligence", "ctx.read_source/v1", "MIT"), "Reviewed source-reading procedure."),
            (HarnessIntelligenceDraft("tool.write_report", "tool", "Write a report",
                "code_intelligence", "code.write_report/v1", "MIT",
                declared_effects=("reads_fs", "writes_fs")), "uninstalled candidate body"),
            (HarnessIntelligenceDraft("skill.unselected", "skill", "Unselected procedure",
                "context_intelligence", "ctx.unselected/v1", "MIT"), "Never offered.")):
        catalogue.register(item_from_body(draft, body))
    return catalogue


def fixture_configuration(*, kind="reason", catalogue=None, rules=None, preparation=True,
                          resources=None, overrides=(), style="claude_code", tags=None):
    catalogue = fixture_catalogue() if catalogue is None else catalogue
    selected = ("skill.read_source", "tool.write_report") if resources is None else resources
    choice = HarnessAssignmentConfiguration(
        kind, style, tuple(HarnessResourceBinding.from_item(catalogue.items[key]) for key in selected),
        json.dumps((tags or TagSet({})).to_dict()))
    return HarnessProvisioningConfiguration.bind(
        assignment=choice, catalogue=catalogue, guardrails=rules,
        preparation_writes_authorized=preparation, assignment_overrides=overrides)


def fixture_services(folder, configuration, *, writes=False, mode="hybrid", session=True):
    return SimpleNamespace(
        request=SimpleNamespace(allow_workspace_writes=writes, mode=mode,
            harness_provisioning_digest=configuration.content_digest if configuration is not None else ""),
        dependencies=SimpleNamespace(harness_provisioning=configuration),
        workspace_base=Path(folder) / "spawned" / "1", workspace_scope_root=Path(folder),
        model_session=object() if session else None)


def run_checks():
    from .spawned_provisioning import configuration_for, provision_spawned

    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed), "detail": "offline temporary-folder check"})

    def refused(action, expected=ValueError):
        try:
            action()
        except expected:
            return True
        return False

    catalogue = fixture_catalogue()
    rules = GuardrailSet()
    rules.register(Guardrail("guard.contract", "Require a declared output", "process", "block",
        "before_provisioning", "proceed without an output contract", evidence_required=("output_contract_refs",)))
    configuration = fixture_configuration(catalogue=catalogue, rules=rules)
    digest = configuration.content_digest
    catalogue.items.clear()
    rules.rules.clear()
    check("immutable_snapshots_survive_mutation_of_supplied_catalogue_and_guardrails",
          configuration.content_digest == digest
          and len(configuration.catalogue_for(configuration.assignment).items) == 2
          and len(configuration.guardrail_set().rules) == 1)
    returned = configuration.catalogue_for(configuration.assignment)
    returned.items.clear()
    check("snapshot_materializations_are_fresh_and_body_free",
          len(configuration.catalogue_for(configuration.assignment).items) == 2
          and configuration.to_dict()["resource_bodies_included"] is False
          and all(item.default_exposure == "metadata_only"
                  for item in configuration.catalogue_for(configuration.assignment).items.values()))
    check("versions_and_exact_resource_pins_are_required",
          refused(lambda: replace(configuration, schema_version="harness_provisioning_configuration/v0"))
          and refused(lambda: replace(configuration, assignment=replace(configuration.assignment,
              resources=(replace(configuration.assignment.resources[0], digest="0" * 64),)))))
    check("duplicate_snapshot_fields_and_repeated_assignment_ids_are_refused",
          refused(lambda: replace(configuration, catalogue_json='{"record_type":"x","record_type":"y","items":[]}'))
          and refused(lambda: replace(configuration, assignment_overrides=(
              ("same", configuration.assignment), ("same", configuration.assignment)))))
    check("resource_selection_without_a_catalogue_is_refused",
          refused(lambda: replace(configuration, catalogue_json="")))
    check("guardrails_without_an_installed_owning_path_are_refused",
          all(refused(lambda point=point: fixture_configuration(rules=GuardrailSet({
              "guard.unsupported": Guardrail("guard.unsupported", "Unsupported point", "process", "block",
                  point, "proceed without required enforcement")})))
              for point in ("before_dispatch", "on_output", "before_publication")))
    check("explicit_kind_and_write_authority_remain_separate",
          effects_for(SimpleNamespace(allow_workspace_writes=True), HarnessAssignmentConfiguration("reason"))
          == ("reads_fs",)
          and effects_for(SimpleNamespace(allow_workspace_writes=False), HarnessAssignmentConfiguration("build"))
          == ("reads_fs",)
          and effects_for(SimpleNamespace(allow_workspace_writes=True), HarnessAssignmentConfiguration("build"))
          == ("reads_fs", "writes_fs")
          and refused(lambda: HarnessAssignmentConfiguration("inferred")))
    check("assignment_mode_and_version_are_explicit",
          NodeAssignment("atomic", "reason", "Read the task", mode="hybrid").to_dict()["mode"] == "hybrid"
          and NodeAssignment("atomic", "reason", "Read the task").to_dict()["record_type"] == "node_assignment/v3"
          and refused(lambda: NodeAssignment("atomic", "reason", "Read the task", mode="unknown")))
    experimental = HarnessAssignmentConfiguration("reason", workspace_effects=("reads_fs", "writes_fs"))
    check("reasoning_experiments_need_separate_owning_write_authority",
          effects_for(SimpleNamespace(allow_workspace_writes=True), experimental) == ("reads_fs", "writes_fs")
          and refused(lambda: effects_for(SimpleNamespace(allow_workspace_writes=False), experimental))
          and effects_for(SimpleNamespace(allow_workspace_writes=True),
                          HarnessAssignmentConfiguration("build", workspace_effects=())) == ())
    check("workspace_choices_are_frozen_and_do_not_invent_network_authority",
          refused(lambda: HarnessAssignmentConfiguration("reason", workspace_effects=("network",)))
          and experimental.to_dict()["record_type"] == "harness_assignment_configuration/v2"
          and experimental.to_dict()["workspace_effects"] == ["reads_fs", "writes_fs"])

    with tempfile.TemporaryDirectory() as root:
        services = fixture_services(root, configuration, writes=True)
        check("blocking_guardrail_prevents_assignment_files_before_execution",
              refused(lambda: provision_spawned(services, node_id="source", objective="Read input"), SpawnedProvisioningError)
              and not (services.workspace_base / ASSIGNMENT_FILE).exists())
        services = fixture_services(Path(root) / "allowed", configuration, writes=True)
        record = provision_spawned(services, node_id="source", objective="Read input",
                                   output_contract_refs=("value/v1",))
        stored = json.loads((services.workspace_base / ASSIGNMENT_FILE).read_text())
        instructions = (services.workspace_base / "AGENTS.md").read_text()
        check("reason_choice_is_not_inferred_from_outer_write_authority",
              record["kind"] == "reason" and stored["effects"] == ["reads_fs"]
              and stored["model_calls_authorized"] is True and stored["mode"] == "hybrid")
        check("only_selected_eligible_metadata_reaches_the_assignment",
              [item["identity"] for item in record["offered"]] == ["skill.read_source"]
              and "skill.unselected" not in instructions and "tool.write_report" not in instructions
              and "uninstalled candidate body" not in instructions and record["exposed_bytes"] == 0
              and record["native_loading_observed"] is False and record["resource_admission_established"] is False
              and (services.workspace_base / "CLAUDE.md").is_file()
              and json.loads((services.workspace_base / PROVISIONING_FILE).read_text())["record_type"] == "provisioned_node/v2")
        check("request_identity_cannot_be_replaced_by_a_different_configuration",
              refused(lambda: configuration_for(SimpleNamespace(
                  request=replace_namespace(services.request, harness_provisioning_digest="0" * 64),
                  dependencies=services.dependencies)), ProvisioningConfigurationError))

    with tempfile.TemporaryDirectory() as root:
        services = fixture_services(root, fixture_configuration(kind="build"), session=False)
        record = provision_spawned(services, node_id="build", objective="Prepare a report")
        stored = json.loads((services.workspace_base / ASSIGNMENT_FILE).read_text())
        instructions = (services.workspace_base / "AGENTS.md").read_text()
        check("build_kind_does_not_manufacture_worker_writes_or_model_authority",
              record["kind"] == "build" and stored["effects"] == ["reads_fs"]
              and stored["model_calls_authorized"] is False
              and "Write your result inside" not in instructions
              and "No worker file writes are authorized" in instructions)

    with tempfile.TemporaryDirectory() as root:
        services = fixture_services(root, None, writes=True)
        decision = provision_spawned(services, node_id="absent", objective="Read")
        check("unconfigured_provisioning_is_explicit_and_writes_no_folder",
              decision["reason"] == "not_configured" and not decision["provisioned"]
              and not services.workspace_base.exists())
        services = fixture_services(root, fixture_configuration(preparation=False), writes=True)
        check("worker_write_authority_does_not_grant_preparation_writes",
              refused(lambda: provision_spawned(services, node_id="refused", objective="Read"), SpawnedProvisioningError)
              and not services.workspace_base.exists())

    with tempfile.TemporaryDirectory() as root:
        guidance = GuardrailSet()
        guidance.register(Guardrail("guard.guidance", "Effect guidance", "process", "block", "before_effect",
                                   "write outside the assigned folder"))
        configured = fixture_configuration(rules=guidance)
        services = fixture_services(root, configured)
        record = provision_spawned(services, node_id="guidance", objective="Read")
        manifest = configured.to_dict()
        check("before_effect_text_is_recorded_as_guidance_not_dispatch_enforcement",
              record["provisioned"] and "write outside the assigned folder"
              in (services.workspace_base / "AGENTS.md").read_text()
              and manifest["guardrail_supported_enforcement_points"] == ["before_provisioning"]
              and manifest["guardrail_guidance_only_points"] == ["before_effect"]
              and manifest["dispatch_or_publication_guardrails_installed"] is False)

    with tempfile.TemporaryDirectory() as root:
        absent = HarnessProvisioningConfiguration.bind(assignment=HarnessAssignmentConfiguration("reason"),
                                                       preparation_writes_authorized=True)
        empty = HarnessProvisioningConfiguration.bind(assignment=HarnessAssignmentConfiguration("reason"),
            catalogue=HarnessIntelligenceCatalogue(), preparation_writes_authorized=True)
        first = provision_spawned(fixture_services(Path(root) / "a", absent), node_id="a", objective="Read")
        second = provision_spawned(fixture_services(Path(root) / "b", empty), node_id="b", objective="Read")
        check("absent_and_explicitly_empty_catalogues_remain_distinct_without_invented_items",
              first["provisioned"] and second["provisioned"]
              and first["catalogue_available"] is False and second["catalogue_available"] is True
              and first["offered"] == [] and second["offered"] == [])

    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
        services = fixture_services(root, fixture_configuration())
        (Path(root) / "spawned").symlink_to(outside, target_is_directory=True)
        check("symlink_ancestor_cannot_redirect_preparation_writes",
              refused(lambda: provision_spawned(services, node_id="escape", objective="Read"), SpawnedProvisioningError)
              and not (Path(outside) / "1").exists())
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "spawned_provisioning_test/v2", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}


def replace_namespace(value, **changes):
    return SimpleNamespace(**{**vars(value), **changes})
