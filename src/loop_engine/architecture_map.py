"""Architecture map: top-level package ownership as one projection authority.

Every module in this package belongs to exactly one of nine top-level package
groups or is package plumbing at the root. This map is
the folder shape: the mover consulted it, `--map` prints it,
`step_registry` resolves module paths through it, and the self-test
refuses any module on disk that is not classified here, so the
projection can never silently drift from the code.
"""
from __future__ import annotations

import os

# The package has one public import root.
PACKAGE = __package__ or "loop_engine"

#: the nine governed top-level package groups
SUBPACKAGES = ("ontology", "loop", "strings", "code_nodes",
               "core", "catalog", "memory", "generation",
               "templates")

PUBLIC_CORE_ARCHITECTURE_CAPABILITY_GROUPS = (
    ("Intelligence Search and Retrieval",
     ("intelligence_layers", "retrieval", "capability_directory")),
    ("Web Research", ("brave_search",)),
    ("Custom Plugins", ("capability_directory", "brave_search")),
)

#: package plumbing that stays at the root
ROOT_MODULES = ("__init__", "__main__", "_self_test", "_conformance_test",
                "_conformance_scan", "architecture_contract",
                "adaptive_practitioner_cli", "architecture_map",
                "conformance_report",
                "nomenclature_conformance", "public_runtime_conformance",
                "reachability_report",
                "repository_conformance", "repository_structure",
                "backend_isolation", "structure_review",
                "runtime_ontology_check", "scheduling", "campaign",
                "parallel_runner", "cli_operations", "parameter_boundary",
                "solve_cli", "cli_help", "run_history_cli", "record_cli", "service_cli", "decision_cli", "kaggle_report",
                "overnight_cli",
                "parameter_boundary_checks", "semantic_conformance",
                "semantic_freedom_conformance")

# Existing ontology-only namespaces are physical packages, not a tenth runtime
# group. The old serialized-record reader is tracked pre-launch cleanup.
ONTOLOGY_NAMESPACE_MODULES = ("node.__init__", "node.loop_node.__init__")

#: module -> subpackage.  "steps" and "regimes" are subpackages riding in loop/.
MODULE_MAP = {
    "core.decisions": ("__init__", "contracts", "contract_checks", "credentials", "configuration", "gateway",
                       "http_transport", "wire", "jev", "jev_checks", "system_one", "system_one_checks"),
    "core.service_runtime": (
        "__init__", "records", "storage", "runtime", "runtime_checks", "provisioning",
        "billing", "billing_records", "billing_checks", "stripe_provider",
        "billing_effects", "stripe_sessions", "stripe_session_checks", "stripe_session_transport_checks",
        "billing_policy", "billing_policy_checks",
        "http", "http_auth", "http_entrypoint", "http_checks", "http_boundary_checks",
        "http_test_fixtures", "refusals", "web_pages", "web_site_map", "access", "access_checks",
        "browser_identity", "browser_identity_checks",
        "request_limits", "request_limit_checks", "capacity_checks",
        "promotions", "promotion_checks",
        "account_email", "account_email_checks",
        "account_origin", "account_origin_checks", "account_policy", "account_administration",
        "account_administration_checks", "free_monthly",
        "observability", "observability_checks",
        "waitlist", "waitlist_checks",
        "protocol_checks",
        "retention", "retention_checks", "waitlist_source_checks",
        "catalogue_packages", "catalogue_schema", "catalogue_bundle", "catalogue_releases",
        "catalogue_search", "catalogue_serving", "catalogue_grants", "catalogue_commands",
        "catalogue_release_checks", "catalogue_serving_checks",
    ),
    "core.practitioner_runtime": ("__init__", "capabilities", "observations", "provisioning"),
    "core.library_ingestion": ("__init__", "candidates", "connection_rendering", "duplicates", "effects", "engines", "fetch_cache", "format_builtin", "format_connection", "format_json_schema", "format_skills_ref", "github_reader", "https_transport", "licence_checks", "licences", "near_duplicate_builtin", "near_duplicate_datasketch", "optional_engine_checks", "outline_deterministic", "outline_model", "package_resolver", "pipeline", "pipeline_checks", "processes", "provenance", "provenance_checks", "quarantine", "record_rules", "registry_sync", "render_checks", "rendering_types", "request_log", "scan_builtin", "scan_checks", "scan_skillspector", "selection", "skill_rendering", "source_checks", "source_declarations", "source_github", "source_mcp_registry", "staging_rows", "topics"),
    "core.engines": (
        "__init__", "records", "host_records", "selection_records", "decision_records",
        "records_checks", "selection_records_checks",
        "slots", "slot_index", "slot_checks",
    ),
    "core.step_execution": ("__init__",),
    "ontology": (
        "artifacts", "catalog", "folders", "loop_definition_record",
        "loop_node", "node", "ontology_checks", "records",
    ),
    "catalog.stores": (
        "duckdb_files", "duckdb_store", "in_memory", "package_jsonl",
        "sqlite_store",
    ),
    "memory": (
        "loop_integration",
    ),
    "memory.model": (
        "identity", "lifecycle", "memory_type", "reference", "scope",
    ),
    "memory.working": (
        "state",
    ),
    "memory.episodic": (
        "record",
    ),
    "memory.semantic": (
        "record",
    ),
    "memory.procedural": (
        "control_assessment", "control_assessment_checks", "record",
    ),
    "memory.query": (
        "query", "receipts",
    ),
    "memory.lifecycle": (
        "lifecycle",
    ),
    "memory.storage": (
        "store", "learning_cycle", "learning_cycle_checks",
        "learning_records",
    ),
    "generation": (
        "expansion", "operators", "space", "space_checks", "search",
        "search_records", "search_checks", "search_optuna", "search_optuna_checks",
        "layering_axes", "layering_axes_checks",
    ),
    "generation.model": (
        "campaign", "dimensions", "fragments", "seeds",
    ),
    "templates": (
        "compiler", "intake", "library", "model",
    ),
    "catalog": (
        "capabilities", "composite", "conformance", "handshake",
        "protocol", "registry", "query", "versioning",
    ),
    "loop": (
        "approval_state_store", "approval_state_store_checks",
        "atomic_primitives", "intrinsic_kernel",
        "capability_loops",
        "canvas", "spawned_runtime_port", "spawned_task_checkpoint",
        "spawned_task_state_store", "spawned_task_state_store_checks",
        "spawned_workspace_executor", "spawned_workspace_executor_checks",
        "delegation_checkpoint_checks", "delegation_runtime",
        "delegation_runtime_checks",
        "effect_approval", "kernel", "kernel_runtime",
        "loop_templates", "lens",
        "intelligence_loops",
        "encapsulate", "loop_capsule", "loop_contract",
        "loop_definition", "loop_definition_checks", "runtime_context",
        "loop_doctrine", "loop_profile_catalog", "loop_profile_ontology",
        "loop_role", "loop_control",
        "reactive_activation", "reactive_contract_checks",
        "reactive_contracts", "reactive_outputs",
        "recursive_loop", "service_loop_envelope", "supervision_policy",
        "checklist_loop", "loop_handoff",
        "spawned_practitioner", "spawned_deadline", "spawned_deadline_checks",
    ),
    "strings": (
        "ask_strategies", "context", "decision_schemas", "capability_resources",
        "frame", "intelligence_strings", "interrogation",
        "knowledge", "knowledge_state", "notes",
        "output_templates", "prompt_fragments", "verification_prompts", "solution_export_templates",
        "question_engine", "solution_shaping",
    ),
    "code_nodes": (
        "decision_tools", "decision_tool_checks", "decision_gateway_checks",
        "ascii_views", "ascii_views_checks",
        "blueprint", "campaign_runner", "capture", "context_seed",
        "core_engine_proof",
        "complex_task_benchmark",
        "complex_task_native_evidence", "complex_task_published_evidence",
        "follow_up", "housekeeping", "kaggle_executor", "live_run_demo",
        "learning_bundle", "guided_setup", "logic_ast", "loop_report",
        "measurement",
        "material_questions",
        "public_examples",
        "guidance_ledger",
        "run_analytics",
        "run_playback", "run_quality",
        "runtime_contracts", "self_improvement_loop",
        "smoke_ladder",
        "solve_learned_memory",
        "solve_region_evidence", "solve_request_adaptation", "solve_runtime", "solve_provisioning_checks",
        "solve_mode_checks", "solve_terminal", "solve_terminal_checks",
        "architecture_diagram", "architecture_diagram_text",
        "solution_canvas", "solution_canvas_checks", "solution_compiler",
        "solution_model_port",
        "solution_graph", "solution_graph_builder", "solution_graph_checks",
        "solution_graph_validation", "solution_graph_execution", "solution_operation_identity",
        "solution_records", "solutions_space",
        "solution_export", "solution_export_checks", "service_endpoints",
        "string_foundry",
        "text_conformance", "text_conformance_checks", "text_conformance_operations",
        "duplicate_detection", "field_recovery", "database_copy", "address_components",
        "data_quality_surfaces", "overnight_authority", "overnight_journal", "overnight_night",
        "overnight_night_checks",
    ),
    "core": (
        "adaptive_practitioner", "adaptive_practitioner_acceptance_checks",
        "adaptive_practitioner_capabilities", "adaptive_practitioner_checks",
        "adaptive_practitioner_orientation_capabilities",
        "adaptive_practitioner_project",
        "adaptive_practitioner_deterministic", "adaptive_practitioner_planning",
        "adaptive_practitioner_planning_checks", "adaptive_practitioner_scope",
        "adaptive_practitioner_scope_checks",
        "adaptive_practitioner_bindings", "adaptive_practitioner_bindings_checks",
        "adaptive_practitioner_orientation",
        "adaptive_practitioner_orientation_repair", "task_materials",
        "source_profile", "independent_judgment",
        "independent_failure_review", "independent_failure_review_checks",
        "adaptive_practitioner_prompting", "adaptive_practitioner_records",
        "adaptive_practitioner_result", "adaptive_practitioner_source",
        "adaptive_practitioner_recovery", "adaptive_practitioner_reuse",
        "adaptive_practitioner_supervision",
        "recovery_learning", "recovery_learning_checks", "cognitive_response_checks",
        "action_vector_assessment", "action_vector_routing",
        "work_function_catalog",
        "adaptive_practitioner_validation",
        "adaptive_practitioner_verification", "adaptive_practitioner_routing",
        "adaptive_practitioner_feedback_checks",
        "independent_verification", "independent_verification_checks",
        "independent_probe_planning", "independent_verification_plan_checks",
        "independent_probe_review", "independent_probe_review_checks",
        "independent_probe_review_integration_checks",
        "workspace_docker_cleanup_checks",
        "host_runtime", "adaptive_host_verification", "adaptive_host_runtime_checks",
        "host_completion_checks",
        "capability_invocation",
        "source_admission_checks",
        "api_quality", "asset_class", "component_contracts",
        "component_inventory",
        "asset_lifecycle", "brave_search",
        "capability_directory",
        "capability_rejection",
        "run_history", "run_history_authorship",
        "run_history_checks", "run_history_paths", "run_history_usage",
        "run_history_usage_checks", "config", "context_artifacts",
        "record_operations", "record_operations_records", "record_operations_checks",
        "action_fence",
        "context_budget", "context_pack_manifest", "observation_expectations", "task_frontier",
        "prompt_experiment", "task_region_statistics", "option_selection",
        "semantic_decision", "decision_outcome",
        "stage_fingerprint", "convergence", "outcome_vector",
        "stage_store", "stage_store_checks", "stage_store_records", "stage_evidence_records",
        "stage_action_lineage", "stage_action_lineage_adversarial_checks",
        "run_checkpoint",
        "solution_ratchet",
        "solve_control_manifest", "semantic_event_history",
        "stage_assistance_experiment", "stage_assistance_material",
        "stage_assistance_runtime_records",
        "stage_evidence_projection", "stage_evidence_temporal",
        "stage_evidence_values",
        "stage_assistance_checks", "model_demand", "run_stages", "choice",
        "recovery", "template_negotiation",
        "cognitive_grammar", "terminal_layer", "run_validity",
        "practitioner_contract_guards",
        "workspace_read", "verifier_execute",
        "self_tuning",
        "context_catalog",
        "context_classification", "context_ontology",
        "code_intelligence_assets", "code_intelligence_asset_checks", "event_vocabulary", "duckdb_catalog",
        "live_dependency_checks",
        "artifact_constraints",
        "independent_evidence",
        "differential_verification", "differential_drivers",
        "external_harness", "external_harness_output", "external_harness_adapters",
        "external_harness_accounting", "external_harness_adapter_checks",
        "external_harness_checks", "external_harness_contract", "external_harness_contract_checks",
        "harness_execution_contracts",
        "harness_model_authority", "harness_process", "harness_process_relay",
        "harness_process_checks", "harness_confinement",
        "harness_configuration", "harness_semantic", "harness_semantic_checks",
        "instance_instructions", "instance_instructions_checks",
        "harness_intelligence", "harness_intelligence_search",
        "external_service_intelligence", "provisioning_server", "provisioning_server_checks",
        "provisioning_mcp", "provisioning_mcp_checks",
        "node_provisioning", "intelligence_tagging", "credential_leases",
        "capability_needs", "guardrail_intelligence", "spawned_provisioning", "spawned_provisioning_checks", "model_call_collection",
        "harness_output_limit_binding",
        "harness_fallback", "harness_fallback_checks", "harness_layering",
        "harness_layering_space", "harness_layering_availability",
        "harness_layering_availability_checks",
        "harness_layering_configuration", "harness_layering_configuration_checks",
        "harness_selection_records", "harness_selection", "harness_selection_checks",
        "harness_response_evaluation",
        "harness_additional_recipes", "harness_additional_recipe_checks",
        "harness_cline_kilo_recipes", "harness_cline_kilo_recipe_checks",
        "harness_goose_recipe", "harness_goose_recipe_checks",
        "harness_lightweight_recipes", "harness_lightweight_recipe_checks",
        "harness_mini_swe_recipe", "harness_mini_swe_recipe_checks",
        "harness_opencode_recipe", "harness_opencode_recipe_checks",
        "harness_python_recipes", "harness_python_recipe_checks",
        "harness_responses_recipes", "harness_responses_recipe_checks",
        "harness_remaining_recipes", "harness_remaining_recipe_checks",
        "harness_recipes", "harness_recipe_catalog_checks",
        "harness_builtin_recipes", "harness_builtin_recipe_checks",
        "harness_fresh_instances", "harness_fresh_instance_checks",
        "opencode_harness_adapter", "opencode_step_session",
        "opencode_step_session_checks",
        "opencode_step_composition", "opencode_step_composition_checks",
        "opencode_step_guard", "opencode_step_layers", "step_content",
        "night_budget", "step_state", "overnight_outcome",
        "multipath_select", "opencode_step_provision", "facets",
        "harness_intelligence_bridge", "intelligence_layers",
        "intelligence_query_contracts",
        "intelligence_portfolio", "intelligence_portfolio_checks",
        "runtime_memory", "user_feedback_intelligence",
        "intelligence_registry",
        "live_model_verification", "live_text_scenarios",
        "mcp_adapter", "mcp_adapter_checks",
        "mcp_sdk_transport",
        "practitioner_runtime_facts", "source_role_orientation",
        "runtime_capacity",
        "model_call", "model_call_contract", "model_capabilities", "model_gateway",
        "model_ontology", "response_contracts", "suggested_output", "contract_matching",
        "capability_directory_checks",
        "reuse_evidence", "model_call_records", "operation_cost_records",
        "temporal_facts", "shared_memory_scopes",
        "step_efficiency_review", "heuristic_adoption", "implementation_choice",
        "specialist_training", "operation_cost_capture",
        "evaluation_suite", "configuration_optimizer", "node_grid", "service_api",
        "seeded_generation", "typed_decision", "route_separation", "route_separation_checks",
        "prompt_elements", "typed_action_decision", "local_resources",
        "local_model_readiness", "instance_hibernation",
        "registered_capability_call",
        "model_prompt_envelope",
        "model_gateway_accounting", "model_gateway_accounting_checks", "model_token_preflight",
        "retrieval_backends", "retrieval_backend_checks",
        "model_output_recovery_checks", "model_output_allocation_checks",
        "route_health",
        "model_response_admission", "model_response_admission_checks",
        "model_response_text",
        "model_routing_intelligence", "model_routing_intelligence_checks",
        "model_routing_records", "model_routing_selector",
        "ngram_benchmark", "ngram_retrieval",
        "otel_export",
        "primitive_conformance",
        "runtime_observer", "runtime_settings", "settings_loader",
        "parameter_resolution",
        "configuration_capabilities", "configuration_setters", "configuration_setter_checks",
        "configuration_preferences", "configuration_preference_checks",
        "information_evidence_contracts", "information_theory_evidence",
        "information_update_evidence", "information_theory_adversarial_checks",
        "information_theory_evidence_checks", "state_policy_evidence",
        "information_access", "information_access_checks",
        "reactive_output_store", "reactive_output_store_checks",
        "reactive_scheduler", "reactive_scheduler_checks",
        "reactive_worker", "reactive_worker_checks",
        "plugin_bundles", "plugin_bundles_checks", "extension_discovery",
        "development_planning", "development_planning_checks",
        "development_execution", "development_execution_checks",
        "development_governance", "development_governance_checks",
        "lifecycle_extensions", "lifecycle_extensions_checks",
        "software_tdd_skill_checks",
        "model_routes", "ollama_client",
        "mistral_client", "openrouter_client", "openai_responses_client",
        "openai_responses_client_checks", "astra_route_authority",
        "astra_route_authority_checks", "astra_route_planning",
        "astra_route_record_identity",
        "provider_failover", "provider_failure_classes",
        "provider_pinned",
        "model_discovery", "autoconfigure", "custom_endpoint",
        "custom_endpoint_checks",
        "product_outcome_store",
        "generated_project", "generated_project_artifact_validation",
        "knowledge_loader",
        "llm_work_packet",
        "opencode_client", "opencode_zen_catalog", "operating_profile",
        "persistence",
        "practitioner_context",
        "reasoning_call", "resolution", "retrieval",
        "reusable_capability_checks", "reusable_capability_flywheel",
        "reusable_capability_harvest", "reusable_capability_hybrid",
        "reusable_capability_records",
        "reusable_capability_resolution", "skill_discovery_projection",
        "skill_registry",
        "skill_registry_checks",
        "skill_state_context", "skill_state_context_checks",
        "semantic_runtime", "semantic_runtime_checks",
        "semantic_runtime_evidence", "semantic_runtime_fixture",
        "semantic_runtime_records", "semantic_state",
        "solution_library", "task_compile_model", "task_fingerprint",
        "task_fingerprint_facets", "task_similarity_engine",
        "store_serve",
        "boundary_registry", "boundary_runtime_checks", "saas_routes",
        "studio_operational_views", "studio_server", "workspace_backends",
        "workspace_contracts",
        "workspace_local", "workspace_operation_checks",
        "web_fetch", "web_search", "workspace_operations",
        "workspace_optional",
    ),
}

_QUALIFIED = {f"{package}.{module}": package
              for package, modules in MODULE_MAP.items() for module in modules}
_QUALIFIED.update({module: "ontology" for module in ONTOLOGY_NAMESPACE_MODULES})


def subpackage_of(module: str) -> str:
    """Resolve an exact module or an unambiguous short name; never guess an owner."""
    if module in ROOT_MODULES:
        return ""
    if module in _QUALIFIED:
        return _QUALIFIED[module]
    matches = [package for package, modules in MODULE_MAP.items() if module in modules]
    if len(matches) != 1:
        raise ValueError("module name must identify exactly one mapped owner")
    return matches[0]


def module_path(module: str) -> str:
    """Full import path for an exact or unambiguous mapped module."""
    sub = subpackage_of(module)
    if module in _QUALIFIED:
        return f"{PACKAGE}.{module}"
    return f"{PACKAGE}.{sub}.{module}" if sub else f"{PACKAGE}.{module}"


def _coverage(package_root: str, modules: dict, root_modules: tuple) -> dict:
    """Compare complete module paths, including nested folders, without imports."""
    declared = {module.replace(".", "/") + ".py" for module in root_modules}
    for package, names in modules.items():
        folder = package.replace(".", "/")
        declared.update(f"{folder}/{name}.py" for name in names)
        # Package initialization is plumbing inside an explicitly mapped folder.
        declared.add(folder + "/__init__.py")
    on_disk = set()
    for folder, directories, files in os.walk(package_root, followlinks=False):
        directories[:] = [name for name in directories if name != "__pycache__"]
        for name in files:
            if name.endswith(".py"):
                on_disk.add(os.path.relpath(os.path.join(folder, name), package_root).replace(os.sep, "/"))
    return {"unmapped": sorted(on_disk - declared), "missing": sorted(declared - on_disk)}


def render_map() -> str:
    out = [f"ARCHITECTURE MAP: {len(SUBPACKAGES)} top-level package groups"]
    for s in SUBPACKAGES:
        mods = MODULE_MAP[s]
        out.append(f"  {s}/  ({len(mods)} modules)")
        out.append("    " + ", ".join(mods))
        for nested in sorted(k for k in MODULE_MAP
                             if k.startswith(s + ".")):
            nested_mods = MODULE_MAP[nested]
            out.append(f"    {nested}/  ({len(nested_mods)} modules)")
            out.append("      " + ", ".join(nested_mods))
    out.append("PUBLIC CORE ARCHITECTURE CAPABILITY GROUPS (3)")
    for title, modules in PUBLIC_CORE_ARCHITECTURE_CAPABILITY_GROUPS:
        out.append(f"  {title}: {', '.join(modules)}")
    out.append("All other core modules are internal runtime "
               "services, not peer public capability groups.")
    return "\n".join(out)


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    here = os.path.dirname(__file__)
    # 1. every .py on disk is classified (root or one abstraction): anti-drift.
    on_disk = sorted(f[:-3] for f in os.listdir(here) if f.endswith(".py"))
    stray = [m for m in on_disk if m not in ROOT_MODULES]
    check("no_unclassified_module_at_package_root", not stray,
          f"root may hold only plumbing; found: {stray}")
    for s in SUBPACKAGES:
        files = sorted(f[:-3] for f in os.listdir(os.path.join(here, s))
                       if f.endswith(".py") and f != "__init__.py")
        unmapped = [m for m in files if m not in MODULE_MAP[s]]
        check(f"every_module_in_{s}_is_mapped_there", not unmapped,
              f"unmapped/misfiled: {unmapped}")
    # 2. every mapped module exists on disk where the map says.
    missing = []
    for package, modules in MODULE_MAP.items():
        for module in modules:
            target = os.path.join(here, package.replace(".", os.sep), module)
            if not os.path.isfile(target + ".py"):
                missing.append(f"{package}/{module}")
    check("every_mapped_module_exists_on_disk", not missing, str(missing))
    complete = _coverage(here, MODULE_MAP, ROOT_MODULES + ONTOLOGY_NAMESPACE_MODULES)
    check("every_nested_module_has_an_exact_mapped_path", not complete["unmapped"], str(complete))
    check("every_declared_module_and_package_path_exists", not complete["missing"], str(complete["missing"]))
    check("qualified_names_preserve_distinct_modules_with_the_same_filename",
          module_path("core.service_runtime.records") == f"{PACKAGE}.core.service_runtime.records"
          and module_path("ontology.records") == f"{PACKAGE}.ontology.records")
    ambiguous_refused = False
    try:
        subpackage_of("records")
    except ValueError:
        ambiguous_refused = True
    check("ambiguous_short_module_names_are_refused", ambiguous_refused)
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(prefix="architecture-map-") as temporary:
        fixture = Path(temporary)
        (fixture / "first").mkdir()
        (fixture / "first/records.py").write_text("", encoding="utf-8")
        (fixture / "unmapped").mkdir()
        (fixture / "unmapped/records.py").write_text("", encoding="utf-8")
        measured = _coverage(temporary, {"first": ("records",), "second": ("records",)}, ())
        check("nested_coverage_canary_detects_missing_and_unmapped_duplicate_basenames",
              "second/records.py" in measured["missing"]
              and measured["unmapped"] == ["unmapped/records.py"])
    # 3. the top-level abstraction set is frozen; nested subpackages ride
    #    inside their owning abstraction.
    check("top_level_abstractions_are_frozen",
          {s for s in MODULE_MAP if "." not in s} == set(SUBPACKAGES),
          "the set is closed")
    public_groups = tuple(
        title for title, _modules in
        PUBLIC_CORE_ARCHITECTURE_CAPABILITY_GROUPS)
    check("core_has_three_public_capability_groups",
          public_groups == ("Intelligence Search and Retrieval",
                            "Web Research", "Custom Plugins"),
          "internal services do not become peer public capability groups")
    return {"tests": results}
