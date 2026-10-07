"""The forwarding proxy range check reports drift from the pinned Cloudflare ranges and reads nothing unauthorized.

Every document is served by an injected reader built from the pinned set itself, so no test opens a connection. The
known-wrong cases: a read without the network authorization, documents that disagree with each other, an unreadable
document, and a published range the service would refuse to trust, whose candidate set must not be printed.
"""
from __future__ import annotations

import contextlib
import datetime
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import check_forwarding_proxy_ranges as tool  # noqa: E402
from loop_engine.core.service_runtime.forwarding_proxy import (  # noqa: E402
    RANGE_SETS_RECORD_TYPE, RANGES_RESOURCE, parse_range_sets, read_range_sets)

NOW = datetime.datetime(2026, 11, 2, 9, 30, 0, tzinfo=datetime.timezone.utc)


def pinned_entry():
    from importlib.resources import files
    return parse_range_sets(files("loop_engine").joinpath(*RANGES_RESOURCE).read_text("utf-8"))["sets"][0]


def documents(ipv4=None, ipv6=None, api_ipv4=None):
    """The three documents the pinned set names, by address: the JSON interface and the two text lists."""
    entry = pinned_entry()
    ipv4, ipv6 = ipv4 if ipv4 is not None else entry["ipv4"], ipv6 if ipv6 is not None else entry["ipv6"]
    api = {"result": {"ipv4_cidrs": api_ipv4 if api_ipv4 is not None else ipv4, "ipv6_cidrs": ipv6,
                      "etag": "38f79d050aa027e3be3865e495dcc9bc"},
           "success": True, "errors": [], "messages": []}
    bodies = [json.dumps(api).encode(), "\n".join(ipv4).encode(), "\n".join(ipv6).encode()]
    return {source["url"]: body for source, body in zip(entry["sources"], bodies)}


class Reader:
    """An injected reader that answers from a mapping and records every address it was asked for."""

    def __init__(self, bodies, status=200, failing=()):
        self.bodies, self.status, self.failing, self.asked = bodies, status, set(failing), []

    def __call__(self, url, timeout):
        self.asked.append(url)
        if url in self.failing:
            raise OSError("connection refused")
        return self.status, {"etag": '"38f79d050aa027e3be3865e495dcc9bc"'}, self.bodies[url]


class RangeCheck(unittest.TestCase):

    def run_check(self, reader, **options):
        return tool.check(authorize_network_reads=True, fetch=reader, now=NOW, **options)

    def test_without_the_network_authorization_nothing_is_read(self):
        reader = Reader(documents())
        record, code = tool.check(authorize_network_reads=False, fetch=reader, now=NOW)
        self.assertEqual((record["outcome"], record["reason"], code), ("refused", "network_reads_not_authorized", 2))
        self.assertEqual(reader.asked, [])

    def test_an_unknown_set_is_refused_before_any_read(self):
        reader = Reader(documents())
        record, code = self.run_check(reader, set_id="cloudflare-1999-01-01")
        self.assertEqual((record["outcome"], record["reason"], code), ("refused", "unknown_set_id", 2))
        self.assertEqual(reader.asked, [])

    def test_the_pinned_documents_are_unchanged(self):
        reader = Reader(documents())
        record, code = self.run_check(reader)
        self.assertEqual((record["outcome"], code), ("unchanged", 0))
        self.assertEqual(record["added"], {"ipv4": [], "ipv6": []})
        self.assertEqual(record["removed"], {"ipv4": [], "ipv6": []})
        self.assertEqual(sorted(reader.asked), sorted(source["url"] for source in pinned_entry()["sources"]))
        self.assertNotIn("candidate_set", record)

    def test_an_added_range_is_drift_with_a_candidate_the_service_reader_accepts(self):
        entry = pinned_entry()
        record, code = self.run_check(Reader(documents(ipv4=entry["ipv4"] + ["5.10.0.0/16"])))
        self.assertEqual((record["outcome"], code), ("drift", 1))
        self.assertEqual(record["added"], {"ipv4": ["5.10.0.0/16"], "ipv6": []})
        candidate = record["candidate_set"]
        self.assertEqual(candidate["set_id"], "cloudflare-2026-11-02")
        self.assertEqual(candidate["retrieved_at"], "2026-11-02T09:30:00Z")
        verified = read_range_sets({"record_type": RANGE_SETS_RECORD_TYPE, "sets": [candidate]})
        self.assertEqual(len(verified["cloudflare-2026-11-02"].networks), 23)

    def test_a_removed_range_is_drift(self):
        entry = pinned_entry()
        record, code = self.run_check(Reader(documents(ipv6=entry["ipv6"][:-1])))
        self.assertEqual((record["outcome"], code), ("drift", 1))
        self.assertEqual(record["removed"], {"ipv4": [], "ipv6": [entry["ipv6"][-1]]})

    def test_documents_that_disagree_are_reported_and_give_no_candidate(self):
        entry = pinned_entry()
        record, code = self.run_check(Reader(documents(api_ipv4=entry["ipv4"] + ["5.10.0.0/16"])))
        self.assertEqual((record["outcome"], code), ("sources_disagree", 1))
        self.assertNotIn("candidate_set", record)

    def test_an_unreadable_document_exits_two(self):
        bodies = documents()
        first = next(iter(bodies))
        cases = [Reader(bodies, status=500), Reader(bodies, failing=[first]),
                 Reader({**bodies, first: b"x" * (tool.MAXIMUM_DOCUMENT_BYTES + 1)}),
                 Reader({**bodies, first: b'{"success": false, "result": null}'}),
                 Reader({**bodies, first: b"not a range\n"})]
        for reader in cases:
            record, code = self.run_check(reader)
            self.assertEqual((record["outcome"], code), ("unreadable", 2))
            self.assertNotIn("candidate_set", record)

    def test_a_published_range_the_service_refuses_gives_drift_without_a_candidate(self):
        entry = pinned_entry()
        record, code = self.run_check(Reader(documents(ipv4=entry["ipv4"] + ["10.0.0.0/8"])))
        self.assertEqual((record["outcome"], code), ("drift", 1))
        self.assertIn("candidate_refused", record)
        self.assertNotIn("candidate_set", record)

    def test_main_prints_one_record_and_reads_nothing_without_authorization(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = tool.main([])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["outcome"], "refused")


if __name__ == "__main__":
    unittest.main()
