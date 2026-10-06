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
from io import BytesIO, StringIO
import subprocess
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
        return json.dumps({'result':self.result}) if 'tail -c' in command else ''

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

    def test_exact_result_and_live_content_confirm_only_our_release(self):
        answer,upload=self.simulate()
        self.assertTrue(answer['published'])
        self.assertEqual(answer['active_release_id'],self.proof['result_release'])
        self.assertEqual(upload.call_args.args[1],[hashlib.sha256(b'new').hexdigest()])
        command=next(value for value in self.commands if 'publish-catalogue' in value)
        self.assertIn('--expected-bundle-digest '+self.digest,command)
        self.assertIn('--expected-release '+'a'*64,command)
        self.assertTrue(any('rm -r' in command for command in self.commands))

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
