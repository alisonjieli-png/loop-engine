"""Checks for the promotion code operator command.

The command's host loader is replaced by a real service runtime over a
temporary SQLite database, so these checks exercise the real records and the
real refusals without a host configuration file, a network request or a
payment provider. The service domain has its own checks in
`loop_engine.core.service_runtime.promotion_checks`.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import promotion_codes as tool  # noqa: E402

from loop_engine.core.service_runtime.promotions import (  # noqa: E402
    PromotionPolicy, PromotionRedemption, PromotionRedemptionRequest,
)
from loop_engine.core.service_runtime.records import (  # noqa: E402
    ServiceRuntimeConfig, TenantKeyIssue, TenantRegistration,
)
from loop_engine.core.service_runtime.runtime import ServiceRuntime  # noqa: E402

NOW = 1_800_000_000
APPROVER = "reviewer.one"
APPROVAL = "review:promotion-2026-09-21"
CODE_SHAPE = re.compile(r"[A-Z]{2,12}(?:-[A-Z2-9]{4}){3}")


class _Application:
    """The one attribute the command reads from a loaded host application."""

    def __init__(self, runtime):
        self.runtime = runtime


class PromotionCommandTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="promotion-command-")
        self.addCleanup(self.folder.cleanup)
        config = ServiceRuntimeConfig(str(Path(self.folder.name) / "service.sqlite"), writes_authorized=True)
        self.runtime = ServiceRuntime(config, clock=lambda: NOW)
        self.runtime.register_tenant(TenantRegistration("account-a", "space:a"))
        self.key = self.runtime.issue_key(TenantKeyIssue("account-a", "operator command fixture"))
        patched = patch.object(tool, "load_host_application",
                               lambda path: (_Application(self.runtime), {"promotions": {}}))
        patched.start()
        self.addCleanup(patched.stop)

    def run_command(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = tool.main(["--config", "/absent/host.json", *argv])
        return status, out.getvalue(), json.loads(err.getvalue())

    def create(self, *extra):
        return self.run_command("create", "--label", "invited beta", "--days", "30",
                                "--redemptions", "2", "--window-days", "30",
                                "--approved-by", APPROVER, "--approval-ref", APPROVAL, *extra)

    def test_creation_without_confirmation_creates_nothing(self):
        status, shown, summary = self.create()
        self.assertEqual(status, tool.EXIT_REFUSED)
        self.assertEqual(shown, "")
        self.assertEqual(summary["refused"], "explicit_confirmation_required_no_code_was_created")
        listed = self.run_command("list")[2]["result"]
        self.assertEqual(listed["total_codes"], 0)

    def test_a_created_code_is_shown_once_and_never_stored(self):
        status, shown, summary = self.create("--acknowledge-promotion-grant")
        self.assertEqual(status, 0)
        code = shown.strip()
        self.assertEqual(shown, code + "\n")
        self.assertIsNotNone(CODE_SHAPE.fullmatch(code))
        self.assertNotIn(code, json.dumps(summary))
        self.assertIs(summary["result"]["code_returned"], False)
        self.assertNotIn(code.encode(), Path(self.runtime.config.database_path).read_bytes())

    def test_listing_shows_counts_and_accounts_but_no_code(self):
        code = self.create("--acknowledge-promotion-grant")[1].strip()
        redemption = PromotionRedemption(self.runtime, PromotionPolicy(redemption_enabled=True))
        redemption.redeem(self.runtime.authenticate_key(self.key.key),
                          PromotionRedemptionRequest(code=code, request_id="r1"))
        status, shown, summary = self.run_command("list")
        listed = summary["result"]
        self.assertEqual((status, shown), (0, ""))
        self.assertEqual(listed["total_codes"], 1)
        self.assertEqual(listed["codes"][0]["redemptions_used"], 1)
        self.assertEqual(listed["codes"][0]["redeemed_by"], ["account-a"])
        self.assertNotIn(code, json.dumps(summary))
        self.assertIs(listed["codes_returned"], False)

    def test_suspend_and_expire_need_a_known_code_identity(self):
        self.create("--acknowledge-promotion-grant")
        code_id = self.run_command("list")[2]["result"]["codes"][0]["code_id"]
        self.assertEqual(self.run_command("suspend", "--code-id", code_id)[0], 0)
        self.assertIs(self.run_command("list")[2]["result"]["codes"][0]["enabled"], False)
        self.assertEqual(self.run_command("expire", "--code-id", code_id)[0], 0)
        self.assertEqual(self.run_command("list")[2]["result"]["codes"][0]["expires_at"], NOW)
        status, _shown, summary = self.run_command("suspend", "--code-id", "not-a-code")
        self.assertEqual((status, summary["refused"]), (tool.EXIT_REFUSED, "promotion_code_not_found"))
        self.assertEqual(self.run_command("suspend")[2]["refused"], "a_code_identity_is_required")

    def test_refusals_before_any_record_is_written(self):
        for extra, expected in (
                (("--prefix", "lower"), "code_prefix_refused"),
                (("--prefix", "B"), "code_prefix_refused"),
                (("--approved-by", " "), "an_approver_and_an_approval_reference_are_required"),
                (("--window-days", "0"), "redemption_window_refused"),
                (("--starts-in-days", "40"), "redemption_window_refused")):
            status, shown, summary = self.create("--acknowledge-promotion-grant", *extra)
            self.assertEqual((status, shown), (tool.EXIT_REFUSED, ""), extra)
            self.assertEqual(summary["refused"], expected, extra)
        self.assertEqual(self.run_command("list")[2]["result"]["total_codes"], 0)

    def test_a_code_is_generated_here_and_never_taken_from_an_argument(self):
        options = {action.option_strings[0] for action in tool.build_parser()._actions
                   if action.option_strings}
        self.assertNotIn("--code", options)
        first, second = tool.generated_code("BALTOR"), tool.generated_code("BALTOR")
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("BALTOR-"))
        self.assertFalse(set(first[len("BALTOR-"):]) & set("IO01"))


if __name__ == "__main__":
    unittest.main()
