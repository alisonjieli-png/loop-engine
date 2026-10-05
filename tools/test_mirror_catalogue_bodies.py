"""The body mirror copies volume bodies to the object store engine through the edge, resumably, and only when allowed.

Each test runs against `object_store_fake.ObjectStoreFake` on a loopback port, which verifies every SigV4
signature, payload hash and If-None-Match, so a copy that bypassed the edge or signed wrongly would be refused.

1. A dry run writes nothing and plans exactly the missing bodies, and with --inventory none it contacts nothing.
2. An authorized run writes each body once; a second run finds every body already present and writes none, and
   eight workers write exactly what one worker writes.
3. A run cut short by --limit resumes with --start-after and ends with the same objects as one full run.
4. A body whose bytes no longer match its digest is refused by reason and never uploaded.
5. A bundle scope copies only the files the bundle lists.
6. Operations and their list price are counted, and the report never holds a credential.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import mirror_catalogue_bodies as tool  # noqa: E402
from loop_engine.core.service_runtime.catalogue_object_store import ObjectStoreBodyStore  # noqa: E402
from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore, sha256_hex  # noqa: E402
from loop_engine.core.service_runtime.object_store_fake import ObjectStoreFake  # noqa: E402

KEY_ID, SECRET = "BALTORMIRRORKEY4Z8", "baltor-mirror-secret-v6q2w9"
KEY_REF, SECRET_REF = "env:BALTOR_MIRROR_TEST_KEY_ID", "env:BALTOR_MIRROR_TEST_SECRET"
BUCKET = "baltor-mirror-test"
BODIES = [f"body number {index}\n".encode() * (index + 1) for index in range(7)]


def resolver(reference):
    return {KEY_REF: KEY_ID, SECRET_REF: SECRET}[reference]


class Mirror(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mirror-bodies-")
        self.root = Path(self.temp.name).resolve() / "bodies"
        self.root.mkdir()
        writer = VolumeBodyStore(str(self.root), writes_authorized=True)
        self.digests = sorted(writer.put(body)["digest"] for body in BODIES)
        self.source = VolumeBodyStore(str(self.root))
        self.fake = ObjectStoreFake(access_key_id=KEY_ID, secret_access_key=SECRET, bucket=BUCKET, page_keys=3).start()

        self.opened = []

    def tearDown(self):
        for store in self.opened:
            store.close()
        self.fake.close()
        self.temp.cleanup()

    def destination(self, *, write):
        store = ObjectStoreBodyStore(self.fake.endpoint, BUCKET, access_key_id_ref=KEY_REF,
                                     secret_access_key_ref=SECRET_REF, writes_authorized=write, secret_resolver=resolver)
        self.opened.append(store)
        return store

    def stored(self):
        return sorted(key.rsplit("/", 1)[1] for key in self.fake.objects)

    def test_a_dry_run_writes_nothing_and_plans_exactly_the_missing_bodies(self):
        destination = self.destination(write=True)
        destination.put(BODIES[0])
        objects = tool.volume_objects(self.root)
        report = tool.mirror(self.source, self.destination(write=False), objects, write=False)
        self.assertEqual((report["objects"], report["already_present"], report["planned"], report["written"]),
                         (len(BODIES), 1, len(BODIES) - 1, 0))
        self.assertEqual(self.fake.count("PUT"), 1, "a dry run sent a write")
        self.assertEqual(report["a_write_run_would_send"]["class_a"], len(BODIES) - 1)
        self.assertGreaterEqual(report["operations"]["by_kind"].get("LIST", 0), 1)

    def test_an_authorized_run_writes_each_body_once_and_a_rerun_writes_none(self):
        objects = tool.volume_objects(self.root)
        first = tool.mirror(self.source, self.destination(write=True), objects, write=True)
        self.assertEqual((first["written"], first["already_present"], first["refused_by_reason"]), (len(BODIES), 0, {}))
        self.assertEqual(self.stored(), self.digests)
        reader = self.destination(write=False)
        self.assertTrue(all(reader.read(sha256_hex(body), len(body)) == body for body in BODIES))
        puts = self.fake.count("PUT")
        second = tool.mirror(self.source, self.destination(write=True), objects, write=True)
        self.assertEqual((second["written"], second["already_present"]), (0, len(BODIES)))
        self.assertEqual(self.fake.count("PUT"), puts, "a rerun wrote again although every body was listed")
        self.assertEqual(first["operations"]["by_kind"]["PUT"], len(BODIES))
        self.assertEqual(first["operations"]["by_kind"]["GET"], len(BODIES), "every write is read back once")

    def test_a_run_cut_short_resumes_after_its_last_digest(self):
        objects = tool.volume_objects(self.root)
        part = tool.mirror(self.source, self.destination(write=True), objects, write=True, limit=3)
        self.assertEqual(part["written"], 3)
        self.assertEqual(part["last_digest"], self.digests[2])
        rest = tool.mirror(self.source, self.destination(write=True), objects, write=True,
                           start_after=part["last_digest"])
        self.assertEqual((rest["objects"], rest["written"]), (len(BODIES) - 3, len(BODIES) - 3))
        self.assertEqual(self.stored(), self.digests)

    def test_parallel_workers_write_the_same_objects_as_one_worker(self):
        objects = tool.volume_objects(self.root)
        report = tool.mirror(self.source, self.destination(write=True), objects, write=True, workers=8)
        self.assertEqual((report["written"], report["workers"], report["refused_by_reason"]), (len(BODIES), 8, {}))
        self.assertEqual(self.stored(), self.digests)
        self.assertEqual(report["last_digest"], self.digests[-1])
        with self.assertRaises(ValueError):
            tool.mirror(self.source, self.destination(write=True), objects, write=True, workers=0)

    def test_a_body_that_no_longer_matches_its_digest_is_refused_and_never_uploaded(self):
        changed = self.root / VolumeBodyStore.object_key(self.digests[0])
        os.chmod(changed, 0o644)
        original = changed.read_bytes()
        changed.write_bytes(bytes(reversed(original)))
        report = tool.mirror(self.source, self.destination(write=True), tool.volume_objects(self.root), write=True)
        self.assertEqual(report["refused_by_reason"], {"body_digest_mismatch": 1})
        self.assertNotIn(self.digests[0], self.stored())
        self.assertEqual(report["written"], len(BODIES) - 1)

    def test_a_bundle_scope_copies_only_the_files_the_bundle_lists(self):
        bundle = Path(self.temp.name) / "bundle"
        bundle.mkdir()
        listed = [self.digests[1], self.digests[4]]
        sizes = {sha256_hex(body): len(body) for body in BODIES}
        lines = [{"package": {"files": [{"digest": digest, "size_bytes": sizes[digest]}]}} for digest in listed]
        (bundle / "items.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines))
        report = tool.mirror(self.source, self.destination(write=True), tool.bundle_objects(bundle), write=True)
        self.assertEqual(report["written"], 2)
        self.assertEqual(self.stored(), sorted(listed))

    def test_the_command_is_a_dry_run_without_authorization_and_contacts_nothing_without_an_inventory(self):
        record = {"record_type": "catalogue_body_store_engine/v1", "engine": "r2_object_storage",
                  "endpoint": "https://" + "a1b2c3d4" * 4 + ".r2.cloudflarestorage.com", "bucket": "baltor-catalogue-bodies",
                  "access_key_id_ref": "env:BALTOR_R2_ACCESS_KEY_ID", "secret_access_key_ref": "env:BALTOR_R2_SECRET_ACCESS_KEY"}
        path = Path(self.temp.name) / "record.json"
        path.write_text(json.dumps(record))

        def no_network(*_arguments, **_keywords):
            raise AssertionError("the dry run contacted the network")
        output = io.StringIO()
        with mock.patch.object(socket, "getaddrinfo", no_network), mock.patch.object(socket.socket, "connect", no_network), \
                redirect_stdout(output):
            status = tool.main(["--source-root", str(self.root), "--body-store-record", str(path), "--inventory", "none"])
        report = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual((report["mode"], report["planned"], report["written"]), ("dry_run", len(BODIES), 0))
        self.assertEqual(report["record_type"], "catalogue_body_mirror_report/v1")
        self.assertEqual(report["a_write_run_would_send"], {"class_a": len(BODIES), "class_b": len(BODIES),
                                                            "list_price_usd": round(len(BODIES) * 4.86 / 1_000_000, 6)})
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                tool.main(["--source-root", str(self.root), "--body-store-record", str(path), "--inventory", "none",
                           "--authorize-object-store-writes"])
        volume = dict(record, engine="service_volume_files")
        for key in ("endpoint", "bucket", "access_key_id_ref", "secret_access_key_ref"):
            volume.pop(key)
        path.write_text(json.dumps(volume))
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                tool.main(["--source-root", str(self.root), "--body-store-record", str(path)])

    def test_the_report_counts_and_prices_operations_and_holds_no_credential(self):
        objects = tool.volume_objects(self.root)
        report = tool.mirror(self.source, self.destination(write=True), objects, write=True)
        text = json.dumps(report)
        self.assertNotIn(KEY_ID, text)
        self.assertNotIn(SECRET, text)
        operations = report["operations"]
        self.assertEqual(operations["class_a"], operations["by_kind"]["PUT"] + operations["by_kind"]["LIST"])
        self.assertEqual(operations["class_b"], operations["by_kind"]["GET"])
        expected = round(operations["class_a"] * 4.50 / 1e6 + operations["class_b"] * 0.36 / 1e6, 6)
        self.assertEqual(report["list_price_usd"]["total"], expected)
        self.assertTrue(report["list_price_usd"]["inside_the_monthly_free_operations"])
        self.assertEqual(report["bytes"], sum(len(body) for body in BODIES))


if __name__ == "__main__":
    unittest.main()
