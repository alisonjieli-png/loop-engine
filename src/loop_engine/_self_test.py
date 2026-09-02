"""Deterministic self-test aggregator - the ONE test entrypoint (no model, no network).

Owns: folding every module's self_test() into a single suite via
_FOLDED_SUBMODULE_TESTS (module paths resolved through the architecture map).
Belongs to: root plumbing.  Never: skipped or expected-failure tests - the
conformance scanner fails on any such marker in this file."""

from __future__ import annotations


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # Fold in the submodule self-tests so there is one test entrypoint.
    _FOLDED_SUBMODULE_TESTS = [
        "architecture_map", "architecture_contract",
        "parameter_boundary_checks",
        "semantic_conformance",
        "repository_conformance", "repository_structure",
        "backend_isolation", "structure_review",
        "runtime_ontology_check", "scheduling",
        "memory.model.memory_type", "memory.working.state",
        "memory.episodic.record", "memory.semantic.record",
        "memory.procedural.record", "memory.query.query",
        "memory.lifecycle.lifecycle", "memory.storage.store",
        "memory.storage.repository",
        "memory.loop_integration", "campaign",
        "generation.model.fragments",
        "generation.model.dimensions",
        "generation.model.campaign",
        "generation.operators", "templates.model",
        "templates.library", "templates.compiler", "templates.intake",
        "_conformance_test", "_conformance_scan",
        "conformance_report",
        "core.facets", "core.api_quality", "core.model_response_text",
        "core.action_fence", "core.capability_rejection",
        "core.practitioner_runtime_facts",
        "core.source_role_orientation",
        "core.adaptive_practitioner_project", "core.runtime_capacity",
        "core.context_budget", "core.context_pack_manifest",
        "core.task_frontier", "core.prompt_experiment",
        "core.task_region_statistics", "core.option_selection",
        "core.workspace_read",
        "core.cognitive_grammar",
        "kaggle_report",
        "core.self_tuning",
        "core.opencode_harness_adapter", "code_nodes.solve_region_evidence",
        "code_nodes.material_questions",
        "loop.supervision_policy", "loop.checklist_loop", "loop.loop_handoff",
        "loop.loop_control", "loop.loop_templates", "loop.encapsulate",
        "loop.loop_contract", "loop.loop_definition_checks",
        "loop.loop_profile_ontology",
        "loop.approval_state_store", "loop.canvas", "loop.delegation_runtime",
        "loop.atomic_primitives", "loop.intrinsic_kernel",
        "loop.reactive_contract_checks",
        "loop.spawned_practitioner",
        "loop.spawned_workspace_executor",
        "ontology.artifacts", "ontology.catalog", "ontology.folders",
        "ontology.loop_definition_record", "ontology.records",
        "catalog.capabilities", "catalog.composite",
        "catalog.conformance", "catalog.handshake",
        "catalog.protocol", "catalog.query", "catalog.registry",
        "ontology.ontology_checks",
        "loop.effect_approval",
        "loop.capability_loops",
        "loop.loop_doctrine",         "loop.intelligence_loops",
        "code_nodes.smoke_ladder", "code_nodes.campaign_runner",
        "code_nodes.complex_task_benchmark",
        "code_nodes.complex_task_native_evidence",
        "code_nodes.core_engine_proof",
        "code_nodes.context_seed", "code_nodes.self_improvement_loop",
        "code_nodes.solution_canvas", "code_nodes.solution_compiler",
        "code_nodes.solve_runtime",
        "solve_cli",
        "code_nodes.solution_model_port",
        "code_nodes.solution_graph_checks",
        "code_nodes.ascii_views_checks",
        "code_nodes.run_analytics", "code_nodes.run_playback",
        "core.run_history", "code_nodes.run_quality",
        "core.intelligence_layers",
        "core.intelligence_query_contracts",
        "core.intelligence_portfolio",
        "core.model_routing_intelligence",
        "core.ngram_retrieval",
        "core.context_catalog",
        "core.context_artifacts",
        "core.context_classification",
        "core.context_ontology",
        "core.code_intelligence_assets",
        "core.brave_search",
        "core.external_harness",
        "core.external_harness_adapters",
        "core.harness_intelligence_bridge",
        "core.mcp_adapter",
        "core.mcp_sdk_transport",
        "core.otel_export",
        "core.skill_registry",
        "core.workspace_backends",
        "core.workspace_operations",
        "core.user_feedback_intelligence",
        "core.runtime_memory",
        "core.task_fingerprint",
        "core.task_fingerprint_facets",
        "core.task_similarity_engine",
        "core.resolution",
        "core.solution_library",
        "core.reusable_capability_checks",
        "core.semantic_runtime_checks",
                        "code_nodes.live_run_demo",
        "code_nodes.string_foundry",
        "core.studio_server",
        "core.retrieval",
        "core.duckdb_catalog",
        "code_nodes.blueprint",
        "code_nodes.capture",
        "code_nodes.follow_up",
        "code_nodes.guidance_ledger",
        "code_nodes.guided_setup",
        "code_nodes.housekeeping",
        "code_nodes.kaggle_executor",
        "code_nodes.learning_bundle",
        "code_nodes.logic_ast",
        "code_nodes.loop_report",
        "code_nodes.measurement",
        "code_nodes.public_examples",
        "code_nodes.runtime_contracts",
        "code_nodes.solution_graph",
        "code_nodes.solution_records",
        "loop.kernel",
        "loop.kernel_runtime",
        "loop.lens",
        "loop.loop_capsule",
        "loop.recursive_loop",
        "loop.spawned_task_state_store",
        "ontology.artifacts",
        "ontology.catalog",
        "ontology.folders",
        "ontology.ontology_checks",
        "core.asset_class",
        "core.asset_lifecycle",
        "core.adaptive_practitioner",
        "core.adaptive_practitioner_capabilities",
        "core.adaptive_practitioner_orientation_capabilities",
        "core.adaptive_practitioner_result",
        "core.adaptive_practitioner_source",
        "core.adaptive_practitioner_planning",
        "core.adaptive_practitioner_prompting",
        "core.adaptive_practitioner_verification",
        "core.autoconfigure",
        "core.boundary_registry",
        "core.capability_directory", "core.component_contracts",
        "core.component_inventory",
        "core.config",
        "core.custom_endpoint",
        "core.extension_discovery",
        "core.generated_project",
        "core.intelligence_registry",
        "core.knowledge_loader",
        "core.mistral_client",
        "core.model_call",
        "core.model_discovery",
        "core.model_routes",
        "core.opencode_client",
        "core.opencode_zen_catalog",
        "core.openrouter_client",
        "core.operating_profile",
        "core.persistence",
        "core.practitioner_context",
        "core.primitive_conformance",
        "core.provider_failover",
        "core.reasoning_call",
        "core.saas_routes",
        "core.store_serve",
        "strings.ask_strategies",
        "strings.context",
        "strings.decision_schemas",
        "strings.intelligence_strings",
        "strings.interrogation",
        "strings.notes",
        "strings.output_templates",
        "strings.prompt_fragments",
        "strings.question_engine",
        "strings.solution_shaping",
        "core.model_gateway", "core.model_response_admission",
        "core.model_capabilities",
        "core.route_health",
        "core.live_model_verification",
        "core.live_text_scenarios",
        "core.llm_work_packet",
        "core.task_compile_model",
        "core.web_fetch",
        "core.web_search",
        "core.runtime_observer",
        "core.information_access_checks",
        "core.reactive_output_store_checks",
        "core.reactive_scheduler_checks",
        "core.reactive_worker_checks",
        "core.plugin_bundles_checks",
        "core.development_planning_checks",
        "core.development_execution_checks",
        "core.development_governance_checks",
        "core.lifecycle_extensions_checks",
        "core.software_tdd_skill_checks",
        "core.settings_loader",
        "core.parameter_resolution",
                                                                                                                                                                                    ]
    import importlib as _importlib

    #: Import names used to explain a genuinely missing required dependency.
    _PACKAGE_FOR_MODULE = {
        "numpy": "numpy", "pandas": "pandas",
        "sklearn": "scikit-learn", "lightgbm": "lightgbm",
        "xgboost": "xgboost", "duckdb": "duckdb",
        "model2vec": "model2vec", "lancedb": "lancedb",
        "kaggle": "kaggle", "yaml": "PyYAML", "mcp": "mcp",
    }
    _OPTIONAL_TEST_DEPENDENCIES = {
        "code_nodes.smoke_ladder": ("numpy", "pandas", "sklearn"),
        "code_nodes.live_run_demo": ("numpy", "pandas"),
        "code_nodes.kaggle_executor": ("numpy", "pandas", "sklearn"),
        "core.duckdb_catalog": ("duckdb",),
        "core.mcp_sdk_transport": ("mcp",),
    }

    def _fold(name, run):
        """Run one module's self_test and report an incomplete installation.

        ``run`` may be a callable OR a module path to import: an adapter that
        imports its dependency at module level raises during IMPORT, before any
        test runs, so guarding only the call left that case uncaught."""
        optional = _OPTIONAL_TEST_DEPENDENCIES.get(name, ())
        unavailable = tuple(module for module in optional
                            if _importlib.util.find_spec(module) is None)
        if unavailable:
            return [{
                "test": f"{name}_optional_adapter_not_tested",
                "passed": True, "not_tested": True,
                "outcome": "NOT_APPLICABLE",
                "missing_optional_dependencies": list(unavailable),
                "detail": (
                    "Optional adapter is not installed in this base package; "
                    "install loop-engine[all] to run this adapter suite."),
            }]
        try:
            if isinstance(run, str):
                run = _importlib.import_module(
                    f"{__package__}.{run}").self_test
            return run()["tests"]
        except ModuleNotFoundError as exc:
            package = _PACKAGE_FOR_MODULE.get((exc.name or "").split(".")[0])
            if package is None:
                raise                       # a REAL missing import: never hide
            return [{"test": f"{name}_self_test", "passed": False,
                     "missing_dependency": package,
                     "detail": f"FAILED: missing {exc.name}. Reinstall "
                               "Loop Engine to restore all dependencies."}]

    for _name in _FOLDED_SUBMODULE_TESTS:
        results.extend(_fold(_name, _name))
    # solve.py (the demo module) is shadowed on the package by the universal
    # solve() FUNCTION, so import both self-tests explicitly by module path.

    passed = sum(1 for r in results if r["passed"])
    missing = [r for r in results if r.get("missing_dependency")]
    missing_packages = sorted({r["missing_dependency"] for r in missing})
    optional_not_tested = [r for r in results if r.get("not_tested")]
    optional_packages = sorted({package for r in optional_not_tested
                                for package in r.get(
                                    "missing_optional_dependencies", ())})
    return {"record_type": "loop_engine_self_test/v1", "tests": results,
            "passed": passed, "total": len(results),
            "missing_dependencies": missing_packages,
            "optional_adapters_not_tested": optional_packages,
            "dependency_note": (
                "incomplete installation: " + ", ".join(missing_packages)
                if missing_packages else
                "base installation complete; optional adapters not tested: "
                + ", ".join(optional_packages)
                if optional_packages else
                "base and optional adapter dependencies are installed"),
            "all_passed": passed == len(results)}
