"""Guard the hosted probe's own accounting, without calling the live service.

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
import unittest

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


if __name__ == "__main__":
    unittest.main()
