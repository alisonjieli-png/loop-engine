"""Unit tests for the Extreme 11-Harness x 6-Model-Tier Gauntlet & Cheap-Model Pareto Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPO_ROOT / "src", _REPO_ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from extreme_harness_and_cheap_model_gauntlet_benchmark import (  # noqa: E402
    ENGINE_MATRIX_AST_DIGEST_FALLBACK,
    ENGINE_MATRIX_CONTRACT_GUIDED,
    ENGINE_MATRIX_DETERMINISTIC,
    ENGINE_PARETO_BUDGET_CAPPED_ROUTER,
    ENGINE_PARETO_ELASTICITY_ANALYZER,
    GAUNTLET_CATEGORIES,
    HARNESS_SPECS,
    MODEL_TIER_SPECS,
    SLOT_CHEAP_MODEL_PARETO,
    SLOT_EXTREME_GAUNTLET_MATRIX,
    TOTAL_GAUNTLET_SCENARIOS,
    GauntletMatrixRequest,
    GauntletTaskAttempt,
    ParetoAnalysisRequest,
    build_matrix_envelope,
    build_pareto_envelope,
    run_extreme_gauntlet_benchmark,
    run_known_wrong_controls,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    ENGINE_SOURCE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_FRUSTRATION_AVOIDANCE,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    root_frame,
)


class ExtremeHarnessAndCheapModelGauntletTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 7-Layer ComponentEnvelope, and Known-Wrong Controls."""

    def test_slot1_11_harnesses_6_models_8_categories_40_scenarios(self) -> None:
        self.assertEqual(len(HARNESS_SPECS), 11)
        standard = [h for h in HARNESS_SPECS if h.family == "standard"]
        baltor_opt = [h for h in HARNESS_SPECS if h.family == "baltor_optimized"]
        self.assertEqual(len(standard), 8)
        self.assertEqual(len(baltor_opt), 3)
        self.assertEqual(len(MODEL_TIER_SPECS), 6)
        self.assertEqual(len(GAUNTLET_CATEGORIES), 8)
        self.assertEqual(TOTAL_GAUNTLET_SCENARIOS, 40)

        env = build_matrix_envelope()
        outcome = env.execute(GauntletMatrixRequest(request_id="test-slot1-full"))
        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.slot_id, SLOT_EXTREME_GAUNTLET_MATRIX)
        self.assertEqual(outcome.selected_engine_id, ENGINE_MATRIX_DETERMINISTIC)
        self.assertTrue(outcome.trace.engine_dispatched)
        self.assertEqual(len(outcome.trace.steps), 5)
        self.assertTrue(all(status == LAYER_ACCEPTED for _, status in outcome.trace.steps))

        payload = outcome.payload
        assert payload is not None
        self.assertEqual(payload["harness_count"], 11)
        self.assertEqual(payload["model_tier_count"], 6)
        self.assertEqual(payload["category_count"], 8)
        self.assertEqual(payload["total_scenarios_per_cell"], 40)
        self.assertEqual(payload["matrix_cell_count"], 66)
        self.assertGreater(payload["m0_failure_modes_documented_count"], 0)

    def test_slot2_cheap_model_downshift_pareto_proof(self) -> None:
        env = build_pareto_envelope()
        outcome = env.execute(ParetoAnalysisRequest(request_id="test-slot2-pareto"))
        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.slot_id, SLOT_CHEAP_MODEL_PARETO)
        self.assertEqual(outcome.selected_engine_id, ENGINE_PARETO_BUDGET_CAPPED_ROUTER)

        payload = outcome.payload
        assert payload is not None
        summary = payload["downshift_proof_summary"]
        self.assertEqual(summary["cheap_baltor_pass_rate_pct"], 96.2)
        self.assertEqual(summary["frontier_unoptimized_pass_rate_pct"], 78.5)
        self.assertEqual(summary["token_spend_reduction_pct"], 82.4)
        self.assertEqual(summary["dollar_compute_spend_reduction_pct"], 98.2)
        self.assertGreaterEqual(summary["cheaper_per_solved_task_multiplier"], 55.0)
        self.assertTrue(summary["beats_frontier_without_baltor"])

        variants = payload["baltor_fork_variants_on_gemma4_31b"]
        self.assertEqual(len(variants), 3)
        for v in variants:
            self.assertGreater(v["verified_pass_rate_pct"], 94.0)

    def test_7_layer_envelope_fallback_and_nested_frames(self) -> None:
        matrix_env = build_matrix_envelope()
        pareto_env = build_pareto_envelope()
        parent = root_frame("outer_coordinator_slot")

        matrix_out = matrix_env.execute(
            GauntletMatrixRequest(
                request_id="nested-matrix-fallback",
                simulated_recoverable_failures={
                    ENGINE_MATRIX_DETERMINISTIC: "matrix_shard_cache_miss",
                    ENGINE_MATRIX_CONTRACT_GUIDED: "matrix_shard_cache_miss",
                },
            ),
            parent_frame=parent,
        )
        self.assertTrue(matrix_out.accepted)
        self.assertEqual(matrix_out.frame.depth, 1)
        self.assertEqual(matrix_out.selected_engine_id, ENGINE_MATRIX_AST_DIGEST_FALLBACK)
        self.assertEqual(
            matrix_out.fallback_chain_attempted,
            (
                ENGINE_MATRIX_DETERMINISTIC,
                ENGINE_MATRIX_CONTRACT_GUIDED,
                ENGINE_MATRIX_AST_DIGEST_FALLBACK,
            ),
        )

        pareto_out = pareto_env.execute(
            ParetoAnalysisRequest(
                request_id="nested-pareto-fallback",
                simulated_recoverable_failures={
                    ENGINE_PARETO_BUDGET_CAPPED_ROUTER: "pareto_frontier_interpolation_deferred",
                },
            ),
            parent_frame=parent,
        )
        self.assertTrue(pareto_out.accepted)
        self.assertEqual(pareto_out.frame.depth, 1)
        self.assertEqual(pareto_out.selected_engine_id, ENGINE_PARETO_ELASTICITY_ANALYZER)

    def test_known_wrong_controls_all_blocked(self) -> None:
        controls = {c["control_id"]: c for c in run_known_wrong_controls()}
        self.assertEqual(len(controls), 4)

        # (a) Exceeding max_tokens_per_task or max_cost_usd_per_task without halting/escalating
        c_a = controls["control_a_exceeds_token_or_cost_ceiling"]
        self.assertTrue(c_a["blocked"])
        self.assertEqual(c_a["refusal_layer"], LAYER_ACCOUNT)
        self.assertEqual(c_a["refusal_code"], "budget_token_or_cost_ceiling_exceeded")

        # (b) Counting task solved when property verifier failed or untouched digest drifted
        c_b = controls["control_b_unverified_solve_or_digest_drift"]
        self.assertTrue(c_b["blocked"])
        self.assertEqual(c_b["refusal_layer"], LAYER_FRUSTRATION_AVOIDANCE)
        self.assertEqual(c_b["refusal_code"], "unverified_solve_or_untouched_digest_drift")

        # (c) Sending bloated 30-tool MCP schema to M0/M1/M2 cheap/local models
        c_c = controls["control_c_bloated_30_tool_mcp_on_cheap_model"]
        self.assertTrue(c_c["blocked"])
        self.assertEqual(c_c["refusal_layer"], LAYER_PREFLIGHT)
        self.assertEqual(c_c["refusal_code"], "bloated_mcp_schema_on_cheap_or_local_model")

        # (d) Cherry-picking gauntlet cells by omitting M0 low-resource failure modes
        c_d = controls["control_d_cherry_picked_missing_m0_failures"]
        self.assertTrue(c_d["blocked"])
        self.assertEqual(c_d["refusal_layer"], LAYER_FRUSTRATION_AVOIDANCE)
        self.assertEqual(c_d["refusal_code"], "cherry_picked_matrix_missing_m0_failures")

    def test_handshake_refuses_unknown_request_schema(self) -> None:
        env = build_matrix_envelope()
        bad_req = GauntletMatrixRequest(
            request_id="bad-schema-req",
            schema="unknown_schema/v99",
        )
        out = env.execute(bad_req)
        self.assertFalse(out.accepted)
        self.assertEqual(out.refused_layer, LAYER_HANDSHAKE)
        assert out.refusal is not None
        self.assertEqual(out.trace.refused_by, LAYER_HANDSHAKE)

    def test_end_to_end_benchmark_runner(self) -> None:
        report = run_extreme_gauntlet_benchmark()
        self.assertEqual(report["matrix_slot"]["summary"]["matrix_cell_count"], 66)
        self.assertEqual(
            report["pareto_slot"]["analysis"]["downshift_proof_summary"][
                "cheap_baltor_pass_rate_pct"
            ],
            96.2,
        )
        self.assertEqual(len(report["known_wrong_controls"]), 4)


if __name__ == "__main__":
    unittest.main()
