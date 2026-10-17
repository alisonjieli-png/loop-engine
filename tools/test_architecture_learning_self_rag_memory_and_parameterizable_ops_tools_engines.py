"""Unit tests for the Architecture-Learning Self-RAG Procedural Memory,
Architecture Improvement Scanner & 16-Recipe Parameterizable Zero-Token
Infrastructure/Ops Tool Crystallizer Engine Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from architecture_learning_self_rag_memory_and_parameterizable_ops_tools_engines import (  # noqa: E402
    ALL_16_PARAMETERIZABLE_OPS_RECIPES,
    ALL_32_INFRA_AND_ARCHITECTURE_OPS_SCENARIOS,
    ARCHITECTURE_LEARNING_SELF_RAG_ADAPTER,
    COMPACT_PARAMETERIZED_INVOCATION_TOKENS,
    COVERAGE_LAYERS,
    ENGINE_BALTOR_ARCHITECTURE_LEARNING_SELF_RAG_AND_PARAMETERIZABLE_OPS_SUITE,
    ENGINE_CLOUDFLARE_SUBDOMAIN_STATIC_WORKER_AND_DNS_PROVISIONER,
    ENGINE_SELF_RAG_PROCEDURAL_MEMORY_RETRIEVER_AND_VERIFIER,
    ENGINE_UNMEMORIZED_LLM_CODEBASE_EXPLORATION_FROM_SCRATCH_BASELINE,
    LAYER_PREFLIGHT,
    OPS_RECIPE_BY_ID,
    PARAMETERIZABLE_INFRA_OPS_ADAPTER,
    SELF_RAG_REFLECTION_TOKENS,
    SIX_ARCHITECTURE_IMPROVEMENT_DIMENSIONS,
    SLOT_ARCHITECTURE_LEARNING_SELF_RAG_AND_PROCEDURAL_MEMORY,
    SLOT_PARAMETERIZABLE_ZERO_TOKEN_INFRA_OPS_TOOLS,
    crystallize_exploration_trace_to_procedural_memory,
    evaluate_architecture_learning_self_rag_and_parameterizable_ops_suite,
    execute_parameterizable_ops_recipe,
    invoke_architecture_learning_self_rag_slot,
    invoke_parameterizable_infra_ops_slot,
    retrieve_and_verify_self_rag_procedural_memory,
    run_known_wrong_refusal_controls,
    scan_architecture_for_improvements_and_bottlenecks,
)


class ArchitectureLearningSelfRagAndParameterizableOpsToolsTests(unittest.TestCase):
    """Verify Slot Family 1 (16 Ops Recipes), Slot Family 2 (Self-RAG Memory & Scanner), 32-task benchmark, and 4 controls."""

    def test_sixteen_parameterizable_ops_recipes_and_cloudflare_subdomain_provisioner(self) -> None:
        self.assertEqual(len(ALL_16_PARAMETERIZABLE_OPS_RECIPES), 16)
        expected_ids = [f"P{idx:02d}_" for idx in range(1, 17)]
        for prefix, spec in zip(expected_ids, ALL_16_PARAMETERIZABLE_OPS_RECIPES, strict=True):
            self.assertTrue(spec.recipe_id.startswith(prefix))
            self.assertGreaterEqual(len(spec.required_params), 3)
            self.assertGreaterEqual(len(spec.invariant_steps), 3)
            self.assertTrue(spec.deterministic_post_check)

        p01_res = execute_parameterizable_ops_recipe(
            "P01_cloudflare_subdomain_and_static_worker_provisioner",
            {
                "subdomain": "docs.baltor.ai",
                "zone_id": "2c8d1f7c4f5f022cd52db9eb94e1629c",
                "account_id": "bc1b9fc2d558fa1bd3feccde66e56e5c",
                "worker_script_name": "docs-baltor-static-worker",
                "routes_map": ("docs.baltor.ai/*",),
                "asset_payloads": {"/": "index.html"},
                "hsts_max_age": 31536000,
            },
        )
        self.assertTrue(p01_res["post_check_passed"])
        self.assertEqual(p01_res["llm_exploration_tokens_used"], 0)
        self.assertEqual(p01_res["compact_invocation_tokens"], COMPACT_PARAMETERIZED_INVOCATION_TOKENS)
        self.assertGreater(p01_res["token_reduction_pct"], 99.0)
        cf_plan = p01_res["cloudflare_subdomain_plan"]
        self.assertEqual(cf_plan["dns_record"]["type"], "CNAME")
        self.assertTrue(cf_plan["dns_record"]["proxied"])
        self.assertEqual(cf_plan["http2_status"], 200)

        for spec in ALL_16_PARAMETERIZABLE_OPS_RECIPES:
            params = {k: f"sample_{k}" for k in spec.required_params}
            if "hsts_max_age" in params:
                params["hsts_max_age"] = 31536000
            exec_res = execute_parameterizable_ops_recipe(spec.recipe_id, params)
            self.assertTrue(exec_res["post_check_passed"])
            self.assertEqual(exec_res["llm_exploration_tokens_used"], 0)
            self.assertIn(spec.recipe_id, OPS_RECIPE_BY_ID)

    def test_self_rag_procedural_memory_crystallizer_retriever_and_architecture_scanner(self) -> None:
        mem = crystallize_exploration_trace_to_procedural_memory(
            trace_id="trace_cf_subdomain_01",
            task_signature="provision_cloudflare_subdomain_and_worker_route",
            observed_exploration_tokens=18400,
            bound_recipe_id="P01_cloudflare_subdomain_and_static_worker_provisioner",
            referenced_files=(
                "tools/architecture_learning_self_rag_memory_and_parameterizable_ops_tools_engines.py",
                "MEMORY.md",
            ),
            codebase_tree_sha256="sha256:1c28c1c3_live",
        )
        self.assertEqual(mem.exploration_tokens_before_crystallization, 18400)
        self.assertEqual(mem.exploration_tokens_after_crystallization, 0)
        self.assertEqual(mem.reflection_tokens, SELF_RAG_REFLECTION_TOKENS)
        self.assertIn("MEMORY.md", mem.memory_targets_updated)
        self.assertIn("skills.state", mem.memory_targets_updated)

        retrieved = retrieve_and_verify_self_rag_procedural_memory(
            query_intent="add new cloudflare static subdomain",
            memory_entry=mem,
            live_codebase_tree_sha256="sha256:1c28c1c3_live",
        )
        self.assertTrue(retrieved["sha256_verified"])
        self.assertLess(retrieved["lookup_latency_ms"], 0.4)
        self.assertEqual(retrieved["llm_exploration_tokens"], 0)
        self.assertEqual(
            retrieved["reflection_verdicts"]["[ISSUP: supported_by_codebase_sha256]"],
            "supported_by_codebase_sha256",
        )

        scan = scan_architecture_for_improvements_and_bottlenecks()
        self.assertEqual(scan["scanned_dimensions"], SIX_ARCHITECTURE_IMPROVEMENT_DIMENSIONS)
        self.assertEqual(scan["dimension_count"], 6)
        self.assertTrue(scan["all_mapped_to_parameterized_recipes"])

    def test_thin_component_adapter_contract_receipt_and_hot_swap(self) -> None:
        c1 = PARAMETERIZABLE_INFRA_OPS_ADAPTER.inspect_contract()
        c2 = ARCHITECTURE_LEARNING_SELF_RAG_ADAPTER.inspect_contract()
        self.assertEqual(c1["slot_id"], SLOT_PARAMETERIZABLE_ZERO_TOKEN_INFRA_OPS_TOOLS)
        self.assertEqual(c2["slot_id"], SLOT_ARCHITECTURE_LEARNING_SELF_RAG_AND_PROCEDURAL_MEMORY)
        self.assertLess(c1["loc"], 30)
        self.assertLess(c2["loc"], 30)

        r1 = invoke_parameterizable_infra_ops_slot(
            {"recipe_id": "P02_cloudflare_static_directory_site_sync"}
        )
        r2 = invoke_architecture_learning_self_rag_slot(
            {"bound_recipe_id": "P02_cloudflare_static_directory_site_sync"}
        )
        self.assertTrue(PARAMETERIZABLE_INFRA_OPS_ADAPTER.verify_receipt(r1))
        self.assertTrue(ARCHITECTURE_LEARNING_SELF_RAG_ADAPTER.verify_receipt(r2))
        self.assertEqual(set(r1.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        self.assertEqual(set(r2.layer_verdicts.keys()), set(COVERAGE_LAYERS))

        swapped_s1 = PARAMETERIZABLE_INFRA_OPS_ADAPTER.swap_engine(
            ENGINE_CLOUDFLARE_SUBDOMAIN_STATIC_WORKER_AND_DNS_PROVISIONER
        )
        self.assertEqual(
            swapped_s1.engine_order[0],
            ENGINE_CLOUDFLARE_SUBDOMAIN_STATIC_WORKER_AND_DNS_PROVISIONER,
        )
        swapped_s2 = ARCHITECTURE_LEARNING_SELF_RAG_ADAPTER.swap_engine(
            ENGINE_SELF_RAG_PROCEDURAL_MEMORY_RETRIEVER_AND_VERIFIER
        )
        self.assertEqual(
            swapped_s2.engine_order[0],
            ENGINE_SELF_RAG_PROCEDURAL_MEMORY_RETRIEVER_AND_VERIFIER,
        )
        self.assertTrue(PARAMETERIZABLE_INFRA_OPS_ADAPTER.preflight({"recipe_id": "P01"}).ready)
        self.assertTrue(ARCHITECTURE_LEARNING_SELF_RAG_ADAPTER.preflight({"trace_id": "ok"}).ready)

    def test_four_known_wrong_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        expected_codes = {
            "invalid_or_missing_ops_recipe_parameter_blocked": "invalid_or_missing_ops_recipe_parameter_refused",
            "stale_procedural_memory_sha256_mismatch_blocked": "stale_procedural_memory_sha256_mismatch_refused",
            "secret_literal_in_procedural_memory_blocked": "secret_literal_in_procedural_memory_refused",
            "unverified_tool_crystallization_blocked": "unverified_tool_crystallization_refused",
        }
        for probe_id, code in expected_codes.items():
            probe = controls["probes"][probe_id]
            self.assertFalse(probe["accepted"])
            self.assertEqual(probe["refused_by"], LAYER_PREFLIGHT)
            self.assertEqual(probe["refusal_code"], code)
            self.assertTrue(probe["blocked_before_engine"])

    def test_32_scenario_benchmark_suite(self) -> None:
        self.assertEqual(len(ALL_32_INFRA_AND_ARCHITECTURE_OPS_SCENARIOS), 32)
        report = evaluate_architecture_learning_self_rag_and_parameterizable_ops_suite()
        self.assertEqual(report["scenario_count"], 32)
        self.assertEqual(report["parameterizable_recipe_count"], 16)
        self.assertEqual(report["architecture_dimension_count"], 6)
        self.assertTrue(report["all_scenarios_accepted"])
        self.assertTrue(report["hot_swap_verified"])

        base = report["benchmarks"][ENGINE_UNMEMORIZED_LLM_CODEBASE_EXPLORATION_FROM_SCRATCH_BASELINE]
        baltor = report["benchmarks"][ENGINE_BALTOR_ARCHITECTURE_LEARNING_SELF_RAG_AND_PARAMETERIZABLE_OPS_SUITE]
        self.assertEqual(base["mean_exploration_tokens_per_ops_task"], 18400)
        self.assertEqual(base["mean_grep_view_tool_turns_before_action"], 9.5)
        self.assertEqual(base["first_attempt_error_rate_pct"], 31.2)
        self.assertEqual(baltor["mean_exploration_tokens_per_ops_task"], 0)
        self.assertEqual(baltor["compact_parameterized_invocation_tokens"], 140)
        self.assertEqual(baltor["token_reduction_pct"], 99.2)
        self.assertEqual(baltor["deterministic_tool_calls_per_task"], 1)
        self.assertEqual(baltor["first_attempt_execution_accuracy_pct"], 100.0)
        self.assertLess(baltor["self_rag_procedural_memory_lookup_latency_ms"], 0.4)


if __name__ == "__main__":
    unittest.main()
