"""Tests for the counting proxy, against a fake upstream that calls no model.

Run from this folder:

    python -m unittest test_meter -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import meter as meter_module  # noqa: E402


class FakeUpstream:
    """Answers chat completions with a fixed stream; counts what it receives."""

    def __init__(self, usage=True, status=200):
        self.received = []
        upstream = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                return

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                upstream.received.append(json.loads(self.rfile.read(length)))
                self.send_response(status)
                self.send_header("Content-Type", "text/event-stream")
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
                    chunks.append({"choices": [], "usage": {"prompt_tokens": 120,
                                                            "completion_tokens": 7,
                                                            "total_tokens": 127}})
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
                                                         "Authorization": "Bearer not-a-key"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


class MeterTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def make(self, upstream, ceiling=10):
        meter = meter_module.Meter(self.root / "ledger.jsonl", self.root / "transcripts", ceiling,
                                   upstream_port=upstream.port, upstream_timeout=10)
        port = meter.start()
        self.addCleanup(meter.stop)
        return meter, port

    def ledger(self):
        path = self.root / "ledger.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def context(self, trial="t1", model="m", cap=2, markers=()):
        return meter_module.StepContext(trial_id=trial, model=model, arm="a", family="phones",
                                        repetition=1, cap=cap, material_markers=markers)

    def test_a_request_is_forwarded_unchanged_and_recorded_with_usage(self):
        upstream = FakeUpstream()
        self.addCleanup(upstream.stop)
        meter, port = self.make(upstream)
        meter.open_step(self.context(markers=("MARKER-ONE", "MARKER-TWO")))
        status, data = post(port, "t1", "m", marker_text="MARKER-ONE")
        self.assertEqual(status, 200)
        self.assertIn(b"[DONE]", data)
        self.assertEqual(len(upstream.received), 1)
        self.assertEqual(upstream.received[0]["messages"][1]["content"], "clean it")
        events = [row["event"] for row in self.ledger()]
        self.assertEqual(events, ["sent", "completed"])
        completed = self.ledger()[1]
        self.assertEqual(completed["usage"], {"prompt_tokens": 120, "completion_tokens": 7,
                                              "total_tokens": 127})
        self.assertEqual(completed["tool_calls"], ["write"])
        self.assertEqual(completed["material_markers_present"], [True, False])
        self.assertNotIn("not-a-key", (self.root / "ledger.jsonl").read_text())

    def test_the_step_cap_refuses_without_forwarding(self):
        upstream = FakeUpstream()
        self.addCleanup(upstream.stop)
        meter, port = self.make(upstream)
        meter.open_step(self.context(cap=2))
        statuses = [post(port, "t1", "m")[0] for _ in range(3)]
        self.assertEqual(statuses, [200, 200, 429])
        self.assertEqual(len(upstream.received), 2)
        refused = [row for row in self.ledger() if row["event"] == "refused"]
        self.assertEqual([row["reason"] for row in refused], ["step_cap_reached"])

    def test_the_total_ceiling_counts_earlier_ledger_lines_after_a_restart(self):
        upstream = FakeUpstream()
        self.addCleanup(upstream.stop)
        meter, port = self.make(upstream, ceiling=3)
        meter.open_step(self.context(cap=5))
        self.assertEqual([post(port, "t1", "m")[0] for _ in range(2)], [200, 200])
        meter.stop()
        restarted, port = self.make(upstream, ceiling=3)
        self.assertEqual(restarted.physical_total, 2)
        self.assertEqual(restarted.remaining(), 1)
        restarted.open_step(self.context(trial="t2", cap=5))
        self.assertEqual([post(port, "t2", "m")[0] for _ in range(2)], [200, 429])
        self.assertEqual(len(upstream.received), 3)
        reasons = [row.get("reason") for row in self.ledger() if row["event"] == "refused"]
        self.assertEqual(reasons, ["total_ceiling_reached"])

    def test_an_unknown_step_or_another_model_is_refused(self):
        upstream = FakeUpstream()
        self.addCleanup(upstream.stop)
        meter, port = self.make(upstream)
        meter.open_step(self.context())
        self.assertEqual(post(port, "other", "m")[0], 429)
        self.assertEqual(post(port, "t1", "bigger-model")[0], 429)
        self.assertEqual(upstream.received, [])
        reasons = [row["reason"] for row in self.ledger()]
        self.assertEqual(reasons, ["unknown_or_closed_step", "model_differs_from_step"])

    def test_missing_usage_stays_unknown(self):
        upstream = FakeUpstream(usage=False)
        self.addCleanup(upstream.stop)
        meter, port = self.make(upstream)
        meter.open_step(self.context())
        post(port, "t1", "m")
        self.assertIsNone(self.ledger()[1]["usage"])

    def test_an_upstream_rate_limit_is_counted_and_named(self):
        upstream = FakeUpstream(status=429)
        self.addCleanup(upstream.stop)
        meter, port = self.make(upstream)
        meter.open_step(self.context())
        self.assertEqual(post(port, "t1", "m")[0], 429)
        completed = self.ledger()[1]
        self.assertEqual((completed["event"], completed["outcome"]), ("completed", "rate_limited"))
        self.assertEqual(meter.physical_total, 1)


if __name__ == "__main__":
    unittest.main()
