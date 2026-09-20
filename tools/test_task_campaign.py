"""Tests for tools/task_campaign.py without network or solver launches.

Every test works on temporary directories: the task database constant is
monkeypatched, the health probe's urlopen is replaced by a fake that
records the TLS context and never connects, and no cell is ever solved.
They cover outcome scanning across gateway record versions, deferred-cell
counting, previous-attempt archiving, bridging-rule recording, and the
health probe's key and TLS behavior.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import ssl
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import task_campaign  # noqa: E402


def _gateway(version: int, calls: int) -> str:
    return json.dumps({"record_type": f"model_gateway_result/v{version}",
                       "physical_model_calls": calls})


class ScanOutcomeChecks(unittest.TestCase):
    def test_gateway_records_of_any_version_are_summed(self):
        text = "\n".join([
            _gateway(1, 2), _gateway(2, 3),
            json.dumps({"record_type": "other/v1",
                        "physical_model_calls": 100})])
        outcome = task_campaign._scan_outcome(text)
        self.assertEqual(outcome["model_calls"], 5)
        self.assertEqual(outcome["model_calls_from"], "gateway_docs_fallback")
        self.assertIn("no solve outcome doc", outcome["note"])

    def test_outcome_doc_without_a_count_gets_the_fallback_sum(self):
        text = "progress line\n" + _gateway(2, 4) + "\n" + json.dumps({
            "record_type": "solve_outcome/v6", "terminal_code": "ACCEPTED",
            "model_calls": None})
        outcome = task_campaign._scan_outcome(text)
        self.assertEqual(outcome["terminal_code"], "ACCEPTED")
        self.assertEqual(outcome["model_calls"], 4)
        self.assertEqual(outcome["model_calls_from"], "gateway_docs_fallback")

    def test_outcome_doc_with_its_own_count_is_kept(self):
        text = _gateway(1, 2) + "\n" + json.dumps({
            "record_type": "solve_outcome/v6", "terminal_code": "ACCEPTED",
            "model_calls": 7})
        outcome = task_campaign._scan_outcome(text)
        self.assertEqual(outcome["model_calls"], 7)
        self.assertNotIn("model_calls_from", outcome)

    def test_empty_or_non_json_stdout_gives_an_empty_outcome(self):
        self.assertEqual(task_campaign._scan_outcome(""), {})
        self.assertEqual(task_campaign._scan_outcome("nothing here"), {})


def _cell(task: str, status: str, **extra) -> dict:
    base = {"record_type": task_campaign.RECORD_TYPE, "task": task,
            "arm": "arm", "status": status, "solve_rc": None,
            "solve_terminal": None, "solve_error": "", "gate_passed": None,
            "gate_score": None, "model_calls": None, "error": "",
            "elapsed_seconds": 0.0}
    base.update(extra)
    return base


class WriteReportChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="campaign-report-")
        self.addCleanup(self.directory.cleanup)
        self.runs_dir = Path(self.directory.name)

    def test_deferred_cells_are_counted_apart_from_attempted(self):
        cells = [
            _cell("t1", "staged"),
            task_campaign.deferred_record({"task": "t2", "arm": "arm"},
                                          "endpoint unhealthy"),
            _cell("t3", "gate_passed", gate_passed=True, gate_score=0.9,
                  solve_rc=0),
            _cell("t4", "solve_failed", solve_rc=1),
        ]
        report = task_campaign.write_report(cells, self.runs_dir)
        self.assertEqual(report["cells_total"], 4)
        self.assertEqual(report["cells_attempted"], 2)
        self.assertEqual(report["cells_deferred"], 1)
        self.assertEqual(report["gate_passed"], 1)
        self.assertEqual(report["by_status"]["deferred"], 1)
        on_disk = json.loads((self.runs_dir / "report.json").read_text(
            encoding="utf-8"))
        self.assertEqual(on_disk["cells_deferred"], 1)
        self.assertEqual(on_disk["cells_attempted"], 2)
        markdown = (self.runs_dir / "report.md").read_text(encoding="utf-8")
        self.assertIn("(2 attempted, 1 deferred)", markdown)
        self.assertTrue(any("mid-run verifier" in item
                            for item in report["limitations"]))

    def test_a_retried_deferred_cell_replaces_the_prior_record(self):
        deferred = task_campaign.deferred_record(
            {"task": "t1", "arm": "arm"}, "endpoint unhealthy")
        first = task_campaign.write_report([deferred], self.runs_dir)
        self.assertEqual(first["cells_deferred"], 1)
        self.assertEqual(first["cells_attempted"], 0)
        second = task_campaign.write_report(
            [_cell("t1", "gate_failed", gate_passed=False, solve_rc=0)],
            self.runs_dir)
        self.assertEqual(second["cells_total"], 1)
        self.assertEqual(second["cells_deferred"], 0)
        self.assertEqual(second["cells_attempted"], 1)


class TaskDatabaseFixture(unittest.TestCase):
    """A temporary task database standing in for TASK_DB."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="campaign-cells-")
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.task_db = root / "adapted"
        task = self.task_db / "demo_task"
        (task / "data").mkdir(parents=True)
        (task / "task.txt").write_text("Predict the target.\n",
                                       encoding="utf-8")
        (task / "gate.sh").write_text("#!/bin/bash\nexit 0\n",
                                      encoding="utf-8")
        (task / "metric.json").write_text('{"metric": "rmse", "floor": 1.0}',
                                          encoding="utf-8")
        self.cells = root / "runs" / "cells"
        original = task_campaign.TASK_DB
        task_campaign.TASK_DB = self.task_db
        self.addCleanup(setattr, task_campaign, "TASK_DB", original)


class StageCellChecks(TaskDatabaseFixture):
    def test_previous_attempt_is_archived_not_deleted(self):
        cell_dir = self.cells / "demo_task__arm"
        first = task_campaign.stage_cell("demo_task", cell_dir)
        self.assertEqual(first["previous_attempt_dir"], "")
        attempt = cell_dir / "workspace" / "attempt-1"
        attempt.mkdir(parents=True)
        (attempt / "solution.py").write_text("def predict(row): return 1\n",
                                             encoding="utf-8")
        (cell_dir / "solve.stdout.json").write_text("{}", encoding="utf-8")
        (cell_dir / "cell.json").write_text('{"status": "gate_failed"}',
                                            encoding="utf-8")
        second = task_campaign.stage_cell("demo_task", cell_dir)
        archived = Path(second["previous_attempt_dir"])
        self.assertTrue(archived.is_dir())
        self.assertEqual(archived.parent, cell_dir.parent)
        self.assertTrue(archived.name.startswith("demo_task__arm.previous-"))
        self.assertEqual(
            (archived / "workspace" / "attempt-1" / "solution.py").read_text(
                encoding="utf-8"),
            "def predict(row): return 1\n")
        self.assertEqual((archived / "cell.json").read_text(encoding="utf-8"),
                         '{"status": "gate_failed"}')
        self.assertEqual((archived / "solve.stdout.json").read_text(
            encoding="utf-8"), "{}")
        self.assertFalse((cell_dir / "workspace").exists())
        self.assertFalse((cell_dir / "cell.json").exists())
        staged_text = (cell_dir / "task.txt").read_text(encoding="utf-8")
        self.assertTrue(staged_text.startswith("Predict the target."))
        self.assertIn("Evaluation contract", staged_text)
        self.assertEqual(first["staged_sha256"], second["staged_sha256"])
        self.assertTrue(second["contract_appended"])
        self.assertEqual(
            (self.task_db / "demo_task" / "task.txt").read_text(
                encoding="utf-8"),
            "Predict the target.\n")

    def test_archives_in_the_same_second_get_distinct_names(self):
        cell_dir = self.cells / "demo_task__arm"
        task_campaign.stage_cell("demo_task", cell_dir)
        second = task_campaign.stage_cell("demo_task", cell_dir)
        third = task_campaign.stage_cell("demo_task", cell_dir)
        self.assertNotEqual(second["previous_attempt_dir"],
                            third["previous_attempt_dir"])
        self.assertTrue(Path(second["previous_attempt_dir"]).is_dir())
        self.assertTrue(Path(third["previous_attempt_dir"]).is_dir())
        self.assertTrue(cell_dir.is_dir())
        names = sorted(p.name for p in cell_dir.parent.iterdir())
        self.assertEqual(len(names), 3)

    def test_insecure_health_probe_flag_parses_with_the_old_flags(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = task_campaign.main(["--list", "--insecure-health-probe"])
        self.assertEqual(code, 0)
        listed = json.loads(stdout.getvalue())
        self.assertEqual([item["task"] for item in listed], ["demo_task"])


class BridgeArtifactsChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="campaign-bridge-")
        self.addCleanup(self.directory.cleanup)
        self.cell_dir = Path(self.directory.name) / "demo_task__arm"
        self.workspace = self.cell_dir / "workspace"
        self.first = self.workspace / "attempt-1" / "solution.py"
        self.second = self.workspace / "attempt-2" / "solution.py"
        for path, text in ((self.first, "# attempt 1\n"),
                           (self.second, "# attempt 2\n")):
            path.parent.mkdir(parents=True)
            path.write_text(text, encoding="utf-8")
        now = time.time()
        os.utime(self.first, (now - 100, now - 100))
        os.utime(self.second, (now, now))

    def bridged_text(self):
        return (self.cell_dir / "solution.py").read_text(encoding="utf-8")

    def test_without_an_outcome_the_mtime_rule_is_recorded(self):
        record = task_campaign.bridge_artifacts(self.cell_dir)
        self.assertEqual(record, {
            "bridged": True,
            "bridged_from": "workspace/attempt-2/solution.py",
            "bridged_rule": "newest_by_mtime",
            "bridged_accepted": False})
        self.assertEqual(self.bridged_text(), "# attempt 2\n")

    def test_outcome_without_artifacts_also_records_the_mtime_rule(self):
        outcome = {"terminal_code": "VERIFICATION_FAILED", "artifacts": []}
        record = task_campaign.bridge_artifacts(self.cell_dir, outcome)
        self.assertEqual(record["bridged_rule"], "newest_by_mtime")
        self.assertFalse(record["bridged_accepted"])

    def test_outcome_named_artifact_wins_over_a_newer_attempt(self):
        outcome = {"terminal_code": "ACCEPTED", "solved": True,
                   "workspace": str(self.workspace),
                   "artifacts": [{"path": str(self.first), "verified": True}]}
        record = task_campaign.bridge_artifacts(self.cell_dir, outcome)
        self.assertEqual(record, {
            "bridged": True,
            "bridged_from": "workspace/attempt-1/solution.py",
            "bridged_rule": "outcome_artifact",
            "bridged_accepted": True})
        self.assertEqual(self.bridged_text(), "# attempt 1\n")

    def test_unverified_named_artifact_is_recorded_as_not_accepted(self):
        outcome = {"terminal_code": "VERIFICATION_FAILED",
                   "artifacts": [{"path": str(self.first), "verified": False}]}
        record = task_campaign.bridge_artifacts(self.cell_dir, outcome)
        self.assertEqual(record["bridged_rule"], "outcome_artifact_unverified")
        self.assertFalse(record["bridged_accepted"])
        self.assertEqual(record["bridged_from"],
                         "workspace/attempt-1/solution.py")

    def test_verified_artifact_outranks_an_earlier_unverified_one(self):
        outcome = {"artifacts": [
            {"path": str(self.second), "verified": False},
            {"path": str(self.first), "verified": True}]}
        record = task_campaign.bridge_artifacts(self.cell_dir, outcome)
        self.assertEqual(record["bridged_from"],
                         "workspace/attempt-1/solution.py")
        self.assertTrue(record["bridged_accepted"])

    def test_relative_artifact_path_resolves_against_the_workspace(self):
        outcome = {"workspace": str(self.workspace),
                   "artifacts": [{"path": "attempt-1/solution.py",
                                  "verified": True}]}
        record = task_campaign.bridge_artifacts(self.cell_dir, outcome)
        self.assertEqual(record["bridged_from"],
                         "workspace/attempt-1/solution.py")
        self.assertEqual(self.bridged_text(), "# attempt 1\n")

    def test_artifact_outside_the_cell_falls_back_to_the_mtime_rule(self):
        outside = Path(self.directory.name) / "elsewhere" / "solution.py"
        outside.parent.mkdir()
        outside.write_text("# outside\n", encoding="utf-8")
        outcome = {"artifacts": [{"path": str(outside), "verified": True}]}
        record = task_campaign.bridge_artifacts(self.cell_dir, outcome)
        self.assertEqual(record["bridged_rule"], "newest_by_mtime")
        self.assertFalse(record["bridged_accepted"])
        self.assertEqual(self.bridged_text(), "# attempt 2\n")

    def test_artifacts_that_are_not_solution_py_are_ignored(self):
        notes = self.first.parent / "notes.md"
        notes.write_text("notes\n", encoding="utf-8")
        outcome = {"artifacts": [{"path": str(notes), "verified": True}]}
        record = task_campaign.bridge_artifacts(self.cell_dir, outcome)
        self.assertEqual(record["bridged_rule"], "newest_by_mtime")
        self.assertEqual(self.bridged_text(), "# attempt 2\n")

    def test_nothing_to_bridge_stays_absent(self):
        empty = Path(self.directory.name) / "empty_cell"
        empty.mkdir()
        record = task_campaign.bridge_artifacts(empty)
        self.assertEqual(record, {"bridged": False, "bridged_from": "",
                                  "bridged_rule": "none",
                                  "bridged_accepted": False})
        self.assertFalse((empty / "solution.py").exists())


class EndpointHealthChecks(unittest.TestCase):
    KEY_ENV = "TASK_CAMPAIGN_TEST_KEY"
    URL = "https://127.0.0.1:9/v1"

    def probe(self, key, *, insecure=False):
        """Run one probe against a fake urlopen; return (result, contexts,
        request, stderr)."""
        contexts, requests = [], []

        def fake_urlopen(request, context=None, timeout=None):
            contexts.append(context)
            requests.append(request)
            raise OSError("connection refused by the test")

        environment = {self.KEY_ENV: key} if key is not None else {}
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, environment, clear=False):
            if key is None:
                os.environ.pop(self.KEY_ENV, None)
            with mock.patch.object(urllib.request, "urlopen", fake_urlopen), \
                    contextlib.redirect_stderr(stderr):
                result = task_campaign.endpoint_healthy(
                    self.URL, self.KEY_ENV, "model", timeout=5.0,
                    insecure=insecure)
        return result, contexts, requests, stderr.getvalue()

    def test_refuses_without_a_key_and_makes_no_request(self):
        (healthy, detail), contexts, requests, stderr = self.probe(None)
        self.assertFalse(healthy)
        self.assertEqual(detail, f"no key in {self.KEY_ENV}")
        self.assertEqual(contexts, [])
        self.assertEqual(requests, [])
        self.assertEqual(stderr, "")

    def test_default_probe_verifies_tls_and_sends_the_bearer_key(self):
        (healthy, detail), contexts, requests, stderr = self.probe("secret")
        self.assertFalse(healthy)
        self.assertIn("OSError", detail)
        self.assertEqual(len(contexts), 1)
        self.assertTrue(contexts[0].check_hostname)
        self.assertEqual(contexts[0].verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(requests[0].get_header("Authorization"),
                         "Bearer secret")
        self.assertEqual(requests[0].full_url, self.URL + "/chat/completions")
        self.assertEqual(stderr, "")

    def test_insecure_probe_restores_the_old_behavior_and_warns(self):
        (healthy, _detail), contexts, _requests, stderr = self.probe(
            "secret", insecure=True)
        self.assertFalse(healthy)
        self.assertFalse(contexts[0].check_hostname)
        self.assertEqual(contexts[0].verify_mode, ssl.CERT_NONE)
        self.assertIn("TLS verification disabled", stderr)

    def test_default_signature_is_unchanged_for_old_callers(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(self.KEY_ENV, None)
            self.assertEqual(
                task_campaign.endpoint_healthy(self.URL, self.KEY_ENV, "m"),
                (False, f"no key in {self.KEY_ENV}"))


if __name__ == "__main__":
    unittest.main()
