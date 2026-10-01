"""Unlisted Dot briefs: exact HTML/JSON, public-only inputs and route restrictions."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from loop_engine.core.service_runtime import dot_pages as pages, web_pages
from loop_engine.core.service_runtime.web_site_map import load_site_map


class DotPageTests(unittest.TestCase):
    def test_both_pages_and_json_use_the_same_reviewed_record(self):
        for address, name in pages.ADDRESSES.items():
            record = pages.load_record(name)
            body, media = pages.rendered(address, "GET", "Baltor")
            raw, kind = pages.rendered(address + ".json", "GET", "Baltor")
            self.assertEqual(json.loads(raw), record)
            self.assertEqual(kind, "application/json")
            self.assertEqual(media, "text/html")
            self.assertIn(pages.revision(record).encode(), body)
            self.assertIn(b'name="robots" content="noindex"', body)
            self.assertIn(record["updated_at"].encode(), body)
            self.assertEqual(pages.rendered(address, "HEAD", "Baltor"), (body, media))

    def test_both_pages_are_absent_from_navigation_and_search_index(self):
        site = load_site_map()
        for address in pages.ADDRESSES:
            self.assertFalse(site.page(address).indexed)
            self.assertNotIn(address.encode(), web_pages.sitemap_xml(site))
            self.assertNotIn(("Disallow: " + address).encode(), web_pages.robots_text(site))
            self.assertIn(b"Disallow: /account", web_pages.robots_text(site))
            for rows in site.header.values():
                self.assertNotIn(address, [row.href for row in rows])
            for group in site.footer_groups:
                self.assertNotIn(address, [row.href for row in group.links])

    def test_html_escapes_editorial_text_and_attributes(self):
        record = deepcopy(pages.load_record("context"))
        record["title"] = '<script>alert("test")</script>'
        record["links"][0]["label"] = '<img src=x onerror=alert(1)>'
        rendered = pages.page_body(pages.validate_record(record), "/dot-context")
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img src=x", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_unknown_fields_duplicate_tasks_and_unsafe_links_refuse(self):
        original = pages.load_record("context")
        for change in (lambda row: row.update(tenant_id="synthetic-private"),
                       lambda row: row.update(record_type="baltor_dot_brief/v999"),
                       lambda row: row["tasks"].append(row["tasks"][0]),
                       lambda row: row["tasks"][0].update(status="verified"),
                       lambda row: row["links"][0].update(url="javascript:alert(1)"),
                       lambda row: row["links"][0].update(url="//untrusted.example"),
                       lambda row: row.update(review_after=row["updated_at"]),
                       lambda row: row.update(updated_at="2026-10-01")):
            candidate = deepcopy(original)
            change(candidate)
            with self.assertRaises(ValueError):
                pages.validate_record(candidate)

    def test_only_exact_read_addresses_are_served(self):
        for path in ("/dot-context/", "/dot-context.json.json", "/dot-feedback/private", "/dot-feedback.csv"):
            self.assertIsNone(pages.rendered(path, "GET", "Baltor"))
        for method in ("POST", "PUT", "DELETE"):
            self.assertIsNone(pages.rendered("/dot-feedback", method, "Baltor"))

    def test_task_contract_contains_the_requested_work_and_no_claimed_schedule(self):
        record = pages.load_record("context")
        self.assertEqual(len(record["tasks"]), 8)
        text = json.dumps(record)
        for value in ("country", "17 goals", "10 to 60 minutes", "Ollama", "DueCare", "independent", "source"):
            self.assertIn(value, text)
        self.assertIn("scheduling happens in your existing task system", text)
        self.assertTrue(all(row["status"] != "complete" for row in record["tasks"]))


class DotPageHttpTests(unittest.TestCase):
    def setUp(self):
        from test_public_good_http import PublicGoodHttp
        self.fixture = PublicGoodHttp()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_read_only_public_routes_never_access_private_feedback(self):
        import httpx
        with patch.object(self.fixture.app.feedback, "staff_view", side_effect=AssertionError("private read")):
            with httpx.Client(base_url=self.fixture.base, trust_env=False) as client:
                for path in pages.ADDRESSES:
                    for route in (path, path + ".json"):
                        answer = client.get(route)
                        self.assertEqual(answer.status_code, 200, answer.text[:100])
                        self.assertEqual(answer.headers["x-robots-tag"], "noindex, nofollow, noarchive")
                        self.assertIn("no-store", answer.headers["cache-control"])
                        head = client.head(route)
                        self.assertEqual(head.status_code, 200)
                        self.assertEqual(head.content, b"")
                        self.assertEqual(int(head.headers["content-length"]), len(answer.content))
                        unchanged = client.get(route, headers={"If-None-Match": answer.headers["etag"]})
                        self.assertEqual(unchanged.status_code, 304)
                        self.assertEqual(unchanged.content, b"")
                        self.assertEqual(client.post(route, json={"note":"synthetic private note"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
