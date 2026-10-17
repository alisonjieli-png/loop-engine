"""Tests for Generalized & 144-Variation Combinatorial Remix Engine (Prompt Attention & Recovery)."""
from __future__ import annotations

import json
import unittest

from tools.prompt_attention_and_output_recovery_remix_feeds_and_components_engines import (
    apply_analytic_bookend_caveman_remix,
    build_remix_compiler_envelopes,
    build_remix_evolution_publisher_envelopes,
    catalog_twelve_domain_model_archetypes,
    catalog_twelve_generalized_primitives,
    catalog_twelve_remix_recipes,
    evaluate_known_wrong_controls,
    execute_combinatorial_remix_compiler,
    run_iterative_remix_evolution_and_publish_feeds,
    run_seven_stage_zero_token_output_recovery,
    run_thirty_six_task_iterative_remix_benchmark,
    synthesize_all_144_combinatorial_remix_packs,
)


class PromptAttentionAndOutputRecoveryRemixTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 144 5-file remix packs, 36-task benchmark, and 4 controls."""

    def test_twelve_generalized_primitives_and_twelve_archetypes(self) -> None:
        primitives = catalog_twelve_generalized_primitives()
        self.assertEqual(len(primitives), 12)
        expected_ids = {
            "G01_standardized_technical_english",
            "G02_chinese_analytic_topic_comment_grammar",
            "G03_explicit_cause_mechanism_effect_chain",
            "G04_primacy_recency_bookend_doubling",
            "G05_rope_keyword_proximity_packing",
            "G06_caveman_telegraphic_compression",
            "G07_invisible_unicode_and_ansi_stripper",
            "G08_think_tag_and_chatter_peeler",
            "G09_python_js_literal_to_rfc8259_normalizer",
            "G10_pushdown_automaton_truncated_json_closer",
            "G11_sharded_overlapping_leaf_deduplicator",
            "G12_csls_dpp_anti_convergence_diversifier",
        }
        self.assertEqual({p.primitive_id for p in primitives}, expected_ids)

        archetypes = catalog_twelve_domain_model_archetypes()
        self.assertEqual(len(archetypes), 12)
        expected_archetypes = {
            "A01_local_gemma4_31b_surgical_swe_codegen",
            "A02_deepseek_r1_v32_reasoning_trace_and_json_peeler",
            "A03_qwen3_5_vl_and_ui_tars_pixel_gui_grounding",
            "A04_kaggle_tabular_and_timeseries_feature_synthesis",
            "A05_muse_and_dot_restricted_browser_relay",
            "A06_openclaw_and_hermes_long_horizon_handoff",
            "A07_duecare_investigative_entity_and_stakeholder_triage",
            "A08_high_throughput_100k_record_entity_resolution",
            "A09_3d_webgl_and_9x16_shortform_video_scene_compiler",
            "A10_crisis_logistics_and_lunar_physics_simulation",
            "A11_enterprise_byoc_sql_and_warehouse_planner",
            "A12_multi_agent_logjam_breakout_and_brainstorm",
        }
        self.assertEqual({a.archetype_id for a in archetypes}, expected_archetypes)

        recipes = catalog_twelve_remix_recipes()
        self.assertEqual(len(recipes), 12)

    def test_144_combinatorial_five_file_harness_component_packs(self) -> None:
        packs = synthesize_all_144_combinatorial_remix_packs()
        self.assertEqual(len(packs), 144)
        digests = {p.cas_sha256 for p in packs}
        self.assertEqual(len(digests), 144)
        for pack in packs:
            self.assertLessEqual(pack.contract_card_bytes, 2048)
            parsed_card = json.loads(pack.contract_card_json)
            self.assertEqual(parsed_card["remix_id"], pack.remix_id)
            self.assertIn("AGENTS.md", pack.agents_md)
            self.assertIn("[INVARIANT_ANCHOR_START]", pack.rules_md)
            self.assertIn("[INVARIANT_ANCHOR_END]", pack.rules_md)
            self.assertIn("MEMORY.md", pack.memory_md)
            self.assertIn("def verify_remix_pack_output", pack.verifier_py)
            self.assertEqual(len(pack.cas_sha256), 64)

    def test_seven_stage_zero_token_output_recovery_and_analytic_bookend_prompt(self) -> None:
        prompt_text = apply_analytic_bookend_caveman_remix(
            topic_scope="Please kindly analyze the repository module and fix the bug",
            hard_constraints=("Preserve public API", "Pass all unit tests"),
            causal_rule="IF public signature changes -> callers break -> MUST preserve signature",
            action_directive="Could you please emit the minimal surgical JSON patch",
            output_schema_summary="$.patch_hunks",
            enable_caveman_compression=True,
        )
        self.assertTrue(prompt_text.startswith("[INVARIANT_ANCHOR_START]"))
        self.assertTrue(prompt_text.endswith("$.patch_hunks"))
        self.assertNotIn("kindly", prompt_text.lower())

        noisy_truncated = (
            "\ufeff\x1b[32m<think>Checking coordinates and schema...</think>\n"
            "Sure! Here is the payload:\n```json\n"
            '{status: "ok", active: True, missing: None, coords: [420, 680,], nested: {"x": 10'
        )
        recovered = run_seven_stage_zero_token_output_recovery(noisy_truncated)
        self.assertTrue(recovered.recovered_ok)
        self.assertIsNotNone(recovered.parsed_payload)
        assert recovered.parsed_payload is not None
        self.assertEqual(recovered.parsed_payload["status"], "ok")
        self.assertIs(recovered.parsed_payload["active"], True)
        self.assertIsNone(recovered.parsed_payload["missing"])
        self.assertEqual(recovered.parsed_payload["coords"], [420, 680])
        self.assertEqual(recovered.parsed_payload["nested"]["x"], 10)
        self.assertIn("stage2_think_tag_and_chatter_peeler", recovered.stages_applied)
        self.assertIn("stage6_pushdown_automaton_truncated_json_closer", recovered.stages_applied)

    def test_slot_family_1_and_slot_family_2_envelopes_and_execution(self) -> None:
        compiler_envelopes = build_remix_compiler_envelopes()
        self.assertEqual(len(compiler_envelopes), 4)
        compiler_res = execute_combinatorial_remix_compiler()
        self.assertEqual(compiler_res.status, "completed")
        self.assertEqual(compiler_res.primitives_count, 12)
        self.assertEqual(compiler_res.archetypes_count, 12)
        self.assertEqual(compiler_res.recipes_count, 12)
        self.assertEqual(compiler_res.total_remixes_compiled, 144)
        self.assertTrue(compiler_res.envelope_trace["engine_dispatched"])

        publisher_envelopes = build_remix_evolution_publisher_envelopes()
        self.assertEqual(len(publisher_envelopes), 4)
        pub_res = run_iterative_remix_evolution_and_publish_feeds()
        self.assertEqual(pub_res.status, "completed")
        self.assertEqual(pub_res.promoted_generation, 3)
        self.assertEqual(pub_res.agentfeeds_channel, "agentfeeds.si/attention-and-recovery-remixes")
        self.assertEqual(pub_res.agentfoundry_channel, "agentfoundry.si/remix-packs")
        self.assertEqual(pub_res.published_feed_entries, 144)
        self.assertEqual(pub_res.pareto_pass_rate_pct, 98.6)
        self.assertEqual(pub_res.pareto_tokens_per_turn, 540)
        self.assertEqual(pub_res.token_reduction_vs_baseline_pct, -67.3)
        self.assertEqual(len(pub_res.feed_manifest_sha256), 64)

    def test_thirty_six_task_multi_generation_benchmark(self) -> None:
        bench = run_thirty_six_task_iterative_remix_benchmark()
        self.assertEqual(bench["total_multi_domain_tasks"], 36)
        self.assertEqual(bench["verified_remix_packs_count"], 144)
        self.assertLessEqual(bench["max_contract_card_bytes"], 2048)

        arms = bench["arms"]
        base = arms["unremixed_vanilla_prompting_and_strict_json_parser_baseline"]
        iter1 = arms["iteration_1_single_primitive_generalized_pack"]
        iter2 = arms["iteration_2_pairwise_domain_specific_remix"]
        iter3 = arms["iteration_3_pareto_4way_combinatorial_remix_suite"]

        self.assertEqual(base["pass_rate_pct"], 47.2)
        self.assertEqual(base["mean_tokens_per_turn"], 1650)
        self.assertEqual(base["json_parse_or_truncation_failure_rate_pct"], 33.3)

        self.assertEqual(iter1["pass_rate_pct"], 77.8)
        self.assertEqual(iter1["mean_tokens_per_turn"], 980)

        self.assertEqual(iter2["pass_rate_pct"], 91.7)
        self.assertEqual(iter2["mean_tokens_per_turn"], 690)

        self.assertEqual(iter3["pass_rate_pct"], 98.6)
        self.assertEqual(iter3["mean_tokens_per_turn"], 540)
        self.assertEqual(iter3["token_delta_vs_baseline_pct"], -67.3)
        self.assertEqual(iter3["unrecovered_json_failure_rate_pct"], 0.0)
        self.assertEqual(iter3["verified_remix_packs"], 144)

    def test_four_known_wrong_controls_refused_in_preflight(self) -> None:
        controls = evaluate_known_wrong_controls()
        self.assertEqual(
            controls["incompatible_caveman_and_public_humanizer_prose_mode"]["refusal_code"],
            "incompatible_primitive_remix_combination_refused",
        )
        self.assertEqual(
            controls["regressing_remix_iteration_pareto_promotion"]["refusal_code"],
            "remix_iteration_pareto_regression_refused",
        )
        self.assertEqual(
            controls["oversized_contract_card_above_2048_bytes"]["refusal_code"],
            "oversized_remix_contract_card_refused",
        )
        self.assertEqual(
            controls["unhashed_feed_emission_missing_sha256_cas_digest"]["refusal_code"],
            "unhashed_remix_feed_emission_refused",
        )
        for key, item in controls.items():
            self.assertEqual(item["status"], "refused", msg=key)
            self.assertEqual(item["refused_by"], "preflight", msg=key)


if __name__ == "__main__":
    unittest.main()
