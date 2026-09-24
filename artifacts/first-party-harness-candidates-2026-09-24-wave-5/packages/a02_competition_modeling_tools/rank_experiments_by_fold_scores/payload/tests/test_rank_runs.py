"""Tests for scripts/rank_runs.py. Effects: starts the script with the current interpreter and reads the shipped example; writes no file.

Run from the package folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import json
import statistics
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "rank_runs.py"


def run_script(*arguments, stdin=None):
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(PACKAGE), *arguments],
                          input=stdin, capture_output=True, text=True, timeout=120)
    return done.returncode, json.loads(done.stdout)


def csv_ledger(runs):
    lines = ["run,fold,score"]
    for run, scores in runs.items():
        lines += [f"{run},{fold},{score}" for fold, score in enumerate(scores)]
    return "\n".join(lines) + "\n"


def by_run(report):
    return {row["run"]: row for row in report["ranking"]}


class RankRuns(unittest.TestCase):
    def test_example_ledger_ranks_and_marks_the_tie_at_the_top(self):
        status, report = run_script("--ledger", "examples/ledger.json", "--direction", "maximize",
                                    "--baseline", "baseline_lr")
        self.assertEqual((status, report["status"]), (0, "pass"))
        self.assertEqual([row["run"] for row in report["ranking"]],
                         ["gbm_v2", "gbm_v1", "gbm_v1_more_trees", "baseline_lr"])
        self.assertIs(report["leader_established"], False)
        self.assertEqual(report["tied_with_leader"], ["gbm_v1", "gbm_v1_more_trees"])
        self.assertEqual(report["baseline"]["beats_baseline"], ["gbm_v2", "gbm_v1", "gbm_v1_more_trees"])
        self.assertEqual(report["input"]["format"], "json_array")

    def test_known_wrong_mean_only_comparison_is_not_established(self):
        run_a = [0.841, 0.869, 0.820, 0.852, 0.828]
        gains = [0.012, -0.006, 0.009, -0.004, 0.009]
        run_b = [round(a + g, 3) for a, g in zip(run_a, gains)]
        self.assertGreater(statistics.mean(run_b), statistics.mean(run_a))
        status, report = run_script("--ledger", "-", "--direction", "maximize",
                                    stdin=csv_ledger({"run_a": run_a, "run_b": run_b}))
        self.assertEqual(status, 0)
        self.assertEqual(report["leader"], "run_b")
        verdict = by_run(report)["run_a"]["leader_over_this"]
        self.assertEqual(verdict["verdict"], "gain_not_established")
        self.assertAlmostEqual(verdict["mean_gain"], 0.004, places=9)
        self.assertAlmostEqual(verdict["gain_spread"], statistics.stdev(gains), places=9)

    def test_small_gain_on_every_fold_is_established_by_pairing(self):
        base = [0.70, 0.76, 0.66, 0.74, 0.68]
        better = [score + 0.005 for score in base]
        self.assertLess(0.005, statistics.stdev(base))
        status, report = run_script("--ledger", "-", "--direction", "maximize",
                                    stdin=csv_ledger({"base": base, "better": better}))
        self.assertEqual(status, 0)
        self.assertEqual(report["leader"], "better")
        self.assertIs(report["leader_established"], True)

    def test_minimize_reverses_the_order(self):
        ledger = csv_ledger({"low_loss": [0.30, 0.31, 0.29], "high_loss": [0.40, 0.42, 0.41]})
        status, report = run_script("--ledger", "-", "--direction", "minimize", stdin=ledger)
        self.assertEqual((status, report["leader"]), (0, "low_loss"))
        status, report = run_script("--ledger", "-", "--direction", "maximize", stdin=ledger)
        self.assertEqual(report["leader"], "high_loss")

    def test_json_lines_and_csv_give_the_same_ranking(self):
        runs = {"a": [0.5, 0.6, 0.7], "b": [0.52, 0.61, 0.73]}
        lines = "\n".join(json.dumps({"run": run, "fold": fold, "score": score})
                          for run, scores in runs.items() for fold, score in enumerate(scores)) + "\n"
        first = run_script("--ledger", "-", "--direction", "maximize", stdin=lines)[1]
        second = run_script("--ledger", "-", "--direction", "maximize", stdin=csv_ledger(runs))[1]
        self.assertEqual(first["input"]["format"], "json_lines")
        self.assertEqual(first["ranking"], second["ranking"])

    def test_different_fold_sets_are_not_compared_and_exit_1(self):
        ledger = csv_ledger({"a": [0.5, 0.6, 0.7, 0.8], "b": [0.5, 0.6, 0.7, 0.8], "c": [0.9, 0.9, 0.9]})
        status, report = run_script("--ledger", "-", "--direction", "maximize", stdin=ledger)
        self.assertEqual((status, report["status"]), (1, "fold_sets_differ"))
        self.assertEqual(report["fold_set_mismatch"], ["c"])
        self.assertEqual(report["reference_folds"], ["0", "1", "2", "3"])
        self.assertEqual([row["run"] for row in report["ranking"]], ["a", "b", "c"])
        self.assertEqual(by_run(report)["c"]["leader_over_this"]["verdict"], "not_comparable")
        self.assertIs(by_run(report)["c"]["same_folds_as_reference"], False)
        self.assertEqual(report["tied_with_leader"], ["b"])

    def test_known_wrong_partial_run_with_high_early_folds_does_not_lead(self):
        ledger = csv_ledger({"full_a": [0.80, 0.82, 0.79, 0.81, 0.80], "full_b": [0.81, 0.83, 0.80, 0.82, 0.81],
                             "crashed": [0.86, 0.85, 0.87]})
        status, report = run_script("--ledger", "-", "--direction", "maximize", stdin=ledger)
        self.assertEqual(status, 1)
        crashed_mean = by_run(report)["crashed"]["mean"]
        self.assertGreater(crashed_mean, by_run(report)["full_b"]["mean"])
        self.assertEqual(report["leader"], "full_b")
        self.assertIs(report["leader_established"], True)
        self.assertEqual(report["tied_with_leader"], [])
        self.assertEqual([row["run"] for row in report["ranking"]], ["full_b", "full_a", "crashed"])
        self.assertEqual(report["fold_set_mismatch"], ["crashed"])

    def test_too_few_shared_folds(self):
        status, report = run_script("--ledger", "-", "--direction", "maximize",
                                    stdin=csv_ledger({"a": [0.5, 0.6], "b": [0.7, 0.8]}))
        self.assertEqual(status, 0)
        self.assertEqual(by_run(report)["a"]["leader_over_this"]["verdict"], "too_few_shared_folds")

    def test_refusals(self):
        cases = [
            (["--ledger", "-"], csv_ledger({"a": [0.5, 0.6, 0.7]}), "bad_arguments"),
            (["--ledger", "-", "--direction", "maximize"], "run,fold,score\na,0,0.5\na,0,0.6\n", "duplicate_run_fold"),
            (["--ledger", "-", "--direction", "maximize"], "run,fold,score\na,0,NaN\n", "score_invalid"),
            (["--ledger", "-", "--direction", "maximize"], '[{"run": "a", "fold": 0, "score": NaN}]', "ledger_not_json"),
            (["--ledger", "-", "--direction", "maximize"], '[{"run": "a", "fold": 0.5, "score": 1}]', "fold_invalid"),
            (["--ledger", "-", "--direction", "maximize"], "name,fold,score\na,0,0.5\n", "ledger_field_missing"),
            (["--ledger", "-", "--direction", "maximize", "--baseline", "zzz"], csv_ledger({"a": [1, 2, 3]}),
             "baseline_missing"),
            (["--ledger", "-", "--direction", "maximize"], "", "ledger_empty"),
            (["--ledger", "../ledger.csv", "--direction", "maximize"], None, "path_leaves_root"),
            (["--ledger", "examples/none.json", "--direction", "maximize"], None, "input_missing"),
        ]
        for arguments, stdin, reason in cases:
            status, report = run_script(*arguments, stdin=stdin)
            self.assertEqual((status, report["reason"]), (2, reason), arguments)


if __name__ == "__main__":
    unittest.main()
