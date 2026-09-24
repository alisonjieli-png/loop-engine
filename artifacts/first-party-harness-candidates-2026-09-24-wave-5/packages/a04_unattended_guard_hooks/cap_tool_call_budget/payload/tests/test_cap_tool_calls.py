"""Tests for hooks/cap_tool_calls.py. Effects: starts the hook with the running Python; writes workspaces and counters only inside temporary folders."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import fcntl
except ImportError:  # the lock test needs fcntl
    fcntl = None

PAYLOAD = Path(__file__).resolve().parent.parent
HOOK = PAYLOAD / "hooks" / "cap_tool_calls.py"
POLICY_NAME = ".baltor/step/cap-tool-call-budget.json"
STATE_NAME = ".baltor/state/cap-tool-call-budget/state.json"
SCRIPT_PLACE = ".baltor/cap-tool-call-budget/hooks/cap_tool_calls.py"
DEFAULT_POLICY = PAYLOAD / "defaults" / "cap-tool-call-budget.json"
CURSOR_ALLOW = {"permission": "allow"}


def launch(arguments, root, cwd=None):
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}
    if root is not None:
        environment["CLAUDE_PROJECT_DIR"] = str(root)
        environment["CURSOR_PROJECT_DIR"] = str(root)
    return subprocess.Popen([sys.executable, "-I", "-B", str(HOOK), *arguments], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, cwd=str(cwd or root or PAYLOAD))


def answer_of(process, data):
    stdout, stderr = process.communicate(data, timeout=30)
    lines = stdout.decode("utf-8").splitlines()
    if process.returncode != 0 or len(lines) != 1:
        raise AssertionError("exit %s, output %r, errors %r" % (process.returncode, stdout, stderr))
    return json.loads(lines[0])


def run_hook(harness, event=None, *, root, raw=None, extra=(), cwd=None):
    data = raw if raw is not None else json.dumps(event).encode("utf-8")
    return answer_of(launch((["--harness", harness] if harness else []) + list(extra), root, cwd), data)


def reason_of(answer):
    if "hookSpecificOutput" in answer:
        output = answer["hookSpecificOutput"]
        return output["permissionDecisionReason"] if output.get("permissionDecision") == "deny" else None
    if answer.get("permission") == "deny":
        return answer["agent_message"]
    if answer.get("permissionDecision") == "deny":
        return answer["permissionDecisionReason"]
    return None


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tool-budget-")
        self.root = Path(self.temp.name) / "workspace"
        (self.root / ".baltor" / "step").mkdir(parents=True)
        self.write_policy("step-1", 3)

    def tearDown(self):
        self.temp.cleanup()

    def write_policy(self, step_id, ceiling, **fields):
        policy = {"record_type": "tool_call_budget_policy/v1", "step_id": step_id, "max_tool_calls": ceiling,
                  "handoff_path": ".baltor/step/handoff.md", "max_handoff_calls": 2}
        policy.update(fields)
        (self.root / POLICY_NAME).write_text(json.dumps(policy), encoding="utf-8")

    def state(self):
        return json.loads((self.root / STATE_NAME).read_text(encoding="utf-8"))

    def call(self, tool="Bash", tool_input=None):
        return reason_of(self.claude_answer(tool, tool_input))

    def claude_answer(self, tool="Bash", tool_input=None):
        event = {"session_id": "test", "cwd": str(self.root), "hook_event_name": "PreToolUse", "tool_name": tool,
                 "tool_input": tool_input if tool_input is not None else {"command": "ls"}}
        return run_hook("claude_code", event, root=self.root)

    def handoff(self, tool="Write", path=None):
        return self.call(tool, {"file_path": str(path or self.root / ".baltor" / "step" / "handoff.md"), "content": "x"})


class Counting(Workspace):
    def test_calls_up_to_the_ceiling_pass_and_the_next_is_refused(self):
        for _ in range(3):
            self.assertIsNone(self.call())
        reason = self.call()
        self.assertIn("used all 3 of its tool calls", reason)
        self.assertIn(".baltor/step/handoff.md", reason)
        self.assertEqual(self.state()["calls_used"], 3)
        self.assertEqual(self.state()["refused_calls"], 1)

    def test_handoff_file_stays_reachable_for_a_small_allowance(self):
        for _ in range(3):
            self.call()
        self.assertIsNone(self.handoff("Read"))
        self.assertIsNone(self.handoff("Write"))
        reason = self.handoff("Edit")
        self.assertIn("handoff allowance", reason)
        self.assertIn("final message", reason)

    def test_only_file_calls_on_the_exact_handoff_path_are_exempt(self):
        self.write_policy("step-1", 0)
        self.assertIsNotNone(self.call("Bash", {"command": "cat .baltor/step/handoff.md"}))
        self.assertIsNotNone(self.handoff(path=self.root / ".baltor" / "step" / "notes.md"))
        self.assertIsNone(self.handoff(path=str(self.root / "src") + "/../.baltor/step/handoff.md"))

    def test_handoff_path_behind_a_link_is_not_exempt(self):
        self.write_policy("step-1", 0)
        outside = Path(self.temp.name) / "outside.md"
        (self.root / ".baltor" / "step" / "handoff.md").symlink_to(outside)
        self.assertIsNotNone(self.handoff())
        (self.root / ".baltor" / "step" / "handoff.md").unlink()
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
        (self.root / ".baltor" / "step" / "handoff.md").symlink_to(self.root / "src" / "app.py")
        self.assertIsNotNone(self.handoff())

    def test_zero_allowance_says_to_finish_in_the_final_message(self):
        self.write_policy("step-1", 0, max_handoff_calls=0)
        self.assertIn("final message", self.handoff())

    def test_new_step_identity_starts_a_new_count(self):
        for _ in range(4):
            self.call()
        self.write_policy("step-2", 3)
        self.assertIsNone(self.call())
        self.assertEqual(self.state()["calls_used"], 1)

    def test_claude_code_session_ends_after_the_refused_call_limit(self):
        self.write_policy("step-1", 1, max_refused_calls=2)
        self.assertEqual(self.claude_answer(), {})
        first = self.claude_answer()
        self.assertIsNotNone(reason_of(first))
        self.assertNotIn("continue", first)
        second = self.claude_answer()
        self.assertIs(second["continue"], False)
        self.assertIn("ended the session", second["stopReason"])
        self.assertEqual(second["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIs(self.claude_answer()["continue"], False)
        self.assertEqual(self.state()["refused_calls"], 3)

    def test_handoff_calls_do_not_count_as_refused_calls(self):
        self.write_policy("step-1", 0, max_refused_calls=2)
        self.assertNotIn("continue", self.claude_answer())
        self.assertIsNone(self.handoff("Write"))
        self.assertIsNone(self.handoff("Edit"))
        self.assertIs(self.claude_answer()["continue"], False)

    def test_other_harnesses_keep_refusing_without_an_end_answer(self):
        self.write_policy("step-1", 0, max_refused_calls=1)
        shell = {"hook_event_name": "preToolUse", "tool_name": "Shell", "cwd": str(self.root),
                 "tool_input": {"command": "npm test"}}
        bash = {"cwd": str(self.root), "toolName": "bash", "toolArgs": json.dumps({"command": "ls"})}
        for _ in range(2):
            cursor = run_hook("cursor", shell, root=self.root)
            self.assertEqual(cursor["permission"], "deny")
            self.assertNotIn("continue", cursor)
            copilot = run_hook("copilot", bash, root=self.root, cwd=self.root)
            self.assertEqual(copilot["permissionDecision"], "deny")
            self.assertNotIn("continue", copilot)

    @unittest.skipIf(fcntl is None, "fcntl is not available")
    def test_counting_waits_for_the_state_lock(self):
        self.assertIsNone(self.call())
        lock_path = self.root / ".baltor" / "state" / "cap-tool-call-budget" / "lock"
        data = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(self.root),
                           "tool_input": {"command": "ls"}}).encode("utf-8")
        with open(lock_path, "ab") as holder:
            fcntl.flock(holder, fcntl.LOCK_EX)
            process = launch(["--harness", "claude_code"], self.root)
            process.stdin.write(data)
            process.stdin.close()
            try:
                process.wait(timeout=4)
                answered_while_locked = True
            except subprocess.TimeoutExpired:
                answered_while_locked = False
            fcntl.flock(holder, fcntl.LOCK_UN)
        stdout = process.stdout.read()
        process.stdout.close()
        process.stderr.close()
        process.wait(timeout=30)
        self.assertFalse(answered_while_locked)
        self.assertEqual(json.loads(stdout), {})
        self.assertEqual(self.state()["calls_used"], 2)

    def test_parallel_calls_never_pass_the_ceiling(self):
        self.write_policy("step-1", 5)
        data = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(self.root),
                           "tool_input": {"command": "ls"}}).encode("utf-8")
        processes = [launch(["--harness", "claude_code"], self.root) for _ in range(10)]
        answers = [answer_of(process, data) for process in processes]
        self.assertEqual(sum(1 for answer in answers if answer == {}), 5)
        self.assertEqual(self.state()["calls_used"], 5)
        self.assertEqual(self.state()["refused_calls"], 5)


class FailClosed(Workspace):
    def test_malformed_events_are_refused(self):
        for raw, fragment in ((b"{", "not valid JSON"), (b"[]", "not a JSON object"),
                              (b" " * (1024 * 1024 + 1), "larger than 1 MiB"),
                              (b'{"hook_event_name": "PreToolUse"}', "names no tool")):
            self.assertIn(fragment, reason_of(run_hook("claude_code", raw=raw, root=self.root)))

    def test_missing_or_invalid_policy_refuses_every_call(self):
        (self.root / POLICY_NAME).unlink()
        self.assertIn("no budget policy file", self.call())
        self.write_policy("step-1", -1)
        self.assertIn("max_tool_calls", self.call())
        self.write_policy("bad id with spaces", 3)
        self.assertIn("step_id", self.call())
        self.write_policy("step-1", 3, max_refused_calls=0)
        self.assertIn("max_refused_calls", self.call())

    def test_unreadable_state_and_linked_state_folder_are_refused(self):
        self.call()
        (self.root / STATE_NAME).write_text("{}", encoding="utf-8")
        self.assertIn("state file", self.call())
        shutil.rmtree(self.root / ".baltor" / "state")
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / ".baltor" / "state").symlink_to(outside, target_is_directory=True)
        self.assertIn("symbolic link", self.call())
        self.assertEqual(list(outside.iterdir()), [])

    def test_unknown_root_and_missing_harness(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}
        self.assertIn("root is unknown", reason_of(run_hook("claude_code", event, root=None)))
        process = launch([], self.root)
        process.communicate(json.dumps(event).encode("utf-8"), timeout=30)
        self.assertEqual(process.returncode, 2)

    def test_policy_check_command(self):
        process = launch(["--check-policy", "--root", str(self.root)], self.root)
        stdout, _ = process.communicate(b"", timeout=30)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(json.loads(stdout)["max_tool_calls"], 3)
        process = launch(["--check-policy", "--root", str(self.root), "--policy",
                          str(PAYLOAD / "examples" / "invalid-policy.json")], self.root)
        process.communicate(b"", timeout=30)
        self.assertEqual(process.returncode, 1)


class OtherHarnesses(Workspace):
    def test_cursor_and_copilot_count_and_answer_in_their_shapes(self):
        self.write_policy("step-1", 1)
        shell = {"hook_event_name": "preToolUse", "tool_name": "Shell", "cwd": str(self.root),
                 "tool_input": {"command": "npm test"}}
        self.assertEqual(run_hook("cursor", shell, root=self.root), CURSOR_ALLOW)
        refused = run_hook("cursor", shell, root=self.root)
        self.assertEqual(refused["permission"], "deny")
        self.assertEqual(refused["user_message"], refused["agent_message"])
        write = dict(shell, tool_name="Write", tool_input={"file_path": str(self.root / ".baltor/step/handoff.md")})
        self.assertEqual(run_hook("cursor", write, root=self.root), CURSOR_ALLOW)
        bash = {"cwd": str(self.root), "toolName": "bash", "toolArgs": json.dumps({"command": "ls"})}
        self.assertEqual(run_hook("copilot", bash, root=self.root, cwd=self.root)["permissionDecision"], "deny")
        create = {"cwd": str(self.root), "toolName": "create", "toolArgs": json.dumps({"path": ".baltor/step/handoff.md"})}
        self.assertEqual(run_hook("copilot", create, root=self.root, cwd=self.root), {})
        self.assertIn("could not read this tool call",
                      reason_of(run_hook("copilot", {"cwd": str(self.root)}, root=self.root, cwd=self.root)))

    def test_other_events_are_left_alone(self):
        event = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}
        self.assertEqual(run_hook("claude_code", event, root=self.root), {})
        self.assertEqual(run_hook("cursor", {"hook_event_name": "stop", "status": "completed"}, root=self.root),
                         CURSOR_ALLOW)
        self.assertFalse((self.root / STATE_NAME).exists())


class DefaultPolicy(unittest.TestCase):
    """The file the package places at .baltor/step/cap-tool-call-budget.json."""

    def test_default_policy_is_valid(self):
        process = launch(["--check-policy", "--root", str(PAYLOAD), "--policy", str(DEFAULT_POLICY)], None)
        stdout, _ = process.communicate(b"", timeout=30)
        self.assertEqual(process.returncode, 0, stdout)
        document = json.loads(stdout)
        self.assertEqual((document["max_tool_calls"], document["max_refused_calls"]), (200, 5))
        self.assertEqual(document["handoff_path"], ".baltor/step/handoff.md")


class ShippedFiles(unittest.TestCase):
    def test_samples_give_the_expected_answers(self):
        samples = sorted((PAYLOAD / "examples").glob("*-pretooluse-*.json"))
        self.assertEqual(len(samples), 6)
        for sample in samples:
            harness = sample.name.split("-", 1)[0]
            with tempfile.TemporaryDirectory(prefix="tool-budget-sample-") as folder:
                copy = Path(folder) / "payload"
                shutil.copytree(PAYLOAD, copy)
                text = sample.read_text(encoding="utf-8").replace("/work/", str(copy) + "/")
                answer = run_hook(harness, raw=text.encode("utf-8"), root=copy, cwd=copy,
                                  extra=["--root", "examples/budget-spent"])
                if sample.stem.endswith("-allowed"):
                    self.assertEqual(answer, CURSOR_ALLOW if harness == "cursor" else {}, sample.name)
                else:
                    self.assertIn("used all 40 of its tool calls", reason_of(answer), sample.name)

    def test_variants_register_this_script(self):
        claude = json.loads((PAYLOAD / "variants/claude_code/settings.json").read_text(encoding="utf-8"))
        entry = claude["hooks"]["PreToolUse"][0]
        self.assertEqual(entry["matcher"], "*")
        self.assertIn("$CLAUDE_PROJECT_DIR/" + SCRIPT_PLACE, entry["hooks"][0]["command"])
        cursor = json.loads((PAYLOAD / "variants/cursor/hooks.json").read_text(encoding="utf-8"))
        self.assertTrue(cursor["hooks"]["preToolUse"][0]["failClosed"])
        copilot = json.loads((PAYLOAD / "variants/copilot/cap-tool-call-budget.json").read_text(encoding="utf-8"))
        self.assertIn(SCRIPT_PLACE + " --harness copilot", copilot["hooks"]["preToolUse"][0]["bash"])
        self.assertEqual(Path(SCRIPT_PLACE).name, HOOK.name)


if __name__ == "__main__":
    unittest.main()
