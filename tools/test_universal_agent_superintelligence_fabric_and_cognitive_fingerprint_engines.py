"""Unit tests for the Universal Decentralized Agent Superintelligence Fabric
(`Dot`, `OpenClaw`, `Hermes`, `Baltor`, `Claude Code`, `Codex`, `OpenCode`, `Pi`,
`Cursor`, Local Personal AI), Cognitive Fingerprinting, and Continuously Variable
Composable/Deconstructable `Loop` Graph Engine Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

TOOLS_DIR = Path(__file__).resolve().parent
REPOSITORY = TOOLS_DIR.parent
for p in (TOOLS_DIR, REPOSITORY / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from universal_agent_superintelligence_fabric_and_cognitive_fingerprint_engines import (  # noqa: E402
    ALL_10_AGENT_PROFILES,
    ALL_12_ISOMORPHISM_FAMILIES,
    ALL_36_CROSS_DOMAIN_TASKS,
    ENGINE_BALTOR_UNIVERSAL_FABRIC_SUITE,
    ENGINE_CONTINUOUS_ONTOLOGY_COMPILER,
    ENGINE_GOSSIP_MESH_FABRIC,
    ENGINE_ISOLATED_SILOED_AGENTS_BASELINE,
    ENGINE_MATRYOSHKA_ISOMORPHISM_MATCHER,
    ENGINE_SPECTRAL_TOPOLOGY_FINGERPRINT,
    ENGINE_TYPED_EDGE_GRAPH_MORPHISM,
    ENGINE_UNIVERSAL_HARNESS_BRIDGE,
    NODE_HARNESS_REQUIRED_FILES,
    SLOT_COGNITIVE_FINGERPRINT,
    SLOT_UNIVERSAL_AGENT_FABRIC,
    SLOT_VARIABLE_LOOP_GRAPH,
    CognitiveFingerprintAndSolutionReuseSlot,
    ComposableDeconstructableVariableLoopGraphSlot,
    UniversalAgentSuperintelligenceFabricSlot,
    run_known_wrong_controls,
    run_universal_superintelligence_fabric_benchmark,
)
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_PREFLIGHT, LAYER_REFUSED  # noqa: E402


class UniversalAgentSuperintelligenceFabricTests(unittest.TestCase):
    def test_10_first_class_agent_profiles_and_36_cross_domain_tasks(self) -> None:
        self.assertEqual(len(ALL_10_AGENT_PROFILES), 10)
        self.assertEqual(len(ALL_12_ISOMORPHISM_FAMILIES), 12)
        self.assertEqual(len(ALL_36_CROSS_DOMAIN_TASKS), 36)

        expected_profiles = {
            "dot_personal_and_venture_assistant",
            "openclaw_autonomous_desktop_and_browser_agent",
            "hermes_persistent_skill_and_memory_agent",
            "baltor_native_practitioner_solution_loop",
            "claude_code_cli_and_ide_agent",
            "openai_codex_cli_and_cloud_agent",
            "opencode_baltor_tui_agent",
            "pi_pie_minimal_4tool_agent",
            "cursor_windsurf_ide_composer_agent",
            "local_lan_edge_personal_ai_assistant",
        }
        self.assertEqual({p.profile_id for p in ALL_10_AGENT_PROFILES}, expected_profiles)

    def test_slot_family_1_universal_decentralized_fabric_and_gossip_receipts(self) -> None:
        fabric = UniversalAgentSuperintelligenceFabricSlot()
        res_first = fabric.run_universal_agent_task_on_fabric(
            "TASK_01",
            preferred_engine=ENGINE_GOSSIP_MESH_FABRIC,
            request_id="test_fabric_task_01",
        )
        self.assertTrue(res_first.accepted)
        self.assertEqual(res_first.slot_id, SLOT_UNIVERSAL_AGENT_FABRIC)
        self.assertEqual(res_first.selected_engine, ENGINE_GOSSIP_MESH_FABRIC)
        for layer in COVERAGE_LAYERS:
            self.assertEqual(res_first.layer_verdicts[layer], "full")
        self.assertFalse(res_first.output["reused_existing_gossip_crystal"])
        self.assertTrue(res_first.output["gossip_receipt_packet"]["pii_anonymized"])
        self.assertLess(res_first.output["gossip_receipt_packet"]["gossip_lookup_latency_ms"], 2.0)

        # Second task in the same isomorphism family (SQLite WAL vs Air-Traffic holding pattern)
        # immediately reuses the promoted gossip crystal across agent ecosystems!
        res_second = fabric.run_universal_agent_task_on_fabric(
            "TASK_02",
            preferred_engine=ENGINE_UNIVERSAL_HARNESS_BRIDGE,
            request_id="test_fabric_task_02",
        )
        self.assertTrue(res_second.accepted)
        self.assertEqual(res_second.selected_engine, ENGINE_UNIVERSAL_HARNESS_BRIDGE)
        self.assertTrue(res_second.output["reused_existing_gossip_crystal"])

    def test_slot_family_2_cognitive_fingerprint_and_cross_domain_isomorphism(self) -> None:
        fp_slot = CognitiveFingerprintAndSolutionReuseSlot()
        r1 = fp_slot.match_task_cognitive_fingerprint(
            "TASK_01",
            preferred_engine=ENGINE_MATRYOSHKA_ISOMORPHISM_MATCHER,
            request_id="test_fp_01",
        )
        r2 = fp_slot.match_task_cognitive_fingerprint(
            "TASK_02",
            preferred_engine=ENGINE_SPECTRAL_TOPOLOGY_FINGERPRINT,
            request_id="test_fp_02",
        )
        r3 = fp_slot.match_task_cognitive_fingerprint(
            "TASK_03",
            preferred_engine=ENGINE_MATRYOSHKA_ISOMORPHISM_MATCHER,
            request_id="test_fp_03",
        )
        self.assertTrue(r1.accepted and r2.accepted and r3.accepted)
        self.assertEqual(r1.slot_id, SLOT_COGNITIVE_FINGERPRINT)
        self.assertEqual(
            r1.output["matched_isomorphism_id"],
            "bounded_capacity_priority_fair_queue_with_aging",
        )
        # Air-traffic holding pattern (TASK_01), SQLite WAL queue (TASK_02), and ER triage (TASK_03)
        # share the exact same 64-bit Matryoshka hex and topology digest!
        self.assertEqual(
            r1.output["cognitive_fingerprint"]["binary_matryoshka_64bit_hex"],
            r2.output["cognitive_fingerprint"]["binary_matryoshka_64bit_hex"],
        )
        self.assertEqual(
            r2.output["cognitive_fingerprint"]["topology_invariant_digest"],
            r3.output["cognitive_fingerprint"]["topology_invariant_digest"],
        )

    def test_slot_family_3_four_live_variable_loop_graph_morphisms(self) -> None:
        graph_slot = ComposableDeconstructableVariableLoopGraphSlot()
        res = graph_slot.execute_graph_morphism(
            "bounded_capacity_priority_fair_queue_with_aging",
            alpha_interpolation=0.6,
            preferred_engine=ENGINE_TYPED_EDGE_GRAPH_MORPHISM,
            request_id="test_graph_morph_01",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_VARIABLE_LOOP_GRAPH)
        self.assertTrue(res.output["all_vertices_are_concrete_loop_class"])

        m1 = res.output["morphism_1_splice_interstitial_loop_node"]
        self.assertTrue(m1["edge_contracts_preserved"])
        self.assertLess(m1["splice_latency_ms"], 1.1)
        self.assertEqual(tuple(m1["harness_files"]), tuple(sorted(NODE_HARNESS_REQUIRED_FILES)))

        m2 = res.output["morphism_2_deconstruct_macro_loop_into_subgraph"]
        self.assertEqual(len(m2["child_loop_node_ids"]), 3)
        self.assertTrue(m2["every_child_has_full_5_file_harness"])

        m3 = res.output["morphism_3_compose_subgraph_into_reusable_macro_loop"]
        self.assertTrue(m3["reusable_across_all_10_agent_harnesses"])

        m4 = res.output["morphism_4_continuous_ontology_and_parameter_morph"]
        self.assertAlmostEqual(m4["alpha"], 0.6)
        self.assertEqual(len(m4["morphed_ontology_vector"]), 4)

        res_alt = graph_slot.execute_graph_morphism(
            "idempotent_outbox_with_compensating_saga_rollback",
            alpha_interpolation=0.2,
            preferred_engine=ENGINE_CONTINUOUS_ONTOLOGY_COMPILER,
            request_id="test_graph_morph_02",
        )
        self.assertTrue(res_alt.accepted)
        self.assertEqual(res_alt.selected_engine, ENGINE_CONTINUOUS_ONTOLOGY_COMPILER)

    def test_benchmark_10_agent_ecosystems_across_36_cross_domain_tasks(self) -> None:
        bench = run_universal_superintelligence_fabric_benchmark()
        self.assertEqual(bench["total_agent_ecosystems"], 10)
        self.assertEqual(bench["total_cross_domain_tasks"], 36)
        self.assertEqual(bench["total_isomorphism_families"], 12)
        self.assertTrue(bench["all_36_tasks_executed_through_7_layer_envelope"])

        siloed = bench["isolated_siloed_agents_with_static_graphs_without_baltor"]
        self.assertEqual(siloed["engine_id"], ENGINE_ISOLATED_SILOED_AGENTS_BASELINE)
        self.assertEqual(siloed["pass_rate_pct"], "47.2%")
        self.assertEqual(siloed["cross_agent_knowledge_transfer_pct"], "0.0%")
        self.assertEqual(siloed["cold_start_rederivation_cost_pct"], "100.0%")

        baltor = bench["baltor_universal_fabric_with_cognitive_fingerprints_and_variable_graphs"]
        self.assertEqual(baltor["engine_id"], ENGINE_BALTOR_UNIVERSAL_FABRIC_SUITE)
        self.assertEqual(baltor["pass_rate_pct"], "97.2%")
        self.assertEqual(baltor["cognitive_fingerprint_reuse_hit_rate_pct"], "94.4%")
        self.assertEqual(baltor["cold_start_token_spend_reduction_pct"], "-89.1%")
        self.assertLess(baltor["mean_gossip_receipt_query_latency_ms"], 2.0)
        self.assertLess(baltor["mean_interstitial_node_splice_latency_ms"], 1.1)

    def test_four_known_wrong_controls_refused_at_preflight(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "non_loop_concrete_runtime_subclass_refused",
            "incompatible_interstitial_edge_splice_schema_refused",
            "unanonymized_or_self_approved_gossip_receipt_refused",
            "unbounded_cyclic_graph_composition_refused",
        }
        observed_codes = set()
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"])
            self.assertEqual(ctrl["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(ctrl["refused_before_engine"])
            observed_codes.add(ctrl["actual_refusal_code"])
        self.assertEqual(observed_codes, expected_codes)


if __name__ == "__main__":
    unittest.main()
