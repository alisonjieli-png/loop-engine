"""Rendered offering routes share navigation and preserve source-defined setup facts."""
import json
from pathlib import Path
import unittest

from loop_engine.core.service_runtime import offering_guides as guides
from loop_engine.core.service_runtime import web_pages

ASSETS = Path(__file__).resolve().parents[1] / "src/loop_engine/core/service_runtime/web_assets"


class OfferingGuideTests(unittest.TestCase):
    def test_routes_keep_shared_navigation_and_exact_assets(self):
        for path in guides.ADDRESSES:
            body, media = guides.rendered(path, "GET", "Baltor")
            text = body.decode()
            self.assertEqual(media, web_pages.HTML_MEDIA_TYPE)
            for address in ("/pricing", "/library", "/feeds", "/setup", "/support", "/terms", "/privacy"):
                self.assertIn('href="' + address + '"', text)
            self.assertIn("/assets/offering-pages.js?v=", text)
            self.assertIn("/assets/offering-pages.css?v=", text)
            self.assertIn('id="theme"', text)
            self.assertIsNone(guides.rendered(path, "POST", "Baltor"))
        self.assertIsNone(guides.rendered("/unregistered-guide", "GET", "Baltor"))

    def test_agent_collections_refer_to_the_packaged_directory(self):
        body = guides.feeds_setup_body()
        for _label, collections in guides.AGENT_FEEDS:
            for collection in collections:
                self.assertIn(collection, body)
        self.assertIn("/feeds/", body)
        self.assertNotIn("[PRICE]", body)

    def test_feed_setup_keeps_current_price_free_period_and_paid_consent(self):
        body = guides.feeds_setup_body()
        for fact in ("$9 a month", "December 31, 2026 (Eastern)", "opt-in"):
            self.assertIn(fact, body)
        self.assertNotIn("$4.99", body)

    def test_app_configuration_contains_references_never_example_credentials(self):
        endpoint = "https://baltor.example/mcp"
        entries = guides.app_configurations(endpoint)
        for entry in entries.values():
            self.assertIn(endpoint, json.dumps(entry))
            self.assertIn("Baltor-Step-Effects", json.dumps(entry))
        self.assertIn("${env:BALTOR_SERVICE_TOKEN}", json.dumps(entries["cursor"]))
        self.assertIn("${input:baltor-token}", json.dumps(entries["vscode"]))
        self.assertIn("${BALTOR_SERVICE_TOKEN}", json.dumps(entries["gemini-cli"]))

    def test_unknown_counts_remain_unknown_and_known_files_do_not_use_item_count(self):
        unknown = guides.harness_files_body()
        self.assertIn("data-library-file-count>Not measured</span>", unknown)
        known = guides.harness_files_body({"kinds": (), "items": 7, "distinct_files": 13})
        self.assertIn("13", known)
        self.assertNotIn("7 files", known)


if __name__ == "__main__":
    unittest.main()
