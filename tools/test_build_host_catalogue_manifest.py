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
    """The review record covers the catalogue and records a reason for every rejection.

    The record names every catalogue item, including the ones no reviewer has
    judged. An item with no verdict is a written fact, not an absence, so a row
    that quietly disappears is a difference this check reports.
    """

    def test_the_record_names_every_item_of_the_catalogue(self):
        record = _review()
        catalogue = json.loads((CATALOGUE / "items.json").read_text("utf-8"))
        self.assertEqual(sorted(row["identity"] for row in record["rows"]),
                         sorted(row["reference"]["identity"] for row in catalogue["items"]))
        self.assertEqual(record["totals"]["items_in_catalogue"], len(catalogue["items"]))
        counted = {outcome: sum(1 for row in record["rows"] if row["outcome"] == outcome)
                   for outcome in tool.OUTCOMES}
        for outcome, count in counted.items():
            self.assertEqual(record["totals"][outcome], count, outcome)

    def test_every_judged_candidate_is_judged_by_every_named_reviewer(self):
        record = _review()
        reviewers = [row["reviewer_id"] for row in record["reviewers"]]
        self.assertEqual(len(reviewers), 3)
        judged = [row for row in record["rows"] if row["outcome"] != tool.NOT_REVIEWED]
        self.assertTrue(judged)
        for row in judged:
            with self.subTest(item=row["identity"]):
                self.assertEqual(sorted(d["reviewer_id"] for d in row["decisions"]), sorted(reviewers))
                for decision in row["decisions"]:
                    if decision["decision"] == "reject":
                        self.assertTrue(decision["reason"].strip(), row["identity"])

    def test_an_item_with_no_verdict_carries_no_decision_and_no_digest(self):
        unjudged = [row for row in _review()["rows"] if row["outcome"] == tool.NOT_REVIEWED]
        self.assertTrue(unjudged)
        for row in unjudged:
            with self.subTest(item=row["identity"]):
                self.assertEqual(row["decisions"], [])
                self.assertIsNone(row["body_digest"])
                self.assertIsNone(row["body_size_bytes"])
                self.assertEqual(row["approval_state"], tool.NO_STATE)

    def test_no_reviewer_produced_an_item_it_judged(self):
        for reviewer in _review()["reviewers"]:
            self.assertIs(reviewer["produced_any_item_under_review"], False)

    def test_only_an_approved_item_carries_an_approval_reference(self):
        for row in _review()["rows"]:
            with self.subTest(item=row["identity"]):
                if row["outcome"] == tool.APPROVED:
                    self.assertTrue(row["approval_ref"].strip())
                    self.assertIn(row["approval_state"], (tool.REVIEWED_STATE, tool.CARRIED_STATE))
                else:
                    self.assertEqual(row["approval_ref"], "")
                    self.assertEqual(row["approval_state"], tool.NO_STATE)

    def test_a_carried_approval_keeps_the_decisions_and_names_both_digests(self):
        carried = [row for row in _review()["rows"] if row["approval_state"] == tool.CARRIED_STATE]
        self.assertTrue(carried)
        for row in carried:
            with self.subTest(item=row["identity"]):
                self.assertEqual(row["carry"]["record_type"], tool.CARRY_RECORD_TYPE)
                self.assertEqual(row["carry"]["proof"]["record_type"], tool.PROOF_RECORD_TYPE)
                self.assertEqual(row["carry"]["carried_body_digest"], row["body_digest"])
                self.assertNotEqual(row["carry"]["reviewed_body_digest"], row["body_digest"])
                self.assertIs(row["carry"]["decisions_unchanged"], True)
                self.assertIs(row["carry"]["reviewed_again"], False)
                self.assertTrue(all(decision["decision"] == "approve" for decision in row["decisions"]))


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

    def _tampered(self, change, code):
        """Apply one change to a copy of the committed record and require the named refusal."""
        with tempfile.TemporaryDirectory(prefix="loop-engine-review-tamper-") as held:
            folder = Path(held).resolve() / "catalogue"
            shutil.copytree(CATALOGUE, folder, ignore=shutil.ignore_patterns("host-release"))
            record = json.loads((folder / "reviews.json").read_text("utf-8"))
            change(record)
            (folder / "reviews.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(tool.ManifestBuildError) as raised:
                tool.build(folder, artifact_root=IMAGE_ARTIFACT_ROOT, accepted_licenses=("MIT",), grants=[])
            self.assertEqual(raised.exception.code, code)

    @staticmethod
    def _first(record, outcome):
        return next(row for row in record["rows"] if row["outcome"] == outcome)

    def test_the_generator_refuses_a_review_record_that_approves_a_rejected_item(self):
        """An edited summary must not approve an item whose reviewer wrote an objection."""
        def forge(record):
            for row in record["rows"]:
                if row["outcome"] == tool.REJECTED:
                    row["outcome"] = tool.APPROVED
                    row["approval_state"] = tool.REVIEWED_STATE
                    row["approval_ref"] = "forged"
            record["totals"][tool.APPROVED] += record["totals"][tool.REJECTED]
            record["totals"][tool.REJECTED] = 0
        self._tampered(forge, "review_record_inconsistent")

    def test_the_generator_refuses_a_record_that_approves_an_item_no_reviewer_judged(self):
        """A row with no verdict must never become an approval by editing its outcome."""
        def forge(record):
            row = self._first(record, tool.NOT_REVIEWED)
            row.update(outcome=tool.APPROVED, approval_state=tool.REVIEWED_STATE,
                       approval_ref="forged", body_digest="0" * 64, body_size_bytes=1)
            record["totals"][tool.APPROVED] += 1
            record["totals"][tool.NOT_REVIEWED] -= 1
        self._tampered(forge, "review_record_inconsistent")

    def test_the_generator_refuses_a_record_that_reopens_an_approval_it_returned_to_candidate(self):
        """An item whose approval did not carry is a candidate; only a new review changes that."""
        def forge(record):
            row = self._first(record, tool.APPROVED)
            row.update(outcome=tool.CARRY_REFUSED, approval_state=tool.NO_STATE, approval_ref="",
                       body_digest=None, body_size_bytes=None)
            row.pop("carry", None)
            record["totals"][tool.APPROVED] -= 1
            record["totals"][tool.CARRY_REFUSED] += 1
        self._tampered(forge, "carry_record_inconsistent")

    def test_the_generator_refuses_a_carried_approval_with_no_carry_record(self):
        def forge(record):
            self._first(record, tool.APPROVED).pop("carry")
        self._tampered(forge, "carry_record_unsupported")

    def test_the_generator_refuses_a_carried_approval_whose_proof_is_missing(self):
        def forge(record):
            self._first(record, tool.APPROVED)["carry"].pop("proof")
        self._tampered(forge, "carry_record_unsupported")

    def test_the_generator_refuses_a_carry_that_names_a_digest_its_row_does_not(self):
        def forge(record):
            self._first(record, tool.APPROVED)["carry"]["carried_body_digest"] = "0" * 64
        self._tampered(forge, "carry_record_inconsistent")

    def test_the_generator_refuses_a_carry_that_claims_the_new_bytes_were_reviewed(self):
        def forge(record):
            self._first(record, tool.APPROVED)["carry"]["reviewed_again"] = True
        self._tampered(forge, "carry_record_inconsistent")

    def test_the_generator_refuses_a_carry_that_names_the_same_digest_before_and_after(self):
        def forge(record):
            row = self._first(record, tool.APPROVED)
            row["carry"]["reviewed_body_digest"] = row["body_digest"]
        self._tampered(forge, "carry_record_inconsistent")

    def test_the_generator_refuses_a_carried_approval_recorded_as_reviewed(self):
        """A reader must be able to tell the two apart, so the two facts may not disagree."""
        def forge(record):
            self._first(record, tool.APPROVED)["approval_state"] = tool.REVIEWED_STATE
        self._tampered(forge, "carry_record_inconsistent")

    def test_the_generator_refuses_a_totals_summary_that_does_not_count_the_rows(self):
        def forge(record):
            record["totals"][tool.NOT_REVIEWED] = 0
        self._tampered(forge, "review_record_inconsistent")

    def test_the_generator_refuses_an_unsupported_review_record_version(self):
        def forge(record):
            record["record_type"] = "starter_catalogue_independent_review/v1"
        self._tampered(forge, "review_record_unsupported")

    def test_the_generator_refuses_an_outcome_it_does_not_read(self):
        def forge(record):
            self._first(record, tool.APPROVED)["outcome"] = "approved_by_the_owner"
        self._tampered(forge, "review_record_unsupported")

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


class SameBasenameTest(unittest.TestCase):
    """Two bodies with one file name in different folders never share one release path.

    The release folder names a body by its file name alone. Before September 22,
    2026 the second of two such bodies replaced the first in the release folder
    without a refusal, so one approved item was written beside the bytes of
    another. The generator now refuses before it writes anything.
    """

    def test_two_bodies_with_the_same_file_name_are_refused_before_writing(self):
        first, second = _approved()[:2]
        with tempfile.TemporaryDirectory(prefix="loop-engine-same-name-") as directory:
            folder = Path(directory).resolve() / "catalogue"
            shutil.copytree(CATALOGUE, folder, ignore=shutil.ignore_patterns("host-release"))
            (folder / "bodies" / "moved").mkdir()
            (folder / "bodies" / f"{second}.md").rename(folder / "bodies" / "moved" / f"{first}.md")
            items = json.loads((folder / "items.json").read_text("utf-8"))
            for row in items["items"]:
                if row["reference"]["identity"] == second:
                    row["body_path"] = f"bodies/moved/{first}.md"
            (folder / "items.json").write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(tool.ManifestBuildError) as held:
                tool.build(folder, artifact_root=IMAGE_ARTIFACT_ROOT, accepted_licenses=("MIT",), grants=[],
                           include=(first, second))
            self.assertEqual(held.exception.code, "duplicate_release_path")
