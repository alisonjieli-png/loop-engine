"""Checks for tools/build_host_catalogue_manifest.py and the release folder it owns.

Every check runs against the real starter catalogue, the real review record and
the real host loader, ``load_host_manifest``. No network, model or provider call
happens. The known-wrong cases are the point of this file: a body changed after
its digest was computed, an item a reviewer rejected, a body path that escapes
the artifact root, and a licence the host policy does not accept. Each one names
the exact refusal code the host or the generator returns.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import build_host_catalogue_manifest as tool  # noqa: E402
from loop_engine.core.service_runtime.http_entrypoint import (  # noqa: E402
    HostLicensePolicy, load_host_manifest,
)
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

CATALOGUE = HERE.parent / "examples/29_intelligence_service/starter-catalogue"
RELEASE = CATALOGUE / "host-release"
#: The absolute path the release folder is copied to inside the service image.
IMAGE_ARTIFACT_ROOT = "/opt/baltor/catalogue"
GRANTS = ["pilot-owner:bodies:required"]


def _review():
    return json.loads((CATALOGUE / "reviews.json").read_text("utf-8"))


def _approved():
    return sorted(row["identity"] for row in _review()["rows"] if row["outcome"] == "approved")


def _rejected():
    return sorted(row["identity"] for row in _review()["rows"] if row["outcome"] == "rejected")


class ReviewRecordTest(unittest.TestCase):
    """The review record covers the catalogue and records a reason for every rejection."""

    def test_every_candidate_is_judged_by_every_named_reviewer(self):
        record = _review()
        catalogue = json.loads((CATALOGUE / "items.json").read_text("utf-8"))
        reviewers = [row["reviewer_id"] for row in record["reviewers"]]
        self.assertEqual(len(reviewers), 3)
        self.assertEqual(sorted(row["identity"] for row in record["rows"]),
                         sorted(row["reference"]["identity"] for row in catalogue["items"]))
        for row in record["rows"]:
            self.assertEqual(sorted(d["reviewer_id"] for d in row["decisions"]), sorted(reviewers))
            for decision in row["decisions"]:
                if decision["decision"] == "reject":
                    self.assertTrue(decision["reason"].strip(), row["identity"])
        self.assertEqual(record["totals"]["approved"], 43)
        self.assertEqual(record["totals"]["rejected"], 6)

    def test_no_reviewer_produced_an_item_it_judged(self):
        for reviewer in _review()["reviewers"]:
            self.assertIs(reviewer["produced_any_item_under_review"], False)

    def test_a_rejected_item_carries_no_approval_reference(self):
        for row in _review()["rows"]:
            if row["outcome"] == "rejected":
                self.assertEqual(row["approval_ref"], "")
            else:
                self.assertTrue(row["approval_ref"].strip())


class GeneratedReleaseTest(unittest.TestCase):
    """The committed release folder is exactly what the command generates today."""

    def test_the_committed_release_folder_matches_the_review_record(self):
        code = tool.main(["--catalogue", str(CATALOGUE), "--output", str(RELEASE),
                          "--artifact-root", IMAGE_ARTIFACT_ROOT, "--accept-license", "MIT",
                          *sum((["--grant", value] for value in GRANTS), [])])
        self.assertEqual(code, 0, "the release folder differs from what the command generates")

    def test_the_release_folder_holds_only_approved_bodies(self):
        manifest = json.loads((RELEASE / "manifest.json").read_text("utf-8"))
        self.assertEqual(manifest["artifact_root"], IMAGE_ARTIFACT_ROOT)
        self.assertEqual(sorted(row["reference"]["identity"] for row in manifest["items"]), _approved())
        held = sorted(path.stem for path in (RELEASE / "bodies").iterdir())
        self.assertEqual(held, _approved())
        for identity in _rejected():
            self.assertFalse((RELEASE / "bodies" / f"{identity}.md").exists(), identity)

    def test_every_manifest_row_carries_exactly_the_keys_the_host_reads(self):
        manifest = json.loads((RELEASE / "manifest.json").read_text("utf-8"))
        self.assertEqual(set(manifest), {"record_type", "artifact_root", "items"})
        for row in manifest["items"]:
            self.assertEqual(set(row), {"reference", "body_path", "approval_ref", "grants"})
            self.assertEqual(row["reference"]["license"], "MIT")
            self.assertTrue(row["approval_ref"].startswith(
                "examples/29_intelligence_service/starter-catalogue/reviews.json#"))
            self.assertEqual(row["grants"], [{"tenant_id": "pilot-owner", "body_allowed": True,
                                              "metering": "required"}])


class _Staged:
    """Generate the release folder into a temporary artifact root the host can open."""

    def __enter__(self):
        self.folder = Path(tempfile.mkdtemp(prefix="loop-engine-manifest-check-")).resolve()
        self.root = self.folder / "catalogue"
        code = tool.main(["--catalogue", str(CATALOGUE), "--output", str(self.root),
                          "--artifact-root", str(self.root), "--accept-license", "MIT",
                          *sum((["--grant", value] for value in GRANTS), []), "--write"])
        assert code == 0, "the staged release folder could not be generated"
        self.manifest = self.root / "manifest.json"
        return self

    def __exit__(self, *_details):
        shutil.rmtree(self.folder, ignore_errors=True)
        return False

    def rewrite(self, change):
        manifest = json.loads(self.manifest.read_text("utf-8"))
        change(manifest)
        self.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


class HostAcceptsTheReleaseTest(unittest.TestCase):
    """The real host loader registers every approved item and no rejected item."""

    def test_the_host_registers_the_approved_items_and_reads_their_bodies(self):
        with _Staged() as staged:
            catalogue, resolver, read, grants = load_host_manifest(str(staged.manifest))
            self.assertEqual(sorted(catalogue.items), _approved())
            for identity in _rejected():
                self.assertNotIn(identity, catalogue.items)
            self.assertEqual(sorted(grants), ["pilot-owner"])
            self.assertEqual(len(grants["pilot-owner"]), len(_approved()))
            item = catalogue.items[_approved()[0]]
            self.assertEqual(len(read(item)), item.size_bytes)
            from loop_engine.core.provisioning_server import ProvisioningItemBinding
            decision = resolver.resolve(ProvisioningItemBinding.from_item(item))
            self.assertEqual(decision.status, "approved")
            self.assertTrue(decision.approval_ref.endswith(item.identity))


class KnownWrongCaseTest(unittest.TestCase):
    """Each case below must be refused. A removed guard makes exactly one of these fail."""

    def test_a_body_changed_after_its_digest_was_computed_is_refused(self):
        with _Staged() as staged:
            body = staged.root / "bodies" / f"{_approved()[0]}.md"
            body.write_bytes(body.read_bytes().replace(b"\n", b" \n", 1))
            with self.assertRaises(ServiceRuntimeError) as held:
                load_host_manifest(str(staged.manifest))
            self.assertIn(held.exception.code, ("artifact_size_mismatch", "artifact_digest_mismatch"))

    def test_a_body_changed_without_changing_its_size_is_refused_by_digest(self):
        with _Staged() as staged:
            body = staged.root / "bodies" / f"{_approved()[0]}.md"
            payload = bytearray(body.read_bytes())
            payload[0] = ord("X") if payload[0] != ord("X") else ord("Y")
            body.write_bytes(bytes(payload))
            with self.assertRaises(ServiceRuntimeError) as held:
                load_host_manifest(str(staged.manifest))
            self.assertEqual(held.exception.code, "artifact_digest_mismatch")

    def test_the_generator_refuses_an_item_a_reviewer_rejected(self):
        for identity in _rejected():
            with self.subTest(identity=identity), self.assertRaises(tool.ManifestBuildError) as held:
                tool.build(CATALOGUE, artifact_root=IMAGE_ARTIFACT_ROOT, accepted_licenses=("MIT",),
                           grants=[], include=(identity,))
            self.assertEqual(held.exception.code, "item_not_approved")

    def test_the_generator_refuses_a_review_record_that_approves_a_rejected_item(self):
        """An edited summary must not approve an item whose reviewer wrote an objection."""
        with tempfile.TemporaryDirectory(prefix="loop-engine-review-tamper-") as held:
            folder = Path(held).resolve() / "catalogue"
            shutil.copytree(CATALOGUE, folder, ignore=shutil.ignore_patterns("host-release"))
            record = json.loads((folder / "reviews.json").read_text("utf-8"))
            for row in record["rows"]:
                if row["outcome"] == "rejected":
                    row["outcome"] = "approved"
                    row["approval_ref"] = "forged"
            (folder / "reviews.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(tool.ManifestBuildError) as raised:
                tool.build(folder, artifact_root=IMAGE_ARTIFACT_ROOT, accepted_licenses=("MIT",), grants=[])
            self.assertEqual(raised.exception.code, "review_record_inconsistent")

    def test_a_body_path_that_escapes_the_artifact_root_is_refused(self):
        with _Staged() as staged:
            outside = staged.folder / "outside.md"
            outside.write_text("This file is outside the artifact root.\n", encoding="utf-8")
            staged.rewrite(lambda manifest: manifest["items"][0].update(body_path="../outside.md"))
            with self.assertRaises(ServiceRuntimeError) as held:
                load_host_manifest(str(staged.manifest))
            self.assertEqual(held.exception.code, "unsafe_artifact_path")

    def test_an_absolute_body_path_is_refused(self):
        with _Staged() as staged:
            outside = staged.folder / "outside.md"
            outside.write_text("This file is outside the artifact root.\n", encoding="utf-8")
            staged.rewrite(lambda manifest: manifest["items"][0].update(body_path=str(outside)))
            with self.assertRaises(ServiceRuntimeError) as held:
                load_host_manifest(str(staged.manifest))
            self.assertEqual(held.exception.code, "unsafe_artifact_path")

    def test_the_generator_refuses_a_body_path_that_escapes_the_catalogue_folder(self):
        with self.assertRaises(tool.ManifestBuildError) as held:
            tool._body_path(CATALOGUE, "../../../etc/hostname")
        self.assertEqual(held.exception.code, "unsafe_artifact_path")

    def test_a_licence_the_host_policy_does_not_accept_is_refused(self):
        with _Staged() as staged:
            policy = HostLicensePolicy(accepted_licenses=("Apache-2.0",))
            with self.assertRaises(ServiceRuntimeError) as held:
                load_host_manifest(str(staged.manifest), license_policy=policy)
            self.assertEqual(held.exception.code, "item_license_not_accepted")

    def test_the_generator_refuses_a_licence_the_host_policy_does_not_accept(self):
        with self.assertRaises(tool.ManifestBuildError) as held:
            tool.build(CATALOGUE, artifact_root=IMAGE_ARTIFACT_ROOT,
                       accepted_licenses=("Apache-2.0",), grants=[])
        self.assertEqual(held.exception.code, "item_license_not_accepted")

    def test_no_host_policy_can_accept_the_unknown_licence_the_rejected_items_declare(self):
        """The two unknown-licence candidates are refused before registration, by the host and here."""
        unknown = [row["identity"] for row in _review()["rows"] if row["declared_license"] == "unknown"]
        self.assertEqual(unknown, ["check_a_table_join_before_trusting_it",
                                   "make_a_data_pipeline_safe_to_run_again"])
        with self.assertRaises(ServiceRuntimeError) as held:
            HostLicensePolicy(accepted_licenses=("MIT", "unknown"))
        self.assertEqual(held.exception.code, "invalid_license_policy")
        self.assertEqual(HostLicensePolicy().refusal("unknown"), "item_license_unknown")

    def test_an_approval_reference_is_required_for_every_served_row(self):
        with _Staged() as staged:
            staged.rewrite(lambda manifest: manifest["items"][0].update(approval_ref="  "))
            with self.assertRaises(ServiceRuntimeError) as held:
                load_host_manifest(str(staged.manifest))
            self.assertEqual(held.exception.code, "explicit_host_review_required")


if __name__ == "__main__":
    unittest.main()
