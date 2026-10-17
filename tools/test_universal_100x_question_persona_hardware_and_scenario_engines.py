"""Tests for Universal 10x/100x combinatorial question, persona, industry, hardware, and ingestion pipeline engines."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _path in (_REPOSITORY_ROOT / "src", _REPOSITORY_ROOT / "tools"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from universal_100x_question_persona_hardware_and_scenario_engines import (  # noqa: E402
    AUTONOMY_LEVEL_COUNT,
    BASE_PERSONA_COUNT,
    BASE_PIPELINE_QUESTION_TEMPLATES,
    BENCHMARK_REPORT_SCHEMA,
    COMPUTE_TIER_COUNT,
    ENGINE_COMPACT_CARD_CHECKLIST_FALLBACK,
    ENGINE_HIERARCHICAL_100X_TENSOR,
    ENGINE_SITUATIONAL_MATRIX_FALLBACK,
    ENGINE_TEN_STAGE_100X_INTERROGATOR,
    INTERROGATOR_ENGINE_IDS,
    LEGACY_SUBSTRATE_COUNT,
    MACRO_SECTOR_COUNT,
    MATRIX_ENGINE_IDS,
    MAX_CONTRACT_CARD_BYTES,
    PIPELINE_STAGE_COUNT,
    QUESTIONS_PER_PIPELINE_STAGE,
    SUB_SECTORS_PER_MACRO,
    TOTAL_ADDRESSABLE_SITUATIONAL_CELLS,
    TOTAL_DOMAIN_PIPELINE_QUESTIONS,
    TOTAL_HARDWARE_CONFIGS_100X,
    TOTAL_INDUSTRIES_100X,
    TOTAL_PERSONAS_100X,
    Pipeline100xQuestionInterrogatorOrchestrator,
    PipelineInterrogatorRequest,
    SituationalMatrixRequest,
    Universal100xPersonaIndustryHardwareOrchestrator,
    resolve_situational_cell,
    run_universal_100x_benchmark,
)


class Universal100xQuestionPersonaHardwareScenarioTests(unittest.TestCase):
    """Verify 7-layer ComponentEnvelope, 2,160,000 situational cells, 120,000 pipeline questions, and known-wrong controls."""

    def test_slot_family_1_dimensions_and_situational_cell_resolution(self) -> None:
        self.assertEqual(BASE_PERSONA_COUNT, 18)
        self.assertEqual(AUTONOMY_LEVEL_COUNT, 10)
        self.assertEqual(TOTAL_PERSONAS_100X, 180)
        self.assertEqual(MACRO_SECTOR_COUNT, 12)
        self.assertEqual(SUB_SECTORS_PER_MACRO, 10)
        self.assertEqual(TOTAL_INDUSTRIES_100X, 120)
        self.assertEqual(COMPUTE_TIER_COUNT, 10)
        self.assertEqual(LEGACY_SUBSTRATE_COUNT, 10)
        self.assertEqual(TOTAL_HARDWARE_CONFIGS_100X, 100)
        self.assertEqual(TOTAL_ADDRESSABLE_SITUATIONAL_CELLS, 2_160_000)

        cell_first = resolve_situational_cell(0, 0, 0)
        cell_last = resolve_situational_cell(179, 119, 99)
        self.assertEqual(cell_first.cell_linear_index, 0)
        self.assertEqual(cell_last.cell_linear_index, 2_159_999)
        self.assertEqual(cell_first.memory_ceiling_mb, 2048)
        self.assertEqual(cell_first.required_encoding_transcoder, "ebcdic_cp037_to_utf8_comp3_unpacker")

        orch = Universal100xPersonaIndustryHardwareOrchestrator()
        res = orch.handle(SituationalMatrixRequest(request_id="test-matrix-1", sample_cell_count=30))
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, ENGINE_HIERARCHICAL_100X_TENSOR)
        self.assertEqual(res.total_addressable_cells, 2_160_000)
        self.assertEqual(len(res.sampled_cells), 30)
        self.assertTrue(res.trace.engine_dispatched)

    def test_slot_family_1_fallback_chain_and_carrier_refusal(self) -> None:
        orch = Universal100xPersonaIndustryHardwareOrchestrator()
        fallback_res = orch.handle(
            SituationalMatrixRequest(
                request_id="test-matrix-fallback",
                sample_cell_count=12,
                simulate_primary_deferral=True,
                simulate_secondary_deferral=True,
                simulate_tertiary_deferral=True,
            )
        )
        self.assertTrue(fallback_res.succeeded)
        self.assertEqual(fallback_res.selected_engine, ENGINE_SITUATIONAL_MATRIX_FALLBACK)
        self.assertEqual(fallback_res.attempted_engines, MATRIX_ENGINE_IDS)

        bad_carrier = orch.handle(SituationalMatrixRequest(request_id="bad-carrier", sample_cell_count=0))
        self.assertFalse(bad_carrier.succeeded)
        self.assertEqual(bad_carrier.trace.refused_by, "carrier")
        self.assertIsNotNone(bad_carrier.refusal)
        self.assertEqual(bad_carrier.refusal.code, "invalid_situational_matrix_carrier")

    def test_slot_family_2_pipeline_interrogator_and_compact_cards(self) -> None:
        self.assertEqual(PIPELINE_STAGE_COUNT, 10)
        self.assertEqual(QUESTIONS_PER_PIPELINE_STAGE, 100)
        self.assertEqual(BASE_PIPELINE_QUESTION_TEMPLATES, 1_000)
        self.assertEqual(TOTAL_DOMAIN_PIPELINE_QUESTIONS, 120_000)

        orch = Pipeline100xQuestionInterrogatorOrchestrator()
        res = orch.handle(PipelineInterrogatorRequest(request_id="test-interrogator-1"))
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, ENGINE_TEN_STAGE_100X_INTERROGATOR)
        self.assertEqual(res.total_domain_questions, 120_000)
        self.assertEqual(len(res.sampled_questions), 20)
        self.assertEqual(len(res.compiled_bundles), 12)
        self.assertLessEqual(res.max_contract_card_bytes, MAX_CONTRACT_CARD_BYTES)
        self.assertTrue(res.all_verifiers_reject_counterexamples)

        for bundle in res.compiled_bundles:
            self.assertLessEqual(bundle.contract_card_bytes, MAX_CONTRACT_CARD_BYTES)
            self.assertIn("# AGENTS.md", bundle.agents_md)
            self.assertIn("# RULES.md", bundle.rules_md)
            self.assertIn("# MEMORY.md", bundle.memory_md)
            self.assertTrue(bundle.verifier_passes_valid)
            self.assertTrue(bundle.verifier_rejects_counterexample)

    def test_slot_family_2_fallback_chain_and_carrier_refusal(self) -> None:
        orch = Pipeline100xQuestionInterrogatorOrchestrator()
        fallback_res = orch.handle(
            PipelineInterrogatorRequest(
                request_id="test-interrogator-fallback",
                simulate_primary_deferral=True,
                simulate_secondary_deferral=True,
                simulate_tertiary_deferral=True,
            )
        )
        self.assertTrue(fallback_res.succeeded)
        self.assertEqual(fallback_res.selected_engine, ENGINE_COMPACT_CARD_CHECKLIST_FALLBACK)
        self.assertEqual(fallback_res.attempted_engines, INTERROGATOR_ENGINE_IDS)

        bad_carrier = orch.handle(PipelineInterrogatorRequest(request_id="bad-interrogator", producer_id="   "))
        self.assertFalse(bad_carrier.succeeded)
        self.assertEqual(bad_carrier.trace.refused_by, "carrier")
        self.assertIsNotNone(bad_carrier.refusal)
        self.assertEqual(bad_carrier.refusal.code, "invalid_pipeline_interrogator_carrier")

    def test_known_wrong_controls_and_30_scenario_benchmark(self) -> None:
        matrix_orch = Universal100xPersonaIndustryHardwareOrchestrator()
        interrogator_orch = Pipeline100xQuestionInterrogatorOrchestrator()

        # Control 1: GPU FP16 on 2GB CPU-only edge node
        r1 = matrix_orch.handle(
            SituationalMatrixRequest(
                request_id="kw-gpu-edge",
                requested_model_precision="FP16_WEIGHTS",
                target_compute_tier_id="raspberry_pi_4_2gb_armv8",
            )
        )
        self.assertFalse(r1.succeeded)
        self.assertEqual(r1.trace.refused_by, "preflight")
        self.assertEqual(r1.refusal.code, "gpu_fp16_exceeds_edge_memory_and_device_ceiling")

        # Control 2: Cloud network egress inside air-gapped SCIF
        r2 = matrix_orch.handle(
            SituationalMatrixRequest(
                request_id="kw-scif-egress",
                target_compute_tier_id="air_gapped_scif_workstation",
                attempt_cloud_network_egress=True,
            )
        )
        self.assertFalse(r2.succeeded)
        self.assertEqual(r2.trace.refused_by, "preflight")
        self.assertEqual(r2.refusal.code, "network_egress_forbidden_in_air_gapped_scif")

        # Control 3: Naive UTF-8 decode on EBCDIC CP037 mainframe records
        r3 = matrix_orch.handle(
            SituationalMatrixRequest(
                request_id="kw-ebcdic-utf8",
                target_compute_tier_id="legacy_ibm_zos_cobol_db2_ebcdic",
                target_legacy_substrate_id="ebcdic_cp037_vsam_copybook",
                attempt_naive_utf8_on_ebcdic=True,
            )
        )
        self.assertFalse(r3.succeeded)
        self.assertEqual(r3.trace.refused_by, "preflight")
        self.assertEqual(r3.refusal.code, "ebcdic_cp037_naive_utf8_decode_corruption")

        # Control 4: Unverified or oversized situational card promotion
        r4 = interrogator_orch.handle(
            PipelineInterrogatorRequest(
                request_id="kw-oversized-card",
                custom_card_override="X" * (MAX_CONTRACT_CARD_BYTES + 128),
            )
        )
        self.assertFalse(r4.succeeded)
        self.assertEqual(r4.trace.refused_by, "preflight")
        self.assertEqual(r4.refusal.code, "unverified_or_oversized_situational_card_refused")

        report = run_universal_100x_benchmark()
        self.assertEqual(report["schema"], BENCHMARK_REPORT_SCHEMA)
        bench = report["extreme_30_scenario_benchmark"]
        self.assertEqual(bench["scenarios_evaluated"], 30)
        self.assertEqual(bench["baltor_100x_situational_matrix_router"]["task_pass_rate_pct"], 100.0)
        self.assertEqual(bench["baltor_100x_situational_matrix_router"]["memory_violation_rate_pct"], 0.0)
        self.assertGreater(
            bench["baltor_100x_situational_matrix_router"]["task_pass_rate_pct"],
            bench["one_size_fits_all_generic_agent_without_baltor"]["task_pass_rate_pct"],
        )
        for probe in report["known_wrong_refusal_probes"]:
            self.assertTrue(probe["refused"])
            self.assertEqual(probe["layer"], "preflight")


if __name__ == "__main__":
    unittest.main()
