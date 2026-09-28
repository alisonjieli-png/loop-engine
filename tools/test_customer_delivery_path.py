"""The customer delivery path, checked through the real service on loopback with its own fixtures.

Kind: continuous integration check.

On September 27, 2026 a customer run through the documented setup found that customers could not use the library
(handoff u of the consolidation, and docs/research/USER-JOURNEY-AND-3D-WITH-WITHOUT-2026-09-27.md). Each class here
holds one repair to the behaviour that run saw, and each has a known-wrong control that puts the old behaviour back
and must fail:

- the protocol tool `provisioning_read` delivers a package's files, not only the package document that lists them;
- search, listing and manifests show every item with the effects its step would still have to declare, and a read
  of an item whose effects the step did not declare is refused, naming the header and the effects to add;
- an account's repeated downloads of one item version count once in a calendar month, whatever request identity
  each download names, and two first downloads that race count once.

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
from loop_engine.core.service_runtime import http as service_http
from loop_engine.core.service_runtime.http import (PACKAGE_READ_VERSION, RETRIEVAL_REQUEST_VERSION,
                                                   STEP_EFFECTS_REFUSAL_VERSION, TIERED_PROVISIONING_REQUEST_VERSION,
                                                   ServiceHttpApplication)
from loop_engine.core.service_runtime import runtime as service_runtime
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding
from loop_engine.core.provisioning_server import ProvisioningMeterRequest
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
#: A skill that writes files and runs a script, so a step must declare both before it may read it.
WRITER = (("SKILL.md", b"# Part writer\nWrites the part file with scripts/write.sh.\n", "text/markdown",
           "skill_definition"),
          ("scripts/write.sh", b"#!/bin/sh\nprintf part > part.stl\n", "text/x-shellscript", "skill_script"))
WRITER_EFFECTS = ("reads_fs", "writes_fs", "spawns_process")
#: What the quickstarts now tell a coding harness to declare.
DECLARED = "reads_fs, writes_fs, spawns_process, network"
#: A protocol answer limit small enough that the package needs two pages and one file cannot fit any answer.
ANSWER_BYTES = 40_000


def v2(operation, **fields):
    return {"record_type": TIERED_PROVISIONING_REQUEST_VERSION, "operation": operation, **fields}


class _Keyed:
    """What the protocol client helper reads from a fixture: the headers of one account, and any the client adds."""

    def __init__(self, key, **extra):
        self.key, self.extra = key, extra

    def headers(self, _tenant="alpha"):
        return {"Authorization": "Bearer " + self.key, **self.extra}


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
                            "one_file": tuple(row[1] for row in SINGLE),
                            "part_writer": tuple(row[1] for row in WRITER)}
        self.case.publish([bundle_line("gear_maker", PACKAGE, effects=("reads_fs",)),
                           bundle_line("one_file", SINGLE, effects=("reads_fs",)),
                           bundle_line("part_writer", WRITER, effects=WRITER_EFFECTS)])
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

    def protocol(self, *calls, **headers):
        """Run tool calls, in order, through the official protocol client; return each tool result."""
        async def run():
            answers = []
            async with _protocol_client(self.base, _Keyed(self.case.key.key, **headers), "legacy") as client:
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
        capabilities = self.service.client.get("/api/v1/capabilities").json()["result"]
        delivery = capabilities["delivery"]
        self.assertEqual(delivery["package_files"], "download_by_path")
        self.assertEqual(delivery["protocol_package_files"], "provisioning_read_by_page_or_path")
        self.assertEqual(delivery["protocol_package_record_type"], PACKAGE_READ_VERSION)
        self.assertEqual(capabilities["limits"]["response_bytes"], ANSWER_BYTES)

    def test_known_wrong_a_read_that_answers_only_the_package_document_fails(self):
        def document_only(application, authentication, fields):
            fields = {key: value for key, value in fields.items() if key not in ("file_offset", "path")}
            return application._invoke(authentication, "read", fields, tiered=True)
        with mock.patch.object(ServiceHttpApplication, "_protocol_read", document_only):
            self.assertFalse(package_is_delivered(self.service, "known-wrong"))



def search(service, query, **fields):
    headers = fields.pop("headers", {})
    answer = service.client.post("/api/v1/retrieval", headers=headers, json={
        "record_type": RETRIEVAL_REQUEST_VERSION, "query": query, **fields})
    return answer.json()["result"]


def writer_is_shown_marked(service):
    """A search with no effects stated shows the writer, marked with the two effects its step still has to declare."""
    found = search(service, "part writer")
    marks = {hit["reference"]["identity"]: hit.get("effects_to_declare") for hit in found["hits"]}
    return marks.get("part_writer") == ["writes_fs", "spawns_process"] and found.get("step_effects") == ["reads_fs"]


class StepEffectsAreMarkedAndCheckedAtRead(unittest.TestCase):
    """Defect 2: an item that declares effects is shown with them; only a read by a step without them is refused."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.service = DeliveryService(self.stack)
        self.writer_digest = self.service.served.provisioning.current_view().catalogue.items["part_writer"].digest

    def read(self, **headers):
        return self.service.client.post("/api/v1/download", headers=headers, json=v2(
            "read", identity="part_writer", request_id="writer-read", expected_digest=self.writer_digest,
            path="scripts/write.sh"))

    def test_search_without_the_header_shows_every_item_marked(self):
        self.assertTrue(writer_is_shown_marked(self.service))
        found = search(self.service, "gear maker")
        gear = next(hit for hit in found["hits"] if hit["reference"]["identity"] == "gear_maker")
        self.assertEqual(gear["effects_to_declare"], [])
        self.assertEqual(found["step_effects_header"], "Baltor-Step-Effects")

    def test_listing_and_manifest_show_the_item_and_its_marks(self):
        listed = self.service.client.post("/api/v1/provisioning", json=v2("list")).json()["result"]
        rows = {row["identity"]: row["effects_to_declare"] for row in listed["items"]}
        self.assertEqual(rows["part_writer"], ["writes_fs", "spawns_process"])
        self.assertNotIn("part_writer", {row["identity"] for row in listed["withheld"]})
        manifest = self.service.client.post("/api/v1/provisioning", json=v2(
            "manifest", identity="part_writer", expected_digest=self.writer_digest))
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.json()["result"]["effects_to_declare"], ["writes_fs", "spawns_process"])

    def test_a_read_by_a_step_without_the_effects_is_refused_with_the_header_and_nothing_is_counted(self):
        refused = self.read()
        self.assertEqual(refused.status_code, 403)
        error = refused.json()["error"]
        self.assertEqual(error["code"], "step_effects_required")
        self.assertIn("Baltor-Step-Effects", error["next_action"])
        self.assertEqual(error["details"]["record_type"], STEP_EFFECTS_REFUSAL_VERSION)
        self.assertEqual(error["details"]["effects_to_declare"], ["writes_fs", "spawns_process"])
        self.assertEqual(error["details"]["header"], "Baltor-Step-Effects")
        self.assertEqual(error["details"]["header_value"], "reads_fs, writes_fs, spawns_process")
        self.assertNotIn(b"printf part", refused.content)
        partial = self.read(**{"Baltor-Step-Effects": "reads_fs, writes_fs"})
        self.assertEqual(partial.json()["error"]["details"]["effects_to_declare"], ["spawns_process"])
        self.assertEqual(self.service.usage(), 0)

    def test_a_step_that_declares_the_effects_reads_the_exact_bytes(self):
        allowed = self.read(**{"Baltor-Step-Effects": DECLARED})
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.content, WRITER[1][1])
        self.assertEqual(self.service.usage(), 1)

    def test_an_explicit_authority_effects_field_still_narrows_what_is_shown(self):
        narrowed = search(self.service, "part writer", authority_effects=["reads_fs"])
        self.assertNotIn("part_writer", {hit["reference"]["identity"] for hit in narrowed["hits"]})
        refused = self.service.client.post("/api/v1/download", json=v2(
            "read", identity="part_writer", request_id="field-read", authority_effects=["reads_fs"]))
        self.assertEqual(refused.json()["error"]["code"], "step_effects_required")

    def test_the_protocol_tools_show_the_marks_and_refuse_with_the_details(self):
        found, refused = self.service.protocol(
            ("intelligence_search", {"query": "part writer"}),
            ("provisioning_read", {"identity": "part_writer", "request_id": "protocol-writer"}))
        hits = {hit["reference"]["identity"]: hit for hit in found.structured_content["result"]["hits"]}
        self.assertEqual(hits["part_writer"]["effects_to_declare"], ["writes_fs", "spawns_process"])
        self.assertTrue(refused.is_error)
        self.assertEqual(refused.structured_content["error"]["code"], "step_effects_required")
        self.assertEqual(refused.structured_content["error"]["details"]["effects_to_declare"],
                         ["writes_fs", "spawns_process"])
        (allowed,) = self.service.protocol(("provisioning_read", {"identity": "part_writer",
                                                                  "request_id": "protocol-writer"}),
                                           **{"Baltor-Step-Effects": DECLARED})
        self.assertFalse(allowed.is_error, allowed)
        files = {row["path"]: file_bytes(row) for row in allowed.structured_content["result"]["files"]}
        self.assertEqual(files, {path: data for path, data, _media, _role in WRITER})
        self.assertEqual(self.service.usage(), 1)

    def test_known_wrong_the_old_header_filter_hides_the_writer(self):
        def header_filter(fields, header_effects):
            chosen = tuple(fields.get("authority_effects") or header_effects or service_http.DEFAULT_STEP_EFFECTS)
            return {**fields, "authority_effects": list(chosen)}, chosen
        with mock.patch.object(service_http, "effect_selection", header_filter):
            self.assertFalse(writer_is_shown_marked(self.service))

    def test_known_wrong_without_the_step_check_the_refusal_does_not_name_the_effects(self):
        with mock.patch.object(service_http, "effects_to_declare", lambda declared, step: []):
            refused = self.read()
        self.assertNotEqual(refused.json()["error"]["code"], "step_effects_required")
        self.assertNotIn(b"printf part", refused.content, "the provisioning boundary still withholds the body")



#: Two moments in consecutive calendar months, in UTC: September 30 and October 1, 2026.
SEPTEMBER, OCTOBER = 1_790_726_400, 1_790_812_800


def downloads_of_one_version_count_once(service):
    """Three downloads of one item version under three request identities, and a protocol read: one unit."""
    before = service.usage()
    for request_id in ("first", "second", "third"):
        answer = service.client.post("/api/v1/download", json=v2("read", identity="one_file", request_id=request_id))
        if answer.status_code != 200 or answer.content != SINGLE[0][1]:
            return False
    (read,) = service.protocol(("provisioning_read", {"identity": "one_file", "request_id": "fourth"}))
    return not read.is_error and service.usage() - before == 1


class MeteringCountsEachItemVersionOncePerMonth(unittest.TestCase):
    """Defect 3: the same account downloading the same item version counts once in a billing month."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)

    def test_repeat_downloads_with_new_request_identities_count_once(self):
        service = DeliveryService(self.stack)
        self.assertTrue(downloads_of_one_version_count_once(service))
        usage = service.case.runtime.usage_for(service.case.runtime.authenticate_key(service.case.key.key))
        self.assertEqual(usage["unit_rule"], "one_per_item_version_per_calendar_month_utc")
        self.assertEqual(usage["current_period_records"], 1)
        # Another item is another unit.
        service.client.post("/api/v1/download", json=v2("read", identity="gear_maker", request_id="gear"))
        self.assertEqual(service.usage(), 2)

    def test_a_new_month_and_a_new_version_are_new_units(self):
        folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="metering-months-")))
        fixture = HttpDomainFixture(folder)
        moment = [SEPTEMBER]
        runtime = service_runtime.ServiceRuntime(fixture.runtime.config, clock=lambda: moment[0])
        # The fixture's grant runs for an hour of real time; this account's plan must cover both months.
        runtime.set_operator_entitlement("alpha", valid_until=OCTOBER + 30 * 86400, evidence_ref="metering-months")
        principal = runtime.authenticate_key(fixture.keys["alpha"].key)
        alpha = fixture.bindings["skill.alpha"]
        first = runtime.record_usage(ProvisioningMeterRequest("alpha", "one", alpha), principal)
        again = runtime.record_usage(ProvisioningMeterRequest("alpha", "two", alpha), principal)
        self.assertTrue(first.committed and again.committed)
        self.assertEqual(first.acknowledgment_ref, again.acknowledgment_ref)
        changed = fixture.bindings["skill.large"]
        runtime.record_usage(ProvisioningMeterRequest("alpha", "three", changed), principal)
        moment[0] = OCTOBER
        runtime.record_usage(ProvisioningMeterRequest("alpha", "four", alpha), principal)
        usage = runtime.usage_for(principal)
        self.assertEqual(usage["records"], 3, "September's two versions and October's first read")
        self.assertEqual((usage["current_period"], usage["current_period_records"]), ("2026-10", 1))

    def test_two_first_downloads_that_race_count_once(self):
        folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="metering-race-")))
        fixture = HttpDomainFixture(folder)
        runtime = fixture.runtime
        principal = runtime.authenticate_key(fixture.keys["alpha"].key)
        alpha = fixture.bindings["skill.alpha"]
        original, raced = ServiceCatalogBinding.commit, []

        def commit_after_a_rival(binding, store, records, guards, removals=()):
            # The first usage write waits until a rival read of the same unit has committed through its own
            # connection, as two harness runs downloading one item at once would.
            if not raced and records and records[0]["artifact_kind"] == service_runtime.USAGE:
                raced.append(None)
                raced[0] = runtime.record_usage(ProvisioningMeterRequest("alpha", "rival", alpha), principal)
            return original(binding, store, records, guards, removals)
        with mock.patch.object(ServiceCatalogBinding, "commit", commit_after_a_rival):
            first = runtime.record_usage(ProvisioningMeterRequest("alpha", "first", alpha), principal)
        self.assertTrue(raced and raced[0].committed and first.committed)
        self.assertEqual(first.acknowledgment_ref, raced[0].acknowledgment_ref)
        self.assertEqual(runtime.usage_for(principal)["records"], 1)

    def test_known_wrong_a_unit_per_request_identity_counts_every_download(self):
        service = DeliveryService(self.stack)

        def per_request(request, period):
            return (request.tenant_id, request.request_id), service_runtime.digest(
                {"tenant_id": request.tenant_id, "request_id": request.request_id})
        with mock.patch.object(service_runtime, "usage_unit", per_request):
            self.assertFalse(downloads_of_one_version_count_once(service))


if __name__ == "__main__":
    unittest.main()
