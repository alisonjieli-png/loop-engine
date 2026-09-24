"""Tests for hooks/guard_shell_commands.py. Effects: starts the hook with the running Python and loads it in memory by its path; reads package files; writes nothing."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
HOOK = PAYLOAD / "hooks" / "guard_shell_commands.py"
POLICY = "examples/step-policy.json"
DEFAULT_POLICY = "defaults/guard-shell-command-allowlist.json"
SCRIPT_PLACE = ".baltor/guard-shell-command-allowlist/hooks/guard_shell_commands.py"


def load_guard():
    spec = importlib.util.spec_from_file_location("guard_shell_commands_under_test", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GUARD = load_guard()


def run_hook(harness, event=None, *, raw=None, policy=POLICY, root_variable=True, extra=()):
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}
    if root_variable:
        environment["CLAUDE_PROJECT_DIR"] = str(PAYLOAD)
        environment["CURSOR_PROJECT_DIR"] = str(PAYLOAD)
    arguments = [sys.executable, "-I", "-B", str(HOOK)]
    if harness:
        arguments += ["--harness", harness]
    if policy is not None:
        arguments += ["--policy", policy]
    arguments += list(extra)
    data = raw if raw is not None else json.dumps(event).encode("utf-8")
    return subprocess.run(arguments, input=data, capture_output=True, timeout=30, env=environment, cwd=str(PAYLOAD))


def claude_event(command, tool="Bash", event_name="PreToolUse"):
    return {"session_id": "test-session", "cwd": str(PAYLOAD), "hook_event_name": event_name,
            "tool_name": tool, "tool_input": {"command": command}}


def answer_of(finished):
    lines = finished.stdout.decode("utf-8").splitlines()
    if finished.returncode != 0 or len(lines) != 1:
        raise AssertionError("exit %s, output %r, errors %r" % (finished.returncode, finished.stdout, finished.stderr))
    return json.loads(lines[0])


def claude_reason(answer):
    output = answer.get("hookSpecificOutput", {})
    if output.get("permissionDecision") != "deny":
        return None
    return output.get("permissionDecisionReason", "")


def policy_of(*entries, names=()):
    document = {"record_type": "shell_command_allowlist/v1", "allowed_commands": list(entries),
                "environment_names": list(names)}
    return GUARD.parse_policy(json.dumps(document).encode("utf-8"), "test-policy.json")


def in_memory_verdict(command, policy):
    try:
        GUARD.check_command(command, policy)
    except GUARD.Refusal as refusal:
        return str(refusal)
    return None


class AllowedCommands(unittest.TestCase):
    def assert_allowed(self, command, policy=POLICY):
        answer = answer_of(run_hook("claude_code", claude_event(command), policy=policy))
        self.assertEqual(answer, {}, command)

    def test_listed_command_gets_the_empty_answer(self):
        self.assert_allowed("python3 -m pytest -q")

    def test_every_joined_part_that_is_listed_passes(self):
        for command in ("git status && git diff --stat", "git status; ls", "ls tests | rg test_",
                        "git log --oneline || git status"):
            self.assert_allowed(command)

    def test_quoted_operators_braces_and_dollars_are_arguments(self):
        for command in ('rg "a|b" src', "rg 'x && y' src", "ls 'file with spaces.txt'", 'rg "\\$HOME" src',
                        "rg 'a{1,2}' src", "rg 'cost$' src", "rg cost$ src", "find . -name '*.tmp'"):
            self.assert_allowed(command)

    def test_stream_merge_and_null_device_are_accepted(self):
        for command in ("python3 -m pytest -q 2>&1", "ls >/dev/null", "ls 2>/dev/null", "rg x src &>/dev/null"):
            self.assert_allowed(command)

    def test_declared_variable_prefix_and_comment(self):
        self.assert_allowed("PYTHONPATH=src python3 -m pytest")
        self.assert_allowed("git status  # check the tree first")

    def test_unquoted_patterns_pass_for_entries_without_refused_arguments(self):
        for command in ("ls tests/*.py", "python3 -m pytest tests/test_*.py", "ls src/[ab]*"):
            self.assert_allowed(command)


class RefusedCommands(unittest.TestCase):
    def assert_refused(self, command, fragment, tool="Bash", policy=POLICY):
        reason = claude_reason(answer_of(run_hook("claude_code", claude_event(command, tool=tool), policy=policy)))
        self.assertIsNotNone(reason, command)
        self.assertIn(fragment, reason, command)
        self.assertIn("Allowed command starts", reason)

    def test_unlisted_program_is_refused_with_the_allowed_starts(self):
        self.assert_refused("rm -rf build", '"rm -rf build" does not start with an allowed command')
        self.assert_refused("git push", "does not start with an allowed command")
        self.assert_refused("./ls", "does not start with an allowed command")
        self.assert_refused("git -c core.pager=less status", "does not start with an allowed command")
        self.assert_refused("cat notes.txt", "does not start with an allowed command")

    def test_one_unlisted_part_refuses_the_whole_line(self):
        self.assert_refused("git status && rm -rf build", '"rm -rf build"')
        self.assert_refused("ls | xargs cat", '"xargs" runs other programs')

    def test_unchecked_shell_syntax_is_refused(self):
        cases = {
            "ls > listing.txt": "redirection to or from a file",
            "ls < notes.txt": "redirection to or from a file",
            "ls $(pwd)": "$( )",
            "ls `pwd`": "backtick",
            'ls "$(pwd)"': "inside double quotes",
            "ls &": "background jobs",
            "(ls)": "subshells",
            "ls <<END": "here-documents",
            "ls\nrm notes.txt": "more than one line",
            "ls <(ls tests)": "process substitution",
            "ls &&": "ends with an operator",
            "": "empty",
            'ls "unclosed': "unclosed double quote",
        }
        for command, fragment in cases.items():
            self.assert_refused(command, fragment)

    def test_programs_that_run_other_programs_are_refused(self):
        for command in ("env ls", "bash -c ls", "/usr/bin/env ls", "sudo ls", "timeout 5 ls", "trap ls EXIT"):
            self.assert_refused(command, "runs other programs")

    def test_builtins_that_change_later_commands_are_refused_and_cannot_be_listed(self):
        policy = policy_of({"start": ["ls"]})
        for command in ("export PATH=/tmp/tools; ls", "alias ls=pwd; ls", "hash -p /tmp/tool ls; ls",
                        "enable -f ./lib.so ls", "set -o posix; ls", "unset HOME; ls"):
            self.assertIn("changes how later commands in the shell run", in_memory_verdict(command, policy) or "",
                          command)
        for name in ("export", "alias", "hash", "declare", "shopt"):
            with self.assertRaises(GUARD.PolicyError, msg=name):
                policy_of({"start": [name]})

    def test_undeclared_variable_prefix_is_refused(self):
        self.assert_refused("FOO=1 ls", "variable prefix FOO=")

    def test_refused_arguments_of_a_listed_command(self):
        self.assert_refused("git diff --output=patch.txt", '"--output" is not allowed with "git diff"')
        self.assert_refused("git diff --output patch.txt", '"--output"')
        self.assert_refused("git diff --outp=patch.txt", '"--output"')
        self.assert_refused("find . -delete", '"-delete" is not allowed with "find"')
        self.assert_refused("find . -exec cat '{}' \\;", '"-exec"')
        self.assert_refused("find . '-del'ete", '"-delete"')
        self.assert_refused("rg --pre=./convert x", '"--pre"')


class ExpansionIsRefused(unittest.TestCase):
    """Bash turns these words into refused options; the guard must not read them as plain text."""

    def assert_refused(self, command, fragment):
        reason = claude_reason(answer_of(run_hook("claude_code", claude_event(command))))
        self.assertIsNotNone(reason, command)
        self.assertIn(fragment, reason, command)

    def test_brace_expansion_that_builds_a_refused_option(self):
        for command in ("find . -name '*.tmp' {-delete,}", "find . {-exec,rm,-rf,build,\\;}",
                        "rg {--pre=./convert,TODO} src", "git diff {--output=/tmp/x,HEAD}", "ls {a,b}"):
            self.assert_refused(command, "unquoted braces")

    def test_parameter_expansion_in_any_word(self):
        for command in ("find . -name '*.tmp' ${UNSET_NAME:--delete}", 'find . "${UNSET_NAME:--delete}"',
                        "git diff \"--output=$HOME/x\"", "ls $HOME", 'ls "$HOME"', "ls ${HOME}", "ls $1", "ls $@",
                        "python3 -m pytest $ARGS", "ls $[1+1]"):
            self.assert_refused(command, "$NAME")

    def test_unquoted_patterns_after_a_start_with_refused_arguments(self):
        for command in ("find . -name *.tmp", "find . -name x *", "rg TODO src/*.py", "rg TODO [ab]*",
                        "git diff HEAD -- src/?.py"):
            self.assert_refused(command, "put the pattern in single quotes")


class OptionForms(unittest.TestCase):
    """Short options with attached values and abbreviated long options, checked in memory."""

    def setUp(self):
        self.policy = policy_of({"start": ["sort"], "refused_arguments": ["-o", "--output", "--compress-program"]})

    def test_attached_values_and_groups_of_a_short_option_are_refused(self):
        for command in ("sort -o out.txt in.txt", "sort -oout.txt in.txt", "sort -o/tmp/out in.txt",
                        "sort -o../out in.txt", "sort -uo out.txt in.txt", "sort -ro out.txt in.txt"):
            self.assertIn('"-o" is not allowed', in_memory_verdict(command, self.policy) or "", command)

    def test_abbreviated_long_options_are_refused(self):
        for command in ("sort --outp=out.txt in.txt", "sort --out out.txt in.txt", "sort --output=out.txt in.txt",
                        "sort --compress-prog=gzip in.txt"):
            self.assertIsNotNone(in_memory_verdict(command, self.policy), command)

    def test_other_options_still_pass(self):
        for command in ("sort in.txt", "sort -u in.txt", "sort -r -n in.txt", "sort --unique in.txt",
                        "sort -k2,2 in.txt", "sort -- in.txt"):
            self.assertIsNone(in_memory_verdict(command, self.policy), command)

    def test_refused_argument_rules(self):
        self.assertEqual(GUARD.refused_argument("--o", ("--output",)), "--output")
        self.assertEqual(GUARD.refused_argument("--", ("--output",)), "")
        self.assertEqual(GUARD.refused_argument("--outputs", ("--output",)), "")
        self.assertEqual(GUARD.refused_argument("--pre-glob=*.gz", ("--pre",)), "")
        self.assertEqual(GUARD.refused_argument("-execdir", ("-exec",)), "")


class ClaudeCodeTools(unittest.TestCase):
    def verdict(self, tool, tool_input):
        event = {"session_id": "test-session", "hook_event_name": "PreToolUse", "tool_name": tool,
                 "tool_input": tool_input}
        return answer_of(run_hook("claude_code", event))

    def test_monitor_command_is_checked_like_a_bash_line(self):
        self.assertIn("does not start with an allowed command",
                      claude_reason(self.verdict("Monitor", {"command": "rm -rf build", "description": "x"})))
        self.assertIn("unquoted braces",
                      claude_reason(self.verdict("Monitor", {"command": "find . {-delete,}", "description": "x"})))
        self.assertEqual(self.verdict("Monitor", {"command": "python3 -m pytest -q 2>&1", "description": "tests",
                                                  "timeout_ms": 600000}), {})

    def test_monitor_without_a_command_is_refused(self):
        self.assertIn("WebSocket", claude_reason(self.verdict("Monitor", {"ws": {"url": "sample-address"},
                                                                          "description": "x"})))
        self.assertIn("no command text", claude_reason(self.verdict("Monitor", {"description": "x"})))

    def test_monitor_with_a_websocket_is_refused_even_beside_an_allowed_command(self):
        answer = self.verdict("Monitor", {"command": "git status", "ws": {"url": "sample-address"},
                                          "description": "x"})
        self.assertIn("WebSocket", claude_reason(answer))

    def test_powershell_is_refused(self):
        reason = claude_reason(self.verdict("PowerShell", {"command": "Get-ChildItem"}))
        self.assertIn("PowerShell commands are not checked", reason)


class FailClosed(unittest.TestCase):
    def assert_input_refused(self, raw, fragment):
        reason = claude_reason(answer_of(run_hook("claude_code", raw=raw)))
        self.assertIsNotNone(reason)
        self.assertIn(fragment, reason)

    def test_malformed_events_are_refused(self):
        self.assert_input_refused(b"not json", "not valid JSON")
        self.assert_input_refused(b"[]", "not a JSON object")
        self.assert_input_refused(b'{"tool_name": "Bash", "tool_name": "Read"}', "not valid JSON")
        self.assert_input_refused(b'{"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {}}',
                                  "no command text")
        self.assert_input_refused(b"\xff\xfe", "not valid JSON")

    def test_oversized_event_is_refused_not_truncated(self):
        self.assert_input_refused(b" " * (1024 * 1024 + 8), "larger than 1 MiB")

    def test_missing_policy_refuses_every_command(self):
        answer = answer_of(run_hook("claude_code", claude_event("ls"), policy="examples/no-such-policy.json"))
        self.assertIn("there is no allowlist file", claude_reason(answer))

    def test_invalid_policy_refuses_every_command(self):
        answer = answer_of(run_hook("claude_code", claude_event("ls"), policy="examples/invalid-policy.json"))
        self.assertIn("runs other programs", claude_reason(answer))

    def test_unknown_root_refuses_a_relative_policy(self):
        answer = answer_of(run_hook("claude_code", claude_event("ls"), root_variable=False))
        self.assertIn("workspace root is unknown", claude_reason(answer))

    def test_absolute_policy_needs_no_root(self):
        answer = answer_of(run_hook("claude_code", claude_event("ls"), policy=str(PAYLOAD / POLICY), root_variable=False))
        self.assertEqual(answer, {})

    def test_missing_harness_argument_exits_two(self):
        finished = run_hook(None, claude_event("ls"))
        self.assertEqual(finished.returncode, 2)


class PolicyCheck(unittest.TestCase):
    def test_example_policy_is_valid(self):
        finished = run_hook(None, raw=b"", extra=["--check-policy"])
        self.assertEqual(finished.returncode, 0, finished.stdout)
        self.assertEqual(json.loads(finished.stdout)["allowed_commands"], 7)

    def test_launcher_entry_and_unsafe_variable_are_refused(self):
        finished = run_hook(None, raw=b"", policy="examples/invalid-policy.json", extra=["--check-policy"])
        self.assertEqual(finished.returncode, 1)
        self.assertEqual(json.loads(finished.stdout)["policy"], "refused")

    def test_tokens_with_shell_characters_are_refused(self):
        for entry in ({"start": ["ls*"]}, {"start": ["$TOOL"]}, {"start": ["git", "{status,push}"]},
                      {"start": ["~/bin/tool"]}, {"start": ["find"], "refused_arguments": ["--"]},
                      {"start": ["find"], "refused_arguments": ["-"]}, {"start": ["find"], "refused_arguments": ["delete"]}):
            with self.assertRaises(GUARD.PolicyError, msg=json.dumps(entry)):
                policy_of(entry)

    def test_variables_that_choose_programs_or_their_configuration_are_refused(self):
        for name in ("PATH", "LD_PRELOAD", "HOME", "XDG_CONFIG_HOME", "RIPGREP_CONFIG_PATH", "GIT_DIR",
                     "GIT_EXTERNAL_DIFF", "GIT_CONFIG_GLOBAL", "JAVA_TOOL_OPTIONS"):
            with self.assertRaises(GUARD.PolicyError, msg=name):
                policy_of({"start": ["ls"]}, names=[name])
        self.assertEqual(policy_of({"start": ["ls"]}, names=["PYTHONPATH"]).environment_names, frozenset({"PYTHONPATH"}))


class DefaultPolicy(unittest.TestCase):
    """The file the package places at .baltor/step/guard-shell-command-allowlist.json."""

    def test_default_policy_is_valid(self):
        finished = run_hook(None, raw=b"", policy=DEFAULT_POLICY, extra=["--check-policy"])
        self.assertEqual(finished.returncode, 0, finished.stdout)
        self.assertEqual(json.loads(finished.stdout)["environment_names"], [])

    def test_default_allows_inspection_only(self):
        for command in ("git status", "git diff --stat", "git log --oneline -5", "ls -la", "rg TODO src", "pwd",
                        "find . -name '*.py'"):
            self.assertEqual(answer_of(run_hook("claude_code", claude_event(command), policy=DEFAULT_POLICY)), {},
                             command)
        for command in ("python3 -m pytest", "cat notes.txt", "find . -delete", "rg -z TODO src",
                        "git diff --output=x", "git commit -m x", "rg --hostname-bin=./tool TODO",
                        "rg --host ./tool TODO"):
            self.assertIsNotNone(claude_reason(answer_of(run_hook("claude_code", claude_event(command),
                                                                  policy=DEFAULT_POLICY))), command)


class OtherToolsAndHarnesses(unittest.TestCase):
    def test_non_shell_tools_are_left_alone(self):
        self.assertEqual(answer_of(run_hook("claude_code", {"hook_event_name": "PreToolUse", "tool_name": "Read",
                                                             "tool_input": {"file_path": "/x"}})), {})
        self.assertEqual(answer_of(run_hook("claude_code", claude_event("rm -rf build", event_name="PostToolUse"))), {})
        self.assertEqual(answer_of(run_hook("copilot", {"toolName": "view", "toolArgs": "{}"})), {})

    def test_cursor_answers_always_name_a_permission(self):
        allowed = answer_of(run_hook("cursor", {"hook_event_name": "beforeShellExecution", "command": "git status"}))
        self.assertEqual(allowed, {"permission": "allow"})
        refused = answer_of(run_hook("cursor", {"hook_event_name": "beforeShellExecution", "command": "rm notes.txt"}))
        self.assertEqual(refused["permission"], "deny")
        self.assertEqual(refused["user_message"], refused["agent_message"])
        tool = answer_of(run_hook("cursor", {"hook_event_name": "preToolUse", "tool_name": "Shell",
                                              "tool_input": {"command": "rm notes.txt"}}))
        self.assertEqual(tool["permission"], "deny")
        other = answer_of(run_hook("cursor", {"hook_event_name": "preToolUse", "tool_name": "Read",
                                               "tool_input": {"file_path": "/x"}}))
        self.assertEqual(other, {"permission": "allow"})
        broken = answer_of(run_hook("cursor", {"hook_event_name": "beforeShellExecution"}))
        self.assertEqual(broken["permission"], "deny")

    def test_copilot_answer_shape_and_argument_forms(self):
        refused = answer_of(run_hook("copilot", {"toolName": "bash", "toolArgs": json.dumps({"command": "rm notes.txt"})}))
        self.assertEqual(refused["permissionDecision"], "deny")
        self.assertEqual(answer_of(run_hook("copilot", {"toolName": "bash", "toolArgs": {"command": "ls"}})), {})
        self.assertEqual(answer_of(run_hook("copilot", {"toolName": "powershell", "toolArgs": "{}"}))["permissionDecision"],
                         "deny")
        self.assertEqual(answer_of(run_hook("copilot", {"toolName": "bash", "toolArgs": "{broken"}))["permissionDecision"],
                         "deny")


class ShippedFiles(unittest.TestCase):
    def test_samples_give_the_expected_answers(self):
        samples = sorted((PAYLOAD / "examples").glob("*-*-*.json"))
        self.assertEqual(len(samples), 7)
        for sample in samples:
            harness = sample.name.split("-", 1)[0]
            answer = answer_of(run_hook(harness, raw=sample.read_bytes()))
            if sample.stem.endswith("-allowed"):
                self.assertEqual(answer, GUARD.allow(harness), sample.name)
            else:
                self.assertIn("deny", json.dumps(answer), sample.name)

    def test_variants_register_this_script(self):
        claude = json.loads((PAYLOAD / "variants/claude_code/settings.json").read_text(encoding="utf-8"))
        entry = claude["hooks"]["PreToolUse"][0]
        self.assertEqual(entry["matcher"], "Bash|PowerShell|Monitor")
        self.assertIn('$CLAUDE_PROJECT_DIR/' + SCRIPT_PLACE, entry["hooks"][0]["command"])
        self.assertTrue(entry["hooks"][0]["command"].endswith("--harness claude_code"))
        cursor = json.loads((PAYLOAD / "variants/cursor/hooks.json").read_text(encoding="utf-8"))
        hook = cursor["hooks"]["beforeShellExecution"][0]
        self.assertTrue(hook["failClosed"])
        self.assertIn(SCRIPT_PLACE + " --harness cursor", hook["command"])
        copilot = json.loads((PAYLOAD / "variants/copilot/guard-shell-command-allowlist.json").read_text(encoding="utf-8"))
        hook = copilot["hooks"]["preToolUse"][0]
        self.assertIn(SCRIPT_PLACE + " --harness copilot", hook["bash"])
        self.assertEqual(hook["cwd"], ".")
        self.assertEqual(Path(SCRIPT_PLACE).name, HOOK.name)


if __name__ == "__main__":
    unittest.main()
