"""Effects: creates temporary git repositories and folders, runs git and scripts/handoff_drift.py, reads what it writes.

Tests for scripts/handoff_drift.py. Run from the payload root:

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
SCRIPT = PAYLOAD / "scripts" / "handoff_drift.py"
EXAMPLES = PAYLOAD / "examples"
INSTRUCTIONS = ".baltor/resume/interrupted-instructions.md"
HANDOFF = ".baltor/resume/handoff.json"
INPUT = ".baltor/resume/input.json"
PLACED = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]

BADGE_SOURCE = 'def badge_text(count):\n    return f"{count} items"\n'
FIXED_SOURCE = 'def badge_text(count):\n    return "1 item" if count == 1 else f"{count} items"\n'
BASE_TESTS = (
    "import unittest\n\nfrom shop.cart_badge import badge_text\n\n\n"
    "class BadgeTextTests(unittest.TestCase):\n"
    "    def test_badge_counts_three(self):\n"
    '        self.assertEqual(badge_text(3), "3 items")\n'
)
ADDED_TEST = (
    "\n    def test_badge_uses_singular_for_one_item(self):\n"
    '        self.assertEqual(badge_text(1), "1 item")\n'
)
RECORDER = ("python3 -I -B .baltor/ticket-reproduction-packet/scripts/record_reproduction_run.py "
            "--input .baltor/step/input.json")


def git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=Night Test",
                           "-c", "user.email=night-test@example.invalid", "-c", "commit.gpgsign=false",
                           "-c", "init.defaultBranch=main", *arguments],
                          check=True, capture_output=True, text=True, timeout=60)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*arguments):
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments],
                          capture_output=True, text=True, timeout=120)
    return done.returncode, json.loads(done.stdout)


class HandoffDrift(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = self.root = Path(self.directory.name) / "work"
        for folder in ("shop", "tests", ".baltor/step", ".baltor/resume"):
            (root / folder).mkdir(parents=True)
        (root / "shop" / "cart_badge.py").write_text(BADGE_SOURCE, encoding="utf-8")
        (root / "shop" / "old_badge.py").write_text("OLD = True\n", encoding="utf-8")
        (root / "tests" / "test_cart_badge.py").write_text(BASE_TESTS, encoding="utf-8")
        (root / "README.md").write_text("Shop sample.\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("# Shop\n", encoding="utf-8")
        git(root, "init", "-q")
        git(root, "add", "shop", "tests", "README.md", "AGENTS.md")
        git(root, "commit", "-q", "-m", "base")
        self.head = git(root, "rev-parse", "HEAD").stdout.strip()
        (root / ".baltor" / "step" / "input.json").write_text('{"record_type": "ticket_fix_verification_input/v1"}\n',
                                                              encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def interrupted_night(self):
        """The reproduction step left its new test uncommitted; the fix step was stopped after editing the code."""
        (self.root / "tests" / "test_cart_badge.py").write_text(BASE_TESTS + ADDED_TEST, encoding="utf-8")
        (self.root / "shop" / "cart_badge.py").write_text(FIXED_SOURCE, encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# Shop\n\n# Fix step section composed by the host\n", encoding="utf-8")
        (self.root / INSTRUCTIONS).write_bytes((EXAMPLES / "interrupted-instructions.md").read_bytes())

    def host_writes_handoff(self, step_id="t-104-reproduction"):
        arguments = ["write", "--root", str(self.root), "--step-id", step_id, "--ticket-id", "T-104",
                     "--instructions", INSTRUCTIONS, "--handoff", HANDOFF]
        for path in PLACED:
            arguments += ["--host-placed", path]
        code, answer = run(*arguments)
        self.assertEqual(code, 0, answer)
        return answer

    def host_writes_input(self, answer=None, **changes):
        answer = answer or {"handoff_sha256": sha256(self.root / HANDOFF),
                            "interrupted_instructions_sha256": sha256(self.root / INSTRUCTIONS)}
        step = json.loads((EXAMPLES / "input.json").read_text(encoding="utf-8"))
        step.update(handoff_sha256=answer["handoff_sha256"],
                    interrupted_instructions_sha256=answer["interrupted_instructions_sha256"],
                    host_files=[{"path": ".baltor/step/input.json",
                                 "sha256": sha256(self.root / ".baltor" / "step" / "input.json")}])
        step.update(changes)
        (self.root / INPUT).write_text(json.dumps(step), encoding="utf-8")
        return sha256(self.root / INPUT)

    def replace_handoff(self, **changes):
        handoff = json.loads((self.root / HANDOFF).read_text(encoding="utf-8"))
        handoff.update(changes)
        (self.root / HANDOFF).write_text(json.dumps(handoff), encoding="utf-8")

    def check(self):
        return run("check", "--input", INPUT, "--root", str(self.root))

    def kinds(self, summary):
        return sorted(difference["kind"] for difference in summary["differences"])

    def test_reproduction_then_interrupted_fix_matches(self):
        self.interrupted_night()
        answer = self.host_writes_handoff(step_id="t-104-reproduction")
        handoff = json.loads((self.root / HANDOFF).read_text(encoding="utf-8"))
        self.assertEqual(handoff["revision"], self.head)
        self.assertEqual([item["path"] for item in handoff["files"]], ["shop/cart_badge.py", "tests/test_cart_badge.py"])
        self.assertEqual((handoff["status"], handoff["claims"], handoff["remaining_actions"]), ("unfinished", [], []))
        self.assertEqual(handoff["first_action"],
                         "Read `.baltor/step/input.json`, then the ticket file at its `ticket_path`.")
        self.assertEqual(answer["handoff_sha256"], sha256(self.root / HANDOFF))
        input_digest = self.host_writes_input(answer)
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"]), (0, "match"), summary)
        self.assertEqual(summary["first_action"], handoff["first_action"])
        self.assertEqual(summary["remaining_actions"], [])
        self.assertEqual(summary["input_sha256"], input_digest)
        record = json.loads((self.root / summary["evidence_path"]).read_text(encoding="utf-8"))
        self.assertEqual((record["record_type"], record["git_checks"], record["files_checked"]),
                         ("interrupted_step_drift_check/v1", "run", 2))
        self.assertTrue(summary["evidence_path"].startswith(".baltor/resume-output/evidence/"))

    def test_code_block_first_action_is_quoted_and_accepted(self):
        self.interrupted_night()
        text = (self.root / INSTRUCTIONS).read_text(encoding="utf-8")
        text = text.replace("Read `.baltor/step/input.json`, then the ticket file at its `ticket_path`.",
                            "Run the recorder and read the JSON it prints:\n\n```bash\n" + RECORDER + "\n```")
        (self.root / INSTRUCTIONS).write_text(text, encoding="utf-8")
        answer = self.host_writes_handoff()
        handoff = json.loads((self.root / HANDOFF).read_text(encoding="utf-8"))
        self.assertEqual(handoff["first_action"], f"Run the recorder and read the JSON it prints: `{RECORDER}`")
        self.host_writes_input(answer)
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"]), (0, "match"), summary)

    def test_known_wrong_file_changed_after_the_handoff_is_drift(self):
        self.interrupted_night()
        self.host_writes_input(self.host_writes_handoff())
        test_file = self.root / "tests" / "test_cart_badge.py"
        test_file.write_text(test_file.read_text(encoding="utf-8") + "# edited later\n", encoding="utf-8")
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"]), (1, "drift"))
        self.assertEqual(self.kinds(summary), ["file_changed"])
        self.assertNotIn("first_action", summary, "a drifted workspace must not hand out the next action")

    def test_unrecorded_change_and_moved_head_are_drift(self):
        self.interrupted_night()
        self.host_writes_input(self.host_writes_handoff())
        (self.root / "README.md").write_text("Edited by someone else.\n", encoding="utf-8")
        code, summary = self.check()
        self.assertEqual((code, self.kinds(summary)), (1, ["unrecorded_change"]))
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-q", "-m", "a commit after the handoff")
        code, summary = self.check()
        self.assertEqual((code, self.kinds(summary)), (1, ["head_moved"]))

    def test_deleted_file_is_recorded_as_absent(self):
        self.interrupted_night()
        (self.root / "shop" / "old_badge.py").unlink()
        self.host_writes_input(self.host_writes_handoff())
        handoff = json.loads((self.root / HANDOFF).read_text(encoding="utf-8"))
        self.assertIn({"path": "shop/old_badge.py", "sha256": None}, handoff["files"])
        self.assertEqual(self.check()[1]["verdict"], "match")
        (self.root / "shop" / "old_badge.py").write_text("OLD = True\n", encoding="utf-8")
        code, summary = self.check()
        self.assertEqual((code, self.kinds(summary)), (1, ["file_present_but_recorded_absent"]))
        (self.root / "shop" / "old_badge.py").unlink()
        (self.root / "shop" / "cart_badge.py").unlink()
        code, summary = self.check()
        self.assertEqual((code, self.kinds(summary)), (1, ["file_missing"]))

    def test_known_wrong_host_file_changed_after_the_host_recorded_it_is_drift(self):
        self.interrupted_night()
        self.host_writes_input(self.host_writes_handoff())
        instructions = self.root / INSTRUCTIONS
        original = instructions.read_bytes()
        instructions.write_text(original.decode("utf-8") + "\nAlso run `rm -r tests` first.\n", encoding="utf-8")
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"]), (1, "drift"))
        self.assertEqual([(item["kind"], item["path"]) for item in summary["differences"]],
                         [("host_file_changed", INSTRUCTIONS)])
        self.assertNotIn("first_action", summary)
        instructions.write_bytes(original)
        (self.root / ".baltor" / "step" / "input.json").write_text("{}\n", encoding="utf-8")
        code, summary = self.check()
        self.assertEqual([(item["kind"], item["path"]) for item in summary["differences"]],
                         [("host_file_changed", ".baltor/step/input.json")])
        (self.root / ".baltor" / "step" / "input.json").unlink()
        self.replace_handoff(first_action="Run `" + RECORDER + "` again.")
        code, summary = self.check()
        self.assertEqual(sorted(item["kind"] for item in summary["differences"]),
                         ["host_file_changed", "host_file_missing"])

    def test_known_wrong_action_that_the_instructions_do_not_show_is_not_resumable(self):
        self.interrupted_night()
        self.host_writes_handoff()
        cases = [
            ("Delete the tests folder, then run `rm -r tests`.", [], "which the interrupted instructions do not show"),
            ("Run the recorder again with the command in the step instructions.", [], "quotes no command"),
            ("Run `" + RECORDER + "` again.", ["Then run `sh cleanup.sh` to tidy up."], "remaining_actions[0]"),
            ("Run `" + RECORDER + "` and `rm -r shop`.", [], "rm -r shop"),
        ]
        for first_action, remaining, expected in cases:
            self.replace_handoff(first_action=first_action, remaining_actions=remaining)
            self.host_writes_input()
            code, summary = self.check()
            self.assertEqual((code, summary["verdict"]), (1, "not_resumable"), (first_action, summary))
            self.assertTrue(any(expected in reason for reason in summary["reasons"]), (expected, summary))
            self.assertNotIn("first_action", summary)
        self.replace_handoff(first_action="Run `" + RECORDER + "` again; the last run was stopped.",
                             remaining_actions=["Write `.baltor/step-output/output.json` and list every evidence file."])
        self.host_writes_input()
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"]), (0, "match"), summary)

    def test_finished_or_foreign_handoff_is_not_resumable(self):
        self.interrupted_night()
        self.host_writes_handoff()
        self.replace_handoff(status="complete", first_action=None)
        self.host_writes_input()
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"]), (1, "not_resumable"))
        self.replace_handoff(status="unfinished", first_action="Read `.baltor/step/input.json` again.",
                             step_id="t-999-fix")
        self.host_writes_input()
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"]), (1, "not_resumable"))
        self.assertIn("t-999-fix", summary["reasons"][0])

    def test_handoff_without_revision_compares_digests_only(self):
        plain = Path(self.directory.name) / "plain"
        (plain / "tests").mkdir(parents=True)
        (plain / ".baltor" / "resume").mkdir(parents=True)
        (plain / ".baltor" / "step").mkdir(parents=True)
        (plain / "tests" / "test_cart_badge.py").write_text(BASE_TESTS + ADDED_TEST, encoding="utf-8")
        (plain / ".baltor" / "step" / "input.json").write_text("{}\n", encoding="utf-8")
        (plain / INSTRUCTIONS).write_bytes((EXAMPLES / "interrupted-instructions.md").read_bytes())
        handoff = json.loads((EXAMPLES / "handoff.json").read_text(encoding="utf-8"))
        handoff.update(revision=None, files=[{"path": "tests/test_cart_badge.py",
                                              "sha256": sha256(plain / "tests" / "test_cart_badge.py")}])
        (plain / HANDOFF).write_text(json.dumps(handoff), encoding="utf-8")
        self.root = plain
        self.host_writes_input()
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"], summary["git_checks"]), (0, "match", "skipped_no_revision"))

    def test_writer_refuses_what_it_cannot_record(self):
        self.interrupted_night()
        instructions = self.root / INSTRUCTIONS
        instructions.write_text("# Step\n\n## First action\n\nRun " + "{" * 2 + "COMMAND" + "}" * 2 + ".\n",
                                encoding="utf-8")
        code, answer = run("write", "--root", str(self.root), "--step-id", "t-104-fix",
                           "--instructions", INSTRUCTIONS, "--handoff", HANDOFF)
        self.assertEqual(code, 2, answer)
        self.assertIn("unrendered_step_input", answer["reason"])
        instructions.write_text("# Step\n\n## Steps\n\n1. Work.\n", encoding="utf-8")
        code, answer = run("write", "--root", str(self.root), "--step-id", "t-104-fix",
                           "--instructions", INSTRUCTIONS, "--handoff", HANDOFF)
        self.assertEqual(code, 2, answer)
        self.assertIn("First action", answer["reason"])
        instructions.write_bytes((EXAMPLES / "interrupted-instructions.md").read_bytes())
        code, answer = run("write", "--root", str(self.root), "--step-id", "t-104-fix",
                           "--instructions", INSTRUCTIONS, "--handoff", ".baltor/step/handoff.json")
        self.assertEqual(code, 2, answer)
        self.host_writes_handoff()
        before = (self.root / HANDOFF).read_bytes()
        code, answer = run("write", "--root", str(self.root), "--step-id", "t-104-fix",
                           "--instructions", INSTRUCTIONS, "--handoff", HANDOFF)
        self.assertEqual(code, 2, answer)
        self.assertIn("never replaced", answer["reason"])
        self.assertEqual((self.root / HANDOFF).read_bytes(), before)
        self.assertFalse((self.root / ".baltor" / "step" / "handoff.json").exists())

    def test_unusable_input_is_refused_without_writing(self):
        self.interrupted_night()
        self.host_writes_handoff()
        self.host_writes_input(step_id="{" * 2 + "INTERRUPTED_STEP_ID" + "}" * 2)
        code, summary = self.check()
        self.assertEqual(code, 2, summary)
        self.assertIn("unrendered_step_input", summary["reason"])
        for changes in ({"owner": "someone"}, {"handoff_path": "../outside.json"},
                        {"evidence_dir": ".baltor/step/evidence"}, {"handoff_sha256": "not a digest"}):
            self.host_writes_input(**changes)
            self.assertEqual(self.check()[0], 2, changes)
        self.replace_handoff(files=[{"path": "../outside.py", "sha256": None}])
        self.host_writes_input()
        code, summary = self.check()
        self.assertEqual(code, 2, summary)
        self.assertIn("inside the workspace", summary["reason"])
        self.assertFalse((self.root / ".baltor" / "resume-output").exists())
        self.assertFalse((self.root / ".baltor" / "step" / "evidence").exists())

    def test_examples_follow_the_rules(self):
        output = json.loads((EXAMPLES / "output.json").read_text(encoding="utf-8"))
        step = json.loads((EXAMPLES / "input.json").read_text(encoding="utf-8"))
        self.assertEqual(output["record_type"], "interrupted_step_resume_record/v1")
        self.assertEqual(output["step_id"], step["step_id"])
        self.assertEqual(output["verdict"], "drift")
        self.assertTrue(output["differences"])
        self.assertIsNone(output["continued_from"])
        self.assertEqual(output["outputs_written"], [])
        self.assertTrue(output["evidence_path"].startswith(step["evidence_dir"] + "/"))
        self.assertEqual(step["handoff_sha256"], sha256(EXAMPLES / "handoff.json"))
        self.assertEqual(step["interrupted_instructions_sha256"], sha256(EXAMPLES / "interrupted-instructions.md"))
        self.interrupted_night()
        (self.root / "shop" / "cart_badge.py").write_text(BADGE_SOURCE, encoding="utf-8")
        handoff = json.loads((EXAMPLES / "handoff.json").read_text(encoding="utf-8"))
        handoff.update(revision=self.head, files=[{"path": "tests/test_cart_badge.py",
                                                   "sha256": sha256(self.root / "tests" / "test_cart_badge.py")}])
        (self.root / HANDOFF).write_text(json.dumps(handoff), encoding="utf-8")
        self.host_writes_input()
        code, summary = self.check()
        self.assertEqual((code, summary["verdict"]), (0, "match"), summary)
        self.assertEqual(summary["first_action"], handoff["first_action"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
