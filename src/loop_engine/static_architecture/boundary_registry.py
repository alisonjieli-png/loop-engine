"""Canonical Loop operational-boundary register.

Every declared boundary is joined to a role profile and runtime evidence.
"""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass, replace
from types import MappingProxyType

from ..loop.loop_profile_catalog import LoopProfileError, LoopProfileRef
from ..loop.loop_profile_ontology import get_profile
from ..loop.loop_role import LOOP_RELATIONSHIP_KINDS


ROLE_FAMILIES = ("practitioner", "intelligence", "solution")
ROLE_RELATIONSHIP_KINDS = MappingProxyType({
    "practitioner": frozenset(("starting", "spawned_by")),
    "intelligence": frozenset(("starting", "queried_by", "retrieved_by")),
    "solution": frozenset(("starting", "spawned_by", "connected_from")),
})

PUBLIC_CAPABILITY_GROUP_BOUNDARIES = MappingProxyType({
    "Intelligence Search and Retrieval": ("retrieval tournament", "intelligence serving"),
    "Web Research": ("custom plugin invocation",),
    "Custom Plugins": ("custom plugin invocation",),
})


@dataclass(frozen=True)
class DynamicProfileSource:
    """A typed runtime source of an exact, catalog-validated profile."""

    source: str
    validator: str
    allowed_families: tuple[str, ...]


@dataclass(frozen=True)
class BoundaryOntologyBinding:
    """The one Loop classification joined to an operational boundary row."""

    runtime_type: str
    role_families: tuple[str, ...]
    relationship_kinds: tuple[str, ...]
    profile_ref: str = ""
    dynamic_profile_source: "DynamicProfileSource | None" = None


def _exact(role: str, profile_ref: str, *relationships: str) -> BoundaryOntologyBinding:
    return BoundaryOntologyBinding(
        "Loop", (role,), tuple(relationships), profile_ref=profile_ref)


def _dynamic(*roles: str, source: str,
             validator: str,
             relationships: tuple[str, ...]) -> BoundaryOntologyBinding:
    families = tuple(roles)
    return BoundaryOntologyBinding(
        "Loop", families, tuple(relationships),
        dynamic_profile_source=DynamicProfileSource(
            source, validator, families))

BINDING_KINDS = (
    "practitioner_loop",     # wrapped by as_practitioner_loop
    "component_loop",        # wrapped by as_component_loop (fallback arms)
    "stage_loop_tree",       # runs as a loop of stage loops
    "native_loop",           # IS the loop runtime itself
    "api_dispatch",          # crosses in through serve_api
    "template_governed",     # runs under a registered template envelope
    "unbound",               # honestly not wrapped yet
)

BOUNDARIES = (
    {"boundary": "task entry", "crosses": "a user task enters the runtime",
     "binding": "native_loop", "envelope": "loop.recursive_loop.Loop",
     "test": "recursive_loop.self_test"},
    {"boundary": "reference nine-step stages",
     "crosses": "each of the nine stages executes",
     "binding": "stage_loop_tree",
     "envelope": "loop.encapsulate.as_loop_of_stage_loops",
     "test": "encapsulate:reference_nine_step_runs_as_nine_stage_loops"},
    {"boundary": "Practitioner kernel execution",
     "crosses": "typed kernel passes calculate an operational task result",
     "binding": "native_loop",
     "envelope": "loop.kernel_runtime.execute_kernel_run",
     "test": "kernel_runtime.self_test"},
    {"boundary": "deterministic check",
     "crosses": "a plain callable runs as governed work",
     "binding": "practitioner_loop",
     "envelope": "loop.encapsulate.as_practitioner_loop",
     "test": "encapsulate:deterministic_check_runs_as_practitioner_loop"},
    {"boundary": "solution component",
     "crosses": "a Solution Canvas box executes",
     "binding": "native_loop",
     "envelope": "code_nodes.solution_canvas._run_atomic_operation",
     "test": "solution_canvas_checks:"
             "every_registry_callable_runs_inside_one_atomic_solution_loop"},
    {"boundary": "api endpoint",
     "crosses": "a browser, harness, or tenant reads Loop Engine",
     "binding": "api_dispatch", "envelope": "static_architecture.saas_routes"
                                            ".serve_api",
     "test": "saas_routes:every_api_call_crosses_into_a_practitioner_loop"},
    {"boundary": "user intelligence resolution",
     "crosses": "a loop consults human guidance before deciding",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.user_feedback_intelligence"
                 ".resolve_user_feedback_intelligence",
     "test": "user_feedback_intelligence:"
             "snapshot_resolution_is_a_thin_deterministic_loop"},
    {"boundary": "external harness delegation",
     "crosses": "a bounded assignment goes to an outside coding agent",
     "binding": "template_governed",
     "envelope": "loop_templates:external_harness_worker",
     "test": "loop_templates:"
             "external_harness_worker_is_opaque_bounded_and_clamped"},
    {"boundary": "promotion review",
     "crosses": "a candidate is considered for registered status",
     "binding": "template_governed",
     "envelope": "static_architecture.asset_lifecycle"
                 ".promotion_review_as_loop",
     "test": "asset_lifecycle.self_test"},
    {"boundary": "external submission",
     "crosses": "an artifact leaves for a third party",
     "binding": "template_governed",
     "envelope": "code_nodes.smoke_ladder.submission_as_loop",
     "test": "smoke_ladder.self_test"},
    {"boundary": "retrieval tournament",
     "crosses": "a backend is measured against the incumbent",
     "binding": "template_governed",
     "envelope": "static_architecture.retrieval.tournament_as_loop",
     "test": "retrieval.self_test"},
    {"boundary": "intelligence foundry wave",
     "crosses": "raw model output becomes candidate Strings",
     "binding": "template_governed",
     "envelope": "code_nodes.string_foundry.foundry_wave_as_loop",
     "test": "string_foundry.self_test"},
    {"boundary": "model invocation",
     "crosses": "a prompt reaches a provider",
     "binding": "practitioner_loop",
     "envelope": "loop.encapsulate.as_model_loop",
     "test": "encapsulate:the_model_boundary_crosses_a_loop_that_permits_one_"
             "semantic_call"},
    {"boundary": "provider-neutral model routing",
     "crosses": "one typed model request is attempted across configured routes",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.model_gateway.invoke_model_gateway",
     "test": "model_gateway.self_test"},
    {"boundary": "runtime settings resolution",
     "crosses": "YAML and environment preferences become typed runtime settings",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.settings_loader.load_runtime_settings",
     "test": "settings_loader:yaml_then_environment_precedence_is_visible"},
    {"boundary": "runtime settings file creation",
     "crosses": "a default user settings file is written to disk",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.settings_loader.write_default_settings",
     "test": "settings_loader:settings_file_creation_is_also_a_loop"},
    {"boundary": "runtime memory write",
     "crosses": "a loop leaves a note for its siblings",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.runtime_memory.RunNoteBoard",
     "test": "runtime_memory.self_test"},
    # --- found by the completeness detector, 2026-08-24 -------------------
    # The register read 14/14 while these five were doing envelope work and
    # were absent from it.  "Complete about itself" is not "complete".
    {"boundary": "preference resolution",
     "crosses": "requested settings become the immutable spec a loop runs on",
     "binding": "practitioner_loop",
     "envelope": "loop.effective_spec.resolve_effective_spec",
     "test": "effective_spec:resolution_is_deterministic_and_digested"},
    {"boundary": "intelligence serving",
     "crosses": "a stored String, capability, guidance row or prior run is "
                "served to a caller",
     "binding": "practitioner_loop",
     "envelope": "loop.intelligence_loops.serve_pillar",
     "test": "intelligence_loops.self_test"},
    {"boundary": "improvement campaign",
     "crosses": "a bounded self-improvement campaign runs",
     "binding": "practitioner_loop",
     "envelope": "loop.practitioner_campaign.development_practitioner_loop",
     "test": "practitioner_campaign.self_test"},
    {"boundary": "multi-problem comparison campaign",
     "crosses": "frozen problem cases expand into mode and provider arms",
     "binding": "native_loop",
     "envelope": "code_nodes.campaign_runner.run_campaign_arm",
     "test": "campaign_runner.self_test"},
    {"boundary": "knowledge planning service",
     "crosses": "an internal decision algorithm executes for a public solve",
     "binding": "practitioner_loop",
     "envelope": "loop.solver.solve",
     "test": "solver.self_test"},
    {"boundary": "studio history read",
     "crosses": "the Studio reads a saved run",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.studio_server._load_run_as_historical_loop",
     "test": "studio_server:the_event_stream_is_the_canonical_vocabulary"},
    {"boundary": "loop reference invocation",
     "crosses": "a chosen LoopRef becomes content",
     "binding": "practitioner_loop",
     "envelope": "loop.loop_capsule.invoke_ref",
     "test": "loop_capsule:invoking_a_ref_runs_the_loop_and_returns_content"},
    {"boundary": "custom plugin invocation",
     "crosses": "a selected registered plugin performs work",
     "binding": "component_loop",
     "envelope": "loop.capability_loops.run_capability_as_loop",
     "test": "capability_loops.self_test"},
    {"boundary": "Code Intelligence entry point",
     "crosses": "a selected Code Intelligence body executes one entry point",
     "binding": "component_loop",
     "envelope": "static_architecture.code_intelligence_assets.execute_code_ref",
     "test": "code_intelligence_assets.self_test"},
    {"boundary": "solution graph adapter",
     "crosses": "a value converts between two incompatible typed ports",
     "binding": "component_loop",
     "envelope": "code_nodes.solution_graph.run_adapter_loop",
     "test": "solution_graph:"
             "the_adapter_executes_as_a_loop_not_an_edge_function"},
    {"boundary": "typed spawned task",
     "crosses": "a bounded spawned assignment starts and returns typed output",
     "binding": "native_loop",
     "envelope": "loop.delegation_runtime.SpawnedTaskManager",
     "test": "delegation_runtime.self_test"},
    {"boundary": "external harness execution",
     "crosses": "a bounded task enters a configured external agent harness",
     "binding": "native_loop",
     "envelope": "static_architecture.external_harness"
                 ".run_external_harness",
     "test": "external_harness.self_test"},
    {"boundary": "external harness memory import",
     "crosses": "external harness output becomes intelligence candidates",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.harness_intelligence_bridge"
                 ".import_harness_memory_as_loop",
     "test": "harness_intelligence_bridge.self_test"},
    {"boundary": "MCP tool discovery",
     "crosses": "a registered MCP server returns an allowed tool catalog",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.mcp_adapter.McpRegistry",
     "test": "mcp_adapter.self_test"},
    {"boundary": "MCP tool operation",
     "crosses": "a discovered MCP tool is invoked",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.mcp_adapter.McpRegistry",
     "test": "mcp_adapter.self_test"},
    {"boundary": "skill instruction load",
     "crosses": "a selected skill body enters active task context",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.skill_registry.SkillRegistry",
     "test": "skill_registry.self_test"},
    {"boundary": "skill admission",
     "crosses": "an independently reviewed skill becomes available to tasks",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.skill_registry.SkillRegistry.admit",
     "test": "skill_registry.self_test"},
    {"boundary": "OpenTelemetry export",
     "crosses": "safe saved-run fields become external trace spans",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.otel_export"
                 ".export_run_history_as_loop",
     "test": "otel_export.self_test"},
    {"boundary": "context compaction",
     "crosses": "selected raw context becomes a separate compacted artifact",
     "binding": "native_loop",
     "envelope": "static_architecture.context_artifacts"
                 ".compact_context_as_loop",
     "test": "context_artifacts.self_test"},
    {"boundary": "durable approval decision",
     "crosses": "one exact approval decision advances durable state",
     "binding": "native_loop",
     "envelope": "loop.effect_approval.EffectApprovalService.resume",
     "test": "effect_approval.self_test"},
    {"boundary": "durable approval consumption",
     "crosses": "one exact approved effect is consumed once",
     "binding": "native_loop",
     "envelope": "loop.effect_approval.EffectApprovalService.consume",
     "test": "effect_approval.self_test"},
    {"boundary": "workspace file write",
     "crosses": "approved bytes cross into a workspace backend",
     "binding": "native_loop",
     "envelope": "static_architecture.workspace_operations"
                 ".WorkspaceOperationService.file",
     "test": "workspace_operations.self_test"},
    {"boundary": "workspace command",
     "crosses": "an approved command crosses into a workspace backend",
     "binding": "native_loop",
     "envelope": "static_architecture.workspace_operations"
                 ".WorkspaceOperationService.command",
     "test": "workspace_operations.self_test"},
    {"boundary": "spawned checkpoint restore",
     "crosses": "a typed saved spawned task rejoins its parent manager",
     "binding": "native_loop",
     "envelope": "loop.spawned_task_checkpoint.SpawnedTaskLifecycleMixin"
                 ".restore_checkpoint",
     "test": "delegation_checkpoint_checks.self_test"},
    {"boundary": "spawned task join",
     "crosses": "a parent waits within a bound for selected spawned results",
     "binding": "native_loop",
     "envelope": "loop.spawned_task_checkpoint.SpawnedTaskLifecycleMixin.join",
     "test": "delegation_checkpoint_checks.self_test"},
    {"boundary": "solution pipeline execution",
     "crosses": "an ordered Solution composition runs",
     "binding": "native_loop",
     "envelope": "code_nodes.solution_canvas._run_solution_runtime",
     "test": "solution_canvas_checks.self_test"},
    {"boundary": "solution member execution",
     "crosses": "one nested member of a Solution composition runs",
     "binding": "native_loop",
     "envelope": "code_nodes.solution_canvas._execute_spec",
     "test": "solution_canvas_checks.self_test"},
    {"boundary": "solution router execution",
     "crosses": "a Solution route or fallback order is selected and run",
     "binding": "native_loop",
     "envelope": "code_nodes.solution_canvas._run_solution_node",
     "test": "solution_canvas_checks.self_test"},
    {"boundary": "solution validator execution",
     "crosses": "a Solution output is checked by a validator Loop",
     "binding": "native_loop",
     "envelope": "code_nodes.solution_canvas._run_members",
     "test": "solution_canvas_checks.self_test"},
    {"boundary": "persistence",
     "crosses": "an artifact is written to disk",
     "binding": "practitioner_loop",
     "envelope": "static_architecture.persistence.append_record_as_loop",
     "test": "persistence.self_test"},
)


#: The boundary and ontology key sets must match exactly.
BOUNDARY_ONTOLOGY = MappingProxyType({
    "task entry": _exact(
        "practitioner", "practitioner.solver@1.0.0", "starting"),
    "reference nine-step stages": _exact(
        "practitioner", "practitioner.reference_nine_step@1.0.0",
        "spawned_by"),
    "Practitioner kernel execution": _exact(
        "practitioner", "practitioner.reference_nine_step@1.0.0",
        "starting", "spawned_by"),
    "deterministic check": _exact(
        "practitioner", "practitioner.code_execution@1.0.0",
        "starting", "spawned_by"),
    "solution component": _exact(
        "solution", "solution.atomic_component@1.0.0", "connected_from"),
    "api endpoint": _exact(
        "practitioner", "practitioner.code_execution@1.0.0", "starting"),
    "user intelligence resolution": _exact(
        "intelligence", "intelligence.user_feedback.scope@1.0.0",
        "queried_by"),
    "external harness delegation": _exact(
        "practitioner", "practitioner.solver@1.0.0", "spawned_by"),
    "promotion review": _exact(
        "practitioner", "practitioner.verifier@1.0.0", "spawned_by"),
    "external submission": _exact(
        "practitioner", "practitioner.code_execution@1.0.0", "spawned_by"),
    "retrieval tournament": _exact(
        "practitioner", "practitioner.verifier@1.0.0", "spawned_by"),
    "intelligence foundry wave": _exact(
        "practitioner", "practitioner.self_improvement@1.0.0",
        "spawned_by"),
    "model invocation": _exact(
        "practitioner", "practitioner.solver@1.0.0",
        "starting", "spawned_by"),
    "provider-neutral model routing": _exact(
        "practitioner", "practitioner.solver@1.0.0", "spawned_by"),
    "runtime settings resolution": _exact(
        "practitioner", "practitioner.code_execution@1.0.0",
        "starting", "spawned_by"),
    "runtime settings file creation": _exact(
        "practitioner", "practitioner.code_execution@1.0.0", "spawned_by"),
    "runtime memory write": _exact(
        "practitioner", "practitioner.code_execution@1.0.0", "spawned_by"),
    "preference resolution": _exact(
        "practitioner", "practitioner.code_execution@1.0.0", "spawned_by"),
    "intelligence serving": _exact(
        "intelligence", "intelligence.search@1.0.0",
        "queried_by", "retrieved_by"),
    "improvement campaign": _exact(
        "practitioner", "practitioner.self_improvement@1.0.0",
        "starting", "spawned_by"),
    "multi-problem comparison campaign": _exact(
        "practitioner", "practitioner.solver@1.0.0",
        "starting", "spawned_by"),
    "knowledge planning service": _exact(
        "practitioner", "practitioner.solver@1.0.0",
        "starting", "spawned_by"),
    "studio history read": _exact(
        "intelligence",
        "intelligence.runtime_history_solution.replay@1.0.0", "queried_by"),
    "loop reference invocation": _exact(
        "intelligence", "intelligence.materialize@1.0.0", "retrieved_by"),
    "custom plugin invocation": _exact(
        "intelligence", "intelligence.code.invoke@1.0.0", "retrieved_by"),
    "Code Intelligence entry point": _exact(
        "intelligence", "intelligence.code.invoke@1.0.0", "retrieved_by"),
    "solution graph adapter": _exact(
        "solution", "solution.atomic_component@1.0.0", "connected_from"),
    "typed spawned task": _dynamic(
        *ROLE_FAMILIES,
        source="loop.delegation_runtime.DelegationSpec.profile",
        validator="loop.delegation_runtime.SpawnedTaskManager._validate_spec",
        relationships=("spawned_by",)),
    "external harness execution": _dynamic(
        "practitioner",
        source="static_architecture.external_harness"
               ".HarnessRunRequest.profile_id",
        validator="static_architecture.external_harness"
                  ".HarnessRunRequest.__post_init__",
        relationships=("spawned_by",)),
    "external harness memory import": _exact(
        "intelligence", "intelligence.materialize@1.0.0", "retrieved_by"),
    "MCP tool discovery": _exact(
        "intelligence", "intelligence.code.resolve@1.0.0",
        "starting", "queried_by"),
    "MCP tool operation": _exact(
        "intelligence", "intelligence.code.invoke@1.0.0",
        "starting", "retrieved_by"),
    "skill instruction load": _exact(
        "intelligence", "intelligence.context.serve@1.0.0",
        "starting", "retrieved_by"),
    "skill admission": _exact(
        "practitioner", "practitioner.verifier@1.0.0",
        "starting", "spawned_by"),
    "OpenTelemetry export": _exact(
        "practitioner", "practitioner.code_execution@1.0.0", "starting"),
    "context compaction": _exact(
        "intelligence", "intelligence.context.frame@1.0.0",
        "starting", "retrieved_by"),
    "durable approval decision": _exact(
        "practitioner", "practitioner.verifier@1.0.0",
        "starting", "spawned_by"),
    "durable approval consumption": _exact(
        "practitioner", "practitioner.verifier@1.0.0",
        "starting", "spawned_by"),
    "workspace file write": _exact(
        "practitioner", "practitioner.code_execution@1.0.0",
        "starting", "spawned_by"),
    "workspace command": _exact(
        "practitioner", "practitioner.code_execution@1.0.0",
        "starting", "spawned_by"),
    "spawned checkpoint restore": _dynamic(
        *ROLE_FAMILIES,
        source="loop.spawned_task_checkpoint.SpawnedTaskCheckpoint.spec",
        validator="loop.spawned_task_checkpoint.SpawnedTaskLifecycleMixin"
                  ".restore_checkpoint",
        relationships=("spawned_by",)),
    "spawned task join": _dynamic(
        *ROLE_FAMILIES,
        source="loop.delegation_runtime.DelegationSpec.profile",
        validator="loop.spawned_task_checkpoint.SpawnedTaskLifecycleMixin.join",
        relationships=("spawned_by",)),
    "solution pipeline execution": _exact(
        "solution", "solution.pipeline@1.0.0",
        "starting", "spawned_by", "connected_from"),
    "solution member execution": _exact(
        "solution", "solution.ensemble@1.0.0",
        "spawned_by", "connected_from"),
    "solution router execution": _exact(
        "solution", "solution.router_fallback@1.0.0", "spawned_by"),
    "solution validator execution": _exact(
        "solution", "solution.validator@1.0.0", "connected_from"),
    "persistence": _exact(
        "practitioner", "practitioner.code_execution@1.0.0", "spawned_by"),
})


class BoundaryError(ValueError):
    """A register row that claims more than it can show."""


def _profile_ref(value: str) -> LoopProfileRef:
    if not isinstance(value, str) or value.count("@") != 1:
        raise BoundaryError(
            f"profile reference {value!r} must be exact profile_id@version")
    profile_id, version = value.split("@", 1)
    if not profile_id or not version:
        raise BoundaryError(
            f"profile reference {value!r} must include an explicit version")
    try:
        return LoopProfileRef(profile_id, version)
    except LoopProfileError as exc:
        raise BoundaryError(str(exc)) from exc


def _mapped_symbol_exists(reference: str) -> bool:
    """Resolve a mapped module symbol without importing or running it."""
    from ..architecture_map import MODULE_MAP
    parts = reference.split(".")
    if len(parts) < 3 or parts[0] not in MODULE_MAP:
        return False
    subpackage, module = parts[:2]
    if module not in MODULE_MAP[subpackage]:
        return False
    package_root = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(package_root, subpackage, module) + ".py"
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except (OSError, SyntaxError):
        return False
    candidates = {getattr(node, "name", ""): node for node in tree.body
                  if isinstance(node, (ast.FunctionDef,
                                       ast.AsyncFunctionDef, ast.ClassDef))}
    current = candidates.get(parts[2])
    for name in parts[3:]:
        if not isinstance(current, ast.ClassDef):
            return False
        nested = {}
        for node in current.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                nested[node.name] = node
            elif isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name):
                nested[node.target.id] = node
            elif isinstance(node, ast.Assign):
                nested.update({target.id: node for target in node.targets
                               if isinstance(target, ast.Name)})
        current = nested.get(name)
    return current is not None


def _validate(row: dict,
              ontology: "BoundaryOntologyBinding | None" = None) -> None:
    if row.get("binding") not in BINDING_KINDS:
        raise BoundaryError(f"{row.get('boundary')!r}: binding "
                            f"{row.get('binding')!r} not in {BINDING_KINDS}")
    if row["binding"] != "unbound" and not (row.get("envelope")
                                            and row.get("test")):
        raise BoundaryError(
            f"{row['boundary']!r} claims binding {row['binding']!r} without "
            "naming both an envelope and a test — a claimed binding with no "
            "proof is worse than an honest unbound row")
    ontology = ontology or BOUNDARY_ONTOLOGY.get(row.get("boundary", ""))
    if not isinstance(ontology, BoundaryOntologyBinding):
        raise BoundaryError(
            f"{row.get('boundary')!r} has no typed ontology binding")
    if ontology.runtime_type != "Loop":
        raise BoundaryError(
            f"{row.get('boundary')!r}: runtime_type must be exactly 'Loop'")
    if (not ontology.role_families
            or any(role not in ROLE_FAMILIES
                   for role in ontology.role_families)
            or len(set(ontology.role_families))
            != len(ontology.role_families)):
        raise BoundaryError(
            f"{row.get('boundary')!r}: role families must be a unique subset "
            f"of {ROLE_FAMILIES}")
    relationships = ontology.relationship_kinds
    allowed_relationships = set().union(
        *(ROLE_RELATIONSHIP_KINDS[role]
          for role in ontology.role_families))
    if (not relationships
            or len(set(relationships)) != len(relationships)
            or any(kind not in LOOP_RELATIONSHIP_KINDS
                   for kind in relationships)):
        raise BoundaryError(
            f"{row.get('boundary')!r}: relationship kinds must be a non-empty "
            f"unique subset of {LOOP_RELATIONSHIP_KINDS}")
    incompatible = sorted(set(relationships) - allowed_relationships)
    if incompatible:
        raise BoundaryError(
            f"{row.get('boundary')!r}: relationship kinds {incompatible} are "
            f"incompatible with roles {ontology.role_families}")
    exact = bool(ontology.profile_ref)
    dynamic = ontology.dynamic_profile_source is not None
    if exact == dynamic:
        raise BoundaryError(
            f"{row.get('boundary')!r}: declare exactly one exact profile or "
            "typed dynamic profile source")
    if exact:
        ref = _profile_ref(ontology.profile_ref)
        try:
            profile = get_profile(ref)
        except LoopProfileError as exc:
            raise BoundaryError(str(exc)) from exc
        if profile.state != "registered":
            raise BoundaryError(
                f"{ontology.profile_ref} is not a registered runnable profile")
        if ontology.role_families != (profile.family,):
            raise BoundaryError(
                f"{ontology.profile_ref} belongs to {profile.family!r}, not "
                f"declared role {ontology.role_families!r}")
        return
    source = ontology.dynamic_profile_source
    if not isinstance(source, DynamicProfileSource):
        raise BoundaryError("dynamic profile source must be typed")
    if source.allowed_families != ontology.role_families:
        raise BoundaryError(
            "dynamic profile source families must match the boundary role scope")
    if not (_mapped_symbol_exists(source.source)
            and _mapped_symbol_exists(source.validator)):
        raise BoundaryError(
            f"dynamic profile source {source.source!r} and validator "
            f"{source.validator!r} must resolve through the architecture map")


def boundary_report(rows=BOUNDARIES, ontology=BOUNDARY_ONTOLOGY) -> dict:
    """The computed inventory. Nothing here is rounded up: a boundary is
    bound only if it names the envelope that wraps it AND the test that
    proves it."""
    rows = tuple(rows)
    names = [str(row.get("boundary", "")) for row in rows]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    missing = sorted(set(names) - set(ontology))
    extra = sorted(set(ontology) - set(names))
    invalid = []
    for row in rows:
        name = str(row.get("boundary", ""))
        try:
            _validate(row, ontology.get(name))
        except BoundaryError as exc:
            invalid.append({"boundary": name, "error": str(exc)})
    bound = [r for r in rows if r.get("binding") != "unbound"]
    unbound = [r for r in rows if r.get("binding") == "unbound"]
    by_kind: dict = {}
    for r in bound:
        by_kind[r["binding"]] = by_kind.get(r["binding"], 0) + 1
    invalid_names = {item["boundary"] for item in invalid}
    valid_names = set(names) - invalid_names - set(duplicates)
    by_role = {role: 0 for role in ROLE_FAMILIES}
    by_profile: dict[str, int] = {}
    dynamic_sources: dict[str, int] = {}
    by_relationship = {kind: 0 for kind in LOOP_RELATIONSHIP_KINDS}
    for name in sorted(valid_names):
        binding = ontology[name]
        for kind in binding.relationship_kinds:
            by_relationship[kind] += 1
        if binding.profile_ref:
            role = binding.role_families[0]
            by_role[role] += 1
            by_profile[binding.profile_ref] = (
                by_profile.get(binding.profile_ref, 0) + 1)
        else:
            source = binding.dynamic_profile_source
            scope = "|".join(binding.role_families)
            key = f"{scope}:{source.source}"
            dynamic_sources[key] = dynamic_sources.get(key, 0) + 1
    unclassified = sorted(set(missing) | set(duplicates))
    outside = sorted(
        set(unclassified) | invalid_names
        | {str(row.get("boundary", "")) for row in unbound}
        | {f"ontology-only:{name}" for name in extra})
    conforming = [name for name in valid_names
                  if next(row for row in rows
                          if row.get("boundary") == name).get("binding")
                  != "unbound"]
    return {"record_type": "operational_boundary_report/v2",
            "total": len(rows), "bound": len(bound),
            "unbound": len(unbound),
            "ontology_conforming": len(conforming),
            "coverage": (round(len(conforming) / len(rows), 3)
                         if rows else 0.0),
            "by_binding_kind": by_kind,
            "by_role": by_role,
            "by_profile": dict(sorted(by_profile.items())),
            "by_relationship_kind": by_relationship,
            "dynamic_profile_sources": dynamic_sources,
            "exact_profile_boundaries": sum(by_role.values()),
            "dynamic_profile_boundaries": sum(dynamic_sources.values()),
            "invalid_rows": invalid,
            "invalid_relationship_rows": [
                item for item in invalid
                if "relationship kinds" in item["error"]],
            "unclassified_rows": unclassified,
            "missing_ontology_keys": missing,
            "extra_ontology_keys": extra,
            "duplicate_boundary_names": duplicates,
            "outside_loop_ontology": len(outside),
            "outside_loop_ontology_boundaries": outside,
            "unbound_boundaries": [r["boundary"] for r in unbound],
            "honesty": "coverage counts only rows joined one-to-one to a "
                       "validated Loop role profile; invalid, unclassified, "
                       "extra, duplicate, and unbound rows stay visible"}


def unbound_boundaries() -> list:
    """The work queue, in the register's own words."""
    return [{"boundary": r["boundary"], "crosses": r["crosses"],
             "why_open": r.get("note", "")}
            for r in BOUNDARIES if r["binding"] == "unbound"]


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    rep = boundary_report()

    from .boundary_runtime_checks import run_runtime_ontology_proof
    runtime_ok, runtime_detail = run_runtime_ontology_proof(
        BOUNDARY_ONTOLOGY)
    check("runtime_events_match_boundary_profiles_and_relationships",
          runtime_ok, runtime_detail)

    from ..architecture_map import PUBLIC_STATIC_ARCHITECTURE_CAPABILITY_GROUPS
    public_group_names = tuple(
        title for title, _modules in
        PUBLIC_STATIC_ARCHITECTURE_CAPABILITY_GROUPS)
    categorized_boundaries = {
        name for names in PUBLIC_CAPABILITY_GROUP_BOUNDARIES.values()
        for name in names}
    check("three_public_capability_groups_map_to_real_boundaries",
          tuple(PUBLIC_CAPABILITY_GROUP_BOUNDARIES) == public_group_names
          and categorized_boundaries <= {
              row["boundary"] for row in BOUNDARIES},
          "internal runtime services are not public peer groups")

    check("every_boundary_is_classified_inside_the_loop_ontology",
          rep["total"] == len(BOUNDARIES)
          and rep["bound"] + rep["unbound"] == rep["total"]
          and rep["ontology_conforming"] == rep["total"]
          and rep["outside_loop_ontology"] == 0
          and not rep["invalid_rows"]
          and not rep["unclassified_rows"]
          and not rep["extra_ontology_keys"]
          and rep["total"] > 0,
          f"{rep['ontology_conforming']}/{rep['total']} conforming; "
          f"roles={rep['by_role']}; profiles={rep['by_profile']}")

    unresolved = []
    for r in BOUNDARIES:
        env = r.get("envelope", "")
        if not env or ":" in env:          # template refs checked separately
            continue
        if not _mapped_symbol_exists(env):
            unresolved.append(env)
    check("every_claimed_envelope_resolves_to_real_code", not unresolved,
          f"unresolved: {unresolved}" if unresolved
          else "all dotted envelopes resolve through the architecture map")

    from ..loop.loop_templates import TEMPLATE_LIBRARY
    registered = {t["template_id"] for t in TEMPLATE_LIBRARY
                  if t.get("maturity") == "registered"}
    tmpl_refs = [r["envelope"].split(":", 1)[1] for r in BOUNDARIES
                 if r.get("envelope", "").startswith("loop_templates:")]
    check("template_bound_boundaries_name_registered_templates",
          all(t in registered for t in tmpl_refs) and tmpl_refs,
          f"{tmpl_refs} all registered")

    fixture = {"boundary": "canary", "crosses": "test",
               "binding": "native_loop",
               "envelope": "loop.recursive_loop.Loop",
               "test": "boundary_registry.self_test"}
    valid = _exact(
        "practitioner", "practitioner.solver@1.0.0", "spawned_by")
    positive = True
    try:
        _validate(fixture, valid)
    except BoundaryError:
        positive = False
    adversarial = {
        "missing_runtime_type": replace(valid, runtime_type=""),
        "unknown_profile": _exact(
            "practitioner", "practitioner.not_registered@1.0.0", "spawned_by"),
        "wrong_role_family": _exact(
            "solution", "practitioner.solver@1.0.0", "spawned_by"),
        "unversioned_profile": _exact(
            "practitioner", "practitioner.solver", "spawned_by"),
        "missing_relationship": replace(valid, relationship_kinds=()),
        "role_incompatible_relationship": replace(
            valid, relationship_kinds=("retrieved_by",)),
        "unknown_relationship": replace(
            valid, relationship_kinds=("invented",)),
        "unresolved_dynamic_source": _dynamic(
            "practitioner", source="loop.missing.Request.profile",
            validator="loop.missing.Validator.validate",
            relationships=("spawned_by",)),
    }
    refused = []
    for name, binding in adversarial.items():
        try:
            _validate(fixture, binding)
        except BoundaryError:
            refused.append(name)
    check("ontology_canaries_accept_valid_and_refuse_every_invalid_shape",
          positive and set(refused) == set(adversarial),
          f"positive={positive}; refused={sorted(refused)}")

    missing_report = boundary_report((fixture,), MappingProxyType({}))
    extra_report = boundary_report(
        (fixture,), MappingProxyType({"canary": valid, "extra": valid}))
    duplicate_report = boundary_report(
        (fixture, fixture), MappingProxyType({"canary": valid}))
    check("ontology_join_refuses_missing_extra_and_duplicate_keys",
          missing_report["outside_loop_ontology"] > 0
          and extra_report["outside_loop_ontology"] > 0
          and duplicate_report["outside_loop_ontology"] > 0,
          "the boundary rows and ontology keys must stay one-to-one")

    open_work = unbound_boundaries()
    check("unbound_boundaries_are_named_work_with_reasons",
          len(open_work) == rep["unbound"]
          and all(w["why_open"] for w in open_work),
          f"open: {[w['boundary'] for w in open_work] or 'none — 100%'}")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
