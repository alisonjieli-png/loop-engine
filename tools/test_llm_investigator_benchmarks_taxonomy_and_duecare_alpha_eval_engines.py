"""Unit tests for 24-Benchmark LLM Investigator Taxonomy, Ecological Gap Matrix & DueCare-Alpha Evaluation Engine Suite."""

from __future__ import annotations

import unittest

from tools.llm_investigator_benchmarks_taxonomy_and_duecare_alpha_eval_engines import (
    BENCHMARK_TAXONOMY_CATALOG,
    DUECARE_ALPHA_SIX_ARMS,
    INVESTIGATIVE_REALISM_DIMENSIONS,
    DueCareAlphaSixArmCounterfactualEvaluatorEngine,
    LLMInvestigatorBenchmarkTaxonomyAndGapAnalyzerEngine,
    ThinComponentAdapter,
    run_all_llm_investigator_taxonomy_and_duecare_alpha_evaluations,
)


def test_benchmark_taxonomy_and_gap_analyzer_engine() -> None:
    engine = LLMInvestigatorBenchmarkTaxonomyAndGapAnalyzerEngine()
    assert engine.preflight().ready is True
    assert engine.recovery_policy().maximum_automatic_attempts == 3

    adapter = ThinComponentAdapter(engine, "llm_investigator_benchmark_taxonomy_and_gap_analyzer_slot")
    assert adapter.inspect_contract()["slot_id"] == "llm_investigator_benchmark_taxonomy_and_gap_analyzer_slot"

    res = adapter.execute({})
    assert res["status"] == "ok"
    assert adapter.verify_receipt(res) is True

    summary = res["summary"]
    assert summary["total_benchmarks_cataloged"] == 24
    assert summary["family_count"] == 6
    assert summary["existing_academic_benchmark_count"] == 22
    assert summary["duecare_suite_benchmark_count"] == 2
    assert summary["investigative_realism_dimension_count"] == 6
    assert summary["existing_academic_mean_coverage_pct"] == 18.4
    assert summary["duecare_alpha_mean_coverage_pct"] == 97.5
    assert summary["coverage_gap_delta_pct"] == 79.1
    assert set(INVESTIGATIVE_REALISM_DIMENSIONS) == set(res["dimension_averages_duecare"].keys())

    # Known-wrong control 1: fictional whodunit claimed as real regulatory investigation proof refused
    ref1 = adapter.execute({"claim_fictional_whodunit_as_regulatory_proof": True})
    assert ref1["status"] == "refused"
    assert ref1["error"]["code"] == "fictional_whodunit_claimed_as_real_regulatory_investigation_refused"
    assert engine.preflight({"claim_fictional_whodunit_as_regulatory_proof": True}).ready is False

    # Known-wrong control 2: missing matched benign twin control refused
    ref2 = adapter.execute({"omit_matched_benign_twin_control": True})
    assert ref2["status"] == "refused"
    assert ref2["error"]["code"] == "missing_matched_benign_twin_control_refused"


def test_duecare_alpha_six_arm_counterfactual_evaluator_engine() -> None:
    engine = DueCareAlphaSixArmCounterfactualEvaluatorEngine()
    assert engine.preflight().ready is True
    assert engine.recovery_policy().maximum_automatic_attempts == 3

    adapter = ThinComponentAdapter(engine, "duecare_alpha_six_arm_counterfactual_evaluator_slot")
    res = adapter.execute({})
    assert res["status"] == "ok"
    assert adapter.verify_receipt(res) is True

    summary = res["summary"]
    assert summary["arm_count"] == 6
    assert summary["arm_ids"] == (
        "A0_model_only",
        "A1_length_placebo",
        "A2_normative_pack",
        "A3_entity_evidence_graph",
        "A4_competing_hypothesis_verifier",
        "A5_bayesian_calibrated_router",
    )
    assert summary["constant_token_budget"] == 4096
    assert summary["a5_concerning_recall"] > 0.95
    assert summary["a5_benign_twin_false_alarm_rate"] <= 0.005
    assert summary["placebo_a1_minus_a0_delta"] < 0.02

    # Known-wrong control 3: unequal token budget or missing A1 length placebo refused
    ref3 = adapter.execute({"unequal_token_budget": True})
    assert ref3["status"] == "refused"
    assert ref3["error"]["code"] == "unequal_token_budget_without_a1_placebo_refused"
    assert engine.preflight({"unequal_token_budget": True}).ready is False

    # Known-wrong control 4: accusatory tier T5 emission refused
    ref4 = adapter.execute({"evidence_tier": "T5_accusatory"})
    assert ref4["status"] == "refused"
    assert ref4["error"]["code"] == "accusatory_tier_t5_emission_refused"
    assert engine.preflight({"evidence_tier": "T5_accusatory"}).ready is False


def test_end_to_end_taxonomy_and_duecare_alpha_suite() -> None:
    suite = run_all_llm_investigator_taxonomy_and_duecare_alpha_evaluations()
    assert suite["status"] == "ok"
    assert suite["all_receipts_verified"] is True
    assert len(BENCHMARK_TAXONOMY_CATALOG) == 24
    assert len(DUECARE_ALPHA_SIX_ARMS) == 6


class TestLLMInvestigatorBenchmarksAndDueCareAlpha(unittest.TestCase):
    def test_taxonomy_and_gap_analyzer(self) -> None:
        test_benchmark_taxonomy_and_gap_analyzer_engine()

    def test_six_arm_counterfactual_evaluator(self) -> None:
        test_duecare_alpha_six_arm_counterfactual_evaluator_engine()

    def test_end_to_end_suite(self) -> None:
        test_end_to_end_taxonomy_and_duecare_alpha_suite()


if __name__ == "__main__":
    unittest.main()
