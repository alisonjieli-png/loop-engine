"""Tests for hooks/require_tests_before_stop.py. Effects: starts the hook with the running Python; writes workspaces and state only inside temporary folders."""
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
HOOK = PAYLOAD / "hooks" / "require_tests_before_stop.py"
POLICY_NAME = ".baltor/step/require-tests-before-stop.json"
STATE_NAME = ".baltor/state/require-tests-before-stop/state.json"
SCRIPT_PLACE = ".baltor/require-tests-before-stop/hooks/require_tests_before_stop.py"
DEFAULT_POLICY = PAYLOAD / "defaults" / "require-tests-before-stop.json"


def launch(arguments, data, root, cwd=None):
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8",
                   "CLAUDE_PROJECT_DIR": str(root), "CURSOR_PROJECT_DIR": str(root)}
    return subprocess.Popen([sys.executable, "-I", "-B", str(HOOK), *arguments], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, cwd=str(cwd or root))


def run_hook(harness, event=None, *, root, raw=None, extra=(), cwd=None):
    arguments = (["--harness", harness] if harness else []) + list(extra)
    data = raw if raw is not None else json.dumps(event).encode("utf-8")
    process = launch(arguments, data, root, cwd)
    stdout, stderr = process.communicate(data, timeout=30)
    lines = stdout.decode("utf-8").splitlines()
    if process.returncode != 0 or len(lines) != 1:
        raise AssertionError("exit %s, output %r, errors %r" % (process.returncode, stdout, stderr))
    return json.loads(lines[0]), stderr.decode("utf-8")


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tests-before-stop-")
        self.root = Path(self.temp.name) / "workspace"
        (self.root / ".baltor" / "step").mkdir(parents=True)
        self.write_policy("step-1")

    def tearDown(self):
        self.temp.cleanup()

    def write_policy(self, step_id, **fields):
        policy = {"record_type": "tests_before_stop_policy/v1", "step_id": step_id,
                  "test_commands": [["python3", "-m", "pytest"], ["make", "test"]],
                  "source_globs": ["src/**", "tests/**"]}
        policy.update(fields)
        (self.root / POLICY_NAME).write_text(json.dumps(policy), encoding="utf-8")

    def state(self):
        return json.loads((self.root / STATE_NAME).read_text(encoding="utf-8"))

    def claude(self, name, **fields):
        event = {"session_id": "test", "cwd": str(self.root), "hook_event_name": name}
        event.update(fields)
        return run_hook("claude_code", event, root=self.root)[0]

    def edit(self, relative, tool="Edit", cwd=None):
        event = {"session_id": "test", "cwd": str(cwd or self.root), "hook_event_name": "PostToolUse",
                 "tool_name": tool, "tool_input": {"file_path": str(self.root / relative)}}
        return run_hook("claude_code", event, root=self.root)[0]

    def shell(self, command, name="PostToolUse", tool="Bash", **fields):
        return self.claude(name, tool_name=tool, tool_input={"command": command}, **fields)

    def stop(self, active=False):
        return self.claude("Stop", stop_hook_active=active)


class ClaudeCode(Workspace):
    def test_edit_without_tests_blocks_once_and_names_the_command(self):
        self.assertEqual(self.edit("src/app.py", tool="Write"), {})
        answer = self.stop()
        self.assertEqual(answer["decision"], "block")
        self.assertIn("python3 -m pytest", answer["reason"])
        self.assertIn("src/app.py", answer["reason"])
        self.assertEqual(self.stop(), {})
        self.assertEqual(self.state()["finishes_without_tests"], 1)

    def test_test_run_after_the_last_edit_lets_the_finish_happen(self):
        self.edit("src/app.py")
        self.shell("python3 -m pytest -q")
        self.assertEqual(self.stop(), {})
        self.assertEqual(self.state()["changed_paths"], [])

    def test_edit_after_the_test_run_blocks_again(self):
        self.edit("src/app.py")
        self.shell("python3 -m pytest -q")
        self.edit("tests/test_app.py")
        answer = self.stop()
        self.assertEqual(answer["decision"], "block")
        self.assertIn("tests/test_app.py", answer["reason"])
        self.assertNotIn("src/app.py", answer["reason"])

    def test_files_outside_the_source_patterns_do_not_count(self):
        for relative in ("docs/guide.md", "src/README.md", ".baltor/step/handoff.md", "build/out.txt"):
            self.edit(relative)
        self.claude("PostToolUse", tool_name="Write", tool_input={"file_path": "/elsewhere/src/app.py"})
        self.assertEqual(self.stop(), {})

    def test_which_shell_commands_count_as_a_test_run(self):
        counted = ("cd src && python3 -m pytest -q", "PYTHONPATH=src python3 -m pytest", "python3 -m pytest | tail -5",
                   "make test", "python3 -m pytest > report.txt")
        not_counted = ("python3 -m pip list", "echo python3 -m pytest", "python3 -m pytestx", "cat 'unclosed")
        for command in not_counted:
            self.edit("src/app.py")
            self.shell(command)
            self.assertEqual(self.stop()["decision"], "block", command)
        for command in counted:
            self.edit("src/app.py")
            self.shell(command)
            self.assertEqual(self.stop(), {}, command)

    def test_runs_that_do_not_run_the_tests_do_not_count(self):
        not_counted = ("true || python3 -m pytest", "python3 -m pytest --version", "python3 -m pytest --collect-only -q",
                       "python3 -m pytest --co", "python3 -m pytest &", "python3 -m pytest -h",
                       "make build || python3 -m pytest -q")
        for command in not_counted:
            self.edit("src/app.py")
            self.shell(command)
            self.assertEqual(self.stop()["decision"], "block", command)
        counted = ("python3 -m pytest || true", "python3 -m pytest -q; echo done", "python3 -m pytest &>/dev/null",
                   "(cd src && python3 -m pytest)")
        for command in counted:
            self.edit("src/app.py")
            self.shell(command)
            self.assertEqual(self.stop(), {}, command)

    def test_policy_can_name_its_own_excluded_arguments(self):
        self.write_policy("step-1", excluded_arguments=["--list-only"])
        self.edit("src/app.py")
        self.shell("make test --list-only")
        self.assertEqual(self.stop()["decision"], "block")
        self.edit("src/app.py")
        self.shell("python3 -m pytest --version")
        self.assertEqual(self.stop(), {})

    def test_powershell_and_monitor_test_runs_count(self):
        for tool in ("PowerShell", "Monitor"):
            self.edit("src/app.py")
            self.shell("python3 -m pytest -q", tool=tool)
            self.assertEqual(self.stop(), {}, tool)
        self.edit("src/app.py")
        self.shell("python3 -m pytest", name="PostToolUseFailure", tool="PowerShell", error="Exit code 1")
        self.assertEqual(self.stop(), {})

    def test_a_failing_test_run_counts_but_an_interrupted_one_does_not(self):
        self.edit("src/app.py")
        self.shell("python3 -m pytest", name="PostToolUseFailure", error="Exit code 1", is_interrupt=True)
        self.assertEqual(self.stop()["decision"], "block")
        self.edit("src/app.py")
        self.shell("python3 -m pytest", name="PostToolUseFailure", error="Exit code 1")
        self.assertEqual(self.stop(), {})

    def test_stop_hook_active_is_never_blocked(self):
        self.edit("src/app.py")
        self.assertEqual(self.stop(active=True), {})

    def test_new_step_identity_starts_a_clean_record(self):
        self.edit("src/app.py")
        self.write_policy("step-2")
        self.assertEqual(self.stop(), {})
        self.assertEqual(self.state()["step_id"], "step-2")

    @unittest.skipIf(fcntl is None, "fcntl is not available")
    def test_state_updates_wait_for_the_lock(self):
        self.edit("src/app.py")
        lock_path = self.root / ".baltor" / "state" / "require-tests-before-stop" / "lock"
        data = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": str(self.root),
                           "tool_input": {"command": "python3 -m pytest"}}).encode("utf-8")
        with open(lock_path, "ab") as holder:
            fcntl.flock(holder, fcntl.LOCK_EX)
            process = launch(["--harness", "claude_code"], data, self.root)
            process.stdin.write(data)
            process.stdin.close()
            try:
                process.wait(timeout=4)
                answered_while_locked = True
            except subprocess.TimeoutExpired:
                answered_while_locked = False
            fcntl.flock(holder, fcntl.LOCK_UN)
        process.stdout.read()
        process.stdout.close()
        process.stderr.close()
        process.wait(timeout=30)
        self.assertFalse(answered_while_locked)
        self.assertEqual(self.state()["changed_paths"], [])

    def test_parallel_events_lose_no_update(self):
        events = [json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Write", "cwd": str(self.root),
                              "tool_input": {"file_path": str(self.root / "src" / ("m%d.py" % n))}}).encode("utf-8")
                  for n in range(8)]
        processes = [(launch(["--harness", "claude_code"], data, self.root), data) for data in events]
        for process, data in processes:
            process.communicate(data, timeout=30)
            self.assertEqual(process.returncode, 0)
        state = self.state()
        self.assertEqual(state["sequence"], 8)
        self.assertEqual(len(state["changed_paths"]), 8)


class ClaudeCodeWorktrees(Workspace):
    """Claude Code keeps CLAUDE_PROJECT_DIR at the main checkout and moves cwd into .claude/worktrees/<name>."""

    def setUp(self):
        super().setUp()
        self.worktree = self.root / ".claude" / "worktrees" / "feature-a"
        (self.worktree / "src").mkdir(parents=True)
        (self.worktree / ".git").write_text("gitdir: ../../../.git/worktrees/feature-a\n", encoding="utf-8")

    def test_edits_in_a_worktree_match_the_source_patterns(self):
        self.edit(".claude/worktrees/feature-a/src/app.py", tool="Write", cwd=self.worktree)
        answer = self.stop()
        self.assertEqual(answer["decision"], "block")
        self.assertIn("src/app.py", answer["reason"])
        self.assertNotIn(".claude/worktrees", answer["reason"])

    def test_a_folder_without_a_git_file_is_not_a_worktree(self):
        fake = self.root / ".claude" / "worktrees" / "made-up"
        (fake / "src").mkdir(parents=True)
        self.edit(".claude/worktrees/made-up/src/app.py", cwd=fake)
        self.assertEqual(self.stop(), {})


class DefaultPolicy(unittest.TestCase):
    """The file the package places at .baltor/step/require-tests-before-stop.json."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tests-before-stop-default-")
        self.root = Path(self.temp.name) / "workspace"
        (self.root / ".baltor" / "step").mkdir(parents=True)
        (self.root / POLICY_NAME).write_bytes(DEFAULT_POLICY.read_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def event(self, name, **fields):
        event = {"session_id": "test", "cwd": str(self.root), "hook_event_name": name}
        event.update(fields)
        return run_hook("claude_code", event, root=self.root)[0]

    def test_default_policy_is_valid(self):
        process = launch(["--check-policy", "--root", str(self.root)], b"", self.root)
        stdout, _ = process.communicate(b"", timeout=30)
        self.assertEqual(process.returncode, 0, stdout)
        self.assertEqual(json.loads(stdout)["test_commands"], ["python3 -m pytest"])

    def test_invalid_policy_is_reported_to_the_host(self):
        (self.root / POLICY_NAME).write_text('{"record_type": "tests_before_stop_policy/v1"}', encoding="utf-8")
        process = launch(["--check-policy", "--root", str(self.root)], b"", self.root)
        stdout, _ = process.communicate(b"", timeout=30)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(json.loads(stdout)["policy"], "refused")

    def test_default_reminds_after_python_edits_only(self):
        self.event("PostToolUse", tool_name="Edit", tool_input={"file_path": str(self.root / "notes" / "plan.md")})
        self.assertEqual(self.event("Stop"), {})
        self.event("PostToolUse", tool_name="Edit", tool_input={"file_path": str(self.root / "pkg" / "core.py")})
        self.assertIn("python3 -m pytest", self.event("Stop")["reason"])


class OtherHarnesses(Workspace):
    def test_cursor_edit_then_stop_sends_one_follow_up(self):
        run_hook("cursor", {"hook_event_name": "afterFileEdit", "file_path": str(self.root / "src" / "app.py"),
                            "edits": [{"old_string": "a", "new_string": "b"}]}, root=self.root)
        answer, _ = run_hook("cursor", {"hook_event_name": "stop", "status": "completed"}, root=self.root)
        self.assertIn("python3 -m pytest", answer["followup_message"])
        self.assertEqual(run_hook("cursor", {"hook_event_name": "stop", "status": "completed"}, root=self.root)[0], {})
        run_hook("cursor", {"hook_event_name": "afterFileEdit", "file_path": str(self.root / "src" / "b.py")}, root=self.root)
        self.assertEqual(run_hook("cursor", {"hook_event_name": "stop", "status": "aborted"}, root=self.root)[0], {})
        run_hook("cursor", {"hook_event_name": "afterShellExecution", "command": "make test", "output": "x"}, root=self.root)
        self.assertEqual(run_hook("cursor", {"hook_event_name": "stop", "status": "completed"}, root=self.root)[0], {})

    def test_copilot_events_with_and_without_the_event_argument(self):
        edit = {"toolName": "edit", "cwd": str(self.root), "toolArgs": json.dumps({"path": "src/app.py"}),
                "toolResult": {"resultType": "success"}}
        run_hook("copilot", edit, root=self.root, extra=["--event", "postToolUse"])
        answer, _ = run_hook("copilot", {"cwd": str(self.root)}, root=self.root, extra=["--event", "agentStop"])
        self.assertEqual(answer["decision"], "block")
        self.assertEqual(run_hook("copilot", {"cwd": str(self.root)}, root=self.root)[0], {})
        self.assertEqual(self.state()["finishes_without_tests"], 1)
        run_hook("copilot", edit, root=self.root, extra=["--event", "postToolUse"])
        active = {"cwd": str(self.root), "stop_hook_active": True}
        self.assertEqual(run_hook("copilot", active, root=self.root, extra=["--event", "agentStop"])[0], {})
        denied = {"toolName": "bash", "toolArgs": json.dumps({"command": "python3 -m pytest"}),
                  "toolResult": {"resultType": "denied"}}
        run_hook("copilot", denied, root=self.root)
        run_hook("copilot", edit, root=self.root)
        self.assertEqual(run_hook("copilot", {"cwd": str(self.root)}, root=self.root)[0]["decision"], "block")
        passed = dict(denied, toolResult={"resultType": "success"})
        run_hook("copilot", passed, root=self.root)
        self.assertEqual(run_hook("copilot", {"cwd": str(self.root)}, root=self.root)[0], {})


class FailOpen(Workspace):
    def assert_let_through(self, answer_and_errors, fragment):
        answer, errors = answer_and_errors
        self.assertEqual(answer, {})
        self.assertIn(fragment, errors)

    def test_malformed_event_is_let_through(self):
        self.assert_let_through(run_hook("claude_code", raw=b"{", root=self.root), "not valid JSON")
        self.assert_let_through(run_hook("claude_code", raw=b" " * (1024 * 1024 + 1), root=self.root), "larger than 1 MiB")

    def test_missing_or_bad_policy_and_state(self):
        self.edit("src/app.py")
        (self.root / POLICY_NAME).unlink()
        self.assert_let_through(run_hook("claude_code", {"hook_event_name": "Stop"}, root=self.root), "no policy file")
        self.write_policy("step-1", test_commands=[])
        self.assert_let_through(run_hook("claude_code", {"hook_event_name": "Stop"}, root=self.root), "test_commands")
        self.write_policy("step-1")
        (self.root / STATE_NAME).write_text("[1, 2]", encoding="utf-8")
        self.assert_let_through(run_hook("claude_code", {"hook_event_name": "Stop"}, root=self.root), "state file")

    def test_state_folder_behind_a_link_is_never_written(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / ".baltor" / "state").symlink_to(outside, target_is_directory=True)
        self.assert_let_through(run_hook("claude_code", {"hook_event_name": "Stop"}, root=self.root), "symbolic link")
        self.assertEqual(list(outside.iterdir()), [])

    def test_bad_registration_exits_zero_and_blocks_nothing(self):
        for extra in ([], ["--harness", "unknown"]):
            process = launch(extra, b'{"hook_event_name": "Stop"}', self.root)
            stdout, _ = process.communicate(b'{"hook_event_name": "Stop"}', timeout=30)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(json.loads(stdout), {})


class ShippedFiles(unittest.TestCase):
    def test_samples_give_the_expected_answers(self):
        cases = [("claude_code", "stop", []), ("cursor", "stop", []), ("copilot", "agentstop", ["--event", "agentStop"])]
        for harness, event, extra in cases:
            for case, folder in (("refused", "workspace-changed"), ("allowed", "workspace-tested")):
                with tempfile.TemporaryDirectory(prefix="tests-before-stop-sample-") as temporary:
                    copy = Path(temporary) / "payload"
                    shutil.copytree(PAYLOAD, copy)
                    sample = (copy / "examples" / ("%s-%s-%s.json" % (harness, event, case))).read_bytes()
                    answer, _ = run_hook(harness, raw=sample, root=copy, cwd=copy,
                                         extra=["--root", "examples/" + folder, *extra])
                    if case == "allowed":
                        self.assertEqual(answer, {}, (harness, case))
                    else:
                        self.assertIn("python3 -m pytest", json.dumps(answer), (harness, case))

    def test_variants_register_this_script(self):
        claude = json.loads((PAYLOAD / "variants/claude_code/settings.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(sorted(claude), ["PostToolUse", "PostToolUseFailure", "Stop"])
        for tool in ("Bash", "PowerShell", "Monitor"):
            self.assertIn(tool, claude["PostToolUse"][0]["matcher"].split("|"))
            self.assertIn(tool, claude["PostToolUseFailure"][0]["matcher"].split("|"))
        for entries in claude.values():
            self.assertIn("$CLAUDE_PROJECT_DIR/" + SCRIPT_PLACE, entries[0]["hooks"][0]["command"])
        cursor = json.loads((PAYLOAD / "variants/cursor/hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(sorted(cursor), ["afterFileEdit", "afterShellExecution", "stop"])
        copilot = json.loads((PAYLOAD / "variants/copilot/require-tests-before-stop.json").read_text(encoding="utf-8"))
        self.assertIn("--event agentStop", copilot["hooks"]["agentStop"][0]["bash"])
        self.assertIn("--event postToolUse", copilot["hooks"]["postToolUse"][0]["bash"])
        self.assertEqual(Path(SCRIPT_PLACE).name, HOOK.name)


if __name__ == "__main__":
    unittest.main()
