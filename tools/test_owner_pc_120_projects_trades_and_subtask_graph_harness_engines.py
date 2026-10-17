"""Tests and known-wrong controls for the Owner PC 120-Project Portfolio,
Physical/Digital Trades, and Per-Node Sub-Task Graph Unique-Harness Configurator Suite.
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

import owner_pc_120_projects_trades_and_subtask_graph_harness_engines as op  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class OwnerPc120ProjectsTradesAndSubtaskGraphHarnessTests(unittest.TestCase):
    """Verify the 12 domains (120 packs), 2 slot families, 12-workflow DAG benchmark, and 4 known-wrong controls."""

    def test_12_domains_and_120_owner_pc_project_trade_catalog(self) -> None:
        self.assertEqual(len(op.PORTFOLIO_TRADE_DOMAINS), 12)
        self.assertEqual(len(op.OWNER_PC_120_PROJECT_TRADE_CATALOG), 120)

        expected_domain_ids = (
            "D01_janitorial_and_facilities_sourceloop",
            "D02_welding_and_structural_fabrication",
            "D03_framing_demising_walls_and_building_permits",
            "D04_legal_discovery_preservation_and_touhy",
            "D05_parametric_design_3d_and_creative_studio",
            "D06_affiliate_marketing_and_comparison_sites",
            "D07_growth_engineering_and_bhw_style_automation",
            "D08_skills_state_and_hermes_portability",
            "D09_entity_radar_and_suspicious_network_intel",
            "D10_geospatial_delivery_and_address_verification",
            "D11_quant_trading_and_roll_watch_signals",
            "D12_duecare_and_humanitarian_safety",
        )
        self.assertEqual(tuple(d.domain_id for d in op.PORTFOLIO_TRADE_DOMAINS), expected_domain_ids)
        for dom in op.PORTFOLIO_TRADE_DOMAINS:
            self.assertEqual(len(dom.workflows), 10)

    def test_slot1_owner_pc_projects_and_trades_synthesizer_across_all_engines(self) -> None:
        slot1 = op.OwnerPcProjectsAndTradesComponentSlot()
        for idx, engine_id in enumerate(op.TRADES_SLOT_ENGINE_ORDER):
            res = slot1.synthesize_project_or_trade_pack(
                "D03_W01_tenant_demising_wall_ul_u419_fire_rating_checker",
                request_id=f"test_slot1_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.output["total_catalog_packs"], 120)
            self.assertEqual(res.output["total_catalog_files"], 600)
            self.assertTrue(res.output["contract_card_within_2048_bytes"])
            self.assertLessEqual(int(res.output["contract_card_bytes"]), 2048)

            files = res.output["files"]
            for req_file in ("baltor_contract_card.json", "AGENTS.md", "RULES.md", "MEMORY.md", "verifier.py"):
                self.assertIn(req_file, files)
                self.assertGreater(len(files[req_file]), 40)

            card = json.loads(files["baltor_contract_card.json"])
            self.assertEqual(card["domain_id"], "D03_framing_demising_walls_and_building_permits")
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

    def test_slot2_per_node_unique_harness_dag_configurator_across_all_engines(self) -> None:
        slot2 = op.PerNodeUniqueHarnessDagConfiguratorSlot()
        for idx, engine_id in enumerate(op.DAG_SLOT_ENGINE_ORDER):
            res = slot2.decompose_and_configure_dag(
                "D04_legal_discovery_preservation_and_touhy",
                request_id=f"test_slot2_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.output["node_count"], 6)
            self.assertTrue(res.output["all_nodes_unique_harness"])
            self.assertTrue(res.output["all_slices_within_220_tokens"])
            self.assertTrue(res.output["all_verifiers_separated"])

            nodes = res.output["nodes"]
            levels = {n["hierarchy_level"] for n in nodes}
            self.assertEqual(levels, {"macro_orchestrator", "meso_subtask", "micro_sub_subtask"})
            for node in nodes:
                self.assertLessEqual(int(node["contract_slice_tokens"]), 220)
                self.assertNotEqual(node["worker_profile_id"], node["node_verifier_id"])
                self.assertEqual(node["skills_state_manifest"]["cross_node_context_pollution"], 0)
                self.assertGreaterEqual(len(node["skills_state_manifest"]["pinned_contract_cards"]), 1)
                self.assertLessEqual(len(node["skills_state_manifest"]["pinned_contract_cards"]), 2)

    def test_12_workflow_end_to_end_benchmark_matches_targets(self) -> None:
        bench = op.run_owner_pc_120_and_subtask_dag_benchmark()
        self.assertEqual(bench["total_domains"], 12)
        self.assertEqual(bench["total_portfolio_trade_packs"], 120)
        self.assertEqual(bench["total_harness_component_files"], 600)
        self.assertLessEqual(int(bench["max_contract_card_bytes"]), 2048)
        self.assertEqual(bench["total_end_to_end_workflows"], 12)
        self.assertEqual(bench["total_dag_nodes_evaluated"], 72)

        mono = bench["monolithic_single_harness_agent_without_baltor"]
        self.assertEqual(mono["engine_id"], op.ENGINE_MONOLITHIC_SINGLE_HARNESS_BASELINE)
        self.assertEqual(mono["pass_rate_pct"], "54.2%")
        self.assertEqual(mono["tokens_per_workflow"], 41800)

        baltor = bench["baltor_per_node_unique_harness_dag"]
        self.assertEqual(baltor["engine_id"], op.ENGINE_BALTOR_PER_NODE_UNIQUE_HARNESS_DAG)
        self.assertEqual(baltor["pass_rate_pct"], "98.6%")
        self.assertEqual(baltor["tokens_per_workflow"], 3420)
        self.assertEqual(baltor["token_spend_delta_pct"], "-91.8%")
        self.assertEqual(baltor["mean_workflow_cost_usd"], 0.0014)

    def test_four_known_wrong_controls_refuse_at_layer6_preflight(self) -> None:
        controls = op.run_known_wrong_controls()
        expected = {
            "control_1_child_node_unrestricted_effect_inheritance": "child_subtask_unrestricted_effect_inheritance_refused",
            "control_2_skills_state_digest_drift": "skills_state_lockfile_digest_drift_refused",
            "control_3_affiliate_or_growth_compliance_violation": "ftc_canspam_or_cfaa_compliance_gate_refused",
            "control_4_cyclic_subtask_dag_dependency": "cyclic_subtask_graph_dependency_refused",
        }
        for key, refusal_code in expected.items():
            res = controls[key]
            self.assertFalse(res.accepted, f"Expected {key} to be refused")
            self.assertIsNotNone(res.refusal)
            assert res.refusal is not None
            self.assertEqual(res.refusal.code, refusal_code)
            self.assertEqual(res.layer_verdicts["preflight"], LAYER_REFUSED)


if __name__ == "__main__":
    unittest.main()
