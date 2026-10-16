"""Administrator key rotation: no gap, no printed secret, and every failure leaves a working saved key.

The host step runs against a real service store here, and the session check authenticates through the same
runtime, so a revoked or unconfirmed key is refused the way the deployed service refuses it.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loop_engine.core.service_runtime.records import (  # noqa: E402
    ACCESS_MANAGE_SCOPE, ServiceRuntimeError, TenantKeyIssue, TenantRegistration)
from loop_engine.core.service_runtime.runtime import ServiceRuntime, ServiceRuntimeConfig  # noqa: E402

import rotate_service_administrator as rotation  # noqa: E402
import service_admin_rotation_host as host_step  # noqa: E402

ORIGIN = "https://service.example"
ADMIN = "baltor-admin"


class Item:
    def __init__(self, value):
        self.value = value
        self.attributes = {"application": "loop-engine", "service": "service.example", "account": ADMIN,
                           "purpose": "service-access"}
        self.fail_store = False

    def get_secret(self):
        return self.value.encode()

    def set_secret(self, value):
        if self.fail_store:
            raise RuntimeError("keyring write failed")
        self.value = value.decode()

    def get_attributes(self):
        return dict(self.attributes)

    def set_attributes(self, attributes):
        self.attributes = dict(attributes)


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class Store(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="admin-rotation-")
        self.addCleanup(folder.cleanup)
        self.config = ServiceRuntimeConfig(str(Path(folder.name) / "service.sqlite"), writes_authorized=True)
        self.runtime = ServiceRuntime(self.config)
        self.runtime.register_tenant(TenantRegistration(ADMIN, ADMIN + ":private", (ACCESS_MANAGE_SCOPE,)))
        self.old = self.runtime.issue_key(TenantKeyIssue(ADMIN, "Owner administrator", int(time.time()) + 3600,
                                                         (ACCESS_MANAGE_SCOPE,)))
        patched = mock.patch.object(host_step, "_host", lambda path, needs_bodies=False: (None, None, self.config))
        patched.start()
        self.addCleanup(patched.stop)
        self.calls = []
        self.refuse_values = set()

    def host_run(self, *arguments):
        self.calls.append(arguments)
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            try:
                status = host_step.main(list(arguments))
            except ServiceRuntimeError as error:
                raise RuntimeError("host step refused: " + error.code) from None
        if status != 0:
            raise RuntimeError("host step failed")
        return json.loads(out.getvalue())

    def host(self):
        test = self

        class Host:
            uploaded = 0

            def upload_step(self):
                Host.uploaded += 1

            def run(self, *arguments):
                return test.host_run(*arguments)
        return Host()

    def opener(self, request, timeout=None):
        value = request.get_header("Authorization").removeprefix("Bearer ")
        try:
            if value in self.refuse_values:
                raise ServiceRuntimeError("unauthorized")
            principal = self.runtime.authenticate_key(value)
        except ServiceRuntimeError:
            raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b"{}")) from None
        body = {"result": {"record_type": "service_session/v1", "principal": {
            "tenant_id": principal.tenant_id, "key_id": principal.key_id, "scopes": list(principal.scopes)}}}
        return Response(json.dumps(body).encode())

    def enabled(self):
        return {row["key_id"] for row in host_step.keys(self.runtime, ADMIN) if row["enabled"]}

    def rotate(self, item, confirm=True, days=90):
        return rotation.rotate(origin=ORIGIN, administrator=ADMIN, days=days, confirm=confirm, item=item,
                               host=self.host(), opener=self.opener)


class RotationTests(Store):
    def test_rotation_saves_a_working_key_and_then_revokes_the_old_one(self):
        item = Item(self.old.key)
        report = self.rotate(item)
        self.assertNotEqual(item.value, self.old.key)
        self.assertEqual(self.runtime.authenticate_key(item.value).key_id, report["key_id"])
        with self.assertRaises(ServiceRuntimeError):
            self.runtime.authenticate_key(self.old.key)
        self.assertEqual(self.enabled(), {report["key_id"]})
        self.assertTrue(report["replaced_key_revoked"])
        self.assertEqual(item.attributes["key_id"], report["key_id"])
        self.assertEqual(item.attributes["expires_at"], str(report["expires_at"]))
        self.assertGreaterEqual(report["expires_at"] - report["issued_at"], 90 * 86400)
        serialized = json.dumps(report)
        self.assertNotIn(item.value, serialized)
        self.assertNotIn(self.old.key, serialized)

    def test_a_dry_run_reads_and_changes_nothing(self):
        item = Item(self.old.key)
        report = self.rotate(item, confirm=False)
        self.assertTrue(report["dry_run"])
        self.assertEqual(item.value, self.old.key)
        self.assertEqual(self.enabled(), {self.old.key_id})
        self.assertEqual([call[0] for call in self.calls], ["list"])

    def test_known_wrong_a_new_key_the_service_refuses_puts_the_old_value_back_and_is_revoked(self):
        item = Item(self.old.key)
        original = self.runtime.issue_key

        def issue_and_refuse(request):
            issued = original(request)
            self.refuse_values.add(issued.key)
            return issued
        with mock.patch.object(ServiceRuntime, "issue_key", lambda runtime, request: issue_and_refuse(request)):
            with self.assertRaises(rotation.RotationError) as caught:
                self.rotate(item)
        self.assertEqual(caught.exception.code, "new_key_not_confirmed")
        self.assertEqual(item.value, self.old.key)
        self.assertNotIn("key_id", item.attributes)
        self.assertEqual(self.enabled(), {self.old.key_id})
        self.assertEqual(self.runtime.authenticate_key(self.old.key).key_id, self.old.key_id)

    def test_known_wrong_a_keyring_that_cannot_store_keeps_the_old_key_working(self):
        item = Item(self.old.key)
        item.fail_store = True
        with self.assertRaises(rotation.RotationError) as caught:
            self.rotate(item)
        self.assertEqual(caught.exception.code, "new_key_not_confirmed")
        self.assertEqual(self.enabled(), {self.old.key_id})
        self.assertEqual(self.runtime.authenticate_key(item.value).key_id, self.old.key_id)

    def test_known_wrong_a_keyring_stuck_on_the_new_value_never_revokes_the_only_saved_key(self):
        item = Item(self.old.key)
        writes = []

        def stuck_secret(value):
            if writes:
                raise RuntimeError("keyring write failed")
            writes.append(value)
            item.value = value.decode()

        def failing_attributes(_attributes):
            raise RuntimeError("keyring attribute write failed")
        item.set_secret, item.set_attributes = stuck_secret, failing_attributes
        with self.assertRaises(rotation.RotationError) as caught:
            self.rotate(item)
        self.assertEqual((caught.exception.code, caught.exception.status),
                         ("keyring_state_unknown", rotation.EXIT_UNKNOWN))
        self.assertNotEqual(item.value, self.old.key)
        self.assertEqual(len(self.enabled()), 2)
        self.assertIsNotNone(self.runtime.authenticate_key(item.value))

    def test_a_saved_key_the_service_refuses_has_its_own_status_and_touches_no_host(self):
        item = Item(self.old.key)
        self.runtime.revoke_key(ADMIN, self.old.key_id)
        with self.assertRaises(rotation.RotationError) as caught:
            self.rotate(item)
        self.assertEqual((caught.exception.code, caught.exception.status),
                         ("saved_key_refused", rotation.EXIT_SAVED_KEY_REFUSED))
        self.assertEqual(self.calls, [])

    def test_a_key_without_access_management_is_refused_before_any_change(self):
        self.runtime.register_tenant(TenantRegistration("pilot-owner", "pilot-owner:private"))
        other = self.runtime.issue_key(TenantKeyIssue("pilot-owner", "diagnostic"))
        with self.assertRaises(rotation.RotationError) as caught:
            rotation.rotate(origin=ORIGIN, administrator="pilot-owner", days=90, confirm=True, item=Item(other.key),
                            host=self.host(), opener=self.opener)
        self.assertEqual(caught.exception.code, "saved_key_lacks_access_management")
        self.assertEqual(self.calls, [])


class ArgumentTests(unittest.TestCase):
    def test_known_wrong_origins_and_lifetimes_are_refused_before_the_keyring_is_opened(self):
        with mock.patch.object(rotation, "keyring_item", side_effect=AssertionError("keyring opened")):
            for arguments in (["--origin", "http://service.example"], ["--origin", "https://service.example/api"],
                              ["--origin", "https://service.example:8443"], ["--origin", "service.example"],
                              ["--origin", "https://service.example", "--days", "91"],
                              ["--origin", "https://service.example", "--days", "0"]):
                with self.assertRaises(SystemExit), mock.patch("sys.stderr", io.StringIO()):
                    rotation.main(arguments)


class HostStepTests(Store):
    def test_issue_refuses_a_lifetime_over_ninety_days(self):
        with self.assertRaises(RuntimeError):
            self.host_run("issue", ADMIN, "91", self.old.key_id)
        self.assertEqual(self.enabled(), {self.old.key_id})

    def test_issue_refuses_a_replaced_key_that_is_not_current(self):
        self.runtime.revoke_key(ADMIN, self.old.key_id)
        with self.assertRaises(RuntimeError):
            self.host_run("issue", ADMIN, "30", self.old.key_id)
        self.assertEqual(self.enabled(), set())

    def test_list_prints_no_secret_and_issue_prints_it_once(self):
        listing = self.host_run("list", ADMIN)
        self.assertNotIn(self.old.key, json.dumps(listing))
        issued = self.host_run("issue", ADMIN, "30", self.old.key_id)
        self.assertEqual(self.runtime.authenticate_key(issued["key"]).key_id, issued["key_id"])
        self.assertEqual(issued["replaces"], self.old.key_id)
        self.assertNotIn(issued["key"], json.dumps(self.host_run("list", ADMIN)))


if __name__ == "__main__":
    unittest.main()
