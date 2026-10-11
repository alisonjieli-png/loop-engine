"""Queue preparation and report interpretation against the existing worker contract.

The generated command is parsed, not executed. No model or external call.
"""
import json
from pathlib import Path
import shlex
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src/loop_engine/core/service_runtime/web_assets/run-desk-core.js"


def call(operation, value):
    program = "import fs from 'node:fs'; const api=await import(" + json.dumps(MODULE.as_uri()) + ");" + \
        "const input=JSON.parse(fs.readFileSync(0,'utf8')); try { console.log(JSON.stringify({value:api[" + \
        json.dumps(operation) + "](input)})); } catch(error) { console.log(JSON.stringify({error:error.message})); }"
    result = subprocess.run(["node", "--input-type=module", "-e", program], input=json.dumps(value),
                            capture_output=True, text=True, timeout=20, check=True)
    return json.loads(result.stdout)


class RunDeskChecks(unittest.TestCase):
    def configuration(self, **changes):
        return {"tasks": "/work/tasks/one.txt\n/work/tasks/two.txt", "checkout": "/work/engine",
                "runs": "/work/runs/first", "workspace": "/work/outputs", "calls": "12", "budget": "24",
                "timeout": "600", "deadline": "3600", **changes}

    def test_generated_arguments_use_the_existing_worker_parser(self):
        from overnight_queue import main
        from unittest.mock import patch
        prepared = call("prepareQueue", self.configuration())["value"]
        self.assertEqual(prepared["manifest"], "/work/tasks/one.txt\n/work/tasks/two.txt\n")
        self.assertEqual(prepared["taskCount"], 2)
        arguments = shlex.split(prepared["command"].split("\n", 1)[1])[3:]
        with patch("overnight_queue.run_queue", return_value=0) as runner:
            main(arguments)
        parsed = runner.call_args.args[0]
        self.assertEqual(str(parsed.manifest), "/work/engine/baltor-tasks.txt")
        self.assertEqual(parsed.max_calls_per_task, 12)
        self.assertEqual(parsed.queue_call_budget, 24)
        self.assertEqual(parsed.task_timeout, 600)
        self.assertEqual(parsed.queue_timeout, 3600)
        self.assertFalse(parsed.fresh)
        self.assertEqual(prepared["statusCommand"], prepared["command"] + " --status")

    def test_shell_metacharacters_remain_one_literal_argument(self):
        folder = "/work/a folder'$(printf injected);still-a-path"
        prepared = call("prepareQueue", self.configuration(checkout=folder, runs=folder + "/runs"))["value"]
        first, second = prepared["command"].split("\n", 1)
        self.assertEqual(shlex.split(first), ["cd", folder, "&&"])
        arguments = shlex.split(second)
        self.assertEqual(arguments[3], folder + "/baltor-tasks.txt")
        self.assertEqual(arguments[arguments.index("--runs-dir") + 1], folder + "/runs")
        self.assertNotIn("--authorize-reconcile", arguments)

    def test_invalid_limits_and_paths_refuse_preparation(self):
        for change in ({"budget": "0"}, {"calls": "1.5"}, {"deadline": "Infinity"},
                       {"runs": "relative"}, {"checkout": "/work\nsecond-command"},
                       {"tasks": ""}, {"tasks": "/work/one\n/work/one"}):
            self.assertIn("error", call("prepareQueue", self.configuration(**change)), change)

    def status(self, **changes):
        return {"record_type": "overnight_queue_status/v2", "binding_sha256": "a" * 64,
                "calls_allocated": 12, "observed_model_calls": None, "call_budget": 24,
                "deadline": 1791583200, "attempts": [{"task_file": "/work/one", "queue_status": "unknown",
                "allocation": 12, "exit": None}], **changes}

    def test_reservations_are_not_reported_as_observed_model_usage(self):
        value = call("readQueueStatus", json.dumps(self.status()))["value"]
        self.assertEqual(value["allocated"], 12)
        self.assertIsNone(value["observed"])
        self.assertEqual(value["attempts"][0]["status"], "unknown")
        self.assertIsNone(value["attempts"][0]["exit"])

    def test_old_versions_corrupt_counts_and_unknown_states_are_refused(self):
        for value in (self.status(record_type="overnight_queue_status/v1"),
                      self.status(calls_allocated=25), self.status(observed_model_calls="unknown"),
                      self.status(deadline=1e20),
                      self.status(attempts=[{"task_file": "/work/one", "queue_status": "accepted",
                                           "allocation": 12, "exit": 0}])):
            self.assertIn("error", call("readQueueStatus", json.dumps(value)))
        self.assertIn("error", call("readQueueStatus", "not JSON"))


if __name__ == "__main__":
    unittest.main()
