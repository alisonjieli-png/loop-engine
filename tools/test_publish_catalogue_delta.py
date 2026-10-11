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

from contextlib import redirect_stdout
import hashlib
import json
import os
from io import BytesIO, StringIO
import shlex
import stat
import subprocess
import tarfile
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

    @staticmethod
    def _remote_folder(landed, kind="blobs"):
        """A Machine whose release folder holds `landed`; it answers the read-back's summary and prefix listings."""
        by_prefix = {}
        for name in landed:
            by_prefix.setdefault(name[:2], []).append(name)
        calls = []

        def execute(command, **kwargs):
            calls.append(command)
            if "for d in ??" in command:
                return "\n".join(f"{prefix} {len(names)} {delta._names_digest(names)}"
                                 for prefix, names in sorted(by_prefix.items()))
            for prefix, names in by_prefix.items():
                if f"/{kind}/sha256/{prefix} " in command:
                    return "\n".join(names)
            return ""
        return execute, calls

    def test_a_large_read_back_is_one_bounded_answer_when_every_blob_landed(self):
        expected = [hashlib.sha256(str(n).encode()).hexdigest() for n in range(70_000)]
        for kind in ("blobs", "segments", "items"):
            with self.subTest(kind=kind):
                execute, calls = self._remote_folder(expected, kind)
                with mock.patch.object(delta, "machine_exec", side_effect=execute):
                    self.assertEqual(delta.absent_blobs("delta-test", expected, kind=kind), [])
                self.assertEqual(len(calls), 1)
                self.assertLessEqual(len(execute(calls[0]).splitlines()), 256)
                self.assertIn(f"/{kind}/sha256", calls[0])

    def test_known_wrong_only_a_prefix_that_differs_is_listed_and_never_the_whole_folder(self):
        expected = [hashlib.sha256(str(n).encode()).hexdigest() for n in range(5_000)]
        lost = expected[1234]
        execute, calls = self._remote_folder([name for name in expected if name != lost] + ["f" * 64])
        with mock.patch.object(delta, "machine_exec", side_effect=execute):
            self.assertEqual(delta.absent_blobs("delta-test", expected), [lost])
        listings = [command for command in calls if "for d in ??" not in command]
        self.assertEqual(len(listings), 2)  # the lost blob's prefix and the prefix holding the stray file
        self.assertTrue(any(f"/blobs/sha256/{lost[:2]} " in command for command in listings))
        for command in calls:
            self.assertNotRegex(command, r"find \S+/blobs/sha256 -type f")

    def test_known_wrong_the_upload_never_asks_for_every_landed_name_at_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            blobs = {hashlib.sha256(str(n).encode()).hexdigest(): 4 for n in range(300)}
            bundle = _bundle(Path(tmp), blobs)
            execute, calls = self._remote_folder(list(blobs))
            with mock.patch.object(delta, "machine_exec", side_effect=execute), \
                    mock.patch.object(delta, "extract_archive"), mock.patch.object(delta, "fly", return_value=""):
                self.assertIsNone(delta.upload_missing(bundle, sorted(blobs), "delta-test"))
        self.assertTrue(calls)
        for command in calls:
            self.assertNotRegex(command, r"find \S+/blobs/sha256 -type f")

    def test_the_summary_digest_matches_the_machine_shell(self):
        names = [hashlib.sha256(str(n).encode()).hexdigest() for n in range(40)] + ["0" * 64, "a" * 64]
        with tempfile.TemporaryDirectory() as tmp:
            for name in names:
                Path(tmp, name).write_bytes(b"")
            shell = subprocess.run(["sh", "-c", f"find {tmp} -maxdepth 1 -type f -printf '%f\\n' | "
                                    "LC_ALL=C sort | sha256sum | cut -c1-64"],
                                   capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(delta._names_digest(names), shell)

    def test_a_segment_cannot_stand_in_for_an_item_with_the_same_digest(self):
        digest = hashlib.sha256(b"object").hexdigest()
        relative = f"items/sha256/{digest[:2]}/{digest}"
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            target = bundle / relative
            target.parent.mkdir(parents=True)
            target.write_bytes(b"object")

            def execute(command, **kwargs):
                # The old combined listing loses whether the file was an item or a segment.
                if "/segments " in command and "/items " in command:
                    return f"sha256/{digest[:2]}/{digest}\n"
                return ""  # the actual items directory is empty

            with mock.patch.object(delta, "machine_exec", side_effect=execute), \
                    mock.patch.object(delta, "extract_archive"), mock.patch.object(delta, "fly", return_value=""):
                with self.assertRaises(RuntimeError):
                    delta.upload_missing(bundle, [], "delta-test", extra_paths=[relative])

    def test_an_unreadable_listing_is_an_error_and_never_an_empty_set(self):
        def refusing_exec(command, **kwargs):
            raise RuntimeError("the listing failed")

        with mock.patch.object(delta, "machine_exec", side_effect=refusing_exec):
            with self.assertRaises(RuntimeError):
                delta.remote_digests()


class StagedOwnership(unittest.TestCase):
    """Every staged object reaches the Machine owned by the service user that publishes it.

    On October 9, 2026 publication 83 stopped before activation: the root extraction kept the workstation owner
    (UID 1000, mode 0600) on 151,841 staged objects, and the native publisher, running as UID 65534, could not
    read them. Removing `service_owned` from the archive puts that behaviour back and fails the first check.
    """

    def test_staged_archive_names_the_service_user_and_keeps_private_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _bundle(Path(tmp), {"a" * 64: 4, "b" * 64: 4})
            for path in (bundle / "blobs").rglob("*"):
                if path.is_file():
                    path.chmod(0o600)
            missing = ["a" * 64, "b" * 64]
            members = []

            def capture(archive, remote_archive, digest):
                with tarfile.open(archive) as stream:
                    members.extend(stream.getmembers())

            def fake_exec(command, **kwargs):
                return "\n".join(missing) if "find" in command else ""

            # The publication operators run with umask 077, so each staged copy is private (0600), as in October 9.
            previous = os.umask(0o077)
            try:
                with mock.patch.object(delta, "machine_exec", side_effect=fake_exec), \
                        mock.patch.object(delta, "extract_archive"), \
                        mock.patch.object(delta, "put_archive", side_effect=capture):
                    delta.upload_missing(bundle, missing, "delta-test", compress=True)
            finally:
                os.umask(previous)
            self.assertEqual(sorted(member.name for member in members), sorted(delta.blob_path(d) for d in missing))
            for member in members:
                self.assertEqual((member.uid, member.gid, member.uname, member.gname), (65534, 65534, "", ""))
                self.assertEqual(member.mode & 0o777, 0o600)

    def test_extraction_restores_the_numeric_owner_the_archive_names(self):
        with mock.patch.object(delta, "machine_exec", side_effect=["a" * 64 + " archive", "", "0"]) as remote:
            delta.extract_archive("/data/incoming/probe.tar", "a" * 64, "/data/incoming/probe")
        self.assertIn("tar --numeric-owner -xf /data/incoming/probe.tar", remote.call_args_list[1].args[0])


class DeltaStagingOwnership(unittest.TestCase):
    """Private upload modes survive; only a fully checked exact stage changes owner."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.incoming = Path(self.temporary.name) / 'incoming'
        self.stage = self.incoming / ('delta-slot-' + 'a' * 12)
        self.stage.mkdir(parents=True, mode=0o700)
        nested = self.stage / 'segments' / 'sha256' / 'ab'
        nested.mkdir(parents=True, mode=0o700)
        self.payload = nested / ('ab' + '1' * 62)
        self.payload.write_bytes(b'private staged payload')
        for path in [self.stage, *self.stage.rglob('*')]:
            path.chmod(0o700 if path.is_dir() else 0o600)
        self.outside = self.incoming / 'existing-published-object'
        self.outside.write_bytes(b'published bytes must not change')
        self.outside.chmod(0o600)

    def own(self):
        # An ordinary CI user can reassert its own ownership through the real
        # descriptor syscall. The production wrapper pins service UID/GID65534.
        return delta.own_staging_tree(str(self.stage), str(self.incoming), os.getuid(), os.getgid())

    def snapshot(self):
        return {str(path): (path.lstat().st_uid, path.lstat().st_gid,
                stat.S_IMODE(path.lstat().st_mode), path.lstat().st_ino,
                path.read_bytes() if path.is_file() and not path.is_symlink() else None)
                for path in [self.incoming, self.stage, *self.stage.rglob('*'), self.outside]}

    def assert_originals_preserved(self, before):
        after = self.snapshot()
        self.assertEqual({path: after[path] for path in before}, before)
        self.assertEqual(set(after) - set(before), {str(self.stage / 'ownership-transfer.jsonl')})

    def journal(self):
        return [json.loads(line) for line in (self.stage / 'ownership-transfer.jsonl').read_text().splitlines()]

    def test_private_tree_changes_exact_owners_without_chmod_or_source_changes(self):
        before = self.snapshot()
        touched = []
        original = os.fchown
        def change(fd, uid, gid):
            prepared = self.journal()
            self.assertEqual(prepared[0]['state'], 'prepared')
            self.assertEqual(len(prepared), prepared[0]['entries'] + 1)
            self.assertFalse(any(row.get('state') == 'verified' for row in prepared))
            touched.append((os.fstat(fd).st_ino, uid, gid))
            original(fd, uid, gid)
        with mock.patch.object(os, 'fchown', side_effect=change), \
                mock.patch.object(os, 'chmod', side_effect=AssertionError('no chmod')), \
                mock.patch.object(os, 'fchmod', side_effect=AssertionError('no fchmod')):
            receipt = self.own()
        self.assertEqual(receipt['record_type'], 'catalogue_staging_ownership/v1')
        self.assertEqual((receipt['directories'], receipt['files']), (4, 2))
        self.assertEqual(receipt['stage'], self.stage.name)
        self.assertIs(receipt['helper_wrote_payload_bytes'], False)
        expected = {path.stat().st_ino for path in [self.stage, *self.stage.rglob('*')]}
        self.assertEqual({row[0] for row in touched}, expected)
        self.assertEqual(len(touched), len(expected))
        self.assertTrue(all(row[1:] == (os.getuid(), os.getgid()) for row in touched))
        self.assert_originals_preserved(before)
        journal = self.journal()
        self.assertEqual(journal[-1]['state'], 'verified')
        self.assertEqual(journal[-1]['entries'], len(expected))
        self.assertEqual((self.stage / receipt['journal']).stat().st_mode & 0o777, 0o600)

    def test_links_and_special_entries_refuse_before_any_ownership_write(self):
        for kind in ('file_symlink', 'directory_symlink', 'hardlink', 'fifo'):
            with self.subTest(kind=kind):
                invalid = self.stage / ('z-' + kind)
                if kind == 'file_symlink': invalid.symlink_to(self.outside)
                elif kind == 'directory_symlink': invalid.symlink_to(self.incoming, target_is_directory=True)
                elif kind == 'hardlink': os.link(self.outside, invalid)
                else: os.mkfifo(invalid)
                with mock.patch.object(os, 'fchown') as ownership:
                    with self.assertRaisesRegex(RuntimeError, 'staging ownership refused'):
                        self.own()
                    ownership.assert_not_called()
                invalid.unlink()
        self.assertEqual(self.outside.read_bytes(), b'published bytes must not change')

    def test_stage_or_ancestor_symlink_and_broad_targets_refuse_before_writes(self):
        alias = Path(self.temporary.name) / 'alias'
        alias.symlink_to(self.incoming, target_is_directory=True)
        linked_stage = self.incoming / ('delta-linked-' + 'a' * 12)
        linked_stage.symlink_to(self.stage, target_is_directory=True)
        for stage, incoming in ((str(linked_stage), str(self.incoming)),
                (str(alias / self.stage.name), str(alias)),
                (str(self.incoming), str(self.incoming)),
                (str(self.outside), str(self.incoming)),
                (str(self.stage / '..' / self.stage.name), str(self.incoming)),
                (str(self.stage), '/')):
            with self.subTest(stage=stage, incoming=incoming), mock.patch.object(os, 'fchown') as ownership:
                with self.assertRaisesRegex((RuntimeError, ValueError), 'staging ownership'):
                    delta.own_staging_tree(stage, incoming, os.getuid(), os.getgid())
                ownership.assert_not_called()
                self.assertFalse((self.stage / 'ownership-transfer.jsonl').exists())

    def test_unreadable_owner_modes_or_setid_refuse_before_writes(self):
        for mode in (0o000, 0o200, 0o4600, 0o2600):
            with self.subTest(mode=mode), mock.patch.object(os, 'fchown') as ownership:
                self.payload.chmod(mode)
                with self.assertRaisesRegex(RuntimeError, 'staging ownership refused'):
                    self.own()
                ownership.assert_not_called()
        self.payload.chmod(0o600)

    def test_failed_ownership_retains_all_bytes_and_never_claims_completion(self):
        before = self.snapshot()
        with mock.patch.object(os, 'fchown', side_effect=PermissionError('synthetic refusal')):
            with self.assertRaisesRegex(RuntimeError, 'staging ownership refused.*preserve'):
                self.own()
        self.assert_originals_preserved(before)
        self.assertEqual(self.journal()[0]['state'], 'prepared')
        self.assertFalse(any(row.get('state') == 'verified' for row in self.journal()))

    def test_generated_remote_helper_pins_service_owner_and_runs_same_checked_code(self):
        with mock.patch.object(delta, 'machine_exec', return_value='verified') as remote:
            self.assertEqual(delta.prepare_staging_owner(self.stage.name), 'verified')
        arguments = shlex.split(remote.call_args.args[0])
        self.assertEqual(arguments[:2], ['python3', '-c'])
        script = arguments[2]
        self.assertIn(repr(delta.REMOTE_ROOT + '/' + self.stage.name), script)
        self.assertIn('65534, 65534)', script)
        self.assertEqual(remote.call_args.kwargs, {'timeout':delta.EXEC_TIMEOUT})
        # Rebind only the declared root and owner numbers to this unprivileged
        # temporary fixture; run the exact serialized helper in a fresh process.
        local_script = script.replace(repr(delta.REMOTE_ROOT + '/' + self.stage.name), repr(str(self.stage)))
        local_script = local_script.replace(repr(delta.REMOTE_ROOT), repr(str(self.incoming)))
        local_script = local_script.replace('65534, 65534)', f'{os.getuid()}, {os.getgid()})')
        before = self.snapshot()
        completed = subprocess.run([delta.sys.executable, '-c', local_script],
                                   capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)['stage'], self.stage.name)
        self.assert_originals_preserved(before)

    def test_journal_and_directory_are_flushed_before_any_ownership_write(self):
        events = []
        flush, ownership = os.fsync, os.fchown
        def record_flush(fd):
            events.append(('flush', os.fstat(fd).st_ino))
            return flush(fd)
        def record_ownership(fd, uid, gid):
            events.append(('owner', os.fstat(fd).st_ino))
            return ownership(fd, uid, gid)
        with mock.patch.object(os, 'fsync', side_effect=record_flush), \
                mock.patch.object(os, 'fchown', side_effect=record_ownership):
            self.own()
        journal_inode = (self.stage / 'ownership-transfer.jsonl').stat().st_ino
        self.assertEqual(events[:2], [('flush', journal_inode), ('flush', self.stage.stat().st_ino)])
        self.assertEqual(events[-1], ('flush', journal_inode))

    def test_failed_journal_flush_or_existing_journal_never_changes_ownership(self):
        with mock.patch.object(os, 'fsync', side_effect=OSError('synthetic flush failure')), \
                mock.patch.object(os, 'fchown') as ownership:
            with self.assertRaisesRegex(RuntimeError, 'staging ownership refused'):
                self.own()
            ownership.assert_not_called()
        before = self.snapshot()
        with mock.patch.object(os, 'fchown') as ownership:
            with self.assertRaisesRegex(RuntimeError, 'staging ownership refused'):
                self.own()
            ownership.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_unapplied_owner_transfer_cannot_get_a_completion_record(self):
        different_uid = os.getuid() + 1
        with mock.patch.object(os, 'fchown', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'staging ownership refused'):
                delta.own_staging_tree(str(self.stage), str(self.incoming), different_uid, os.getgid())
        self.assertFalse(any(row.get('state') == 'verified' for row in self.journal()))

    def test_changed_pretransfer_owner_refuses_before_first_chown(self):
        root_inode = self.stage.stat().st_ino
        flush, stat_fd = os.fsync, os.fstat
        flushes = []
        def change_after_journal_flush(fd):
            flushes.append(fd)
            return flush(fd)
        def changed_owner(fd):
            info = stat_fd(fd)
            if len(flushes) >= 2 and info.st_ino == root_inode:
                values = list(info)
                values[4] += 1
                return os.stat_result(values)
            return info
        with mock.patch.object(os, 'fsync', side_effect=change_after_journal_flush), \
                mock.patch.object(os, 'fstat', side_effect=changed_owner), \
                mock.patch.object(os, 'fchown') as ownership:
            with self.assertRaisesRegex(RuntimeError, 'staging ownership refused'):
                self.own()
            ownership.assert_not_called()
        self.assertEqual(self.journal()[0]['state'], 'prepared')
        self.assertFalse(any(row.get('state') == 'verified' for row in self.journal()))

    def test_invalid_remote_names_never_execute_an_ownership_command(self):
        for name in ('../published', 'delta-slot', 'delta-slot-' + 'a' * 12 + ';true', None, []):
            with self.subTest(name=name), mock.patch.object(delta, 'machine_exec') as remote:
                with self.assertRaisesRegex(ValueError, 'exact stage'):
                    delta.prepare_staging_owner(name)
                remote.assert_not_called()

    def test_disappearing_or_replaced_entries_refuse_in_second_pass(self):
        original = os.fchown
        calls = []
        def race(fd, uid, gid):
            original(fd, uid, gid)
            calls.append(os.fstat(fd).st_ino)
            if len(calls) == 1:
                self.payload.unlink()
                self.payload.symlink_to(self.outside)
        with mock.patch.object(os, 'fchown', side_effect=race):
            with self.assertRaisesRegex(RuntimeError, 'staging ownership refused'):
                self.own()
        self.assertEqual(self.outside.read_bytes(), b'published bytes must not change')
        self.assertNotIn(self.outside.stat().st_ino, calls)


class DeltaPublishOrder(unittest.TestCase):
    """Current-base publication, exercised through real local bundle/proof readers."""

    def setUp(self):
        import reconcile_catalogue_bundle as reconcile
        from test_reconcile_catalogue_bundle import bundle, line, request, observation
        self.reconcile = reconcile
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.base = bundle(root/'base', [line('old','held')], ['held'])
        self.update = bundle(root/'update', [line('new','new'),line('same-bytes','held')], ['new','held'])
        changes = request(self.base, additions=('new','same-bytes'))
        self.before = observation(self.base)
        self.output = root/'output'
        self.plan = reconcile.write_reconciled(self.base,(self.update,),changes,self.output,self.before)
        self.digest = self.plan['bundle_digest']
        self.kwargs = {'base_bundle':self.base.folder, 'base_release':'a'*64,
                       'reconciliation_digest':self.plan['reconciliation_digest']}
        self.proof = json.loads((self.output/reconcile.PROOF_FILE).read_text())
        self.after = {**self.before, 'release_id':self.proof['result_release'],
                      'content_digest':self.proof['result_content_digest'], 'items':3}
        self.result = {'release_id':self.after['release_id'], 'content_digest':self.after['content_digest'],
                       'bundle_digest':self.digest}
        self.commands = []

    def execute(self, command, **kwargs):
        self.commands.append(command)
        if 'tail -c' in command:
            return getattr(self, 'receipt_text', json.dumps({'result':self.result}))
        return ''

    def simulate(self, observations=None):
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(delta,'machine_exec',side_effect=self.execute))
            stack.enter_context(mock.patch.object(delta,'active_catalogue',side_effect=observations or [self.before,self.before,self.after]))
            upload=stack.enter_context(mock.patch.object(delta,'upload_missing'))
            stack.enter_context(mock.patch.object(delta,'fly',return_value=''))
            stack.enter_context(mock.patch.object(delta.time,'monotonic',side_effect=[0,0,2]))
            stack.enter_context(mock.patch.object(delta.time,'sleep'))
            stack.enter_context(mock.patch.object(delta,'POINTER_WAIT_SECONDS',1))
            answer=delta.publish('slot',self.output,self.digest,**self.kwargs)
            return answer,upload

    def test_a_typed_native_error_ends_the_wait_as_a_refusal(self):
        # Publication 83's native command wrote service_cli_error/v1; the wait matched only older words and
        # polled for nineteen minutes. The fake applies the loop's own grep pattern to that receipt.
        receipt = json.dumps({'record_type': 'service_cli_error/v1', 'code': 'service_configuration_or_io_failure',
                              'effect_commitment': 'not_asserted', 'automatic_retry': False})

        def execute(command, **kwargs):
            self.commands.append(command)
            if 'tail -c' in command:
                return receipt
            if 'grep -q' in command:
                pattern = command.split("grep -q '", 1)[1].split("'", 1)[0]
                words = [word.replace('\\"', '"') for word in pattern.split('\\|')]
                return receipt if any(word in receipt for word in words) else ''
            return ''
        self.execute = execute
        with self.assertRaisesRegex(RuntimeError, 'native publication error service_configuration_or_io_failure'):
            self.simulate([self.before, self.before, self.before])
        self.assertFalse(any('rm -r' in command for command in self.commands))

    def test_exact_result_and_live_content_confirm_only_our_release(self):
        answer,upload=self.simulate()
        self.assertTrue(answer['published'])
        self.assertEqual(answer['active_release_id'],self.proof['result_release'])
        self.assertEqual(upload.call_args.args[1],[hashlib.sha256(b'new').hexdigest()])
        command=next(value for value in self.commands if 'publish-catalogue' in value)
        self.assertIn('--expected-bundle-digest '+self.digest,command)
        self.assertIn('--expected-release '+'a'*64,command)
        self.assertTrue(any('rm -r' in command for command in self.commands))

    def test_exact_ownership_transfer_precedes_native_dispatch_and_failure_stops_it(self):
        self.simulate()
        self.assertTrue(any(command.startswith('python3 -c ') for command in self.commands))
        ownership = next(index for index, command in enumerate(self.commands) if command.startswith('python3 -c '))
        dispatch = next(index for index, command in enumerate(self.commands) if 'publish-catalogue' in command)
        self.assertLess(ownership, dispatch)
        self.assertFalse(any(command.startswith('chown ') for command in self.commands))
        original = self.execute
        def refuse(command, **kwargs):
            if command.startswith('python3 -c '):
                self.commands.append(command)
                raise RuntimeError('synthetic ownership refusal')
            return original(command, **kwargs)
        self.commands = []
        with mock.patch.object(self, 'execute', side_effect=refuse):
            with self.assertRaisesRegex(RuntimeError, 'ownership refusal'):
                self.simulate()
        self.assertFalse(any('publish-catalogue' in command or 'rm -r' in command for command in self.commands))

    def test_a_blob_the_base_holds_is_not_uploaded_again_and_one_it_lacks_is(self):
        # A reconciled bundle writes only the bodies its base lacks, so the candidate here also keeps a copy of the base's
        # 'held' body, as a bundle written with every payload would. The publish and the dry run's plan must both send
        # 'new' alone. Until October 5, 2026 this check filtered a list written inside the test and called no tool code.
        held=hashlib.sha256(b'held').hexdigest()
        source=next(self.base.folder.glob('blobs/sha256/*/'+held))
        kept=self.output/source.relative_to(self.base.folder)
        kept.parent.mkdir(parents=True,exist_ok=True)
        kept.write_bytes(source.read_bytes())
        answer,upload=self.simulate()
        self.assertEqual(upload.call_args.args[1],[hashlib.sha256(b'new').hexdigest()])
        argv=['publish_catalogue_delta.py','slot',str(self.output),self.digest,'--base-bundle',str(self.base.folder),
              '--base-release','a'*64,'--reconciliation-digest',self.plan['reconciliation_digest'],'--dry-run']
        printed=StringIO()
        with mock.patch('sys.argv',argv),redirect_stdout(printed):
            self.assertEqual(delta.main(),0)
        for plan in (answer,json.loads(printed.getvalue())):
            self.assertEqual((plan['local_blobs'],plan['already_present'],plan['uploading'],plan['upload_bytes']),(2,1,1,3))

    def test_a_stale_base_refuses_before_any_remote_effect(self):
        with mock.patch.object(delta,'active_catalogue',return_value={**self.before,'release_id':'b'*64}), \
                mock.patch.object(delta,'machine_exec') as remote, mock.patch.object(delta,'upload_missing') as upload:
            with self.assertRaisesRegex(ValueError,'live baseline'):
                delta.publish('slot',self.output,self.digest,**self.kwargs)
            remote.assert_not_called()
            upload.assert_not_called()

    def test_base_content_mismatch_refuses_before_any_remote_effect(self):
        with mock.patch.object(delta,'active_catalogue',return_value={**self.before,'content_digest':'b'*64}), \
                mock.patch.object(delta,'machine_exec') as remote:
            with self.assertRaisesRegex(ValueError,'live baseline'):
                delta.publish('slot',self.output,self.digest,**self.kwargs)
            remote.assert_not_called()

    def test_a_withdrawn_live_row_this_proof_keeps_refuses_before_any_remote_effect(self):
        # The live view leaves out 'old' after a durable withdrawal; this additions-only proof still lists it, which the
        # service refuses. Every remote function is mocked, so the old code's upload never reaches a Machine.
        withdrawn={**self.before,'items':0,'withdrawn_left_out':1}
        with self.assertRaisesRegex(ValueError,'durably withdrawn'):
            self.simulate([withdrawn,withdrawn,self.after])
        self.assertEqual(self.commands,[])

    def test_concurrent_pointer_move_after_upload_refuses_server_publish(self):
        with self.assertRaisesRegex(ValueError,'live baseline'):
            self.simulate([self.before,{**self.before,'release_id':'c'*64}])
        self.assertFalse(any('publish-catalogue' in command for command in self.commands))
        self.assertFalse(any('rm -r' in command for command in self.commands))

    def test_unrelated_pointer_or_wrong_result_content_never_confirms(self):
        for mutate in ('pointer','result_content','live_content'):
            with self.subTest(mutate=mutate):
                self.commands=[]
                after=dict(self.after)
                self.result={'release_id':self.after['release_id'],'content_digest':self.after['content_digest'],'bundle_digest':self.digest}
                if mutate=='pointer':after['release_id']='c'*64;self.result['release_id']='c'*64
                elif mutate=='result_content':self.result['content_digest']='d'*64
                else:after['content_digest']='e'*64
                with self.assertRaisesRegex(RuntimeError,'uncertain publication'):
                    self.simulate([self.before,self.before,after])
                self.assertFalse(any('rm -r' in command for command in self.commands))

    def test_native_structured_error_stops_without_retry_or_cleanup_even_without_health(self):
        # This is the native CLI's lower-case error record, which the old grep
        # missed. A generic error does not prove that no earlier effect committed.
        for observed in (self.before, {}, self.after):
            for wrapped in (False, True):
                with self.subTest(observed=observed, wrapped=wrapped):
                    self.commands = []
                    failure = {'record_type':'service_cli_error/v1',
                               'code':'service_configuration_or_io_failure',
                               'effect_commitment':'not_asserted', 'automatic_retry':False}
                    self.receipt_text = json.dumps({'result':failure} if wrapped else failure)
                    with self.assertRaisesRegex(RuntimeError, 'service_configuration_or_io_failure.*reconciliation required') as raised:
                        self.simulate([self.before, self.before, observed])
                    message = str(raised.exception)
                    self.assertIn('effect commitment is not asserted', message)
                    self.assertIn('preserve staging and receipt', message)
                    self.assertIn('no automatic retry', message)
                    self.assertNotIn('nothing was published', message)
                    self.assertEqual(sum('publish-catalogue' in command for command in self.commands), 1)
                    self.assertFalse(any('rm -r' in command or command.startswith('cp ') for command in self.commands))

    def test_native_error_cannot_be_hidden_by_matching_result_claims(self):
        self.receipt_text = json.dumps({'record_type':'service_cli_error/v1',
            'code':'commit_unknown', 'effect_commitment':'not_asserted',
            'automatic_retry':False, 'result':self.result})
        with self.assertRaisesRegex(RuntimeError, 'commit_unknown.*reconciliation required'):
            self.simulate()
        self.assertFalse(any('rm -r' in command or command.startswith('cp ') for command in self.commands))

    def test_malformed_receipts_never_confirm_or_crash_shape_reading(self):
        for receipt in ('[]', 'null', 'true', '"receipt"', '{"result":[]}',
                        '{"result":null}', '{"result":true}', '{"result":"receipt"}',
                        '{"record_type":"service_cli_error/v1",',
                        '{"result":' + json.dumps(self.result) + ',"result":null}',
                        json.dumps({'result':self.result, 'number':float('nan')})):
            with self.subTest(receipt=receipt):
                self.commands = []
                self.receipt_text = receipt
                with self.assertRaisesRegex(RuntimeError, 'uncertain publication'):
                    self.simulate()
                self.assertFalse(any('rm -r' in command or command.startswith('cp ') for command in self.commands))

    def test_structured_refusal_precedes_matching_success_claims(self):
        self.receipt_text = json.dumps({'refused':True, 'result':self.result})
        with self.assertRaisesRegex(RuntimeError, 'reconciliation required'):
            self.simulate()
        self.assertFalse(any('rm -r' in command for command in self.commands))

    def test_error_code_is_bounded_sanitized_and_cannot_authorize_retry(self):
        for code in (None, {}, [], 'private detail\ncredential', 'x' * 129):
            with self.subTest(code=code):
                self.receipt_text = json.dumps({'record_type':'service_cli_error/v1',
                    'code':code, 'effect_commitment':'none', 'automatic_retry':True})
                with self.assertRaisesRegex(RuntimeError, 'unreadable_error_code.*reconciliation required') as raised:
                    self.simulate()
                self.assertNotIn('private detail', str(raised.exception))
                self.assertIn('no automatic retry', str(raised.exception))

    def test_changed_proof_or_missing_base_is_not_a_legacy_bypass(self):
        for kwargs in ({}, {**self.kwargs,'reconciliation_digest':'0'*64},
                       {**self.kwargs,'base_release':'b'*64}):
            with self.subTest(kwargs=kwargs), mock.patch.object(delta,'machine_exec') as remote:
                with self.assertRaises(ValueError):
                    delta.publish('slot',self.output,self.digest,**kwargs)
                remote.assert_not_called()

    def test_bad_names_and_wrong_headers_refuse_before_remote_effects(self):
        for name,digest in (('../escape',self.digest),('safe','0'*64)):
            with mock.patch.object(delta,'machine_exec') as remote:
                with self.assertRaises(ValueError):
                    delta.publish(name,self.output,digest,**self.kwargs)
                remote.assert_not_called()

    def test_declared_withdrawal_only_snapshot_needs_no_new_blob_upload(self):
        from test_reconcile_catalogue_bundle import bundle,line,request,observation
        root=Path(self.folder.name)
        base=bundle(root/'withdraw-base',[line('kept','held'),line('removed','removed')],['held','removed'])
        version=next(item.version for item in base.items if item.identity=='removed')
        changes=request(base,withdrawals=({'identity':'removed','expected_version':version,'note':'Explicit withdrawal'},))
        self.before=observation(base)
        self.base=base
        self.output=root/'withdraw-output'
        self.plan=self.reconcile.write_reconciled(base,(),changes,self.output,self.before)
        self.digest=self.plan['bundle_digest']
        self.kwargs={'base_bundle':base.folder,'base_release':'a'*64,'reconciliation_digest':self.plan['reconciliation_digest']}
        self.proof=json.loads((self.output/self.reconcile.PROOF_FILE).read_text())
        self.after={**self.before,'release_id':self.proof['result_release'],'content_digest':self.proof['result_content_digest'],'items':1}
        self.result={'release_id':self.after['release_id'],'content_digest':self.after['content_digest'],'bundle_digest':self.digest}
        answer,upload=self.simulate()
        self.assertTrue(answer['published'])
        self.assertEqual(upload.call_args.args[1],[])

    def test_missing_live_row_with_a_rehashed_proof_still_refuses(self):
        from test_reconcile_catalogue_bundle import bundle,line
        bad=bundle(Path(self.folder.name)/'bad',[line('new','new'),line('same-bytes','held')],['new','held'])
        proof={**self.proof,'bundle_digest':bad.digest}
        raw=json.dumps(proof).encode()
        (bad.folder/self.reconcile.PROOF_FILE).write_bytes(raw)
        with mock.patch.object(delta,'machine_exec') as remote:
            with self.assertRaisesRegex(ValueError,'preservation'):
                delta.publish('slot',bad.folder,bad.digest,base_bundle=self.base.folder,
                    base_release='a'*64,reconciliation_digest=hashlib.sha256(raw).hexdigest())
            remote.assert_not_called()

    def test_dry_run_verifies_locally_without_any_live_request(self):
        argv=['publish_catalogue_delta.py','slot',str(self.output),self.digest,
              '--base-bundle',str(self.base.folder),'--base-release','a'*64,
              '--reconciliation-digest',self.plan['reconciliation_digest'],'--dry-run']
        with mock.patch('sys.argv',argv),mock.patch.object(delta,'active_catalogue') as live, \
                mock.patch.object(delta,'machine_exec') as remote:
            self.assertEqual(delta.main(),0)
            live.assert_not_called()
            remote.assert_not_called()

if __name__ == "__main__":
    unittest.main()
