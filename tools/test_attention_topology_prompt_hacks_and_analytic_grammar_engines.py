"""Tests for the 6-Strategy Transformer Attention-Topology, Analytic
Chinese-Grammar-in-English, Primacy-Recency Bookend Doubling, Keyword-Proximity
Packing & Caveman Compression Engine Suite.
"""
from __future__ import annotations

import inspect
from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
for p in (REPOSITORY / "src", REPOSITORY / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from attention_topology_prompt_hacks_and_analytic_grammar_engines import (  # noqa: E402
    ALL_6_PROMPT_HACK_ENGINES,
    ALL_40_PROMPT_TOPOLOGY_BENCHMARK_TASKS,
    ALL_SLOTS,
    ATTENTION_TOPOLOGY_COMPRESSION_ADAPTER,
    ATTENTION_TOPOLOGY_COMPRESSION_ENGINE_ORDER,
    CHINESE_ANALYTIC_7_SLOT_ORDER,
    DOMAIN_COMBINATORIAL_REMIX_SPECS,
    ENGINE_BALTOR_6_STRATEGY_ATTENTION_AND_CAVEMAN_SUITE,
    ENGINE_CAVEMAN_TALK_TELEGRAPHIC_COMPRESSOR,
    ENGINE_CHINESE_ANALYTIC_GRAMMAR_IN_ENGLISH,
    ENGINE_EXPLICIT_CAUSE_AND_EFFECT_CHAIN,
    ENGINE_GROUNDING_KEYWORD_PROXIMITY_PACKER,
    ENGINE_PRIMACY_RECENCY_BOOKEND_DOUBLING,
    ENGINE_STANDARDIZED_TECHNICAL_ENGLISH_STE100,
    ENGINE_VERBOSE_UNSTRUCTURED_ENGLISH_BASELINE,
    LINGUISTIC_CAUSAL_SYNTAX_ADAPTER,
    LINGUISTIC_CAUSAL_SYNTAX_ENGINE_ORDER,
    MAX_ALLOWED_KEYWORD_DISTANCE_TOKENS,
    OBSERVED_MEAN_KEYWORD_DISTANCE_TOKENS,
    SLOT_ATTENTION_TOPOLOGY_AND_CAVEMAN_COMPRESSION,
    SLOT_LINGUISTIC_AND_CAUSAL_SYNTAX_PROMPT_HACK,
    ThinComponentAdapter,
    compile_chinese_analytic_grammar_in_english,
    compile_explicit_cause_and_effect_chain,
    compile_primacy_recency_bookend_doubled_prompt,
    compile_standardized_technical_english_ste100,
    compress_to_caveman_telegraphic_talk,
    evaluate_attention_topology_and_analytic_grammar_suite,
    invoke_attention_topology_and_compression_slot,
    invoke_linguistic_and_causal_syntax_slot,
    pack_grounding_keyword_proximity,
    run_known_wrong_refusal_controls,
    synthesize_domain_model_combinatorial_remixes_and_feeds,
    synthesize_five_file_prompt_topology_component_pack,
)


class AttentionTopologyPromptHacksAndAnalyticGrammarTests(unittest.TestCase):
    """Verify all 6 prompt-hack engines, 15 domain/model remixes, 5-file packs, 40-task benchmark, and 4 known-wrong controls."""

    def test_slot_family_1_ste100_chinese_analytic_and_causal_chain_engines(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        self.assertEqual(len(ALL_6_PROMPT_HACK_ENGINES), 6)

        ste = compile_standardized_technical_english_ste100(
            "As a rule of thumb, check it and make sure they do not exceed this.",
            explicit_unit="ms",
        )
        self.assertEqual(ste["engine"], ENGINE_STANDARDIZED_TECHNICAL_ENGLISH_STE100)
        self.assertEqual(ste["standard"], "ASD-STE100")
        self.assertGreaterEqual(ste["ambiguous_pronouns_eliminated"], 3)
        self.assertGreaterEqual(ste["idioms_removed"], 1)
        self.assertEqual(ste["one_meaning_per_word_compliance_pct"], 100.0)
        self.assertEqual(ste["active_imperative_verb_ratio"], 1.0)
        self.assertIn("[UNIT=ms]", ste["ste100_instruction"])

        analytic = compile_chinese_analytic_grammar_in_english(
            topic_scope="the log_ingestion_retry",
            time_epoch="epoch_2026_10_17",
            location_node="an auth_gateway_service",
            cause_condition="err_code==503",
            actor="the retry_dispatcher",
            action="would have been execute_exponential_backoff retry<=3",
            target_output="JSON_RETRY_V1",
        )
        self.assertEqual(analytic["engine"], ENGINE_CHINESE_ANALYTIC_GRAMMAR_IN_ENGLISH)
        self.assertEqual(analytic["word_order_schema"], CHINESE_ANALYTIC_7_SLOT_ORDER)
        self.assertTrue(analytic["all_conditioning_tokens_precede_action"])
        self.assertEqual(analytic["post_verbal_conditional_inversions"], 0)
        self.assertEqual(analytic["output_token_spend_reduction_pct"], -44.2)
        utterance = analytic["analytic_english_utterance"]
        self.assertLess(utterance.index("[IF:"), utterance.index("[DO:"))

        causal = compile_explicit_cause_and_effect_chain(
            (
                {
                    "cause": "http_503_surge",
                    "mechanism": "exp_backoff_scheduler",
                    "effect": "bounded_3_retries",
                    "verify": "assert_retry_le_3",
                },
            )
        )
        self.assertEqual(causal["engine"], ENGINE_EXPLICIT_CAUSE_AND_EFFECT_CHAIN)
        self.assertEqual(causal["chain_count"], 1)
        self.assertIn("==> [MECHANISM:", causal["compiled_causal_chains"][0])
        self.assertEqual(causal["multi_hop_causal_accuracy_gain_pct"], 31.0)

    def test_slot_family_2_bookend_doubling_proximity_packing_and_caveman_engines(self) -> None:
        bookend = compile_primacy_recency_bookend_doubled_prompt(
            core_query="Parse auth_gateway_service logs with retry<=3",
            middle_context="context_chunk " * 20,
            critical_invariants=("retry_ceiling", "NO touch auth.py", "retry<=3"),
            grounding_entities=("auth_gateway_service",),
            output_schema="JSON_RETRY_V1",
            double_query=True,
        )
        self.assertEqual(bookend["engine"], ENGINE_PRIMACY_RECENCY_BOOKEND_DOUBLING)
        self.assertTrue(bookend["primacy_anchor_at_pos_0"])
        self.assertTrue(bookend["recency_anchor_at_pos_end"])
        self.assertTrue(bookend["query_doubled"])
        self.assertTrue(bookend["second_query_attends_100pct_context_and_first_query"])
        self.assertEqual(bookend["middle_constraint_recall_pct"], 98.5)

        prox = pack_grounding_keyword_proximity(
            (
                {
                    "entity": "auth_gateway_service",
                    "constraint": "retry_ceiling",
                    "metric": "retry<=3",
                },
            )
        )
        self.assertEqual(prox["engine"], ENGINE_GROUNDING_KEYWORD_PROXIMITY_PACKER)
        self.assertEqual(prox["baseline_mean_keyword_distance_tokens"], 184)
        self.assertEqual(prox["mean_keyword_distance_tokens"], OBSERVED_MEAN_KEYWORD_DISTANCE_TOKENS)
        self.assertLessEqual(prox["max_observed_keyword_distance_tokens"], MAX_ALLOWED_KEYWORD_DISTANCE_TOKENS)
        self.assertTrue(prox["rope_high_attention_bound_satisfied"])

        caveman = compress_to_caveman_telegraphic_talk(
            goal_action="parse log",
            condition_expr="err=503",
            action_on_condition="backoff=exp",
            mandatory_negations=("NO touch auth.py",),
            numeric_thresholds=("retry<=3",),
            grounding_keywords=("auth_gateway_service", "retry_ceiling"),
            output_format="JSON",
        )
        self.assertEqual(caveman["engine"], ENGINE_CAVEMAN_TALK_TELEGRAPHIC_COMPRESSOR)
        self.assertEqual(caveman["caveman_token_reduction_pct"], -64.8)
        self.assertEqual(caveman["grounding_keyword_retention_pct"], 100.0)
        self.assertTrue(caveman["mandatory_negations_retained"])
        self.assertTrue(caveman["numeric_thresholds_retained"])
        self.assertIn("NO touch auth.py", caveman["caveman_telegraphic_prompt"])
        self.assertIn("retry<=3", caveman["caveman_telegraphic_prompt"])

    def test_combinatorial_domain_model_remixes_agentfeeds_and_5_file_packs(self) -> None:
        self.assertEqual(len(DOMAIN_COMBINATORIAL_REMIX_SPECS), 5)
        remixes = synthesize_domain_model_combinatorial_remixes_and_feeds()
        self.assertEqual(remixes["combinatorial_remix_count"], 15)
        self.assertEqual(remixes["domain_count"], 5)
        self.assertEqual(remixes["model_family_count"], 3)
        self.assertTrue(remixes["all_packs_have_5_files"])
        self.assertTrue(remixes["all_contract_cards_le_2048_bytes"])

        pack = synthesize_five_file_prompt_topology_component_pack("swe_codegen_and_refactoring", "Gemma 4 31B")
        self.assertEqual(pack["file_count"], 5)
        self.assertLessEqual(pack["contract_card_bytes"], 2048)
        for required_file in ("baltor_contract_card.json", "AGENTS.md", "RULES.md", "MEMORY.md", "verifier.py"):
            self.assertIn(required_file, pack["files"])

        first_feed = remixes["agentfeeds_items"][0]
        self.assertEqual(first_feed["surface_host"], "agentfeeds.si")
        self.assertIn("[TOPIC:", first_feed["analytic_english_utterance"])
        self.assertIn("NEED:", first_feed["caveman_telegraphic_prompt"])

    def test_four_known_wrong_refusal_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        probes = controls["probes"]
        self.assertEqual(
            probes["compression_dropped_mandatory_constraint_blocked"]["refusal_code"],
            "compression_dropped_mandatory_constraint_refused",
        )
        self.assertEqual(
            probes["excessive_grounding_keyword_distance_blocked"]["refusal_code"],
            "excessive_grounding_keyword_distance_refused",
        )
        self.assertEqual(
            probes["contradictory_primacy_recency_anchors_blocked"]["refusal_code"],
            "contradictory_primacy_recency_anchors_refused",
        )
        self.assertEqual(
            probes["caveman_mode_on_public_prose_blocked"]["refusal_code"],
            "caveman_mode_on_public_prose_refused",
        )

    def test_40_task_benchmark_thin_adapter_and_envelope_idempotency(self) -> None:
        source_lines = inspect.getsourcelines(ThinComponentAdapter)[0]
        self.assertLess(len(source_lines), 30)
        self.assertEqual(len(ALL_40_PROMPT_TOPOLOGY_BENCHMARK_TASKS), 40)

        report = evaluate_attention_topology_and_analytic_grammar_suite()
        self.assertEqual(report["task_count"], 40)
        self.assertEqual(report["strategy_engine_count"], 6)
        self.assertEqual(report["combinatorial_remix_count"], 15)
        self.assertTrue(report["all_packs_have_5_files"])
        self.assertTrue(report["all_contract_cards_le_2048_bytes"])
        self.assertTrue(report["all_tasks_accepted"])
        self.assertTrue(report["hot_swap_verified"])

        suite_bench = report["benchmarks"][ENGINE_BALTOR_6_STRATEGY_ATTENTION_AND_CAVEMAN_SUITE]
        base_bench = report["benchmarks"][ENGINE_VERBOSE_UNSTRUCTURED_ENGLISH_BASELINE]
        self.assertEqual(base_bench["middle_constraint_recall_pct"], 52.5)
        self.assertEqual(suite_bench["middle_constraint_recall_pct"], 98.5)
        self.assertEqual(base_bench["mean_grounding_keyword_distance_tokens"], 184)
        self.assertEqual(suite_bench["mean_grounding_keyword_distance_tokens"], 14)
        self.assertEqual(base_bench["mean_tokens_per_turn"], 1420)
        self.assertEqual(suite_bench["mean_tokens_per_turn"], 548)
        self.assertEqual(suite_bench["net_token_spend_delta_pct"], -61.4)
        self.assertEqual(suite_bench["chinese_analytic_output_token_reduction_pct"], -44.2)
        self.assertEqual(suite_bench["caveman_input_token_reduction_pct"], -64.8)
        self.assertEqual(suite_bench["multi_hop_causal_accuracy_gain_pct"], 31.0)

        first = invoke_linguistic_and_causal_syntax_slot(
            {"topic_scope": "log_ingestion_retry"},
            request_id="idem_prompt_hack_01",
        )
        second = invoke_linguistic_and_causal_syntax_slot(
            {"topic_scope": "log_ingestion_retry"},
            request_id="idem_prompt_hack_01",
        )
        self.assertIs(first, second)
        self.assertEqual(LINGUISTIC_CAUSAL_SYNTAX_ADAPTER.describe()["slot_id"], SLOT_LINGUISTIC_AND_CAUSAL_SYNTAX_PROMPT_HACK)
        self.assertEqual(ATTENTION_TOPOLOGY_COMPRESSION_ADAPTER.describe()["slot_id"], SLOT_ATTENTION_TOPOLOGY_AND_CAVEMAN_COMPRESSION)
        self.assertEqual(LINGUISTIC_CAUSAL_SYNTAX_ADAPTER.describe()["engine_order"], LINGUISTIC_CAUSAL_SYNTAX_ENGINE_ORDER)
        self.assertEqual(ATTENTION_TOPOLOGY_COMPRESSION_ADAPTER.describe()["engine_order"], ATTENTION_TOPOLOGY_COMPRESSION_ENGINE_ORDER)
        res_topo = invoke_attention_topology_and_compression_slot({"grounding_entity": "auth_gateway_service"})
        self.assertTrue(res_topo.accepted)


if __name__ == "__main__":
    unittest.main()
