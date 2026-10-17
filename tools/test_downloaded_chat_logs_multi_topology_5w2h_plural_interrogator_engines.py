"""Unit tests for the Downloaded Chat Archive & Public Dump Multi-Topology Chunking,
Mixed-Ontology Brainstorming, Context-Ablated Plural 5W2H Interrogator &
Repeated-Correction Harness Generator Suite.
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

from downloaded_chat_logs_multi_topology_5w2h_plural_interrogator_engines import (  # noqa: E402
    ALL_8_CORPUS_FAMILIES,
    ALL_16_PROMPT_CORRECTED_PATHOLOGIES,
    ALL_24_ARCHETYPES,
    CHUNK_TOPOLOGIES,
    CONTEXT_REGIMES,
    DIMENSIONS_5W2H,
    ENGINE_BALTOR_5_TOPOLOGY_4_CONTEXT_5W2H,
    ENGINE_DETERMINISTIC_5W2H_COMPILER,
    ENGINE_MULTI_TOPOLOGY_LSH_CHUNKER,
    ENGINE_PLURAL_5W2H_CONSENSUS,
    ENGINE_SINGLE_PASS_RAG_BASELINE,
    ENGINE_SLIDING_DILATED_CHUNKER,
    MAX_CONTRACT_CARD_BYTES,
    MIN_PLURAL_ANSWERS_REQUIRED,
    SLOT_MULTI_TOPOLOGY_CHUNKER,
    SLOT_PLURAL_5W2H_INTERROGATOR,
    ChatArchiveAndPublicDumpMultiTopologyChunkerSlot,
    ContextAblatedPlural5W2HBrainstormSlot,
    dual_stage_anonymize_text,
    run_chat_archive_5w2h_benchmark,
    run_known_wrong_controls,
)
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_PREFLIGHT, LAYER_REFUSED  # noqa: E402


class DownloadedChatLogsMultiTopology5W2HPluralInterrogatorTests(unittest.TestCase):
    def test_8_corpora_5_topologies_4_regimes_and_16_pathologies_catalog(self) -> None:
        self.assertEqual(len(ALL_8_CORPUS_FAMILIES), 8)
        self.assertEqual(len(CHUNK_TOPOLOGIES), 5)
        self.assertEqual(len(CONTEXT_REGIMES), 4)
        self.assertEqual(DIMENSIONS_5W2H, ("Who", "What", "Where", "When", "Why", "How"))
        self.assertEqual(len(ALL_16_PROMPT_CORRECTED_PATHOLOGIES), 16)
        self.assertEqual(len(ALL_24_ARCHETYPES), 24)

        quotes = [p.representative_owner_correction_quote for p in ALL_16_PROMPT_CORRECTED_PATHOLOGIES]
        self.assertIn("Stop asking me dumb questions, I want a clean best practice newsletter", quotes)
        self.assertIn(
            "Go through all of the design files and make sure there aren't broken links / alert('Message sent') stubs",
            quotes,
        )
        self.assertIn("I want more styles and ideas and color schemes", quotes)
        self.assertIn("Memory overflow in code execution", quotes)
        self.assertIn("Don't make floating 3D islands without a horizon", quotes)
        self.assertIn("The anonymizer should be both local and public", quotes)

    def test_dual_stage_local_and_public_anonymizer(self) -> None:
        raw = (
            "User alison@example.com in /home/username/Downloads/design_chats "
            "uuid 816973d2-4a2b-4c1e-9f00-112233445566 key sk-abcdefghijklmnop1234"
        )
        res = dual_stage_anonymize_text(raw)
        self.assertTrue(res["local_stage_scrubbed"])
        self.assertTrue(res["public_stage_scrubbed"])
        self.assertEqual(res["pii_leak_count"], 0)
        self.assertNotIn("alison@example.com", res["sanitized_text"])
        self.assertNotIn("816973d2-4a2b-4c1e-9f00-112233445566", res["sanitized_text"])
        self.assertNotIn("/home/username", res["sanitized_text"])

    def test_slot_family_1_and_nested_slot_family_2_execution(self) -> None:
        chunker_slot = ChatArchiveAndPublicDumpMultiTopologyChunkerSlot()
        res_primary = chunker_slot.chunk_and_interrogate_archetype(
            "ARCH_01",
            preferred_engine=ENGINE_MULTI_TOPOLOGY_LSH_CHUNKER,
            request_id="test_chunk_primary",
        )
        self.assertTrue(res_primary.accepted)
        self.assertEqual(res_primary.slot_id, SLOT_MULTI_TOPOLOGY_CHUNKER)
        self.assertEqual(res_primary.selected_engine, ENGINE_MULTI_TOPOLOGY_LSH_CHUNKER)
        for layer in COVERAGE_LAYERS:
            self.assertEqual(res_primary.layer_verdicts[layer], "full")
        self.assertTrue(res_primary.output["local_and_public_anonymized"])
        self.assertEqual(res_primary.output["topology_count"], 5)
        for top in CHUNK_TOPOLOGIES:
            self.assertIn(top, res_primary.output["chunk_topologies_generated"])
        self.assertTrue(res_primary.output["nested_interrogation_accepted"])

        res_fallback = chunker_slot.chunk_and_interrogate_archetype(
            "ARCH_02",
            preferred_engine=ENGINE_SLIDING_DILATED_CHUNKER,
            request_id="test_chunk_fallback",
        )
        self.assertTrue(res_fallback.accepted)
        self.assertEqual(res_fallback.selected_engine, ENGINE_SLIDING_DILATED_CHUNKER)

        interrogator_slot = ContextAblatedPlural5W2HBrainstormSlot()
        res_int = interrogator_slot.interrogate_archetype(
            "ARCH_03",
            preferred_engine=ENGINE_DETERMINISTIC_5W2H_COMPILER,
            request_id="test_int_fallback",
        )
        self.assertTrue(res_int.accepted)
        self.assertEqual(res_int.slot_id, SLOT_PLURAL_5W2H_INTERROGATOR)
        self.assertEqual(res_int.selected_engine, ENGINE_DETERMINISTIC_5W2H_COMPILER)
        self.assertGreaterEqual(res_int.output["min_plurality_observed"], MIN_PLURAL_ANSWERS_REQUIRED)
        self.assertLessEqual(
            res_int.output["compiled_harness_artifacts"]["contract_card_byte_length"],
            MAX_CONTRACT_CARD_BYTES,
        )
        self.assertEqual(res_int.selected_engine, ENGINE_DETERMINISTIC_5W2H_COMPILER)
        res_int_primary = interrogator_slot.interrogate_archetype(
            "ARCH_04",
            preferred_engine=ENGINE_PLURAL_5W2H_CONSENSUS,
            request_id="test_int_primary",
        )
        self.assertEqual(res_int_primary.selected_engine, ENGINE_PLURAL_5W2H_CONSENSUS)

    def test_benchmark_across_24_archetypes(self) -> None:
        bench = run_chat_archive_5w2h_benchmark()
        self.assertEqual(bench["total_archetypes_evaluated"], 24)
        self.assertEqual(bench["archetypes_passed"], 24)
        self.assertEqual(bench["corpus_families_covered"], 8)
        self.assertEqual(bench["chunk_topologies_covered"], 5)
        self.assertEqual(bench["context_regimes_covered"], 4)
        self.assertEqual(bench["catalogued_pathologies_total"], 16)
        self.assertEqual(bench["catalogued_pathologies_captured"], 16)

        base = bench["single_pass_sequential_single_answer_rag_baseline"]
        self.assertEqual(base["engine_id"], ENGINE_SINGLE_PASS_RAG_BASELINE)
        self.assertEqual(base["repeated_correction_capture_rate_pct"], "31.2%")
        self.assertAlmostEqual(base["plural_entity_coverage_per_5w2h_slot"], 1.0)

        baltor = bench["baltor_5_topology_4_context_plural_5w2h_engine"]
        self.assertEqual(baltor["engine_id"], ENGINE_BALTOR_5_TOPOLOGY_4_CONTEXT_5W2H)
        self.assertEqual(baltor["repeated_correction_capture_rate_pct"], "100.0%")
        self.assertAlmostEqual(baltor["plural_entity_coverage_per_5w2h_slot"], 5.4)
        self.assertAlmostEqual(baltor["cross_domain_brainstorm_signal_yield_multiplier"], 18.5)
        self.assertEqual(baltor["repeat_correction_prompt_reduction_pct"], "-94.2%")

    def test_four_known_wrong_controls_refused_at_preflight(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "unanonymized_personal_chat_log_refused",
            "singular_5w2h_answer_set_refused",
            "inconsistent_context_regime_invariant_promotion_refused",
            "contract_card_byte_ceiling_exceeded_refused",
        }
        observed = set()
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"])
            self.assertEqual(ctrl["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(ctrl["refused_before_engine"])
            observed.add(ctrl["actual_refusal_code"])
        self.assertEqual(observed, expected_codes)


if __name__ == "__main__":
    unittest.main()
