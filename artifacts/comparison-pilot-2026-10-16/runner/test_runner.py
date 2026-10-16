"""Known-wrong controls for the pilot's guards: request limits, egress refusal, secret redaction and scoring refusals.

Run with: python3 -m unittest test_runner   (from this folder; standard library only, no model call)
"""
from __future__ import annotations

import http.client
import json
import socket
import tempfile
import time
import unittest
from pathlib import Path

import egress_proxy
import meter
import run_pilot
import scoring
from offline_fake_model import FakeModel


def post(port, path, body):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.request("POST", path, body=json.dumps(body), headers={"Content-Type": "application/json"})
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, data


class MeterLimits(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.fake = FakeModel([], self.folder / "fake")
        upstream = meter.Upstream(scheme="http", host="127.0.0.1", port=self.fake.start(), base_path="/v1")
        self.meter = meter.Meter(self.folder / "ledger.jsonl", self.folder / "bodies", ceiling=3, upstream=upstream)
        self.port = self.meter.start()

    def tearDown(self):
        self.meter.stop()
        self.fake.stop()

    def ledger(self):
        return [json.loads(line) for line in (self.folder / "ledger.jsonl").read_text().splitlines()]

    def test_cap_refuses_the_request_after_the_cap(self):
        self.meter.open_step(meter.StepContext("s1", "m", "none", "t", 1, cap=1))
        self.assertEqual(post(self.port, "/trial/s1/v1/chat/completions", {"model": "m", "messages": []})[0], 200)
        status, _ = post(self.port, "/trial/s1/v1/chat/completions", {"model": "m", "messages": []})
        self.assertEqual(status, 429)
        self.assertEqual([row["reason"] for row in self.ledger() if row["event"] == "refused"], ["step_cap_reached"])

    def test_deadline_refuses_a_late_request(self):
        self.meter.open_step(meter.StepContext("s2", "m", "none", "t", 1, cap=5,
                                               deadline_monotonic=time.monotonic() - 1))
        status, _ = post(self.port, "/trial/s2/v1/chat/completions", {"model": "m", "messages": []})
        self.assertEqual(status, 429)
        self.assertEqual(self.ledger()[-1]["reason"], "step_deadline_reached")

    def test_unknown_step_and_other_model_are_refused_and_not_counted(self):
        self.meter.open_step(meter.StepContext("s3", "m", "none", "t", 1, cap=5))
        self.assertEqual(post(self.port, "/trial/other/v1/chat/completions", {"model": "m"})[0], 429)
        self.assertEqual(post(self.port, "/trial/s3/v1/chat/completions", {"model": "x", "messages": []})[0], 429)
        self.assertEqual(self.meter.remaining(), 3)

    def test_ceiling_survives_a_restart(self):
        self.meter.open_step(meter.StepContext("s4", "m", "none", "t", 1, cap=5))
        for _ in range(3):
            post(self.port, "/trial/s4/v1/chat/completions", {"model": "m", "messages": []})
        again = meter.Meter(self.folder / "ledger.jsonl", self.folder / "bodies", ceiling=3,
                            upstream=self.meter.upstream)
        self.assertEqual(again.remaining(), 0)


class EgressRefusal(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.proxy = egress_proxy.EgressProxy(self.folder / "egress.jsonl", "t", ["baltor.ai"])
        self.port = self.proxy.start()

    def tearDown(self):
        self.proxy.stop()

    def connect(self, target):
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as client:
            client.sendall(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode())
            return client.recv(200).decode(errors="replace")

    def test_a_host_outside_the_allowlist_is_refused_and_recorded(self):
        self.assertIn("403", self.connect("example.com:443"))
        row = json.loads((self.folder / "egress.jsonl").read_text().splitlines()[-1])
        self.assertEqual((row["host"], row["allowed"], row["reason"]), ("example.com", False, "host_not_allowed"))

    def test_an_allowed_host_on_another_port_is_refused(self):
        self.assertIn("403", self.connect("baltor.ai:80"))

    def test_plain_http_is_refused(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.request("GET", "http://baltor.ai/")
        self.assertEqual(connection.getresponse().status, 403)


class Redaction(unittest.TestCase):
    def test_a_secret_in_a_result_file_stops_the_run(self):
        folder = Path(tempfile.mkdtemp())
        redactor = run_pilot.Redactor(["s3cret-value-0123456789"])
        (folder / "clean.json").write_text(redactor.text("token s3cret-value-0123456789"))
        redactor.assert_clean(folder)
        (folder / "leak.json").write_text("token s3cret-value-0123456789")
        with self.assertRaises(SystemExit):
            redactor.assert_clean(folder)


class SpaceshipRefusals(unittest.TestCase):
    def write(self, text):
        path = Path(tempfile.mkdtemp()) / "predictions.csv"
        path.write_text(text)
        return path

    def test_wrong_files_are_refused(self):
        ids = {"0001_01": True, "0002_01": False}
        cases = {"Passenger,Transported\n0001_01,True\n0002_01,False\n": "columns_not_exactly_PassengerId_Transported",
                 "PassengerId,Transported\n0001_01,True\n0001_01,False\n": "duplicate_passenger",
                 "PassengerId,Transported\n0001_01,yes\n0002_01,no\n": "label_not_boolean",
                 "PassengerId,Transported\n0001_01,True\n": "passenger_set_differs"}
        for text, reason in cases.items():
            self.assertEqual(scoring.read_predictions(self.write(text), ids), (None, reason))
        good, refusal = scoring.read_predictions(self.write("PassengerId,Transported\n0001_01,True\n0002_01,0\n"), ids)
        self.assertEqual((good, refusal), ({"0001_01": True, "0002_01": False}, None))


class WrongFileRule(unittest.TestCase):
    def test_changing_the_data_is_an_incident_and_adding_a_file_is_not(self):
        before, after = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        for root in (before, after):
            (root / "data").mkdir()
            (root / "data" / "train.csv").write_text("a\n1\n")
        (after / "data" / "train.csv").write_text("a\n2\n")
        (after / "solution.py").write_text("print(1)\n")
        changes, incidents = run_pilot.workspace_changes("c-spaceship-titanic", before, after)
        self.assertEqual(sorted(changes), ["data/train.csv", "solution.py"])
        self.assertEqual([row["file"] for row in incidents], ["data/train.csv"])


if __name__ == "__main__":
    unittest.main()
