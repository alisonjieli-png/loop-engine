"""Tests for Continuously Variable N-Scale Layering (N in [0.0, 10.0]) and
6-Operator Logjam Recovery, Breakout & Anti-Convergence Engine Suite.
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

from continuous_n_scale_hierarchy_and_logjam_anti_convergence_engines import (  # noqa: E402
    BALTOR_CONTINUOUS_N_SCALE_AND_6_OPERATOR_SUITE,
    BASELINE_FIXED_5_LABEL_NAIVE_RETRY,
    CONTINUOUS_N_SCALE_ENGINE_ORDER,
    ENGINE_ASSUMPTION_INVERSION_CONSTRAINT_RELAXATION,
    ENGINE_CAUSAL_BISECTION_FAULT_ISOLATOR,
    ENGINE_CONTINUOUS_N_SCALE_COORDINATE_RESOLVER,
    ENGINE_CONTINUOUS_N_SCALE_ZOOM_BREAKOUT,
    ENGINE_FRACTIONAL_INTERSTITIAL_LAYER_SPLICER,
    ENGINE_ORTHOGONAL_ONTOLOGY_ROTATION_BREAKOUT,
    ENGINE_PRIME_DIRECTIVE_Q0_TO_Q10_ESCALATION,
    ENGINE_QUALITY_DIVERSITY_MAP_ELITES_ANTI_CONVERGENCE,
    LEGACY_5_LABEL_TO_CONTINUOUS_N,
    LOGJAM_BREAKOUT_ENGINE_ORDER,
    N_SCALE_INTEGER_ANCHORS,
    PRIME_DIRECTIVE_Q0_TO_Q10_QUESTIONS,
    SLOT_CONTINUOUS_N_SCALE_RESOLUTION,
    SLOT_LOGJAM_BREAKOUT_AND_ANTI_CONVERGENCE,
    STAGNATION_LOCAL_OPTIMUM_TRAP,
    STAGNATION_LOGJAM_STALL,
    STAGNATION_REDUNDANT_CONVERGENCE_COLLAPSE,
    ContinuousNScaleResolutionSlotEngine,
    EnvelopeInvocationRequest,
    LogjamBreakoutAndAntiConvergenceSlotEngine,
    detect_stagnation_state,
    execute_six_operator_breakout,
    resolve_continuous_n_scale_layer,
    run_continuous_n_scale_and_logjam_benchmark,
    subdivide_n_scale_interval,
    synthesize_interstitial_layer,
)
from loop_engine.core.engines.envelope import COVERAGE_LAYERS  # noqa: E402


class ContinuousNScaleAndLogjamBreakoutTests(unittest.TestCase):
    def test_eleven_integer_anchors_and_fractional_interstitial_resolution(self) -> None:
        self.assertEqual(len(N_SCALE_INTEGER_ANCHORS), 11)
        for anchor_n, slug, _, _ in N_SCALE_INTEGER_ANCHORS:
            desc = resolve_continuous_n_scale_layer(float(anchor_n))
            self.assertEqual(desc.scale_n, float(anchor_n))
            self.assertFalse(desc.is_interstitial_fractional)
            self.assertIn(slug, desc.layer_slug)

        # Fractional interstitial N = 2.50 between function (N=2) and slot envelope (N=3)
        d_250 = resolve_continuous_n_scale_layer(2.50)
        self.assertTrue(d_250.is_interstitial_fractional)
        self.assertEqual(d_250.lower_anchor_n, 2)
        self.assertEqual(d_250.upper_anchor_n, 3)
        self.assertAlmostEqual(d_250.lower_ontology_weight, 0.50)
        self.assertAlmostEqual(d_250.upper_ontology_weight, 0.50)

        # Fractional interstitial N = 6.37 between platform arch (N=6) and company PMF (N=7)
        d_637 = resolve_continuous_n_scale_layer(6.37)
        self.assertTrue(d_637.is_interstitial_fractional)
        self.assertEqual(d_637.lower_anchor_n, 6)
        self.assertEqual(d_637.upper_anchor_n, 7)
        self.assertAlmostEqual(d_637.lower_ontology_weight, 0.63)
        self.assertAlmostEqual(d_637.upper_ontology_weight, 0.37)
        self.assertGreater(d_637.time_horizon_seconds, d_250.time_horizon_seconds)
        self.assertGreater(d_637.context_budget_tokens, d_250.context_budget_tokens)

        # Legacy 5-label compatibility mapping into continuous N
        self.assertEqual(set(LEGACY_5_LABEL_TO_CONTINUOUS_N), {"nano", "micro", "meso", "macro", "super_macro"})

    def test_ultra_fine_fractional_interstitial_splicing_and_subdivision(self) -> None:
        # Splice between N_a = 2.10 and N_b = 2.15 -> N_mid = 2.125
        splice = synthesize_interstitial_layer(2.10, 2.15, alpha=0.50)
        self.assertAlmostEqual(splice.spliced_scale_n, 2.125)
        self.assertTrue(splice.interstitial_descriptor.is_interstitial_fractional)
        self.assertLess(splice.max_substep_gap_after, splice.scale_gap_before)

        sub_layers = subdivide_n_scale_interval(2.10, 2.15, interstitial_count=4)
        self.assertEqual(len(sub_layers), 4)
        coords = [d.scale_n for d in sub_layers]
        self.assertEqual(coords, sorted(coords))
        self.assertTrue(all(2.10 < c < 2.15 for c in coords))

    def test_three_pathological_stagnation_states_and_six_operators(self) -> None:
        self.assertEqual(len(PRIME_DIRECTIVE_Q0_TO_Q10_QUESTIONS), 11)
        self.assertEqual(len(LOGJAM_BREAKOUT_ENGINE_ORDER), 6)

        # 1. logjam_stall
        d_stall = detect_stagnation_state(
            {
                "score_history": (0.61, 0.611, 0.611, 0.611),
                "max_candidate_cosine_similarity": 0.50,
                "edit_revert_oscillation": True,
                "artifact_valid": True,
                "score_valid": True,
            }
        )
        self.assertTrue(d_stall.stagnation_detected)
        self.assertIn(STAGNATION_LOGJAM_STALL, d_stall.triggered_states)
        self.assertEqual(d_stall.recommended_operator, ENGINE_CONTINUOUS_N_SCALE_ZOOM_BREAKOUT)

        # 2. redundant_convergence_collapse
        d_conv = detect_stagnation_state(
            {
                "score_history": (0.40, 0.55, 0.70),
                "max_candidate_cosine_similarity": 0.96,
                "artifact_valid": True,
                "score_valid": True,
            }
        )
        self.assertTrue(d_conv.stagnation_detected)
        self.assertIn(STAGNATION_REDUNDANT_CONVERGENCE_COLLAPSE, d_conv.triggered_states)
        self.assertEqual(
            d_conv.recommended_operator,
            ENGINE_QUALITY_DIVERSITY_MAP_ELITES_ANTI_CONVERGENCE,
        )

        # 3. local_optimum_trap
        d_trap = detect_stagnation_state(
            {
                "score_history": (0.40, 0.55, 0.70),
                "max_candidate_cosine_similarity": 0.40,
                "artifact_valid": True,
                "score_valid": False,
                "local_optimum_holdout_gap": 0.25,
            }
        )
        self.assertTrue(d_trap.stagnation_detected)
        self.assertIn(STAGNATION_LOCAL_OPTIMUM_TRAP, d_trap.triggered_states)
        self.assertEqual(
            d_trap.recommended_operator,
            ENGINE_ASSUMPTION_INVERSION_CONSTRAINT_RELAXATION,
        )

        # Execute full 6-operator pipeline
        for op in (
            ENGINE_CONTINUOUS_N_SCALE_ZOOM_BREAKOUT,
            ENGINE_ORTHOGONAL_ONTOLOGY_ROTATION_BREAKOUT,
            ENGINE_ASSUMPTION_INVERSION_CONSTRAINT_RELAXATION,
            ENGINE_QUALITY_DIVERSITY_MAP_ELITES_ANTI_CONVERGENCE,
            ENGINE_CAUSAL_BISECTION_FAULT_ISOLATOR,
            ENGINE_PRIME_DIRECTIVE_Q0_TO_Q10_ESCALATION,
        ):
            res = execute_six_operator_breakout(
                {
                    "scenario_id": f"test_{op}",
                    "current_scale_n": 2.20,
                    "parent_scale_n": 3.40,
                    "preferred_operator": op,
                }
            )
            self.assertTrue(res.escaped_logjam)
            self.assertEqual(res.selected_operator, op)
            self.assertEqual(len(res.prime_directive_receipt.steps_completed), 11)
            self.assertGreater(res.diversity_entropy_after, res.diversity_entropy_before)

    def test_seven_layer_component_envelope_and_fallback_chains(self) -> None:
        slot1 = ContinuousNScaleResolutionSlotEngine()
        req1 = EnvelopeInvocationRequest(
            slot_id=SLOT_CONTINUOUS_N_SCALE_RESOLUTION,
            request_id="req-slot1-fallback",
            idempotency_key="idem-slot1-fallback",
            account_id="acct-01",
            tier="pro",
            payload={"scale_n": 6.37, "n_a": 2.10, "n_b": 2.15, "alpha": 0.50},
            simulate_unhealthy_engines=(ENGINE_CONTINUOUS_N_SCALE_COORDINATE_RESOLVER,),
        )
        res1 = slot1.invoke(req1)
        self.assertTrue(res1.accepted)
        self.assertEqual(res1.selected_engine, ENGINE_FRACTIONAL_INTERSTITIAL_LAYER_SPLICER)
        self.assertEqual(
            res1.fallback_chain_tried,
            (
                ENGINE_CONTINUOUS_N_SCALE_COORDINATE_RESOLVER,
                ENGINE_FRACTIONAL_INTERSTITIAL_LAYER_SPLICER,
            ),
        )
        for layer in COVERAGE_LAYERS:
            self.assertEqual(res1.layer_verdicts[layer], "full")
        self.assertEqual(len(CONTINUOUS_N_SCALE_ENGINE_ORDER), 4)

    def test_four_known_wrong_preflight_controls(self) -> None:
        slot1 = ContinuousNScaleResolutionSlotEngine()
        slot2 = LogjamBreakoutAndAntiConvergenceSlotEngine()

        # Control (a): Refuse rigid integer-only or 5-label-only scale constraint on fractional N
        bad_a = slot1.invoke(
            EnvelopeInvocationRequest(
                slot_id=SLOT_CONTINUOUS_N_SCALE_RESOLUTION,
                request_id="req-control-a",
                idempotency_key="idem-control-a",
                account_id="acct-01",
                tier="pro",
                payload={
                    "scale_n": 2.50,
                    "enforce_rigid_five_labels_or_integer_only": True,
                },
            )
        )
        self.assertFalse(bad_a.accepted)
        assert bad_a.refusal is not None
        self.assertEqual(
            bad_a.refusal.code,
            "rigid_five_label_or_integer_only_scale_constraint_refused",
        )

        # Control (b): Refuse 4th consecutive identical retry without breakout operator
        bad_b = slot2.invoke(
            EnvelopeInvocationRequest(
                slot_id=SLOT_LOGJAM_BREAKOUT_AND_ANTI_CONVERGENCE,
                request_id="req-control-b",
                idempotency_key="idem-control-b",
                account_id="acct-01",
                tier="pro",
                payload={
                    "consecutive_identical_retries": 4,
                    "breakout_operator_applied": False,
                },
            )
        )
        self.assertFalse(bad_b.accepted)
        assert bad_b.refusal is not None
        self.assertEqual(bad_b.refusal.code, "redundant_convergence_collapse_refused")

        # Control (c): Refuse logjam fix that skips Q0 evidence preservation or Q8 non-regression
        bad_c = slot2.invoke(
            EnvelopeInvocationRequest(
                slot_id=SLOT_LOGJAM_BREAKOUT_AND_ANTI_CONVERGENCE,
                request_id="req-control-c",
                idempotency_key="idem-control-c",
                account_id="acct-01",
                tier="pro",
                payload={
                    "preserve_q0_evidence": False,
                    "verify_q8_non_regression": False,
                },
            )
        )
        self.assertFalse(bad_c.accepted)
        assert bad_c.refusal is not None
        self.assertEqual(bad_c.refusal.code, "prime_directive_q0_or_q8_skipped_refused")

        # Control (d): Refuse scale inversion where child N_child > N_parent without zoom-out receipt
        bad_d = slot1.invoke(
            EnvelopeInvocationRequest(
                slot_id=SLOT_CONTINUOUS_N_SCALE_RESOLUTION,
                request_id="req-control-d",
                idempotency_key="idem-control-d",
                account_id="acct-01",
                tier="pro",
                payload={
                    "scale_n": 3.25,
                    "child_scale_n": 4.80,
                    "parent_scale_n": 3.10,
                    "explicit_zoom_out_breakout_receipt": False,
                },
            )
        )
        self.assertFalse(bad_d.accepted)
        assert bad_d.refusal is not None
        self.assertEqual(bad_d.refusal.code, "unauthorized_n_scale_inversion_refused")

    def test_thirty_scenario_logjam_and_anti_convergence_benchmark(self) -> None:
        report = run_continuous_n_scale_and_logjam_benchmark()
        self.assertEqual(report["scenario_count"], 30)
        self.assertEqual(report["baseline_system"], BASELINE_FIXED_5_LABEL_NAIVE_RETRY)
        self.assertEqual(report["baltor_system"], BALTOR_CONTINUOUS_N_SCALE_AND_6_OPERATOR_SUITE)
        self.assertEqual(report["baseline_logjam_escape_rate_pct"], 16.7)
        self.assertEqual(report["baltor_logjam_escape_rate_pct"], 100.0)
        self.assertEqual(report["baseline_candidate_diversity_entropy"], 0.21)
        self.assertEqual(report["baltor_candidate_diversity_entropy"], 0.94)
        self.assertEqual(report["wasted_retry_tokens_reduction_pct"], -88.5)
        self.assertEqual(report["fractional_interstitial_splice_accuracy_pct"], 100.0)
        self.assertEqual(len(report["scenarios"]), 30)


if __name__ == "__main__":
    unittest.main()
