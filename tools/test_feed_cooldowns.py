"""Provider cooldowns survive bounded feed reads, restart and forced cadence.

All transport responses are fixtures. Managed records and scheduler are real;
no public network, model call or installed schedule is exercised here.
"""
import io
from datetime import datetime, timezone
from email.message import Message
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import urllib.error

from knowledge_radar.community_intake import read_registry
from knowledge_radar.community_store import CommunityStore
from knowledge_radar.community_watch import network_for, tick
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport, HttpsResponse, _retry_after
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog

NOW = "2026-10-13T12:00:00Z"
EPOCH = datetime(2026, 10, 13, 12, tzinfo=timezone.utc).timestamp()
ACCEPT = "application/rss+xml, application/atom+xml, application/xml"
RSS = b'<rss><channel><item><title>Blender workflow update</title><link>https://forum.example/task</link><description>Godot shader workflow</description></item></channel></rss>'


class Opener:
    def __init__(self, status=429, retry="172800", date=None):
        self.status, self.retry, self.date, self.calls = status, retry, date, []

    def open(self, request, timeout):
        self.calls.append(request)
        headers = Message()
        if self.retry is not None:
            headers["Retry-After"] = self.retry
        if self.date:
            headers["Date"] = self.date
        raise urllib.error.HTTPError(request.full_url, self.status, "fixture refusal", headers, io.BytesIO(b"private error body"))


class Network:
    def __init__(self, response):
        self.response, self.calls, self.conditional = response, [], {}

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


class RetryAfterTransportTests(unittest.TestCase):
    def test_delta_seconds_are_finite_nonnegative_decimal_integers(self):
        for raw, expected in (("120", 120), ("0", 0), (" \t3600\t", 3600), ("0" * 30 + "1", 1)):
            self.assertEqual(_retry_after({"Retry-After": raw}, now=EPOCH), expected)
        for raw in (None, "", "-1", "+2", "1.5", "NaN", "inf", "1e6", "١٢", "1\r\nX: value", "9" * 201, True, 120):
            self.assertIsNone(_retry_after({"Retry-After": raw}, now=EPOCH), raw)

    def test_http_dates_and_obsolete_http_forms(self):
        for raw in ("Tue, 13 Oct 2026 13:00:00 GMT", "Tuesday, 13-Oct-26 13:00:00 GMT", "Tue Oct 13 13:00:00 2026"):
            self.assertEqual(_retry_after({"Retry-After": raw}, now=EPOCH), 3600)
        self.assertEqual(_retry_after({"Retry-After": "Tue, 13 Oct 2026 11:00:00 GMT"}, now=EPOCH), 0)
        for raw in ("Tue, 13 Oct 2026 13:00:00", "Tue, 13 Oct 2026 13:00:00 PST", "Tue, 99 Oct 2026 13:00:00 GMT", "not a date"):
            self.assertIsNone(_retry_after({"Retry-After": raw}, now=EPOCH))

    def test_clock_skew_cannot_shorten_server_date_interval(self):
        headers = {"Retry-After": "Tue, 13 Oct 2026 13:00:00 GMT", "Date": "Tue, 13 Oct 2026 12:00:00 GMT"}
        self.assertEqual(_retry_after(headers, now=EPOCH + 7200), 3600)
        self.assertEqual(_retry_after(headers, now=EPOCH - 3600), 7200)
        self.assertEqual(_retry_after({**headers, "Date": "malformed"}, now=EPOCH), 3600)
        self.assertIsNone(_retry_after(headers, now=float("nan")))

    def test_durable_mode_returns_one_accounted_response_without_pause_or_retry(self):
        for status in (429, 503):
            budget, log, opener = RequestBudget(1, maximum_pause_seconds=0), RequestLog(), Opener(status)
            transport = HttpsGetTransport(("forum.example",), budget, log, retry_rate_limit=False)
            transport._opener = opener
            answer = transport.get("forum.example", "/feed")
            self.assertEqual((answer.status, answer.retry_after, budget.used, len(opener.calls)), (status, 172800, 1, 1))
            self.assertEqual(budget.pauses, [])
            self.assertEqual(len(log.records), 1)
            self.assertNotIn("private error body", str(log.records))

    def test_default_inline_retry_is_preserved_and_bounded(self):
        sleeps = []
        budget = RequestBudget(2, maximum_pause_seconds=3, sleep=sleeps.append)
        transport = HttpsGetTransport(("forum.example",), budget, RequestLog())
        opener = Opener(retry="2")
        transport._opener = opener
        answer = transport.get("forum.example", "/feed")
        self.assertEqual((answer.status, budget.used, len(opener.calls)), (429, 2, 2))
        self.assertEqual(sleeps, [3])
        with self.assertRaises(ValueError):
            HttpsGetTransport(("forum.example",), budget, RequestLog(), retry_rate_limit="no")

    def test_date_header_reaches_existing_response_field(self):
        budget = RequestBudget(1, maximum_pause_seconds=0, clock=lambda: EPOCH)
        transport = HttpsGetTransport(("forum.example",), budget, RequestLog(), retry_rate_limit=False)
        transport._opener = Opener(retry="Tue, 13 Oct 2026 13:00:00 GMT")
        self.assertEqual(transport.get("forum.example", "/feed").retry_after, 3600)


class FeedCooldownTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "private"
        self.registry = read_registry()
        self.registry["sources"] = [dict(self.registry["sources"][0], id="test_forum", url="https://forum.example/feed")]
        self.addCleanup(mock.patch.stopall)
        mock.patch("knowledge_radar.community_watch.time.monotonic", return_value=0).start()

    def run_tick(self, network, now=NOW, **changes):
        return tick(self.registry, self.root, network_allowed=True, writes_allowed=True, network=network, now=now, **changes)

    def source(self):
        return CommunityStore(self.root).get("community.source.test_forum")["document"]["data"]

    def test_two_qualified_feed_declarations_keep_the_existing_tick_ceiling(self):
        registry = read_registry()
        self.assertEqual(len(registry["sources"]), 12)
        self.assertEqual(registry["maximum_reads_per_tick"], 12)
        expected = {"godot_news": "https://godotengine.org/rss.xml", "huggingface_blog": "https://huggingface.co/blog/feed.xml"}
        for source in registry["sources"]:
            if source["id"] in expected:
                self.assertEqual(source["url"], expected.pop(source["id"]))
                self.assertEqual(source["interval_seconds"], 21600)
                self.assertEqual(source["use"], "internal_link_discovery")
        self.assertEqual(expected, {})

    def test_limited_feed_window_remains_partial_without_conditional_validator(self):
        self.registry["maximum_entries_per_source"] = 1
        body = RSS.replace(b'</channel>', b'<item><title>Another Blender workflow</title><link>https://forum.example/second</link></item></channel>')
        report = self.run_tick(Network(HttpsResponse(200, body, etag='"partial"')))
        self.assertEqual(report["status"], "partial")
        self.assertTrue(report["sources"][0]["coverage"]["truncated"])
        self.assertEqual(self.source()["validators"], {})
        self.assertEqual(self.source()["last_successful_at"], NOW)

    def test_real_transport_preserves_long_cooldown_and_failed_outcome(self):
        log = RequestLog()
        network = network_for(self.registry, log)
        opener = Opener()
        network.transports[("test_forum", ACCEPT)]._opener = opener
        report = self.run_tick(network)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["sources"][0]["reason"], "source_http_429")
        self.assertEqual(self.source()["next_check_at"], "2026-10-15T12:00:01Z")
        self.assertEqual(self.source()["retry_after_not_before"], "2026-10-15T12:00:01Z")
        self.assertEqual((len(opener.calls), network.budget.used, network.budget.pauses), (1, 1, []))

    def test_restart_and_force_do_not_bypass_provider_minimum(self):
        self.run_tick(Network(HttpsResponse(429, b"", retry_after=172800)))
        for force in (False, True):
            network = Network(HttpsResponse(200, RSS))
            report = self.run_tick(network, now="2026-10-13T17:00:00Z", force=force)
            self.assertEqual(network.calls, [])
            self.assertEqual(report["status"], "partial")
            self.assertEqual(report["sources"][0]["status"], "provider_cooldown")

    def test_failed_refresh_retains_success_and_validators_then_recovery_clears_cooldown(self):
        self.run_tick(Network(HttpsResponse(200, RSS, etag='"original"')))
        self.run_tick(Network(HttpsResponse(503, b"", retry_after=172800)), now="2026-10-13T15:00:00Z")
        state = self.source()
        self.assertEqual((state["last_successful_at"], state["validators"]), (NOW, {"etag": '"original"'}))
        self.assertEqual(state["retry_after_not_before"], "2026-10-15T15:00:01Z")
        recovered = self.run_tick(Network(HttpsResponse(304, b"")), now="2026-10-15T15:00:01Z")
        self.assertEqual(recovered["sources"][0]["status"], "not_modified")
        self.assertNotIn("retry_after_not_before", self.source())
        self.assertEqual(self.source()["validators"], {"etag": '"original"'})

    def test_bad_or_missing_delay_uses_existing_backoff_not_success(self):
        for delay in (None, -1, float("nan"), float("inf"), True):
            with self.subTest(delay=delay), tempfile.TemporaryDirectory() as directory:
                self.root = Path(directory) / "private"
                report = self.run_tick(Network(HttpsResponse(429, b"", retry_after=delay)))
                self.assertEqual(report["sources"][0]["status"], "failed")
                self.assertEqual(self.source()["next_check_at"], "2026-10-13T16:00:00Z")
                self.assertNotIn("last_successful_at", self.source())

    def test_unrepresentable_valid_delay_requires_review_instead_of_truncating(self):
        self.run_tick(Network(HttpsResponse(429, b"", retry_after=1e100)))
        self.assertTrue(self.source()["retry_after_requires_review"])
        network = Network(HttpsResponse(200, RSS))
        report = self.run_tick(network, now="2027-10-13T12:00:00Z", force=True)
        self.assertEqual(network.calls, [])
        self.assertEqual(report["sources"][0]["status"], "provider_hold")

    def test_elapsed_collection_time_is_rounded_up(self):
        with mock.patch("knowledge_radar.community_watch.time.monotonic", side_effect=[0, 2.1]):
            self.run_tick(Network(HttpsResponse(503, b"", retry_after=172800)))
        self.assertEqual(self.source()["retry_after_not_before"], "2026-10-15T12:00:04Z")

    def test_changed_exact_source_does_not_reuse_another_urls_cooldown(self):
        self.run_tick(Network(HttpsResponse(429, b"", retry_after=172800)))
        self.registry["sources"][0]["url"] = "https://another.example/feed"
        network = Network(HttpsResponse(200, RSS))
        self.run_tick(network, now="2026-10-13T13:00:00Z")
        self.assertEqual(len(network.calls), 1)
        self.assertNotIn("retry_after_not_before", self.source())

    def test_known_wrong_inline_retry_loses_provider_cooldown_before_watch(self):
        network = network_for(self.registry, RequestLog())
        transport = network.transports[("test_forum", ACCEPT)]
        transport.retry_rate_limit = True  # Removed-guard control: original watch behavior.
        transport._opener = Opener()
        report = self.run_tick(network)
        self.assertEqual(report["sources"][0]["reason"], "PauseExceedsBound")
        self.assertNotIn("retry_after_not_before", self.source())
        self.assertEqual(self.source()["next_check_at"], "2026-10-13T16:00:00Z")


if __name__ == "__main__":
    unittest.main()
