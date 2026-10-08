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
  each download names, and two first downloads that race count once;
- downloads made at once on one account succeed, or answer a precise refusal that recorded nothing and says when to
  retry, never an unknown commitment, even while other work holds the store's write lock;
- an account without a plan that asks for a download is told how to take one, not to ask the operator.

Every service here is a real application on a loopback socket over a temporary SQLite store and body folder, built
from `catalogue_release_checks.Fixture`. Nothing reaches a provider or the network beyond 127.0.0.1.
"""
from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import sqlite3
import threading
import time
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
from loop_engine.core.service_runtime import usage_meter
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding
from loop_engine.core.service_runtime import storage as service_storage
from loop_engine.core.service_runtime import access as service_access
from loop_engine.core.service_runtime.records import (ServiceCommitUnknown, ServiceRuntimeConfig, ServiceRuntimeError,
                                                     TenantKeyIssue, TenantRegistration)
from loop_engine.core.service_runtime.catalogue_grants import follow_active_release
from loop_engine.core.provisioning_server import ProvisioningMeterRequest
from loop_engine.catalog.protocol import (CatalogBatchAcknowledgment, CatalogRecordPrecondition, CatalogWriteBatch,
                                         StoreBusy, StoreError)
from loop_engine.catalog.query import IntelligenceQuery
from loop_engine.loop.encapsulate import as_loop
from loop_engine.catalog.stores import sqlite_store
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
            return (request.tenant_id, request.request_id), usage_meter.digest(
                {"tenant_id": request.tenant_id, "request_id": request.request_id})
        with mock.patch.object(usage_meter, "usage_unit", per_request):
            self.assertFalse(downloads_of_one_version_count_once(service))



class HeldWriteLock:
    """Another connection holds the store's write lock for `seconds`, as another process's write would."""

    def __init__(self, database_path, seconds):
        self.database_path, self.seconds = database_path, seconds
        self.ready, self.thread = threading.Event(), None

    def __enter__(self):
        def hold():
            connection = sqlite3.connect(self.database_path, timeout=30)
            try:
                connection.execute("BEGIN IMMEDIATE")
                self.ready.set()
                time.sleep(self.seconds)
                connection.rollback()
            finally:
                connection.close()
        self.thread = threading.Thread(target=hold)
        self.thread.start()
        if not self.ready.wait(10):
            raise AssertionError("the lock holder did not start")
        return self

    def __exit__(self, *_exc):
        self.thread.join(30)


def download_waits_out_a_held_lock(service, request_id="behind-a-lock"):
    """A download while another connection holds the write lock past one busy wait: it is delivered and counted."""
    before = service.usage()
    with HeldWriteLock(service.case.config.database_path, 0.8):
        answer = service.client.post("/api/v1/download", json=v2("read", identity="one_file", request_id=request_id))
    return answer.status_code == 200 and answer.content == SINGLE[0][1] and service.usage() == before + 1


class ConcurrentDownloadsOnOneAccount(unittest.TestCase):
    """Defect 4: downloads at once on one account succeed or answer a precise, retryable refusal."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        # A short busy wait and meter time keep the held locks below short; the rules are the released ones.
        self.stack.enter_context(mock.patch.object(sqlite_store, "BUSY_TIMEOUT_SECONDS", 0.2))
        self.stack.enter_context(mock.patch.object(usage_meter, "METER_WRITE_SECONDS", 4.0))
        self.service = DeliveryService(self.stack)

    def test_the_store_edge_says_a_busy_batch_wrote_nothing(self):
        store = sqlite_store.SQLiteRecordStore(self.service.case.config.database_path)
        self.addCleanup(store.close)
        row = {"record_id": "held-lock-probe", "record_version": "1", "namespace": "probe", "source_collection": "probe",
               "artifact_kind": "probe", "intelligence_layer": "", "lifecycle": "probe", "attributes": {}, "payload": {}}
        batch = CatalogWriteBatch.from_records((row,), (CatalogRecordPrecondition("held-lock-probe", must_not_exist=True),))
        with HeldWriteLock(self.service.case.config.database_path, 0.6):
            with self.assertRaises(StoreBusy):
                store.apply_batch(batch)
        self.assertIsNone(store.get("held-lock-probe"))

    def test_a_download_behind_another_write_is_retried_and_delivered(self):
        self.assertTrue(download_waits_out_a_held_lock(self.service))

    def test_a_store_busy_past_the_meter_time_answers_a_precise_retryable_refusal(self):
        before = self.service.usage()
        with mock.patch.object(usage_meter, "METER_WRITE_SECONDS", 0.5), \
                HeldWriteLock(self.service.case.config.database_path, 2.0):
            refused = self.service.client.post("/api/v1/download", json=v2(
                "read", identity="one_file", request_id="busy"))
        self.assertEqual(refused.status_code, 503)
        self.assertEqual(refused.json()["error"]["code"], "usage_store_busy")
        self.assertEqual(refused.headers["retry-after"], "1")
        self.assertEqual(refused.json()["error"]["details"],
                         {"record_type": "service_retry_refusal/v1", "retry_after_seconds": 1, "nothing_recorded": True})
        self.assertNotIn(SINGLE[0][1], refused.content)
        self.assertEqual(self.service.usage(), before, "a refused read is not counted")
        again = self.service.client.post("/api/v1/download", json=v2("read", identity="one_file", request_id="busy"))
        self.assertEqual((again.status_code, self.service.usage()), (200, before + 1))

    def test_downloads_at_once_on_one_account_never_answer_an_unknown_commitment(self):
        stop = threading.Event()

        def contend():
            # Other work keeps taking the write lock for a moment, as other runs' downloads and the catalogue do.
            while not stop.is_set():
                with HeldWriteLock(self.service.case.config.database_path, 0.3):
                    pass
                time.sleep(0.05)
        rival = threading.Thread(target=contend)
        rival.start()

        def download(index):
            identity, path = (("gear_maker", PACKAGE[index % 5][0]) if index % 2 else ("one_file", None))
            fields = {"identity": identity, "request_id": f"parallel-{index}", **({"path": path} if path else {})}
            with httpx.Client(base_url=self.service.base, headers=self.service.headers, trust_env=False,
                              timeout=60) as own:
                answer = own.post("/api/v1/download", json=v2("read", **fields))
            code = None if answer.status_code == 200 else answer.json()["error"]["code"]
            return answer.status_code, code, answer.headers.get("retry-after")
        try:
            with ThreadPoolExecutor(8) as pool:
                outcomes = list(pool.map(download, range(8)))
        finally:
            stop.set()
            rival.join(30)
        precise = {(429, "tenant_concurrency_limit_reached"), (503, "usage_store_busy"), (503, "store_busy")}
        for status, code, retry_after in outcomes:
            self.assertTrue(status == 200 or ((status, code) in precise and retry_after == "1"), outcomes)
        self.assertTrue(any(status == 200 for status, _code, _retry in outcomes), outcomes)
        self.assertLessEqual(self.service.usage(), 2, "two item versions are at most two units")

    def test_only_the_meters_busy_refusal_promises_that_nothing_was_recorded(self):
        # A download's usage record is its only write; another request may have finished an earlier write first.
        self.assertTrue(service_http._retry_refusal("usage_store_busy")["nothing_recorded"])
        self.assertNotIn("nothing_recorded", service_http._retry_refusal("store_busy"))

    def test_known_wrong_a_busy_store_read_as_an_unknown_write_refuses_the_download(self):
        with mock.patch.object(sqlite_store, "_busy", lambda error: False):
            self.assertFalse(download_waits_out_a_held_lock(self.service, "old-classification"))

    def test_authentication_read_contention_is_not_an_invalid_key(self):
        with mock.patch.object(sqlite_store.SQLiteRecordStore, "get", side_effect=StoreBusy("busy read")):
            answer = self.service.client.post("/api/v1/download", json=v2(
                "read", identity="one_file", request_id="auth-read-busy"))
        self.assertEqual((answer.status_code, answer.json()["error"]["code"]), (503, "store_busy"))
        self.assertEqual(answer.headers.get("retry-after"), "1")
        self.assertNotIn("nothing_recorded", answer.json()["error"]["details"])
        self.assertEqual(self.service.usage(), 0)

    def test_unavailable_read_is_not_an_invalid_key(self):
        with mock.patch.object(sqlite_store.SQLiteRecordStore, "get", side_effect=StoreError("read failure")):
            answer = self.service.client.post("/api/v1/download", json=v2(
                "read", identity="one_file", request_id="auth-read-unavailable"))
        self.assertEqual((answer.status_code, answer.json()["error"]["code"]), (503, "store_unavailable"))
        self.assertEqual(self.service.usage(), 0)

    def test_busy_prewrite_meter_read_is_retryable_and_records_nothing(self):
        original = ServiceCatalogBinding.read
        def read(binding, store, kind, identity):
            if kind == service_runtime.USAGE:
                raise StoreBusy("usage lookup busy")
            return original(binding, store, kind, identity)
        with mock.patch.object(ServiceCatalogBinding, "read", read), \
                mock.patch.object(usage_meter, "METER_WRITE_SECONDS", 0.01):
            answer = self.service.client.post("/api/v1/download", json=v2(
                "read", identity="one_file", request_id="meter-read-busy"))
        self.assertEqual((answer.status_code, answer.json()["error"]["code"]), (503, "usage_store_busy"))
        self.assertTrue(answer.json()["error"]["details"]["nothing_recorded"])
        self.assertEqual(answer.headers.get("retry-after"), "1")
        self.assertEqual(self.service.usage(), 0)

    def test_busy_revalidation_after_metering_does_not_claim_nothing_recorded(self):
        original_batch = sqlite_store.SQLiteRecordStore.apply_batch
        original_revalidate = service_runtime.ServiceRuntime.revalidate
        writes = []
        def apply_batch(store, request):
            result = original_batch(store, request)
            if any(row.get("artifact_kind") == service_runtime.USAGE for row in request.records):
                writes.append(request.digest)
            return result
        def revalidate(runtime, principal):
            if writes:
                raise ServiceRuntimeError("store_busy")
            return original_revalidate(runtime, principal)
        with mock.patch.object(sqlite_store.SQLiteRecordStore, "apply_batch", apply_batch), \
                mock.patch.object(service_runtime.ServiceRuntime, "revalidate", revalidate):
            answer = self.service.client.post("/api/v1/download", json=v2(
                "read", identity="one_file", request_id="postmeter-read-busy"))
        self.assertEqual((answer.status_code, answer.json()["error"]["code"]), (503, "store_busy"))
        self.assertEqual(answer.headers.get("retry-after"), "1")
        self.assertNotIn("nothing_recorded", answer.json()["error"]["details"])
        self.assertEqual(len(writes), 1)
        self.assertEqual(self.service.usage(), 1)


class ReadContentionAndOneShotEffects(unittest.TestCase):
    """Deterministic controls for read errors and the hidden callback replay found by CI."""

    def test_sqlite_get_and_query_keep_the_busy_type(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(sqlite_store, "BUSY_TIMEOUT_SECONDS", 0.02):
            path = str(Path(folder) / "records.sqlite")
            store = sqlite_store.SQLiteRecordStore(path)
            rival = sqlite3.connect(path)
            try:
                rival.execute("BEGIN EXCLUSIVE")
                with self.assertRaises(StoreBusy):
                    store.get("not-present")
                with self.assertRaises(StoreBusy):
                    store.query(IntelligenceQuery())
            finally:
                rival.rollback()
                rival.close()
                store.close()

    def test_failed_callable_is_not_replayed_even_if_a_second_call_would_succeed(self):
        calls, failure = [], ServiceRuntimeError("store_busy")
        def once():
            calls.append(1)
            if len(calls) == 1:
                raise failure
            return "unauthorized second effect"
        result = as_loop("one bounded effect", once)
        self.assertEqual(calls, [1])
        self.assertIs(result["error"], failure)
        self.assertIsNone(result["value"])
        self.assertEqual(result["accepted"], 0)

    def test_http_loop_preserves_one_unknown_effect_without_replay(self):
        calls = []
        def uncertain():
            calls.append(1)
            raise ServiceCommitUnknown()
        with self.assertRaises(ServiceCommitUnknown):
            service_http.invoke_http_service_as_loop("download", uncertain)
        self.assertEqual(calls, [1])

    def test_tenant_resolver_keeps_its_typed_busy_refusal(self):
        from loop_engine.core.provisioning_server import ProvisioningError, ProvisioningServer, ProvisioningTenantResolver
        server = object.__new__(ProvisioningServer)
        def busy(_key):
            raise ProvisioningError("lookup busy", "store_busy")
        object.__setattr__(server, "tenant_resolver", ProvisioningTenantResolver("test_busy", busy))
        with self.assertRaises(ProvisioningError) as caught:
            server.tenant_for("test-credential")
        self.assertEqual(caught.exception.code, "store_busy")

    def test_confirmation_retries_reads_without_repeating_a_committed_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            case = Fixture(Path(folder) / "service")
            binding = ServiceCatalogBinding(case.config)
            row = binding.record("test", "one", {"record_type": "test/v1"})
            store = mock.Mock()
            store.apply_batch.side_effect = lambda batch: CatalogBatchAcknowledgment(batch.digest, True)
            store.get.side_effect = [StoreBusy("confirmation busy"), row]
            binding.commit(store, (row,), (binding.guard(None, row["record_id"]),))
            self.assertEqual(store.apply_batch.call_count, 1)
            self.assertEqual(store.get.call_count, 2)

    def test_exhausted_confirmation_stays_unknown_and_never_rewrites(self):
        with tempfile.TemporaryDirectory() as folder:
            case = Fixture(Path(folder) / "service")
            binding = ServiceCatalogBinding(case.config)
            row = binding.record("test", "one", {"record_type": "test/v1"})
            store = mock.Mock()
            store.apply_batch.side_effect = lambda batch: CatalogBatchAcknowledgment(batch.digest, True)
            store.get.side_effect = StoreBusy("confirmation still busy")
            with mock.patch.object(service_storage, "COMMIT_CONFIRMATION_SECONDS", 0), \
                    self.assertRaises(ServiceCommitUnknown):
                binding.commit(store, (row,), (binding.guard(None, row["record_id"]),))
            self.assertEqual(store.apply_batch.call_count, 1)

    def test_a_commit_is_read_back_before_another_write_of_this_process_changes_its_record(self):
        """The write queue is held through the read-back, so a busy record cannot turn a committed batch unknown.

        Known wrong (October 5 review, N1): the queue was given back before the read-back, so another commit to the
        same record in between, such as the shared Public Good window or the OAuth counter, made the read-back differ
        from the written row, and a committed write answered commit_unknown."""
        with tempfile.TemporaryDirectory() as folder:
            binding = ServiceCatalogBinding(ServiceRuntimeConfig(str(Path(folder) / "records.db"), writes_authorized=True))
            def write(value):
                with binding.store(write=True) as store:
                    previous = binding.read(store, "test", "busy")
                    row = binding.record("test", "busy", {"record_type": "test/v1", "value": value})
                    binding.commit(store, (row,), (binding.guard(previous, row["record_id"]),))
            write(0)
            main, state, outcomes = threading.current_thread(), {"armed": False, "other": None}, []
            def other_write():
                try:
                    write(2)
                    outcomes.append("committed")
                except ServiceRuntimeError as error:
                    outcomes.append(error.code)
            real_apply, real_get = sqlite_store.SQLiteRecordStore.apply_batch, sqlite_store.SQLiteRecordStore.get
            def apply_batch(store, batch):
                acknowledgment = real_apply(store, batch)
                state["armed"] = threading.current_thread() is main and state["other"] is None
                return acknowledgment
            def get(store, identity, version=None):
                if state["armed"] and threading.current_thread() is main:
                    # The read-back of the committed batch: another write of this process to the record arrives now.
                    state["armed"], state["other"] = False, threading.Thread(target=other_write)
                    state["other"].start()
                    state["other"].join(timeout=0.5)
                return real_get(store, identity, version)
            with mock.patch.object(sqlite_store.SQLiteRecordStore, "apply_batch", apply_batch), \
                    mock.patch.object(sqlite_store.SQLiteRecordStore, "get", get):
                write(1)
                state["other"].join(timeout=10)
            self.assertEqual(outcomes, ["committed"])
            with binding.store() as store:
                self.assertEqual(binding.read(store, "test", "busy")["payload"]["value"], 2)



def no_plan_is_told_how_to_subscribe(service, key):
    """A download by an account without a plan: 403 plan_required, with the pricing page and nothing counted."""
    answer = service.client.post("/api/v1/download", headers={"Authorization": "Bearer " + key}, json=v2(
        "read", identity="one_file", request_id="no-plan"))
    if answer.status_code != 403:
        return False
    error = answer.json()["error"]
    return (error["code"] == "plan_required" and "pricing page" in error["next_action"]
            and "Ask the person who runs this service" not in error["next_action"]
            and error["details"]["pricing_url"] == service.base + "/pricing"
            and error["details"]["plan"] == "Agent Feeds + Harness Files" and SINGLE[0][1] not in answer.content)


class AnAccountWithoutAPlanIsToldHowToSubscribe(unittest.TestCase):
    """Defect 6: a refused download names the plan and where to take it, not the operator."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.service = DeliveryService(self.stack)
        runtime = self.service.case.runtime
        for tenant in ("noplan", "switched_off"):
            runtime.register_tenant(TenantRegistration(tenant, "tenant:" + tenant))
        self.no_plan = runtime.issue_key(TenantKeyIssue("noplan", "no plan")).key
        self.switched_off = runtime.issue_key(TenantKeyIssue("switched_off", "downloads switched off")).key
        follow_active_release(runtime, ["noplan", "switched_off"])
        runtime.revoke_entitlement("switched_off")

    def test_a_download_names_the_plan_and_the_pricing_page(self):
        self.assertTrue(no_plan_is_told_how_to_subscribe(self.service, self.no_plan))
        found = self.service.client.post("/api/v1/retrieval", headers={"Authorization": "Bearer " + self.no_plan},
                                         json={"record_type": RETRIEVAL_REQUEST_VERSION, "query": "one file"})
        self.assertEqual(found.status_code, 200, "an account without a plan still searches")

    def test_the_protocol_read_carries_the_same_refusal(self):
        async def run():
            async with _protocol_client(self.service.base, _Keyed(self.no_plan), "legacy") as client:
                return await client.call_tool("provisioning_read", {"identity": "one_file", "request_id": "no-plan"})
        refused = asyncio.run(run())
        self.assertTrue(refused.is_error)
        self.assertEqual(refused.structured_content["error"]["code"], "plan_required")
        self.assertEqual(refused.structured_content["error"]["details"]["get_started_url"],
                         self.service.base + "/get-started")

    def test_an_account_an_operator_switched_off_keeps_the_operator_answer(self):
        answer = self.service.client.post("/api/v1/download", headers={"Authorization": "Bearer " + self.switched_off},
                                          json=v2("read", identity="one_file", request_id="switched-off"))
        self.assertEqual((answer.status_code, answer.json()["error"]["code"]), (403, "body_forbidden"))

    def test_the_founding_offer_is_named_only_while_places_remain(self):
        class Identity:
            founding_accounts = 10
            def __init__(self, open_now):
                self.open_now = open_now
            def founding_offer_open(self):
                return self.open_now
        with mock.patch.object(self.service.service, "browser_identity", Identity(True)):
            offer = self.service.service.plan_offer()
        self.assertEqual((offer["founding_offer_open"], offer["founding_places_remaining"]), (True, 10))
        with mock.patch.object(self.service.service, "browser_identity", Identity(False)):
            offer = self.service.service.plan_offer()
        self.assertEqual((offer["founding_offer_open"], offer["founding_places_remaining"]), (False, None))

    def test_known_wrong_without_the_plan_check_the_operator_wording_returns(self):
        with mock.patch.object(service_access, "holds_no_plan", lambda runtime, tenant_id: False):
            self.assertFalse(no_plan_is_told_how_to_subscribe(self.service, self.no_plan))


if __name__ == "__main__":
    unittest.main()
