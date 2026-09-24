"""Effects: creates temporary git repositories, runs git and scripts/run_fix_checks.py, reads what it writes.

Tests for scripts/run_fix_checks.py. Run from the payload root:

    python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v

Every fixture is synthetic and lives in a temporary directory.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "run_fix_checks.py"
EXAMPLE_INPUT = PAYLOAD / "examples" / "input.json"
EXAMPLE_OUTPUT = PAYLOAD / "examples" / "output.json"
INPUT = ".baltor/step/input.json"

BUGGY_SOURCE = 'def badge_text(count):\n    return f"{count} items"\n'
FIXED_SOURCE = 'def badge_text(count):\n    return "1 item" if count == 1 else f"{count} items"\n'
TESTS_WITH_REPRODUCTION = (
    "import unittest\n\nfrom shop.cart_badge import badge_text\n\n\n"
    "class BadgeTextTests(unittest.TestCase):\n"
    "    def test_badge_counts_three(self):\n"
    '        self.assertEqual(badge_text(3), "3 items")\n\n'
    "    def test_badge_uses_singular_for_one_item(self):\n"
    '        self.assertEqual(badge_text(1), "1 item")\n'
)
GOOD_MESSAGE = ("T-104: Use singular badge text for one item\n\nbadge_text(1) now returns 1 item.\n"
                "The new test in tests/test_cart_badge.py fails before the change and passes after it.\n")


def git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=Night Test",
                           "-c", "user.email=night-test@example.invalid", "-c", "commit.gpgsign=false",
                           "-c", "init.defaultBranch=main", *arguments],
                          check=True, capture_output=True, text=True, timeout=60)


class RunFixChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = self.root = Path(self.directory.name) / "work"
        for folder in ("shop", "tests", "docs"):
            (root / folder).mkdir(parents=True)
        (root / "shop" / "cart_badge.py").write_text(BUGGY_SOURCE, encoding="utf-8")
        (root / "tests" / "test_cart_badge.py").write_text(TESTS_WITH_REPRODUCTION.split("\n\n    def test_badge_uses")[0] + "\n", encoding="utf-8")
        (root / "docs" / "badge.md").write_text("The badge shows the item count.\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("# Shop\n\nRun the tests with unittest.\n", encoding="utf-8")
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "base")
        self.base = git(root, "rev-parse", "HEAD").stdout.strip()
        test_file = root / "tests" / "test_cart_badge.py"
        test_file.write_text(TESTS_WITH_REPRODUCTION, encoding="utf-8")
        self.recorded = hashlib.sha256(test_file.read_bytes()).hexdigest()

    def tearDown(self):
        self.directory.cleanup()

    def write_input(self, **changes):
        step = json.loads(EXAMPLE_INPUT.read_text(encoding="utf-8"))
        step.update(base_revision=self.base, reproduction_test_sha256=self.recorded, timeout_seconds=120,
                    relevant_test_command=[sys.executable, "-B", "-m", "unittest", "tests.test_cart_badge"],
                    full_test_command=[sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"])
        step.update(changes)
        target = self.root / INPUT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(step), encoding="utf-8")
        return hashlib.sha256(target.read_bytes()).hexdigest()

    def run_checks(self, *extra):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--input", INPUT,
                               "--root", str(self.root), *extra], capture_output=True, text=True, timeout=300)
        return done.returncode, json.loads(done.stdout)

    def fix(self):
        (self.root / "shop" / "cart_badge.py").write_text(FIXED_SOURCE, encoding="utf-8")

    def failed(self, summary):
        return summary["failed_checks"]

    def test_correct_fix_is_ready_for_review(self):
        self.fix()
        host_digest = self.write_input()
        code, summary = self.run_checks()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["verdict"], "ready_for_review")
        self.assertEqual(summary["changed_paths"], ["shop/cart_badge.py", "tests/test_cart_badge.py"])
        self.assertEqual(summary["new_paths"], [])
        self.assertEqual(summary["input_sha256"], host_digest)
        record = json.loads((self.root / summary["evidence_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["record_type"], "ticket_fix_verification_run/v1")
        self.assertEqual(record["runs"]["relevant"]["exit_code"], 0)
        self.assertEqual(record["runs"]["full"]["exit_code"], 0)
        self.assertEqual((record["input_path"], record["input_sha256"]), (INPUT, host_digest))
        self.assertIn(INPUT, record["ignored_paths"])
        self.assertTrue(summary["evidence_path"].startswith(".baltor/step-output/evidence/"))

    def test_diff_holds_only_the_judged_paths(self):
        self.fix()
        (self.root / "AGENTS.md").write_text("# Shop\n\nRun the tests with unittest.\n\n# Step section\n",
                                             encoding="utf-8")
        (self.root / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        (self.root / "shop" / "plural.py").write_text("SINGULAR = 'item'\n", encoding="utf-8")
        self.write_input()
        code, summary = self.run_checks()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["new_paths"], ["shop/plural.py"])
        self.assertIsNone(summary["diff_error"])
        diff = (self.root / summary["diff_path"]).read_text(encoding="utf-8")
        self.assertIn("+++ b/shop/cart_badge.py", diff)
        self.assertIn("+++ b/tests/test_cart_badge.py", diff)
        self.assertNotIn("AGENTS.md", diff, "a file the host placed is not part of the fix")
        self.assertNotIn("CLAUDE.md", diff)
        self.assertTrue(summary["diff_path"].startswith(".baltor/step-output/evidence/verification-"))

    def test_known_wrong_weakened_reproduction_test_is_not_ready(self):
        test_file = self.root / "tests" / "test_cart_badge.py"
        test_file.write_text(TESTS_WITH_REPRODUCTION.replace('"1 item"', '"1 items"'), encoding="utf-8")
        self.write_input()
        code, summary = self.run_checks()
        self.assertEqual(code, 1, summary)
        self.assertEqual(summary["verdict"], "not_ready")
        self.assertIn("reproduction_test_unchanged", self.failed(summary))
        self.assertNotIn("relevant_tests_pass", self.failed(summary), "the weakened test passes, so only the digest catches it")

    def test_path_outside_allowed_prefixes_is_not_ready_and_full_run_is_skipped(self):
        self.fix()
        (self.root / "docs" / "badge.md").write_text("Changed without permission.\n", encoding="utf-8")
        self.write_input()
        code, summary = self.run_checks()
        self.assertEqual(code, 1, summary)
        self.assertEqual(self.failed(summary), ["changed_paths_allowed", "full_tests_pass"])
        record = json.loads((self.root / summary["evidence_path"]).read_text(encoding="utf-8"))
        self.assertEqual(record["paths_outside_allowed"], ["docs/badge.md"])
        self.assertFalse(record["runs"]["full"]["ran"])
        self.assertIn("+++ b/docs/badge.md", (self.root / summary["diff_path"]).read_text(encoding="utf-8"))

    def test_failing_relevant_tests_are_not_ready(self):
        self.write_input()
        code, summary = self.run_checks()
        self.assertEqual(code, 1, summary)
        self.assertEqual(self.failed(summary), ["relevant_tests_pass", "full_tests_pass"])

    def test_commit_after_base_and_file_limit_are_not_ready(self):
        self.fix()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "fix committed too early")
        self.write_input(max_files_changed=1)
        code, summary = self.run_checks()
        self.assertEqual(code, 1, summary)
        self.assertIn("head_at_base_revision", self.failed(summary))
        self.assertIn("changed_file_count", self.failed(summary))

    def test_commits_since_base_pass_only_when_allowed_and_history_is_kept(self):
        self.fix()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "T-104: local commit made by the fix step")
        self.write_input(allow_commits_since_base=True)
        code, summary = self.run_checks()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["checks"][0]["name"], "base_is_ancestor_of_head")
        git(self.root, "checkout", "-q", "--orphan", "rewritten")
        git(self.root, "commit", "-q", "-m", "history without the base")
        code, summary = self.run_checks()
        self.assertEqual(code, 1, summary)
        self.assertIn("base_is_ancestor_of_head", self.failed(summary))

    def test_unknown_base_and_markers_are_refused(self):
        self.fix()
        self.write_input(base_revision="0" * 40)
        code, summary = self.run_checks()
        self.assertEqual(code, 2, summary)
        self.assertIn("not a commit", summary["reason"])
        self.write_input(allow_commits_since_base="yes")
        self.assertEqual(self.run_checks()[0], 2)
        self.write_input(ticket_id="{" * 2 + "TICKET_ID" + "}" * 2)
        code, summary = self.run_checks()
        self.assertEqual(code, 2, summary)
        self.assertIn("unrendered_step_input", summary["reason"])
        self.assertFalse((self.root / ".baltor" / "step-output" / "evidence").exists())

    def test_output_paths_inside_the_packet_folder_are_refused(self):
        self.fix()
        for name, value in (("summary_path", ".baltor/step/change-summary.md"),
                            ("commit_message_path", ".baltor/step/commit-message.txt"),
                            ("evidence_dir", ".baltor/step/evidence")):
            self.write_input(**{name: value})
            code, summary = self.run_checks()
            self.assertEqual(code, 2, (name, summary))
            self.assertIn(".baltor/step/", summary["reason"])
        self.assertFalse((self.root / ".baltor" / "step" / "evidence").exists())

    def test_commit_message_check(self):
        self.write_input()
        message = self.root / ".baltor" / "step-output" / "commit-message.txt"
        message.parent.mkdir(parents=True, exist_ok=True)
        code, result = self.run_checks("--check-commit-message")
        self.assertEqual((code, result["passed"]), (1, False))
        message.write_text(GOOD_MESSAGE, encoding="utf-8")
        code, result = self.run_checks("--check-commit-message")
        self.assertEqual((code, result["passed"]), (0, True), result)
        message.write_text("Fix the badge text so that a cart with exactly one item no longer shows the plural form\n",
                           encoding="utf-8")
        code, result = self.run_checks("--check-commit-message")
        self.assertEqual(code, 1)
        self.assertTrue(any("subject has" in problem for problem in result["problems"]))
        self.assertTrue(any("T-104" in problem for problem in result["problems"]))
        message.write_text("T-104: Fix badge\nno blank line here\n", encoding="utf-8")
        code, result = self.run_checks("--check-commit-message")
        self.assertEqual(code, 1)
        self.assertTrue(any("second line" in problem for problem in result["problems"]))

    def test_commit_message_names_the_ticket_in_the_subject_and_keeps_a_short_body(self):
        self.write_input()
        message = self.root / ".baltor" / "step-output" / "commit-message.txt"
        message.parent.mkdir(parents=True, exist_ok=True)
        message.write_text("Use singular badge text for one item\n\nFixes T-104.\nThe new test now passes.\n",
                           encoding="utf-8")
        code, result = self.run_checks("--check-commit-message")
        self.assertEqual(code, 1, result)
        self.assertIn("the subject does not name the ticket T-104", result["problems"])
        message.write_text("T-104: Use singular badge text for one item\n\nOne body line only.\n", encoding="utf-8")
        code, result = self.run_checks("--check-commit-message")
        self.assertEqual(code, 1, result)
        self.assertTrue(any("1 nonempty lines" in problem for problem in result["problems"]))
        body = "".join(f"Line {number} of the body.\n" for number in range(1, 7))
        message.write_text("T-104: Use singular badge text for one item\n\n" + body, encoding="utf-8")
        code, result = self.run_checks("--check-commit-message")
        self.assertEqual(code, 1, result)
        self.assertTrue(any("6 nonempty lines" in problem for problem in result["problems"]))
        message.write_text("T-1040: Use singular badge text for one item\n\nFirst line.\nSecond line.\n",
                           encoding="utf-8")
        code, result = self.run_checks("--check-commit-message")
        self.assertEqual(code, 1, result)
        self.assertIn("the subject does not name the ticket T-104", result["problems"])

    def test_example_output_matches_the_output_rules(self):
        output = json.loads(EXAMPLE_OUTPUT.read_text(encoding="utf-8"))
        step = json.loads(EXAMPLE_INPUT.read_text(encoding="utf-8"))
        self.assertEqual(output["record_type"], "ticket_fix_verification_record/v1")
        self.assertEqual(output["verdict"], "ready_for_review")
        self.assertEqual(output["failed_checks"], [])
        self.assertIs(output["committed"], False)
        self.assertIsNone(output["blocker"])
        self.assertEqual((output["summary_path"], output["commit_message_path"]),
                         (step["summary_path"], step["commit_message_path"]))
        self.assertTrue(output["evidence_path"].startswith(step["evidence_dir"] + "/"))
        for name in ("evidence_dir", "summary_path", "commit_message_path"):
            self.assertTrue(step[name].startswith(".baltor/step-output/"), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
