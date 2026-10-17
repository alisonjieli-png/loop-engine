"""Unit tests for entity linking, record deduplication, messy data cleaning, and extended AI/ML competition benchmarks."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
_TOOLS_ROOT = _REPO_ROOT / "tools"
for _p in (_SRC_ROOT, _TOOLS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from entity_dedup_messy_data_and_ml_benchmarks import (  # noqa: E402
    ARCHETYPE_AMES_HOUSING,
    ARCHETYPE_DRIVENDATA_IMBALANCED,
    ARCHETYPE_KDD_GRAPH_LINK,
    ARCHETYPE_NEURIPS_CALIBRATION,
    ARCHETYPE_RECSYS_COLD_START,
    ARCHETYPE_SPACESHIP_TITANIC,
    CLEANING_ENGINES,
    ENGINE_CLEANING_WITH_BALTOR,
    ENGINE_CLEANING_WITHOUT_BALTOR,
    ENGINE_ENTITY_BALTOR_RESOLVER,
    ENGINE_ENTITY_HYBRID_LINKER,
    ENGINE_ENTITY_LSH_BLOCKER,
    ENGINE_ENTITY_NAIVE_WITHOUT_BALTOR,
    ENGINE_ML_WITH_BALTOR,
    ENGINE_ML_WITHOUT_BALTOR,
    ENTITY_DEDUP_ENGINES,
    EXTENDED_ML_ENGINES,
    ML_COMPETITION_ARCHETYPES,
    SLOT_ENTITY_DEDUP,
    SLOT_EXTENDED_ML,
    SLOT_MESSY_CLEANING,
    ComponentEnvelope,
    benchmark_entity_linking_and_deduplication,
    benchmark_extended_ai_ml_competitions,
    benchmark_messy_data_cleaning,
    run_all_benchmarks,
    verify_known_wrong_controls,
)
from loop_engine.core.engines.envelope import COVERAGE_LAYERS  # noqa: E402


class EntityDedupMessyDataAndMlBenchmarksTest(unittest.TestCase):
    """Verifies Tracks 1, 2, 3, the 7-layer ComponentEnvelope, and known-wrong controls."""

    def test_seven_layer_component_envelope_handshake_and_account_guards(self) -> None:
        env = ComponentEnvelope(SLOT_ENTITY_DEDUP, ENTITY_DEDUP_ENGINES)
        bad_engine = env.execute("unregistered_engine", {"records": ()}, lambda req: {})
        self.assertFalse(bad_engine.ok)
        self.assertIsNotNone(bad_engine.refusal)
        self.assertEqual(bad_engine.refusal.code, "unsupported_engine_id")
        self.assertEqual(bad_engine.layers_verified, COVERAGE_LAYERS)

        blank_account = env.execute(
            ENGINE_ENTITY_BALTOR_RESOLVER,
            {"records": ()},
            lambda req: {},
            account_id="   ",
        )
        self.assertFalse(blank_account.ok)
        self.assertIsNotNone(blank_account.refusal)
        self.assertEqual(blank_account.refusal.code, "handshake_or_account_refused")

    def test_track1_entity_linking_and_record_deduplication(self) -> None:
        summary = benchmark_entity_linking_and_deduplication()
        self.assertEqual(summary["slot_id"], SLOT_ENTITY_DEDUP)
        self.assertEqual(summary["layers_verified"], COVERAGE_LAYERS)

        engines = summary["engines"]
        naive = engines[ENGINE_ENTITY_NAIVE_WITHOUT_BALTOR]
        lsh = engines[ENGINE_ENTITY_LSH_BLOCKER]
        hybrid = engines[ENGINE_ENTITY_HYBRID_LINKER]
        baltor = engines[ENGINE_ENTITY_BALTOR_RESOLVER]

        self.assertEqual(naive["candidate_reduction_ratio"], 0.0)
        self.assertEqual(naive["pairwise_f1"], 0.0)
        self.assertEqual(naive["cluster_ari"], 0.0)

        self.assertGreater(lsh["candidate_reduction_ratio"], 0.90)
        self.assertGreater(lsh["pairwise_f1"], 0.80)
        self.assertGreaterEqual(hybrid["pairwise_f1"], lsh["pairwise_f1"])

        self.assertGreater(baltor["candidate_reduction_ratio"], 0.90)
        self.assertEqual(baltor["pairwise_precision"], 1.0)
        self.assertEqual(baltor["pairwise_recall"], 1.0)
        self.assertEqual(baltor["pairwise_f1"], 1.0)
        self.assertEqual(baltor["cluster_ari"], 1.0)

        datasets = summary["datasets"]
        for ds_id in (
            "company_vendor_names",
            "bibliographic_records",
            "product_skus_units",
            "cross_lingual_transliterations",
        ):
            ds_metrics = datasets[ds_id]
            self.assertEqual(ds_metrics["without_baltor_f1"], 0.0)
            self.assertEqual(ds_metrics["with_baltor_f1"], 1.0)
            self.assertEqual(ds_metrics["with_baltor_ari"], 1.0)
            self.assertGreaterEqual(ds_metrics["candidate_reduction_ratio"], 0.65)

    def test_track2_messy_data_cleaning_and_schema_reconciliation(self) -> None:
        cleaning = benchmark_messy_data_cleaning()
        self.assertEqual(cleaning["slot_id"], SLOT_MESSY_CLEANING)
        self.assertEqual(cleaning["layers_verified"], COVERAGE_LAYERS)

        without_b = cleaning["without_baltor"]
        with_b = cleaning["with_baltor"]
        self.assertEqual(without_b["engine_id"], ENGINE_CLEANING_WITHOUT_BALTOR)
        self.assertEqual(with_b["engine_id"], ENGINE_CLEANING_WITH_BALTOR)

        self.assertLess(without_b["overall_accuracy"], 0.25)
        self.assertEqual(with_b["overall_accuracy"], 1.0)

        for challenge in (
            "mixed_locale_currencies",
            "ambiguous_iso_us_eu_timestamps",
            "mojibake_utf8_cp1252_repair",
            "unit_normalization_mass",
            "duplicate_pk_conflict_resolution",
            "referential_integrity_enforcement",
        ):
            self.assertEqual(with_b["challenge_scores"][challenge], 1.0)
            self.assertGreater(
                with_b["challenge_scores"][challenge],
                without_b["challenge_scores"][challenge],
            )

    def test_track3_extended_ai_ml_competitions(self) -> None:
        ml = benchmark_extended_ai_ml_competitions()
        self.assertEqual(ml["slot_id"], SLOT_EXTENDED_ML)
        self.assertEqual(ml["layers_verified"], COVERAGE_LAYERS)

        archetypes = ml["archetypes"]
        self.assertEqual(tuple(archetypes.keys()), ML_COMPETITION_ARCHETYPES)

        # 1. Spaceship Titanic (GroupKFold classification)
        st = archetypes[ARCHETYPE_SPACESHIP_TITANIC]
        self.assertGreater(st["with_baltor"]["score"], st["without_baltor"]["score"])
        self.assertLess(st["with_baltor"]["cv_to_holdout_gap"], st["without_baltor"]["cv_to_holdout_gap"])
        self.assertTrue(st["with_baltor"]["group_leak_free"])

        # 2. Ames Housing (RMSLE lower is better)
        ames = archetypes[ARCHETYPE_AMES_HOUSING]
        self.assertLess(ames["with_baltor"]["score"], ames["without_baltor"]["score"])
        self.assertTrue(ames["with_baltor"]["oof_target_encoding"])

        # 3. DrivenData Public Health Imbalanced (macro-F1 higher is better)
        dd = archetypes[ARCHETYPE_DRIVENDATA_IMBALANCED]
        self.assertGreater(dd["with_baltor"]["score"], dd["without_baltor"]["score"])
        self.assertGreater(dd["with_baltor"]["minority_class_recall"], dd["without_baltor"]["minority_class_recall"])

        # 4. KDD Cup Entity Graph Link Prediction (Hits@50 higher is better)
        kdd = archetypes[ARCHETYPE_KDD_GRAPH_LINK]
        self.assertGreater(kdd["with_baltor"]["score"], kdd["without_baltor"]["score"])
        self.assertGreater(kdd["with_baltor"]["roc_auc"], kdd["without_baltor"]["roc_auc"])

        # 5. NeurIPS Uncertainty Calibrated Prediction (ECE & Brier lower is better)
        nips = archetypes[ARCHETYPE_NEURIPS_CALIBRATION]
        self.assertLess(nips["with_baltor"]["score"], nips["without_baltor"]["score"])
        self.assertLess(nips["with_baltor"]["brier_score"], nips["without_baltor"]["brier_score"])

        # 6. RecSys Cold-Start Hybrid Ranking (NDCG@10 higher is better)
        recsys = archetypes[ARCHETYPE_RECSYS_COLD_START]
        self.assertGreater(recsys["with_baltor"]["score"], recsys["without_baltor"]["score"])
        self.assertGreater(
            recsys["with_baltor"]["cold_item_recall_at_10"],
            recsys["without_baltor"]["cold_item_recall_at_10"],
        )

    def test_known_wrong_controls_refuse_bad_inputs(self) -> None:
        controls = verify_known_wrong_controls()
        self.assertEqual(
            controls["transitive_merge_explosion_control"]["refusal_code"],
            "transitive_merge_explosion_refused",
        )
        self.assertEqual(
            controls["locale_currency_sign_inversion_control"]["refusal_code"],
            "locale_currency_sign_or_scale_inversion_refused",
        )
        self.assertEqual(
            controls["train_test_target_leakage_control"]["refusal_code"],
            "train_test_target_or_group_leakage_refused",
        )
        self.assertEqual(
            controls["uncalibrated_probability_control"]["refusal_code"],
            "uncalibrated_probability_ece_refused",
        )

        # Also verify out-of-bounds probability refusal
        full_suite = run_all_benchmarks()
        self.assertIn("track1_entity_linking_and_deduplication", full_suite)
        self.assertIn("track2_messy_data_cleaning", full_suite)
        self.assertIn("track3_extended_ai_ml_competitions", full_suite)
        self.assertIn("known_wrong_controls", full_suite)


if __name__ == "__main__":
    unittest.main()
