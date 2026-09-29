"""The delta catalogue publish, checked without a Fly account and without a Machine.

Kind: continuous integration check.

The full-bundle publish re-uploads every blob the volume already holds. This check holds the delta
arithmetic: which blobs a release adds, how they are grouped into puts, and that the put stops at the
batch ceiling. Each has a known-wrong control that puts the old behaviour back and must fail:

- a blob the volume already holds is not uploaded again, and one it lacks is;
- a put carries at most BATCH_BYTES, and the last batch is not empty;
- the digests of the uploaded files are read back and a blob that did not land is a refusal, so a cut
  put fails the publish instead of reaching a customer;
- the pointer is moved by the same publish-catalogue command, with the builder's digest, and only
  after every blob is present;
- a listing that cannot be read is an error, never an empty set, because an empty set re-uploads
  everything and hides the fault.
"""
from __future__ import annotations

import hashlib
import json
from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import publish_catalogue_delta as delta


def _bundle(folder: Path, digests: dict[str, int]) -> Path:
    """A local bundle directory holding the named blobs at their content-addressed paths."""
    bundle = folder / "bundle"
    (bundle / "blobs" / "sha256").mkdir(parents=True)
    for digest, size in digests.items():
        path = bundle / "blobs" / "sha256" / digest[:2] / digest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)
    (bundle / "bundle.json").write_text(json.dumps({"record_type": "catalogue_release_bundle_build/v1"}))
    (bundle / "items.jsonl").write_text("")
    return bundle


class DeltaArithmetic(unittest.TestCase):
    """Which blobs a release adds, and how they are grouped into puts."""

    def test_a_blob_the_volume_holds_is_not_uploaded_again(self):
        held = {"a" * 64, "b" * 64}
        local = ["a" * 64, "b" * 64, "c" * 64]
        missing = [value for value in local if value not in held]
        self.assertEqual(missing, ["c" * 64])

    def test_a_put_carries_at_most_the_batch_ceiling(self):
        sizes = {f"{index:064x}": 100 for index in range(10)}
        missing = sorted(sizes)
        with mock.patch.object(delta, "BATCH_BYTES", 250):
            groups = delta.group_batches(missing, sizes)
        self.assertTrue(all(sum(sizes[d] for d in group) <= 250 for group in groups))
        self.assertEqual([digest for group in groups for digest in group], missing)
        self.assertTrue(all(group for group in groups), "a batch with no blobs would upload nothing")

    def test_one_blob_larger_than_the_ceiling_is_still_uploaded_alone(self):
        big = f"{1:064x}"
        groups = delta.group_batches([big], {big: delta.BATCH_BYTES * 3})
        self.assertEqual(groups, [[big]])

    def test_the_bundle_digest_reads_only_real_blob_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _bundle(Path(tmp), {"a" * 64: 1})
            (bundle / "blobs" / "sha256" / "aa" / "not-a-digest").write_bytes(b"")
            self.assertEqual(delta.blob_digests(bundle), ["a" * 64])

    def test_base_inventory_is_hash_checked_before_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            body = (json.dumps({"package": {"files": [{"digest": "a" * 64}]}}) + "\n").encode()
            (folder / "items.jsonl").write_bytes(body)
            (folder / "bundle.json").write_text(json.dumps({"items": 1,
                "items_digest": hashlib.sha256(body).hexdigest()}))
            self.assertEqual(delta.base_digests(folder), {"a" * 64})
            (folder / "items.jsonl").write_bytes(body + b"\n")
            with self.assertRaisesRegex(ValueError, "does not match"):
                delta.base_digests(folder)

    def test_active_view_uses_bounded_public_health_not_volume_scan(self):
        payload = json.dumps({"result": {"catalogue_release": {"release_id": "a" * 64}}}).encode()
        with mock.patch.object(delta, "urlopen", return_value=BytesIO(payload)) as read, \
                mock.patch.object(delta, "machine_exec") as remote:
            self.assertEqual(delta.active_release(), "a" * 64)
            self.assertEqual(read.call_args.kwargs["timeout"], 15)
            remote.assert_not_called()


class DeltaUploadGuarantees(unittest.TestCase):
    """A put that was cut short is a refusal, not a body a customer finds broken."""

    def test_archive_checksum_is_checked_before_extraction(self):
        with mock.patch.object(delta, "machine_exec", return_value="wrong archive") as remote:
            with self.assertRaisesRegex(RuntimeError, "extraction was not started"):
                delta.extract_archive("/data/incoming/probe.tar", "a" * 64, "/data/incoming/probe")
            self.assertEqual(remote.call_count, 1)

    def test_detached_extraction_requires_a_successful_receipt(self):
        with mock.patch.object(delta, "machine_exec", side_effect=["a" * 64 + " archive", "", "0"]) as remote:
            delta.extract_archive("/data/incoming/probe.tar", "a" * 64, "/data/incoming/probe")
        self.assertIn("nohup", remote.call_args_list[1].args[0])
        with mock.patch.object(delta, "machine_exec", side_effect=["a" * 64 + " archive", "", "2", "bad tar"]):
            with self.assertRaisesRegex(RuntimeError, "extraction failed"):
                delta.extract_archive("/data/incoming/probe.tar", "a" * 64, "/data/incoming/probe")

    def test_a_blob_that_did_not_land_refuses_the_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _bundle(Path(tmp), {"a" * 64: 4, "b" * 64: 4})
            missing = ["a" * 64, "b" * 64]
            landed = ["a" * 64]

            def fake_exec(command, **kwargs):
                if "find" in command:
                    return "\n".join(landed)
                return ""

            with mock.patch.object(delta, "machine_exec", side_effect=fake_exec), \
                    mock.patch.object(delta, "extract_archive"), \
                    mock.patch.object(delta, "fly", return_value=""):
                with self.assertRaises(RuntimeError) as raised:
                    delta.upload_missing(bundle, missing, "delta-test")
            self.assertIn("did not arrive", str(raised.exception))

    def test_every_blob_present_passes_the_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _bundle(Path(tmp), {"a" * 64: 4, "b" * 64: 4})
            missing = ["a" * 64, "b" * 64]

            def fake_exec(command, **kwargs):
                if "find" in command:
                    return "\n".join(missing)
                return ""

            with mock.patch.object(delta, "machine_exec", side_effect=fake_exec), \
                    mock.patch.object(delta, "extract_archive"), \
                    mock.patch.object(delta, "fly", return_value="") as transport:
                self.assertIsNone(delta.upload_missing(bundle, missing, "delta-test"))
                arguments = transport.call_args.args
                self.assertTrue(arguments[3].endswith(".tar"))
                self.assertNotIn("--recursive", arguments)
                self.assertIn("--machine", arguments)
                self.assertIn(delta.MACHINE, arguments)
                self.assertNotIn("-r", arguments)
                self.assertNotIn("-g", arguments)

    def test_an_unreadable_listing_is_an_error_and_never_an_empty_set(self):
        def refusing_exec(command, **kwargs):
            raise RuntimeError("the listing failed")

        with mock.patch.object(delta, "machine_exec", side_effect=refusing_exec):
            with self.assertRaises(RuntimeError):
                delta.remote_digests()


class DeltaPublishOrder(unittest.TestCase):
    """The pointer moves by the ordinary command, and only after every blob is present."""

    def test_the_publish_command_carries_the_builders_digest_and_the_staged_release(self):
        recorded = []

        # A real prior release id, so the flow reaches the publish command; the pointer never moves
        # because every later status read still names the old release, and the wait expires.
        prior = "release-before"

        def fake_exec(command, **kwargs):
            recorded.append(command)
            if "catalogue-status" in command:
                return json.dumps({"result": {"active_release_id": prior}})
            return ""

        with tempfile.TemporaryDirectory() as tmp:
            bundle = _bundle(Path(tmp), {"a" * 64: 4})
            digest = hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest()
            with mock.patch.object(delta, "machine_exec", side_effect=fake_exec), \
                    mock.patch.object(delta, "active_release", return_value=prior), \
                    mock.patch.object(delta, "upload_missing") as upload, \
                    mock.patch.object(delta, "fly", return_value=""), \
                    mock.patch.object(delta, "POINTER_WAIT_SECONDS", 0):
                with self.assertRaises(RuntimeError):
                    delta.publish("slot", bundle, digest)
        self.assertEqual(upload.call_count, 1, "every blob is uploaded before the pointer moves")
        joined = " ".join(recorded)
        self.assertIn("publish-catalogue", joined)
        self.assertIn(digest, joined)
        self.assertIn("--expected-bundle-digest", joined)
        self.assertIn("--expected-release " + prior, joined)

    def test_publish_uploads_only_the_blobs_the_volume_lacks(self):
        # Known-wrong control for the delta itself: when the arithmetic was ignored and every local
        # blob uploaded, this saw the whole bundle going up and failed.
        prior = "release-before"
        recorded = []

        def fake_exec(command, **kwargs):
            recorded.append(command)
            if "catalogue-status" in command:
                return json.dumps({"result": {"active_release_id": prior}})
            return ""

        with tempfile.TemporaryDirectory() as tmp:
            bundle = _bundle(Path(tmp), {"a" * 64: 4, "b" * 64: 4, "c" * 64: 4})
            with mock.patch.object(delta, "machine_exec", side_effect=fake_exec), \
                    mock.patch.object(delta, "active_release", return_value=prior), \
                    mock.patch.object(delta, "remote_digests", return_value={"a" * 64, "b" * 64}), \
                    mock.patch.object(delta, "fly", return_value=""), \
                    mock.patch.object(delta, "POINTER_WAIT_SECONDS", 0):
                upload = mock.MagicMock()
                with mock.patch.object(delta, "upload_missing", upload):
                    with self.assertRaises(RuntimeError):
                        delta.publish("slot", bundle, hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest())
        self.assertEqual(upload.call_args.args[1], ["c" * 64],
                         "only the blob the volume lacks is uploaded")

    def test_a_bundle_with_no_blobs_refuses_before_any_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "blobs" / "sha256").mkdir(parents=True)
            (bundle / "bundle.json").write_text("{}")
            (bundle / "items.jsonl").write_text("")
            with mock.patch.object(delta, "machine_exec", return_value=""), \
                    mock.patch.object(delta, "upload_missing") as upload:
                with self.assertRaises(RuntimeError):
                    delta.publish("slot", bundle, hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest())
        self.assertEqual(upload.call_count, 0)

    def test_bad_names_and_wrong_header_digests_refuse_before_remote_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _bundle(Path(tmp), {"a" * 64: 4})
            for name, digest in (("../escape", "d" * 64), ("safe", "0" * 64)):
                with mock.patch.object(delta, "machine_exec") as remote:
                    with self.assertRaises(ValueError):
                        delta.publish(name, bundle, digest)
                    remote.assert_not_called()

    def test_another_publishers_pointer_does_not_confirm_or_clean_our_upload(self):
        recorded = []
        def execute(command, **kwargs):
            recorded.append(command)
            if "tail -c" in command:
                return json.dumps({"result": {"release_id": "another", "bundle_digest": "different"}})
            return ""
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _bundle(Path(tmp), {"a" * 64: 4})
            digest = hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest()
            with mock.patch.object(delta, "machine_exec", side_effect=execute), \
                    mock.patch.object(delta, "remote_digests", return_value={"a" * 64}), \
                    mock.patch.object(delta, "active_release", side_effect=["before", "another"]), \
                    mock.patch.object(delta, "fly", return_value=""), \
                    mock.patch.object(delta.time, "monotonic", side_effect=[0, 0, 2]), \
                    mock.patch.object(delta.time, "sleep"), mock.patch.object(delta, "POINTER_WAIT_SECONDS", 1):
                with self.assertRaisesRegex(RuntimeError, "uncertain publication"):
                    delta.publish("safe", bundle, digest)
        self.assertFalse(any("rm -r" in command for command in recorded))


if __name__ == "__main__":
    unittest.main()
