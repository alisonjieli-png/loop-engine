"""Guarded Public Good selection and public metadata; no provider or production writes."""
from dataclasses import asdict, replace
import hashlib
import json
import unittest

import test_public_good as fixtures
from loop_engine.core.service_runtime import public_good_page
from loop_engine.core.service_runtime.public_good_operator import apply_policy, REQUEST_VERSION
from loop_engine.core.service_runtime.records import ServiceRuntimeError


class PublicGoodOperatorTests(unittest.TestCase):
    setUp = fixtures.PublicGoodTests.setUp

    def raw(self, **changes):
        snapshot = self.service.snapshot(self.view)
        return json.dumps({"record_type":REQUEST_VERSION, "expected_release":"synthetic-release",
            "expected_version":snapshot.version or None, "grants":[asdict(self.grant)],
            "limits":asdict(snapshot.limits), **changes}).encode()

    def test_plan_is_read_only_and_apply_binds_exact_file_and_policy(self):
        view = replace(self.view, release_id="synthetic-release")
        raw = self.raw()
        before = self.service.snapshot(view).version
        plan = apply_policy(self.runtime, view, raw)
        self.assertFalse(plan["applied"])
        self.assertEqual(self.service.snapshot(view).version, before)
        with self.assertRaises(ServiceRuntimeError) as refused:
            apply_policy(self.runtime, view, raw, apply=True, expected_digest="f"*64)
        self.assertEqual(refused.exception.code, "public_good_policy_digest_mismatch")
        answer = apply_policy(self.runtime, view, raw, apply=True, expected_digest=hashlib.sha256(raw).hexdigest())
        self.assertTrue(answer["applied"])
        self.assertNotEqual(answer["policy_version"], before)
        with self.assertRaises(ServiceRuntimeError) as refused:
            apply_policy(self.runtime, view, raw, apply=True, expected_digest=plan["file_digest"])
        self.assertEqual(refused.exception.code, "public_good_policy_changed")

    def test_wrong_release_shape_or_duplicate_refuses_before_writes(self):
        view = replace(self.view, release_id="synthetic-release")
        before = self.service.snapshot(view).version
        for raw in (self.raw(expected_release="different"), self.raw(extra="not-allowed"),
                    b'{"record_type":"one","record_type":"two"}', b'null', b'['):
            with self.subTest(raw=raw[:80]), self.assertRaises(ServiceRuntimeError):
                apply_policy(self.runtime, view, raw, apply=True, expected_digest=hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.service.snapshot(view).version, before)

    def test_collection_is_body_free_explicit_and_filters_all_goals(self):
        snapshot = self.service.snapshot(self.view)
        record = public_good_page.collection(self.view, snapshot)
        self.assertEqual(len(record["goals"]), 17)
        self.assertTrue(record["authentication_required"])
        self.assertFalse(record["subscription_required"])
        self.assertEqual(record["packages"], 1)
        self.assertEqual(record["distinct_useful_files"], 0)
        self.assertEqual(public_good_page.collection(self.view, snapshot, goal="8")["matches"], 1)
        self.assertEqual(public_good_page.collection(self.view, snapshot, goal="3")["matches"], 0)
        self.assertEqual(public_good_page.collection(self.view, snapshot, query="worker support")["matches"], 1)
        self.assertFalse(self.reads)
        self.assertNotIn("body", record["items"][0])

    def test_invalid_filter_and_nonexistent_useful_path_refuse(self):
        snapshot = self.service.snapshot(self.view)
        for changes in ({"goal":"18"},{"page":True},{"query":"x\n"},{"page_size":1001}):
            with self.subTest(changes=changes), self.assertRaises(ServiceRuntimeError):
                public_good_page.collection(self.view, snapshot, **changes)
        grant = replace(self.grant, useful_paths=("missing.py",))
        with self.assertRaises(ServiceRuntimeError):
            self.service.configure(self.view, (grant,), expected_version=snapshot.version)


if __name__ == "__main__":
    unittest.main()
