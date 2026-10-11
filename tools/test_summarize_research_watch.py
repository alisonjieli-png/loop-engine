"""The research watch separates source changes from failed collection and unreadable reports."""
from __future__ import annotations

import contextlib
import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import summarize_research_watch as summary  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORT = {"record_type": "research_source_watch_report/v1", "created_at": "2026-09-24T14:13:02Z", "mode": "online", "sources": [
    {"id": "zcode", "name": "ZCode source", "kind": "github_repository", "change": "changed",
     "url": "https://github.com/zai-org/ZCode", "roadmap_step": "S-6.42", "observed": {"revision": "29628c9a", "fingerprint": "a" * 40}, "failure": None},
    {"id": "spec", "name": "A specification", "kind": "web_page", "change": "unknown",
     "observed": None, "failure": {"kind": "network_error"}},
    {"id": "steady", "name": "Steady", "kind": "web_page", "change": "unchanged",
     "observed": {"fingerprint": "b" * 64}, "failure": None}]}


def run(argv):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        summary.main(argv)
    return stream.getvalue()


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "report.json"
        self.path.write_text(json.dumps(REPORT))

    def tearDown(self):
        self.folder.cleanup()

    def test_the_count_is_the_number_of_changed_sources(self):
        self.assertEqual(run([str(self.path), "--changed-count"]).strip(), "1")
        self.assertEqual(run([str(self.path), "--error-count"]).strip(), "1")

    def test_the_summary_names_the_changed_source_and_the_failed_check(self):
        text = run([str(self.path)])
        self.assertIn("[ZCode source](https://github.com/zai-org/ZCode)", text)
        self.assertIn("Checks failed: spec (network_error).", text)
        self.assertNotIn("Steady", text)

    def test_known_wrong_another_record_is_refused(self):
        self.path.write_text(json.dumps({"record_type": "something_else/v1", "sources": []}))
        with self.assertRaises(SystemExit):
            run([str(self.path)])

    def test_known_wrong_a_report_with_no_change_counts_zero(self):
        self.path.write_text(json.dumps({**REPORT, "sources": REPORT["sources"][1:]}))
        self.assertEqual(run([str(self.path), "--changed-count"]).strip(), "0")
        self.assertEqual(run([str(self.path), "--error-count"]).strip(), "1")

    def test_successful_first_observation_is_not_a_source_failure(self):
        self.path.write_text(json.dumps({**REPORT, "sources": [{**REPORT["sources"][2], "change": "unknown"}]}))
        self.assertEqual(run([str(self.path), "--changed-count"]).strip(), "0")
        self.assertEqual(run([str(self.path), "--error-count"]).strip(), "0")

    def test_missing_observation_is_coverage_loss_not_a_source_change(self):
        row = {**REPORT["sources"][2], "change": "unknown", "observed": None}
        self.path.write_text(json.dumps({**REPORT, "sources": [row]}))
        self.assertEqual(run([str(self.path), "--changed-count"]).strip(), "0")
        self.assertEqual(run([str(self.path), "--error-count"]).strip(), "1")
        self.assertIn("No observation recorded: steady.", run([str(self.path)]))
        self.assertNotIn("Checks failed: steady", run([str(self.path)]))

    def test_missing_and_malformed_reports_cannot_claim_zero_changes(self):
        malformed = [None, "not JSON", "[]", "null", json.dumps({**REPORT, "extra": float("nan")}),
                     json.dumps({"record_type": "other/v1", "sources": []}),
                     json.dumps({**REPORT, "sources": []}), json.dumps({**REPORT, "sources": ["not a source"]}),
                     json.dumps({**REPORT, "sources": [{**REPORT["sources"][2], "failure": False}]}),
                     json.dumps({**REPORT, "sources": [{**REPORT["sources"][2], "observed": []}]}),
                     json.dumps({**REPORT, "sources": [{**REPORT["sources"][2], "failure": {"kind": "timeout"}}]}),
                     json.dumps({**REPORT, "sources": [REPORT["sources"][2], REPORT["sources"][2]]}),
                     '{"record_type":"other/v1","record_type":"research_source_watch_report/v1","sources":[]}']
        for raw in malformed:
            with self.subTest(raw=raw):
                if raw is None:
                    self.path.unlink(missing_ok=True)
                else:
                    self.path.write_text(raw)
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    run([str(self.path), "--changed-count"])
                self.assertEqual(error.exception.code, 2)
                self.assertEqual(run([str(self.path), "--error-count"]).strip(), "1")

    def test_unexplained_command_failure_survives_a_valid_unchanged_report(self):
        self.path.write_text(json.dumps({**REPORT, "sources": [REPORT["sources"][2]]}))
        self.assertEqual(run([str(self.path), "--error-count", "--watch-exit-code", "2"]).strip(), "1")
        self.assertIn("Watcher exit status: 2", run([str(self.path), "--watch-exit-code", "2"]))


def workflow_condition(expression, outputs, outcome="success"):
    """Evaluate only the actual workflow's boolean comparison grammar, without running an issue command."""
    for name, value in {"steps.watch.outcome": outcome,
                        "steps.watch.outputs.changed": outputs.get("changed", ""),
                        "steps.watch.outputs.errors": outputs.get("errors", "")}.items():
        expression = expression.replace(name, repr(value))
    expression = expression.replace("always()", "True").replace("&&", " and ").replace("||", " or ")

    def value(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, bool)):
            return node.value
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            return (all if isinstance(node.op, ast.And) else any)(value(item) for item in node.values)
        if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
            left, right = value(node.left), value(node.comparators[0])
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
        raise AssertionError("unsupported workflow condition: " + ast.dump(node))

    return bool(value(ast.parse(expression, mode="eval").body))


class WorkflowChecks(unittest.TestCase):
    def setUp(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/research-watch.yml").read_text())
        self.steps = workflow["jobs"]["watch"]["steps"]
        self.watch = next(step for step in self.steps if step.get("id") == "watch")
        self.issue = next(step for step in self.steps if "gh issue create" in step.get("run", ""))
        self.failure = next(step for step in self.steps if step.get("name") == "Fail the run when collection coverage is degraded")

    def execute_watch_step(self, raw, exit_code):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            binaries = temporary / "bin"
            binaries.mkdir()
            # Replace only the bounded network reader. The actual workflow shell invokes the real summarizer.
            stub = binaries / "python"
            stub.write_text(f"#!{sys.executable}\n" + '''import os, sys
from pathlib import Path
root = Path(os.environ["RUNNER_TEMP"])
expected = ["tools/refresh_research_sources.py", "--online", "--max-online-sources", "50",
            "--prior-dir", str(root / "research-watch-prior"), "--output", str(root / "research-watch.json")]
assert sys.argv[1:] == expected, sys.argv[1:]
fixture = root / "fixture.json"
if fixture.exists():
    (root / "research-watch.json").write_bytes(fixture.read_bytes())
print("Fixture source watcher completed; no network requests.")
sys.exit(int(os.environ["TEST_WATCH_EXIT"]))
''')
            stub.chmod(0o700)
            if raw is not None:
                (temporary / "fixture.json").write_text(raw)
            output = temporary / "outputs"
            environment = {"PATH": str(binaries) + os.pathsep + os.defpath,
                           "RUNNER_TEMP": str(temporary), "GITHUB_OUTPUT": str(output),
                           "TEST_WATCH_EXIT": str(exit_code), "PYTHONDONTWRITEBYTECODE": "1"}
            result = subprocess.run(["bash", "-c", self.watch["run"]], cwd=ROOT, env=environment,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
            self.assertEqual(set(outputs), {"changed", "errors"})
            self.assertTrue((temporary / "research-watch.log").is_file())
            return outputs, (temporary / "research-watch.md").read_text()

    def test_actual_workflow_handles_success_change_partial_total_and_report_failure(self):
        changed, failed, unchanged = REPORT["sources"]
        cases = [
            ("unchanged", {**REPORT, "sources": [unchanged]}, 0, "0", "0", False),
            ("first observation", {**REPORT, "sources": [{**unchanged, "change": "unknown"}]}, 0, "0", "0", False),
            ("changed", {**REPORT, "sources": [changed, unchanged]}, 0, "1", "0", True),
            ("partial failure", {**REPORT, "sources": [failed, unchanged]}, 1, "0", "1", True),
            ("changed and failed", REPORT, 1, "1", "1", True),
            ("total failure", {**REPORT, "sources": [failed, {**failed, "id": "other"}]}, 1, "0", "2", True),
            ("missing report", None, 2, "unknown", "1", True),
            ("malformed report", "not JSON", 2, "unknown", "1", True),
            ("unexplained command failure", {**REPORT, "sources": [unchanged]}, 2, "0", "1", True),
        ]
        for name, report, exit_code, changes, errors, notify in cases:
            with self.subTest(case=name):
                raw = json.dumps(report) if isinstance(report, dict) else report
                outputs, text = self.execute_watch_step(raw, exit_code)
                self.assertEqual(outputs, {"changed": changes, "errors": errors})
                self.assertEqual(workflow_condition(self.issue["if"], outputs), notify)
                self.assertEqual(workflow_condition(self.failure["if"], outputs), errors != "0")
                if errors != "0":
                    self.assertTrue("coverage is degraded" in text or "coverage was not established" in text)
                if changes == "unknown":
                    self.assertIn("Change count is unknown", text)
                if name == "partial failure":
                    self.assertFalse(workflow_condition("steps.watch.outputs.changed != '0'", outputs),
                                     "the former condition must miss this retained failure control")

    def test_artifacts_survive_failure_and_existing_issue_identity_is_preserved(self):
        upload = next(step for step in self.steps if step.get("uses", "").startswith("actions/upload-artifact@"))
        self.assertEqual(upload["if"], "always()")
        for name in ("research-watch.json", "research-watch.md", "research-watch.log"):
            self.assertIn(name, upload["with"]["path"])
        self.assertEqual(upload["with"]["if-no-files-found"], "warn")
        self.assertNotIn("|| true", self.watch["run"])
        self.assertIn('--watch-exit-code "$watch_exit_code"', self.watch["run"])
        self.assertIn('--github-output "$GITHUB_OUTPUT"', self.watch["run"])
        self.assertIn('title="Research watch: sources changed"', self.issue["run"])
        self.assertIn('--body-file "$RUNNER_TEMP/research-watch.md"', self.issue["run"])
        self.assertLess(self.steps.index(upload), self.steps.index(self.failure))
        result = subprocess.run(["bash", "-c", self.failure["run"]], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)

    def test_a_missing_step_output_is_not_a_spurious_issue_or_a_new_source_claim(self):
        self.assertFalse(workflow_condition(self.issue["if"], {}, outcome="failure"))
        self.assertFalse(workflow_condition(self.failure["if"], {}))


if __name__ == "__main__":
    unittest.main()
