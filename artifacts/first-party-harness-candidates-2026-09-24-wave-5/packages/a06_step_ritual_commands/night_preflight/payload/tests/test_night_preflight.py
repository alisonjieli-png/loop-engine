"""Tests for scripts/night_preflight.py and the command variants. Effects: writes only inside temporary folders; starts the script and small synthetic test programs with the current interpreter, and loads the script by its exact path to test the guard rules directly."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "night_preflight.py"
EXAMPLES = PAYLOAD / "examples"
VARIANTS = PAYLOAD / "variants"
PLACED_SCRIPT = ".baltor/night-preflight/scripts/night_preflight.py"
HEADINGS = ("## Purpose", "## First action", "## Steps", "## Output", "## Stop and report when")
GUARD = '{"permissions": {"deny": ["Bash(git push *)"]}}\n'
HELPER_PROGRAM = ("import pathlib, subprocess, sys, time\n"
                  "subprocess.Popen([sys.executable, '-c', 'import pathlib, time; time.sleep(3); "
                  "pathlib.Path(\"helper-ran.txt\").write_text(\"x\")'])\n"
                  "time.sleep(30)\n")


def run(root: Path, *arguments: str) -> tuple[int, dict]:
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments, "--root", str(root)],
                              capture_output=True, text=True, timeout=120)
    return finished.returncode, json.loads(finished.stdout)


def load_helper():
    spec = importlib.util.spec_from_file_location("night_preflight_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NightPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        (self.root / ".baltor" / "night").mkdir(parents=True)
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "settings.json").write_text(GUARD, encoding="utf-8")
        (self.root / "check_ok.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        (self.root / "check_fails.py").write_text("print('one test failed')\nraise SystemExit(3)\n", encoding="utf-8")
        (self.root / "check_slow.py").write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
        (self.root / "check_with_helper.py").write_text(HELPER_PROGRAM, encoding="utf-8")
        (self.root / "check_loud.py").write_text("for number in range(20000):\n    print('x' * 60)\nprint('last line')\n",
                                                 encoding="utf-8")
        self.settings = json.loads((EXAMPLES / "settings.json").read_text(encoding="utf-8"))
        self.settings.update({"test_command": [sys.executable, "-I", "-B", "check_ok.py"], "test_timeout_seconds": 60})
        self.save_settings()
        self.queue_path = self.root / ".baltor" / "night" / "queue.json"
        self.queue_path.write_bytes((EXAMPLES / "queue.json").read_bytes())

    def tearDown(self) -> None:
        self.folder.cleanup()

    def save_settings(self) -> None:
        (self.root / ".baltor" / "night" / "settings.json").write_text(json.dumps(self.settings), encoding="utf-8")

    def probe_and_check(self) -> tuple[int, dict]:
        code, probe = run(self.root, "probe")
        self.assertEqual(code, 0, probe)
        return run(self.root, "check", "--nonce", probe["nonce"])

    def test_go_after_a_real_probe_round_trip(self) -> None:
        code, report = self.probe_and_check()
        self.assertEqual(code, 0, report)
        self.assertEqual((report["decision"], report["failed"]), ("go", []))
        self.assertEqual([check["name"] for check in report["checks"]],
                         ["structured_tool_calls", "budgets", "guards", "queue", "test_command"])
        self.assertTrue((self.root / report["test_output"]).is_file())
        saved = json.loads((self.root / report["report_path"]).read_text(encoding="utf-8"))
        self.assertEqual(saved["decision"], "go")
        example = json.loads((EXAMPLES / "report-go.json").read_text(encoding="utf-8"))
        self.assertEqual(set(example), set(saved))
        self.assertEqual(set(example["test_command"]), set(saved["test_command"]))
        self.assertEqual([check["name"] for check in example["checks"]], [check["name"] for check in saved["checks"]])

    def test_known_wrong_report_without_the_command_is_fixed(self) -> None:
        code, probe = run(self.root, "probe")
        self.assertEqual(probe["will_run"]["argv"], self.settings["test_command"])
        self.assertEqual((probe["will_run"]["cwd"], probe["will_run"]["timeout_seconds"]), (".", 60))
        code, report = run(self.root, "check", "--nonce", probe["nonce"])
        saved = (self.root / report["report_path"]).read_text(encoding="utf-8")
        self.assertIn("check_ok.py", saved)
        self.assertEqual(report["test_command"]["argv"], self.settings["test_command"])
        self.assertIn("check_ok.py", (self.root / report["test_output"]).read_text(encoding="utf-8").splitlines()[0])

    def test_known_wrong_invented_or_missing_nonce_is_no_go(self) -> None:
        code, probe = run(self.root, "probe")
        invented = "0123456789ab" if probe["nonce"] != "0123456789ab" else "ba9876543210"
        code, report = run(self.root, "check", "--nonce", invented)
        self.assertEqual((code, report["decision"], report["failed"]), (1, "no-go", ["structured_tool_calls"]))
        self.assertIn("not read from a real probe", report["checks"][0]["detail"])
        code, report = run(self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("run probe first", report["checks"][0]["detail"])
        code, report = run(self.root, "check", "--nonce", "{nonce}")
        self.assertEqual(code, 1)
        self.assertIn("12 lower-case hex", report["checks"][0]["detail"])

    def test_a_nonce_works_once_and_a_stale_probe_fails(self) -> None:
        code, probe = run(self.root, "probe")
        self.assertEqual(run(self.root, "check", "--nonce", probe["nonce"])[0], 0)
        code, report = run(self.root, "check", "--nonce", probe["nonce"])
        self.assertEqual(code, 1)
        self.assertIn("used before", report["checks"][0]["detail"])
        code, probe = run(self.root, "probe")
        path = self.root / ".baltor" / "state" / "night-preflight" / f"probe-{probe['nonce']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["created_epoch"] = int(time.time()) - 3600
        path.write_text(json.dumps(record), encoding="utf-8")
        code, report = run(self.root, "check", "--nonce", probe["nonce"])
        self.assertEqual(code, 1)
        self.assertIn("older than 15 minutes", report["checks"][0]["detail"])

    def test_known_wrong_empty_or_permissive_guard_files_are_no_go(self) -> None:
        cases = {"{}\n": "is not one nonempty strict JSON object",
                 json.dumps({"permissions": {"allow": ["Bash(*)"], "defaultMode": "bypassPermissions"}}):
                     "bypassPermissions",
                 json.dumps({"permissions": {"allow": ["Bash"], "deny": ["Bash(git push *)"]}}):
                     "allows every shell command",
                 json.dumps({"permissions": {"allow": ["Bash(python3 -m unittest *)"]}}): "holds no guard rule"}
        for text, expected in cases.items():
            with self.subTest(text):
                (self.root / ".claude" / "settings.json").write_text(text, encoding="utf-8")
                code, report = self.probe_and_check()
                self.assertEqual((code, report["failed"]), (1, ["guards"]))
                self.assertIn(expected, report["checks"][2]["detail"])

    def test_guard_rules_per_recognized_file(self) -> None:
        helper = load_helper()
        claude_hooks = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 guard.py"}]}]}}
        cases = [
            ("claude_code_settings", claude_hooks, [], ["hook commands"]),
            ("claude_code_settings", {"permissions": {"defaultMode": "dontAsk", "allow": ["Read"]}}, [], ["default mode dontAsk"]),
            ("claude_code_settings", {"sandbox": {"enabled": True}}, [], ["sandbox"]),
            ("cursor_hooks", {"version": 1, "hooks": {"beforeShellExecution": [{"command": "python3 guard.py"}]}}, [], ["hook commands"]),
            ("cursor_hooks", {"version": 1, "hooks": {"beforeShellExecution": []}}, [], []),
            ("copilot_hooks", {"version": 1, "hooks": {"preToolUse": [{"type": "command", "bash": "python3 guard.py"}]}}, [], ["hook commands"]),
            ("opencode_config", {"permission": {"bash": {"*": "deny", "python3 -m unittest *": "allow"}}}, [], ["deny rules"]),
            ("opencode_config", {"permission": {"bash": "allow"}}, ["allows every shell command through its permission setting"], []),
            ("gemini_settings", {"tools": {"core": ["read_file"]}}, [], ["tool lists"]),
        ]
        for kind, value, problems, guards in cases:
            with self.subTest(kind=kind, value=value):
                self.assertEqual(helper.inspect_guard(kind, value), (problems, guards))
        self.assertEqual(helper.guard_kind(".github/hooks/guard.json"), "copilot_hooks")
        self.assertEqual(helper.guard_kind("guards/policy.json"), "unrecognized")
        (self.root / "guards").mkdir()
        (self.root / "guards" / "policy.json").write_text('{"rules": ["no pushes"]}\n', encoding="utf-8")
        self.settings["guard_files"] = ["guards/policy.json"]
        self.save_settings()
        code, report = self.probe_and_check()
        self.assertEqual(report["failed"], ["guards"])
        self.assertIn("no listed file is a recognized guard file", report["checks"][2]["detail"])

    def test_failing_slow_missing_or_shell_string_test_commands_are_no_go(self) -> None:
        for script, expected in (("check_fails.py", "exit 3"), ("check_slow.py", "did not finish in 1 seconds")):
            self.settings.update({"test_command": [sys.executable, "-I", "-B", script], "test_timeout_seconds": 1})
            self.save_settings()
            code, report = self.probe_and_check()
            self.assertEqual((code, report["failed"]), (1, ["test_command"]), script)
            self.assertIn(expected, report["checks"][-1]["detail"])
        output = (self.root / ".baltor" / "state" / "night-preflight").glob("test-output-*.txt")
        self.assertTrue(any("one test failed" in path.read_text(encoding="utf-8") for path in output))
        for command, expected in (("python3 -m unittest", "never run through a shell"),
                                  (["no-such-program-for-preflight"], "was not found")):
            self.settings["test_command"] = command
            self.save_settings()
            code, report = self.probe_and_check()
            self.assertEqual(code, 1)
            self.assertIn(expected, report["checks"][-1]["detail"])

    def test_a_timed_out_test_command_is_stopped_with_what_it_started(self) -> None:
        self.settings.update({"test_command": [sys.executable, "-I", "-B", "check_with_helper.py"],
                              "test_timeout_seconds": 1})
        self.save_settings()
        code, report = self.probe_and_check()
        self.assertEqual(code, 1)
        self.assertIn("was stopped with the processes it started", report["checks"][-1]["detail"])
        time.sleep(4)
        self.assertFalse((self.root / "helper-ran.txt").exists())

    def test_long_output_keeps_only_its_tail(self) -> None:
        self.settings["test_command"] = [sys.executable, "-I", "-B", "check_loud.py"]
        self.save_settings()
        code, report = self.probe_and_check()
        self.assertEqual(code, 0, report)
        saved = (self.root / report["test_output"]).read_bytes()
        header, _, tail = saved.partition(b"\n")
        self.assertLessEqual(len(tail), 64 * 1024)
        self.assertTrue(tail.rstrip().endswith(b"last line"))
        self.assertIn(b"1220010 bytes of output", header)

    def test_missing_budget_guard_and_empty_queue_are_reported_together(self) -> None:
        del self.settings["model_calls"]
        self.settings["guard_files"] = [".claude/settings.json", "../outside.json", ".cursor/hooks.json"]
        self.save_settings()
        queue = json.loads(self.queue_path.read_text(encoding="utf-8"))
        stamp = "2026-09-23T21:00:00Z"
        tickets = {item["id"]: {"status": "blocked", "blocker": f".baltor/night/blockers/{item['id']}.md",
                                "changes": [{"from": "queued", "to": "blocked", "at": stamp, "by": "record-blocker"}]}
                   for item in queue["items"]}
        status = {"record_type": "night_queue_status/v1",
                  "queue_sha256": hashlib.sha256(self.queue_path.read_bytes()).hexdigest(), "tickets": tickets}
        status_path = self.root / ".baltor" / "night" / "queue-status.json"
        status_path.write_text(json.dumps(status), encoding="utf-8")
        code, report = self.probe_and_check()
        self.assertEqual((code, report["failed"]), (1, ["budgets", "guards", "queue"]))
        details = {check["name"]: check["detail"] for check in report["checks"]}
        self.assertIn("model_calls", details["budgets"])
        self.assertIn("../outside.json is outside the workspace", details["guards"])
        self.assertIn(".cursor/hooks.json is missing", details["guards"])
        self.assertIn("holds no queued or in_progress ticket", details["queue"])
        status["queue_sha256"] = "0" * 64
        status_path.write_text(json.dumps(status), encoding="utf-8")
        code, report = self.probe_and_check()
        self.assertIn("belongs to another queue", {check["name"]: check["detail"] for check in report["checks"]}["queue"])

    def test_missing_or_unversioned_settings_give_no_go_not_a_crash(self) -> None:
        settings_path = self.root / ".baltor" / "night" / "settings.json"
        del self.settings["record_type"]
        self.save_settings()
        code, report = self.probe_and_check()
        self.assertEqual((code, report["failed"]), (1, ["budgets", "guards", "test_command"]))
        self.assertIn("record_type night_settings/v1", report["checks"][1]["detail"])
        settings_path.unlink()
        code, report = self.probe_and_check()
        self.assertEqual((code, report["failed"]), (1, ["budgets", "guards", "test_command"]))
        self.assertIsNone(report["test_output"])
        self.assertIsNone(report["test_command"])

    def test_every_variant_names_the_placed_script_and_the_headings(self) -> None:
        variants = sorted(path for path in VARIANTS.rglob("*") if path.is_file())
        self.assertEqual(len(variants), 5)
        for path in variants:
            text = path.read_text(encoding="utf-8")
            for expected in (PLACED_SCRIPT, "# Run an overnight preflight check", "--nonce NONCE", "will_run"):
                self.assertIn(expected, text, path.name)
            for heading in HEADINGS:
                self.assertIn(heading, text.splitlines(), f"{path.name} lacks {heading}")
        copilot = (VARIANTS / "copilot" / "night-preflight.prompt.md").read_text(encoding="utf-8")
        self.assertIn("\nagent: agent\n", copilot.split("---")[1] + "\n")
        self.assertTrue(SCRIPT.is_file())


if __name__ == "__main__":
    unittest.main()
