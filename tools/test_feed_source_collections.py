"""The public source directory is a bounded, dated reference projection, never fresh collected intelligence."""
from dataclasses import FrozenInstanceError
import ast
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from loop_engine.core.service_runtime import catalogue_feed, feed_source_collections as sources
from loop_engine.core.service_runtime import static_site_export
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
from loop_engine.core.service_runtime.records import ServiceRuntimeError


class FeedSourceCollectionsTests(unittest.TestCase):
    def source_record(self):
        return json.loads(Path(sources.__file__).with_suffix(".json").read_bytes())

    def refused(self, data):
        with self.assertRaises(ServiceRuntimeError) as failure:
            sources.parse_directory(json.dumps(data).encode())
        self.assertEqual(failure.exception.code, "feed_source_directory_invalid")

    def test_complete_directory_is_immutable_has_exact_references_and_useful_jobs(self):
        directory = sources.directory()
        self.assertEqual(len(directory.collections), 13)
        self.assertEqual(len(directory.sources), 28)
        self.assertEqual(directory.source_docs_checked_on, "2026-10-08")
        self.assertEqual(directory.digest, hashlib.sha256(Path(sources.__file__).with_suffix(".json").read_bytes()).hexdigest())
        self.assertTrue(all(len(collection.compare_fields) >= 4 and collection.agent_task
                            and collection.decision_question and collection.review_trigger for collection in directory.collections))
        self.assertTrue(all(source.access and source.reuse for source in directory.sources))
        with self.assertRaises(FrozenInstanceError):
            directory.digest = "a changed snapshot"

    def test_network_import_exception_allows_only_the_url_parser(self):
        def only_parser(source):
            network = {"urllib", "requests", "http", "socket", "httpx", "aiohttp"}
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Import):
                    if any(alias.name.split(".", 1)[0] in network for alias in node.names):
                        return False
                elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".", 1)[0] in network:
                    if node.module != "urllib.parse" or any(alias.name != "urlsplit" for alias in node.names):
                        return False
            return True
        source = Path(sources.__file__).read_text()
        self.assertTrue(only_parser(source))
        for added in ("import urllib.request", "from urllib import request", "import requests", "import http.client",
                      "import socket", "import httpx", "import aiohttp", "from urllib.parse import *"):
            self.assertFalse(only_parser(source + "\n" + added), added)

    def test_unknown_version_and_claimed_daily_refresh_are_refused(self):
        for key, value in (("record_type", "agent_feed_source_directory/v2"), ("refresh_mode", "daily"),
                           ("data_scope", "current_benchmark_results"), ("source_docs_checked_on", "2026-02-31")):
            data = self.source_record()
            data[key] = value
            self.refused(data)

    def test_unknown_fields_duplicate_identity_and_broken_source_reference_are_refused(self):
        wrong = []
        data = self.source_record()
        data["current_score"] = 99
        wrong.append(data)
        data = self.source_record()
        data["sources"][0]["id"] = data["sources"][1]["id"]
        wrong.append(data)
        data = self.source_record()
        data["sources"][0]["url"] = data["sources"][1]["url"]
        wrong.append(data)
        data = self.source_record()
        data["collections"][0]["source_ids"] = ["missing-source"]
        wrong.append(data)
        data = self.source_record()
        data["collections"][0]["source_ids"] *= 2
        wrong.append(data)
        data = self.source_record()
        data["collections"][0]["id"] = "../../account"
        wrong.append(data)
        for data in wrong:
            self.refused(data)

    def test_removed_contract_guard_admits_the_known_wrong_control(self):
        data = self.source_record()
        data["current_score"] = "unsupported claim"
        self.refused(data)
        with mock.patch.object(sources, "_fields", return_value=None):
            self.assertIsInstance(sources.parse_directory(json.dumps(data).encode()), sources.Directory)

    def test_unsafe_links_controls_bad_types_and_duplicate_json_keys_are_refused(self):
        for value in ("javascript:alert(1)", "https://name:password@example.invalid/", "https://example.invalid/?key=value",
                      "https://example.invalid/\n", 'https://example.invalid/\"onclick=bad', "file:///etc/passwd"):
            data = self.source_record()
            data["sources"][0]["url"] = value
            self.refused(data)
        data = self.source_record()
        data["sources"][0]["kind"] = []
        self.refused(data)
        with self.assertRaises(ServiceRuntimeError):
            sources.parse_directory(b'{"record_type":"first","record_type":"second"}')
        with self.assertRaises(ServiceRuntimeError):
            sources.parse_directory(b" " * (sources.MAXIMUM_DIRECTORY_BYTES + 1))

    def test_every_collection_has_deterministic_bounded_json_and_markdown_without_false_dates(self):
        paths = sources.formats()
        self.assertEqual(len(paths), 2 * (len(sources.directory().collections) + 1))
        for path, media in paths.items():
            with self.subTest(path=path):
                body, actual = sources.render(path, "https://feed.example.invalid")
                self.assertEqual(actual, media)
                self.assertEqual((body, actual), sources.render(path, "https://feed.example.invalid"))
                self.assertLess(len(body), sources.MAXIMUM_OUTPUT_BYTES)
                if path.endswith(".json"):
                    record = json.loads(body)
                    self.assertEqual(record["version"], sources.FEED_VERSION)
                    self.assertEqual(record["_baltor"]["refresh_mode"], "release_curated")
                    for item in record["items"]:
                        self.assertNotIn("date_published", item)
                        self.assertNotIn("date_modified", item)
                        self.assertEqual(item["_baltor"]["record_type"], sources.SOURCE_RECORD_TYPE)
                else:
                    self.assertIn(b"not a live research digest", body)
                    self.assertIn(b"Agent research task:", body)
                    self.assertIn(b"Decision question:", body)
                    self.assertIn(b"When to revisit:", body)

    def test_collection_selection_is_exact_without_other_sources_or_an_arbitrary_url(self):
        body, _media = sources.render("/feeds/collections/finance-research.json", "https://feed.example.invalid")
        record = json.loads(body)
        self.assertEqual([item["_baltor"]["id"] for item in record["items"]], ["sec-edgar", "fred"])
        self.assertEqual([item["id"] for item in record["_baltor"]["collections"]], ["finance-research"])
        for path in ("/feeds/collections/missing.json", "/feeds/collections/../founder-stack.json", "/feeds/sources.rss"):
            with self.assertRaises(ServiceRuntimeError):
                sources.render(path, "https://feed.example.invalid")
        with self.assertRaises(ServiceRuntimeError):
            sources.render("/feeds/sources.json", 'https://feed.example.invalid/\"bad')

    def test_public_page_shows_collections_limits_and_matching_downloads_with_escaped_text(self):
        body = catalogue_feed.page_body()
        self.assertIn("Updates your agents can use.", body)
        self.assertIn("not live digests", body)
        self.assertIn("Your harness owns scheduling and source access.", body)
        self.assertNotIn("personalized daily digests", body)
        self.assertNotIn("in development", body)
        self.assertNotIn("refreshing its context", body)
        self.assertNotIn("Baltor Pro", body)
        for path in sources.formats():
            self.assertIn(f'href="{path}"', body)
        data = self.source_record()
        data["sources"][0]["name"] = '<script>bad & "text"</script>'
        changed = sources.parse_directory(json.dumps(data).encode())
        with mock.patch.object(sources, "directory", return_value=changed):
            rendered = sources.page_section()
            self.assertNotIn("<script>bad", rendered)
            self.assertIn("&lt;script&gt;bad &amp;", rendered)

    def test_actual_http_is_anonymous_read_only_conditional_and_independent_of_catalogue(self):
        import httpx
        with TemporaryDirectory(prefix="feed-source-http-") as folder:
            case = Fixture(Path(folder))
            case.publish([case.line("not-a-source-reference", "PRIVATE PACKAGE BODY")])
            served = type("Served", (), {"runtime": case.runtime, "provisioning": case.binding()})()
            with running_http(served) as (origin, application), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
                with mock.patch.object(type(application.provisioning), "current_view", side_effect=AssertionError("catalogue read")):
                    for path, media in sources.formats().items():
                        with self.subTest(path=path):
                            answer = client.get(path)
                            self.assertEqual(answer.status_code, 200)
                            self.assertIn(media, answer.headers["content-type"])
                            self.assertEqual(answer.headers["cache-control"], sources.CACHE_CONTROL)
                            self.assertNotIn("set-cookie", answer.headers)
                            self.assertNotIn(folder, answer.text)
                            self.assertEqual(client.get(path, headers={"If-None-Match": answer.headers["etag"]}).status_code, 304)
                            head = client.head(path)
                            self.assertEqual(head.content, b"")
                            self.assertEqual(int(head.headers["content-length"]), len(answer.content))
                    for path in ("/feeds/sources.json?source=https://private.invalid/", "/feeds/collections/finance-research.md?account=other"):
                        self.assertEqual(client.get(path).status_code, 400)
                    self.assertEqual(client.post("/feeds/sources.json", content=b"{}").status_code, 400)
                    self.assertEqual(client.get("/feeds/collections/missing.json").status_code, 404)
                    with mock.patch.object(sources, "render", side_effect=ServiceRuntimeError("feed_source_directory_invalid")):
                        failed = client.get("/feeds/sources.json")
                        self.assertEqual(failed.status_code, 503)
                        self.assertEqual(failed.headers["cache-control"], "no-store")

    def test_cloudflare_export_uses_exact_bounded_bytes_and_feed_cache_class(self):
        paths = static_site_export.static_addresses(include_model_details=False)
        classes = static_site_export.header_classes("")
        self.assertEqual(classes["feed_source"]["headers"]["Cache-Control"], sources.CACHE_CONTROL)
        self.assertTrue(classes["feed_source"]["etag"])
        for path, media in sources.formats().items():
            self.assertIn(path, paths)
            body, actual = static_site_export.render(path, "baltor.ai", "Baltor")
            self.assertEqual((body, actual), sources.render(path, "https://baltor.ai"))
            self.assertEqual(static_site_export.header_class(path, media), "feed_source")
        self.assertNotIn("/feeds/catalogue.json", paths)

    def test_route_classification_does_not_read_the_directory(self):
        with mock.patch.object(sources, "directory", side_effect=ServiceRuntimeError("feed_source_directory_invalid")) as reader:
            for path in ("/feeds/sources.json", "/feeds/sources.md", "/feeds/collections/finance-research.json",
                         "/feeds/collections/not-in-directory.md"):
                self.assertTrue(sources.handles(path))
            for path in ("/", "/api/v1/health", "/api/v1/session", "/feeds/sources.rss",
                         "/feeds/collections/../account.json", "/feeds/collections/name.json/extra", None):
                self.assertFalse(sources.handles(path))
            reader.assert_not_called()
            # Restoring data-dependent classification reproduces the outage.
            with mock.patch.object(sources, "handles", side_effect=lambda path: path in sources.formats()):
                with self.assertRaises(ServiceRuntimeError):
                    sources.handles("/api/v1/health")

    def test_bad_directory_isolated_from_health_home_and_unauthorized_api(self):
        import httpx
        with TemporaryDirectory(prefix="feed-failure-isolation-") as folder:
            fixture = HttpDomainFixture(Path(folder))
            with running_http(fixture) as (origin, _application), httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
                expected = {path: client.get(path).status_code for path in
                            ("/", "/api/v1/health", "/api/v1/capabilities", "/api/v1/session")}
                self.assertEqual(expected, {"/": 200, "/api/v1/health": 200, "/api/v1/capabilities": 200,
                                            "/api/v1/session": 401})
                with mock.patch.object(sources, "directory", side_effect=ServiceRuntimeError("feed_source_directory_invalid")):
                    for path, status in expected.items():
                        answer = client.get(path)
                        self.assertEqual(answer.status_code, status, path)
                        self.assertEqual(answer.headers["cache-control"], "no-store")
                    for method in ("GET", "HEAD"):
                        for path in ("/feeds", "/feeds/sources.json", "/feeds/collections/hardware-fit.md"):
                            answer = client.request(method, path)
                            self.assertEqual(answer.status_code, 503, (method, path))
                            self.assertEqual(answer.headers["cache-control"], "no-store")
                            self.assertNotIn("etag", answer.headers)
                            if method == "HEAD":
                                self.assertEqual(answer.content, b"")
                            else:
                                self.assertEqual(answer.json()["error"]["code"], "feed_source_directory_unavailable")
                        refused = client.request(method, "/feeds/sources.json?source=unused")
                        self.assertEqual(refused.status_code, 400)
                        self.assertEqual(refused.headers["cache-control"], "no-store")
                self.assertEqual(client.get("/feeds/collections/not-in-directory.json").status_code, 404)
                self.assertEqual(client.get("/feeds/sources.json").status_code, 200)


if __name__ == "__main__":
    unittest.main()
