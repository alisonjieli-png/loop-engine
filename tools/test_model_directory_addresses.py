"""An address the model directory served once still answers through the running service: never "not found".

Kind: development check over the service on a loopback socket, with a temporary database and no credential
of its own. It needs the serving extras, so it lives apart from tools/test_model_directory.py, which the daily
refresh workflow runs with the project alone. The rules:

- every address in the packaged moved-address record answers a permanent redirect (301) to an address that
  answers the page, or 410 Gone with the reason and the way back; HEAD answers the same status and length;
- a live model page answers 200 and an address the directory never served answers 404;
- the known-wrong control: a service without the moved-address record answers 404 at an old address, and
  the named check fails.

    PYTHONPATH=src:tools python -m unittest tools/test_model_directory_addresses.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loop_engine.core.service_runtime import model_directory as records  # noqa: E402

HTML = {"Accept": "text/html"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

    def http_error_301(self, request, response, code, message, headers):
        return response


def answer(opener, base: str, address: str, method: str = "GET") -> tuple:
    """(status, headers, body) of one request, whatever the status."""
    try:
        with opener.open(urllib.request.Request(base + address, method=method, headers=HTML), timeout=20) as reply:
            return reply.status, reply.headers, reply.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


class ServedMovedAddresses(unittest.TestCase):
    """The running service answers each address the directory stopped serving with 301 or 410."""

    def test_each_address_the_directory_stopped_serving_answers_301_or_410(self):
        from loop_engine.core.service_runtime.access_checks import prepared
        from loop_engine.core.service_runtime.http import ServiceHttpApplication
        from loop_engine.core.service_runtime.http_test_fixtures import running_http
        record = records._packaged(records.MOVED_FILE)
        live = records.load_directory().models[0]["slug"]
        with tempfile.TemporaryDirectory(prefix="model-directory-addresses-") as folder:
            held = prepared(Path(folder))
            factory = lambda config: ServiceHttpApplication(held.runtime, held.provisioning, config)  # noqa: E731
            with running_http(held, application_factory=factory) as (base, _service):
                opener = urllib.request.build_opener(NoRedirect)
                broken, targets = [], set()
                for item in record["moved"]:
                    status, headers, body = answer(opener, base, item["from"])
                    if (status, headers.get("Location"), body) != (301, item["to"], b""):
                        broken.append(f"{item['from']} answered {status} to {headers.get('Location')}")
                    targets.add(item["to"])
                for target in sorted(targets):
                    status = answer(opener, base, target)[0]
                    if status != 200:
                        broken.append(f"the redirect target {target} answered {status}")
                for item in record["gone"]:
                    status, headers, body = answer(opener, base, item["address"])
                    back = b'href="/models"' if item["address"].startswith("/models/") else b'href="/endpoints"'
                    if status != 410 or back not in body or b"was removed" not in body:
                        broken.append(f"{item['address']} answered {status} without the removed page")
                    head_status, head_headers, head_body = answer(opener, base, item["address"], "HEAD")
                    if (head_status, head_body, head_headers.get("Content-Length")) != (410, b"", str(len(body))):
                        broken.append(f"HEAD {item['address']} answered {head_status} with {len(head_body)} bytes")
                self.assertEqual(broken, [])
                self.assertEqual(answer(opener, base, "/models/" + live)[0], 200)
                self.assertEqual(answer(opener, base, "/models/no-such-model-anywhere")[0], 404)
                moved = record["moved"][0]
                self.assertEqual(answer(opener, base, moved["from"], "HEAD")[:1], (301,))

    def test_a_service_without_the_moved_record_is_caught(self):
        """The known-wrong control: every old address answers 404, and the named check fails."""
        with mock.patch.object(records, "load_moved", lambda: {}):
            result = unittest.TestResult()
            ServedMovedAddresses("test_each_address_the_directory_stopped_serving_answers_301_or_410").run(result)
        self.assertEqual(len(result.failures), 1)
        self.assertIn("answered 404", result.failures[0][1])


if __name__ == "__main__":
    unittest.main()
