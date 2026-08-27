"""Architecture map: the top-level abstractions as one projection authority.

Every module in this package belongs to exactly one of the five frozen
abstractions (ontology | loop | strings | code_nodes |
core) or is package plumbing at the root.  This map IS
the folder shape: the mover consulted it, `--map` prints it,
`step_registry` resolves module paths through it, and the self-test
refuses any module on disk that is not classified here, so the
projection can never silently drift from the code.
"""
from __future__ import annotations

import os

# The package has one public import root.
PACKAGE = __package__ or "loop_engine"

#: the frozen top-level abstractions
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
                "architecture_map", "conformance_report",
                "nomenclature_conformance", "public_runtime_conformance",
                "repository_conformance", "repository_structure",
                "backend_isolation", "structure_review",
                "runtime_ontology_check", "scheduling", "campaign",
                "parallel_runner", "cli_operations", "parameter_boundary",
                "parameter_boundary_checks", "semantic_conformance")

#: module -> subpackage.  "steps" and "regimes" are subpackages riding in loop/.
MODULE_MAP = {
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
        "record",
    ),
    "memory.query": (
        "query", "receipts",
    ),
    "memory.lifecycle": (
        "lifecycle",
    ),
    "memory.storage": (
        "store", "repository", "learning_cycle", "learning_cycle_checks",
        "learning_records",
    ),
    "generation": (
        "expansion", "operators",
    ),
    "generation.model": (
        "campaign", "dimensions", "fragments", "seeds",
    ),
    "templates": (
        "compiler", "intake", "library", "model",
    ),
    "catalog": (
        "capabilities", "composite", "conformance", "handshake",
        "protocol", "registry", "query",
    ),
    "loop": (
        "approval_state_store", "approval_state_store_checks",
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
        "recursive_loop", "service_loop_envelope",
        "spawned_practitioner",
    ),
    "strings": (
        "ask_strategies", "context", "decision_schemas",
        "frame", "intelligence_strings", "interrogation",
        "knowledge", "knowledge_state", "notes",
        "output_templates", "prompt_fragments",
        "question_engine", "solution_shaping",
    ),
    "code_nodes": (
        "blueprint", "campaign_runner", "capture", "context_seed",
        "core_engine_proof",
        "complex_task_benchmark",
        "complex_task_native_evidence", "complex_task_published_evidence",
        "follow_up", "housekeeping", "kaggle_executor", "live_run_demo",
        "learning_bundle", "guided_setup", "logic_ast", "universal_solve", "loop_report", "measurement",
        "public_examples",
        "guidance_ledger",
        "run_analytics",
        "run_playback", "run_quality",
        "runtime_contracts", "self_improvement_loop",
        "smoke_ladder",
        "solve_runtime",
        "solution_canvas", "solution_canvas_checks", "solution_compiler",
        "solution_model_port",
        "solution_graph", "solution_graph_builder", "solution_graph_checks",
        "solution_graph_validation", "solution_records",
        "string_foundry",
    ),
    "core": (
        "api_quality", "asset_class", "asset_lifecycle", "brave_search",
        "capability_directory",
        "run_history", "config", "context_artifacts", "context_catalog",
        "context_classification", "context_ontology",
        "code_intelligence_assets", "event_vocabulary", "duckdb_catalog",
        "external_harness", "external_harness_adapters",
        "external_harness_checks", "facets",
        "harness_intelligence_bridge", "intelligence_layers",
        "intelligence_query_contracts",
        "intelligence_portfolio", "intelligence_portfolio_checks",
        "runtime_memory", "user_feedback_intelligence",
        "intelligence_registry",
        "live_model_verification", "live_text_scenarios",
        "mcp_adapter", "mcp_adapter_checks",
        "mcp_sdk_transport",
        "model_call", "model_capabilities", "model_gateway", "model_response_text",
        "model_routing_intelligence", "model_routing_intelligence_checks",
        "model_routing_records", "model_routing_selector",
        "ngram_benchmark", "ngram_retrieval",
        "otel_export",
        "runtime_observer", "runtime_settings", "settings_loader",
        "model_routes", "ollama_client",
        "mistral_client", "openrouter_client", "provider_failover",
        "provider_pinned",
        "model_discovery", "autoconfigure", "custom_endpoint", "knowledge_loader",
        "opencode_client", "operating_profile", "persistence",
        "reasoning_call", "resolution", "retrieval", "skill_registry",
        "solution_library", "task_fingerprint",
        "store_serve",
        "boundary_registry", "boundary_runtime_checks", "saas_routes",
        "studio_operational_views", "studio_server", "workspace_backends",
        "workspace_contracts",
        "workspace_local", "workspace_operation_checks",
        "workspace_operations", "workspace_optional",
    ),
}

_FLAT = {m: s for s, mods in MODULE_MAP.items() for m in mods}


def subpackage_of(module: str) -> str:
    """Which of the four abstractions owns this module ("" for root plumbing)."""
    if module in ROOT_MODULES:
        return ""
    return _FLAT[module]


def module_path(module: str) -> str:
    """Full import path for a bare module name, via the map."""
    sub = subpackage_of(module)
    return f"{PACKAGE}.{sub}.{module}" if sub else f"{PACKAGE}.{module}"


def render_map() -> str:
    out = ["ARCHITECTURE MAP: six top-level abstractions"]
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
        unmapped = [m for m in files if m not in _FLAT or _FLAT[m] != s]
        check(f"every_module_in_{s}_is_mapped_there", not unmapped,
              f"unmapped/misfiled: {unmapped}")
    # 2. every mapped module exists on disk where the map says.
    missing = []
    for m, s in _FLAT.items():
        target = os.path.join(here, s.replace(".", os.sep), m)
        if not (os.path.exists(target + ".py") or os.path.isdir(target)):
            missing.append(f"{s}/{m}")
    check("every_mapped_module_exists_on_disk", not missing, str(missing))
    # 3. the top-level abstraction set is frozen; nested subpackages ride
    #    inside their owning abstraction.
    check("top_level_abstractions_are_frozen",
          set(s for s in MODULE_MAP if "." not in s) == set(SUBPACKAGES),
          "the set is closed")
    public_groups = tuple(
        title for title, _modules in
        PUBLIC_CORE_ARCHITECTURE_CAPABILITY_GROUPS)
    check("core_has_three_public_capability_groups",
          public_groups == ("Intelligence Search and Retrieval",
                            "Web Research", "Custom Plugins"),
          "internal services do not become peer public capability groups")
    return {"tests": results}
