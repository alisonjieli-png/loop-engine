"""Tests for scripts/recompute_cv_score.py. Effects: reads package files and starts the script with the current Python; writes nothing."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "recompute_cv_score.py"


def run(*arguments, stdin=None):
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], cwd=PACKAGE,
                              input=stdin, capture_output=True, text=True, timeout=120)
    return finished.returncode, json.loads(finished.stdout)


def one_file(rows, *arguments, header="id,fold,target,prediction"):
    """rows: (id, fold, label, prediction) in one predictions file."""
    text = header + "\n" + "".join(",".join(str(part) for part in row) + "\n" for row in rows)
    return run("--bundle", "-", *arguments, stdin=json.dumps({"predictions": text}))


def one_fold(labels, predictions):
    return [(f"r{index}", 0, label, prediction) for index, (label, prediction) in enumerate(zip(labels, predictions))]


class HandComputedMetrics(unittest.TestCase):
    """Each case is one fold, so the mean of fold scores equals the value worked out in the comment."""

    def assert_score(self, rows, metric, expected, *arguments):
        status, report = one_file(rows, "--metric", metric, "--claimed-score", f"{expected:.8f}", *arguments)
        self.assertEqual(status, 0, report)
        self.assertAlmostEqual(report["recomputed"]["mean"], expected, places=7)

    def test_roc_auc_counts_a_tie_as_one_half(self):
        # Positive scores 0.9 and 0.4, negative scores 0.9 and 0.1: pairs give 0.5 + 1 + 0 + 1 = 2.5 of 4.
        self.assert_score(one_fold([1, 0, 1, 0], [0.9, 0.9, 0.4, 0.1]), "roc_auc", 0.625)

    def test_log_loss(self):
        # (-ln 0.8 - ln 0.6) / 2
        self.assert_score(one_fold([1, 0], [0.8, 0.4]), "log_loss", (-math.log(0.8) - math.log(0.6)) / 2)

    def test_error_metrics(self):
        rows = one_fold([1, 2, 3], [2, 2, 5])
        self.assert_score(rows, "rmse", math.sqrt(5 / 3))   # squared errors 1, 0, 4
        self.assert_score(rows, "mae", 1.0)                 # absolute errors 1, 0, 2
        self.assert_score(rows, "r2", -1.5)                 # 1 - 5 / 2
        # log1p gives 0 and ln 4 for the labels, ln 2 and ln 4 for the predictions.
        self.assert_score(one_fold([0, 3], [1, 3]), "rmsle", math.log(2) / math.sqrt(2))

    def test_label_metrics(self):
        rows = one_fold(["cat", "dog", "owl", "dog"], ["cat", "owl", "owl", "dog"])
        self.assert_score(rows, "accuracy", 0.75)
        self.assert_score(rows, "balanced_accuracy", (1 + 0.5 + 1) / 3)   # recall of cat, dog and owl
        # One true positive, one false positive and one false negative.
        self.assert_score(one_fold([1, 1, 0, 0], [1, 0, 1, 0]), "f1", 0.5)

    def test_threshold_and_number_formats(self):
        rows = one_fold([1, 1, 0, 0], [0.7, 0.2, 0.6, 0.1])
        self.assert_score(rows, "accuracy", 0.5, "--threshold", "0.5")
        self.assert_score(rows, "f1", 0.5, "--threshold", "0.5")
        self.assert_score(one_fold([1, 0], ["1.0", "0.0"]), "accuracy", 1.0)
        self.assert_score(one_fold(["yes", "no", "yes"], [0.9, 0.3, 0.2]), "roc_auc", 0.5, "--positive-label", "yes")


class Claims(unittest.TestCase):
    def test_example_claim_that_matches_the_mean(self):
        status, report = run("--bundle", "examples/oof-bundle.json", "--metric", "roc_auc", "--claimed-score", "0.872")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["claim"]["tolerance"], 0.0005)
        self.assertEqual(report["claim"]["tolerance_source"], "claim_precision")
        self.assertEqual(len(report["folds"]), 5)

    def test_known_wrong_example_claim_is_refuted(self):
        status, report = run("--bundle", "examples/oof-bundle.json", "--metric", "roc_auc", "--claimed-score", "0.912")
        self.assertEqual(status, 1, report)
        self.assertEqual(report["failed_checks"], ["claim_differs"])
        self.assertAlmostEqual(report["claim"]["difference"], 0.0401, places=4)
        self.assertFalse(report["claim"]["within_tolerance"])
        self.assertTrue(report["hints"])

    def test_pooled_score_claimed_as_a_mean_gets_a_hint(self):
        status, report = run("--bundle", "examples/oof-bundle.json", "--metric", "roc_auc", "--claimed-score", "0.859")
        self.assertEqual(status, 1)
        self.assertIn("pooled", report["hints"][0])
        status, report = run("--bundle", "examples/oof-bundle.json", "--metric", "roc_auc", "--claimed-score", "0.859",
                             "--claim-kind", "pooled")
        self.assertEqual(status, 0, report)

    def test_hints_for_sign_squared_error_and_reversed_auc(self):
        rows = one_fold([1, 2, 3], [2, 2, 5])
        status, report = one_file(rows, "--metric", "rmse", "--claimed-score", "-1.2910")
        self.assertEqual(status, 1)
        self.assertIn("opposite sign", " ".join(report["hints"]))
        status, report = one_file(rows, "--metric", "rmse", "--claimed-score", "1.6667")
        self.assertIn("squared error", " ".join(report["hints"]))
        status, report = one_file(one_fold([1, 0, 1, 0], [0.9, 0.9, 0.4, 0.1]), "--metric", "roc_auc",
                                  "--claimed-score", "0.375")
        self.assertIn("1 minus", " ".join(report["hints"]))

    def test_fold_claims_and_an_explicit_tolerance(self):
        rows = [("a", 0, 1, 2), ("b", 0, 3, 3), ("c", 1, 5, 5), ("d", 1, 7, 9)]
        # Fold scores are 0.5 and 1.0; the fold claim 1.2 is 0.2 away.
        status, report = one_file(rows, "--metric", "mae", "--claimed-score", "0.75", "--claimed-fold", "0=0.5",
                                  "--claimed-fold", "1=1.2")
        self.assertEqual(status, 1)
        self.assertEqual(report["failed_checks"], ["fold_claims_differ"])
        status, report = one_file(rows, "--metric", "mae", "--claimed-score", "0.75", "--claimed-fold", "0=0.5",
                                  "--claimed-fold", "1=1.2", "--tolerance", "0.2")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["claim"]["tolerance_source"], "--tolerance")


class Coverage(unittest.TestCase):
    def test_separate_files_joined_by_id_with_own_column_names(self):
        bundle = {"predictions": "key,score\nk1,0.9\nk2,0.2\nk3,0.8\nk4,0.3\n",
                  "folds": "key,split\nk1,A\nk2,A\nk3,B\nk4,B\n",
                  "labels": "key,label\nk1,1\nk2,0\nk3,1\nk4,0\n"}
        status, report = run("--bundle", "-", "--metric", "roc_auc", "--claimed-score", "1.0", "--id-column", "key",
                             "--prediction-column", "score", "--fold-column", "split", "--label-column", "label",
                             stdin=json.dumps(bundle))
        self.assertEqual(status, 0, report)
        self.assertEqual(report["coverage"]["rows_expected_from"], "folds")

    def test_missing_and_unknown_predictions_fail_even_when_the_claim_matches(self):
        bundle = {"predictions": "id,prediction\nk1,0.9\nk2,0.2\nk3,0.8\nk4,0.3\nz9,0.5\n",
                  "folds": "id,fold\nk1,0\nk2,0\nk3,1\nk4,1\nk5,1\n",
                  "labels": "id,target\nk1,1\nk2,0\nk3,1\nk4,0\nk5,0\n"}
        status, report = run("--bundle", "-", "--metric", "roc_auc", "--claimed-score", "1.0",
                             stdin=json.dumps(bundle))
        self.assertEqual(status, 1)
        self.assertEqual(sorted(report["failed_checks"]), ["predictions_for_unknown_rows", "rows_without_prediction"])
        self.assertTrue(report["claim"]["within_tolerance"])

    def test_a_fold_missing_from_the_predictions_is_found_through_the_labels(self):
        bundle = {"predictions": "id,fold,prediction\nk1,0,0.9\nk2,0,0.2\n",
                  "labels": "id,target\nk1,1\nk2,0\nk3,1\nk4,0\n"}
        status, report = run("--bundle", "-", "--metric", "roc_auc", "--claimed-score", "1.0",
                             stdin=json.dumps(bundle))
        self.assertEqual(status, 1)
        self.assertEqual(report["checks"]["rows_without_prediction"], 2)
        self.assertEqual(report["checks"]["rows_without_fold"], 2)

    def test_fold_column_that_differs_between_files(self):
        bundle = {"predictions": "id,fold,prediction\nk1,0,0.9\nk2,1,0.2\nk3,1,0.8\nk4,0,0.3\n",
                  "folds": "id,fold\nk1,0\nk2,0\nk3,1\nk4,1\n",
                  "labels": "id,target\nk1,1\nk2,0\nk3,1\nk4,0\n"}
        status, report = run("--bundle", "-", "--metric", "roc_auc", "--claimed-score", "1.0",
                             stdin=json.dumps(bundle))
        self.assertEqual(status, 1)
        self.assertEqual(report["checks"]["fold_column_differs"], 2)


class DetailsThatChangeTheScore(unittest.TestCase):
    """Cases where a plausible slip in the arithmetic would give another number."""

    def assert_mean(self, rows, metric, expected, *arguments):
        status, report = one_file(rows, "--metric", metric, "--claimed-score", f"{expected:.8f}", *arguments)
        self.assertEqual(status, 0, report)
        self.assertAlmostEqual(report["recomputed"]["mean"], expected, places=7)

    def test_mae_uses_absolute_errors(self):
        # Errors +1 and -1: the absolute mean is 1, the signed mean would be 0.
        self.assert_mean(one_fold([1, 3], [2, 2]), "mae", 1.0)

    def test_f1_is_not_precision(self):
        # One true positive, no false positive, two false negatives: F1 is 2 / 4, precision would be 1.
        self.assert_mean(one_fold([1, 1, 1, 0], [1, 0, 0, 0]), "f1", 0.5)

    def test_a_prediction_equal_to_the_threshold_is_positive(self):
        self.assert_mean(one_fold([1, 0], [0.5, 0.2]), "accuracy", 1.0, "--threshold", "0.5")

    def test_log_loss_keeps_a_certain_wrong_prediction_near_the_clip(self):
        # Probability 0 for a positive row is kept at 1e-15, so its loss is -ln(1e-15).
        self.assert_mean(one_fold([1, 0], [0.0, 0.2]), "log_loss", (-math.log(1e-15) - math.log(0.8)) / 2)

    def test_weighted_mean_weights_folds_by_rows(self):
        rows = [("a", 0, 1, 2), ("b", 1, 1, 1), ("c", 1, 2, 2), ("d", 1, 3, 3)]
        # Fold scores 1.0 (1 row) and 0.0 (3 rows): the mean is 0.5 and the weighted mean is 0.25.
        status, report = one_file(rows, "--metric", "mae", "--claimed-score", "0.25", "--claim-kind", "weighted_mean")
        self.assertEqual(status, 0, report)
        self.assertEqual((report["recomputed"]["mean"], report["recomputed"]["weighted_mean"]), (0.5, 0.25))

    def test_an_explicit_tolerance_replaces_the_claim_precision(self):
        # The claim 0.9 allows 0.05 by its precision, which covers the recomputed 0.8719; --tolerance 0.001 does not.
        status, report = run("--bundle", "examples/oof-bundle.json", "--metric", "roc_auc", "--claimed-score", "0.9")
        self.assertEqual(status, 0, report)
        status, report = run("--bundle", "examples/oof-bundle.json", "--metric", "roc_auc", "--claimed-score", "0.9",
                             "--tolerance", "0.001")
        self.assertEqual(status, 1, report)
        self.assertEqual((report["claim"]["tolerance"], report["claim"]["tolerance_source"]), (0.001, "--tolerance"))

    def test_rows_without_a_label_fail(self):
        bundle = {"predictions": "id,fold,prediction\nk1,0,0.9\nk2,0,0.2\nk3,1,0.8\nk4,1,0.3\n",
                  "labels": "id,target\nk1,1\nk2,0\nk3,1\nk4,0\nk5,\n",
                  "folds": "id,fold\nk1,0\nk2,0\nk3,1\nk4,1\nk5,1\n"}
        status, report = run("--bundle", "-", "--metric", "roc_auc", "--claimed-score", "1.0", stdin=json.dumps(bundle))
        self.assertEqual(status, 1, report)
        self.assertEqual(report["checks"]["rows_without_label"], 1)
        self.assertEqual(report["coverage"]["rows_scored"], 4)


class Refusals(unittest.TestCase):
    def assert_refused(self, status, report, reason):
        self.assertEqual(status, 2, report)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["reason"], reason, report)

    def test_arguments(self):
        rows = one_fold([1, 0], [0.8, 0.4])
        self.assert_refused(*one_file(rows, "--metric", "roc_auc"), "bad_arguments")
        self.assert_refused(*one_file(rows, "--claimed-score", "0.5"), "bad_arguments")
        self.assert_refused(*one_file(rows, "--metric", "gini", "--claimed-score", "0.5"), "bad_arguments")
        self.assert_refused(*one_file(rows, "--metric", "roc_auc", "--claimed-score", "high"), "bad_arguments")
        self.assert_refused(*one_file(rows, "--metric", "roc_auc", "--claimed-score", "0.5", "--threshold", "0.5"),
                            "bad_arguments")
        self.assert_refused(*one_file(rows, "--metric", "roc_auc", "--claimed-score", "0.5", "--claimed-fold", "7=0.5"),
                            "claimed_fold_unknown")

    def test_values_the_metric_cannot_use(self):
        self.assert_refused(*one_file(one_fold([1, 0, 2], [0.1, 0.2, 0.3]), "--metric", "roc_auc", "--claimed-score",
                                      "0.5"), "labels_not_binary")
        self.assert_refused(*one_file(one_fold([1, 0], [1.2, 0.2]), "--metric", "log_loss", "--claimed-score", "0.5"),
                            "probability_out_of_range")
        self.assert_refused(*one_file(one_fold([1, 2], ["high", 2]), "--metric", "rmse", "--claimed-score", "0.5"),
                            "not_a_number")
        self.assert_refused(*one_file(one_fold([1, 2], [-1, 2]), "--metric", "rmsle", "--claimed-score", "0.5"),
                            "negative_value")

    def test_a_fold_without_a_metric_value(self):
        rows = [("a", 0, 1, 0.9), ("b", 0, 1, 0.4), ("c", 1, 1, 0.3), ("d", 1, 0, 0.2)]
        self.assert_refused(*one_file(rows, "--metric", "roc_auc", "--claimed-score", "0.5"), "metric_undefined")
        rows = [("a", 0, 4, 3), ("b", 0, 4, 5), ("c", 1, 1, 2), ("d", 1, 3, 3)]
        self.assert_refused(*one_file(rows, "--metric", "r2", "--claimed-score", "0.5"), "metric_undefined")

    def test_ids_and_columns(self):
        rows = [("a", 0, 1, 0.9), ("a", 0, 0, 0.4)]
        self.assert_refused(*one_file(rows, "--metric", "roc_auc", "--claimed-score", "0.5"), "duplicate_id")
        self.assert_refused(*one_file([("", 0, 1, 0.9)], "--metric", "roc_auc", "--claimed-score", "0.5"), "empty_id")
        self.assert_refused(*one_file(one_fold([1, 0], [0.8, 0.4]), "--metric", "roc_auc", "--claimed-score", "0.5",
                                      header="id,fold,label,prediction"), "column_missing")
        bundle = {"predictions": "id,fold,prediction\nk1,0,0.9\n", "labels": "id,target\nz1,1\n"}
        status, report = run("--bundle", "-", "--metric", "roc_auc", "--claimed-score", "0.5", stdin=json.dumps(bundle))
        self.assert_refused(status, report, "nothing_to_score")

    def test_paths_are_confined_to_the_root(self):
        status, report = run("--predictions", "../SKILL.md", "--metric", "mae", "--claimed-score", "1")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--predictions", "examples/none.csv", "--metric", "mae", "--claimed-score", "1")
        self.assert_refused(status, report, "input_missing")
        status, report = run("--predictions", sys.executable, "--metric", "mae", "--claimed-score", "1")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--predictions", "SKILL.md", "--metric", "mae", "--claimed-score", "1", "--max-bytes", "100")
        self.assert_refused(status, report, "input_too_large")

    @unittest.skipUnless(os.path.islink("/proc/self/root"), "needs the Linux /proc/self/root link")
    def test_symbolic_link_that_leaves_the_root_is_refused(self):
        # /proc/self/root is a link to the file system root, so this path leaves --root /proc.
        status, report = run("--root", "/proc", "--predictions", "self/root" + str(SCRIPT), "--metric", "mae",
                             "--claimed-score", "1")
        self.assert_refused(status, report, "path_leaves_root")


class Documentation(unittest.TestCase):
    def test_every_documented_option_is_accepted_by_the_script(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                                  timeout=60)
        self.assertEqual(finished.returncode, 0)
        for name in ("SKILL.md", "references/metrics.md", "references/checklist.md"):
            with open(PACKAGE / name, encoding="utf-8") as handle:
                text = handle.read()
            for option in sorted(set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]+", text))):
                self.assertIn(option, finished.stdout, f"{name} mentions {option}")
            for metric in re.findall(r"^\| `([a-z0-9_]+)` \|", text, re.MULTILINE):
                if name == "references/metrics.md" and metric not in ("claim_differs", "fold_claims_differ") \
                        and not metric.startswith(("rows_", "predictions_", "fold_column")):
                    self.assertIn(metric, finished.stdout, f"{name} lists the metric {metric}")


if __name__ == "__main__":
    unittest.main()
