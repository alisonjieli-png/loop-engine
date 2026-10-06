"""A public feed over real temporary catalogue records; no provider calls or package-body disclosure."""
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
from xml.etree import ElementTree

from loop_engine.core.service_runtime import catalogue_feed as feed
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.catalogue_releases import rollback, withdraw
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding


class CatalogueFeedTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory(prefix="catalogue-feed-")
        self.addCleanup(self.folder.cleanup)
        self.case = Fixture(Path(self.folder.name))
        self.first = self.case.publish([self.case.line("hidden_item_identity", "DO-NOT-EXPOSE-BODY")],
                                       notes="DO-NOT-EXPOSE-OPERATOR-NOTE")
        self.view = self.case.view()

    def notice(self, view=None):
        return feed.snapshot(self.case.runtime, view or self.view)

    def code(self, action):
        try:
            action()
        except ServiceRuntimeError as error:
            return error.code
        return None

    def test_exact_public_aggregate_snapshot_does_not_read_or_name_bodies(self):
        with mock.patch.object(type(self.view.body_store), "read", side_effect=AssertionError("body read")):
            record = self.notice()
        self.assertEqual((record["packages"], record["distinct_files"]), (1, 1))
        self.assertEqual(record["release_changes"], {"added": 1, "changed": 0, "withdrawn": 0})
        self.assertEqual(record["coverage"], "current_served_state_only")
        encoded = json.dumps(record)
        for private in ("DO-NOT-EXPOSE", "hidden_item_identity", self.folder.name, self.case.key.key):
            self.assertNotIn(private, encoded)

    def test_rebuilding_a_view_does_not_create_an_update_or_change_any_representation(self):
        first = self.notice()
        rebuilt = self.notice(replace(self.view, built_at=self.view.built_at + 3600))
        self.assertEqual(first, rebuilt)
        for path in feed.FORMATS:
            self.assertEqual(feed.render(first, path, "https://feed.example.invalid"),
                             feed.render(rebuilt, path, "https://feed.example.invalid"))

    def test_a_new_pointer_refuses_the_old_view_and_a_rollback_has_a_new_notice_identity(self):
        old = self.notice()
        second = self.case.publish([self.case.line("second", "SECOND PRIVATE BODY")])
        self.assertEqual(self.code(self.notice), "catalogue_feed_updating")
        fresh = self.notice(self.case.view())
        self.assertNotEqual(fresh["notice_id"], old["notice_id"])
        rollback(self.case.context, to_release=self.first["release_id"], expected_release=second["release_id"])
        returned = self.notice(self.case.view())
        self.assertEqual(returned["release_id"], old["release_id"])
        self.assertNotEqual(returned["notice_id"], old["notice_id"])

    def test_a_withdrawal_changes_the_notice_and_keeps_original_release_counts_distinct(self):
        old = self.notice()
        withdraw(self.case.context, identity="hidden_item_identity", note_text="PRIVATE WITHDRAWAL NOTE")
        new = self.notice(self.case.view())
        self.assertEqual(new["release_id"], old["release_id"])
        self.assertNotEqual(new["notice_id"], old["notice_id"])
        self.assertEqual(new["packages"], 0)
        self.assertEqual(new["release_changes_basis"], "original_release_publication_not_subsequent_state_transitions")
        self.assertNotIn("PRIVATE WITHDRAWAL", json.dumps(new))

    def test_missing_source_or_incomplete_population_is_unavailable_not_a_zero_notice(self):
        self.assertEqual(self.code(lambda: self.notice(replace(self.view, source="image"))), "catalogue_feed_unavailable")
        original = self.view.summary()
        for bad in ({}, {**original, "file_population": None},
                    {**original, "file_population": {"complete": False}}, {**original, "items": True}):
            with mock.patch.object(type(self.view), "summary", return_value=bad):
                self.assertEqual(self.code(self.notice), "catalogue_feed_unavailable")

    def test_a_state_change_during_projection_refuses(self):
        summary = self.view.summary
        def changed():
            value = summary()
            withdraw(self.case.context, identity="hidden_item_identity", note_text="changed during projection")
            return value
        with mock.patch.object(type(self.view), "summary", side_effect=changed):
            self.assertEqual(self.code(self.notice), "catalogue_feed_updating")

    def test_json_rss_and_markdown_are_one_bounded_notice_not_a_history_or_okf_claim(self):
        record = self.notice()
        encoded = {}
        for path, media in feed.FORMATS.items():
            encoded[path], result_media = feed.render(record, path, "https://feed.example.invalid")
            self.assertEqual(result_media, media)
            self.assertLess(len(encoded[path]), feed.MAXIMUM_FEED_BYTES)
        doc = json.loads(encoded["/feeds/catalogue.json"])
        self.assertEqual(doc["version"], "https://jsonfeed.org/version/1.1")
        self.assertEqual(len(doc["items"]), 1)
        self.assertEqual(doc["items"][0]["_baltor"], record)
        self.assertNotIn("hubs", doc)
        xml = ElementTree.fromstring(encoded["/feeds/catalogue.rss"])
        self.assertEqual(xml.findtext("channel/item/guid"), record["notice_id"])
        self.assertIn(record["release_id"].encode(), encoded["/feeds/catalogue.md"])
        with self.assertRaises(ServiceRuntimeError):
            feed.render(record, "/feeds/catalogue.json", "https://example.invalid/\" onload=bad")
        self.assertEqual(self.code(lambda: feed.render(record, "/unknown", "https://feed.example.invalid")),
                         "catalogue_feed_format_unknown")

    def test_actual_public_http_polling_etags_head_and_failures_without_any_account(self):
        import httpx
        served = type("Served", (), {"runtime": self.case.runtime, "provisioning": self.case.binding()})()
        with running_http(served) as (origin, _application), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
            response = client.get("/feeds/catalogue.json")
            self.assertEqual(response.status_code, 200)
            self.assertIn("application/feed+json", response.headers["content-type"])
            self.assertEqual(response.headers["cache-control"], feed.CACHE_CONTROL)
            self.assertEqual(response.json()["items"][0]["_baltor"]["packages"], 1)
            self.assertNotIn("DO-NOT-EXPOSE", response.text)
            unchanged = client.get("/feeds/catalogue.json", headers={"If-None-Match": response.headers["etag"]})
            self.assertEqual(unchanged.status_code, 304)
            self.assertEqual(unchanged.content, b"")
            head = client.head("/feeds/catalogue.json")
            self.assertEqual(head.content, b"")
            self.assertEqual(int(head.headers["content-length"]), len(response.content))
            for path in ("/feeds/catalogue.rss", "/feeds/catalogue.md", "/feeds"):
                answer = client.get(path)
                self.assertEqual(answer.status_code, 200)
            for method, path in (("POST", "/feeds/catalogue.json"), ("GET", "/feeds/catalogue.json?identity=hidden_item_identity")):
                self.assertEqual(client.request(method, path).status_code, 400)
            self.case.publish([self.case.line("new", "never disclosed")])
            updating = client.get("/feeds/catalogue.json")
            self.assertEqual(updating.status_code, 503)
            self.assertEqual(updating.headers["cache-control"], "no-store")
            self.assertEqual(updating.json()["error"]["code"], "catalogue_feed_updating")


if __name__ == "__main__":
    unittest.main()
