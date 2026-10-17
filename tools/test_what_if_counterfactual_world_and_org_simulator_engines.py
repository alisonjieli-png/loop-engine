"""Tests and known-wrong controls for the Counterfactual "What-If" World,
Management Personality, Budget/Hardware Constraint, and Organizational Volatility
Simulator -> Adaptive Harness Component Generator Suite.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

import what_if_counterfactual_world_and_org_simulator_engines as what_if  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class WhatIfCounterfactualWorldAndOrgSimulatorTests(unittest.TestCase):
    """Verify the 57,600-world simulator, adaptive harness synthesizer, 32-scenario benchmark, and 4 known-wrong controls."""

    def test_four_orthogonal_dimensions_span_57600_counterfactual_worlds(self) -> None:
        space = what_if.enumerate_counterfactual_space_summary()
        self.assertEqual(space["management_personalities_count"], 16)
        self.assertEqual(space["world_shocks_count"], 15)
        self.assertEqual(space["budget_latency_envelopes_count"], 12)
        self.assertEqual(space["industry_substrates_count"], 20)
        self.assertEqual(space["total_counterfactual_worlds"], 57600)
        self.assertEqual(space["evidence_category"], what_if.EVIDENCE_CATEGORY_COUNTERFACTUAL)

        # Verify first and last world indices in [0, 57599]
        first_idx = what_if.compute_world_index(
            what_if.MANAGEMENT_PERSONALITIES[0].personality_id,
            what_if.COUNTERFACTUAL_WORLD_SHOCKS[0].shock_id,
            what_if.BUDGET_AND_LATENCY_ENVELOPES[0].envelope_id,
            what_if.INDUSTRY_SUBSTRATES[0].industry_id,
        )
        last_idx = what_if.compute_world_index(
            what_if.MANAGEMENT_PERSONALITIES[-1].personality_id,
            what_if.COUNTERFACTUAL_WORLD_SHOCKS[-1].shock_id,
            what_if.BUDGET_AND_LATENCY_ENVELOPES[-1].envelope_id,
            what_if.INDUSTRY_SUBSTRATES[-1].industry_id,
        )
        self.assertEqual(first_idx, 0)
        self.assertEqual(last_idx, 57599)

    def test_slot1_counterfactual_simulator_across_all_four_swappable_engines(self) -> None:
        slot = what_if.WhatIfCounterfactualAndOrgSimulatorSlot()
        for idx, engine_id in enumerate(what_if.SIMULATOR_ENGINE_ORDER):
            res = slot.simulate_world(
                "zero_questions_autonomous_execution_founder",
                "external_cloud_api_blackout_72hr",
                "usd_0_00_day_offline_10ms_edge_interactive",
                "autonomous_coding_harness_foundry",
                request_id=f"test_sim_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertFalse(res.output["cloud_frontier_permitted"])
            self.assertEqual(res.output["evidence_category"], what_if.EVIDENCE_CATEGORY_COUNTERFACTUAL)
            self.assertGreaterEqual(float(res.output["resilience_score"]), 0.98)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

    def test_slot2_adaptive_harness_component_synthesizer_and_generated_verifier(self) -> None:
        synth = what_if.CounterfactualToHarnessComponentSynthesizerSlot()
        for idx, engine_id in enumerate(what_if.SYNTHESIZER_ENGINE_ORDER):
            res = synth.synthesize_adaptation_pack(
                "paranoid_zero_trust_ciso",
                "edge_box_2gb_ram_cpu_only_constraint",
                "usd_0_05_day_micro_50ms_interactive",
                "cybersecurity_soc_and_threat_hunting",
                request_id=f"test_synth_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            files = res.output["files"]
            self.assertIn("AGENTS.md", files)
            self.assertIn("RULES.md", files)
            self.assertIn("MEMORY.md", files)
            self.assertIn("baltor_contract_card.json", files)
            self.assertIn("verify_counterfactual_compliance.py", files)
            self.assertLessEqual(int(res.output["contract_card_bytes"]), 2048)
            self.assertTrue(res.output["contract_card_within_2048_bytes"])

            card = json.loads(files["baltor_contract_card.json"])
            self.assertEqual(card["personality_id"], "paranoid_zero_trust_ciso")
            self.assertEqual(card["effective_ram_mb"], 2048)
            self.assertFalse(card["cloud_frontier_permitted"])

            # Execute generated verify_counterfactual_compliance.py in an isolated namespace
            ns: dict[str, object] = {}
            exec(files["verify_counterfactual_compliance.py"], ns)  # noqa: S102
            verify_fn = ns["verify_compliance"]
            self.assertTrue(
                callable(verify_fn)
                and verify_fn(
                    {
                        "evidence_category": "counterfactual_simulation",
                        "spend_usd": 0.02,
                        "peak_ram_mb": 1400,
                        "used_cloud_llm": False,
                        "asked_questions": False,
                    }
                )
            )
            self.assertFalse(
                callable(verify_fn)
                and verify_fn(
                    {
                        "evidence_category": "observed",
                        "spend_usd": 0.02,
                        "peak_ram_mb": 1400,
                        "used_cloud_llm": False,
                    }
                )
            )

    def test_32_scenario_benchmark_achieves_100_percent_survival_vs_25_percent_rigid_baseline(self) -> None:
        bench = what_if.run_what_if_counterfactual_benchmark()
        self.assertEqual(bench["total_benchmark_scenarios"], 32)

        without_b = bench["without_baltor_baseline"]
        self.assertEqual(without_b["engine_id"], what_if.ENGINE_RIGID_UNADAPTED_BASELINE)
        self.assertEqual(without_b["scenarios_survived"], 8)
        self.assertAlmostEqual(float(without_b["survival_rate"]), 0.25)
        self.assertEqual(without_b["survival_rate_pct"], "25.0%")
        self.assertGreater(int(without_b["budget_or_memory_overruns"]), 0)
        self.assertGreater(int(without_b["management_style_rejections"]), 0)

        with_b = bench["with_baltor_adaptive_harness"]
        self.assertEqual(with_b["engine_id"], what_if.ENGINE_BALTOR_ADAPTIVE_HARNESS)
        self.assertEqual(with_b["scenarios_survived"], 32)
        self.assertAlmostEqual(float(with_b["survival_rate"]), 1.0)
        self.assertEqual(with_b["survival_rate_pct"], "100.0%")
        self.assertEqual(with_b["budget_or_memory_overruns"], 0)
        self.assertEqual(with_b["management_style_rejections"], 0)
        self.assertTrue(with_b["all_cards_within_2048_bytes"])
        self.assertLessEqual(int(with_b["max_contract_card_bytes"]), 2048)

    def test_four_known_wrong_controls_refuse_before_engine_dispatch(self) -> None:
        kw = what_if.run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"], msg=f"Failed control: {ctrl}")
            self.assertTrue(ctrl["refused_before_engine"])

        # Direct verification of each refusal code and layer verdict
        sim = what_if.WhatIfCounterfactualAndOrgSimulatorSlot()
        res_a = sim.simulate_world(
            "zero_questions_autonomous_execution_founder",
            "mandatory_48hr_product_vertical_pivot",
            "usd_50_00_mo_pilot_5s_guarded_ops",
            "autonomous_coding_harness_foundry",
            request_id="direct_kw_a",
            extra_payload={"asks_clarifying_questions": True},
        )
        self.assertFalse(res_a.accepted)
        self.assertIsNotNone(res_a.refusal)
        self.assertEqual(res_a.refusal.code, "founder_clarifying_questions_refused")
        self.assertEqual(res_a.layer_verdicts["preflight"], LAYER_REFUSED)


if __name__ == "__main__":
    unittest.main()
