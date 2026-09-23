"""Offline self-test aggregator: no model or external network calls.

Optional transport checks use real loopback sockets and temporary local state.

Owns: folding every module's self_test() into a single suite via
_FOLDED_SUBMODULE_TESTS (module paths resolved through the architecture map).
Belongs to: root plumbing.  Never: skipped or expected-failure tests - the
conformance scanner fails on any such marker in this file."""

from __future__ import annotations


def _module_test_records(name: str, result: object) -> list[dict]:
    """Validate executed checks and preserve explicitly unavailable adapters."""
    tests = result.get("tests") if isinstance(result, dict) else None
    if not isinstance(tests, (list, tuple)) or not tests:
        raise ValueError("a module must return a non-empty sequence of test records")
    validated = []
    for item in tests:
        if not isinstance(item, dict):
            raise ValueError("each test record must be a mapping")
        identity = item.get("test") or item.get("name")
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("each test record must have an identity")
        record = {**item, "owner_module": f"{__package__}.{name}"}
        if "not_tested" in record and type(record["not_tested"]) is not bool:
            raise ValueError("not_tested must be an explicit Boolean")
        if record.get("not_tested") is True:
            missing = record.get("missing_optional_dependencies")
            if record.get("outcome") != "NOT_APPLICABLE" \
                    or not isinstance(missing, (list, tuple)) or not missing \
                    or any(not isinstance(value, str) or not value for value in missing) \
                    or not (record.get("passed") is True or record.get("passed") is None):
                raise ValueError("an unavailable adapter needs explicit dependency evidence")
            record["passed"] = None
        elif type(record.get("passed")) is not bool:
            raise ValueError("an executed test must report a Boolean passed value")
        validated.append(record)
    return validated


def _result_counts(results: list[dict]) -> dict:
    """Count executed checks separately from unavailable optional adapters."""
    executed = [record for record in results if record.get("not_tested") is not True]
    passed = sum(record["passed"] is True for record in executed)
    return {"passed": passed, "total": len(executed),
            "not_tested": len(results) - len(executed),
            "reported_checks": len(results),
            "all_passed": bool(executed) and passed == len(executed)}


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail,
                        "owner_module": __name__})

    # Fold in the submodule self-tests so there is one test entrypoint.
    # Owner direction, September 21, 2026 (roadmap S-6.28, the harness-first
    # decision record): the main line serves harness intelligence and retires
    # the in-process Loop-native execution path in phases. These are the
    # suites that guard the serving path, the harness adapters, the catalogue
    # and the records. The suites of the parked in-process execution
    # capability were removed from this list and live on
    # checkpoint/full-capability-2026-09-21, where the full tree keeps
    # passing them.
    _FOLDED_SUBMODULE_TESTS = [
        "architecture_map", "architecture_contract", "service_cli", "semantic_conformance", "nomenclature_conformance", "repository_conformance", "repository_structure", "backend_isolation",
        "structure_review", "runtime_ontology_check", "_conformance_test", "_conformance_scan", "conformance_report", "core.facets", "core.api_quality", "core.workspace_read",
        "loop.supervision_policy", "loop.loop_control", "loop.encapsulate", "loop.loop_contract", "catalog.capabilities", "catalog.composite", "catalog.conformance", "catalog.handshake",
        "catalog.protocol", "catalog.query", "catalog.registry", "catalog.stores.package_jsonl", "catalog.stores.sqlite_store", "catalog.stores.in_memory", "catalog.stores.duckdb_store", "catalog.stores.duckdb_files",
        "core.run_history_checks", "core.run_history_authorship", "core.run_history_usage_checks", "core.record_operations_checks", "record_cli", "core.intelligence_layers", "core.external_harness", "core.external_harness_adapters",
        "core.external_harness_contract",
        "core.harness_process_checks", "core.harness_confinement", "core.harness_semantic", "core.instance_instructions", "core.harness_intelligence", "core.provisioning_server", "core.provisioning_mcp_checks", "core.service_runtime.runtime",
        "core.service_runtime.billing", "core.service_runtime.promotions", "core.service_runtime.stripe_provider", "core.service_runtime.http_checks", "core.service_runtime.refusals", "core.service_runtime.stripe_sessions", "core.decisions.contracts", "core.decisions.jev",
        "core.decisions.system_one", "core.retrieval_backends", "core.node_provisioning", "core.intelligence_tagging", "core.credential_leases", "core.capability_needs", "core.guardrail_intelligence", "core.spawned_provisioning",
        "core.model_call_collection", "core.harness_output_limit_binding", "core.harness_fallback", "core.harness_layering", "core.harness_layering_space", "core.harness_layering_availability", "core.harness_layering_configuration", "core.harness_selection",
        "core.harness_response_evaluation", "core.harness_additional_recipe_checks", "core.harness_cline_kilo_recipe_checks", "core.harness_goose_recipe_checks", "core.harness_lightweight_recipe_checks", "core.harness_mini_swe_recipe_checks", "core.harness_opencode_recipe_checks", "core.harness_python_recipe_checks",
        "core.harness_responses_recipe_checks", "core.harness_remaining_recipe_checks", "core.harness_intelligence_bridge", "core.harness_intelligence_search", "core.mcp_adapter", "core.mcp_sdk_transport", "core.skill_registry", "core.workspace_backends", "core.workspace_operations",
        "core.user_feedback_intelligence", "core.runtime_memory", "core.task_fingerprint", "core.task_fingerprint_facets", "core.task_similarity_engine", "core.retrieval", "loop.kernel", "loop.recursive_loop",
        "core.autoconfigure", "core.boundary_registry", "core.component_contracts", "core.component_inventory", "core.config", "core.intelligence_registry", "core.knowledge_loader", "core.model_call",
        "core.model_gateway_accounting_checks", "core.model_call_contract", "core.reuse_evidence", "core.model_call_records", "core.operation_cost_records", "catalog.versioning", "core.operation_cost_capture", "core.configuration_optimizer",
        "core.service_api", "core.local_resources", "core.local_model_readiness", "core.instance_hibernation", "core.model_discovery", "core.model_routes", "core.operating_profile", "core.persistence", "core.primitive_conformance",
        "code_nodes.overnight_authority", "code_nodes.overnight_journal",
        "code_nodes.overnight_night_checks", "overnight_cli",
        "core.saas_routes", "core.store_serve", "core.model_gateway", "core.settings_loader", "core.parameter_resolution", "core.configuration_setters", "core.configuration_preferences",
        "core.engines.records_checks", "core.engines.selection_records_checks", "core.engines.slot_checks",
        "core.live_dependency_checks", "core.capability_directory", "core.heuristic_adoption", "core.context_artifacts",
        "core.outcome_vector", "core.model_capabilities", "core.contract_matching", "core.model_response_admission",
        "core.model_response_admission_checks", "core.custom_endpoint", "core.custom_endpoint_checks",
        "core.provider_failure_classes", "loop.effect_approval", "loop.loop_profile_ontology",
    ]
    import importlib as _importlib
    import importlib.util as _importlib_util

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
        "catalog.stores.duckdb_store": ("duckdb",),
        "catalog.stores.duckdb_files": ("duckdb",),
        "core.mcp_sdk_transport": ("mcp",),
        "core.service_runtime.http_checks": ("mcp", "starlette", "uvicorn", "httpx", "jwt", "cryptography"),
        "core.service_runtime.stripe_sessions": ("mcp", "starlette", "uvicorn", "httpx", "jwt", "cryptography"),
        "core.decisions.jev": ("httpx",),
        "core.decisions.system_one": ("httpx",),
        "code_nodes.decision_tools": ("mcp", "anyio"),
    }

    def _fold(name, run):
        """Run one module's self_test and report an incomplete installation.

        ``run`` may be a callable OR a module path to import: an adapter that
        imports its dependency at module level raises during IMPORT, before any
        test runs, so guarding only the call left that case uncaught."""
        optional = _OPTIONAL_TEST_DEPENDENCIES.get(name, ())
        unavailable = tuple(module for module in optional
                            if _importlib_util.find_spec(module) is None)
        if unavailable:
            return [{
                "test": f"{name}_optional_adapter_not_tested",
                "owner_module": f"{__package__}.{name}",
                "passed": None, "not_tested": True,
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
            return _module_test_records(name, run())
        except ModuleNotFoundError as exc:
            package = _PACKAGE_FOR_MODULE.get((exc.name or "").split(".")[0])
            if package is None:
                raise                       # a REAL missing import: never hide
            return [{"test": f"{name}_self_test", "passed": False,
                     "owner_module": f"{__package__}.{name}",
                     "missing_dependency": package,
                     "detail": f"FAILED: missing {exc.name}. Reinstall "
                               "Loop Engine to restore all dependencies."}]
        except Exception as exc:
            # One module that raises or times out is one failed record, not
            # the end of the suite. A transport check's asyncio timeout once
            # aborted the whole run before its summary, hiding every other
            # module's result; the suite still reports FAILED for this one.
            return [{"test": f"{name}_self_test_completed", "passed": False,
                     "owner_module": f"{__package__}.{name}",
                     "error_type": type(exc).__name__,
                     "detail": f"FAILED: {name} self_test raised "
                               f"{type(exc).__name__}: {str(exc)[:300]}"}]

    def _raises_timeout():
        raise TimeoutError("offline fixture timeout")

    crashed = _fold("suite_crash_fixture", _raises_timeout)
    results.append({
        "test": "a_module_that_raises_is_one_failed_record_not_the_end_of_the_suite",
        "owner_module": __name__,
        "passed": (len(crashed) == 1 and crashed[0]["passed"] is False
                   and crashed[0].get("error_type") == "TimeoutError"),
        "detail": str(crashed)[:300]})
    check("folded_module_registration_is_nonempty_and_unique",
          bool(_FOLDED_SUBMODULE_TESTS)
          and len(set(_FOLDED_SUBMODULE_TESTS)) == len(_FOLDED_SUBMODULE_TESTS))
    for _name in dict.fromkeys(_FOLDED_SUBMODULE_TESTS):
        results.extend(_fold(_name, _name))
    # solve.py (the demo module) is shadowed on the package by the universal
    # solve() FUNCTION, so import both self-tests explicitly by module path.

    missing = [r for r in results if r.get("missing_dependency")]
    missing_packages = sorted({r["missing_dependency"] for r in missing})
    optional_not_tested = [r for r in results if r.get("not_tested")]
    optional_packages = sorted({package for r in optional_not_tested
                                for package in r.get(
                                    "missing_optional_dependencies", ())})
    return {"record_type": "loop_engine_self_test/v2", "tests": results,
            **_result_counts(results),
            "missing_dependencies": missing_packages,
            "optional_adapters_not_tested": optional_packages,
            "dependency_note": (
                "incomplete installation: " + ", ".join(missing_packages)
                if missing_packages else
                "base installation complete; optional adapters not tested: "
                + ", ".join(optional_packages)
                if optional_packages else
                "base and optional adapter dependencies are installed")}
