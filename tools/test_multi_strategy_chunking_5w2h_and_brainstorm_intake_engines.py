"""Tests and known-wrong controls for the Multi-Strategy & Seeded-Random-Boundary Content Chunking,
12-Dimension 5W2H/Causal/Interaction Intake Interrogator & Brainstorm-to-Feed/Tool/Component
Synthesizer Suite.
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

import multi_strategy_chunking_5w2h_and_brainstorm_intake_engines as intake  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class MultiStrategyChunking5W2HAndBrainstormIntakeTests(unittest.TestCase):
    """Verify 8-mode chunking, 12D 5W2H interrogation, component synthesis, benchmark, and 4 known-wrong controls."""

    def test_slot1_8mode_chunking_across_all_four_swappable_engines_and_seed_reproducibility(self) -> None:
        slot = intake.MultiStrategyAndRandomizedChunkingSlot()
        sample_doc = intake.BENCHMARK_CORPUS[0]

        for idx, engine_id in enumerate(intake.CHUNKING_ENGINE_ORDER):
            res = slot.chunk_document(
                sample_doc["doc_id"],
                sample_doc["content"],
                domain_systems=sample_doc["systems"],
                random_seed=20261017,
                request_id=f"test_chunk_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            out = res.output
            self.assertEqual(out["strategies_executed"], ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"])
            self.assertEqual(out["monte_carlo_passes"], 5)
            self.assertTrue(out["all_chunks_have_provenance_and_spans"])
            self.assertGreaterEqual(int(out["total_chunks"]), 40)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

        # Verify deterministic seed reproducibility vs distinct seed variation in M3
        res_seed_a1 = slot.chunk_document(
            sample_doc["doc_id"],
            sample_doc["content"],
            random_seed=20261017,
            request_id="repro_seed_a1",
        )
        res_seed_a2 = slot.chunk_document(
            sample_doc["doc_id"],
            sample_doc["content"],
            random_seed=20261017,
            request_id="repro_seed_a2",
        )
        res_seed_b = slot.chunk_document(
            sample_doc["doc_id"],
            sample_doc["content"],
            random_seed=99999991,
            request_id="repro_seed_b",
        )
        m3_a1 = [c["provenance_sha256"] for c in res_seed_a1.output["chunks_by_strategy"]["M3"]]
        m3_a2 = [c["provenance_sha256"] for c in res_seed_a2.output["chunks_by_strategy"]["M3"]]
        m3_b = [c["provenance_sha256"] for c in res_seed_b.output["chunks_by_strategy"]["M3"]]
        self.assertEqual(m3_a1, m3_a2)
        self.assertNotEqual(m3_a1, m3_b)

    def test_slot2_12d_5w2h_interrogator_and_6_file_component_synthesis(self) -> None:
        interrogator = intake.Deep5W2HCausalAndInteractionInterrogatorSlot()
        sample_doc = intake.BENCHMARK_CORPUS[1]

        for idx, engine_id in enumerate(intake.INTERROGATOR_ENGINE_ORDER):
            res = interrogator.interrogate_and_synthesize(
                sample_doc["doc_id"],
                sample_doc["content"],
                domain_systems=sample_doc["systems"],
                random_seed=20261017,
                request_id=f"test_interrogate_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            out = res.output
            self.assertEqual(tuple(out["dimensions_covered"]), intake.INTERROGATIVE_12_DIMENSIONS)
            self.assertEqual(len(out["dimensions_covered"]), 12)
            self.assertGreaterEqual(int(out["total_questions_generated"]), 3000)
            self.assertEqual(len(out["brainstormed_new_systems"]), 8)
            self.assertEqual(len(out["new_feed_protocols"]), 8)

            files = out["synthesized_files"]
            for expected_file in (
                "AGENTS.md",
                "RULES.md",
                "MEMORY.md",
                "SKILL.md",
                "baltor_contract_card.json",
                "feed_protocol_spec.json",
            ):
                self.assertIn(expected_file, files)
                self.assertTrue(len(files[expected_file]) > 0)

            self.assertTrue(out["contract_card_within_2048_bytes"])
            self.assertLessEqual(int(out["contract_card_bytes"]), 2048)
            card = json.loads(files["baltor_contract_card.json"])
            self.assertEqual(card["dimensions_count"], 12)
            self.assertEqual(card["strategies"], ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"])

    def test_benchmark_exceeds_12000_questions_and_99_4_percent_recall(self) -> None:
        bench = intake.run_multi_strategy_chunking_5w2h_benchmark()
        self.assertEqual(bench["corpus_documents_evaluated"], 4)
        self.assertEqual(bench["chunking_strategies_count"], 8)
        self.assertEqual(bench["interrogative_dimensions_count"], 12)

        without_b = bench["without_baltor_baseline"]
        self.assertEqual(without_b["engine_id"], intake.BASELINE_SINGLE_PASS_FIXED_WITHOUT_5W2H)
        self.assertEqual(without_b["cross_boundary_interaction_recall_pct"], "61.5%")
        self.assertEqual(without_b["idea_and_system_yield_multiplier"], "1.0x")

        with_b = bench["with_baltor_8mode_12d_intake"]
        self.assertEqual(with_b["engine_id"], intake.BALTOR_8MODE_PLUS_12D_5W2H_INTAKE)
        self.assertEqual(with_b["cross_boundary_interaction_recall_pct"], "99.4%")
        self.assertGreaterEqual(int(with_b["structured_questions_generated"]), 12000)
        self.assertEqual(with_b["valid_feed_and_component_synthesis_rate_pct"], "100.0%")
        self.assertTrue(with_b["all_cards_within_2048_bytes"])
        self.assertLessEqual(int(with_b["max_contract_card_bytes"]), 2048)

    def test_four_known_wrong_controls_refuse_before_engine_dispatch(self) -> None:
        kw = intake.run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"], msg=f"Control failed: {ctrl}")
            self.assertTrue(ctrl["refused_before_engine"])

        chunk_slot = intake.MultiStrategyAndRandomizedChunkingSlot()
        res_unseeded = chunk_slot.chunk_document(
            "doc_unseeded",
            "Line 1\nLine 2\nLine 3",
            random_seed=None,
            request_id="direct_unseeded_check",
            extra_payload={"unseeded_randomness": True},
        )
        self.assertFalse(res_unseeded.accepted)
        self.assertIsNotNone(res_unseeded.refusal)
        self.assertEqual(res_unseeded.refusal.code, "unseeded_random_chunking_refused")
        self.assertEqual(res_unseeded.layer_verdicts["preflight"], LAYER_REFUSED)


if __name__ == "__main__":
    unittest.main()
