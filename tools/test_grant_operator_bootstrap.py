"""Grant confirmation keeps catalogue integrity without preparing unused search."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, mock

from loop_engine.core.service_runtime import catalogue_search, catalogue_serving, http_entrypoint
from loop_engine.core.service_runtime.catalogue_grants import follow_active_release
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture, bundle_line
from loop_engine.core.service_runtime.catalogue_releases import withdraw
from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore
from loop_engine.core.service_runtime.records import ServiceRuntimeError, TenantRegistration
from loop_engine.core.service_runtime.runtime import GRANTS


def configured(root, *, source="store"):
    case = Fixture(root)
    lines = [case.line(name, "# " + name + "\n", attributes={"domain": ["data" if name == "keeper" else "design"]})
             for name in ("keeper", "denied", "withdrawn")]
    case.publish(lines)
    follow_active_release(case.runtime, ["alpha"], denials=("denied",))
    withdraw(case.context, identity="withdrawn", note_text="Fixture withdrawal")
    case.runtime.register_tenant(TenantRegistration("beta", "tenant:beta"))
    image = case.root / "image"
    image.mkdir()
    body = b"# Packaged item\n"
    (image / "item.md").write_bytes(body)
    reference = bundle_line("packaged_item", [("SKILL.md", body, "text/markdown", "skill_definition")])["reference"]
    manifest = image / "manifest.json"
    manifest.write_text(json.dumps({"record_type": "host_attested_intelligence_manifest/v1", "artifact_root": str(image),
        "items": [{"reference": reference, "body_path": "item.md", "approval_ref": "review:fixture",
                   "grants": [{"tenant_id": tenant, "body_allowed": True, "metering": "required"}
                              for tenant in ("alpha", "beta")]}]}))
    configuration = {"record_type": "service_http_host_configuration/v1",
        "runtime": {"database_path": case.config.database_path, "writes_authorized": True},
        "http": {"public_base_url": "http://127.0.0.1:8080", "allowed_hosts": ["127.0.0.1:8080"], "allow_loopback_http": True},
        "authentication": {}, "manifest_path": str(manifest),
        "catalogue": {"record_type": "service_catalogue_source/v1", "source": source,
                      "body_store_root": str(case.root / "bodies"), "refresh_seconds": 5}}
    host = case.root / "host.json"
    host.write_text(json.dumps(configuration))
    return case, host, configuration


class GrantOperatorBootstrapTests(TestCase):
    def test_grants_do_not_construct_search_or_the_web_application(self):
        for source in ("store", "image"):
            with self.subTest(source=source), TemporaryDirectory() as directory:
                case, path, _ = configured(Path(directory), source=source)
                with mock.patch.object(catalogue_search, "ReleaseSearchIndex", side_effect=AssertionError("unused search")), \
                        mock.patch.object(http_entrypoint, "load_host_application", side_effect=AssertionError("unused web bootstrap")):
                    result = http_entrypoint.apply_host_grants(str(path))
                self.assertEqual(result["granted_items_by_tenant"], {"alpha": 1, "beta": 1})
                self.assertEqual(result["following_release_tenants"], ["alpha"])
                self.assertEqual(result["tenants_registered"], 0)
                self.assertFalse(result["remote_accounts_created"])
                with case.runtime._catalog.store() as store:
                    following = case.runtime._catalog.read(store, GRANTS, "alpha")["payload"]
                self.assertEqual(following["denials"], ["denied"])
                self.assertEqual(following["engine"], "follow_active_release")

    def test_deferred_index_is_built_once_and_matches_the_serving_index(self):
        with TemporaryDirectory() as directory:
            case, _path, configuration = configured(Path(directory))
            serving = case.view()
            constructor = catalogue_search.ReleaseSearchIndex
            with mock.patch.object(catalogue_search, "ReleaseSearchIndex", wraps=constructor) as built:
                view, _ = catalogue_serving.load_catalogue_view(configuration, case.config,
                    license_policy=case.license_policy, family_policy=case.family_policy, prepare_search=False)
                built.assert_not_called()
                index = view.search_index()
                self.assertIs(index, view.search_index())
                self.assertEqual(built.call_count, 1)
            self.assertEqual(index.rank("keeper", mode="lexical", pool=10),
                             serving.search_index().rank("keeper", mode="lexical", pool=10))
            self.assertEqual(index.rank("keeper", mode="hybrid", pool=10),
                             serving.search_index().rank("keeper", mode="hybrid", pool=10))
            self.assertEqual(index.stats(), serving.search_index().stats())
            self.assertEqual(index.eligible((("domain", "any_of", ("data",)),)),
                             serving.search_index().eligible((("domain", "any_of", ("data",)),)))
            self.assertEqual(set(view.approved_bindings()), {"keeper", "denied"})

    def test_deferral_keeps_body_integrity_checks_and_the_control_detects_their_removal(self):
        with TemporaryDirectory() as directory:
            case, path, _ = configured(Path(directory))
            view = case.view()
            entry = view.packages["keeper"].files[0]
            stored = case.root / "bodies" / VolumeBodyStore.object_key(entry.digest)
            stored.chmod(0o600)
            stored.write_bytes(b"!" * entry.size_bytes)
            with self.assertRaises(ServiceRuntimeError) as caught:
                http_entrypoint.apply_host_grants(str(path))
            self.assertEqual(caught.exception.code, "body_digest_mismatch")
            with mock.patch("loop_engine.core.service_runtime.catalogue_releases.verify_release_bodies"):
                self.assertEqual(http_entrypoint.apply_host_grants(str(path))["granted_items_by_tenant"]["alpha"], 1)

    def test_unknown_preparation_profile_is_refused(self):
        with TemporaryDirectory() as directory:
            case, _path, configuration = configured(Path(directory))
            for value in (0, "false", None):
                with self.subTest(value=value), self.assertRaises(ServiceRuntimeError) as caught:
                    catalogue_serving.load_catalogue_view(configuration, case.config,
                        license_policy=case.license_policy, family_policy=case.family_policy, prepare_search=value)
                self.assertEqual(caught.exception.code, "invalid_catalogue_load_profile")

    def test_eager_index_control_detects_the_original_unnecessary_work(self):
        with TemporaryDirectory() as directory:
            _case, path, _ = configured(Path(directory))
            original = catalogue_serving.load_catalogue_view
            def eager(*args, **kwargs):
                kwargs["prepare_search"] = True
                return original(*args, **kwargs)
            with mock.patch.object(catalogue_serving, "load_catalogue_view", eager), \
                    mock.patch.object(catalogue_search, "ReleaseSearchIndex", side_effect=AssertionError("unused search")), \
                    self.assertRaisesRegex(AssertionError, "unused search"):
                http_entrypoint.apply_host_grants(str(path))


if __name__ == "__main__":
    main()
