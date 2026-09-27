"""The customer delivery path, checked through the real service on loopback with its own fixtures.

Kind: continuous integration check.

On September 27, 2026 a customer run through the documented setup found that customers could not use the library
(handoff u of the consolidation, and docs/research/USER-JOURNEY-AND-3D-WITH-WITHOUT-2026-09-27.md). Each class here
holds one repair to the behaviour that run saw, and each has a known-wrong control that puts the old behaviour back
and must fail:

- the protocol tool `provisioning_read` delivers a package's files, not only the package document that lists them.

Every service here is a real application on a loopback socket over a temporary SQLite store and body folder, built
from `catalogue_release_checks.Fixture`. Nothing reaches a provider or the network beyond 127.0.0.1.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import httpx

from loop_engine.core.service_runtime.catalogue_release_checks import Fixture, bundle_line
from loop_engine.core.service_runtime.catalogue_serving_checks import _Served, _application
from loop_engine.core.service_runtime.http import (PACKAGE_READ_VERSION, TIERED_PROVISIONING_REQUEST_VERSION,
                                                   ServiceHttpApplication)
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.protocol_checks import _protocol_client

PNG = b"\x89PNG\r\n\x1a\n\x00a binary asset"
#: Ten thousand bytes of text, so a small answer limit holds one of them per page.
LONG_A = ("# Reference A\n" + "Tooth profile notes, \"quoted\" and plain.\n" * 240).encode()
LONG_B = ("# Reference B\n" + "Bore and hub notes: keep 8 mm.\n" * 320).encode()
#: Larger than any answer of the small limit, so the protocol names it and the download address serves it.
LARGE = bytes(range(256)) * 160
PACKAGE = (("SKILL.md", b"# Gear maker\nRead references/a.md first.\n", "text/markdown", "skill_definition"),
           ("assets/large.bin", LARGE, "application/octet-stream", "skill_asset"),
           ("assets/logo.png", PNG, "image/png", "skill_asset"),
           ("references/a.md", LONG_A, "text/markdown", "skill_reference"),
           ("references/b.md", LONG_B, "text/markdown", "skill_reference"))
SINGLE = (("SKILL.md", b"# One file\nA single-file skill.\n", "text/markdown", "skill_definition"),)
#: A protocol answer limit small enough that the package needs two pages and one file cannot fit any answer.
ANSWER_BYTES = 40_000


def v2(operation, **fields):
    return {"record_type": TIERED_PROVISIONING_REQUEST_VERSION, "operation": operation, **fields}


class _Keyed:
    """What the protocol client helper reads from a fixture: the headers of one account."""

    def __init__(self, key):
        self.key = key

    def headers(self, _tenant="alpha"):
        return {"Authorization": "Bearer " + self.key}


def file_bytes(row):
    """The exact bytes of one delivered file, decoded as the answer says it was encoded."""
    if row["encoding"] == "utf-8":
        return row["content"].encode("utf-8")
    if row["encoding"] == "base64":
        return base64.b64decode(row["content"], validate=True)
    raise AssertionError("unknown encoding " + repr(row["encoding"]))


class DeliveryService:
    """One served store with a multi-file package and a single-file skill, and one entitled account."""

    def __init__(self, stack, **configuration):
        folder = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="customer-delivery-")))
        self.case = Fixture(folder / "service")
        self.case._bytes = {"gear_maker": tuple(row[1] for row in PACKAGE),
                            "one_file": tuple(row[1] for row in SINGLE)}
        self.case.publish([bundle_line("gear_maker", PACKAGE, effects=("reads_fs",)),
                           bundle_line("one_file", SINGLE, effects=("reads_fs",))])
        self.served = _Served(self.case)
        self.base, self.service = stack.enter_context(running_http(
            self.served, application_factory=_application(self.served, 60), **configuration))
        self.headers = {"Authorization": "Bearer " + self.case.key.key}
        self.client = stack.enter_context(httpx.Client(base_url=self.base, headers=self.headers,
                                                       trust_env=False, timeout=30))
        view = self.served.provisioning.current_view()
        self.package = view.packages["gear_maker"]

    def usage(self):
        runtime = self.case.runtime
        return runtime.usage_for(runtime.authenticate_key(self.case.key.key))["records"]

    def protocol(self, *calls):
        """Run tool calls, in order, through the official protocol client; return each tool result."""
        async def run():
            answers = []
            async with _protocol_client(self.base, _Keyed(self.case.key.key), "legacy") as client:
                for name, arguments in calls:
                    answers.append(await client.call_tool(name, arguments))
            return answers
        return asyncio.run(run())


def read_whole_package(service, request_id):
    """Follow a package read page by page; return the delivered rows, the omitted rows and every record."""
    delivered, omitted, records, offset = {}, {}, [], 0
    while offset is not None:
        (answer,) = service.protocol(("provisioning_read", {"identity": "gear_maker", "request_id": request_id,
                                                            "file_offset": offset}))
        if answer.is_error:
            return None
        record = answer.structured_content["result"]
        records.append(record)
        if record.get("record_type") != PACKAGE_READ_VERSION:
            return None
        delivered.update({row["path"]: row for row in record["files"]})
        omitted.update({row["path"]: row for row in record["omitted"]})
        offset = record["next_file_offset"]
        if len(records) > len(PACKAGE):
            return None
    return delivered, omitted, records


def package_is_delivered(service, request_id="protocol-package"):
    """The whole package reaches a protocol client as exact bytes, with a file too large for an answer named."""
    outcome = read_whole_package(service, request_id)
    if outcome is None:
        return False
    delivered, omitted, records = outcome
    expected = {path: data for path, data, _media, _role in PACKAGE}
    listed = records[0]["package"]
    document = json.dumps({"record_type": "catalogue_package/v1", "files": listed["files"]},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    exact = all(file_bytes(row) == expected[path] and hashlib.sha256(file_bytes(row)).hexdigest() == row["digest"]
                for path, row in delivered.items())
    return (exact and set(delivered) == set(expected) - {"assets/large.bin"}
            and set(omitted) == {"assets/large.bin"}
            and omitted["assets/large.bin"]["reason"] == "too_large_for_one_protocol_answer"
            and delivered["assets/logo.png"]["encoding"] == "base64"
            and delivered["SKILL.md"]["encoding"] == "utf-8"
            and len(records) >= 2
            and hashlib.sha256(document).hexdigest() == listed["package_digest"] == records[0]["digest"])


class ProtocolPackageRead(unittest.TestCase):
    """Defect 1: the protocol read of a package delivers each file's exact bytes, page by page."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.service = DeliveryService(self.stack, maximum_response_bytes=ANSWER_BYTES)

    def test_every_file_of_a_package_arrives_with_its_digest_across_pages_and_counts_once(self):
        self.assertTrue(package_is_delivered(self.service))
        self.assertEqual(self.service.usage(), 1, "every page of one request identity is one download")

    def test_one_file_is_read_by_path(self):
        (answer,) = self.service.protocol(("provisioning_read", {"identity": "gear_maker", "request_id": "by-path",
                                                                 "path": "references/b.md"}))
        self.assertFalse(answer.is_error, answer)
        record = answer.structured_content["result"]
        self.assertEqual(record["record_type"], PACKAGE_READ_VERSION)
        self.assertEqual([row["path"] for row in record["files"]], ["references/b.md"])
        self.assertEqual(file_bytes(record["files"][0]), LONG_B)
        self.assertIsNone(record["next_file_offset"])

    def test_a_file_too_large_for_an_answer_is_named_and_served_by_the_download_address(self):
        (answer,) = self.service.protocol(("provisioning_read", {"identity": "gear_maker", "request_id": "large",
                                                                 "path": "assets/large.bin"}))
        record = answer.structured_content["result"]
        self.assertEqual(record["files"], [])
        self.assertEqual([row["path"] for row in record["omitted"]], ["assets/large.bin"])
        downloaded = self.service.client.post("/api/v1/download", json=v2(
            "read", identity="gear_maker", request_id="large", path="assets/large.bin"))
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, LARGE)

    def test_a_wrong_selection_is_refused_before_it_is_counted(self):
        both, beyond, missing = self.service.protocol(
            ("provisioning_read", {"identity": "gear_maker", "request_id": "wrong", "path": "SKILL.md",
                                   "file_offset": 0}),
            ("provisioning_read", {"identity": "gear_maker", "request_id": "wrong", "file_offset": 9}),
            ("provisioning_read", {"identity": "gear_maker", "request_id": "wrong", "path": "absent.md"}))
        codes = [answer.structured_content["error"]["code"] for answer in (both, beyond, missing)]
        self.assertEqual(codes, ["package_selection_conflict", "file_offset_out_of_range", "package_file_not_found"])
        self.assertEqual(self.service.usage(), 0)

    def test_a_single_file_item_still_answers_its_body_inline(self):
        (answer,) = self.service.protocol(("provisioning_read", {"identity": "one_file", "request_id": "single"}))
        record = answer.structured_content["result"]
        self.assertEqual(record["record_type"], "provisioning_body/v3")
        self.assertEqual(record["body"], SINGLE[0][1].decode())

    def test_the_json_address_keeps_its_version_2_request_shape(self):
        refused = self.service.client.post("/api/v1/provisioning", json=v2(
            "read", identity="gear_maker", request_id="json", file_offset=0))
        self.assertEqual((refused.status_code, refused.json()["error"]["code"]), (400, "invalid_request"))

    def test_the_capabilities_name_the_protocol_package_delivery(self):
        delivery = self.service.client.get("/api/v1/capabilities").json()["result"]["delivery"]
        self.assertEqual(delivery["package_files"], "download_by_path")
        self.assertEqual(delivery["protocol_package_files"]["record_type"], PACKAGE_READ_VERSION)
        self.assertEqual(delivery["protocol_package_files"]["answer_bytes"], ANSWER_BYTES)

    def test_known_wrong_a_read_that_answers_only_the_package_document_fails(self):
        def document_only(application, authentication, fields):
            fields = {key: value for key, value in fields.items() if key not in ("file_offset", "path")}
            return application._invoke(authentication, "read", fields, tiered=True)
        with mock.patch.object(ServiceHttpApplication, "_protocol_read", document_only):
            self.assertFalse(package_is_delivered(self.service, "known-wrong"))


if __name__ == "__main__":
    unittest.main()
