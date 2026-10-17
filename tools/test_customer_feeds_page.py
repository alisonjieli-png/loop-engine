"""The account page's saved feeds section: hidden unless offered, browser sessions only, text only, stable retries.

Reuses the offline Node VM approach of test_client_access_autoload.py: the real customer-feeds.js runs against a
fake DOM and deferred requests. Each known-wrong case removes one guard, and its named behavior check must fail.
The markup checks read the packaged page. Nothing here connects to a service, an identity provider or a model.
"""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/loop_engine/core/service_runtime/web_assets"
SOURCE = ASSETS / "customer-feeds.js"
RUNNER = ROOT / "tools/resources/customer-feeds-page-check.cjs"
NODE = shutil.which("node")


class _Section(HTMLParser):
    """The attributes of the saved feeds section and the scripts the page loads, read from the packaged page."""

    def __init__(self):
        super().__init__()
        self.section, self.scripts = None, []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "section" and values.get("id") == "account-feeds":
            self.section = values
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])


class SavedFeedsMarkupTests(unittest.TestCase):
    def test_the_section_is_hidden_in_the_served_page_and_its_script_loads_before_the_page_script(self):
        parser = _Section()
        parser.feed((ASSETS / "index.html").read_text(encoding="utf-8"))
        self.assertIsNotNone(parser.section)
        self.assertIn("hidden", parser.section)
        scripts = [src.split("?")[0] for src in parser.scripts]
        self.assertLess(scripts.index("/assets/customer-feeds.js"), scripts.index("/assets/service.js"))
        from loop_engine.core.service_runtime.web_pages import WEB_ASSETS
        self.assertEqual(WEB_ASSETS["/assets/customer-feeds.js"], ("customer-feeds.js", "text/javascript"))


@unittest.skipUnless(NODE, "node is not installed")
class SavedFeedsModuleTests(unittest.TestCase):
    def run_checks(self, source):
        done = subprocess.run([NODE, str(RUNNER)], input=source, text=True, capture_output=True, timeout=30, check=False)
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

    def test_the_real_module_passes_every_behavior_check(self):
        status, report = self.run_checks(SOURCE.read_text(encoding="utf-8"))
        for check in report["checks"]:
            with self.subTest(check=check["name"]):
                self.assertTrue(check["passed"], check.get("detail", ""))
        self.assertEqual(status, 0, report)

    def test_removed_browser_session_guard_is_detected(self):
        self.assert_removed_guard_fails('state.mode === "browser_identity" && ', "",
                                        "a_service_key_connection_never_manages_feeds")

    def test_removed_availability_guard_is_detected(self):
        self.assert_removed_guard_fails('$("account-feeds").hidden = !current().available; controls();',
                                        '$("account-feeds").hidden = false; controls();',
                                        "hidden_and_silent_until_the_service_offers_saved_feeds")

    def test_removed_request_identity_reuse_is_detected(self):
        self.assert_removed_guard_fails("if (!identities.has(signature)) identities.set(signature, crypto.randomUUID());",
                                        "identities.set(signature, crypto.randomUUID());",
                                        "a_retry_of_the_same_feed_repeats_its_request_identity")


if __name__ == "__main__":
    unittest.main()
