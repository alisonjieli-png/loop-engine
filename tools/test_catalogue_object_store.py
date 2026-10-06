"""The catalogue body store kit, runnable on its own, and optionally against a real S3-compatible test bucket.

`core/service_runtime/catalogue_body_store_checks.py` is the conformance kit of the `catalogue_body_store`
slot: the volume engine and the R2 engine (`catalogue_object_store.py`) against the same edge checks, the
R2 engine against a loopback fake that verifies SigV4, and the factory table. This wrapper runs it alone and
prints the pass count, and checks that every check name is spelled out in the kit's source, which is how the
slot catalogue's `existing_checks` entries are resolved.

With these variables set, it also runs the edge checks against a real store, such as an S3-compatible server
on 127.0.0.1 or, on the day R2 is enabled, a dedicated R2 test bucket (never the bucket that serves
customers, because the checks write other bytes under a digest's name on purpose):

    LE_OBJECT_STORE_KIT_ENDPOINT=https://<account id>.r2.cloudflarestorage.com
    LE_OBJECT_STORE_KIT_BUCKET=baltor-catalogue-bodies-kit
    LE_OBJECT_STORE_KIT_ACCESS_KEY_ID_REF=env:BALTOR_R2_KIT_ACCESS_KEY_ID
    LE_OBJECT_STORE_KIT_SECRET_ACCESS_KEY_REF=env:BALTOR_R2_KIT_SECRET_ACCESS_KEY
    LE_OBJECT_STORE_KIT_REGION=auto            (optional)
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.service_runtime import catalogue_body_store_checks as kit  # noqa: E402
from loop_engine.core.service_runtime import catalogue_object_store as objects  # noqa: E402
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

EXTERNAL = ("LE_OBJECT_STORE_KIT_ENDPOINT", "LE_OBJECT_STORE_KIT_BUCKET", "LE_OBJECT_STORE_KIT_ACCESS_KEY_ID_REF",
            "LE_OBJECT_STORE_KIT_SECRET_ACCESS_KEY_REF")


class BodyStoreKit(unittest.TestCase):

    def test_every_engine_passes_the_kit(self):
        report = kit.run_checks()
        failed = [row["test"] for row in report["tests"] if not row["passed"]]
        print(f"\ncatalogue body store kit: {report['passed']} of {report['total']} checks passed", file=sys.stderr)
        self.assertEqual(failed, [])
        self.assertGreaterEqual(report["total"], 34)

    def test_every_check_name_is_spelled_out_in_the_kit(self):
        source = Path(kit.__file__).read_text(encoding="utf-8")
        names = [row["test"] for row in kit.run_checks()["tests"]]
        self.assertEqual([name for name in names if f'"{name}"' not in source], [])
        self.assertEqual(len(names), len(set(names)), "a check name is used twice")

    @unittest.skipUnless(all(os.environ.get(name) for name in EXTERNAL), "no external S3-compatible test bucket named")
    def test_the_edge_checks_pass_against_the_named_external_store(self):
        rows = []
        kit.run_external_checks(lambda name, passed: rows.append((name, bool(passed))),
                                endpoint=os.environ["LE_OBJECT_STORE_KIT_ENDPOINT"],
                                bucket=os.environ["LE_OBJECT_STORE_KIT_BUCKET"],
                                access_key_id_ref=os.environ["LE_OBJECT_STORE_KIT_ACCESS_KEY_ID_REF"],
                                secret_access_key_ref=os.environ["LE_OBJECT_STORE_KIT_SECRET_ACCESS_KEY_REF"],
                                region=os.environ.get("LE_OBJECT_STORE_KIT_REGION", "auto"))
        print(f"\nexternal store: {sum(passed for _name, passed in rows)} of {len(rows)} checks passed", file=sys.stderr)
        self.assertEqual([name for name, passed in rows if not passed], [])


class ObjectListingGuards(unittest.TestCase):
    def test_non_listing_missing_flag_entities_negative_sizes_and_duplicate_keys_refuse(self):
        cases = [b"<Other/>", b"<ListBucketResult/>",
                 b'<!DOCTYPE x [<!ENTITY sample "data">]><ListBucketResult><IsTruncated>false</IsTruncated></ListBucketResult>',
                 b"<ListBucketResult><IsTruncated>false</IsTruncated><Contents><Key>x</Key><Size>-1</Size></Contents></ListBucketResult>",
                 b"<ListBucketResult><IsTruncated>false</IsTruncated>" +
                 b"<Contents><Key>x</Key><Size>1</Size></Contents>" * 2 + b"</ListBucketResult>"]
        for document in cases:
            with self.subTest(document=document), self.assertRaises(ServiceRuntimeError) as error:
                objects._listing(document)
            self.assertEqual(error.exception.code, "body_unreadable")

    def test_repeated_cursor_refuses_instead_of_repeating_provider_requests(self):
        body = b"<ListBucketResult><IsTruncated>true</IsTruncated><NextContinuationToken>same</NextContinuationToken></ListBucketResult>"
        store = objects.ObjectStoreBodyStore("http://127.0.0.1:1", "fixture-bucket",
            access_key_id_ref="env:FIXTURE_ID", secret_access_key_ref="env:FIXTURE_SECRET")
        with mock.patch.object(store, "_request", return_value=(200, body)) as request:
            with self.assertRaises(ServiceRuntimeError) as error:
                list(store.stored_objects())
            self.assertEqual(request.call_count, 2)
        self.assertEqual(error.exception.code, "body_unreadable")


if __name__ == "__main__":
    unittest.main()
