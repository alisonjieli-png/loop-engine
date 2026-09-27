"""Account reads wait for a confirmed session and keep requests within one sign-in.

Reuses the offline Node VM approach of test_facet_tags.py. A retained token is
available before /session completes; capabilities may arrive on either side
of that response. The actual client-access.js module must load usage, billing
and personal tokens once after readiness, clear them on sign-out, and ignore
an old generation's delayed response without losing the new pending request.

Known-wrong cases remove the readiness guard, the reset of the old pending
request, or its identity guard. Each must fail its named behavior check.
Nothing here connects to a service, identity provider or model.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/loop_engine/core/service_runtime/web_assets/client-access.js"
RUNNER = ROOT / "tools/resources/client-access-autoload-check.cjs"
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node is not installed")
class ClientAccessAutoloadTest(unittest.TestCase):
    def run_checks(self, source):
        done = subprocess.run([NODE, str(RUNNER)], input=source, text=True,
                              capture_output=True, timeout=30, check=False)
        self.assertIn(done.returncode, (0, 1), done.stderr or done.stdout)
        report = json.loads(done.stdout)
        self.assertEqual(report["total"], len(report["checks"]))
        self.assertGreater(report["total"], 0)
        return done.returncode, report

    def assert_removed_guard_fails(self, guard, replacement, check_name):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(source.count(guard), 1, "the removed-guard control must change exactly one guard")
        status, report = self.run_checks(source.replace(guard, replacement, 1))
        failures = {check["name"] for check in report["checks"] if not check["passed"]}
        self.assertEqual(status, 1, report)
        self.assertIn(check_name, failures, report)

    def test_account_reads_for_both_response_orders_and_signin_generations(self):
        status, report = self.run_checks(SOURCE.read_text(encoding="utf-8"))
        for check in report["checks"]:
            with self.subTest(check=check["name"]):
                self.assertTrue(check["passed"], check.get("detail", ""))
        self.assertEqual(status, 0, report)

    def test_removed_session_readiness_guard_is_detected(self):
        self.assert_removed_guard_fails(
            "if (readers.some(button => !button || button.disabled)) return;", "",
            "capabilities_before_session_loads_usage_and_billing_once")

    def test_removed_generation_reset_is_detected(self):
        self.assert_removed_guard_fails(
            "submission = null; loading = null; opened = false;",
            "submission = null; opened = false;",
            "new_generation_starts_its_own_client_token_request")

    def test_removed_pending_request_identity_guard_is_detected(self):
        self.assert_removed_guard_fails(
            "if (loading === pending) loading = null;", "loading = null;",
            "old_generation_cleanup_does_not_clear_new_pending_request")


if __name__ == "__main__":
    unittest.main()
