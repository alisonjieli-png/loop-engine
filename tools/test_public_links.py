"""The counted links of the public lists redirect only to addresses a list holds and keep nothing but daily counts.

Kind: development check over the service's counted redirect (`src/loop_engine/core/service_runtime/public_links.py`).
It starts a loopback service with a temporary database and no credential of its own. Each rule has a known-wrong
case beside it, and the named rules have mutant controls that patch the rule away and require the check to fail:

- an unknown list, link or row is not found, so a path can never redirect to an address the list does not hold;
- a link table with another record version, an unknown link kind, an address that is not a public https address
  or user information before the host is refused before it is used;
- a follow counts one per list, link, row and day, and a view counts one per list page and day; nothing from the
  request other than the path reaches a count or the database: a sent address header, cookie, browser detail or
  referring page is found nowhere in what the service keeps;
- a redirect is not cached and asks search engines not to index it, and robots.txt disallows /out/;
- counts are written to the service database, added to what the day holds, and folded into monthly totals after
  400 days.

    PYTHONPATH=src:tools python -m unittest tools/test_public_links.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loop_engine.core.service_runtime import public_links  # noqa: E402
from loop_engine.core.service_runtime.public_links import (  # noqa: E402
    COUNT_KIND, MONTHLY_KIND, PublicLinkError, PublicListLinks, fold_old_days, read_link_table)

TABLE = {"record_type": "public_list_links/v1", "list": "directory", "pages": ["/directory", "/mcp-directory"],
         "rows": {"io.github.alice/tool": {"site": "alice.example.org/docs", "code": "github.com/alice/tool"},
                  "docker/notes": {"site": "github.com/bob/notes"}}}
DAY = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)


def links(runtime=None, clock=None):
    return PublicListLinks(runtime, {"directory": read_link_table(json.loads(json.dumps(TABLE)))}, clock=clock or (lambda: DAY))


class LinkTables(unittest.TestCase):
    def test_the_reader_refuses_each_known_wrong_table(self):
        wrong = {
            "another record version": {**TABLE, "record_type": "public_list_links/v2"},
            "an extra field": {**TABLE, "rank": 1},
            "an unknown link kind": {**TABLE, "rows": {"x": {"affiliate": "example.org"}}},
            "a row without links": {**TABLE, "rows": {"x": {}}},
            "a plain http address": {**TABLE, "rows": {"x": {"site": "http://example.org"}}},
            "user information before the host": {**TABLE, "rows": {"x": {"site": "example.org@elsewhere.org/x"}}},
            "a bare network address": {**TABLE, "rows": {"x": {"site": "203.0.113.9/x"}}},
            "a list name that is not a token": {**TABLE, "list": "Directory List"},
        }
        for description, record in wrong.items():
            with self.subTest(case=description), self.assertRaises(PublicLinkError):
                read_link_table(record)

    def test_the_packaged_directory_table_is_read_and_names_its_pages(self):
        tables = public_links.packaged_link_tables()
        self.assertIn("directory", tables)
        self.assertEqual(tables["directory"]["pages"], ("/directory", "/mcp-directory"))
        self.assertTrue(all(address.startswith("https://") for row in tables["directory"]["rows"].values() for address in row.values()))


class Redirects(unittest.TestCase):
    def test_only_a_link_the_list_holds_is_followed_and_counted(self):
        counter = links()
        self.assertEqual(counter.followed("/out/directory/site/io.github.alice/tool"), "https://alice.example.org/docs")
        self.assertEqual(counter.followed("/out/directory/code/io.github.alice/tool"), "https://github.com/alice/tool")
        for path in ("/out/directory/paid/io.github.alice/tool", "/out/directory/site/io.github.alice/other",
                     "/out/models/site/io.github.alice/tool", "/out/directory/site/https://elsewhere.org",
                     "/out/directory/site/../io.github.alice/tool", "/out/directory", "/out/directory/site/"):
            with self.subTest(path=path):
                self.assertIsNone(counter.followed(path))
        self.assertEqual(counter.pending(), {("2026-09-24", "directory", "follow", "site", "io.github.alice/tool"): 1,
                                             ("2026-09-24", "directory", "follow", "code", "io.github.alice/tool"): 1})

    def test_a_counter_that_trusts_the_path_is_caught(self):
        def any_address(self, path):
            return ("directory", "site", "x", "https://" + path.rsplit("/", 1)[-1])
        with mock.patch.object(PublicListLinks, "destination", any_address):
            self.assertIsNotNone(links().followed("/out/directory/site/https://elsewhere.org"))

    def test_views_count_only_list_pages_and_a_head_request_counts_nothing(self):
        counter = links()
        self.assertTrue(counter.viewed("/directory"))
        self.assertTrue(counter.viewed("/mcp-directory"))
        self.assertFalse(counter.viewed("/pricing"))
        answer = counter.redirect("/out/directory/site/docker/notes", "HEAD", Answer)
        self.assertEqual(answer.status_code, 302)
        self.assertEqual(counter.pending(), {("2026-09-24", "directory", "view", "", ""): 2})

    def test_a_redirect_is_not_cached_and_not_indexed(self):
        answer = links().redirect("/out/directory/site/docker/notes", "GET", Answer)
        self.assertEqual((answer.status_code, answer.headers["Location"]), (302, "https://github.com/bob/notes"))
        self.assertEqual(answer.headers["Cache-Control"], "no-store")
        self.assertIn("noindex", answer.headers["X-Robots-Tag"])
        with mock.patch.dict(public_links.REDIRECT_HEADERS, {"X-Robots-Tag": ""}):
            self.assertNotIn("noindex", links().redirect("/out/directory/site/docker/notes", "GET", Answer).headers["X-Robots-Tag"])


class Answer:
    def __init__(self, status_code, headers):
        self.status_code, self.headers = status_code, headers


class Storage(unittest.TestCase):
    def test_counts_are_added_to_the_day_and_folded_into_months_after_400_days(self):
        from loop_engine.core.service_runtime.access_checks import prepared
        with tempfile.TemporaryDirectory(prefix="public-links-") as folder:
            runtime = prepared(Path(folder)).runtime
            counter = links(runtime)
            counter.followed("/out/directory/site/docker/notes")
            self.assertEqual(counter.flush()["outcome"], "completed")
            counter.followed("/out/directory/site/docker/notes")
            counter.followed("/out/directory/site/docker/notes")
            counter.flush()
            with runtime._catalog.store() as store:
                rows = runtime._catalog.rows_all(store, COUNT_KIND)
            self.assertEqual([(row["payload"]["row"], row["payload"]["count"]) for row in rows], [("docker/notes", 3)])
            old = links(runtime, clock=lambda: datetime(2025, 7, 1, tzinfo=timezone.utc))
            old.followed("/out/directory/site/docker/notes")
            old.flush()
            self.assertEqual(fold_old_days(runtime, "2026-09-24"), {"folded": 1, "months": 1})
            with runtime._catalog.store() as store:
                daily = runtime._catalog.rows_all(store, COUNT_KIND)
                monthly = runtime._catalog.rows_all(store, MONTHLY_KIND)
            self.assertEqual([row["payload"]["day"] for row in daily], ["2026-09-24"])
            self.assertEqual([(row["payload"]["month"], row["payload"]["count"]) for row in monthly], [("2025-07", 1)])

    def test_a_scheduled_pass_folds_old_days_once_a_day(self):
        from loop_engine.core.service_runtime.access_checks import prepared
        with tempfile.TemporaryDirectory(prefix="public-links-fold-") as folder:
            runtime = prepared(Path(folder)).runtime
            counter = links(runtime)
            with mock.patch.object(public_links, "fold_old_days", return_value={"folded": 0}) as fold:
                counter.maintain()
                counter.maintain()
            self.assertEqual(fold.call_count, 1)

    def test_a_failed_write_keeps_its_counts_for_the_next_flush(self):
        counter = links(type("Runtime", (), {"_catalog": None, "config": type("Config", (), {"writes_authorized": True})()})())
        counter.followed("/out/directory/site/docker/notes")
        self.assertEqual(counter.flush()["outcome"], "not_written")
        self.assertEqual(sum(counter.pending().values()), 1)


class ServedCounter(unittest.TestCase):
    """The running service: the redirect, robots.txt, and nothing from the request kept beside the path."""

    def test_the_service_keeps_only_the_path_of_a_followed_link(self):
        from loop_engine.core.service_runtime.access_checks import prepared
        from loop_engine.core.service_runtime.http_test_fixtures import running_http
        from loop_engine.core.service_runtime.http import ServiceHttpApplication
        with tempfile.TemporaryDirectory(prefix="public-links-http-") as folder:
            held = prepared(Path(folder))
            factory = lambda config: ServiceHttpApplication(held.runtime, held.provisioning, config)  # noqa: E731
            with running_http(held, application_factory=factory) as (base, service):
                identity = next(iter(service.public_links.tables["directory"]["rows"]))
                opener = urllib.request.build_opener(NoRedirect)
                planted = {"X-Forwarded-For": "198.51.100.23", "Cookie": "visitor=planted-cookie-7",
                           "User-Agent": "planted-browser-9", "Referer": "https://planted.example/page"}
                answer = opener.open(urllib.request.Request(base + "/out/directory/site/" + identity, headers=planted), timeout=10)
                self.assertEqual(answer.status, 302)
                self.assertTrue(answer.headers["Location"].startswith("https://"))
                self.assertEqual(answer.headers["Cache-Control"], "no-store")
                self.assertIn("noindex", answer.headers["X-Robots-Tag"])
                with self.assertRaises(urllib.error.HTTPError) as refused:
                    opener.open(base + "/out/directory/site/io.github.nobody/nothing", timeout=10)
                self.assertEqual(refused.exception.code, 404)
                robots = urllib.request.urlopen(base + "/robots.txt", timeout=10).read().decode("utf-8")
                self.assertIn("Disallow: /out/", robots)
                urllib.request.urlopen(urllib.request.Request(base + "/directory", headers=planted), timeout=10).read()
                pending = service.public_links.pending()
                service.public_links.flush()
                with held.runtime._catalog.store() as store:
                    stored = json.dumps(held.runtime._catalog.rows_all(store, COUNT_KIND))
        keys = json.dumps(sorted(map(list, pending)))
        self.assertIn(identity, keys)
        for value in planted.values():
            with self.subTest(sent=value):
                self.assertNotIn(value.split("=")[-1], keys + stored)
        self.assertIn('"event": "view"', stored)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

    def http_error_302(self, request, response, code, message, headers):
        return response


if __name__ == "__main__":
    unittest.main()
