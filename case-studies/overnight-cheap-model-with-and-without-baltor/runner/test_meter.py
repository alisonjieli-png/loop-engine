"""Tests for the counting proxy, against a fake provider that calls no model.

Run from this folder:

    python -m unittest test_meter -v

Derived from the proxy tests of the data cleanup study, with the provider key,
header and ledger recovery checks added.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import meter as meter_module  # noqa: E402

KEY_VARIABLE = "STUDY_TEST_PROVIDER_KEY"
KEY = "test-provider-key-value-9f3a"


class FakeProvider:
    """Answers chat completions with a fixed stream; records what it receives."""

    def __init__(self, usage=True, status=200):
        self.received, self.headers = [], []
        provider = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                return

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                provider.received.append(json.loads(self.rfile.read(length)))
                provider.headers.append(dict(self.headers))
                self.send_response(status)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("X-Request-Id", "req-123")
                self.send_header("Set-Cookie", "session=private")
                self.end_headers()
                if status != 200:
                    self.wfile.write(b'{"error":"busy"}')
                    return
                chunks = [
                    {"choices": [{"index": 0, "delta": {"role": "assistant", "content": "DO"}}]},
                    {"choices": [{"index": 0, "delta": {"tool_calls": [
                        {"index": 0, "id": "c1", "type": "function",
                         "function": {"name": "write", "arguments": "{}"}}]}}]},
                    {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
                ]
                if usage:
                    chunks.append({"choices": [], "usage": {
                        "prompt_tokens": 120, "completion_tokens": 7, "total_tokens": 127,
                        "prompt_tokens_details": {"cached_tokens": 64}}})
                for chunk in chunks:
                    self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
                self.wfile.write(b"data: [DONE]\n\n")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def post(port, trial, model, marker_text=""):
    body = json.dumps({"model": model, "stream": True, "messages": [
        {"role": "system", "content": "system " + marker_text},
        {"role": "user", "content": "clean it"}]}).encode()
    request = urllib.request.Request(f"http://127.0.0.1:{port}/trial/{trial}/v1/chat/completions",
                                     data=body, headers={"Content-Type": "application/json",
                                                         "Authorization": "Bearer harness-own-key"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


class MeterTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        patcher = mock.patch.dict(os.environ, {KEY_VARIABLE: KEY})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.folder.cleanup()

    def make(self, provider, ceiling=10, key_variable=KEY_VARIABLE):
        upstream = meter_module.Upstream(scheme="http", host="127.0.0.1", port=provider.port,
                                         base_path="/v1", key_variable=key_variable)
        meter = meter_module.Meter(self.root / "ledger.jsonl", self.root / "transcripts", ceiling,
                                   upstream, upstream_timeout=10)
        port = meter.start()
        self.addCleanup(meter.stop)
        return meter, port

    def ledger(self):
        path = self.root / "ledger.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def context(self, trial="t1", model="m", cap=2, markers=()):
        return meter_module.StepContext(trial_id=trial, model=model, arm="a", family="phones",
                                        repetition=1, cap=cap, material_markers=markers)

    def everything_written(self):
        texts = [(self.root / "ledger.jsonl").read_text()]
        texts += [path.read_text(errors="replace") for path in (self.root / "transcripts").rglob("*")
                  if path.is_file()]
        return "\n".join(texts)

    def test_a_request_is_forwarded_unchanged_and_recorded_with_usage(self):
        provider = FakeProvider()
        self.addCleanup(provider.stop)
        meter, port = self.make(provider)
        meter.open_step(self.context(markers=("MARKER-ONE", "MARKER-TWO")))
        status, data = post(port, "t1", "m", marker_text="MARKER-ONE")
        self.assertEqual(status, 200)
        self.assertIn(b"[DONE]", data)
        self.assertEqual(len(provider.received), 1)
        self.assertEqual(provider.received[0]["messages"][1]["content"], "clean it")
        self.assertEqual([row["event"] for row in self.ledger()], ["sent", "completed"])
        completed = self.ledger()[1]
        self.assertEqual(completed["usage"], {"prompt_tokens": 120, "completion_tokens": 7,
                                              "total_tokens": 127})
        self.assertEqual(completed["usage_reported"]["prompt_tokens_details"], {"cached_tokens": 64})
        self.assertEqual(completed["tool_calls"], ["write"])
        self.assertEqual(completed["material_markers_present"], [True, False])

    def test_the_provider_key_reaches_only_the_provider(self):
        provider = FakeProvider()
        self.addCleanup(provider.stop)
        meter, port = self.make(provider)
        meter.open_step(self.context())
        post(port, "t1", "m")
        self.assertEqual(provider.headers[0].get("Authorization"), f"Bearer {KEY}")
        self.assertNotIn(KEY, self.everything_written())
        self.assertNotIn("harness-own-key", json.dumps(provider.headers))

    def test_only_allowed_response_headers_are_kept(self):
        provider = FakeProvider()
        self.addCleanup(provider.stop)
        meter, port = self.make(provider)
        meter.open_step(self.context())
        post(port, "t1", "m")
        kept = self.ledger()[1]["response_headers"]
        self.assertEqual(kept.get("x-request-id"), "req-123")
        self.assertNotIn("set-cookie", kept)
        self.assertNotIn("session=private", self.everything_written())

    def test_a_missing_key_sends_nothing_to_the_provider(self):
        provider = FakeProvider()
        self.addCleanup(provider.stop)
        meter, port = self.make(provider, key_variable="STUDY_TEST_UNSET_VARIABLE")
        meter.open_step(self.context())
        self.assertEqual(post(port, "t1", "m")[0], 502)
        self.assertEqual(provider.received, [])
        completed = self.ledger()[1]
        self.assertEqual(completed["outcome"], "provider_key_missing")
        self.assertEqual(meter.physical_total, 1)

    def test_the_step_cap_refuses_without_forwarding(self):
        provider = FakeProvider()
        self.addCleanup(provider.stop)
        meter, port = self.make(provider)
        meter.open_step(self.context(cap=2))
        statuses = [post(port, "t1", "m")[0] for _ in range(3)]
        self.assertEqual(statuses, [200, 200, 429])
        self.assertEqual(len(provider.received), 2)
        refused = [row for row in self.ledger() if row["event"] == "refused"]
        self.assertEqual([row["reason"] for row in refused], ["step_cap_reached"])

    def test_the_total_ceiling_counts_earlier_ledger_lines_after_a_restart(self):
        provider = FakeProvider()
        self.addCleanup(provider.stop)
        meter, port = self.make(provider, ceiling=3)
        meter.open_step(self.context(cap=5))
        self.assertEqual([post(port, "t1", "m")[0] for _ in range(2)], [200, 200])
        meter.stop()
        restarted, port = self.make(provider, ceiling=3)
        self.assertEqual(restarted.physical_total, 2)
        self.assertEqual(restarted.remaining(), 1)
        restarted.open_step(self.context(trial="t2", cap=5))
        self.assertEqual([post(port, "t2", "m")[0] for _ in range(2)], [200, 429])
        self.assertEqual(len(provider.received), 3)
        reasons = [row.get("reason") for row in self.ledger() if row["event"] == "refused"]
        self.assertEqual(reasons, ["total_ceiling_reached"])

    def test_an_unreadable_ledger_line_is_counted_as_a_sent_request(self):
        provider = FakeProvider()
        self.addCleanup(provider.stop)
        meter, port = self.make(provider, ceiling=3)
        meter.open_step(self.context(cap=5))
        post(port, "t1", "m")
        meter.stop()
        with open(self.root / "ledger.jsonl", "a", encoding="utf-8") as handle:
            handle.write('{"event": "sent", "sequ')
        restarted, _ = self.make(provider, ceiling=3)
        self.assertEqual(restarted.unreadable_ledger_lines, 1)
        self.assertEqual(restarted.physical_total, 2)

    def test_an_unknown_step_or_another_model_is_refused(self):
        provider = FakeProvider()
        self.addCleanup(provider.stop)
        meter, port = self.make(provider)
        meter.open_step(self.context())
        self.assertEqual(post(port, "other", "m")[0], 429)
        self.assertEqual(post(port, "t1", "bigger-model")[0], 429)
        self.assertEqual(provider.received, [])
        reasons = [row["reason"] for row in self.ledger()]
        self.assertEqual(reasons, ["unknown_or_closed_step", "model_differs_from_step"])

    def test_missing_usage_stays_unknown(self):
        provider = FakeProvider(usage=False)
        self.addCleanup(provider.stop)
        meter, port = self.make(provider)
        meter.open_step(self.context())
        post(port, "t1", "m")
        self.assertIsNone(self.ledger()[1]["usage"])

    def test_an_upstream_rate_limit_is_counted_and_named(self):
        provider = FakeProvider(status=429)
        self.addCleanup(provider.stop)
        meter, port = self.make(provider)
        meter.open_step(self.context())
        self.assertEqual(post(port, "t1", "m")[0], 429)
        completed = self.ledger()[1]
        self.assertEqual((completed["event"], completed["outcome"]), ("completed", "rate_limited"))
        self.assertEqual(meter.physical_total, 1)


if __name__ == "__main__":
    unittest.main()
