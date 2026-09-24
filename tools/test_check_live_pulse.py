"""The live pulse passes a healthy service and names each known-wrong answer, with no network."""
from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_live_pulse as pulse_tool  # noqa: E402

HEALTH = {"record_type": "service_health/v2", "ready": True,
          "checks": [{"name": "store", "required": True, "passed": True}]}
CAPABILITIES = {"record_type": "service_capabilities/v1", "website": {"registration_available": True}}
IDENTITY = {"project_url": "https://identity.example", "publishable_key": "sb_publishable_example"}


class Response(io.BytesIO):
    def __init__(self, status, value):
        super().__init__(json.dumps({"result": value}).encode() if value is not None else b"<html></html>")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Opener:
    """Answers like the live service, with the changes a test names."""

    def __init__(self, changes=None):
        self.changes, self.asked = changes or {}, []

    def open(self, request, timeout=30):
        url = request.full_url
        self.asked.append(url)
        if url in self.changes:
            change = self.changes[url]
            if isinstance(change, int):
                raise urllib.error.HTTPError(url, change, "refused", {}, None)
            return Response(200, change)
        if url.endswith("/api/v1/health"):
            return Response(200, HEALTH)
        if url.endswith("/api/v1/capabilities"):
            return Response(200, CAPABILITIES)
        if url.endswith("/api/v1/account/identity"):
            return Response(200, IDENTITY)
        return Response(200, None)


HOSTS = ["baltor.ai", "docs.baltor.ai"]


class LivePulseTests(unittest.TestCase):
    def test_a_healthy_service_passes_and_the_identity_provider_is_asked(self):
        opener = Opener()
        report = pulse_tool.pulse(HOSTS, opener)
        self.assertTrue(report["passed"], report["problems"])
        self.assertIn("https://identity.example/auth/v1/health", opener.asked)
        self.assertEqual(report["registration_available"], True)

    def test_known_wrong_a_page_that_answers_503_fails(self):
        report = pulse_tool.pulse(HOSTS, Opener({"https://docs.baltor.ai/privacy": 503}))
        self.assertFalse(report["passed"])
        self.assertIn("docs.baltor.ai/privacy answered 503", report["problems"])

    def test_known_wrong_a_service_that_is_not_ready_fails(self):
        not_ready = {**HEALTH, "ready": False, "checks": [{"name": "store", "required": True, "passed": False}]}
        report = pulse_tool.pulse(HOSTS, Opener({"https://baltor.ai/api/v1/health": not_ready}))
        self.assertIn("baltor.ai: required check store fails", report["problems"])

    def test_known_wrong_hostnames_with_different_capabilities_fail(self):
        other = {**CAPABILITIES, "website": {"registration_available": False}}
        report = pulse_tool.pulse(HOSTS, Opener({"https://docs.baltor.ai/api/v1/capabilities": other}))
        self.assertIn("the hostnames report different capabilities", report["problems"])

    def test_known_wrong_an_identity_provider_that_refuses_fails(self):
        report = pulse_tool.pulse(HOSTS, Opener({"https://identity.example/auth/v1/health": 503}))
        self.assertIn("the identity provider's health address answered 503", report["problems"])

    def test_the_site_map_hostnames_and_the_technical_hostname_are_all_asked(self):
        hostnames = pulse_tool.site_hostnames()
        self.assertIn("baltor.ai", hostnames)
        self.assertIn(pulse_tool.TECHNICAL_HOSTNAME, hostnames)


if __name__ == "__main__":
    unittest.main()
