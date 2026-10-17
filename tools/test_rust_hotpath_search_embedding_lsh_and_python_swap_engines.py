"""Tests for the Native Rust High-Compute Search, Retrieval, 64-Bit Matryoshka
Embedding, MinHash LSH & LLM Logic Hotpath Accelerator with Instant Hot-Swappable
Python Fallback Engine Suite.
"""
from __future__ import annotations

import unittest

from tools.rust_hotpath_search_embedding_lsh_and_python_swap_engines import (
    ALL_HOTPATH_KERNELS,
    ALL_SLOTS,
    ENGINE_DUAL_PARITY_SHADOW_VERIFIER,
    ENGINE_PYTHON_BIT_EXACT_FALLBACK,
    ENGINE_RUST_NATIVE_CDYLIB,
    ENGINE_SANDBOX_POLICY_GUARD,
    HOTPATH_COMPUTE_ENGINE_ORDER,
    HOTSWAP_CONTROLLER_ENGINE_ORDER,
    PREF_PREFER_PYTHON,
    PREF_PREFER_RUST,
    PREF_SHADOW_VERIFY_BOTH,
    QUANTILE_21_LEVELS,
    SLOT_HOTPATH_COMPUTE,
    SLOT_NODE_HOTSWAP_CONTROLLER,
    HotpathComputeRequest,
    NodeHotswapControllerRequest,
    RuntimeRustPythonNodeHotswapController,
    RustOrPythonHotpathComputeOrchestrator,
    get_or_compile_rust_hotpath_cdylib,
    python_k4_llm_token_quantile_gate,
    run_rust_vs_python_hotpath_benchmark,
    rust_k4_llm_token_quantile_gate,
)


class RustHotpathAndPythonSwapEnginesTest(unittest.TestCase):
    """Verify compiled Rust cdylib kernels, bit-exact Python fallback, hot-swap receipts, and known-wrong controls."""

    def test_slot_and_kernel_catalog_constants(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        self.assertEqual(len(ALL_HOTPATH_KERNELS), 4)
        self.assertEqual(len(HOTPATH_COMPUTE_ENGINE_ORDER), 3)
        self.assertEqual(len(HOTSWAP_CONTROLLER_ENGINE_ORDER), 3)
        self.assertEqual(len(QUANTILE_21_LEVELS), 21)

    def test_rustc_cdylib_compilation_and_symbol_binding(self) -> None:
        lib, so_path, rustc_version = get_or_compile_rust_hotpath_cdylib()
        self.assertIsNotNone(lib)
        self.assertTrue(so_path.exists())
        self.assertIn("rustc", rustc_version)

    def test_slot1_rust_python_and_shadow_verifier_bit_exact_parity(self) -> None:
        orchestrator = RustOrPythonHotpathComputeOrchestrator()

        rust_resp = orchestrator.handle(
            HotpathComputeRequest(
                schema="rust_or_python_hotpath_compute_request/v1",
                preferred_engine=ENGINE_RUST_NATIVE_CDYLIB,
            )
        )
        self.assertTrue(rust_resp.accepted)
        self.assertEqual(rust_resp.slot_id, SLOT_HOTPATH_COMPUTE)
        self.assertEqual(rust_resp.selected_engine, ENGINE_RUST_NATIVE_CDYLIB)
        self.assertFalse(rust_resp.fallback_used)
        self.assertTrue(rust_resp.bit_exact_parity_verified)
        self.assertEqual(rust_resp.nested_frame_depth, 1)
        self.assertEqual(rust_resp.k1_topk_distances[0], 0)
        self.assertEqual(rust_resp.k4_epistemic_gate_decision, "Abstain" if False else "abstain_epistemic_uncertainty")

        py_resp = orchestrator.handle(
            HotpathComputeRequest(
                schema="rust_or_python_hotpath_compute_request/v1",
                preferred_engine=ENGINE_PYTHON_BIT_EXACT_FALLBACK,
            )
        )
        self.assertTrue(py_resp.accepted)
        self.assertEqual(py_resp.selected_engine, ENGINE_PYTHON_BIT_EXACT_FALLBACK)
        self.assertEqual(rust_resp.k1_topk_indices, py_resp.k1_topk_indices)
        self.assertEqual(rust_resp.k1_topk_distances, py_resp.k1_topk_distances)
        self.assertEqual(rust_resp.k2_minhash_sig_head, py_resp.k2_minhash_sig_head)
        self.assertEqual(rust_resp.k2_band_hashes, py_resp.k2_band_hashes)
        self.assertEqual(rust_resp.k2_batch_equal_counts, py_resp.k2_batch_equal_counts)
        self.assertEqual(rust_resp.k2_batch_band_hits, py_resp.k2_batch_band_hits)
        self.assertEqual(rust_resp.k2_batch_jaccards, py_resp.k2_batch_jaccards)
        self.assertEqual(rust_resp.k3_int8_dots, py_resp.k3_int8_dots)
        self.assertEqual(rust_resp.k3_cosine_scores, py_resp.k3_cosine_scores)
        self.assertEqual(rust_resp.k4_estimated_tokens, py_resp.k4_estimated_tokens)
        self.assertEqual(rust_resp.k4_projected_quantiles_bp, py_resp.k4_projected_quantiles_bp)
        self.assertEqual(rust_resp.k4_epistemic_spread_bp, py_resp.k4_epistemic_spread_bp)

        shadow_resp = orchestrator.handle(
            HotpathComputeRequest(
                schema="rust_or_python_hotpath_compute_request/v1",
                preferred_engine=ENGINE_DUAL_PARITY_SHADOW_VERIFIER,
            )
        )
        self.assertTrue(shadow_resp.accepted)
        self.assertEqual(shadow_resp.selected_engine, ENGINE_DUAL_PARITY_SHADOW_VERIFIER)
        self.assertTrue(shadow_resp.bit_exact_parity_verified)

    def test_k4_isotonic_projection_when_crossing_allowed(self) -> None:
        crossed = (
            500, 900, 1500, 1200, 2100, 2500, 2900, 3300, 3700, 4100,
            4500, 4900, 5300, 5700, 6100, 6500, 6900, 7300, 7700, 3800, 8900,
        )
        r_tok, r_proj, r_cross, r_spread, r_gate = rust_k4_llm_token_quantile_gate(
            "Verify non-crossing isotonic projection on 21 quantiles.", crossed
        )
        p_tok, p_proj, p_cross, p_spread, p_gate = python_k4_llm_token_quantile_gate(
            "Verify non-crossing isotonic projection on 21 quantiles.", crossed
        )
        self.assertEqual((r_tok, r_proj, r_cross, r_spread, r_gate), (p_tok, p_proj, p_cross, p_spread, p_gate))
        self.assertEqual(r_cross, 2)
        for i in range(1, 21):
            self.assertGreaterEqual(r_proj[i], r_proj[i - 1])

    def test_slot2_live_runtime_node_hotswap_and_wasi_sandbox_fallback(self) -> None:
        controller = RuntimeRustPythonNodeHotswapController()
        resp = controller.handle(
            NodeHotswapControllerRequest(
                schema="runtime_rust_python_node_hotswap_request/v1",
                node_id="loop_matryoshka_lsh_rerank_vertex",
                preference_sequence=(
                    PREF_PREFER_RUST,
                    PREF_PREFER_PYTHON,
                    PREF_SHADOW_VERIFY_BOTH,
                    PREF_PREFER_RUST,
                ),
            )
        )
        self.assertTrue(resp.accepted)
        self.assertEqual(resp.slot_id, SLOT_NODE_HOTSWAP_CONTROLLER)
        self.assertEqual(resp.transitions_executed, 4)
        self.assertTrue(resp.all_outputs_bit_exact_across_swaps)
        self.assertEqual(resp.dropped_in_flight_requests, 0)
        self.assertLess(resp.max_switchover_latency_ms, 5.0)
        self.assertEqual(
            tuple(r.active_compute_engine for r in resp.selection_receipts),
            (
                ENGINE_RUST_NATIVE_CDYLIB,
                ENGINE_PYTHON_BIT_EXACT_FALLBACK,
                ENGINE_DUAL_PARITY_SHADOW_VERIFIER,
                ENGINE_RUST_NATIVE_CDYLIB,
            ),
        )

        # WASI / browser sandbox policy automatically routes to pure-Python fallback
        sandbox_resp = controller.handle(
            NodeHotswapControllerRequest(
                schema="runtime_rust_python_node_hotswap_request/v1",
                node_id="loop_browser_wasi_sandbox_vertex",
                preference_sequence=(PREF_PREFER_RUST, PREF_SHADOW_VERIFY_BOTH),
                sandbox_restricts_native_cdylib=True,
                preferred_controller_engine="unknown_controller_engine",
            )
        )
        self.assertTrue(sandbox_resp.accepted)
        self.assertTrue(sandbox_resp.fallback_used)
        self.assertEqual(sandbox_resp.selected_controller_engine, ENGINE_SANDBOX_POLICY_GUARD)
        self.assertTrue(
            all(
                r.active_compute_engine == ENGINE_PYTHON_BIT_EXACT_FALLBACK
                and r.sandbox_restricted_native_cdylib
                for r in sandbox_resp.selection_receipts
            )
        )

    def test_known_wrong_controls_refuse_invalid_states(self) -> None:
        orchestrator = RustOrPythonHotpathComputeOrchestrator()
        controller = RuntimeRustPythonNodeHotswapController()

        # Known-wrong control (a): refuse Rust/Python swap when parity divergence fault is injected
        div_resp = orchestrator.handle(
            HotpathComputeRequest(
                schema="rust_or_python_hotpath_compute_request/v1",
                inject_parity_divergence_fault=True,
            )
        )
        self.assertFalse(div_resp.accepted)
        self.assertIsNotNone(div_resp.refusal)
        assert div_resp.refusal is not None
        self.assertEqual(div_resp.refusal.code, "rust_python_parity_divergence_refused")

        ctrl_div_resp = controller.handle(
            NodeHotswapControllerRequest(
                schema="runtime_rust_python_node_hotswap_request/v1",
                compute_request=HotpathComputeRequest(
                    schema="rust_or_python_hotpath_compute_request/v1",
                    inject_parity_divergence_fault=True,
                ),
            )
        )
        self.assertFalse(ctrl_div_resp.accepted)
        assert ctrl_div_resp.refusal is not None
        self.assertEqual(ctrl_div_resp.refusal.code, "rust_python_parity_divergence_refused")

        # Known-wrong control (b): refuse unsafe out-of-bounds FFI buffer lengths
        oob_resp = orchestrator.handle(
            HotpathComputeRequest(
                schema="rust_or_python_hotpath_compute_request/v1",
                declared_corpus_len=999999,
            )
        )
        self.assertFalse(oob_resp.accepted)
        assert oob_resp.refusal is not None
        self.assertEqual(oob_resp.refusal.code, "ffi_buffer_bounds_violation_refused")

        # Known-wrong control (c): refuse silent result fabrication when force_rust_only_no_fallback=True
        no_bin_resp = orchestrator.handle(
            HotpathComputeRequest(
                schema="rust_or_python_hotpath_compute_request/v1",
                simulate_native_binary_unavailable=True,
                force_rust_only_no_fallback=True,
            )
        )
        self.assertFalse(no_bin_resp.accepted)
        assert no_bin_resp.refusal is not None
        self.assertEqual(no_bin_resp.refusal.code, "rust_native_binary_unavailable_refused")

        # Known-wrong control (d): refuse unverified quantile crossing (q_k > q_{k+1})
        crossing_resp = orchestrator.handle(
            HotpathComputeRequest(
                schema="rust_or_python_hotpath_compute_request/v1",
                quantiles_21_bp=(
                    500, 900, 1800, 1200, 2100, 2500, 2900, 3300, 3700, 4100,
                    4500, 4900, 5300, 5700, 6100, 6500, 6900, 7300, 7700, 8100, 8900,
                ),
                refuse_quantile_crossing=True,
            )
        )
        self.assertFalse(crossing_resp.accepted)
        assert crossing_resp.refusal is not None
        self.assertEqual(crossing_resp.refusal.code, "quantile_crossing_monotonicity_violation_refused")

        # Carrier validation controls
        bad_carrier = orchestrator.handle(HotpathComputeRequest(schema="wrong_schema/v0"))
        self.assertFalse(bad_carrier.accepted)
        assert bad_carrier.refusal is not None
        self.assertEqual(bad_carrier.refusal.code, "invalid_hotpath_carrier")

        bad_ctrl_carrier = controller.handle(NodeHotswapControllerRequest(schema="wrong_schema/v0"))
        self.assertFalse(bad_ctrl_carrier.accepted)
        assert bad_ctrl_carrier.refusal is not None
        self.assertEqual(bad_ctrl_carrier.refusal.code, "invalid_hotswap_controller_carrier")

    def test_observed_100k_rust_vs_python_benchmark_suite(self) -> None:
        bench = run_rust_vs_python_hotpath_benchmark(
            hamming_corpus_size=100_000,
            minhash_docs_count=10_000,
            int8_docs_count=10_000,
            int8_dim=32,
        )
        self.assertTrue(bench["k1_hamming_100k"]["bit_exact_parity"])
        self.assertTrue(bench["k2_minhash_lsh_10k"]["bit_exact_parity"])
        self.assertTrue(bench["k3_int8_rerank_10k"]["bit_exact_parity"])
        self.assertGreater(bench["k1_hamming_100k"]["speedup_x"], 2.0)
        self.assertGreater(bench["k2_minhash_lsh_10k"]["speedup_x"], 2.0)
        self.assertGreater(bench["k3_int8_rerank_10k"]["speedup_x"], 2.0)


if __name__ == "__main__":
    unittest.main()
