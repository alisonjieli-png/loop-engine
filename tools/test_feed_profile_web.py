"""Per-agent source selection and real HTTP export isolation over public metadata."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx

from loop_engine.core.service_runtime import feed_profiles as profiles, feed_profile_web as web
from loop_engine.core.service_runtime import feed_source_collections as collections
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.http_test_fixtures import running_http

TODAY = "2026-10-09"


def fields(**changes):
    return {"record_type": web.REQUEST, "directory_digest": profiles.current_directory().digest,
        "agent_label": "Coding reviewer", "collection_ids": ["coding-benchmarks"], "topics": [],
        "source_ids": [], "excluded_source_ids": [], "report_format": "markdown",
        "requested_poll_interval_minutes": 1440, **changes}


class FeedProfileExportTests(unittest.TestCase):
    def test_sources_can_be_picked_directly_and_excluded_without_affecting_another_agent(self):
        first = fields(agent_label="Coding reviewer", source_ids=["swe-bench"], collection_ids=[])
        second = fields(agent_label="Finance researcher", collection_ids=["finance-research"], excluded_source_ids=["sec-edgar"])
        one = web.export(first, today=TODAY)
        two = web.export(second, today=TODAY)
        self.assertEqual([item["id"] for item in one["profile"]["sources"]], ["swe-bench"])
        self.assertEqual([item["id"] for item in two["profile"]["sources"]], ["fred"])
        self.assertNotEqual(one["profile"]["profile_digest"], two["profile"]["profile_digest"])
        two["profile"]["sources"].clear()
        self.assertEqual(web.export(first, today=TODAY), one)
        for collection in one["profile"]["collections"]:
            self.assertEqual(collection["active_source_ids"], ["swe-bench"])

    def test_exact_native_bytes_are_reusable_by_existing_profile_validator(self):
        result = web.export(fields(), today=TODAY)
        self.assertFalse(result["hosted_settings_saved"])
        self.assertFalse(result["scheduled"])
        self.assertEqual(result["effects_granted"], [])
        self.assertEqual(result["upstream_requests"], 0)
        self.assertEqual(result["profile"]["client_reading_preference"]["schedule_owner"], "customer_harness")
        bodies = {row["path"]: row["content"].encode() for row in result["files"]}
        self.assertEqual(profiles.validate(json.loads(bodies["profile.json"]), as_of=TODAY)["status"], "validated_source_profile")
        for row in result["files"]:
            self.assertEqual(row["sha256"], sha256(bodies[row["path"]]).hexdigest())
            self.assertEqual(row["size_bytes"], len(bodies[row["path"]]))
        self.assertEqual(result["native_package"]["payload_bytes"], sum(map(len, bodies.values())))
        self.assertLessEqual(len(profiles.canonical(result)), web.MAXIMUM_RESPONSE_BYTES)

    def test_unknown_sources_conflicts_empty_selection_dates_cadence_and_versions_are_refused(self):
        wrong = [fields(source_ids=["not-a-source"]), fields(excluded_source_ids=["not-a-source"]),
            fields(collection_ids=[], source_ids=[]), fields(source_ids=["swe-bench"], excluded_source_ids=["swe-bench"]),
            fields(collection_ids=["finance-research"], excluded_source_ids=["sec-edgar", "fred"]),
            fields(source_ids=["swe-bench", "swe-bench"]), fields(requested_poll_interval_minutes=True),
            fields(requested_poll_interval_minutes=14), fields(requested_poll_interval_minutes=10081),
            fields(as_of="2026-10-09"), fields(record_type="agent_feed_profile_export_request/v2"),
            fields(tenant_id="another-account"), fields(agent_id="another-agent"), fields(url="https://example.invalid")]
        for value in wrong:
            with self.subTest(value=value), self.assertRaises(profiles.FeedProfileError):web.export(value, today=TODAY)

    def test_directory_change_requires_selection_review_instead_of_silent_expansion(self):
        body = json.loads(Path(collections.__file__).with_suffix(".json").read_bytes())
        body["collections"][0]["source_ids"].append("fred")
        newer = collections.parse_directory(json.dumps(body).encode())
        with self.assertRaisesRegex(profiles.FeedProfileError, "directory_changed"):
            web.export(fields(), directory=newer, today=TODAY)
        with patch.object(profiles, "current_directory", return_value=newer):
            accepted = web.export(fields(), today=TODAY)
        self.assertIn("fred", [row["id"] for row in accepted["profile"]["sources"]])

    def test_host_date_marks_old_documentation_as_held_and_does_not_claim_article_freshness(self):
        held = web.export(fields(), today="2026-11-10")["profile"]
        self.assertEqual(held["freshness"]["source_documentation_status"], "stale")
        self.assertEqual(held["freshness"]["upstream_item_freshness"], "not_observed")
        self.assertEqual(held["source_directory"]["source_docs_checked_on"], TODAY)
        with self.assertRaisesRegex(profiles.FeedProfileError, "date_in_future"):
            web.export(fields(), today="2026-10-08")

    def test_every_current_collection_compiles_in_installed_component(self):
        for collection in profiles.current_directory().collections:
            with self.subTest(collection=collection.id):
                self.assertTrue(web.export(fields(collection_ids=[collection.id]), today=TODAY)["files"])

    def test_real_http_is_bounded_private_and_does_not_mutate_the_catalogue(self):
        with TemporaryDirectory(prefix="feed-profile-http-") as temporary:
            case = Fixture(Path(temporary))
            case.publish([case.line("private-body", "PRIVATE PACKAGE BODY")])
            served = type("Served", (), {"runtime": case.runtime, "provisioning": case.binding()})()
            with running_http(served) as (origin, application), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
                before = client.get("/feeds/sources.json").content
                with patch.object(type(application.provisioning), "current_view", side_effect=AssertionError("catalogue read")):
                    first = client.post(web.PATH, json=fields())
                    second = client.post(web.PATH, json=fields(agent_label="Finance researcher", collection_ids=["finance-research"]))
                    self.assertEqual(first.status_code, 200, first.text)
                    self.assertEqual(second.status_code, 200, second.text)
                    self.assertEqual(first.headers["cache-control"], "no-store")
                    self.assertNotIn("set-cookie", first.headers)
                    self.assertNotIn("etag", first.headers)
                    self.assertNotIn("Finance researcher", first.text)
                    self.assertNotIn("Coding reviewer", second.text)
                    self.assertNotIn("PRIVATE PACKAGE BODY", first.text)
                    self.assertEqual(first.json()["execution"]["model_calls"], 0)
                    self.assertEqual(client.post(web.PATH, json=fields(as_of=TODAY)).status_code, 400)
                    self.assertEqual(client.post(web.PATH + "?agent=other", json=fields()).status_code, 400)
                    self.assertEqual(client.get(web.PATH).status_code, 404)
                    self.assertEqual(client.post(web.PATH, content=b" " * (web.MAXIMUM_REQUEST_BYTES+1),
                        headers={"Content-Type": "application/json"}).status_code, 413)
                self.assertEqual(client.get("/feeds/sources.json").content, before)

    def test_public_page_uses_directory_options_and_no_inline_private_state(self):
        section = web.page_section()
        self.assertIn('id="feed-profile-form"', section)
        self.assertIn('name="excluded_source_ids"', section)
        self.assertIn('name="requested_poll_interval_minutes"', section)
        self.assertNotIn("tenant_id", section)
        self.assertNotIn("localStorage", section)


if __name__ == "__main__":unittest.main()
