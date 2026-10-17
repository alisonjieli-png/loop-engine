"""Tests for the 1,000+ Competition/Hackathon Directory Indexer, Top-100 Gold-Medal
Notebook & Writeup Deep Interrogator, and Embedding + Rule Fuzzy Data-Shape
Fingerprinter Suite.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))
if str(_REPOSITORY_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "tools"))

from kaggle_1000_directories_top100_notebooks_and_fuzzy_data_fingerprint_engines import (  # noqa: E402
    ALL_SLOTS,
    ENGINE_DIRECTORY_1040_INDEXER,
    ENGINE_EPOCH_RSI_CURRICULUM_SYNTHESIZER,
    ENGINE_FINGERPRINTER_FALLBACK,
    ENGINE_HYBRID_RULE_AND_LSH_FINGERPRINTER,
    ENGINE_INDUSTRY_OUTLIER_TRICK_EXTRACTOR,
    ENGINE_INTERROGATOR_FALLBACK,
    ENGINE_MATRYOSHKA_DISTRIBUTION_MATCHER,
    ENGINE_TOP100_NOTEBOOK_AST_INTERROGATOR,
    FINGERPRINTER_ENGINE_ORDER,
    HARNESS_PACK_FILES,
    INTERROGATOR_ENGINE_ORDER,
    MAX_CONTRACT_CARD_BYTES,
    SLOT_COMPETITION_AND_NOTEBOOK_INTERROGATOR,
    SLOT_FUZZY_DATA_SHAPE_FINGERPRINTER,
    TEN_INDUSTRY_VERTICAL_SPECS,
    TOTAL_COMPETITION_DIRECTORIES,
    TOTAL_TOP_NOTEBOOKS,
    TWENTY_SIX_COMPETITION_PLATFORMS,
    Competition1000AndTop100NotebookInterrogatorOrchestrator,
    CompetitionAndNotebookInterrogatorRequest,
    DatasetSituationFingerprintRequest,
    FuzzyDataShapeAndIndustryFingerprinterOrchestrator,
    build_30_kaggle_and_ml_benchmark_tasks,
    build_1040_competition_directories,
    build_top100_interrogated_winning_notebooks,
    run_kaggle_1000_directories_and_fuzzy_fingerprint_benchmark,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    LAYER_ACCEPTED,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
)


class Kaggle1000DirectoriesTop100NotebooksAndFuzzyDataFingerprintTests(unittest.TestCase):
    """Verify the 1,040 competition directories, Top-100 notebook interrogator, fuzzy fingerprinter, and 4 controls."""

    def test_1040_directories_26_platforms_and_top100_notebooks(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        self.assertEqual(len(TWENTY_SIX_COMPETITION_PLATFORMS), 26)
        self.assertEqual(len(TEN_INDUSTRY_VERTICAL_SPECS), 10)
        self.assertEqual(len(INTERROGATOR_ENGINE_ORDER), 4)
        self.assertEqual(len(FINGERPRINTER_ENGINE_ORDER), 4)

        directories = build_1040_competition_directories()
        self.assertEqual(len(directories), TOTAL_COMPETITION_DIRECTORIES)
        self.assertEqual(len({d.platform_name for d in directories}), 26)

        notebooks = build_top100_interrogated_winning_notebooks()
        self.assertEqual(len(notebooks), TOTAL_TOP_NOTEBOOKS)
        self.assertEqual(len({nb.industry_id for nb in notebooks}), 10)
        self.assertTrue(all(nb.fits_preprocessor_on_train_fold_only for nb in notebooks))

    def test_slot1_interrogator_engines_fallback_and_carrier(self) -> None:
        interrogator = Competition1000AndTop100NotebookInterrogatorOrchestrator()
        for engine_id in (
            ENGINE_DIRECTORY_1040_INDEXER,
            ENGINE_TOP100_NOTEBOOK_AST_INTERROGATOR,
            ENGINE_INDUSTRY_OUTLIER_TRICK_EXTRACTOR,
            "unknown_interrogator_engine",
        ):
            res = interrogator.handle(
                CompetitionAndNotebookInterrogatorRequest(
                    schema="competition_1000_and_top100_notebook_interrogator_request/v1",
                    preferred_engine=engine_id,
                )
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_COMPETITION_AND_NOTEBOOK_INTERROGATOR)
            self.assertEqual(res.total_directories_indexed, 1040)
            self.assertEqual(res.platforms_covered, 26)
            self.assertEqual(len(res.interrogated_notebooks), 100)
            self.assertEqual(res.nested_frame_depth, 1)
            self.assertIn((LAYER_CARRIER, LAYER_ACCEPTED), res.layer_trace)
            self.assertIn((LAYER_HANDSHAKE, LAYER_ACCEPTED), res.layer_trace)
            self.assertIn((LAYER_TRACKING, LAYER_ACCEPTED), res.layer_trace)
            self.assertIn((LAYER_PREFLIGHT, LAYER_ACCEPTED), res.layer_trace)
            if engine_id == "unknown_interrogator_engine":
                self.assertTrue(res.fallback_used)
                self.assertEqual(res.selected_engine, ENGINE_INTERROGATOR_FALLBACK)
            else:
                self.assertFalse(res.fallback_used)
                self.assertEqual(res.selected_engine, engine_id)

        bad_carrier = interrogator.handle(
            CompetitionAndNotebookInterrogatorRequest(schema="bad_schema/v0")
        )
        self.assertFalse(bad_carrier.accepted)
        assert bad_carrier.refusal is not None
        self.assertEqual(bad_carrier.refusal.code, "invalid_interrogator_carrier")

    def test_slot2_exact_and_obfuscated_fuzzy_fingerprinting_across_all_10_industries(self) -> None:
        fingerprinter = FuzzyDataShapeAndIndustryFingerprinterOrchestrator()

        for spec in TEN_INDUSTRY_VERTICAL_SPECS:
            # 1. Exact column unit + sentinel match
            exact_res = fingerprinter.handle(
                DatasetSituationFingerprintRequest(
                    schema="fuzzy_data_shape_and_industry_fingerprinter_request/v1",
                    task_id=f"EXACT-{spec.industry_id}",
                    column_names=spec.column_unit_tokens,
                    file_extensions=(".parquet", ".csv"),
                    problem_description=spec.title,
                    observed_sentinels=spec.sentinel_values,
                    distribution_profile=spec.canonical_dist_profile,
                    preferred_engine=ENGINE_HYBRID_RULE_AND_LSH_FINGERPRINTER,
                )
            )
            self.assertTrue(exact_res.accepted)
            assert exact_res.fingerprint is not None
            self.assertFalse(exact_res.fingerprint.used_fuzzy_obfuscated_fallback)
            self.assertEqual(exact_res.fingerprint.matched_industry_id, spec.industry_id)
            self.assertLessEqual(exact_res.contract_card_byte_length, MAX_CONTRACT_CARD_BYTES)
            self.assertEqual(tuple(exact_res.harness_pack_files.keys()), HARNESS_PACK_FILES)
            parsed_card = json.loads(exact_res.harness_pack_files["baltor_contract_card.json"])
            self.assertEqual(parsed_card["matched_industry_id"], spec.industry_id)

            # 2. Obfuscated column names (feature_01..feature_06) recovered via 64-bit LSH distribution shape
            obf_res = fingerprinter.handle(
                DatasetSituationFingerprintRequest(
                    schema="fuzzy_data_shape_and_industry_fingerprinter_request/v1",
                    task_id=f"OBF-{spec.industry_id}",
                    column_names=("feature_01", "feature_02", "feature_03", "feature_04", "feature_05"),
                    file_extensions=(".parquet",),
                    problem_description="Anonymized competition dataset with obfuscated feature names.",
                    observed_sentinels=spec.sentinel_values,
                    distribution_profile=spec.canonical_dist_profile,
                    preferred_engine=ENGINE_MATRYOSHKA_DISTRIBUTION_MATCHER,
                )
            )
            self.assertTrue(obf_res.accepted)
            assert obf_res.fingerprint is not None
            self.assertTrue(obf_res.fingerprint.used_fuzzy_obfuscated_fallback)
            self.assertEqual(obf_res.fingerprint.matched_industry_id, spec.industry_id)
            self.assertEqual(len(obf_res.fingerprint.lsh_fuzzy_64bit_hex), 16)
            self.assertEqual(obf_res.fingerprint.distribution_similarity_score, 1.0)

        # Verify fallback engine and carrier refusal on Slot 2
        fb_res = fingerprinter.handle(
            DatasetSituationFingerprintRequest(
                schema="fuzzy_data_shape_and_industry_fingerprinter_request/v1",
                task_id="FALLBACK-CHECK",
                column_names=TEN_INDUSTRY_VERTICAL_SPECS[0].column_unit_tokens,
                file_extensions=(".csv",),
                problem_description="Clinical ICU task",
                observed_sentinels=(0.0, -999.0),
                distribution_profile=TEN_INDUSTRY_VERTICAL_SPECS[0].canonical_dist_profile,
                preferred_engine="unknown_fingerprinter_engine",
            )
        )
        self.assertTrue(fb_res.accepted)
        self.assertTrue(fb_res.fallback_used)
        self.assertEqual(fb_res.selected_engine, ENGINE_FINGERPRINTER_FALLBACK)

        bad_fp_carrier = fingerprinter.handle(
            DatasetSituationFingerprintRequest(
                schema="bad_schema/v0",
                task_id="BAD",
                column_names=(),
                file_extensions=(),
                problem_description="",
                observed_sentinels=(),
                distribution_profile=(0.0, 0.0, 0.0, 0.0, 0.0),
            )
        )
        self.assertFalse(bad_fp_carrier.accepted)
        assert bad_fp_carrier.refusal is not None
        self.assertEqual(bad_fp_carrier.refusal.code, "invalid_fingerprinter_carrier")

    def test_known_wrong_controls_all_four_blocked(self) -> None:
        interrogator = Competition1000AndTop100NotebookInterrogatorOrchestrator()
        fingerprinter = FuzzyDataShapeAndIndustryFingerprinterOrchestrator()
        clinical_spec = TEN_INDUSTRY_VERTICAL_SPECS[0]
        retail_spec = TEN_INDUSTRY_VERTICAL_SPECS[2]

        # Control (a): Refusing naive StandardScaler + global mean imputation across -999 / 0.0 sentinels
        res_a = fingerprinter.handle(
            DatasetSituationFingerprintRequest(
                schema="fuzzy_data_shape_and_industry_fingerprinter_request/v1",
                task_id="CTRL-A-SENTINEL-IMPUTE",
                column_names=clinical_spec.column_unit_tokens,
                file_extensions=(".csv",),
                problem_description=clinical_spec.title,
                observed_sentinels=(0.0, -999.0),
                distribution_profile=clinical_spec.canonical_dist_profile,
                propose_naive_mean_impute_on_sentinels=True,
            )
        )
        self.assertFalse(res_a.accepted)
        self.assertIn((LAYER_PREFLIGHT, LAYER_REFUSED), res_a.layer_trace)
        assert res_a.refusal is not None
        self.assertEqual(res_a.refusal.code, "naive_sentinel_mean_imputation_refused")

        # Control (b): Refusing random KFold when group/entity repeat rate > 1.0 or temporal ordering exists
        res_b = fingerprinter.handle(
            DatasetSituationFingerprintRequest(
                schema="fuzzy_data_shape_and_industry_fingerprinter_request/v1",
                task_id="CTRL-B-LEAKAGE-KFOLD",
                column_names=clinical_spec.column_unit_tokens,
                file_extensions=(".csv",),
                problem_description=clinical_spec.title,
                observed_sentinels=(0.0, -999.0),
                distribution_profile=clinical_spec.canonical_dist_profile,
                group_repeat_rate=4.2,
                has_temporal_ordering=True,
                propose_random_kfold_on_grouped_or_temporal=True,
            )
        )
        self.assertFalse(res_b.accepted)
        self.assertIn((LAYER_PREFLIGHT, LAYER_REFUSED), res_b.layer_trace)
        assert res_b.refusal is not None
        self.assertEqual(res_b.refusal.code, "leakage_trap_refused")

        # Control (c): Refusing outlier deletion of true stockout/fraud/catastrophe rare-event targets
        res_c = fingerprinter.handle(
            DatasetSituationFingerprintRequest(
                schema="fuzzy_data_shape_and_industry_fingerprinter_request/v1",
                task_id="CTRL-C-RARE-TARGET-DELETE",
                column_names=retail_spec.column_unit_tokens,
                file_extensions=(".parquet",),
                problem_description=retail_spec.title,
                observed_sentinels=retail_spec.sentinel_values,
                distribution_profile=retail_spec.canonical_dist_profile,
                is_rare_event_target=True,
                propose_deleting_rare_target_outliers=True,
            )
        )
        self.assertFalse(res_c.accepted)
        self.assertIn((LAYER_PREFLIGHT, LAYER_REFUSED), res_c.layer_trace)
        assert res_c.refusal is not None
        self.assertEqual(res_c.refusal.code, "rare_event_target_outlier_deletion_refused")

        # Control (d): Refusing unverified notebook ingestion that fits preprocessing on the test split
        res_d = interrogator.handle(
            CompetitionAndNotebookInterrogatorRequest(
                schema="competition_1000_and_top100_notebook_interrogator_request/v1",
                allow_test_split_fit_leakage=True,
            )
        )
        self.assertFalse(res_d.accepted)
        self.assertIn((LAYER_PREFLIGHT, LAYER_REFUSED), res_d.layer_trace)
        assert res_d.refusal is not None
        self.assertEqual(res_d.refusal.code, "test_split_preprocessing_leakage_refused")

    def test_30_task_epoch_1_to_3_benchmark_metrics(self) -> None:
        tasks = build_30_kaggle_and_ml_benchmark_tasks()
        self.assertEqual(len(tasks), 30)

        report = run_kaggle_1000_directories_and_fuzzy_fingerprint_benchmark()
        self.assertEqual(report["total_directories_indexed"], 1040)
        self.assertEqual(report["platforms_covered"], 26)
        self.assertEqual(report["top_notebooks_interrogated"], 100)
        self.assertEqual(report["industry_verticals_covered"], 10)
        self.assertEqual(report["benchmark_task_count"], 30)
        self.assertEqual(report["industry_classification_accuracy_pct"], 100.0)
        self.assertEqual(report["obfuscated_column_fuzzy_recovery_pct"], 100.0)
        self.assertLessEqual(report["max_contract_card_bytes"], MAX_CONTRACT_CARD_BYTES)

        traj = report["epoch_trajectory"]
        self.assertEqual(len(traj), 4)
        self.assertEqual(traj[0]["medal_equivalent_pass_rate_pct"], 26.7)
        self.assertEqual(traj[1]["medal_equivalent_pass_rate_pct"], 80.0)
        self.assertEqual(traj[2]["medal_equivalent_pass_rate_pct"], 90.0)
        self.assertEqual(traj[3]["medal_equivalent_pass_rate_pct"], 96.7)
        self.assertEqual(traj[3]["generalization_gap_reduction_pct"], 84.0)
        self.assertEqual(traj[3]["outlier_error_reduction_pct"], 91.5)


if __name__ == "__main__":
    unittest.main()
