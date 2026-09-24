"""Effects: creates temporary git repositories, runs git and scripts/record_reproduction_run.py, reads what it writes.

Tests for scripts/record_reproduction_run.py. Run from the payload root:

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
SCRIPT = PAYLOAD / "scripts" / "record_reproduction_run.py"
EXAMPLE_INPUT = PAYLOAD / "examples" / "input.json"
EXAMPLE_OUTPUT = PAYLOAD / "examples" / "output.json"

BADGE_SOURCE = 'def badge_text(count):\n    return f"{count} items"\n'
EXISTING_TESTS = (
    "import unittest\n\nfrom shop.cart_badge import badge_text\n\n\n"
    "class BadgeTextTests(unittest.TestCase):\n"
    "    def test_badge_counts_three(self):\n"
    '        self.assertEqual(badge_text(3), "3 items")\n'
)
NEW_TEST = (
    "\n    def test_badge_uses_singular_for_one_item(self):\n"
    '        self.assertEqual(badge_text(1), "1 item")\n'
)
SINGLE_TEST = "tests.test_cart_badge.BadgeTextTests.test_badge_uses_singular_for_one_item"
INPUT = ".baltor/step/input.json"


def git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=Night Test",
                           "-c", "user.email=night-test@example.invalid", "-c", "commit.gpgsign=false",
                           "-c", "init.defaultBranch=main", *arguments],
                          check=True, capture_output=True, text=True, timeout=60)


def make_workspace(directory):
    root = Path(directory) / "work"
    for folder in ("shop", "tests", "tickets"):
        (root / folder).mkdir(parents=True)
    (root / "shop" / "cart_badge.py").write_text(BADGE_SOURCE, encoding="utf-8")
    (root / "tests" / "test_cart_badge.py").write_text(EXISTING_TESTS, encoding="utf-8")
    (root / "tickets" / "T-104.md").write_text("The cart badge says 1 items for a single item.\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def write_input(root, **changes):
    step = json.loads(EXAMPLE_INPUT.read_text(encoding="utf-8"))
    step["test_command"] = [sys.executable, "-B", "-m", "unittest", SINGLE_TEST]
    step.update(changes)
    target = root / INPUT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(step), encoding="utf-8")
    return hashlib.sha256(target.read_bytes()).hexdigest()


def run_recorder(root):
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--input", INPUT,
                           "--root", str(root)], capture_output=True, text=True, timeout=120, cwd=str(root))
    return done.returncode, json.loads(done.stdout)


class RecordReproductionRun(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = make_workspace(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def add_new_test(self, body=NEW_TEST):
        (self.root / "tests" / "test_cart_badge.py").write_text(EXISTING_TESTS + body, encoding="utf-8")

    def evidence(self, summary):
        return json.loads((self.root / summary["evidence_path"]).read_text(encoding="utf-8"))

    def evidence_files(self):
        folder = self.root / ".baltor" / "step-output" / "evidence"
        return sorted(folder.glob("reproduction-run-*.json")) if folder.is_dir() else []

    def test_new_failing_test_is_recorded(self):
        self.add_new_test()
        host_digest = write_input(self.root)
        code, summary = run_recorder(self.root)
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["verdict"], "nonzero_exit_recorded")
        record = self.evidence(summary)
        self.assertEqual(record["record_type"], "ticket_reproduction_run/v1")
        self.assertTrue(record["ran"])
        self.assertNotEqual(record["exit_code"], 0)
        self.assertIn("'1 items' != '1 item'", record["output_tail"])
        self.assertTrue(record["output_mentions_test_name"])
        self.assertEqual(record["test_file_status"], "modified")
        self.assertEqual(record["changed_paths"], ["tests/test_cart_badge.py"])
        self.assertEqual(record["product_paths_changed"], [])
        self.assertEqual(record["other_test_paths_changed"], [])
        self.assertIn(INPUT, record["ignored_paths"])
        self.assertRegex(record["test_file_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual((record["input_path"], record["input_sha256"]), (INPUT, host_digest))
        self.assertTrue(summary["evidence_path"].startswith(".baltor/step-output/evidence/"))

    def test_known_wrong_product_change_is_not_a_reproduction(self):
        self.add_new_test()
        (self.root / "shop" / "cart_badge.py").write_text(BADGE_SOURCE.replace("items", "itemz"), encoding="utf-8")
        write_input(self.root)
        code, summary = run_recorder(self.root)
        self.assertEqual(code, 1, summary)
        self.assertEqual(summary["verdict"], "product_code_changed")
        self.assertEqual(summary["product_paths_changed"], ["shop/cart_badge.py"])
        record = self.evidence(summary)
        self.assertFalse(record["ran"], "the test must not run while product code is changed")

    def test_product_change_hidden_by_editing_the_input_shows_in_the_input_digest(self):
        self.add_new_test()
        (self.root / "shop" / "cart_badge.py").write_text(BADGE_SOURCE.replace("items", "itemz"), encoding="utf-8")
        host_digest = write_input(self.root)
        step = json.loads((self.root / INPUT).read_text(encoding="utf-8"))
        step["host_placed_paths"] = step["host_placed_paths"] + ["shop/cart_badge.py"]
        (self.root / INPUT).write_text(json.dumps(step), encoding="utf-8")
        edited_digest = hashlib.sha256((self.root / INPUT).read_bytes()).hexdigest()
        code, summary = run_recorder(self.root)
        record = self.evidence(summary)
        self.assertEqual(record["input_sha256"], edited_digest)
        self.assertNotEqual(record["input_sha256"], host_digest,
                            "the host compares this digest with the input it wrote and refuses the step")
        self.assertEqual(summary["input_sha256"], edited_digest)
        self.assertEqual(code, 0, summary)

    def test_other_test_file_change_is_not_run(self):
        (self.root / "tests" / "helpers.py").write_text("LIMIT = 1\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "helper")
        (self.root / "tests" / "helpers.py").write_text("LIMIT = 2\n", encoding="utf-8")
        self.add_new_test()
        write_input(self.root)
        code, summary = run_recorder(self.root)
        self.assertEqual((code, summary["verdict"]), (1, "other_test_files_changed"), summary)
        self.assertEqual(summary["other_test_paths_changed"], ["tests/helpers.py"])
        self.assertFalse(self.evidence(summary)["ran"])

    def test_name_only_in_a_comment_is_not_a_test(self):
        self.add_new_test("    # later: test_badge_uses_singular_for_one_item\n")
        write_input(self.root)
        code, summary = run_recorder(self.root)
        self.assertEqual((code, summary["verdict"]), (1, "test_name_not_in_file"), summary)
        self.assertFalse(self.evidence(summary)["ran"])

    def test_longer_name_does_not_count_as_the_name(self):
        self.add_new_test(NEW_TEST.replace("test_badge_uses_singular_for_one_item",
                                           "test_badge_uses_singular_for_one_item_later"))
        write_input(self.root)
        code, summary = run_recorder(self.root)
        self.assertEqual((code, summary["verdict"]), (1, "test_name_not_in_file"), summary)

    def test_passing_test_is_reported_and_not_forced(self):
        self.add_new_test(NEW_TEST.replace('"1 item"', '"1 items"'))
        write_input(self.root)
        code, summary = run_recorder(self.root)
        self.assertEqual(code, 1, summary)
        self.assertEqual(summary["verdict"], "test_passed")
        self.assertEqual(self.evidence(summary)["exit_code"], 0)

    def test_every_run_keeps_its_own_evidence_file(self):
        self.add_new_test(NEW_TEST.replace("badge_text(1)", "badge_textt(1)"))
        write_input(self.root)
        first_code, first = run_recorder(self.root)
        self.add_new_test()
        second_code, second = run_recorder(self.root)
        self.assertEqual((first_code, second_code), (0, 0))
        self.assertIn("NameError", self.evidence(first)["output_tail"])
        self.assertNotEqual(first["evidence_path"], second["evidence_path"])
        self.assertEqual(len(self.evidence_files()), 2)

    def test_host_placed_files_and_caches_are_ignored(self):
        self.add_new_test()
        (self.root / "AGENTS.md").write_text("# Step\n", encoding="utf-8")
        (self.root / "shop" / "__pycache__").mkdir()
        (self.root / "shop" / "__pycache__" / "cart_badge.cpython-310.pyc").write_bytes(b"cache")
        write_input(self.root)
        code, summary = run_recorder(self.root)
        self.assertEqual(code, 0, summary)
        ignored = self.evidence(summary)["ignored_paths"]
        self.assertIn("AGENTS.md", ignored)
        self.assertIn("shop/__pycache__/cart_badge.cpython-310.pyc", ignored)

    def test_missing_name_and_unchanged_file_are_reported(self):
        self.add_new_test(NEW_TEST.replace("test_badge_uses_singular_for_one_item", "test_other_name"))
        write_input(self.root)
        code, summary = run_recorder(self.root)
        self.assertEqual((code, summary["verdict"]), (1, "test_name_not_in_file"))
        self.add_new_test()
        git(self.root, "add", "tests/test_cart_badge.py")
        git(self.root, "commit", "-q", "-m", "test already present")
        code, summary = run_recorder(self.root)
        self.assertEqual((code, summary["verdict"]), (1, "test_file_unchanged"))

    def test_timeout_is_recorded(self):
        self.add_new_test()
        write_input(self.root, test_command=[sys.executable, "-c", "import time; time.sleep(30)"], timeout_seconds=1)
        code, summary = run_recorder(self.root)
        self.assertEqual((code, summary["verdict"]), (1, "timed_out"))
        record = self.evidence(summary)
        self.assertTrue(record["timed_out"])
        self.assertLess(record["duration_seconds"], 20)

    def test_unrendered_marker_is_refused(self):
        self.add_new_test()
        write_input(self.root, ticket_id="{" * 2 + "TICKET_ID" + "}" * 2)
        code, summary = run_recorder(self.root)
        self.assertEqual(code, 2, summary)
        self.assertIn("unrendered_step_input", summary["reason"])
        self.assertEqual(self.evidence_files(), [])

    def test_evidence_inside_the_packet_folder_is_refused(self):
        self.add_new_test()
        write_input(self.root, evidence_dir=".baltor/step/evidence")
        code, summary = run_recorder(self.root)
        self.assertEqual(code, 2, summary)
        self.assertIn(".baltor/step/", summary["reason"])
        self.assertFalse((self.root / ".baltor" / "step" / "evidence").exists())

    def test_paths_that_leave_the_workspace_are_refused(self):
        self.add_new_test()
        write_input(self.root, test_file="../outside/test_cart_badge.py", test_path_prefixes=["../outside/"])
        self.assertEqual(run_recorder(self.root)[0], 2)
        outside = Path(self.directory.name) / "outside"
        outside.mkdir()
        (self.root / "tests" / "linked").symlink_to(outside, target_is_directory=True)
        write_input(self.root, test_file="tests/linked/test_cart_badge.py")
        code, summary = run_recorder(self.root)
        self.assertEqual(code, 2, summary)
        self.assertIn("symbolic link", summary["reason"])

    def test_example_output_matches_the_output_rules(self):
        output = json.loads(EXAMPLE_OUTPUT.read_text(encoding="utf-8"))
        step = json.loads(EXAMPLE_INPUT.read_text(encoding="utf-8"))
        self.assertEqual(output["record_type"], "ticket_reproduction_record/v1")
        self.assertEqual((output["ticket_id"], output["test_file"], output["test_name"]),
                         (step["ticket_id"], step["test_file"], step["test_name"]))
        self.assertEqual(output["status"], "reproduced")
        self.assertIn(output["evidence_path"], output["evidence_files"])
        self.assertTrue(output["evidence_path"].startswith(step["evidence_dir"] + "/"))
        self.assertFalse(step["evidence_dir"].startswith(".baltor/step/"))
        self.assertFalse(output["product_code_changed"])
        self.assertIsNone(output["blocker"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
