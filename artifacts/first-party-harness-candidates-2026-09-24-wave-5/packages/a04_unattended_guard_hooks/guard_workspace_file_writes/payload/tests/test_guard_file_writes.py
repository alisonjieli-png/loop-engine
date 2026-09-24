"""Tests for hooks/guard_file_writes.py. Effects: starts the hook with the running Python; builds small workspaces with links inside temporary folders only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
HOOK = PAYLOAD / "hooks" / "guard_file_writes.py"
EXAMPLE_POLICY = PAYLOAD / "examples" / "step-policy.json"
DEFAULT_POLICY = PAYLOAD / "defaults" / "guard-workspace-file-writes.json"
SCRIPT_PLACE = ".baltor/guard-workspace-file-writes/hooks/guard_file_writes.py"
CURSOR_ALLOW = {"permission": "allow"}


def run_hook(harness, event=None, *, root=None, raw=None, policy=None, extra=(), cwd=None):
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}
    if root is not None:
        environment["CLAUDE_PROJECT_DIR"] = str(root)
        environment["CURSOR_PROJECT_DIR"] = str(root)
    arguments = [sys.executable, "-I", "-B", str(HOOK)]
    if harness:
        arguments += ["--harness", harness]
    if policy is not None:
        arguments += ["--policy", str(policy)]
    arguments += list(extra)
    data = raw if raw is not None else json.dumps(event).encode("utf-8")
    return subprocess.run(arguments, input=data, capture_output=True, timeout=30, env=environment,
                          cwd=str(cwd or root or PAYLOAD))


def answer_of(finished):
    lines = finished.stdout.decode("utf-8").splitlines()
    if finished.returncode != 0 or len(lines) != 1:
        raise AssertionError("exit %s, output %r, errors %r" % (finished.returncode, finished.stdout, finished.stderr))
    return json.loads(lines[0])


def reason_of(answer):
    if "hookSpecificOutput" in answer:
        output = answer["hookSpecificOutput"]
        return output["permissionDecisionReason"] if output.get("permissionDecision") == "deny" else None
    if answer.get("permission") == "deny":
        return answer["agent_message"]
    if answer.get("permissionDecision") == "deny":
        return answer["permissionDecisionReason"]
    return None


def claude_write(path, cwd, tool="Write"):
    field = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return {"session_id": "test", "cwd": str(cwd), "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": {field: str(path), "content": "UNIQUE-CONTENT-MARKER"}}


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="write-guard-")
        base = Path(self.temp.name)
        self.root = base / "workspace"
        self.outside = base / "outside"
        for folder in (self.root / "src", self.root / ".git", self.root / "data" / "raw", self.root / ".baltor" / "step",
                       self.outside):
            folder.mkdir(parents=True)
        (self.root / ".baltor" / "step" / "guard-workspace-file-writes.json").write_bytes(EXAMPLE_POLICY.read_bytes())
        (self.root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
        (self.outside / "secret-notes.txt").write_text("outside\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def decide(self, path, tool="Write", harness="claude_code", cwd=None):
        return reason_of(answer_of(run_hook(harness, claude_write(path, cwd or self.root, tool), root=self.root)))

    def assert_refused(self, path, fragment, **options):
        reason = self.decide(path, **options)
        self.assertIsNotNone(reason, str(path))
        self.assertIn(fragment, reason, str(path))
        self.assertNotIn("UNIQUE-CONTENT-MARKER", reason)


class AllowedWrites(Workspace):
    def test_new_and_existing_files_inside_the_workspace(self):
        self.assertIsNone(self.decide(self.root / "src" / "app.py"))
        self.assertIsNone(self.decide(self.root / "src" / "new_module.py", tool="Edit"))
        self.assertIsNone(self.decide(self.root / "notebooks" / "a.ipynb", tool="NotebookEdit"))

    def test_relative_path_starts_at_the_event_folder(self):
        self.assertIsNone(self.decide("app.py", cwd=self.root / "src"))
        self.assert_refused("../../outside/x.txt", "outside the workspace", cwd=self.root / "src")

    def test_declared_writable_path_inside_a_built_in_folder(self):
        self.assertIsNone(self.decide(self.root / ".baltor" / "step" / "handoff.md"))

    def test_other_tools_are_left_alone(self):
        for event in ({"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "/"}},
                      {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}},
                      {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": "/x"}}):
            self.assertEqual(answer_of(run_hook("claude_code", event, root=self.root)), {})


class RefusedWrites(Workspace):
    def test_outside_paths_and_parent_steps(self):
        self.assert_refused(self.outside / "secret-notes.txt", "outside the workspace")
        self.assert_refused(str(self.root) + "/src/../../outside/x.txt", "outside the workspace")
        self.assert_refused("~/notes.txt", "expand to the home folder")

    def test_symbolic_link_out_of_the_workspace(self):
        (self.root / "link").symlink_to(self.outside, target_is_directory=True)
        self.assert_refused(self.root / "link" / "secret-notes.txt", "symbolic link")
        (self.root / "src" / "file-link.txt").symlink_to(self.outside / "secret-notes.txt")
        self.assert_refused(self.root / "src" / "file-link.txt", "symbolic link")

    def test_symbolic_link_into_version_control_metadata(self):
        (self.root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
        (self.root / "src" / "settings.txt").symlink_to(self.root / ".git" / "config")
        self.assert_refused(self.root / "src" / "settings.txt", "version control metadata")

    def test_version_control_folders_at_any_depth_and_case(self):
        self.assert_refused(self.root / ".git" / "config", "version control metadata (.git)")
        self.assert_refused(self.root / "vendor" / "lib" / ".git" / "HEAD", "version control metadata")
        self.assert_refused(self.root / ".GIT" / "config", "version control metadata")
        self.assert_refused(self.root / ".hg" / "hgrc", "version control metadata")

    def test_built_in_harness_and_step_folders(self):
        self.assert_refused(self.root / ".baltor" / "step" / "guard-workspace-file-writes.json", "inside .baltor")
        self.assert_refused(self.root / ".baltor" / "state" / "counter.json", "inside .baltor")
        self.assert_refused(self.root / ".claude" / "settings.json", "inside .claude")
        self.assert_refused(self.root / ".cursor" / "hooks.json", "inside .cursor")
        self.assert_refused(self.root / ".github" / "hooks" / "guard.json", "inside .github/hooks")

    def test_declared_protected_paths(self):
        self.assert_refused(self.root / "data" / "raw" / "rows.csv", 'matches "data/raw/**"')
        self.assert_refused(self.root / "Data" / "Raw" / "rows.csv", "protected path")
        self.assert_refused(self.root / "tools" / "poetry.lock", 'matches "**/*.lock"')
        self.assertIsNone(self.decide(self.root / "data" / "clean" / "rows.csv"))

    def test_hard_link_and_special_files(self):
        os.link(self.outside / "secret-notes.txt", self.root / "src" / "linked.txt")
        self.assert_refused(self.root / "src" / "linked.txt", "other hard links")
        self.assert_refused(self.root / "src", "not a regular file")
        self.assert_refused(self.root, "workspace folder itself")
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.root / "src" / "pipe")
            self.assert_refused(self.root / "src" / "pipe", "not a regular file")


class FailClosed(Workspace):
    def assert_input_refused(self, raw, fragment, harness="claude_code"):
        reason = reason_of(answer_of(run_hook(harness, raw=raw, root=self.root)))
        self.assertIsNotNone(reason)
        self.assertIn(fragment, reason)

    def test_malformed_events(self):
        self.assert_input_refused(b"{", "not valid JSON")
        self.assert_input_refused(b'"text"', "not a JSON object")
        self.assert_input_refused(b'{"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {}}',
                                  "names no usable target path")
        self.assert_input_refused(b'{"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": "a\\u0000b"}}',
                                  "names no usable target path")
        self.assert_input_refused(b" " * (1024 * 1024 + 1), "larger than 1 MiB")

    def test_missing_and_invalid_policy(self):
        (self.root / ".baltor" / "step" / "guard-workspace-file-writes.json").unlink()
        self.assertIn("there is no write policy file", self.decide(self.root / "src" / "app.py"))
        reason = reason_of(answer_of(run_hook("claude_code", claude_write(self.root / "src" / "app.py", self.root),
                                              root=self.root, policy=PAYLOAD / "examples" / "invalid-policy.json")))
        self.assertIn("writable_globs may only reopen", reason)

    def test_unsafe_or_unknown_root(self):
        event = claude_write("/etc/hostname", "/")
        self.assertIn("filesystem root", reason_of(answer_of(run_hook("claude_code", event, extra=["--root", "/"]))))
        self.assertIn("root is unknown", reason_of(answer_of(run_hook("claude_code", event))))

    def test_policy_check_command(self):
        finished = run_hook(None, raw=b"", root=self.root, extra=["--check-policy", "--root", str(self.root)])
        self.assertEqual(finished.returncode, 0, finished.stdout)
        finished = run_hook(None, raw=b"", root=self.root, policy=PAYLOAD / "examples" / "invalid-policy.json",
                            extra=["--check-policy", "--root", str(self.root)])
        self.assertEqual(finished.returncode, 1)


class ClaudeCodeWorktrees(Workspace):
    """Claude Code keeps CLAUDE_PROJECT_DIR at the main checkout and moves cwd into .claude/worktrees/<name>."""

    def setUp(self):
        super().setUp()
        self.worktree = self.root / ".claude" / "worktrees" / "feature-a"
        (self.worktree / "src").mkdir(parents=True)
        (self.worktree / ".git").write_text("gitdir: ../../../.git/worktrees/feature-a\n", encoding="utf-8")
        (self.worktree / "src" / "app.py").write_text("print(2)\n", encoding="utf-8")

    def test_writes_inside_the_worktree_are_checked_against_the_worktree(self):
        self.assertIsNone(self.decide(self.worktree / "src" / "app.py", cwd=self.worktree))
        self.assertIsNone(self.decide("new_module.py", cwd=self.worktree / "src"))
        self.assertIsNone(self.decide(self.worktree / "notes" / "plan.md", tool="Edit", cwd=self.worktree / "src"))
        self.assert_refused(self.worktree / ".claude" / "settings.json", "inside .claude", cwd=self.worktree)
        self.assert_refused(self.worktree / ".git", "version control metadata", cwd=self.worktree)
        self.assert_refused(self.worktree / "data" / "raw" / "rows.csv", "protected path", cwd=self.worktree)
        self.assert_refused(self.root / "src" / "app.py", "outside the worktree folder .claude/worktrees/feature-a",
                            cwd=self.worktree)

    def test_a_folder_without_a_git_file_is_not_a_worktree(self):
        fake = self.root / ".claude" / "worktrees" / "made-up"
        (fake / "src").mkdir(parents=True)
        self.assert_refused(fake / "src" / "app.py", "inside .claude", cwd=fake)
        (fake / ".git").mkdir()
        self.assert_refused(fake / "src" / "app.py", "inside .claude", cwd=fake)

    def test_a_linked_worktree_folder_is_not_trusted(self):
        elsewhere = self.outside / "checkout"
        (elsewhere / "src").mkdir(parents=True)
        (elsewhere / ".git").write_text("gitdir: /elsewhere\n", encoding="utf-8")
        (self.root / ".claude" / "worktrees" / "linked").symlink_to(elsewhere, target_is_directory=True)
        linked = self.root / ".claude" / "worktrees" / "linked"
        self.assertIsNotNone(self.decide(linked / "src" / "app.py", cwd=linked))

    def test_the_worktree_stays_protected_from_the_main_checkout_and_other_harnesses(self):
        self.assert_refused(self.worktree / "src" / "app.py", "inside .claude", cwd=self.root)
        event = {"hook_event_name": "preToolUse", "tool_name": "Write", "cwd": str(self.worktree),
                 "tool_input": {"file_path": str(self.worktree / "src" / "app.py")}}
        self.assertEqual(answer_of(run_hook("cursor", event, root=self.root))["permission"], "deny")


class DefaultPolicy(Workspace):
    """The file the package places at .baltor/step/guard-workspace-file-writes.json."""

    def setUp(self):
        super().setUp()
        (self.root / ".baltor" / "step" / "guard-workspace-file-writes.json").write_bytes(DEFAULT_POLICY.read_bytes())

    def test_default_policy_is_valid(self):
        finished = run_hook(None, raw=b"", root=self.root, extra=["--check-policy", "--root", str(self.root)])
        self.assertEqual(finished.returncode, 0, finished.stdout)
        self.assertEqual(json.loads(finished.stdout)["writable_globs"], 1)

    def test_default_protects_files_that_widen_a_later_session(self):
        for relative in (".mcp.json", ".vscode/settings.json", ".vscode/mcp.json", "AGENTS.md", "CLAUDE.md",
                         "docs/AGENTS.md", "GEMINI.md", ".github/copilot-instructions.md",
                         ".github/workflows/ci.yml", ".pre-commit-config.yaml", ".gitattributes"):
            self.assert_refused(self.root / relative, "is a protected path")
        self.assertIsNone(self.decide(self.root / "src" / "app.py"))
        self.assertIsNone(self.decide(self.root / ".baltor" / "step" / "handoff.md"))


class OtherHarnesses(Workspace):
    def test_cursor_write_and_delete(self):
        event = {"hook_event_name": "preToolUse", "tool_name": "Delete", "cwd": str(self.root),
                 "tool_input": {"path": str(self.root / "data" / "raw" / "rows.csv")}}
        answer = answer_of(run_hook("cursor", event, root=self.root))
        self.assertEqual(answer["permission"], "deny")
        self.assertEqual(answer["user_message"], answer["agent_message"])
        event = {"hook_event_name": "preToolUse", "tool_name": "Write", "cwd": str(self.root),
                 "tool_input": {"file_path": str(self.root / "src" / "app.py")}}
        self.assertEqual(answer_of(run_hook("cursor", event, root=self.root)), CURSOR_ALLOW)
        event["tool_input"] = {"contents": "no path"}
        self.assertEqual(answer_of(run_hook("cursor", event, root=self.root))["permission"], "deny")

    def test_cursor_answers_always_name_a_permission(self):
        for tool_name, tool_input in (("Read", {"file_path": "/"}), ("Shell", {"command": "ls"})):
            event = {"hook_event_name": "preToolUse", "tool_name": tool_name, "tool_input": tool_input}
            self.assertEqual(answer_of(run_hook("cursor", event, root=self.root)), CURSOR_ALLOW)
        self.assertEqual(answer_of(run_hook("cursor", {"hook_event_name": "stop"}, root=self.root)), CURSOR_ALLOW)

    def test_copilot_create_and_edit(self):
        event = {"toolName": "create", "cwd": str(self.root), "toolArgs": json.dumps({"path": "src/new.py"})}
        self.assertEqual(answer_of(run_hook("copilot", event, cwd=self.root)), {})
        event["toolArgs"] = json.dumps({"path": ".git/HEAD"})
        self.assertEqual(answer_of(run_hook("copilot", event, cwd=self.root))["permissionDecision"], "deny")
        event = {"toolName": "view", "toolArgs": json.dumps({"path": "/"})}
        self.assertEqual(answer_of(run_hook("copilot", event, cwd=self.root)), {})


class ShippedFiles(unittest.TestCase):
    def test_samples_give_the_expected_answers(self):
        samples = sorted((PAYLOAD / "examples").glob("*-pretooluse-*.json"))
        self.assertEqual(len(samples), 6)
        with tempfile.TemporaryDirectory(prefix="write-guard-samples-") as folder:
            root = Path(folder)
            for sample in samples:
                harness = sample.name.split("-", 1)[0]
                text = sample.read_text(encoding="utf-8").replace("/work", str(root))
                answer = answer_of(run_hook(harness, raw=text.encode("utf-8"), root=root, policy=EXAMPLE_POLICY))
                if sample.stem.endswith("-allowed"):
                    self.assertEqual(answer, CURSOR_ALLOW if harness == "cursor" else {}, sample.name)
                else:
                    self.assertIsNotNone(reason_of(answer), sample.name)

    def test_variants_register_this_script(self):
        claude = json.loads((PAYLOAD / "variants/claude_code/settings.json").read_text(encoding="utf-8"))
        entry = claude["hooks"]["PreToolUse"][0]
        self.assertEqual(entry["matcher"], "Write|Edit|MultiEdit|NotebookEdit")
        self.assertIn("$CLAUDE_PROJECT_DIR/" + SCRIPT_PLACE, entry["hooks"][0]["command"])
        cursor = json.loads((PAYLOAD / "variants/cursor/hooks.json").read_text(encoding="utf-8"))
        hook = cursor["hooks"]["preToolUse"][0]
        self.assertTrue(hook["failClosed"])
        self.assertEqual(hook["matcher"], "Write|Delete")
        self.assertIn(SCRIPT_PLACE + " --harness cursor", hook["command"])
        copilot = json.loads((PAYLOAD / "variants/copilot/guard-workspace-file-writes.json").read_text(encoding="utf-8"))
        self.assertIn(SCRIPT_PLACE + " --harness copilot", copilot["hooks"]["preToolUse"][0]["bash"])
        self.assertEqual(Path(SCRIPT_PLACE).name, HOOK.name)


if __name__ == "__main__":
    unittest.main()
