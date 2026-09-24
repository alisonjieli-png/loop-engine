"""The command safety station's command line, run in process.

The harness hook form must only ever narrow: "ask" for a command that must
wait, no output at all for one that may run, and nothing for another tool.
"""
import io
import json
import unittest
from unittest.mock import patch

from loop_engine.decision_cli import command_safety_command, decision_command
from loop_engine.core.decisions import stations


def run(arguments, event=None):
    output = io.StringIO()
    code = command_safety_command(arguments, stdin=io.StringIO(json.dumps(event) if event else ""),
                                  stdout=output)
    return code, output.getvalue()


def bash(command):
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}


class CommandSafetyCommandLine(unittest.TestCase):
    def test_plain_form_prints_the_station_result_and_exits_by_decision(self):
        code, text = run(["--command", "pytest -q"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["decision"], "run")
        code, text = run(["--command", "git reset --hard HEAD~3"])
        record = json.loads(text)
        self.assertEqual((code, record["decision"]), (2, "wait_for_person"))
        self.assertIn("irreversible_waits_for_a_person", record["binding"]["guards"])
        self.assertIs(record["authority_granted"], False)

    def test_a_granted_effect_is_the_only_way_a_risky_command_runs(self):
        self.assertEqual(run(["--command", "curl https://example.com"])[0], 2)
        granted = ["--grant", "read", "--grant", "write", "--grant", "execute", "--grant", "network"]
        self.assertEqual(run(["--command", "curl https://example.com", *granted])[0], 0)
        with self.assertRaises(SystemExit):
            run(["--command", "ls", "--grant", "dynamic"])

    def test_the_hook_form_only_narrows(self):
        self.assertEqual(run(["--hook", "claude_code"], bash("ls -la")), (0, ""))
        code, text = run(["--hook", "claude_code"], bash("rm -rf build"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertEqual(run(["--hook", "claude_code"], {"tool_name": "Read", "tool_input": {}}), (0, ""))

    def test_known_wrong_hook_that_allows_is_caught(self):
        wrong = lambda result: "ask" if result.decision == "wait_for_person" else "allow"
        with patch.object(stations, "_hook_decision", wrong):
            _code, text = run(["--hook", "claude_code"], bash("ls -la"))
        self.assertIn("allow", text)
        self.assertNotIn("allow", run(["--hook", "claude_code"], bash("ls -la"))[1])

    def test_the_decisions_command_routes_to_the_station(self):
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(decision_command(["command-safety", "--command", "ls"]), 0)
        self.assertEqual(json.loads(output.getvalue())["station_id"], "command_safety")


if __name__ == "__main__":
    unittest.main()
