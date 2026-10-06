"""Compressed bounded transfer and explicit stage recovery, without provider calls."""
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import tarfile
import tempfile
import threading
import unittest
from unittest import mock

import publish_catalogue_delta as tool
from test_publish_catalogue_delta import DeltaPublishOrder


class TransferTests(unittest.TestCase):
    def test_four_compressed_transfers_preserve_bytes_and_own_distinct_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            payloads = {hashlib.sha256(bytes([n]) * 100_000).hexdigest(): bytes([n]) * 100_000 for n in range(8)}
            for digest, raw in payloads.items():
                path = bundle / tool.blob_path(digest)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            barrier = threading.Barrier(4)
            lock = threading.Lock()
            sent, extracted = {}, []
            active = maximum = 0

            def upload(*arguments, **_fields):
                nonlocal active, maximum
                local, remote = Path(arguments[3]), arguments[4]
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                barrier.wait(timeout=5)
                archive = local.read_bytes()
                self.assertTrue(remote.endswith(".tar.gz"))
                with tarfile.open(local, "r:gz") as stream:
                    members = stream.getmembers()
                    self.assertEqual(len(members), 1)
                    member = members[0]
                    self.assertTrue(member.isfile())
                    raw = stream.extractfile(member).read()
                    self.assertEqual(raw, payloads[member.name.rsplit("/", 1)[-1]])
                with lock:
                    self.assertNotIn(remote, sent)
                    sent[remote] = archive
                    active -= 1
                return ""

            def extract(remote, digest, destination):
                self.assertEqual(hashlib.sha256(sent[remote]).hexdigest(), digest)
                self.assertEqual(destination, tool.REMOTE_ROOT + "/delta-test")
                with lock:
                    extracted.append(remote)

            with mock.patch.object(tool, "BATCH_BYTES", 100_000), mock.patch.object(tool, "fly", side_effect=upload), \
                    mock.patch.object(tool, "extract_archive", side_effect=extract), \
                    mock.patch.object(tool, "absent_blobs", return_value=[]), redirect_stdout(StringIO()):
                tool.upload_missing(bundle, sorted(payloads), "delta-test", workers=4, compress=True)
            self.assertEqual((len(sent), len(extracted), maximum), (8, 8, 4))
            self.assertLess(sum(map(len, sent.values())), sum(map(len, payloads.values())) / 20)

    def test_invalid_parallelism_refuses_before_any_transfer(self):
        for workers in (0, 5, True, 1.5):
            with self.subTest(workers=workers), mock.patch.object(tool, "fly") as transport:
                with self.assertRaises(ValueError):
                    tool.upload_missing(Path("unused"), [], "delta-test", workers=workers)
                transport.assert_not_called()

    def test_stage_context_refuses_dispatch_changed_binding_and_unapproved_adoption(self):
        context = {"record_type": "catalogue_upload_staging/v1", "bundle_digest": "a" * 64}
        for state, expected in (("dispatched", "already dispatched"), (json.dumps({**context, "bundle_digest": "b" * 64}),
                                "another exact publication"), ("unbound", "explicit adoption"), ("bad-json", "unreadable")):
            with self.subTest(state=state), mock.patch.object(tool, "machine_exec", return_value=state), \
                    mock.patch.object(tool, "fly") as transport:
                with self.assertRaisesRegex(RuntimeError, expected):
                    tool.bind_staging("delta-test", context, resume=True)
                transport.assert_not_called()

    def test_exact_stage_context_needs_no_rewrite_and_explicit_adoption_hashes_new_context(self):
        context = {"record_type": "catalogue_upload_staging/v1", "bundle_digest": "a" * 64}
        with mock.patch.object(tool, "machine_exec", return_value=json.dumps(context)), mock.patch.object(tool, "fly") as transport:
            tool.bind_staging("delta-test", context, resume=True)
            transport.assert_not_called()
        uploaded = []
        def upload(*arguments, **_fields):
            uploaded.append(Path(arguments[3]).read_bytes())
            self.assertEqual(json.loads(uploaded[-1]), context)
        def execute(command, **_fields):
            return hashlib.sha256(uploaded[0]).hexdigest() + " marker" if command.startswith("sha256sum") else "unbound"
        with mock.patch.object(tool, "machine_exec", side_effect=execute), mock.patch.object(tool, "fly", side_effect=upload):
            tool.bind_staging("delta-test", context, resume=True, adopt_unmarked=True)
        self.assertEqual(len(uploaded), 1)

    def test_recovery_keeps_blob_and_metadata_namespaces_separate(self):
        digest = "a" * 64
        extras = [f"items/sha256/aa/{digest}", f"segments/sha256/aa/{digest}"]
        def absent(_remote, names, *, kind="blobs"):
            return names if kind == "items" else []
        with mock.patch.object(tool, "absent_blobs", side_effect=absent):
            bodies, metadata = tool.remaining_uploads("delta-test", [digest], extras)
        self.assertEqual((bodies, metadata), ([], [extras[0]]))


class PublishRecoveryTests(DeltaPublishOrder):
    """Reuse the actual native local proof fixture and exact-result checks."""

    def test_an_invalid_resume_path_refuses_before_remote_effects(self):
        for remote in ("../escape", "delta-other-123456789abc", "delta-slot-not-hex"):
            with mock.patch.object(tool, "machine_exec") as effect:
                with self.assertRaises(ValueError):
                    tool.publish("slot", self.output, self.digest, **self.kwargs, resume_staging=remote)
                effect.assert_not_called()

    def test_resume_uses_the_same_native_commit_and_keeps_all_proof_checks(self):
        remote = "delta-slot-123456789abc"
        def execute(command, **_fields):
            self.commands.append(command)
            if "publish-result.json; then echo dispatched" in command:
                return json.dumps({"record_type": "catalogue_upload_staging/v1", "name": "slot", "bundle_digest": self.digest,
                    "base_release": "a" * 64, "reconciliation_digest": self.plan["reconciliation_digest"],
                    "result_release": self.proof["result_release"], "result_content_digest": self.proof["result_content_digest"]})
            return json.dumps({"result": self.result}) if "tail -c" in command else ""
        with mock.patch.object(tool, "machine_exec", side_effect=execute), \
                mock.patch.object(tool, "active_catalogue", side_effect=[self.before, self.before, self.after]), \
                mock.patch.object(tool, "remaining_uploads", return_value=([], [])), \
                mock.patch.object(tool, "upload_missing") as upload, mock.patch.object(tool, "fly", return_value=""), \
                mock.patch.object(tool.time, "sleep"), mock.patch.object(tool.time, "monotonic", side_effect=[0, 0, 2]), \
                mock.patch.object(tool, "POINTER_WAIT_SECONDS", 1), redirect_stdout(StringIO()):
            answer = tool.publish("slot", self.output, self.digest, **self.kwargs,
                                  resume_staging=remote, upload_workers=4, compress=True)
        self.assertTrue(answer["published"])
        self.assertEqual(answer["resumed_staged_bodies"], 1)
        self.assertEqual(upload.call_args.args[1:3], ([], remote))
        commits = [command for command in self.commands if "nohup loop-engine service publish-catalogue" in command]
        self.assertEqual(len(commits), 1)
        self.assertIn("--expected-bundle-digest " + self.digest, commits[0])
        self.assertIn("--expected-release " + "a" * 64, commits[0])


if __name__ == "__main__":
    unittest.main()
