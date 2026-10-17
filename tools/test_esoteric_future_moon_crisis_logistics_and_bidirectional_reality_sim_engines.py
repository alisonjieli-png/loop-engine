"""Tests and known-wrong controls for the Esoteric, Unseen-Future & Bi-Directional
(Forward-Looking Forecast + Past-Looking Historical Retrodiction) Moon Landing,
Lunar Animation, Food Supply, COVID/Fuel-Shortage Logistics & Alternative-Reality
Simulation Engine Suite.
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

import esoteric_future_moon_crisis_logistics_and_bidirectional_reality_sim_engines as efm  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class EsotericFutureMoonCrisisLogisticsAndBidirectionalRealitySimTests(unittest.TestCase):
    """Verify Slot Family 1 (8 esoteric/crisis/unseen-future domains), Slot Family 2
    (forward & past-looking historical retrodiction simulator), the 24-scenario
    benchmark, and all 4 known-wrong controls.
    """

    def test_slot1_all_8_esoteric_and_crisis_domains_and_swappable_engines(self) -> None:
        solver = efm.EsotericAndCrisisLogisticsSolverSlot()
        self.assertEqual(len(efm.ESOTERIC_PROBLEM_DOMAINS), 8)

        for idx, dom in enumerate(efm.ESOTERIC_PROBLEM_DOMAINS):
            eng = efm.ESOTERIC_SOLVER_ENGINE_ORDER[idx % len(efm.ESOTERIC_SOLVER_ENGINE_ORDER)]
            res = solver.synthesize_esoteric_component_pack(
                dom.domain_id,
                request_id=f"test_dom_{idx}",
                preferred_engine=eng,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, eng)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

            self.assertTrue(res.output["contract_card_within_2048_bytes"])
            self.assertLessEqual(int(res.output["contract_card_bytes"]), 2048)
            self.assertTrue(res.output["nested_sim_verified"])

            files = res.output["files"]
            verifier_name = str(res.output["verifier_filename"])
            self.assertIn(verifier_name, files)
            self.assertIn("AGENTS.md", files)
            self.assertIn("RULES.md", files)
            self.assertIn("MEMORY.md", files)
            self.assertIn("baltor_contract_card.json", files)

            card = json.loads(files["baltor_contract_card.json"])
            self.assertEqual(card["domain_id"], dom.domain_id)

            # Execute generated verifier in an isolated namespace
            ns: dict[str, object] = {}
            exec(files[verifier_name], ns)  # noqa: S102
            verify_fn = ns["verify_esoteric_domain_plan"]
            self.assertTrue(
                callable(verify_fn)
                and verify_fn(
                    {
                        "domain_id": dom.domain_id,
                        "conservation_laws_satisfied": True,
                        "gravity_m_s2": 1.625,
                        "rayleigh_sky_scatter": 0.0,
                        "minimum_inventory_units": 50.0,
                    }
                )
            )
            self.assertFalse(
                callable(verify_fn)
                and verify_fn(
                    {
                        "domain_id": dom.domain_id,
                        "conservation_laws_satisfied": True,
                        "gravity_m_s2": 9.81,
                        "rayleigh_sky_scatter": 0.4,
                        "minimum_inventory_units": -5.0,
                    }
                )
            )

    def test_lunar_powered_descent_and_3d_animation_physics_evaluators(self) -> None:
        descent = efm.evaluate_lunar_powered_descent()
        self.assertTrue(descent["physics_compliant"])
        self.assertEqual(descent["gravity_m_s2"], 1.625)
        self.assertGreaterEqual(descent["available_delta_v_m_s"], descent["required_delta_v_m_s"])
        self.assertGreaterEqual(descent["fuel_remaining_kg"], descent["min_reserve_kg"])

        bad_descent = efm.evaluate_lunar_powered_descent(gravity_m_s2=9.81, touchdown_vz_m_s=-4.5)
        self.assertFalse(bad_descent["physics_compliant"])

        anim = efm.evaluate_lunar_3d_animation_physics()
        self.assertTrue(anim["physics_compliant"])
        self.assertEqual(anim["sky_dome_color"], "pitch_black_000000")
        self.assertAlmostEqual(anim["froude_velocity_scale"], 0.4071, places=3)

        bad_anim = efm.evaluate_lunar_3d_animation_physics(rayleigh_sky_scatter=0.35, atmospheric_drag_coeff=0.2)
        self.assertFalse(bad_anim["physics_compliant"])

    def test_slot2_bidirectional_forward_and_past_historical_retrodiction_simulations(self) -> None:
        sim = efm.BidirectionalForwardAndPastRealitySimulatorSlot()
        self.assertEqual(len(efm.HISTORICAL_RETRODICTION_SCENARIOS), 5)
        self.assertEqual(len(efm.FORWARD_HORIZON_SCENARIOS), 5)

        for idx, hist in enumerate(efm.HISTORICAL_RETRODICTION_SCENARIOS):
            eng = efm.BIDIRECTIONAL_SIM_ENGINE_ORDER[idx % len(efm.BIDIRECTIONAL_SIM_ENGINE_ORDER)]
            res = sim.run_simulation(
                temporal_direction="past",
                scenario_id=hist.scenario_id,
                request_id=f"test_hist_{idx}",
                preferred_engine=eng,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, eng)
            self.assertEqual(res.output["temporal_direction"], "past_looking_retrodiction")
            self.assertTrue(res.output["causal_non_anachronism_verified"])
            self.assertFalse(res.output["future_leakage_detected"])
            self.assertLess(res.output["baltor_counterfactual_loss"], res.output["actual_historical_loss"])
            self.assertGreater(res.output["relative_loss_reduction_pct"], 70.0)

        for idx, (fwd_id, _title, months, _dom_ref) in enumerate(efm.FORWARD_HORIZON_SCENARIOS):
            res = sim.run_simulation(
                temporal_direction="forward",
                scenario_id=fwd_id,
                horizon_months=months,
                request_id=f"test_fwd_{idx}",
                preferred_engine=efm.ENGINE_FORWARD_PROSPECTIVE_REALITY,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.output["temporal_direction"], "forward_looking_forecast")
            self.assertEqual(res.output["baltor_mitigated_stockout_months"], 0)
            self.assertEqual(res.output["double_entry_accounting_gap"], 0.0)
            self.assertGreater(res.output["minimum_projected_inventory_units"], 0.0)

    def test_24_scenario_benchmark_metrics(self) -> None:
        bench = efm.run_esoteric_and_bidirectional_sim_benchmark()
        self.assertEqual(bench["total_scenarios"], 24)
        self.assertEqual(bench["esoteric_domains_count"], 8)
        self.assertEqual(bench["historical_retrodictions_count"], 5)
        self.assertEqual(bench["forward_forecasts_count"], 5)

        base = bench["without_baltor_baseline"]
        self.assertEqual(base["engine_id"], "unconstrained_llm_hallucinated_physics_and_logistics_baseline")
        self.assertEqual(base["conservation_compliant_scenarios"], 7)
        self.assertEqual(base["physical_conservation_compliance_pct"], 29.2)
        self.assertEqual(base["crisis_supply_delivery_completion_pct"], 48.5)
        self.assertEqual(base["lunar_descent_and_animation_physics_accuracy_pct"], 25.0)

        baltor = bench["with_baltor_suite"]
        self.assertEqual(baltor["engine_id"], "baltor_first_principles_esoteric_and_bidirectional_sim_suite")
        self.assertEqual(baltor["conservation_compliant_scenarios"], 24)
        self.assertEqual(baltor["physical_conservation_compliance_pct"], 100.0)
        self.assertEqual(baltor["crisis_supply_delivery_completion_pct"], 97.8)
        self.assertEqual(baltor["fuel_and_cost_waste_reduction_pct"], -64.2)
        self.assertEqual(baltor["lunar_descent_and_animation_physics_accuracy_pct"], 100.0)

    def test_four_known_wrong_controls_refused_in_preflight(self) -> None:
        solver = efm.EsotericAndCrisisLogisticsSolverSlot()
        sim = efm.BidirectionalForwardAndPastRealitySimulatorSlot()

        # Control (a): Refuse lunar descent or animation assuming Earth gravity (9.81 m/s^2) or Rayleigh sky scatter
        bad_lunar = solver.synthesize_esoteric_component_pack(
            "E02_lunar_low_gravity_3d_animation_and_regolith_optics",
            request_id="bad_lunar_physics_01",
            extra_payload={"gravity_m_s2": 9.81, "rayleigh_sky_scatter": 0.45},
        )
        self.assertFalse(bad_lunar.accepted)
        self.assertEqual(bad_lunar.layer_verdicts["preflight"], LAYER_REFUSED)
        self.assertIsNotNone(bad_lunar.refusal)
        assert bad_lunar.refusal is not None
        self.assertEqual(bad_lunar.refusal.code, "lunar_physics_violation_refused")

        # Control (b): Refuse crisis logistics route violating vehicle fuel range or cold-chain spoilage window
        bad_logistics = solver.synthesize_esoteric_component_pack(
            "E03_global_food_supply_cold_chain_and_caloric_reserve_routing",
            request_id="bad_logistics_spoilage_02",
            extra_payload={"route_fuel_required_l": 950.0, "vehicle_fuel_available_l": 600.0, "cold_chain_transit_hours": 96.0},
        )
        self.assertFalse(bad_logistics.accepted)
        self.assertEqual(bad_logistics.layer_verdicts["preflight"], LAYER_REFUSED)
        self.assertIsNotNone(bad_logistics.refusal)
        assert bad_logistics.refusal is not None
        self.assertEqual(bad_logistics.refusal.code, "conservation_or_spoilage_violation_refused")

        # Control (c): Refuse past-looking historical retrodiction with anachronistic post-t future leakage
        bad_retro = sim.run_simulation(
            temporal_direction="past",
            scenario_id="HIST_2020_COVID_GLOBAL_SUPPLY_AND_PPE_SHOCK",
            request_id="bad_retro_anachronism_03",
            extra_payload={
                "decision_timestamp_day": 15,
                "latest_feature_timestamp_day": 45,
                "leaks_future_post_t_prices_or_events": True,
            },
        )
        self.assertFalse(bad_retro.accepted)
        self.assertEqual(bad_retro.layer_verdicts["preflight"], LAYER_REFUSED)
        self.assertIsNotNone(bad_retro.refusal)
        assert bad_retro.refusal is not None
        self.assertEqual(bad_retro.refusal.code, "retrodiction_anachronism_leakage_refused")

        # Control (d): Refuse negative inventory or violated balance-sheet identities in alternative-reality runs
        bad_accounting = sim.run_simulation(
            temporal_direction="forward",
            scenario_id="FWD_01_global_semiconductor_and_neon_supply_shock_t_plus_18m",
            request_id="bad_accounting_identity_04",
            extra_payload={
                "minimum_projected_inventory_units": -42.0,
                "assets_minus_liabilities_and_equity_gap": 12500.0,
            },
        )
        self.assertFalse(bad_accounting.accepted)
        self.assertEqual(bad_accounting.layer_verdicts["preflight"], LAYER_REFUSED)
        self.assertIsNotNone(bad_accounting.refusal)
        assert bad_accounting.refusal is not None
        self.assertEqual(bad_accounting.refusal.code, "negative_inventory_or_accounting_identity_refused")


if __name__ == "__main__":
    unittest.main()
