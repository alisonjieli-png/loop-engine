"""Tests and known-wrong controls for the Jagged Frontier, LLM Agent Trace
Research Analyzer, Capability-Gap Taxonomy & Poor Default LLM/Harness Behavior
Combat Engine Suite.
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

import jagged_frontier_llm_trace_and_default_behavior_combat_engines as jf  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class JaggedFrontierLlmTraceAndDefaultBehaviorCombatTests(unittest.TestCase):
    """Verify the 20-pathology taxonomy, 2 slot families, N=60 benchmark, and 4 known-wrong controls."""

    def test_20_pathology_jagged_frontier_taxonomy_and_literature_corpus(self) -> None:
        self.assertEqual(len(jf.JAGGED_FRONTIER_PATHOLOGIES), 20)
        self.assertEqual(len(jf.LLM_PATHOLOGY_IDS), 10)
        self.assertEqual(len(jf.HARNESS_PATHOLOGY_IDS), 10)
        self.assertEqual(len(jf.RESEARCH_LITERATURE_CORPUS), 6)

        expected_llm_ids = (
            "LLM-01_jagged_arithmetic_and_spatial_blindness",
            "LLM-02_quadratic_all_pairs_reasoning_collapse",
            "LLM-03_lost_in_the_middle_context_rot",
            "LLM-04_sycophantic_premise_capitulation",
            "LLM-05_lazy_ellipsis_and_placeholder_truncation",
            "LLM-06_hallucinated_api_and_version_drift",
            "LLM-07_uncalibrated_confidence_and_quantile_crossing",
            "LLM-08_ai_slop_and_antithetical_cadence_default",
            "LLM-09_temporal_lookahead_and_group_leakage_blindness",
            "LLM-10_reward_hacking_and_test_weakening",
        )
        expected_har_ids = (
            "HAR-01_upfront_mcp_schema_bloat",
            "HAR-02_full_file_rewrite_digest_destruction",
            "HAR-03_blind_unbounded_retry_spirals",
            "HAR-04_clarifying_question_stall_on_autonomous_runs",
            "HAR-05_unverified_self_declared_victory",
            "HAR-06_lossy_compaction_amnesia",
            "HAR-07_overlapping_worktree_and_silent_merge_drop",
            "HAR-08_non_idempotent_effect_retry",
            "HAR-09_always_frontier_model_overspend",
            "HAR-10_human_meat_proxy_dependency",
        )
        self.assertEqual(jf.LLM_PATHOLOGY_IDS, expected_llm_ids)
        self.assertEqual(jf.HARNESS_PATHOLOGY_IDS, expected_har_ids)

    def test_slot1_pathology_mapper_across_all_swappable_engines(self) -> None:
        mapper = jf.JaggedFrontierAndTracePathologyMapperSlot()
        for idx, engine_id in enumerate(jf.MAPPER_ENGINE_ORDER):
            res = mapper.map_pathology_or_taxonomy(
                "LLM-03_lost_in_the_middle_context_rot",
                request_id=f"test_mapper_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.output["code"], "LLM-03")
            self.assertEqual(res.output["total_taxonomy_modes"], 20)
            self.assertGreaterEqual(len(res.output["grounding_studies"]), 1)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

    def test_slot2_combat_and_pack_synthesizer_emits_all_five_pack_artifacts(self) -> None:
        synthesizer = jf.JaggedFrontierCombatAndPackSynthesizerSlot()
        for idx, engine_id in enumerate(jf.COMBAT_ENGINE_ORDER):
            res = synthesizer.synthesize_combat_pack(
                "HAR-01_upfront_mcp_schema_bloat",
                request_id=f"test_combat_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertTrue(res.output["pathology_detected_and_neutralized"])
            self.assertTrue(res.output["contract_card_within_2048_bytes"])
            self.assertLessEqual(int(res.output["contract_card_bytes"]), 2048)

            files = res.output["files"]
            for required_file in ("AGENTS.md", "RULES.md", "MEMORY.md", "SKILL.md", "baltor_contract_card.json"):
                self.assertIn(required_file, files)
                self.assertTrue(len(files[required_file]) > 40)

            card = json.loads(files["baltor_contract_card.json"])
            self.assertEqual(card["pathology_id"], "HAR-01_upfront_mcp_schema_bloat")
            self.assertEqual(card["code"], "HAR-01")
            study_row = res.output["ablation_study_row"]
            self.assertIn("paper.baltor.ai", study_row["publication_targets"])
            self.assertIn("agentbriefs.si", study_row["publication_targets"])

    def test_60_trial_benchmark_matches_empirical_targets(self) -> None:
        bench = jf.run_jagged_frontier_60trial_benchmark()
        self.assertEqual(bench["total_pathologies"], 20)
        self.assertEqual(bench["total_adversarial_trials"], 60)

        unprotected = bench["default_unprotected_llm_and_harness"]
        self.assertEqual(unprotected["engine_id"], jf.ENGINE_UNPROTECTED_DEFAULT_BASELINE)
        self.assertEqual(unprotected["trials_survived"], 7)
        self.assertEqual(unprotected["survival_rate_pct"], "11.7%")
        self.assertEqual(unprotected["wasted_tokens_per_trial"], 4850)

        baltor = bench["baltor_20mode_jagged_frontier_combat_suite"]
        self.assertEqual(baltor["engine_id"], jf.ENGINE_BALTOR_20MODE_COMBAT_SUITE)
        self.assertEqual(baltor["pathologies_detected_and_neutralized"], 60)
        self.assertEqual(baltor["detection_and_neutralization_rate_pct"], "100.0%")
        self.assertEqual(baltor["trials_passed"], 59)
        self.assertEqual(baltor["task_pass_rate_pct"], "98.3%")
        self.assertEqual(baltor["wasted_tokens_per_trial"], 747)
        self.assertEqual(baltor["token_waste_delta_pct"], "-84.6%")

    def test_four_known_wrong_controls_refuse_at_layer6_preflight(self) -> None:
        controls = jf.run_known_wrong_controls()
        expected = {
            "control_1_llm10_test_assertion_weakening": "test_assertion_deletion_or_weakening_refused",
            "control_2_llm05_ellipsis_truncation": "lazy_ellipsis_or_placeholder_truncation_refused",
            "control_3_har02_untouched_ast_mutation": "untouched_ast_symbol_digest_mutation_refused",
            "control_4_har05_unverified_victory": "unverified_self_declared_victory_refused",
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
