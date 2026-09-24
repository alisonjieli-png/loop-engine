"""Tests for hooks/log_tool_activity.py. Effects: starts the hook with the running Python; writes workspaces and logs only inside temporary folders."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
HOOK = PAYLOAD / "hooks" / "log_tool_activity.py"
LOG_NAME = ".baltor/state/log-tool-activity/activity.jsonl"
SCRIPT_PLACE = ".baltor/log-tool-activity/hooks/log_tool_activity.py"
MARKER = "MARKER-VALUE-NOT-LOGGED"


def launch(arguments, root, cwd=None):
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}
    if root is not None:
        environment["CLAUDE_PROJECT_DIR"] = str(root)
        environment["CURSOR_PROJECT_DIR"] = str(root)
    return subprocess.Popen([sys.executable, "-I", "-B", str(HOOK), *arguments], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, cwd=str(cwd or root or PAYLOAD))


def run_hook(harness, event=None, *, root, raw=None, extra=(), cwd=None):
    data = raw if raw is not None else json.dumps(event).encode("utf-8")
    process = launch((["--harness", harness] if harness else []) + list(extra), root, cwd)
    stdout, stderr = process.communicate(data, timeout=30)
    if process.returncode != 0 or stdout != b"{}\n":
        raise AssertionError("exit %s, output %r, errors %r" % (process.returncode, stdout, stderr))
    return stderr.decode("utf-8")


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="activity-log-")
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def lines(self):
        path = self.root / LOG_NAME
        if not path.exists():
            return []
        text = path.read_text(encoding="ascii")
        self.assertNotIn(MARKER, text)
        return [json.loads(line) for line in text.splitlines()]

    def claude(self, tool, tool_input, name="PostToolUse", **fields):
        event = {"session_id": "test", "cwd": str(self.root), "hook_event_name": name, "tool_name": tool,
                 "tool_input": tool_input}
        event.update(fields)
        return run_hook("claude_code", event, root=self.root)


class Lines(Workspace):
    def test_shell_line_keeps_only_the_program_and_short_words(self):
        self.claude("Bash", {"command": "python3 -m pytest -q tests"}, tool_response={"stdout": MARKER})
        self.claude("Bash", {"command": "mytool --token=%s upload" % MARKER})
        self.claude("Bash", {"command": "PYTHONPATH=src ./scripts/run.sh --fast && rm -rf %s" % MARKER})
        self.claude("Bash", {"command": "git commit -m '%s'" % MARKER})
        targets = [line["target"] for line in self.lines()]
        self.assertEqual(targets, ["python3 -m pytest", "mytool", "run.sh --fast", "git commit -m"])

    def test_file_line_keeps_a_relative_path_and_never_the_contents(self):
        self.claude("Write", {"file_path": str(self.root / "src" / "app.py"), "content": MARKER})
        self.claude("Edit", {"file_path": str(self.root / "src" / "app.py"), "old_string": MARKER, "new_string": MARKER})
        self.claude("Read", {"file_path": "/elsewhere/notes.txt"}, tool_response={"content": MARKER})
        self.claude("Grep", {"pattern": MARKER, "path": str(self.root / "src")})
        self.claude("WebSearch", {"query": MARKER})
        targets = [line["target"] for line in self.lines()]
        self.assertEqual(targets, ["src/app.py", "src/app.py", "[outside workspace]", "src", ""])

    def test_line_fields_and_bounds(self):
        self.claude("mcp__" + "x" * 500, {"path": "a/" * 400 + "b.txt"})
        line = self.lines()[0]
        self.assertEqual(sorted(line), ["harness", "outcome", "record_type", "target", "time", "tool"])
        self.assertEqual(line["record_type"], "tool_activity/v1")
        self.assertLessEqual(len(line["tool"]), 64)
        self.assertLessEqual(len(line["target"]), 200)
        self.assertRegex(line["time"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_claude_outcomes(self):
        self.claude("Bash", {"command": "make"}, tool_response={"interrupted": True})
        self.claude("Bash", {"command": "make"}, name="PostToolUseFailure", error="Exit code 2")
        self.claude("Bash", {"command": "make"}, name="PostToolUseFailure", is_interrupt=True)
        self.assertEqual([line["outcome"] for line in self.lines()], ["interrupted", "failed", "interrupted"])


class OtherHarnesses(Workspace):
    def test_cursor_outcomes_and_output_never_copied(self):
        base = {"cwd": str(self.root), "tool_name": "Shell", "tool_input": {"command": "npm test"}}
        run_hook("cursor", dict(base, hook_event_name="postToolUse", tool_output=MARKER), root=self.root)
        for failure in ("timeout", "permission_denied", "error"):
            run_hook("cursor", dict(base, hook_event_name="postToolUseFailure", failure_type=failure,
                                    error_message=MARKER), root=self.root)
        self.assertEqual([line["outcome"] for line in self.lines()], ["ok", "timeout", "denied", "failed"])
        self.assertEqual(self.lines()[0]["target"], "npm test")

    def test_copilot_outcomes(self):
        for kind in ("success", "failure", "denied", "other"):
            event = {"cwd": str(self.root), "toolName": "edit", "toolArgs": json.dumps({"path": "src/a.py"}),
                     "toolResult": {"resultType": kind, "textResultForLlm": MARKER}}
            run_hook("copilot", event, root=self.root, cwd=self.root)
        self.assertEqual([line["outcome"] for line in self.lines()], ["ok", "failed", "denied", "unknown"])
        self.assertEqual({line["target"] for line in self.lines()}, {"src/a.py"})


class FailOpen(Workspace):
    def test_bad_events_are_not_recorded_and_exit_zero(self):
        for raw in (b"{", b"[]", b" " * (1024 * 1024 + 1), b'{"hook_event_name": "PostToolUse"}',
                    b'{"hook_event_name": "PreToolUse", "tool_name": "Bash"}'):
            errors = run_hook("claude_code", raw=raw, root=self.root)
            self.assertIn("not recorded", errors)
        self.assertEqual(self.lines(), [])

    def test_bad_registration_and_unknown_root(self):
        self.assertIn("no valid --harness", run_hook(None, {"hook_event_name": "PostToolUse"}, root=self.root))
        self.assertIn("no valid --harness", run_hook("unknown", {"hook_event_name": "PostToolUse"}, root=self.root))
        event = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}
        self.assertIn("root is unknown", run_hook("claude_code", event, root=None))

    def test_links_are_never_followed(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / ".baltor").symlink_to(outside, target_is_directory=True)
        self.assertIn("symbolic link", self.claude("Bash", {"command": "ls"}))
        self.assertEqual(list(outside.iterdir()), [])
        (self.root / ".baltor").unlink()
        folder = self.root / ".baltor" / "state" / "log-tool-activity"
        folder.mkdir(parents=True)
        (folder / "activity.jsonl").symlink_to(outside / "elsewhere.jsonl")
        self.assertIn("cannot be opened", self.claude("Bash", {"command": "ls"}))
        self.assertEqual(list(outside.iterdir()), [])

    def test_full_log_gets_one_marker_and_stays_bounded(self):
        for _ in range(40):
            run_hook("claude_code", {"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": str(self.root),
                                     "tool_input": {"command": "python3 -m pytest"}}, root=self.root,
                     extra=["--max-log-bytes", "4096"])
        lines = self.lines()
        self.assertEqual([line["outcome"] for line in lines].count("log_full"), 1)
        self.assertEqual(lines[-1]["outcome"], "log_full")
        self.assertLessEqual((self.root / LOG_NAME).stat().st_size, 4096)

    def test_parallel_calls_write_whole_lines(self):
        data = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": str(self.root),
                           "tool_input": {"command": "python3 -m pytest"}}).encode("utf-8")
        processes = [launch(["--harness", "claude_code"], self.root) for _ in range(10)]
        for process in processes:
            process.communicate(data, timeout=30)
        self.assertEqual(len(self.lines()), 10)


class ShippedFiles(unittest.TestCase):
    def test_samples_exit_zero_and_record_only_the_recorded_ones(self):
        samples = sorted((PAYLOAD / "examples").glob("*-posttooluse-*.json"))
        self.assertEqual(len(samples), 6)
        for sample in samples:
            harness = sample.name.split("-", 1)[0]
            with tempfile.TemporaryDirectory(prefix="activity-log-sample-") as folder:
                root = Path(folder)
                text = sample.read_text(encoding="utf-8").replace("/work", str(root))
                run_hook(harness, raw=text.encode("utf-8"), root=root, cwd=root)
                log = root / LOG_NAME
                recorded = log.exists() and log.read_text(encoding="ascii").count("\n") == 1
                self.assertEqual(recorded, not sample.stem.endswith("-not-recorded"), sample.name)
                if recorded:
                    self.assertNotIn("SAMPLE-OUTPUT-NOT-LOGGED", log.read_text(encoding="ascii"))

    def test_variants_register_this_script(self):
        claude = json.loads((PAYLOAD / "variants/claude_code/settings.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(sorted(claude), ["PostToolUse", "PostToolUseFailure"])
        for entries in claude.values():
            self.assertEqual(entries[0]["matcher"], "*")
            self.assertIn("$CLAUDE_PROJECT_DIR/" + SCRIPT_PLACE, entries[0]["hooks"][0]["command"])
        cursor = json.loads((PAYLOAD / "variants/cursor/hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(sorted(cursor), ["postToolUse", "postToolUseFailure"])
        copilot = json.loads((PAYLOAD / "variants/copilot/log-tool-activity.json").read_text(encoding="utf-8"))
        self.assertIn(SCRIPT_PLACE + " --harness copilot", copilot["hooks"]["postToolUse"][0]["bash"])
        self.assertEqual(Path(SCRIPT_PLACE).name, HOOK.name)


if __name__ == "__main__":
    unittest.main()
