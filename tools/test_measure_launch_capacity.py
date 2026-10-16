"""The launch capacity probe stays read-only, bounded and honest about failures."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

import measure_launch_capacity as probe_tool


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    methods: list[str] = []
    delay = 0.0
    fail_paths: set[str] = set()

    def do_GET(self):  # noqa: N802
        Handler.methods.append(self.command)
        time.sleep(Handler.delay)
        status = 503 if self.path in Handler.fail_paths else 200
        body = b"ok"
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


class CapacityProbeTests(unittest.TestCase):
    def setUp(self):
        Handler.methods, Handler.delay, Handler.fail_paths = [], 0.0, set()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.origin = f"http://127.0.0.1:{self.server.server_address[1]}"

    def test_levels_step_up_and_count_every_request(self):
        probe = probe_tool.Probe(self.origin, ("/a", "/b"))
        report = probe_tool.measure(probe, [1, 2], 0.3, 1000, 0.05, 3000)
        self.assertEqual([level["concurrency"] for level in report["levels"]], [1, 2])
        self.assertEqual(report["requests_sent"], sum(level["requests"] for level in report["levels"]))
        self.assertEqual(set(Handler.methods), {"GET"})
        self.assertFalse(report["stopped_early"])
        self.assertEqual(set(report["levels"][0]["by_path"]), {"/a", "/b"})

    def test_known_wrong_failures_stop_the_run_and_stay_in_the_counts(self):
        Handler.fail_paths = {"/b"}
        report = probe_tool.measure(probe_tool.Probe(self.origin, ("/a", "/b")), [1, 2, 4], 0.3, 1000, 0.05, 3000)
        self.assertTrue(report["stopped_early"])
        self.assertEqual(len(report["levels"]), 1)
        level = report["levels"][0]
        self.assertGreater(level["error_share"], 0.4)
        self.assertIn("503", level["statuses"])
        self.assertEqual(level["by_path"]["/b"]["ok"], 0)

    def test_slow_responses_stop_at_the_p95_bound(self):
        Handler.delay = 0.05
        report = probe_tool.measure(probe_tool.Probe(self.origin, ("/a",)), [1, 2], 0.3, 1000, 0.05, 10)
        self.assertEqual((report["stopped_early"], len(report["levels"])), (True, 1))
        self.assertTrue(report["stop_reason"].startswith("p95_above"))

    def test_the_request_cap_bounds_the_whole_run(self):
        report = probe_tool.measure(probe_tool.Probe(self.origin, ("/a",)), [1, 4, 8], 1.0, 25, 0.05, 3000)
        self.assertLessEqual(report["requests_sent"], 25)
        self.assertEqual(len(Handler.methods), report["requests_sent"])

    def test_without_authorization_nothing_is_sent(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch("sys.stdout", io.StringIO()) as shown:
            code = probe_tool.main(["--origin", self.origin, "--output", str(Path(folder) / "r.json")])
        self.assertEqual((code, Handler.methods), (0, []))
        self.assertTrue(json.loads(shown.getvalue())["dry_run"])

    def test_known_wrong_origins_paths_and_bounds_are_refused(self):
        for origin in ("http://example.com", "https://example.com/path", "https://user:pw@example.com"):
            with self.assertRaises(ValueError):
                probe_tool.Probe(origin, ("/",))
        with self.assertRaises(ValueError):
            probe_tool.Probe(self.origin, ("https://elsewhere.example/",))
        with tempfile.TemporaryDirectory() as folder:
            for extra in (["--levels", "8,4"], ["--levels", "64"], ["--seconds", "120"],
                          ["--maximum-requests", "20000"]):
                with self.assertRaises(SystemExit), mock.patch("sys.stderr", io.StringIO()):
                    probe_tool.main(["--origin", self.origin, "--output", str(Path(folder) / "r.json"), *extra])

    def test_an_existing_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            existing = Path(folder) / "r.json"
            existing.write_text("{}")
            with self.assertRaises(SystemExit), mock.patch("sys.stderr", io.StringIO()):
                probe_tool.main(["--origin", self.origin, "--output", str(existing), "--authorize-read-only-load"])
            self.assertEqual(existing.read_text(), "{}")


if __name__ == "__main__":
    unittest.main()
