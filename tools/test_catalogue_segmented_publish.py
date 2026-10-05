"""Segmented (version 2) bundles through the operator tools and the service's own publish, end to end.

Synthetic packages in a real temporary service store and body folder; no provider, network or Machine. The
publish tool's remote calls are mocked, as in test_publish_catalogue_delta.py. The checks:

1. a reconciled version 2 bundle's proof names exactly the release the service publishes, from a version 1 base
   and then from a version 2 base, and the second carries only the segments and item lines the first lacks;
2. the publish tool asks the Machine which bundle versions it reads and refuses a version 2 bundle, before any
   remote effect, when the image predates that question; with version 2 offered it uploads only new objects;
3. a segment list changed after the proof was written is refused by the proof check.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import publish_catalogue_delta as delta
import reconcile_catalogue_bundle as reconcile
from test_reconcile_catalogue_bundle import bundle, line
from loop_engine.core.service_runtime.catalogue_bundle import read_bundle
from loop_engine.core.service_runtime.catalogue_releases import CatalogueOperatorContext, publish
from loop_engine.core.service_runtime.catalogue_segment_publish import publish_segmented
from loop_engine.core.service_runtime.catalogue_segments import (SEGMENTED_BUNDLE_RECORD_TYPE, catalogue_formats,
                                                                 read_segmented_bundle)
from loop_engine.core.service_runtime.http_entrypoint import HostFamilyPolicy, HostLicensePolicy
from loop_engine.core.service_runtime.records import ServiceRuntimeConfig
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding

POLICIES = {"license_policy": HostLicensePolicy(("MIT",)), "family_policy": HostFamilyPolicy()}


def changes_for(base, release, *, additions=(), replacements=(), withdrawals=()):
    return reconcile.Changes.from_dict({"record_type": reconcile.REQUEST_VERSION, "base_release": release,
                                        "base_bundle_digest": base.digest, "additions": list(additions),
                                        "replacements": list(replacements), "withdrawals": list(withdrawals)})


def observed(base, release):
    return {"record_type": "service_catalogue_view/v1", "release_id": release,
            "content_digest": reconcile.bundle_content(base), "schema_digest": base.schema.digest,
            "items": len(base.items), "withdrawn_left_out": 0}


class SegmentedReconciliation(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "bodies").mkdir()
        config = ServiceRuntimeConfig(str(self.root / "service.db"), writes_authorized=True)
        self.context = CatalogueOperatorContext(ServiceCatalogBinding(config), str(self.root / "bodies"))
        with self.context.binding.store(write=True):
            pass  # a first write-mode open creates the records table, as a host's configure step does
        names = [f"skill_{index:03d}" for index in range(40)]
        self.base = bundle(self.root / "base", [line(name, f"body of {name}") for name in names],
                           [f"body of {name}" for name in names])
        first = publish(self.context, read_bundle(self.base.folder, **POLICIES))
        self.release = first["release_id"]

    def reconcile(self, base, release, updates, name, extra_roots=(), **declared):
        changes = changes_for(base, release, **declared)
        plan = reconcile.write_reconciled(base, updates, changes, self.root / name, observed(base, release),
                                          bundle_format=SEGMENTED_BUNDLE_RECORD_TYPE, segment_target=16,
                                          extra_roots=extra_roots)
        proof = json.loads((self.root / name / reconcile.PROOF_FILE).read_text())
        return plan, proof

    def test_the_proof_names_the_release_the_service_publishes_from_both_base_versions(self):
        update = bundle(self.root / "update", [line("skill_100", "a new body")], ["a new body"])
        plan, proof = self.reconcile(self.base, self.release, (update,), "v2-first", additions=("skill_100",))
        self.assertEqual(proof["record_type"], reconcile.PROOF_VERSION_2)
        self.assertEqual(plan["bundle_format"], SEGMENTED_BUNDLE_RECORD_TYPE)
        result = publish_segmented(self.context, read_segmented_bundle(self.root / "v2-first", **POLICIES),
                                   expected_release=self.release)
        self.assertEqual(result["release_id"], proof["result_release"])
        self.assertEqual(result["content_digest"], proof["result_content_digest"])
        self.assertEqual(result["segments_written"], result["segments"])
        first = reconcile.load_bundle(self.root / "v2-first", ("MIT",))
        second_update = bundle(self.root / "update-2", [line("skill_200", "another body")], ["another body"])
        # A delta-only base names the earlier bundles' blob folders, as an operator passes --body-root.
        _plan, second_proof = self.reconcile(first, result["release_id"], (second_update,), "v2-second",
                                             extra_roots=(self.base.folder / "blobs",), additions=("skill_200",))
        candidate = reconcile.load_bundle(self.root / "v2-second", ("MIT",))
        uploads = delta.segmented_uploads(first, candidate)
        new_segments = [path for path in uploads if path.startswith("segments/")]
        self.assertEqual([path for path in uploads if path.startswith("items/")],
                         [f"items/sha256/{item.version[:2]}/{item.version}" for item in candidate.items
                          if item.identity == "skill_200"])
        self.assertTrue(0 < len(new_segments) < len(candidate.segments))
        second = publish_segmented(self.context, read_segmented_bundle(self.root / "v2-second", **POLICIES),
                                   expected_release=result["release_id"])
        self.assertEqual(second["release_id"], second_proof["result_release"])
        self.assertEqual(second["segments_written"], len(new_segments))
        self.assertEqual(second["items_written"], 1)

    def test_a_segment_list_changed_after_the_proof_is_refused(self):
        update = bundle(self.root / "update", [line("skill_100", "a new body")], ["a new body"])
        self.reconcile(self.base, self.release, (update,), "v2-tampered", additions=("skill_100",))
        listing = self.root / "v2-tampered" / "release-segments.jsonl"
        rows = listing.read_bytes().splitlines(keepends=True)
        listing.write_bytes(b"".join(rows[1:] + rows[:1]))
        raw, proof = reconcile.read_control(self.root / "v2-tampered" / reconcile.PROOF_FILE)
        with self.assertRaises(Exception):
            reconcile.check_proof(self.base, reconcile.load_bundle(self.root / "v2-tampered", ("MIT",)), proof)


class SegmentedPublishNegotiation(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.base = bundle(root / "base", [line("old", "held")], ["held"])
        update = bundle(root / "update", [line("new", "new")], ["new"])
        changes = changes_for(self.base, "a" * 64, additions=("new",))
        self.before = observed(self.base, "a" * 64)
        self.output = root / "output"
        self.plan = reconcile.write_reconciled(self.base, (update,), changes, self.output, self.before,
                                               bundle_format=SEGMENTED_BUNDLE_RECORD_TYPE, segment_target=16)
        self.proof = json.loads((self.output / reconcile.PROOF_FILE).read_text())
        self.after = {**self.before, "release_id": self.proof["result_release"],
                      "content_digest": self.proof["result_content_digest"], "items": 2}
        self.result = {"release_id": self.after["release_id"], "content_digest": self.after["content_digest"],
                       "bundle_digest": self.plan["bundle_digest"]}
        self.commands = []

    def simulate(self, formats):
        def execute(command, **kwargs):
            self.commands.append(command)
            if "catalogue-formats" in command:
                if formats is None:
                    raise RuntimeError("invalid choice: 'catalogue-formats'")
                return json.dumps(formats)
            return json.dumps({"result": self.result}) if "tail -c" in command else ""
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(delta, "machine_exec", side_effect=execute))
            stack.enter_context(mock.patch.object(delta, "active_catalogue",
                                                  side_effect=[self.before, self.before, self.after]))
            upload = stack.enter_context(mock.patch.object(delta, "upload_missing"))
            transport = stack.enter_context(mock.patch.object(delta, "fly", return_value=""))
            stack.enter_context(mock.patch.object(delta.time, "monotonic", side_effect=[0, 0, 2]))
            stack.enter_context(mock.patch.object(delta.time, "sleep"))
            stack.enter_context(mock.patch.object(delta, "POINTER_WAIT_SECONDS", 1))
            answer = delta.publish("slot", self.output, self.plan["bundle_digest"], base_bundle=self.base.folder,
                                   base_release="a" * 64, reconciliation_digest=self.plan["reconciliation_digest"])
            return answer, upload, transport

    def test_an_image_without_the_formats_command_is_refused_before_any_remote_effect(self):
        with self.assertRaises(Exception) as caught:
            self.simulate(None)
        self.assertEqual(getattr(caught.exception, "code", None), "catalogue_format_unsupported")
        self.assertEqual([command for command in self.commands if "catalogue-formats" not in command], [])

    def test_with_version_2_offered_only_new_objects_and_the_segment_list_are_sent(self):
        answer, upload, transport = self.simulate(catalogue_formats())
        self.assertTrue(answer["published"])
        self.assertEqual(answer["bundle_record_type"], SEGMENTED_BUNDLE_RECORD_TYPE)
        sent = upload.call_args.args[3]
        candidate = reconcile.load_bundle(self.output, ("MIT",))
        self.assertEqual(sorted(path for path in sent if path.startswith("items/")),
                         [f"items/sha256/{item.version[:2]}/{item.version}" for item in candidate.items
                          if item.identity == "new"])
        self.assertEqual(len([path for path in sent if path.startswith("segments/")]), len(candidate.segments))
        puts = [call.args for call in transport.call_args_list if call.args[:3] == ("ssh", "sftp", "put")]
        self.assertTrue(any(str(args[3]).endswith("release-segments.jsonl") for args in puts))
        self.assertFalse(any(str(args[3]).endswith("items.jsonl") for args in puts))


if __name__ == "__main__":
    unittest.main()
