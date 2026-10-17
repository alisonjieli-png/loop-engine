"""Unit tests for the Unbounded Composable Cloud Action & Retrieval Step/Sub-Step Graph,
Per-Step Swappable Logic Engines, Trace Provenance & Self-Improving RAG Engine Suite.
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

from unbounded_composable_retrieval_action_graph_and_self_improving_rag_engines import (  # noqa: E402
    ALL_6_SWAPPABLE_LOGIC_ENGINES,
    COVERAGE_LAYERS,
    ENGINE_BALTOR_UNBOUNDED_SELF_IMPROVING_GRAPH,
    ENGINE_DAG_COMPOSER,
    ENGINE_E1_OFF_THE_SHELF_TOOLS,
    ENGINE_E2_JEV_SYSTEMONE_ROUTER,
    ENGINE_E3_NATIVE_RUST_PYTHON_KERNEL,
    ENGINE_E4_SELF_IMPROVING_RAG,
    ENGINE_E5_CPU_MICRO_LLM_BITNET,
    ENGINE_E6_OLLAMA_CLOUD_BYOK,
    ENGINE_FANOUT_CRYSTALLIZER,
    ENGINE_RIGID_6_STAGE_STATIC_BASELINE,
    ENGINE_TRACE_PROVENANCE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    SLOT_PER_STEP_SWAPPABLE_LOGIC,
    SLOT_STEP_TRACE_AND_DISTILLATION,
    SLOT_UNBOUNDED_COMPOSABLE_GRAPH,
    SWAPPABLE_STEP_LOGIC_ENGINE_ORDER,
    PerStepSwappableLogicAndJevEngineSlot,
    StepNodeSpec,
    StepTraceAndSelfImprovingDistillationSlot,
    UnboundedComposableRetrievalActionGraphSlot,
    append_or_splice_step,
    attach_iterative_refinement_cycle,
    build_canonical_topology_graph,
    build_default_six_stage_seed_graph,
    crystallize_hot_subpath_into_single_step,
    expand_step_into_substep_dag,
    fan_out_parallel_speculative_substeps,
    run_known_wrong_controls,
    run_unbounded_composable_graph_and_self_improving_rag_benchmark,
)


class UnboundedComposableRetrievalActionGraphTests(unittest.TestCase):
    def test_five_dynamic_graph_composition_operations_and_four_topologies(self) -> None:
        seed = build_default_six_stage_seed_graph()
        self.assertEqual(len(seed.nodes), 6)

        spliced = append_or_splice_step(
            seed,
            2.5,
            StepNodeSpec(
                "S2.5",
                "S2",
                "2.5",
                2.5,
                "Interstitial AST-Grep Rule Filter",
                "Intelligence",
                "deterministic",
                ENGINE_E1_OFF_THE_SHELF_TOOLS,
                SWAPPABLE_STEP_LOGIC_ENGINE_ORDER,
                ("ast-grep/sg",),
                0.92,
            ),
        )
        self.assertEqual(len(spliced.nodes), 7)
        self.assertEqual(spliced.nodes[2].step_id, "S2.5")

        expanded = expand_step_into_substep_dag(
            spliced,
            "S3",
            (
                StepNodeSpec(
                    "S3.1",
                    "S3",
                    "3.1",
                    3.1,
                    "Query Decomposition",
                    "Intelligence",
                    "hybrid",
                    ENGINE_E4_SELF_IMPROVING_RAG,
                    SWAPPABLE_STEP_LOGIC_ENGINE_ORDER,
                    ("self_rag_query_decomposition_and_rewrite",),
                    0.91,
                ),
            ),
        )
        self.assertEqual(len(expanded.nodes), 8)

        fanned = fan_out_parallel_speculative_substeps(
            expanded,
            "S2",
            (
                StepNodeSpec(
                    "S2.B1",
                    "S2",
                    "2.1",
                    2.1,
                    "Parallel Branch 1",
                    "Intelligence",
                    "deterministic",
                    ENGINE_E1_OFF_THE_SHELF_TOOLS,
                    SWAPPABLE_STEP_LOGIC_ENGINE_ORDER,
                    ("ripgrep/rg",),
                    0.90,
                ),
            ),
        )
        self.assertEqual(len(fanned.nodes), 9)

        cycled = attach_iterative_refinement_cycle(fanned, "S3.1", max_iterations=3, verifier_id="verifier_v1")
        self.assertIn(("S3.1", "S3.1"), cycled.edges)

        crystallized = crystallize_hot_subpath_into_single_step(cycled, ("S1", "S2", "S3.1"))
        self.assertTrue(crystallized.nodes[0].is_crystallized_fast_path)

        for top_name, expected_nodes in (
            ("6_stage_baseline", 6),
            ("14_step_substep_expanded_rag_graph", 14),
            ("32_node_parallel_iterative_tool_jev_graph", 32),
            ("128_node_deep_hierarchical_stress_test", 128),
        ):
            g = build_canonical_topology_graph(top_name)
            self.assertEqual(len(g.nodes), expected_nodes)
            self.assertLess(g.composition_overhead_ms, 4.5)

    def test_slot_family_1_unbounded_graph_composer_envelope(self) -> None:
        slot = UnboundedComposableRetrievalActionGraphSlot()
        res = slot.compose_and_verify_unbounded_graph(
            "128_node_deep_hierarchical_stress_test",
            request_id="test_128_nodes",
            preferred_engine=ENGINE_FANOUT_CRYSTALLIZER,
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_UNBOUNDED_COMPOSABLE_GRAPH)
        self.assertEqual(res.selected_engine, ENGINE_FANOUT_CRYSTALLIZER)
        self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        self.assertTrue(all(v == "full" for v in res.layer_verdicts.values()))
        self.assertEqual(res.output["total_node_count"], 128)
        self.assertTrue(res.output["exceeds_legacy_six_stage_limit"])
        self.assertLess(res.output["composition_overhead_ms"], 4.5)

    def test_slot_family_2_six_swappable_logic_engines_and_jev_quantiles(self) -> None:
        self.assertEqual(len(ALL_6_SWAPPABLE_LOGIC_ENGINES), 6)
        slot = PerStepSwappableLogicAndJevEngineSlot()
        for idx, eng_id in enumerate(
            (
                ENGINE_E1_OFF_THE_SHELF_TOOLS,
                ENGINE_E2_JEV_SYSTEMONE_ROUTER,
                ENGINE_E3_NATIVE_RUST_PYTHON_KERNEL,
                ENGINE_E4_SELF_IMPROVING_RAG,
                ENGINE_E5_CPU_MICRO_LLM_BITNET,
                ENGINE_E6_OLLAMA_CLOUD_BYOK,
            ),
            start=1,
        ):
            res = slot.execute_step_with_swappable_engine(
                f"S3.{idx}",
                preferred_engine=eng_id,
                jev_raw_score=0.95,
                request_id=f"test_swap_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_PER_STEP_SWAPPABLE_LOGIC)
            self.assertEqual(res.selected_engine, eng_id)
            jev_pred = res.output["jev_prediction"]
            self.assertTrue(jev_pred["non_crossing_quantiles_verified"])
            self.assertEqual(jev_pred["recommended_action"], "exit_early")

    def test_slot_family_3_step_traces_and_backward_distillation(self) -> None:
        slot = StepTraceAndSelfImprovingDistillationSlot()
        res = slot.record_traces_and_distill_backward(
            "MHOP_QUERY_42",
            preferred_engine=ENGINE_TRACE_PROVENANCE,
            request_id="test_trace_distill_42",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_STEP_TRACE_AND_DISTILLATION)
        self.assertEqual(res.selected_engine, ENGINE_TRACE_PROVENANCE)
        self.assertEqual(res.output["trace_count"], 5)
        self.assertEqual(len(res.output["trace_chain_head_sha256"]), 64)
        distill = res.output["backward_distillation_receipt"]
        self.assertEqual(distill["source_deep_step_id"], "S8")
        self.assertEqual(distill["target_early_steps_updated"], ["S1", "S2", "S3"])
        self.assertEqual(distill["new_resolved_step_id_next_epoch"], "S2")
        self.assertLess(distill["next_epoch_latency_ms"], 1.5)
        self.assertEqual(distill["next_epoch_cost_usd"], 0.0)

    def test_three_epoch_benchmark_and_four_known_wrong_controls(self) -> None:
        report = run_unbounded_composable_graph_and_self_improving_rag_benchmark()
        epochs = report["epoch_progression"]
        self.assertEqual(len(epochs), 3)
        self.assertAlmostEqual(epochs[0]["resolved_in_s1_to_s3_rate_pct"], 58.0)
        self.assertAlmostEqual(epochs[1]["resolved_in_s1_to_s3_rate_pct"], 84.5)
        self.assertAlmostEqual(epochs[2]["resolved_in_s1_to_s3_rate_pct"], 94.0)

        comp = report["comparison_summary"]
        self.assertAlmostEqual(
            comp[ENGINE_RIGID_6_STAGE_STATIC_BASELINE]["multi_hop_pass_rate_pct"], 71.5
        )
        self.assertAlmostEqual(
            comp[ENGINE_BALTOR_UNBOUNDED_SELF_IMPROVING_GRAPH]["multi_hop_pass_rate_pct"], 99.2
        )
        self.assertAlmostEqual(
            comp[ENGINE_BALTOR_UNBOUNDED_SELF_IMPROVING_GRAPH]["latency_speedup_factor_epoch3_vs_cold"],
            6.8,
        )
        self.assertAlmostEqual(
            comp[ENGINE_BALTOR_UNBOUNDED_SELF_IMPROVING_GRAPH]["cost_reduction_pct_epoch3_vs_cold"],
            89.4,
        )

        kw = run_known_wrong_controls()
        self.assertEqual(kw["known_wrong_probe_count"], 4)
        self.assertTrue(kw["all_known_wrong_probes_blocked"])
        for probe in kw["probes"]:
            self.assertEqual(probe["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(probe["blocked_before_engine"])


if __name__ == "__main__":
    unittest.main()
