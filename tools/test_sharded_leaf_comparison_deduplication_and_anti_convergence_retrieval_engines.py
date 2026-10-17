"""Unit tests for the Sharded Canopy/Ball-Tree Leaf-Based All-Pairs Comparator,
4-Stage Exact-to-Semantic Deduplication Pipeline & Anti-Hubness / Anti-Convergence
Retrieval Diversifier (`CSLS` + `DPP` + `Submodular MMR`) Suite.
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

from sharded_leaf_comparison_deduplication_and_anti_convergence_retrieval_engines import (  # noqa: E402
    ALL_40_RETRIEVAL_DEDUP_WORKLOADS,
    ANTI_CONVERGENCE_RETRIEVAL_ADAPTER,
    COMPUTE_REDUCTION_FACTOR,
    COVERAGE_LAYERS,
    DEFAULT_LEAF_MAX_SIZE,
    DEFAULT_OVERLAP_MARGIN_PCT,
    ENGINE_BALTOR_SHARDED_LEAF_AND_CSLS_DPP_SUITE,
    ENGINE_DPP_AND_SUBMODULAR_MMR_DIVERSIFIER,
    ENGINE_FOUR_TIER_EXACT_AST_MINHASH_SEMANTIC_DEDUPLICATOR,
    ENGINE_NAIVE_QUADRATIC_AND_STANDARD_COSINE_BASELINE,
    FULL_CATALOG_COMPONENT_COUNT,
    LAYER_PREFLIGHT,
    MIN_SHANNON_LEAF_ENTROPY_BITS,
    OBSERVED_DUPLICATE_RECALL_PCT,
    SHARDED_LEAF_DEDUP_ADAPTER,
    SIMULATED_INDEXED_RECORD_COUNT,
    SLOT_ANTI_HUBNESS_AND_ANTI_CONVERGENCE_RETRIEVAL,
    SLOT_SHARDED_LEAF_COMPARISON_AND_DEDUPLICATION,
    compute_csls_anti_hubness_score,
    compute_sharded_leaf_comparison_scaling,
    compute_shingle_minhash_jaccard,
    evaluate_sharded_leaf_and_anti_convergence_suite,
    invoke_anti_convergence_retrieval_slot,
    invoke_sharded_leaf_deduplication_slot,
    normalize_ast_structural_signature,
    partition_items_into_overlapping_leaves,
    run_four_tier_deduplication_cascade,
    run_known_wrong_refusal_controls,
    select_dpp_and_submodular_mmr_topk,
)


class ShardedLeafComparisonAndAntiConvergenceRetrievalTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 1M-record / 40-workload benchmarks, and 4 known-wrong controls."""

    def test_sharded_leaf_scaling_reduces_1_9m_pairs_by_29600x(self) -> None:
        scaling = compute_sharded_leaf_comparison_scaling(
            total_items=FULL_CATALOG_COMPONENT_COUNT,
            leaf_max_size=DEFAULT_LEAF_MAX_SIZE,
            overlap_margin_pct=DEFAULT_OVERLAP_MARGIN_PCT,
        )
        self.assertEqual(scaling["total_items"], 1_900_000)
        self.assertEqual(scaling["leaf_max_size"], 64)
        self.assertEqual(scaling["overlap_margin_pct"], 15.0)
        self.assertEqual(scaling["naive_all_pairs_count"], 1_804_999_050_000)
        self.assertEqual(scaling["sharded_within_leaf_pairs_count"], 60_979_698)
        self.assertEqual(scaling["compute_reduction_factor_x"], COMPUTE_REDUCTION_FACTOR)
        self.assertEqual(scaling["true_duplicate_pair_recall_pct"], OBSERVED_DUPLICATE_RECALL_PCT)

    def test_overlapping_leaf_partition_respects_leaf_bound_and_spillover_margin(self) -> None:
        items = [
            {
                "item_id": f"comp_{i:03d}",
                "ontology_prefix": "code.python" if i < 90 else "skill.md",
                "embedding": (float(i) / 100.0, float(100 - i) / 100.0),
            }
            for i in range(120)
        ]
        leaves = partition_items_into_overlapping_leaves(
            items,
            leaf_max_size=32,
            overlap_margin_pct=15.0,
        )
        self.assertGreaterEqual(len(leaves), 4)
        for leaf in leaves:
            self.assertLessEqual(len(leaf.item_ids), 32)
        spillover_leaves = [leaf for leaf in leaves if leaf.spillover_item_ids]
        self.assertGreaterEqual(len(spillover_leaves), 2)

    def test_four_tier_deduplication_cascade_collapses_d1_d2_d3_d4(self) -> None:
        code_a = 'def solve_wave(grid, dt):\n    """Solve wave PDE."""\n    # step forward\n    return grid + dt * 2\n'
        code_b = "def advance_field(mesh, step):\n    return mesh + step * 2\n"
        self.assertEqual(
            normalize_ast_structural_signature(code_a),
            normalize_ast_structural_signature(code_b),
        )
        jaccard = compute_shingle_minhash_jaccard(
            "adaptive runge kutta fourth order trajectory integrator solver",
            "adaptive runge kutta fourth order trajectory integrator module",
        )
        self.assertGreaterEqual(jaccard, 0.70)

        res = invoke_sharded_leaf_deduplication_slot({"dataset_records": 25_000})
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_SHARDED_LEAF_COMPARISON_AND_DEDUPLICATION)
        self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        cascade = res.output["cascade"]
        self.assertEqual(cascade["input_candidate_count"], 5)
        self.assertEqual(cascade["surviving_canonical_count"], 1)
        self.assertEqual(cascade["archived_duplicate_count"], 4)
        self.assertEqual(cascade["tier_collapse_counts"]["D1_sha256_exact"], 1)
        self.assertEqual(cascade["tier_collapse_counts"]["D2_normalized_ast"], 1)
        self.assertEqual(cascade["tier_collapse_counts"]["D3_minhash_simhash"], 1)
        self.assertEqual(cascade["tier_collapse_counts"]["D4_subsumption_merger"], 1)

    def test_csls_anti_hubness_and_dpp_mmr_retrieval_diversifier(self) -> None:
        query_vec = (0.9, 0.2, 0.1, 0.0)
        specialist_vec = (0.88, 0.22, 0.11, 0.0)
        hub_vec = (0.89, 0.21, 0.10, 0.0)
        specialist_csls = compute_csls_anti_hubness_score(query_vec, specialist_vec, 0.50, 0.40)
        hub_csls = compute_csls_anti_hubness_score(query_vec, hub_vec, 0.50, 0.92)
        self.assertGreater(specialist_csls, hub_csls)

        res = invoke_anti_convergence_retrieval_slot({"top_k": 10})
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_ANTI_HUBNESS_AND_ANTI_CONVERGENCE_RETRIEVAL)
        self.assertEqual(len(res.output["selected_cards"]), 10)
        self.assertGreaterEqual(res.output["distinct_leaf_count"], 8)
        self.assertGreaterEqual(res.output["shannon_leaf_entropy_bits"], MIN_SHANNON_LEAF_ENTROPY_BITS)
        self.assertLessEqual(res.output["max_pairwise_similarity"], 0.85)
        self.assertEqual(res.output["redundant_clone_rate_pct"], 0.0)
        self.assertEqual(res.output["hub_cards_selected"], 0)

    def test_thin_component_adapter_hot_swap_and_preflight(self) -> None:
        swapped_dedup = SHARDED_LEAF_DEDUP_ADAPTER.swap_engine(
            ENGINE_FOUR_TIER_EXACT_AST_MINHASH_SEMANTIC_DEDUPLICATOR
        )
        self.assertEqual(
            swapped_dedup.engine_order[0],
            ENGINE_FOUR_TIER_EXACT_AST_MINHASH_SEMANTIC_DEDUPLICATOR,
        )
        swapped_ret = ANTI_CONVERGENCE_RETRIEVAL_ADAPTER.swap_engine(
            ENGINE_DPP_AND_SUBMODULAR_MMR_DIVERSIFIER
        )
        self.assertEqual(swapped_ret.engine_order[0], ENGINE_DPP_AND_SUBMODULAR_MMR_DIVERSIFIER)
        self.assertTrue(SHARDED_LEAF_DEDUP_ADAPTER.preflight({"dataset_records": 5000}).ready)
        self.assertTrue(ANTI_CONVERGENCE_RETRIEVAL_ADAPTER.preflight({"top_k": 10}).ready)

    def test_four_known_wrong_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        expected_codes = {
            "unsharded_quadratic_all_pairs_blowup_blocked": "unsharded_quadratic_all_pairs_blowup_refused",
            "zero_overlap_boundary_miss_risk_blocked": "zero_overlap_boundary_miss_risk_refused",
            "top_k_redundant_convergence_clone_blocked": "top_k_redundant_convergence_clone_refused",
            "subsumption_verifier_regression_blocked": "subsumption_verifier_regression_refused",
        }
        for probe_id, expected_code in expected_codes.items():
            probe = controls["probes"][probe_id]
            self.assertFalse(probe["accepted"])
            self.assertEqual(probe["refused_by"], LAYER_PREFLIGHT)
            self.assertEqual(probe["refusal_code"], expected_code)
            self.assertTrue(probe["blocked_before_engine"])

    def test_full_1m_record_40_workload_benchmark_suite(self) -> None:
        self.assertEqual(len(ALL_40_RETRIEVAL_DEDUP_WORKLOADS), 40)
        report = evaluate_sharded_leaf_and_anti_convergence_suite()
        self.assertEqual(report["workload_count"], 40)
        self.assertEqual(report["simulated_indexed_record_count"], SIMULATED_INDEXED_RECORD_COUNT)
        self.assertTrue(report["all_workloads_accepted"])
        self.assertTrue(report["hot_swap_verified"])
        self.assertTrue(report["known_wrong_controls"]["all_blocked_at_preflight"])

        base = report["benchmarks"][ENGINE_NAIVE_QUADRATIC_AND_STANDARD_COSINE_BASELINE]
        suite = report["benchmarks"][ENGINE_BALTOR_SHARDED_LEAF_AND_CSLS_DPP_SUITE]
        self.assertEqual(suite["pair_comparison_reduction_factor_x"], 29600.0)
        self.assertEqual(suite["true_duplicate_recall_pct"], 99.6)
        self.assertLess(suite["top_10_redundant_clone_rate_pct"], base["top_10_redundant_clone_rate_pct"])
        self.assertLess(suite["hubness_dominance_distortion_pct"], base["hubness_dominance_distortion_pct"])
        self.assertGreater(
            suite["downstream_multi_hypothesis_pass_rate_pct"],
            base["downstream_multi_hypothesis_pass_rate_pct"],
        )


if __name__ == "__main__":
    unittest.main()
