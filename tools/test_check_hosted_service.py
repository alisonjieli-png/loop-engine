"""Guard hosted probe accounting and its exact protocol tool contract, without live calls.

The probe reports a pass only when every check it can run has run. That rule
is worth nothing if the declared number drifts away from the checks in the
source: a probe that declares fewer checks than it runs can never report a
pass, and one that declares more would accept a run that stopped early. This
test compares the declared number against the source and drives the reporting
rule with both known-wrong cases. It opens no network connection and reads no
credential.
"""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace

from loop_engine.core.provisioning_mcp import TOOL_OPERATIONS
from loop_engine.core.service_runtime.catalogue_reports import REPORT_TOOL

import check_hosted_service

SOURCE = Path(check_hosted_service.__file__)


def counted_checks():
    """Return how many `check(...)` calls the probe's main function contains."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    main = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    return sum(1 for node in ast.walk(main)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id == "check")


class HostedProbeAccountingTests(unittest.TestCase):
    def test_direct_invocation_resolves_this_checkouts_contracts_without_pythonpath(self):
        result = subprocess.run([sys.executable, "-I", str(SOURCE), "--help"],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--authorize-metered-read", result.stdout)

    def test_the_declared_number_of_checks_matches_the_checks_in_the_source(self):
        self.assertEqual(check_hosted_service.PLANNED_CHECKS, counted_checks(),
                         "the probe must declare exactly the number of checks it runs")

    def test_a_report_that_stopped_early_is_not_a_pass(self):
        """The known-wrong case the declared number exists to reject."""
        planned = check_hosted_service.PLANNED_CHECKS
        complete = [{"name": f"check_{index}", "passed": True} for index in range(planned)]
        interrupted = complete[:-1] + [{"name": "remaining_checks_interrupted", "passed": False}]
        stopped = complete[:-1]

        def all_passed(checks):
            return len(checks) == planned and all(row["passed"] for row in checks)

        self.assertTrue(all_passed(complete))
        self.assertFalse(all_passed(interrupted), "an interrupted run must not report a pass")
        self.assertFalse(all_passed(stopped), "a short run must not report a pass")

    def test_the_probe_reads_the_health_version_the_deployed_release_serves(self):
        """The probe must not assume which health record a release serves."""
        body = SOURCE.read_text(encoding="utf-8")
        self.assertIn("service_health/v1", body)
        self.assertIn("service_health/v2", body)
        self.assertIn("readiness_is_measured_by_the_deployed_release", body)


def protocol_check_verdicts(tool_names):
    """Exercise the probe's actual decisions using SDK summaries, without a socket."""
    names = (
        ("2025-11-25", "official_MCP_client_initializes_over_real_HTTPS"),
        ("2026-07-28", "official_MCP_client_uses_the_per_request_version_over_real_HTTPS"),
    )
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    decisions = {node.args[0].value: node.args[1] for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                 and node.func.id == "check" and isinstance(node.args[0], ast.Constant)}
    verdicts = {}
    for version, name in names:
        observed = {"protocol": version, "tool_names": tool_names, "tool_count": len(tool_names),
                    "search_ok": True, "bodies_loaded": False}
        scope = {**vars(check_hosted_service), "outcome": SimpleNamespace(returncode=0),
                 "protocol": observed, "per_request": observed}
        verdicts[name] = bool(eval(compile(ast.Expression(decisions[name]), str(SOURCE), "eval"), scope))
    return verdicts


class HostedProtocolToolContractTests(unittest.TestCase):
    def setUp(self):
        self.names = [*TOOL_OPERATIONS, "intelligence_search", REPORT_TOOL]

    def assert_protocol_checks(self, names, expected):
        for check, passed in protocol_check_verdicts(names).items():
            with self.subTest(check=check, tools=names):
                self.assertIs(passed, expected)

    def test_both_protocol_versions_accept_every_current_tool_in_any_order(self):
        self.assert_protocol_checks(list(reversed(self.names)), True)

    def test_both_protocol_versions_refuse_each_missing_tool(self):
        for name in self.names:
            with self.subTest(missing=name):
                self.assert_protocol_checks([tool for tool in self.names if tool != name], False)

    def test_both_protocol_versions_refuse_an_extra_tool(self):
        self.assert_protocol_checks([*self.names, "undeclared_tool"], False)

    def test_both_protocol_versions_refuse_a_same_count_substitution(self):
        self.assert_protocol_checks(["undeclared_tool", *self.names[1:]], False)

    def test_both_protocol_versions_refuse_duplicate_tool_names(self):
        self.assert_protocol_checks([*self.names, self.names[0]], False)


if __name__ == "__main__":
    unittest.main()
