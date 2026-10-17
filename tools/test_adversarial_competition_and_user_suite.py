"""Tests for tools/adversarial_competition_and_user_suite.py.

Verifies the 24-scenario adversarial competition, GitHub supply-chain,
multi-surface strange-user, and public-good/creative safety suite across
four swappable defense engines wrapped in the 7-layer ComponentEnvelope,
plus 18 known-wrong guard controls.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import adversarial_competition_and_user_suite as suite  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    EnvelopeRefusal,
    EnvelopeTrace,
)


class AdversarialCompetitionAndUserSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = suite.run_full_suite()
        cls.by_id = {spec.scenario_id: spec for spec in suite.SCENARIO_SPECS}

    def test_twenty_four_scenarios_cover_four_surfaces_and_all_seven_envelope_layers(self):
        self.assertEqual(len(suite.SCENARIO_SPECS), 24)
        kaggle_ids = [s.scenario_id for s in suite.SCENARIO_SPECS if s.surface == suite.SURFACE_KAGGLE]
        github_ids = [s.scenario_id for s in suite.SCENARIO_SPECS if s.surface == suite.SURFACE_GITHUB]
        user_ids = [s.scenario_id for s in suite.SCENARIO_SPECS if s.surface == suite.SURFACE_USER]
        domain_ids = [s.scenario_id for s in suite.SCENARIO_SPECS if s.surface == suite.SURFACE_DOMAIN]
        self.assertEqual(kaggle_ids, [f"A-KAGGLE-0{i}" for i in range(1, 7)])
        self.assertEqual(github_ids, [f"A-GITHUB-0{i}" for i in range(1, 7)])
        self.assertEqual(user_ids, [f"A-USER-0{i}" for i in range(1, 7)])
        self.assertEqual(domain_ids, [f"A-DOMAIN-0{i}" for i in range(1, 7)])
        primary_layers = {s.primary_layer for s in suite.SCENARIO_SPECS}
        self.assertEqual(primary_layers, set(COVERAGE_LAYERS))

    def test_strict_zero_trust_blocker_catches_non_ast_attacks_and_refuses_repairables(self):
        bench = self.report["benchmarks"][suite.ENGINE_STRICT_ZERO_TRUST]
        self.assertEqual(bench["attacks_blocked"], 14)
        self.assertEqual(bench["repairs_succeeded"], 0)
        self.assertEqual(bench["false_positives"], 6)
        self.assertEqual(bench["total_passed"], 14)

    def test_ast_and_dataflow_leakage_auditor_blocks_all_eighteen_attacks(self):
        bench = self.report["benchmarks"][suite.ENGINE_AST_DATAFLOW]
        self.assertEqual(bench["attacks_blocked"], 18)
        self.assertEqual(bench["attack_block_rate"], 1.0)
        self.assertEqual(bench["repairs_succeeded"], 0)
        self.assertEqual(bench["false_positives"], 6)
        self.assertEqual(bench["total_passed"], 18)
        by_scen = {r["scenario_id"]: r for r in bench["results"]}
        for ast_id in ("A-KAGGLE-01", "A-KAGGLE-02", "A-KAGGLE-04", "A-GITHUB-01"):
            self.assertTrue(by_scen[ast_id]["passed_expectation"], ast_id)
            self.assertEqual(by_scen[ast_id]["outcome"], suite.OUTCOME_BLOCKED)

    def test_tolerant_self_repair_normalizer_repairs_all_six_strange_and_creative_scenarios(self):
        bench = self.report["benchmarks"][suite.ENGINE_TOLERANT_SELF_REPAIR]
        self.assertEqual(bench["attacks_blocked"], 14)
        self.assertEqual(bench["repairs_succeeded"], 6)
        self.assertEqual(bench["repair_rate"], 1.0)
        self.assertEqual(bench["false_positives"], 0)
        self.assertEqual(bench["false_positive_rate"], 0.0)
        self.assertEqual(bench["total_passed"], 20)

    def test_cascade_7layer_competition_guard_passes_all_24_scenarios_with_zero_false_positives(self):
        self.assertTrue(self.report["passed"])
        bench = self.report["benchmarks"][suite.ENGINE_CASCADE_7LAYER]
        self.assertEqual(bench["total_passed"], 24)
        self.assertEqual(bench["attacks_blocked"], 18)
        self.assertEqual(bench["attack_block_rate"], 1.0)
        self.assertEqual(bench["repairs_succeeded"], 6)
        self.assertEqual(bench["repair_rate"], 1.0)
        self.assertEqual(bench["false_positives"], 0)
        self.assertEqual(bench["false_positive_rate"], 0.0)

    def test_cascade_stops_at_first_stage_for_attacks_and_falls_back_for_repairable_defects(self):
        bench = self.report["benchmarks"][suite.ENGINE_CASCADE_7LAYER]
        for row in bench["results"]:
            if row["disposition"] == suite.DISPOSITION_ATTACK:
                self.assertEqual(
                    row["fallback_chain_used"],
                    [suite.ENGINE_AST_DATAFLOW],
                    f"Attack {row['scenario_id']} must be blocked immediately without fallback",
                )
            else:
                self.assertEqual(
                    row["fallback_chain_used"],
                    [suite.ENGINE_AST_DATAFLOW, suite.ENGINE_TOLERANT_SELF_REPAIR],
                    f"Repairable scenario {row['scenario_id']} must cascade to tolerant self-repair",
                )

    def test_16_thread_fair_queue_lock_fifo_order_and_zero_starvation(self):
        res = suite.evaluate_scenario(self.by_id["A-USER-01"], suite.ENGINE_CASCADE_7LAYER)
        self.assertTrue(res.passed_expectation)
        self.assertEqual(res.code, "fair_queue_fifo_16_thread_burst_verified")
        metrics = res.repaired_metrics
        self.assertEqual(metrics["threads_serialized"], 16)
        self.assertEqual(list(metrics["fifo_order"]), list(range(16)))
        self.assertEqual(metrics["starved_threads"], 0)

    def test_strange_user_mcp_header_and_120_line_traceback_repairs(self):
        res_hdr = suite.evaluate_scenario(self.by_id["A-USER-04"], suite.ENGINE_CASCADE_7LAYER)
        self.assertTrue(res_hdr.passed_expectation)
        self.assertEqual(res_hdr.repaired_metrics["normalized_auth_header"], "Bearer baltor_tok_77")
        self.assertEqual(res_hdr.repaired_metrics["normalized_query"], "kaggle timeseries rolling lag")

        res_tb = suite.evaluate_scenario(self.by_id["A-USER-05"], suite.ENGINE_CASCADE_7LAYER)
        self.assertTrue(res_tb.passed_expectation)
        self.assertGreaterEqual(res_tb.repaired_metrics["original_line_count"], 120)
        self.assertEqual(res_tb.repaired_metrics["distilled_query"], "kaggle timeseries rolling lag")
        self.assertEqual(res_tb.repaired_metrics["word_count"], 4)
        self.assertEqual(res_tb.matched_component_id, "kaggle_timeseries_lag_featurizer_v1")

    def test_domain_safety_wbgt_physics_and_creative_media_preflight_repairs(self):
        # NIOSH WBGT physics check at 36C and 85% RH
        true_wbgt = suite._compute_stull_wbgt_c(36.0, 85.0)
        self.assertGreater(true_wbgt, 33.5)
        res_wbgt = suite.evaluate_scenario(self.by_id["A-DOMAIN-01"], suite.ENGINE_CASCADE_7LAYER)
        self.assertTrue(res_wbgt.passed_expectation)
        self.assertEqual(res_wbgt.code, "unsafe_wbgt_heat_stress_underestimation_refused")

        # Vertical video keep-out repair (1080x1920, right 160px, bottom 420px)
        res_vid = suite.evaluate_scenario(self.by_id["A-DOMAIN-03"], suite.ENGINE_CASCADE_7LAYER)
        self.assertTrue(res_vid.passed_expectation)
        self.assertTrue(res_vid.repaired_metrics["right_margin_ok"])
        self.assertTrue(res_vid.repaired_metrics["bottom_margin_ok"])

        # WCAG AAA contrast repair (>= 7.0:1)
        initial_ratio = suite._wcag_contrast_ratio("#c0392b", "#8a2820")
        self.assertAlmostEqual(initial_ratio, 1.65, places=1)
        res_wcag = suite.evaluate_scenario(self.by_id["A-DOMAIN-04"], suite.ENGINE_CASCADE_7LAYER)
        self.assertTrue(res_wcag.passed_expectation)
        self.assertGreaterEqual(res_wcag.repaired_metrics["repaired_contrast_ratio"], 7.0)

        # Procedural Karplus-Strong audio DC offset and peak limiter repair
        res_aud = suite.evaluate_scenario(self.by_id["A-DOMAIN-05"], suite.ENGINE_CASCADE_7LAYER)
        self.assertTrue(res_aud.passed_expectation)
        self.assertAlmostEqual(res_aud.repaired_metrics["dc_offset_after"], 0.0, places=5)
        self.assertLessEqual(res_aud.repaired_metrics["peak_linear_after"], 0.90)
        self.assertLessEqual(res_aud.repaired_metrics["peak_dbfs_after"], -0.95)

    def test_every_trace_and_refusal_satisfies_envelope_contracts(self):
        for engine in suite.DEFENSE_ENGINES:
            for spec in suite.SCENARIO_SPECS:
                res = suite.evaluate_scenario(spec, engine)
                self.assertIsInstance(res.trace, EnvelopeTrace)
                self.assertEqual(res.trace.to_dict()["record_type"], "envelope_trace/v1")
                if res.refusal is not None:
                    self.assertIsInstance(res.refusal, EnvelopeRefusal)
                    rebuilt = EnvelopeRefusal.from_dict(res.refusal.to_dict())
                    self.assertEqual(rebuilt, res.refusal)

    def test_all_eighteen_known_wrong_controls_detect_removed_guards(self):
        controls = self.report["known_wrong_controls"]
        self.assertEqual(len(controls), 18)
        for item in controls:
            self.assertTrue(
                item["known_wrong_detected"],
                f"Known-wrong control {item['control']} failed to detect guard removal: {item}",
            )
            self.assertTrue(item["malicious_leaked_when_removed"])


if __name__ == "__main__":
    unittest.main()
