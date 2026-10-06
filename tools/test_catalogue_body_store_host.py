"""Selected body storage through actual host publication, serving and policy maintenance.

The S3 transport runs against the existing signed loopback stand-in. The host
record still passes the production R2 endpoint validator; only the transport
constructor substitutes the owned listener. No Cloudflare credentials or
provider calls are used, and these checks do not qualify real R2 transport.
"""
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest import mock

from loop_engine.core.provisioning_server import ProvisioningItemBinding
from loop_engine.core.service_runtime import catalogue_object_store as objects
from loop_engine.core.service_runtime.catalogue_commands import publish_catalogue
from loop_engine.core.service_runtime.catalogue_disk_view import disk_store_view
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.catalogue_serving import catalogue_settings, SOURCE_SETTINGS_VERSION_3
from loop_engine.core.service_runtime.http_checks import provisioning_request
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.object_store_fake import ObjectStoreFake
from loop_engine.core.service_runtime.public_good import PublicGoodGrant
from loop_engine.core.service_runtime.public_good_selection import host_selection
from loop_engine.core.service_runtime.records import ServiceRuntimeError

KEY, SECRET = "BALTORHOSTTESTKEY", "inert-local-storage-fixture"
KEY_REF, SECRET_REF = "env:BALTOR_STORAGE_TEST_ID", "env:BALTOR_STORAGE_TEST_SECRET"
R2_RECORD = {"record_type": "catalogue_body_store_engine/v1", "engine": "r2_object_storage",
             "endpoint": "https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com",
             "bucket": "baltor-storage-test", "access_key_id_ref": KEY_REF,
             "secret_access_key_ref": SECRET_REF}
BODY = b"# Checked reference\nA synthetic source for storage-switch tests.\n"


class HostBodyStorage(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory(prefix="body-store-host-")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.case = Fixture(self.root)
        self.fake = ObjectStoreFake(access_key_id=KEY, secret_access_key=SECRET, bucket=R2_RECORD["bucket"]).start()
        self.addCleanup(self.fake.close)
        self.opened, self.open_calls = [], []
        actual = objects.ObjectStoreBodyStore

        def transport(endpoint, bucket, **fields):
            self.assertEqual(endpoint, R2_RECORD["endpoint"])
            self.open_calls.append({"endpoint": endpoint, "write": fields["writes_authorized"]})
            fields["secret_resolver"] = lambda ref: {KEY_REF: KEY, SECRET_REF: SECRET}[ref]
            result = actual(self.fake.endpoint, bucket, **fields)
            self.opened.append(result)
            return result

        patcher = mock.patch.object(objects, "ObjectStoreBodyStore", side_effect=transport)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(lambda: [store.close() for store in self.opened])
        self.configuration = {"record_type": "service_http_host_configuration/v1",
            "runtime": {"database_path": self.case.config.database_path, "writes_authorized": True},
            "catalogue": {"record_type": SOURCE_SETTINGS_VERSION_3, "source": "store",
                          "body_store_root": str(self.root / "bodies"), "body_store_engine": dict(R2_RECORD)}}
        self.host = self.root / "host.json"
        self.write_host()
        self.case.settings = catalogue_settings(self.configuration)

    def write_host(self):
        self.host.write_text(json.dumps(self.configuration), encoding="utf-8")
        self.host.chmod(0o600)

    def publish(self):
        self.bundle = self.case.bundle([self.case.line("reference", BODY.decode())], payloads=(BODY,))
        result = publish_catalogue(str(self.host), str(self.bundle.folder), expected_bundle_digest=self.bundle.digest)
        self.release = result["release_id"]
        return result

    def code(self, operation):
        try:
            operation()
        except ServiceRuntimeError as error:
            return error.code
        return None

    def test_host_publication_and_memory_serving_use_the_selected_store(self):
        self.publish()
        self.assertGreater(self.fake.count("PUT"), 0)
        self.assertEqual(list((self.root / "bodies").rglob("*")), [])
        view = self.case.view()
        self.assertEqual(view.release_id, self.release)
        self.assertEqual(view.body_reader(self.bundle.items[0].item), BODY.decode())
        self.assertEqual(view.body_store.capabilities()["engine"], "r2_object_storage")
        self.assertTrue(any(call["write"] for call in self.open_calls))
        self.assertTrue(any(not call["write"] for call in self.open_calls))

    def test_disk_build_and_cached_view_keep_remote_byte_checks(self):
        self.publish()
        settings = replace(self.case.settings, search_engine="sqlite_disk_index", index_root=str(self.root / "index"))
        policies = {"license_policy": self.case.license_policy, "family_policy": self.case.family_policy}
        first = disk_store_view(self.case.config, settings, **policies)
        self.assertEqual(first.body_reader(self.bundle.items[0].item), BODY.decode())
        cached = disk_store_view(self.case.config, settings, **policies)
        self.assertEqual(cached.body_store.capabilities()["engine"], "r2_object_storage")
        key = next(iter(self.fake.objects))
        original = self.fake.objects[key]
        self.fake.objects[key] = b"!" * len(original)
        self.assertEqual(self.code(lambda: cached.body_reader(self.bundle.items[0].item)), "body_digest_mismatch")

    def test_selected_public_good_maintenance_uses_the_same_store(self):
        self.publish()
        entry = self.bundle.items[0]
        grant = PublicGoodGrant(ProvisioningItemBinding.from_item(entry.item), entry.version, entry.approval_ref,
                                "fixture-rights", (4,), "Synthetic storage selection", int(time.time()) + 3600,
                                useful_paths=("SKILL.md",))
        _runtime, selected = host_selection(str(self.host), (grant,), expected_release=self.release)
        self.assertEqual(selected.summary()["selected_file_placements_verified"], 1)
        self.fake.objects.clear()
        self.assertEqual(self.code(lambda: host_selection(str(self.host), (grant,), expected_release=self.release)),
                         "body_missing")

    def test_wrong_digest_and_anonymous_http_reads_do_not_touch_remote_bodies(self):
        import httpx
        self.publish()
        served = type("Served", (), {"runtime": self.case.runtime, "provisioning": self.case.binding()})()
        with running_http(served) as (origin, _service):
            with httpx.Client(base_url=origin, trust_env=False, timeout=5) as client:
                before = self.fake.count("GET")
                anonymous = client.post("/api/v1/download", json=provisioning_request(
                    "read", identity="reference", request_id="anonymous-storage"))
                self.assertIn(anonymous.status_code, (401, 403))
                headers = {"Authorization": "Bearer " + self.case.key.key}
                wrong = client.post("/api/v1/download", headers=headers, json=provisioning_request(
                    "read", identity="reference", expected_digest="f" * 64, request_id="wrong-storage"))
                self.assertNotEqual(wrong.status_code, 200)
                self.assertEqual(self.fake.count("GET"), before)
                read = client.post("/api/v1/download", headers=headers, json=provisioning_request(
                    "read", identity="reference", request_id="good-storage"))
                self.assertEqual(read.status_code, 200)
                self.assertEqual(read.content, BODY)

    def test_old_record_versions_refuse_engine_selection_before_opening(self):
        for version in ("service_catalogue_source/v1", "service_catalogue_source/v2", "service_catalogue_source/v99"):
            with self.subTest(version=version):
                configuration = {"catalogue": {**self.configuration["catalogue"], "record_type": version}}
                self.assertEqual(self.code(lambda: catalogue_settings(configuration)), "unsupported_catalogue_source")
        self.assertEqual(self.open_calls, [])

    def test_host_selection_is_frozen_and_refuses_unknown_or_wrong_source(self):
        self.configuration["catalogue"]["body_store_engine"]["engine"] = "unknown"
        self.assertEqual(self.case.settings.body_store_engine["engine"], "r2_object_storage")
        with self.assertRaises(TypeError):
            self.case.settings.body_store_engine["engine"] = "unknown"
        self.assertEqual(self.code(lambda: catalogue_settings(self.configuration)), "unsupported_body_store_engine")
        self.configuration["catalogue"]["body_store_engine"] = dict(R2_RECORD)
        self.configuration["catalogue"]["source"] = "image"
        self.assertEqual(self.code(lambda: catalogue_settings(self.configuration)), "unsupported_catalogue_source")
        self.assertEqual(self.open_calls, [])

    def test_remote_failure_never_falls_back_to_a_local_copy(self):
        from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore
        self.publish()
        VolumeBodyStore(str(self.root / "bodies"), writes_authorized=True).put(BODY)
        self.fake.objects.clear()
        self.assertEqual(self.code(self.case.view), "body_missing")
        with mock.patch.object(type(self.case.settings), "body_store", return_value=VolumeBodyStore(str(self.root / "bodies"))):
            # Known-wrong control: bypassing engine selection would conceal the missing remote object.
            self.assertEqual(self.case.view().body_reader(self.bundle.items[0].item), BODY.decode())

    def test_object_storage_does_not_need_a_local_body_folder(self):
        self.configuration["catalogue"].pop("body_store_root")
        self.write_host()
        self.case.settings = catalogue_settings(self.configuration)
        self.publish()
        self.assertEqual(self.case.view().body_reader(self.bundle.items[0].item), BODY.decode())


if __name__ == "__main__":
    unittest.main()
